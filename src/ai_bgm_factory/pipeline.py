import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import replace
from pathlib import Path

from PIL import Image

from . import __version__
from .config import Config, FactoryError
from .media import audio_qc, master_audio, render, validate_thumbnail
from .providers import PROMPTS, DummyProvider, GenerationProvider, GenerationRequest
from .schemas import validate
from .storage import Store, run_lock
from .track_planning import plan_tracks
from .util import (
    artifact,
    command,
    digest,
    now,
    object_hash,
    read_json,
    safe_path,
    scan_secrets,
    validate_run_id,
    verify_artifacts,
    write_json,
)

STAGES = (
    "initialize",
    "concept",
    "music_generate",
    "audio_qc",
    "audio_master",
    "provenance_gate",
    "visual_generate",
    "render",
    "metadata",
    "package_validate",
)


def implementation_hash():
    root = Path(__file__).parent
    return object_hash(
        {
            str(p.relative_to(root)): digest(p)
            for p in sorted(root.rglob("*"))
            if p.suffix in (".py", ".sql", ".json")
        }
    )


def code_info():
    cwd = Path(__file__).parent
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (subprocess.CalledProcessError, OSError):
        commit, dirty = None, None
    return {
        "git_commit": commit,
        "dirty": dirty,
        "pipeline_version": __version__,
        "implementation_sha256": implementation_hash(),
    }


