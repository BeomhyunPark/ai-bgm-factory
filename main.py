"""Source-checkout entry point; also supports installed `bgm`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from ai_bgm_factory.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
