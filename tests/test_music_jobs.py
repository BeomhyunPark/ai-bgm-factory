import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from ai_bgm_factory.config import FactoryError
from ai_bgm_factory.music_jobs import (
    FakeMusicJobProvider,
    JobLimits,
    MusicJobRunner,
)
from ai_bgm_factory.providers import PROMPTS, GenerationRequest
from ai_bgm_factory.storage import run_lock

FIXTURES = json.loads((Path(__file__).parent / "fixtures/music_jobs/lifecycle.json").read_text())
REQUEST = GenerationRequest("audio", 42, PROMPTS["audio"], 2)
LIMITS = JobLimits(100, 200, 10)


class Clock:
    def __init__(self):
        self.value = 0
        self.delays = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.delays.append(seconds)
        self.value += seconds


def runner(root, provider, limits=LIMITS, clock=None, timestamp=None):
    clock = clock or Clock()
    return MusicJobRunner(
        root,
        provider,
        limits,
        clock=clock.now,
        sleep=clock.sleep,
        jitter=lambda: 0,
        timestamp=timestamp or (lambda: "2026-09-28T00:00:00+09:00"),
    )


def execute(instance, run="run", slot=0, reserve=26):
    return instance.execute(run, slot, replace(REQUEST, slot=slot), reserve_cents=reserve)


def rows(root, table):
    with sqlite3.connect(root / "jobs.db") as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute(f"SELECT * FROM {table}")]


def test_success_events_and_completed_reopen_do_not_submit(tmp_path):
    provider = FakeMusicJobProvider(FIXTURES["success"])
    result = execute(runner(tmp_path, provider))
    assert result["actual_cents"] == 26
    assert result["rights_status"] == "blocked"
    assert result["upload_eligible"] is False
    fresh = FakeMusicJobProvider()
    assert execute(runner(tmp_path, fresh)) == result
    assert (fresh.submissions, fresh.polls) == (0, 0)
    events = rows(tmp_path, "events")
    assert [e["status"] for e in events] == ["reserved", "queued", "queued", "running", "succeeded"]
    assert all(e["duration_ms"] >= 0 for e in events)


def test_transient_poll_backoff_is_bounded_and_does_not_resubmit(tmp_path):
    clock = Clock()
    provider = FakeMusicJobProvider(FIXTURES["transient"])
    execute(runner(tmp_path, provider, clock=clock))
    assert provider.submissions == 1
    assert clock.delays == [0.5, 1, 2]


def test_timeout_then_restart_polls_saved_job(tmp_path):
    provider = FakeMusicJobProvider(FIXTURES["pending"])
    clock = Clock()
    with pytest.raises(FactoryError, match="Polling limit"):
        execute(runner(tmp_path, provider, replace(LIMITS, timeout_seconds=1), clock))
    assert clock.value == 1
    assert rows(tmp_path, "jobs")[0]["job_id"]
    fresh = FakeMusicJobProvider(["succeeded"])
    execute(runner(tmp_path, fresh))
    assert fresh.submissions == 0
    assert fresh.polls == 1
    assert len(rows(tmp_path, "jobs")) == 1


def test_poll_count_limit_and_pending_blocks_other_jobs(tmp_path):
    provider = FakeMusicJobProvider(FIXTURES["pending"])
    with pytest.raises(FactoryError, match="Polling limit"):
        execute(runner(tmp_path, provider, replace(LIMITS, max_polls=2)))
    assert provider.polls == 2
    with pytest.raises(FactoryError, match="unresolved"):
        execute(runner(tmp_path, provider), run="other")
    assert provider.submissions == 1


@pytest.mark.parametrize("scenario", ["failure", "malformed"])
def test_terminal_error_is_not_hidden_or_retried(tmp_path, scenario):
    provider = FakeMusicJobProvider(FIXTURES[scenario])
    with pytest.raises(FactoryError):
        execute(runner(tmp_path, provider))
    before = (provider.submissions, provider.polls)
    with pytest.raises(FactoryError, match="reconciliation"):
        execute(runner(tmp_path, provider))
    assert (provider.submissions, provider.polls) == before
    assert rows(tmp_path, "jobs")[0]["reserved_cents"] == 26


@pytest.mark.parametrize("crash", [False, True])
def test_uncertain_submission_and_process_crash_never_resubmit(tmp_path, crash):
    class LostSubmit(FakeMusicJobProvider):
        def submit(self, request_id, request):
            super().submit(request_id, request)
            if crash:
                raise KeyboardInterrupt()
            raise TimeoutError("sensitive-provider-diagnostic")

    provider = LostSubmit()
    expected = KeyboardInterrupt if crash else FactoryError
    with pytest.raises(expected) as error:
        execute(runner(tmp_path, provider))
    assert "sensitive-provider-diagnostic" not in str(error.value)
    assert rows(tmp_path, "jobs")[0]["status"] == ("submitting" if crash else "uncertain")
    fresh = FakeMusicJobProvider()
    with pytest.raises(FactoryError, match="reconciliation"):
        execute(runner(tmp_path, fresh))
    with pytest.raises(FactoryError, match="unresolved"):
        execute(runner(tmp_path, fresh), run="other")
    assert fresh.submissions == 0
    assert "sensitive-provider-diagnostic" not in json.dumps(rows(tmp_path, "events"))


