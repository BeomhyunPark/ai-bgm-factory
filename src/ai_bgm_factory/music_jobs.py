"""Offline job lifecycle experiment; not connected to generate or a paid API."""

import math
import random
import re
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from .config import FactoryError
from .providers import DummyProvider, GenerationRequest
from .schemas import validate
from .storage import run_lock
from .util import now, object_hash, scan_secrets, validate_run_id


class RetryablePollError(Exception):
    """A read-only poll may be retried (e.g. 429, timeout, temporary 5xx)."""


@dataclass(frozen=True)
class JobResult:
    status: str
    cost_cents: int | None = None


class MusicJobProvider(Protocol):
    name: str
    network_required: bool

    def validate_request(self, request: GenerationRequest) -> None: ...
    def submit(self, request_id: str, request: GenerationRequest) -> str: ...
    def poll(self, job_id: str) -> JobResult: ...


class FakeMusicJobProvider:
    """Scripted local responses; creates job receipts, never playable media."""

    name = "fake-music-jobs-v1"
    network_required = False

    def __init__(self, outcomes=("queued", "running", "succeeded"), *, cost_cents=26):
        if not outcomes:
            raise FactoryError("Fake job requires outcomes")
        self.outcomes = tuple(outcomes)
        self.cost_cents = cost_cents
        self.submissions = 0
        self.polls = 0

    def validate_request(self, request):
        if request.kind != "audio":
            raise FactoryError("Music jobs require audio requests")
        DummyProvider().validate_request(request)

    def submit(self, request_id, request):
        self.submissions += 1
        return "fake-" + request_id

    def poll(self, job_id):
        outcome = self.outcomes[min(self.polls, len(self.outcomes) - 1)]
        self.polls += 1
        if outcome in ("429", "timeout", "503"):
            raise RetryablePollError()
        if outcome == "malformed":
            return {"unexpected": True}
        return JobResult(outcome, self.cost_cents if outcome == "succeeded" else None)


@dataclass(frozen=True)
class JobLimits:
    run_budget_cents: int
    daily_budget_cents: int
    daily_requests: int
    max_polls: int = 10
    timeout_seconds: float = 60
    base_delay_seconds: float = 1
    max_delay_seconds: float = 10

    def __post_init__(self):
        for value in (
            self.run_budget_cents,
            self.daily_budget_cents,
            self.daily_requests,
            self.max_polls,
        ):
            if type(value) is not int or value <= 0:
                raise FactoryError("Job limits must be positive integers")
        for value in (self.timeout_seconds, self.base_delay_seconds, self.max_delay_seconds):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise FactoryError("Job timing limits must be positive and finite")
        if self.base_delay_seconds > self.max_delay_seconds:
            raise FactoryError("Base delay exceeds maximum delay")


