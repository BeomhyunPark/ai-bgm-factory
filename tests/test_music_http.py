import io
import json
import sqlite3
import wave
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ai_bgm_factory.config import FactoryError
from ai_bgm_factory.music_http import (
    MODEL,
    RESULT_PATH,
    SUBMIT_PATH,
    FixtureTransport,
    HttpResponse,
    StableAudioFixtureAdapter,
    retry_after,
)
from ai_bgm_factory.music_jobs import JobLimits, MusicJobRunner
from ai_bgm_factory.providers import PROMPTS, GenerationRequest
from ai_bgm_factory.util import scan_secrets

FIXTURE = json.loads((Path(__file__).parent / "fixtures/music_jobs/http.json").read_text())
JOB_ID = "a" * 64
REQUEST = GenerationRequest("audio", 42, PROMPTS["audio"], 10)


def response(name):
    item = FIXTURE[name]
    return HttpResponse(item["status"], item["headers"], json.dumps(item["body"]).encode())


def audio():
    data = io.BytesIO()
    with wave.open(data, "wb") as wav:
        wav.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x00" * 400)
    return HttpResponse(200, {"Content-Type": "audio/wav"}, data.getvalue())


class Clock:
    value = 0

    def __init__(self):
        self.delays = []

    def monotonic(self):
        return self.value

    def timestamp(self):
        return (
            datetime(2026, 9, 28, tzinfo=timezone.utc) + timedelta(seconds=self.value)
        ).isoformat()

    def sleep(self, seconds):
        self.delays.append(seconds)
        self.value += seconds


def setup(root, replies, clock=None, limits=None, **kwargs):
    clock = clock or Clock()
    transport = FixtureTransport(replies)
    adapter = StableAudioFixtureAdapter(
        transport, root / "evidence", timestamp=clock.timestamp, **kwargs
    )
    runner = MusicJobRunner(
        root / "ledger",
        adapter,
        limits or JobLimits(100, 100, 5),
        clock=clock.monotonic,
        sleep=clock.sleep,
        jitter=lambda: 0,
        timestamp=clock.timestamp,
    )
    return transport, adapter, runner


def execute(runner):
    return runner.execute("run", 0, REQUEST, reserve_cents=26)


def test_http_lifecycle_and_allowlisted_evidence(tmp_path):
    transport, _, runner = setup(
        tmp_path, [response("accepted"), response("rate_limited"), response("pending"), audio()]
    )
    receipt = execute(runner)
    assert receipt["status"] == "succeeded" and receipt["rights_status"] == "blocked"
    assert [c["method"] for c in transport.calls] == ["POST", "GET", "GET", "GET"]
    assert transport.calls[0]["path"] == SUBMIT_PATH
    assert transport.calls[0]["form"]["model"] == MODEL
    assert all(c["path"] == RESULT_PATH + JOB_ID for c in transport.calls[1:])
    assert all(c["timeout_seconds"] == 10 for c in transport.calls)
    evidence = [json.loads(p.read_text()) for p in (tmp_path / "evidence").glob("*.json")]
    assert len(evidence) == 4
    assert all(e["response_sha256"] and e["body_retained"] is False for e in evidence)
    assert {e["correlation_id"] for e in evidence} == {receipt["request_id"], JOB_ID}
    assert runner.sleep.__self__.delays[0] == 3


def test_retry_after_survives_reopen_and_never_shortens_cooldown(tmp_path):
    clock = Clock()
    limits = JobLimits(100, 100, 5, timeout_seconds=2)
    transport, _, runner = setup(
        tmp_path, [response("accepted"), response("rate_limited")], clock, limits
    )
    with pytest.raises(FactoryError, match="Polling limit"):
        execute(runner)
    assert len(transport.calls) == 2 and clock.delays == []
    fresh, _, reopened = setup(tmp_path, [audio()], clock, limits)
    with pytest.raises(FactoryError, match="window"):
        execute(reopened)
    assert fresh.calls == []
    clock.value = 3
    assert execute(reopened)["status"] == "succeeded"
    assert [c["method"] for c in fresh.calls] == ["GET"]