@pytest.mark.parametrize(
    "limits,second_run",
    [
        (replace(LIMITS, run_budget_cents=30), "run"),
        (replace(LIMITS, daily_budget_cents=30), "other"),
        (replace(LIMITS, daily_requests=1), "other"),
    ],
)
def test_budget_and_daily_quota_stop_before_submit(tmp_path, limits, second_run):
    provider = FakeMusicJobProvider(["succeeded"])
    job = runner(tmp_path, provider, limits)
    execute(job)
    with pytest.raises(FactoryError, match="limit exceeded"):
        execute(job, run=second_run, slot=1)
    assert provider.submissions == 1
    assert len(rows(tmp_path, "jobs")) == 1


def test_seoul_daily_rollover_preserves_run_budget(tmp_path):
    provider = FakeMusicJobProvider(["succeeded"])
    limits = JobLimits(30, 30, 1)
    execute(runner(tmp_path, provider, limits, timestamp=lambda: "2026-09-27T14:59:59+00:00"))
    tomorrow = runner(tmp_path, provider, limits, timestamp=lambda: "2026-09-27T15:00:00+00:00")
    with pytest.raises(FactoryError, match="limit exceeded"):
        execute(tomorrow, slot=1)
    execute(tomorrow, run="next")
    assert [r["day"] for r in rows(tmp_path, "jobs")] == ["2026-09-27", "2026-09-28"]


def test_request_and_quote_changes_are_rejected(tmp_path):
    provider = FakeMusicJobProvider(["succeeded"])
    job = runner(tmp_path, provider)
    execute(job)
    with pytest.raises(FactoryError, match="differs"):
        execute(job, reserve=27)
    with pytest.raises(FactoryError, match="differs"):
        job.execute("run", 0, replace(REQUEST, seed=43), reserve_cents=26)
    assert provider.submissions == 1


def test_cost_overrun_is_recorded_and_blocks_new_submission(tmp_path):
    provider = FakeMusicJobProvider(["succeeded"], cost_cents=30)
    with pytest.raises(FactoryError, match="exceeded reserved"):
        execute(runner(tmp_path, provider))
    row = rows(tmp_path, "jobs")[0]
    assert row["actual_cents"] == 30
    assert row["status"] == "invalid"
    with pytest.raises(FactoryError, match="unresolved"):
        execute(runner(tmp_path, provider), run="other")
    assert provider.submissions == 1


def test_lock_prevents_concurrent_submission(tmp_path):
    provider = FakeMusicJobProvider()
    with run_lock(tmp_path), pytest.raises(FactoryError, match="locked"):
        execute(runner(tmp_path, provider))
    assert provider.submissions == 0


def test_network_provider_and_unsafe_prompt_are_rejected(tmp_path):
    provider = FakeMusicJobProvider()
    provider.network_required = True
    with pytest.raises(FactoryError, match="offline"):
        runner(tmp_path, provider)
    provider.network_required = False
    with pytest.raises(FactoryError, match="internal dummy"):
        runner(tmp_path, provider).execute(
            "run", 0, replace(REQUEST, prompt="not allowed"), reserve_cents=26
        )
    assert provider.submissions == 0
    assert not (tmp_path / "jobs.db").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_budget_cents", 0),
        ("daily_budget_cents", -1),
        ("daily_requests", True),
        ("max_polls", 1.5),
        ("timeout_seconds", float("nan")),
        ("base_delay_seconds", 0),
        ("max_delay_seconds", float("inf")),
    ],
)
def test_invalid_limits(field, value):
    with pytest.raises(FactoryError):
        replace(LIMITS, **{field: value})


def test_reservation_is_durable_before_provider_is_called(tmp_path):
    class ObservingProvider(FakeMusicJobProvider):
        def submit(self, request_id, request):
            ledger = rows(tmp_path, "jobs")
            assert ledger[0]["reserved_cents"] == 26
            assert ledger[0]["status"] == "submitting"
            assert ledger[0]["request_id"] == request_id
            return super().submit(request_id, request)

    execute(runner(tmp_path, ObservingProvider(["succeeded"])))


def test_failure_keeps_budget_reservation(tmp_path):
    limits = replace(LIMITS, daily_budget_cents=30)
    with pytest.raises(FactoryError):
        execute(runner(tmp_path, FakeMusicJobProvider(["failed"]), limits))
    provider = FakeMusicJobProvider(["succeeded"])
    with pytest.raises(FactoryError, match="limit exceeded"):
        execute(runner(tmp_path, provider, limits), run="other")
    assert provider.submissions == 0


@pytest.mark.parametrize("job_id", [None, "", {"unexpected": 1}, "https://example.invalid/file"])
def test_malformed_submit_is_uncertain(tmp_path, job_id):
    class BadSubmit(FakeMusicJobProvider):
        def submit(self, request_id, request):
            return job_id

    with pytest.raises(FactoryError, match="unknown"):
        execute(runner(tmp_path, BadSubmit()))
    assert rows(tmp_path, "jobs")[0]["status"] == "uncertain"


def test_unknown_ledger_version_is_not_modified(tmp_path):
    with sqlite3.connect(tmp_path / "jobs.db") as db:
        db.execute("PRAGMA user_version=99")
    with pytest.raises(FactoryError, match="version"):
        execute(runner(tmp_path, FakeMusicJobProvider()))
    with sqlite3.connect(tmp_path / "jobs.db") as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99


def test_receipt_schema_rejects_publishable_status(tmp_path):
    from ai_bgm_factory.schemas import validate

    receipt = execute(runner(tmp_path, FakeMusicJobProvider(["succeeded"])))
    with pytest.raises(FactoryError, match="schema"):
        validate("music_job", {**receipt, "upload_eligible": True})