class MusicJobRunner:
    """One in-flight job per shared ledger; reserve before any submit.

    Submitted-but-unacknowledged jobs are never automatically resubmitted.
    Failed and uncertain jobs retain their reservation until future reconciliation.
    """

    def __init__(
        self,
        root: Path,
        provider: MusicJobProvider,
        limits: JobLimits,
        *,
        clock=time.monotonic,
        sleep=time.sleep,
        jitter=random.random,
        timestamp=now,
    ):
        if provider.network_required is not False:
            raise FactoryError("Only offline job providers are enabled")
        validate_run_id(provider.name)
        self.root = Path(root)
        self.provider = provider
        self.limits = limits
        self.clock, self.sleep, self.jitter = clock, sleep, jitter
        self.timestamp = timestamp

    def execute(
        self, run_id: str, slot: int, request: GenerationRequest, *, reserve_cents: int
    ) -> dict:
        validate_run_id(run_id)
        if type(slot) is not int or slot < 0 or slot != request.slot:
            raise FactoryError("Invalid job slot")
        if type(reserve_cents) is not int or reserve_cents <= 0:
            raise FactoryError("Reservation must be positive integer cents")
        self.provider.validate_request(request)
        identity = object_hash(
            {
                "provider": self.provider.name,
                "request": request.__dict__,
                "reserve_cents": reserve_cents,
            }
        )
        request_id = object_hash({"run_id": run_id, "slot": slot})
        self.root.mkdir(parents=True, exist_ok=True)
        with run_lock(self.root), closing(sqlite3.connect(self.root / "jobs.db")) as db:
            db.row_factory = sqlite3.Row
            self._initialize(db)
            row = db.execute("SELECT * FROM jobs WHERE request_id=?", (request_id,)).fetchone()
            if row is not None:
                if row["identity"] != identity:
                    raise FactoryError("Existing job request differs; preserving ledger")
                if row["status"] == "succeeded":
                    return self._receipt(row)
                if row["status"] in ("submitting", "uncertain", "failed", "invalid"):
                    raise FactoryError("Job requires manual reconciliation; no resubmission")
            else:
                self._reserve(db, run_id, request_id, identity, reserve_cents)
                row = db.execute("SELECT * FROM jobs WHERE request_id=?", (request_id,)).fetchone()
            if row["status"] == "reserved":
                self._update(db, request_id, "submitting")
                started = self.clock()
                try:
                    job_id = self.provider.submit(request_id, request)
                    if not isinstance(job_id, str) or not re.fullmatch(
                        r"[a-zA-Z0-9_-]{1,128}", job_id
                    ):
                        raise ValueError()
                    scan_secrets({"job_id": job_id})
                except Exception:
                    self._update(db, request_id, "uncertain")
                    self._event(db, request_id, "submit", "uncertain", started)
                    raise FactoryError("Submission outcome unknown; no resubmission") from None
                with db:
                    db.execute(
                        "UPDATE jobs SET job_id=?, status='queued' WHERE request_id=?",
                        (job_id, request_id),
                    )
                self._event(db, request_id, "submit", "queued", started)
            else:
                job_id = row["job_id"]
            return self._poll(db, request_id, job_id, reserve_cents)

    def _initialize(self, db):
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise FactoryError("Unsupported job ledger version")
        with db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                request_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, identity TEXT NOT NULL,
                day TEXT NOT NULL, reserved_cents INTEGER NOT NULL, actual_cents INTEGER,
                status TEXT NOT NULL, job_id TEXT)""")
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY, request_id TEXT NOT NULL,
                run_id TEXT NOT NULL, attempt INTEGER NOT NULL,
                timestamp TEXT NOT NULL, stage TEXT NOT NULL,
                status TEXT NOT NULL, duration_ms REAL NOT NULL)""")
            db.execute("PRAGMA user_version=1")

    def _reserve(self, db, run_id, request_id, identity, cents):
        started = self.clock()
        day = datetime.fromisoformat(self.timestamp()).astimezone(ZoneInfo("Asia/Seoul"))
        day = day.date().isoformat()
        # The filesystem lock covers all runners sharing this ledger, including submit/poll.
        with db:
            if db.execute(
                "SELECT 1 FROM jobs WHERE status IN "
                "('reserved','submitting','queued','running','uncertain','invalid')"
            ).fetchone():
                raise FactoryError("An unresolved job already occupies the ledger")
            run_total = db.execute(
                "SELECT COALESCE(SUM(MAX(reserved_cents, "
                "COALESCE(actual_cents, 0))),0) FROM jobs WHERE run_id=?",
                (run_id,),
            ).fetchone()[0]
            daily = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(MAX(reserved_cents, "
                "COALESCE(actual_cents, 0))),0) FROM jobs WHERE day=?",
                (day,),
            ).fetchone()
            if (
                run_total + cents > self.limits.run_budget_cents
                or daily[1] + cents > self.limits.daily_budget_cents
                or daily[0] >= self.limits.daily_requests
            ):
                raise FactoryError("Job budget or daily request limit exceeded")
            db.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, NULL, 'reserved', NULL)",
                (request_id, run_id, identity, day, cents),
            )
        self._event(db, request_id, "reserve", "reserved", started)

    def _update(self, db, request_id, status):
        with db:
            db.execute("UPDATE jobs SET status=? WHERE request_id=?", (status, request_id))

    def _event(self, db, request_id, operation, status, started):
        with db:
            run_id = db.execute(
                "SELECT run_id FROM jobs WHERE request_id=?", (request_id,)
            ).fetchone()[0]
            attempt = (
                db.execute(
                    "SELECT COUNT(*) FROM events WHERE request_id=? AND stage=?",
                    (request_id, operation),
                ).fetchone()[0]
                + 1
            )
            db.execute(
                "INSERT INTO events VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request_id,
                    run_id,
                    attempt,
                    self.timestamp(),
                    operation,
                    status,
                    round(max(0, self.clock() - started) * 1000, 3),
                ),
            )

    def _poll(self, db, request_id, job_id, reserved):
        deadline = self.clock() + self.limits.timeout_seconds
        for attempt in range(self.limits.max_polls):
            if self.clock() >= deadline:
                break
            started = self.clock()
            try:
                result = self.provider.poll(job_id)
                if (
                    type(result) is not JobResult
                    or result.status not in ("queued", "running", "succeeded", "failed")
                    or (
                        result.status == "succeeded"
                        and (type(result.cost_cents) is not int or result.cost_cents < 0)
                    )
                    or (result.status != "succeeded" and result.cost_cents is not None)
                ):
                    raise ValueError()
            except RetryablePollError:
                self._event(db, request_id, "poll", "retryable", started)
            except Exception:
                self._update(db, request_id, "invalid")
                self._event(db, request_id, "poll", "invalid", started)
                raise FactoryError("Invalid job response; reconciliation required") from None
            else:
                status = result.status
                if status == "succeeded" and result.cost_cents > reserved:
                    status = "invalid"
                with db:
                    db.execute(
                        "UPDATE jobs SET status=?, actual_cents=? WHERE request_id=?",
                        (status, result.cost_cents, request_id),
                    )
                self._event(db, request_id, "poll", status, started)
                if status in ("failed", "invalid"):
                    raise FactoryError("Job failed or exceeded reserved cost; no resubmission")
                if status == "succeeded":
                    return self._receipt(
                        db.execute(
                            "SELECT * FROM jobs WHERE request_id=?", (request_id,)
                        ).fetchone()
                    )
            if attempt + 1 < self.limits.max_polls:
                delay = min(
                    self.limits.max_delay_seconds,
                    self.limits.base_delay_seconds * 2 ** min(attempt, 20),
                )
                delay *= 0.5 + 0.5 * self.jitter()
                self.sleep(min(delay, max(0, deadline - self.clock())))
        self._event(db, request_id, "poll", "exhausted", self.clock())
        raise FactoryError("Polling limit reached; resume the existing job")

    @staticmethod
    def _receipt(row):
        receipt = {
            "schema_version": "1.0.0",
            "request_id": row["request_id"],
            "run_id": row["run_id"],
            "job_id": row["job_id"],
            "status": row["status"],
            "reserved_cents": row["reserved_cents"],
            "actual_cents": row["actual_cents"],
            "rights_status": "blocked",
            "intended_for_testing_only": True,
            "upload_eligible": False,
        }
        validate("music_job", receipt)
        return receipt
