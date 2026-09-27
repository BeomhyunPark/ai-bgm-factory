"""Offline HTTP contract fixtures for Stable Audio; no live transport or credentials."""

import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Protocol

from .config import FactoryError
from .music_jobs import JobResult, RetryablePollError
from .providers import DummyProvider, GenerationRequest
from .schemas import validate
from .util import now, write_json

SUBMIT_PATH = "/v2beta/audio/stable-audio/text-to-audio"
RESULT_PATH = "/v2beta/audio/results/"
MODEL = "stable-audio-3"


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


class MusicTransport(Protocol):
    network_required: bool

    def request(
        self,
        method: str,
        path: str,
        *,
        form: dict | None,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> HttpResponse: ...


class FixtureTransport:
    network_required = False

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def request(self, method, path, *, form, timeout_seconds, max_response_bytes):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "form": form,
                "timeout_seconds": timeout_seconds,
                "max_response_bytes": max_response_bytes,
            }
        )
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def retry_after(value, *, timestamp):
    """RFC 9110 delay-seconds or HTTP-date; return None for malformed input."""
    if not isinstance(value, str) or len(value) > 128:
        return None
    try:
        if re.fullmatch(r"[0-9]+", value.strip()):
            delay = float(value)
        else:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                return None
            delay = max(0, (date - datetime.fromisoformat(timestamp)).total_seconds())
        return delay if math.isfinite(delay) else None
    except (ValueError, TypeError, OverflowError):
        return None


class StableAudioFixtureAdapter:
    """MusicJobProvider bridge for synthetic HTTP responses only.

    Successful jobs use a simulated 26-cent charge, not provider billing evidence.
    The binary response is fingerprinted but not exported as a playable asset.
    """

    name = "stable-audio-http-fixture-v1"
    network_required = False

    def __init__(
        self,
        transport: MusicTransport,
        evidence_dir: Path,
        *,
        timeout_seconds=10,
        max_response_bytes=80_000_000,
        timestamp=now,
    ):
        if transport.network_required is not False:
            raise FactoryError("Live music transport is disabled")
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 60
        ):
            raise FactoryError("Invalid HTTP timeout")
        if type(max_response_bytes) is not int or not 1 <= max_response_bytes <= 100_000_000:
            raise FactoryError("Invalid HTTP response size limit")
        self.transport = transport
        self.evidence_dir = Path(evidence_dir)
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.timestamp = timestamp

    def validate_request(self, request):
        DummyProvider().validate_request(request)
        if request.kind != "audio" or not 1 <= request.duration_seconds <= 380:
            raise FactoryError("Unsupported audio fixture duration")
        # This API uses zero to randomize; do not silently change deterministic seed semantics.
        if type(request.seed) is not int or not 1 <= request.seed <= 4294967294:
            raise FactoryError("Audio contract requires an explicit nonzero seed")

    def submit(self, request_id: str, request: GenerationRequest):
        self.validate_request(request)
        if not re.fullmatch(r"[a-f0-9]{64}", request_id):
            raise FactoryError("Invalid local request ID")
        response, _ = self._request(
            "POST",
            SUBMIT_PATH,
            request_id,
            {
                "model": MODEL,
                "prompt": request.prompt,
                "duration": request.duration_seconds,
                "seed": request.seed,
                "output_format": "wav",
            },
        )
        if response.status != 202:
            raise FactoryError("Audio submission was not acknowledged")
        try:
            payload = json.loads(response.body)
            job_id = payload["id"]
            if not isinstance(job_id, str) or not re.fullmatch(r"[a-f0-9]{64}", job_id):
                raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise FactoryError("Invalid audio generation ID") from None
        return job_id

    def poll(self, job_id):
        if not isinstance(job_id, str) or not re.fullmatch(r"[a-f0-9]{64}", job_id):
            raise FactoryError("Invalid audio generation ID")
        try:
            response, delay = self._request("GET", RESULT_PATH + job_id, job_id, None)
        except TimeoutError:
            raise RetryablePollError() from None
        if response.status == 202:
            if delay is not None:
                raise RetryablePollError(retry_after_seconds=delay)
            return JobResult("running")
        if response.status == 429 or 500 <= response.status <= 599:
            raise RetryablePollError(retry_after_seconds=delay)
        if response.status != 200:
            return JobResult("failed")
        media = self._headers(response).get("content-type", "").split(";", 1)[0].strip().lower()
        if media not in ("audio/wav", "audio/x-wav") or not (
            response.body[:4] == b"RIFF" and response.body[8:12] == b"WAVE"
        ):
            raise FactoryError("Invalid audio fixture response")
        return JobResult("succeeded", 26)

    @staticmethod
    def _headers(response):
        return {key.lower(): value for key, value in response.headers.items()}

    def _request(self, method, path, correlation_id, form):
        try:
            response = self.transport.request(
                method,
                path,
                form=form,
                timeout_seconds=self.timeout_seconds,
                max_response_bytes=self.max_response_bytes,
            )
        except TimeoutError:
            self._record(method, correlation_id, self.timestamp(), None, None)
            raise TimeoutError("Music transport timed out") from None
        except Exception:
            self._record(method, correlation_id, self.timestamp(), None, None)
            raise FactoryError("Music transport failed") from None
        if (
            type(response) is not HttpResponse
            or type(response.status) is not int
            or not 100 <= response.status <= 599
            or type(response.body) is not bytes
            or not isinstance(response.headers, dict)
            or any(
                not isinstance(k, str) or not isinstance(v, str)
                for k, v in response.headers.items()
            )
        ):
            raise FactoryError("Malformed music transport response")
        if len(response.body) > self.max_response_bytes:
            raise FactoryError("Music response exceeds size limit")
        received = self.timestamp()
        delay = retry_after(self._headers(response).get("retry-after"), timestamp=received)
        self._record(method, correlation_id, received, response, delay)
        return response, delay

    def _record(self, method, correlation_id, received, response, delay):
        # Allowlist only. Never persist arbitrary headers, URLs, errors, or response text.
        record = {
            "schema_version": "1.0.0",
            "correlation_id": correlation_id,
            "adapter": self.name,
            "model": MODEL,
            "model_version": "unknown",
            "operation": "submit" if method == "POST" else "poll",
            "received_at": received,
            "http_status": response.status if response else None,
            "response_sha256": hashlib.sha256(response.body).hexdigest() if response else None,
            "response_bytes": len(response.body) if response else None,
            "retry_after_seconds": delay,
            "body_retained": False,
            "rights_status": "blocked",
            "intended_for_testing_only": True,
        }
        validate("music_http_evidence", record)
        write_json(self.evidence_dir / (uuid.uuid4().hex + ".json"), record)
