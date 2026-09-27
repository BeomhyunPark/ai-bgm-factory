import json
import sqlite3
import wave
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ai_bgm_factory.cli import doctor, main
from ai_bgm_factory.config import Config, FactoryError, load_config
from ai_bgm_factory.media import audio_qc, measure_loudness
from ai_bgm_factory.providers import PROMPTS, DummyProvider, GenerationRequest
from ai_bgm_factory.schemas import validate, validator
from ai_bgm_factory.storage import Store, run_lock
from ai_bgm_factory.util import digest, safe_path, scan_secrets, validate_run_id


@pytest.mark.parametrize(
    "name,value",
    [
        ("ENABLE_MUSIC_API", "true"),
        ("ENABLE_IMAGE_API", "yes"),
        ("ENABLE_YOUTUBE_UPLOAD", "true"),
        ("ENABLE_SCHEDULER", "true"),
        ("ENABLE_ANALYTICS_SYNC", "true"),
        ("DEFAULT_PRIVACY_STATUS", "public"),
        ("HUMAN_APPROVAL_REQUIRED", "false"),
        ("MUSIC_PROVIDER", "unreviewed"),
        ("TIMEZONE", "bad-zone"),
        ("APP_ENV", "typo"),
    ],
)
def test_unsafe_config_blocked(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(FactoryError):
        load_config()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0, 0.5, 120.1, 1.001])
def test_invalid_duration(value):
    with pytest.raises(FactoryError):
        load_config(duration_minutes=value)


def test_env_precedence_and_secrets(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("DEFAULT_DURATION_MINUTES=2\nMUSIC_API_KEY=secret-placeholder\n")
    monkeypatch.setenv("DEFAULT_DURATION_MINUTES", "3")
    cfg = load_config()
    assert cfg.duration_seconds == 180
    assert "secret-placeholder" not in json.dumps(cfg.snapshot())
    assert cfg.snapshot()["privacy_status"] == "private"


def test_doctor_no_output_writes(tmp_path):
    cfg = Config(tmp_path / "not-created")
    assert doctor(cfg)["status"] == "passed"
    assert not cfg.data_dir.exists()


@pytest.mark.parametrize(
    "args",
    [
        ["upload", "example"],
        ["schedule", "example", "--publish-at", "2030-01-01T00:00:00Z"],
        ["analytics", "sync"],
        ["feedback", "build"],
    ],
)
def test_disabled_commands(args):
    assert main(args) == 1


def test_seed_zero(tmp_path):
    assert load_config(seed=0).seed == 0
    with pytest.raises(FactoryError):
        replace(Config(tmp_path), seed=-1)


@pytest.mark.parametrize("run_id", ["../escape", "/tmp/x", "", "a/b", "a;echo x"])
def test_run_traversal(run_id):
    with pytest.raises(FactoryError):
        validate_run_id(run_id)


def test_artifact_symlink_escape(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "escape").symlink_to(tmp_path)
    with pytest.raises(FactoryError):
        safe_path(root, "escape/file")


@pytest.mark.parametrize(
    "payload", [{"api_key": "placeholder"}, {"x": "Bearer abc"}, {"x": "?X-Amz-Signature=example"}]
)
def test_secret_scan(payload):
    with pytest.raises(FactoryError):
        scan_secrets(payload)


def test_provider_determinism_and_prompt_rejection(tmp_path):
    provider = DummyProvider()
    req = GenerationRequest("audio", 42, PROMPTS["audio"], 2)
    provider.generate(req, tmp_path / "a.wav")
    provider.generate(req, tmp_path / "b.wav")
    assert digest(tmp_path / "a.wav") == digest(tmp_path / "b.wav")
    provider.generate(replace(req, slot=1), tmp_path / "c.wav")
    assert digest(tmp_path / "a.wav") != digest(tmp_path / "c.wav")
    with pytest.raises(FactoryError):
        provider.generate(replace(req, prompt="imitate a famous artist"), tmp_path / "bad.wav")
    assert provider.get_rights_evidence()["status"] == "blocked"


@pytest.mark.parametrize("amplitude,expected", [(0, "unexpected_silence"), (32767, "clipping")])
def test_qc_rejects_invalid_audio(tmp_path, amplitude, expected):
    path = tmp_path / "fixture.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setparams((2, 2, 48000, 0, "NONE", "not compressed"))
        wav.writeframes(np.full((48000 * 4, 2), amplitude, dtype="<i2").tobytes())
    report = audio_qc(path, "fixture")
    assert report["status"] == "failed"
    assert expected in report["failures"]


def test_lock_and_migration(tmp_path):
    with run_lock(tmp_path), pytest.raises(FactoryError):
        with run_lock(tmp_path):
            pass
    for _ in range(2):
        Store(tmp_path).close()
    with sqlite3.connect(tmp_path / "app.db") as db:
        assert db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone() == (1,)


@pytest.mark.parametrize("name", ["manifest", "metadata", "provenance", "qc"])
def test_schemas_reject_empty(name):
    validator(name)
    with pytest.raises(FactoryError):
        validate(name, {})


def test_help_and_doc_links():
    repo = Path(__file__).resolve().parents[1]
    import re

    for path in [repo / "README.md", repo / "AGENTS.md", *(repo / "docs").rglob("*.md")]:
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" not in link and not link.startswith("#"):
                assert (path.parent / link.split("#")[0]).exists(), (path, link)


def test_loudness_json_with_trailing_ffmpeg_statistics(monkeypatch):
    measurements = dict(input_i="-14", input_tp="-7", input_lra="1",
                        input_thresh="-24", target_offset="0")
    stderr = "[Parsed_loudnorm_0]\n" + json.dumps(measurements, indent=2)
    stderr += "\n[out#0/null] video:0KiB audio:11250KiB\n"
    monkeypatch.setattr("ai_bgm_factory.media.command",
                        lambda args: SimpleNamespace(stderr=stderr))
    assert measure_loudness("unused.wav") == measurements


@pytest.mark.parametrize("payload", ["{\ninvalid}", "{\n}", '{\n"input_i": "-inf"}'])
def test_invalid_loudness_report_rejected(monkeypatch, payload):
    monkeypatch.setattr("ai_bgm_factory.media.command",
                        lambda args: SimpleNamespace(stderr=payload))
    with pytest.raises(FactoryError, match="invalid loudness"):
        measure_loudness("unused.wav")
