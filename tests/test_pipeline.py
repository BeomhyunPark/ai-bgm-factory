import json

import pytest

from ai_bgm_factory.cli import main
from ai_bgm_factory.config import Config, FactoryError
from ai_bgm_factory.media import validate_video
from ai_bgm_factory.pipeline import Pipeline
from ai_bgm_factory.schemas import validate
from ai_bgm_factory.util import digest, read_json, verify_artifacts


def check_package(root, duration):
    manifest = read_json(root / "manifest.json")
    validate("manifest", manifest)
    assert manifest["status"] == "ready_for_review"
    assert all(s["status"] == "succeeded" for s in manifest["stages"])
    assert len(manifest["stages"]) == 10
    for name in ("manifest.json", "metadata.json", "provenance.json", "final.mp4", "thumbnail.jpg"):
        assert (root / name).stat().st_size > 0
    verify_artifacts(root, manifest["artifacts"])
    metadata = read_json(root / "metadata.json")
    provenance = read_json(root / "provenance.json")
    validate("metadata", metadata)
    validate("provenance", provenance)
    assert metadata["chapters"][0]["timestamp"] == "00:00"
    assert metadata["privacy_status"] == "private"
    assert provenance["rights"]["status"] == "blocked"
    assert len([a for a in provenance["assets"] if a["kind"] == "audio"]) == 8
    for a in provenance["assets"]:
        assert digest(root / a["source_path"]) == a["source_sha256"]
        assert digest(root / a["raw_response_path"]) == a["raw_response_sha256"]
    report = validate_video(root / "final.mp4", duration, full_decode=False)
    assert report["av_delta_seconds"] <= 0.1
    return manifest


def test_e2e_failure_resume_immutability_and_reproducibility(tmp_path):
    cfg = Config(tmp_path / "data", duration_seconds=60)
    with pytest.raises(FactoryError, match="Injected render"):
        Pipeline(cfg).execute(run_id="interrupted", fail_stage="render")
    root = cfg.data_dir / "runs" / "interrupted"
    failed = read_json(root / "manifest.json")
    assert failed["status"] == "failed" and failed["error"]["stage"] == "render"
    assert not (root / "final.mp4").exists()
    assert list(root.rglob("final.partial.mp4"))
    successful_inputs = {a["path"]: a["sha256"] for a in failed["artifacts"]}
    resumed = Pipeline(cfg).execute(run_id="interrupted", resume=True)
    check_package(root, 60)
    for name, original_hash in successful_inputs.items():
        assert digest(root / name) == original_hash
    assert next(s for s in resumed["stages"] if s["name"] == "render")["attempt"] == 2
    before = (root / "manifest.json").read_bytes()
    Pipeline(cfg).execute(run_id="interrupted", resume=True)
    assert (root / "manifest.json").read_bytes() == before
    with pytest.raises(FactoryError, match="already exists"):
        Pipeline(cfg).execute(run_id="interrupted")
    second = Pipeline(cfg).execute()
    other = cfg.data_dir / "runs" / second["run_id"]
    check_package(other, 60)
    assert (other / "metadata.json").read_bytes() == (root / "metadata.json").read_bytes()
    assert main(["inspect", "interrupted", "--data-dir", str(cfg.data_dir)]) == 0
    assert (
        main(
            [
                "generate",
                "--resume",
                "--run-id",
                "interrupted",
                "--seed",
                "43",
                "--data-dir",
                str(cfg.data_dir),
            ]
        )
        == 1
    )
    (root / "metadata.json").write_text("tampered")
    with pytest.raises(FactoryError, match="mismatch"):
        Pipeline(cfg).execute(run_id="interrupted", resume=True)
    assert (root / "metadata.json").read_text() == "tampered"


@pytest.mark.smoke
def test_full_60_minute_default(tmp_path):
    cfg = Config(tmp_path / "data")
    assert main(["generate", "--data-dir", str(cfg.data_dir)]) == 0
    roots = list((cfg.data_dir / "runs").iterdir())
    assert len(roots) == 1
    root = roots[0]
    manifest = check_package(root, 3600)
    # Keep an evidence summary when the caller selects a persistent pytest base directory.
    (tmp_path / "acceptance.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "run_id": manifest["run_id"],
                "checks": "AC-001..010 covered with normal suite + smoke",
                "manifest_sha256": digest(root / "manifest.json"),
                "status": "passed",
            },
            indent=2,
        )
    )


def test_changed_source_cannot_become_ready(tmp_path):
    class TamperedPipeline(Pipeline):
        def _package(self, directory):
            source = next(self.dirs["music_generate"].glob("*.wav"))
            with source.open("r+b") as stream:
                stream.seek(100)
                stream.write(b"changed")
            super()._package(directory)

    cfg = Config(tmp_path / "data", duration_seconds=60)
    with pytest.raises(FactoryError, match="hash mismatch"):
        TamperedPipeline(cfg).execute(run_id="tampered-source")
    root = cfg.data_dir / "runs/tampered-source"
    assert read_json(root / "manifest.json")["status"] == "failed"
    assert not (root / "final.mp4").exists()