@pytest.mark.parametrize(
    "submit_result",
    [
        TimeoutError("private diagnostic"),
        response("rejected"),
        HttpResponse(202, {}, b'{"id":"../bad"}'),
        HttpResponse(202, {}, b"not json"),
    ],
)
def test_submission_uncertain_never_reposts(tmp_path, submit_result):
    transport, _, runner = setup(tmp_path, [submit_result])
    with pytest.raises(FactoryError, match="unknown") as error:
        execute(runner)
    assert "private diagnostic" not in str(error.value)
    with pytest.raises(FactoryError, match="reconciliation"):
        execute(runner)
    assert len(transport.calls) == 1


def test_poll_timeout_and_server_error_are_safe_to_retry(tmp_path):
    transport, _, runner = setup(
        tmp_path,
        [response("accepted"), TimeoutError("private detail"), response("unavailable"), audio()],
    )
    assert execute(runner)["status"] == "succeeded"
    assert [c["method"] for c in transport.calls].count("POST") == 1
    assert "private detail" not in "".join(p.read_text() for p in (tmp_path / "evidence").glob("*"))


@pytest.mark.parametrize(
    "result",
    [
        response("rejected"),
        HttpResponse(200, {}, b"bad audio"),
        HttpResponse(302, {"Location": "https://example.invalid"}, b""),
    ],
)
def test_bad_audio_permanent_error_and_redirect_do_not_succeed(tmp_path, result):
    transport, _, runner = setup(tmp_path, [response("accepted"), result])
    with pytest.raises(FactoryError):
        execute(runner)
    assert len(transport.calls) == 2


def test_arbitrary_response_text_and_headers_are_not_saved(tmp_path):
    # Synthetic canary strings only; no credentials are used in this test.
    marker = "private-fixture-canary"
    payload = {
        "id": JOB_ID,
        "debug": {"contact": marker, "url": "https://example.invalid/" + marker},
    }
    accepted = HttpResponse(
        202, {"X-Debug": marker, "Set-Cookie": marker}, json.dumps(payload).encode()
    )
    _, _, runner = setup(tmp_path, [accepted, audio()])
    execute(runner)
    for path in (tmp_path / "evidence").glob("*.json"):
        assert marker not in path.read_text()
        scan_secrets(json.loads(path.read_text()))


@pytest.mark.parametrize(
    "value,expected",
    [
        ("12", 12),
        ("Mon, 28 Sep 2026 00:00:05 GMT", 5),
        ("Sun, 27 Sep 2026 00:00:00 GMT", 0),
        ("-1", None),
        ("1.5", None),
        ("nan", None),
        (None, None),
        ("x" * 129, None),
    ],
)
def test_retry_after_forms(value, expected):
    assert retry_after(value, timestamp="2026-09-28T00:00:00+00:00") == expected


@pytest.mark.parametrize("seed", [0, 4294967295])
def test_api_seed_semantics_not_silently_changed(tmp_path, seed):
    transport, adapter, _ = setup(tmp_path, [])
    with pytest.raises(FactoryError, match="nonzero"):
        adapter.submit("b" * 64, replace(REQUEST, seed=seed))
    assert transport.calls == []


def test_size_limit_is_forwarded_and_checked(tmp_path):
    transport, _, runner = setup(
        tmp_path, [HttpResponse(202, {}, b"x" * 101)], max_response_bytes=100
    )
    with pytest.raises(FactoryError):
        execute(runner)
    assert transport.calls[0]["max_response_bytes"] == 100
    assert not list((tmp_path / "evidence").glob("*.json"))


def test_live_transport_rejected(tmp_path):
    transport = FixtureTransport([])
    transport.network_required = True
    with pytest.raises(FactoryError, match="disabled"):
        StableAudioFixtureAdapter(transport, tmp_path)


def test_v1_ledger_migrates_without_losing_completed_job(tmp_path):
    _, _, runner = setup(tmp_path, [response("accepted"), audio()])
    receipt = execute(runner)
    with sqlite3.connect(tmp_path / "ledger/jobs.db") as db:
        db.execute("ALTER TABLE jobs DROP COLUMN not_before")
        db.execute("PRAGMA user_version=1")
    transport, _, reopened = setup(tmp_path, [])
    assert execute(reopened) == receipt
    assert transport.calls == []
    with sqlite3.connect(tmp_path / "ledger/jobs.db") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
