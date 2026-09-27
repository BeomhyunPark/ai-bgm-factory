import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import FactoryError

SCHEMA_VERSION = "1.0.0"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def object_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w") as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text())


def safe_path(root, relative):
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts:
        raise FactoryError("Unsafe artifact path")
    result = (Path(root) / p).resolve()
    if not result.is_relative_to(Path(root).resolve()):
        raise FactoryError("Artifact leaves run directory")
    return result


def validate_run_id(run_id):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", run_id):
        raise FactoryError("Invalid run ID")


def command(args, *, timeout=1800):
    try:
        result = subprocess.run(
            [str(x) for x in args], capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        raise FactoryError("Local media command unavailable or timed out") from None
    if result.returncode:
        # Never copy arbitrary subprocess stderr (paths or credentials) into logs.
        raise FactoryError(f"Local media command failed (exit {result.returncode})")
    return result


def probe(path):
    return json.loads(
        command(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]
        ).stdout
    )


def artifact(root, path, role="intermediate"):
    return {
        "role": role,
        "path": str(Path(path).relative_to(root)),
        "sha256": digest(path),
        "bytes": Path(path).stat().st_size,
    }


def verify_artifacts(root, items):
    for item in items:
        path = safe_path(root, item["path"])
        if not path.is_file() or path.stat().st_size != item["bytes"]:
            raise FactoryError("Missing artifact or size mismatch; preserving existing run")
        if digest(path) != item["sha256"]:
            raise FactoryError("Artifact hash mismatch; preserving existing run")


def scan_secrets(obj):
    """Reject credential fields and common key/token formats without echoing values."""
    bad_key = re.compile(
        r"^(authorization|api_key|access_token|refresh_token|client_secret|"
        r"signed_url|x-goog-signature)$",
        re.I,
    )
    bad_value = re.compile(
        r"(?:sk-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{30,}|"
        r"Bearer\s+\S+|-----BEGIN .*PRIVATE KEY-----|"
        r"[?&](?:token|X-Amz-Signature|X-Goog-Signature)=)",
        re.I,
    )

    def walk(value):
        if isinstance(value, dict):
            for key, v in value.items():
                if bad_key.match(key) and v:
                    raise FactoryError("Secret scan rejected a credential field")
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, str) and bad_value.search(value):
            raise FactoryError("Secret scan rejected a credential pattern")

    walk(obj)
