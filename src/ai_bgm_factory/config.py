import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class FactoryError(Exception):
    """Messages contain static, non-sensitive diagnostics only."""


def read_env(path: Path) -> dict[str, str]:
    result = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if not sep or not key.strip().isidentifier():
                raise FactoryError("Invalid .env syntax; use KEY=value without shell expansion")
            result[key.strip()] = value.strip().strip("\"'")
    result.update(os.environ)
    return result


@dataclass(frozen=True)
class Config:
    data_dir: Path
    duration_seconds: float = 3600.0
    seed: int = 42
    timezone: str = "Asia/Seoul"
    min_track_count: int = 8
    crossfade_seconds: float = 2.0
    sample_rate: int = 48000
    width: int = 1280
    height: int = 720
    fps: int = 1

    def __post_init__(self):
        if not math.isfinite(self.duration_seconds) or not 60 <= self.duration_seconds <= 7200:
            raise FactoryError("Duration must be finite and between 1 and 120 minutes")
        if self.duration_seconds != round(self.duration_seconds):
            raise FactoryError("Duration must resolve to whole seconds for the 1 fps test profile")
        if not 0 <= self.seed <= 2**32 - 1:
            raise FactoryError("Seed must be an unsigned 32-bit integer")
        if type(self.min_track_count) is not int or not 8 <= self.min_track_count <= 12:
            raise FactoryError("Minimum track count must be between 8 and 12")
        if (type(self.crossfade_seconds) not in (int, float)
                or not math.isfinite(self.crossfade_seconds) or self.crossfade_seconds <= 0):
            raise FactoryError("Crossfade must be positive and finite")
        if self.sample_rate != 48000 or self.fps != 1:
            raise FactoryError("Phase 1 media settings are fixed")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise FactoryError("Invalid TIMEZONE") from None

    def snapshot(self):
        return {
            "schema_version": "1.1.0",
            **{k: v for k, v in asdict(self).items() if k != "data_dir"},
            "provider": "dummy",
            "privacy_status": "private",
            "intended_for_testing_only": True,
            "human_approval_required": True,
        }


def load_config(*, duration_minutes=None, seed=42, data_dir=None, min_tracks=None) -> Config:
    env = read_env(Path(".env"))
    for name in (
        "ENABLE_MUSIC_API",
        "ENABLE_IMAGE_API",
        "ENABLE_YOUTUBE_UPLOAD",
        "ENABLE_SCHEDULER",
        "ENABLE_ANALYTICS_SYNC",
    ):
        if env.get(name, "false").lower() != "false":
            raise FactoryError(f"{name} must be false in Phase 1")
    if env.get("DEFAULT_PRIVACY_STATUS", "private") != "private":
        raise FactoryError("DEFAULT_PRIVACY_STATUS must be private")
    if env.get("HUMAN_APPROVAL_REQUIRED", "true").lower() != "true":
        raise FactoryError("HUMAN_APPROVAL_REQUIRED must be true")
    for name in ("TEXT_PROVIDER", "MUSIC_PROVIDER", "IMAGE_PROVIDER"):
        if env.get(name, "dummy") != "dummy":
            raise FactoryError(f"{name} must be dummy in Phase 1")
    if env.get("APP_ENV", "development") not in ("development", "test", "production"):
        raise FactoryError("Invalid APP_ENV")
    try:
        minutes = float(
            duration_minutes
            if duration_minutes is not None
            else env.get("DEFAULT_DURATION_MINUTES", "60")
        )
        count = int(env.get("MIN_TRACK_COUNT", "8")) if min_tracks is None else min_tracks
        crossfade = float(env.get("CROSSFADE_SECONDS", "2"))
    except (ValueError, TypeError):
        raise FactoryError("Invalid duration") from None
    return Config(
        Path(data_dir or env.get("DATA_DIR", "./data")).resolve(),
        minutes * 60,
        seed,
        env.get("TIMEZONE", "Asia/Seoul"),
        min_track_count=count,
        crossfade_seconds=crossfade,
    )
