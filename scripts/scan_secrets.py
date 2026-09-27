"""Offline source scanner; package JSON uses the stricter runtime field scanner."""

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(r"(?m)^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----$"),
    re.compile(r"(?i)[?&](?:X-Amz-Signature|X-Goog-Signature)=[a-z0-9]{32,}"),
    re.compile(r"(?m)^\s*(?:OPENAI_API_KEY|MUSIC_API_KEY|IMAGE_API_KEY)=\S{16,}"),
    re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"https?://[^\s/:@]+:[^\s/@]+@"),
]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--staged", action="store_true", help="Scan every staged Git blob")
args = parser.parse_args()
failures = []
if args.staged:
    names = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z"], cwd=ROOT
    ).decode().split("\0")
    for name in filter(None, names):
        blob = subprocess.check_output(["git", "show", f":{name}"], cwd=ROOT)
        try:
            content = blob.decode("utf-8")
        except UnicodeDecodeError:
            failures.append(name + " (non-text file requires review)")
            continue
        if any(pattern.search(content) for pattern in PATTERNS):
            failures.append(name)
for path in (() if args.staged else ROOT.rglob("*")):
    if any(
        part in {".git", ".venv", "data", "__pycache__", ".pytest_cache", ".ruff_cache"}
        for part in path.relative_to(ROOT).parts
    ):
        continue
    if path.is_file() and path.suffix in {".py", ".md", ".json", ".toml", ".sql"}:
        if any(p.search(path.read_text()) for p in PATTERNS):
            failures.append(str(path.relative_to(ROOT)))
if failures:
    print("Secret-pattern review required in: " + ", ".join(failures))
    raise SystemExit(1)
print("Staged secret scan passed" if args.staged else "Source secret scan passed")