def stamp(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"


class Pipeline:
    def __init__(self, config: Config, provider: GenerationProvider | None = None,
                 *, music_provider: GenerationProvider | None = None):
        self.config = config
        self.provider = provider or DummyProvider()
        self.music_provider = music_provider or DummyProvider()
        self.dirs = {}

    def _prepare(self):
        descriptors = {}
        for role, provider in (("text_image", self.provider), ("music", self.music_provider)):
            caps = provider.capabilities()
            rights = provider.get_rights_evidence()
            if (caps.get("network_required") is not False or rights.get("status") != "blocked"
                    or rights.get("intended_for_testing_only") is not True):
                raise FactoryError("Only offline test-only providers are enabled")
            descriptors[role] = {
                "adapter": type(provider).__module__ + "." + type(provider).__qualname__,
                "capabilities": caps,
                "rights": rights,
            }
        caps = descriptors["music"]["capabilities"]
        cfg = self.config
        self.plan = plan_tracks(cfg.duration_seconds, caps.get("max_duration_seconds"),
                                min_tracks=cfg.min_track_count,
                                min_duration_seconds=caps.get("min_duration_seconds"),
                                crossfade_seconds=cfg.crossfade_seconds,
                                sample_rate=cfg.sample_rate)
        self.snapshot = {**cfg.snapshot(), "providers": descriptors, "track_plan": self.plan}
        scan_secrets(self.snapshot)

    def execute(self, *, run_id=None, resume=False, fail_stage=None):
        run_id = run_id or uuid.uuid4().hex
        validate_run_id(run_id)
        self._prepare()
        root = self.config.data_dir / "runs" / run_id
        if resume and not root.is_dir():
            raise FactoryError("Cannot resume missing run")
        if not resume:
            try:
                root.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                raise FactoryError("Run already exists; use --resume to verify/reuse it") from None
        with run_lock(root):
            self.root = root
            self.store = Store(self.config.data_dir)
            try:
                return self._execute(run_id, resume, fail_stage)
            finally:
                self.store.close()

    def _execute(self, run_id, resume, fail_stage):
        root = self.root
        if resume:
            self.manifest = read_json(root / "manifest.json")
            validate("manifest", self.manifest)
            m = self.manifest
            if m["implementation_sha256"] != implementation_hash():
                raise FactoryError("Implementation changed; create a new run")
            if m["config_hash"] != object_hash(self.snapshot):
                raise FactoryError("Config changed; create a new run")
            verify_artifacts(root, m["artifacts"])
            if m["status"] == "ready_for_review":
                self.store.save(m)
                return m
        else:
            m = self.manifest = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "status": "created",
                "created_at": now(),
                "updated_at": now(),
                "seed": self.config.seed,
                "config_hash": object_hash(self.snapshot),
                "config": self.snapshot,
                "implementation_sha256": implementation_hash(),
                "stages": [],
                "artifacts": [],
                "review_scope": "local_test_only",
                "publication": {
                    "privacy_status": "private",
                    "approval_required": True,
                    "upload_eligible": False,
                    "rights_status": "blocked",
                },
            }
            self._save()
        (root / "logs").mkdir(exist_ok=True)
        m["status"] = "generating"
        m.pop("error", None)
        self._save()
        for name in STAGES:
            old = next((s for s in m["stages"] if s["name"] == name), None)
            if old and old["status"] == "succeeded":
                self.dirs[name] = safe_path(root, old["directory"])
                continue
            attempt = (old["attempt"] if old else 0) + 1
            directory = root / "stages" / f"{name}-{attempt:03}-{uuid.uuid4().hex[:8]}"
            directory.mkdir(parents=True)
            input_hash = object_hash(
                {
                    "config": m["config_hash"],
                    "stage": name,
                    "implementation": m["implementation_sha256"],
                    "inputs": m["artifacts"],
                }
            )
            stage = {
                "name": name,
                "status": "running",
                "attempt": attempt,
                "started_at": now(),
                "input_hash": input_hash,
                "directory": str(directory.relative_to(root)),
            }
            if old:
                m["stages"][m["stages"].index(old)] = stage
            else:
                m["stages"].append(stage)
            self._save()
            self._event(stage, "running", 0)
            start = time.monotonic()
            try:
                self.dirs[name] = directory
                self._stage(name, directory, inject_failure=fail_stage == name)
                files = [artifact(root, p) for p in sorted(directory.rglob("*")) if p.is_file()]
                if name == "package_validate":
                    files += [
                        artifact(root, root / filename, role)
                        for filename, role in (
                            ("final.mp4", "final_video"),
                            ("thumbnail.jpg", "thumbnail"),
                            ("metadata.json", "metadata"),
                            ("provenance.json", "provenance"),
                        )
                    ]
                # A crashed package stage may have already created identical root aliases.
                paths = {a["path"] for a in files}
                m["artifacts"] = [a for a in m["artifacts"] if a["path"] not in paths] + files
                stage["status"] = "succeeded"
                stage["finished_at"] = now()
                stage["duration_ms"] = round((time.monotonic() - start) * 1000, 2)
                self._save()
                self._event(stage, "succeeded", stage["duration_ms"])
            except BaseException as error:
                stage.update(
                    status="failed",
                    finished_at=now(),
                    duration_ms=round((time.monotonic() - start) * 1000, 2),
                )
                reason = (
                    str(error)
                    if isinstance(error, FactoryError)
                    else (
                        "Interrupted"
                        if isinstance(error, KeyboardInterrupt)
                        else "Internal stage failure; outputs retained for inspection"
                    )
                )
                m.update(
                    status="failed",
                    error={"stage": name, "reason": reason, "type": type(error).__name__},
                )
                self._save()
                self._event(stage, "failed", stage["duration_ms"], reason)
                raise FactoryError(f"Run {run_id} failed at {name}: {reason}") from None
        m["status"] = "ready_for_review"
        self._save()
        return m

    def _save(self):
        self.manifest["updated_at"] = now()
        validate("manifest", self.manifest)
        write_json(self.root / "manifest.json", self.manifest)
        self.store.save(self.manifest)

    def _event(self, stage, status, duration, reason=None):
        event = {
            "schema_version": "1.0.0",
            "timestamp": now(),
            "run_id": self.manifest["run_id"],
            "stage": stage["name"],
            "attempt": stage["attempt"],
            "duration_ms": duration,
            "status": status,
        }
        if reason:
            event["reason"] = reason
        with (self.root / "logs" / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(event) + "\n")
        print(json.dumps(event), flush=True)

    def _generate(self, kind, output, *, slot=0, duration=0):
        provider = self.music_provider if kind == "audio" else self.provider
        response = provider.generate(
            GenerationRequest(kind, self.config.seed, PROMPTS[kind], duration, slot), output
        )
        response["source_path"] = str(output.relative_to(self.root))
        raw = output.with_name(output.stem + ".response.json")
        response["raw_response_path"] = str(raw.relative_to(self.root))
        scan_secrets(response)
        write_json(raw, response)

    def _stage(self, name, directory, inject_failure=False):
        cfg = self.config
        if name == "initialize":
            write_json(directory / "config.json", self.snapshot)
            write_json(directory / "track-plan.json", self.plan)
            write_json(directory / "code.json", {"schema_version": "1.0.0", **code_info()})
        elif name == "concept":
            self._generate("text", directory / "concept.json")
        elif name == "music_generate":
            fade = self.plan["crossfade_frames"] / cfg.sample_rate
            tracks = []
            for planned in self.plan["tracks"]:
                i = planned["slot"]
                duration = planned["frames"] / cfg.sample_rate
                path = directory / f"track-{i + 1:02}.wav"
                self._generate("audio", path, slot=i, duration=duration)
                tracks.append(
                    {
                        "asset_id": path.stem,
                        "path": str(path.relative_to(self.root)),
                        "start_seconds": round(planned["start_frame"] / cfg.sample_rate, 6),
                        "duration_seconds": duration,
                    }
                )
            write_json(
                directory / "timeline.json",
                {
                    "schema_version": "1.0.0",
                    "tracks": tracks,
                    "crossfade_seconds": fade,
                    "duration_seconds": cfg.duration_seconds,
                },
            )
        elif name == "audio_qc":
            for track in self._timeline()["tracks"]:
                report = audio_qc(safe_path(self.root, track["path"]), track["asset_id"])
                if abs(report["measurements"]["duration_seconds"] - track["duration_seconds"]) > (
                    1 / cfg.sample_rate
                ):
                    report["status"] = "failed"
                    report["failures"].append("source_duration_mismatch")
                validate("qc", report)
                write_json(directory / f"{track['asset_id']}.json", report)
                if report["status"] != "passed":
                    raise FactoryError("Dummy source QC failed")
        elif name == "audio_master":
            tracks = self._timeline()["tracks"]
            reports = [read_json(self.dirs["audio_qc"] / f"{t['asset_id']}.json") for t in tracks]
            report = master_audio(
                [safe_path(self.root, t["path"]) for t in tracks],
                reports,
                directory / "master.wav",
                cfg.duration_seconds,
                self._timeline()["crossfade_seconds"],
            )
            write_json(directory / "master-qc.json", report)
        elif name == "provenance_gate":
            rights = self.music_provider.get_rights_evidence()
            if rights["status"] != "blocked" or rights.get("intended_for_testing_only") is not True:
                raise FactoryError("Phase 1 requires blocked test-only rights")
            write_json(
                directory / "rights.json",
                {
                    "schema_version": "1.0.0",
                    **rights,
                    "decision": "local_test_only",
                    "upload_eligible": False,
                },
            )
        elif name == "visual_generate":
            self._generate("image", directory / "background.png")
            with Image.open(directory / "background.png") as image:
                image.save(directory / "thumbnail.jpg", quality=92)
            validate_thumbnail(directory / "thumbnail.jpg")
        elif name == "render":
            report = render(
                self.dirs["audio_master"] / "master.wav",
                self.dirs["visual_generate"] / "background.png",
                directory / "final.mp4",
                cfg.duration_seconds,
                inject_failure=inject_failure,
            )
            write_json(directory / "video-qc.json", report)
        elif name == "metadata":
            concept = read_json(self.dirs["concept"] / "concept.json")
            chapters = [
                {
                    "start_seconds": t["start_seconds"],
                    "timestamp": stamp(t["start_seconds"]),
                    "title": concept["track_names"][i],
                }
                for i, t in enumerate(self._timeline()["tracks"])
            ]
            note = "Locally synthesized test audio and procedural graphics. Not for publication."
            metadata = {
                "schema_version": "1.0.0",
                "title": "Night Work — Instrumental Pipeline Test",
                "description": note
                + "\n\n"
                + "\n".join(f"{c['timestamp']} {c['title']}" for c in chapters),
                "tags": ["instrumental", "pipeline test"],
                "category_id": "10",
                "default_language": "en",
                "privacy_status": "private",
                "contains_synthetic_media": True,
                "made_for_kids": False,
                "chapters": chapters,
                "disclosure_note": note,
                "intended_for_testing_only": True,
                "creative_distinctiveness": {
                    "concept_id": concept["concept_id"],
                    "novelty_anchors": concept["novelty_anchors"],
                    "similarity_score": None,
                    "evaluation_status": "not_evaluated_test_fixture",
                },
            }
            validate("metadata", metadata)
            write_json(directory / "metadata.json", metadata)
        elif name == "package_validate":
            self._package(directory)

    def _timeline(self):
        return read_json(self.dirs["music_generate"] / "timeline.json")

    def _package(self, directory):
        verify_artifacts(self.root, self.manifest["artifacts"])
        assets = []
        for stage in ("concept", "music_generate", "visual_generate"):
            for response in sorted(self.dirs[stage].glob("*.response.json")):
                asset = read_json(response)
                if digest(safe_path(self.root, asset["source_path"])) != asset["source_sha256"]:
                    raise FactoryError("Source hash differs from provider response")
                asset["raw_response_sha256"] = digest(response)
                asset["qc_report_path"] = (
                    str(
                        (self.dirs["audio_qc"] / f"{asset['asset_id']}.json").relative_to(self.root)
                    )
                    if asset["kind"] == "audio"
                    else None
                )
                assets.append(asset)
        sources = [
            (self.dirs["render"] / "final.mp4", "final.mp4"),
            (self.dirs["visual_generate"] / "thumbnail.jpg", "thumbnail.jpg"),
            (self.dirs["metadata"] / "metadata.json", "metadata.json"),
        ]
        metadata = read_json(sources[2][0])
        chapters = metadata["chapters"]
        starts = [c["start_seconds"] for c in chapters]
        if starts != [t["start_seconds"] for t in self._timeline()["tracks"]] or starts[0] != 0:
            raise FactoryError("Chapter timeline mismatch")
        if (
            not all(a < b for a, b in zip(starts, starts[1:]))
            or starts[-1] >= self.config.duration_seconds
        ):
            raise FactoryError("Chapter bounds mismatch")
        tool_version = command(["ffmpeg", "-version"]).stdout.splitlines()[0]
        provenance = {
            "schema_version": "1.0.0",
            "run_id": self.manifest["run_id"],
            "created_at": now(),
            "code": read_json(self.dirs["initialize"] / "code.json"),
            "inputs": {
                "config_hash": self.manifest["config_hash"],
                "concept_hash": digest(self.dirs["concept"] / "concept.json"),
                "prompt_template_versions": {k: "1.0.0" for k in PROMPTS},
            },
            "assets": assets,
            "rights": read_json(self.dirs["provenance_gate"] / "rights.json"),
            "transforms": [
                {
                    "tool": "ffmpeg",
                    "version": tool_version,
                    "operation": "normalize_crossfade",
                    "input_sha256": [a["source_sha256"] for a in assets if a["kind"] == "audio"],
                    "output_sha256": digest(self.dirs["audio_master"] / "master.wav"),
                    "parameters": read_json(self.dirs["audio_master"] / "master-qc.json"),
                },
                {
                    "tool": "ffmpeg",
                    "version": tool_version,
                    "operation": "static_video_render",
                    "input_sha256": [
                        digest(self.dirs["audio_master"] / "master.wav"),
                        digest(self.dirs["visual_generate"] / "background.png"),
                    ],
                    "output_sha256": digest(sources[0][0]),
                    "parameters": {
                        "fps": 1,
                        "audio_bitrate": "96k",
                        "duration_seconds": self.config.duration_seconds,
                    },
                },
                {
                    "tool": "Pillow",
                    "version": Image.__version__,
                    "operation": "jpeg_thumbnail",
                    "input_sha256": [digest(self.dirs["visual_generate"] / "background.png")],
                    "output_sha256": digest(sources[1][0]),
                    "parameters": {"quality": 92},
                },
            ],
            "final_artifacts": [{"path": dest, "sha256": digest(src)} for src, dest in sources],
        }
        validate("provenance", provenance)
        scan_secrets(provenance)
        write_json(directory / "provenance.json", provenance)
        # Root files are immutable aliases; retries never overwrite completed files.
        for src, dest in sources + [(directory / "provenance.json", "provenance.json")]:
            target = self.root / dest
            if target.exists():
                if dest == "provenance.json":
                    old = read_json(target)
                    candidate = dict(provenance, created_at=old["created_at"])
                    if old != candidate:
                        raise FactoryError("Existing provenance differs; preserving run")
                    shutil.copyfile(target, directory / "provenance.json")
                elif digest(target) != digest(src):
                    raise FactoryError("Completed root artifact differs; preserving run")
            else:
                os.link(src, target)
        for name in ("metadata", "provenance"):
            validate(name, read_json(self.root / f"{name}.json"))
        for p in self.root.rglob("*.json"):
            scan_secrets(read_json(p))
        write_json(
            directory / "package-qc.json",
            {
                "schema_version": "1.0.0",
                "status": "passed",
                "scope": "local_test_only",
                "human_review": "pending",
                "production_qc": "not_implemented",
                "upload_eligible": False,
                "audio": read_json(self.dirs["audio_master"] / "master-qc.json"),
                "video": read_json(self.dirs["render"] / "video-qc.json"),
            },
        )


def resume_config(config, run_id):
    validate_run_id(run_id)
    path = config.data_dir / "runs" / run_id / "manifest.json"
    if not path.is_file():
        raise FactoryError("Cannot resume missing run")
    original = read_json(path)["config"]
    return replace(
        config,
        seed=original["seed"],
        duration_seconds=original["duration_seconds"],
        timezone=original["timezone"],
        min_track_count=original.get("min_track_count", 8),
        crossfade_seconds=original.get("crossfade_seconds", 2.0),
    )
