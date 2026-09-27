import argparse
import json
import os
import shutil
import sys

from .config import FactoryError, load_config
from .pipeline import Pipeline, resume_config
from .schemas import validate
from .util import command, read_json, validate_run_id, verify_artifacts


def doctor(config):
    parent = config.data_dir
    while not parent.exists():
        parent = parent.parent
    encoders = command(["ffmpeg", "-hide_banner", "-encoders"]).stdout
    filters = command(["ffmpeg", "-hide_banner", "-filters"]).stdout
    checks = {
        "python_3_12_plus": sys.version_info >= (3, 12),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
        "libx264": "libx264" in encoders,
        "aac": " aac " in encoders,
        "loudnorm": "loudnorm" in filters,
        "acrossfade": "acrossfade" in filters,
        "data_parent_writable": os.access(parent, os.W_OK),
        "disk_space": shutil.disk_usage(parent).free
        >= max(500_000_000, int(config.duration_seconds * 800_000)),
        "credentials_required": False,
        "external_services_enabled": False,
    }
    required = [
        v
        for k, v in checks.items()
        if k not in ("credentials_required", "external_services_enabled")
    ]
    return {
        "schema_version": "1.0.0",
        "status": "passed" if all(required) else "failed",
        "checks": checks,
        "media_profile": "1280x720, 1 fps static test card; H.264/AAC",
    }


def parser():
    root = argparse.ArgumentParser(description="AI BGM Factory — offline Phase 1 test pipeline")
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("doctor", "generate", "inspect"):
        p = sub.add_parser(name)
        p.add_argument("--data-dir", help="Runtime data root (default DATA_DIR or ./data)")
        if name == "generate":
            p.add_argument("--seed", type=int, default=None)
            p.add_argument("--duration-minutes", type=float, default=None)
            p.add_argument("--run-id")
            p.add_argument("--resume", action="store_true")
            p.add_argument("--fail-stage", choices=["render"], help="Test-only failure injection")
        if name == "inspect":
            p.add_argument("run_id")
    p = sub.add_parser("upload", help="Reserved for Phase 7; disabled")
    p.add_argument("run_id")
    p.add_argument("--privacy", choices=["private"], default="private")
    p = sub.add_parser("schedule", help="Reserved for Phase 8; disabled")
    p.add_argument("run_id")
    p.add_argument("--publish-at", required=True)
    for name, action in (("analytics", "sync"), ("feedback", "build")):
        sub.add_parser(name, help="Reserved for Phase 9; disabled").add_argument(
            "action", choices=[action]
        )
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command in ("upload", "schedule", "analytics", "feedback"):
            raise FactoryError(
                "Command is not implemented in Phase 1; no external action performed"
            )
        config = load_config(
            duration_minutes=getattr(args, "duration_minutes", None),
            seed=args.seed if getattr(args, "seed", None) is not None else 42,
            data_dir=args.data_dir,
        )
        if args.command == "doctor":
            result = doctor(config)
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "passed" else 1
        if args.command == "inspect":
            validate_run_id(args.run_id)
            root = config.data_dir / "runs" / args.run_id
            result = read_json(root / "manifest.json")
            validate("manifest", result)
            verify_artifacts(root, result["artifacts"])
        else:
            if args.resume:
                if not args.run_id:
                    raise FactoryError("--resume requires --run-id")
                stored = resume_config(config, args.run_id)
                if args.seed is not None and args.seed != stored.seed:
                    raise FactoryError("Resume seed differs from original run")
                if (
                    args.duration_minutes is not None
                    and args.duration_minutes * 60 != stored.duration_seconds
                ):
                    raise FactoryError("Resume duration differs from original run")
                config = stored
            if doctor(config)["status"] != "passed":
                raise FactoryError("Doctor failed; run doctor to inspect dependency/disk checks")
            result = Pipeline(config).execute(
                run_id=args.run_id, resume=args.resume, fail_stage=args.fail_stage
            )
        print(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "run_id": result["run_id"],
                    "status": result["status"],
                    "publication": result["publication"],
                    "output": str(config.data_dir / "runs" / result["run_id"]),
                }
            )
        )
        return 0
    except FactoryError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError):
        print(
            json.dumps({"error": "Invalid or unavailable local data; inspect configuration/run"}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
