import socket

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """All tests deny Python sockets/DNS, and ignore any caller .env file."""

    def denied(*args, **kwargs):
        raise AssertionError("Network access prohibited in tests")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.chdir(tmp_path)
    for name in (
        "ENABLE_MUSIC_API",
        "ENABLE_IMAGE_API",
        "ENABLE_YOUTUBE_UPLOAD",
        "ENABLE_SCHEDULER",
        "ENABLE_ANALYTICS_SYNC",
        "DEFAULT_PRIVACY_STATUS",
        "HUMAN_APPROVAL_REQUIRED",
        "TEXT_PROVIDER",
        "MUSIC_PROVIDER",
        "IMAGE_PROVIDER",
        "DEFAULT_DURATION_MINUTES",
        "TIMEZONE",
        "APP_ENV",
        "DATA_DIR",
        "MIN_TRACK_COUNT",
        "CROSSFADE_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)
