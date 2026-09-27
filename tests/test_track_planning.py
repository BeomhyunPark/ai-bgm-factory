from dataclasses import replace

import pytest

from ai_bgm_factory.cli import main
from ai_bgm_factory.config import Config, FactoryError, load_config
from ai_bgm_factory.pipeline import Pipeline, resume_config
from ai_bgm_factory.providers import DummyProvider
from ai_bgm_factory.track_planning import plan_tracks
from ai_bgm_factory.util import digest, read_json


class BoundedMusic(DummyProvider):
    """Offline fixture with a shorter source limit, without a real provider name."""

    def __init__(self, limit=8):
        self.limit = limit
        self.requests = []

    def capabilities(self):
        return {**super().capabilities(), "max_duration_seconds": self.limit}

    def generate(self, request, output):
        assert request.kind == "audio"
        assert request.duration_seconds <= self.limit
        self.requests.append(request)
        return super().generate(request, output)


class TextImage(DummyProvider):
    def __init__(self):
        self.kinds = []

    def generate(self, request, output):
        assert request.kind in ("text", "image")
        self.kinds.append(request.kind)
        return super().generate(request, output)


@pytest.mark.parametrize("limit,count", [(1000, 8), (380, 10), (330, 11), (310, 12)])
def test_hour_plan_covers_exactly_and_respects_limit(limit, count):
    plan = plan_tracks(3600, limit)
    tracks, fade = plan["tracks"], plan["crossfade_frames"]
    assert len(tracks) == count
    assert sum(t["frames"] for t in tracks) - fade * (count - 1) == 3600 * 48000
    assert tracks[-1]["start_frame"] + tracks[-1]["frames"] == 3600 * 48000
    assert max(t["frames"] for t in tracks) <= limit * 48000
    assert max(t["frames"] for t in tracks) - min(t["frames"] for t in tracks) <= 1
    assert all(b["start_frame"] == a["start_frame"] + a["frames"] - fade
               for a, b in zip(tracks, tracks[1:]))


def test_exact_cap_boundary_and_fractional_frames():
    assert len(plan_tracks(60, 9.25)["tracks"]) == 8
    assert len(plan_tracks(60, 9.25 - 1 / 48000)["tracks"]) == 9
    plan = plan_tracks(3600, 380, crossfade_seconds=5)
    assert len(plan["tracks"]) == 10
    assert {t["frames"] / 48000 for t in plan["tracks"]} == {364.5}


@pytest.mark.parametrize("kwargs", [
    {"max_duration_seconds": 290}, {"max_duration_seconds": None},
    {"max_duration_seconds": float("nan")}, {"max_duration_seconds": True},
    {"min_tracks": 7}, {"min_tracks": 13}, {"min_tracks": 8.5},
    {"crossfade_seconds": 0}, {"crossfade_seconds": 500},
    {"crossfade_seconds": 0.000001}, {"min_duration_seconds": 1001},
])
def test_invalid_or_impossible_plans_fail(kwargs):
    args = {"max_duration_seconds": 1000, **kwargs}
    with pytest.raises(FactoryError):
        plan_tracks(3600, **args)


def test_provider_separation_resume_and_actual_timeline(tmp_path):
    cfg = Config(tmp_path / "data", duration_seconds=60, crossfade_seconds=1)
    music, other = BoundedMusic(7), TextImage()
    with pytest.raises(FactoryError, match="Injected render"):
        Pipeline(cfg, other, music_provider=music).execute(run_id="split", fail_stage="render")
    root = cfg.data_dir / "runs/split"
    assert other.kinds == ["text", "image"]
    assert len(music.requests) == 10
    assert {r.slot for r in music.requests} == set(range(10))
    failed = read_json(root / "manifest.json")
    plan = failed["config"]["track_plan"]
    source_hashes = {a["path"]: a["sha256"] for a in failed["artifacts"]}
    with pytest.raises(FactoryError, match="Config changed"):
        Pipeline(cfg, TextImage(), music_provider=BoundedMusic(8)).execute(
            run_id="split", resume=True)
    with pytest.raises(FactoryError, match="Config changed"):
        Pipeline(cfg, TextImage()).execute(run_id="split", resume=True)
    fresh = BoundedMusic(7)
    Pipeline(cfg, TextImage(), music_provider=fresh).execute(run_id="split", resume=True)
    assert fresh.requests == []
    assert all(digest(root / path) == sha for path, sha in source_hashes.items())
    metadata = read_json(root / "metadata.json")
    provenance = read_json(root / "provenance.json")
    assert len(metadata["chapters"]) == 10
    assert len({c["title"] for c in metadata["chapters"]}) == 10
    assert [c["start_seconds"] for c in metadata["chapters"]] == [
        round(t["start_frame"] / 48000, 6) for t in plan["tracks"]]
    assert provenance["transforms"][0]["parameters"]["crossfade_seconds"] == 1
    assert len([a for a in provenance["assets"] if a["kind"] == "audio"]) == 10
    before = (root / "manifest.json").read_bytes()
    Pipeline(cfg, TextImage(), music_provider=BoundedMusic(7)).execute(run_id="split", resume=True)
    assert (root / "manifest.json").read_bytes() == before


def test_invalid_provider_rejected_before_creating_run(tmp_path):
    cfg = Config(tmp_path / "data")
    music = BoundedMusic(200)
    with pytest.raises(FactoryError, match="Cannot cover"):
        Pipeline(cfg, music_provider=music).execute(run_id="invalid")
    assert not cfg.data_dir.exists()
    assert music.requests == []


@pytest.mark.parametrize("role", ["music", "text_image"])
def test_network_or_real_assets_do_not_enter_dummy_gate(tmp_path, role):
    class Unsafe(DummyProvider):
        def get_rights_evidence(self):
            return {**super().get_rights_evidence(), "intended_for_testing_only": False}

    unsafe = Unsafe()
    kwargs = {"music_provider" if role == "music" else "provider": unsafe}
    with pytest.raises(FactoryError, match="offline test-only"):
        Pipeline(Config(tmp_path / "data"), **kwargs).execute()
    assert not (tmp_path / "data").exists()


def test_config_and_cli_minimum_restore_on_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("MIN_TRACK_COUNT", "12")
    monkeypatch.setenv("CROSSFADE_SECONDS", "1")
    cfg = load_config(data_dir=tmp_path / "data", duration_minutes=1)
    assert cfg.min_track_count == 12 and cfg.crossfade_seconds == 1
    assert main(["generate", "--duration-minutes", "1", "--min-tracks", "12",
                 "--run-id", "twelve", "--data-dir", str(cfg.data_dir)]) == 0
    metadata = read_json(cfg.data_dir / "runs/twelve/metadata.json")
    assert len(metadata["chapters"]) == 12
    restored = resume_config(replace(cfg, min_track_count=8, crossfade_seconds=2), "twelve")
    assert restored.min_track_count == 12 and restored.crossfade_seconds == 1
    assert main(["generate", "--resume", "--run-id", "twelve", "--min-tracks", "8",
                 "--data-dir", str(cfg.data_dir)]) == 1
    monkeypatch.setenv("MIN_TRACK_COUNT", "8")
    monkeypatch.setenv("CROSSFADE_SECONDS", "2")
    assert main(["generate", "--resume", "--run-id", "twelve",
                 "--data-dir", str(cfg.data_dir)]) == 0
