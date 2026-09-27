"""Deterministic local adapters. These fixtures are NOT production creative assets."""

import os
import random
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import FactoryError
from .util import digest, now, object_hash, write_json


@dataclass(frozen=True)
class GenerationRequest:
    kind: str
    seed: int
    prompt: str
    duration_seconds: float = 0
    slot: int = 0


class GenerationProvider(Protocol):
    def capabilities(self) -> dict: ...
    def validate_request(self, request: GenerationRequest) -> None: ...
    def generate(self, request: GenerationRequest, output: Path) -> dict: ...
    def get_rights_evidence(self) -> dict: ...


PROMPTS = {
    "text": "Local test brief: quiet night coding; instrumental only; original fixture.",
    "audio": "Algorithmic test signal: warm sine pad and gentle plucks; instrumental only.",
    "image": "Local geometric night-window test card; abstract, no people or branding.",
}
TRACK_NAMES = [
    "First Light",
    "Quiet Terminal",
    "Open Window",
    "Slow Current",
    "Small Orbit",
    "Soft Landing",
    "Blue Hour",
    "Last Commit",
]


class DummyProvider:
    def capabilities(self):
        return {
            "supports_seed": True,
            "supports_instrumental_flag": True,
            "supports_async_job": False,
            "max_duration_seconds": 1000,
            "commercial_use_status": "blocked",
            "network_required": False,
        }

    def validate_request(self, request):
        # Phase 1 accepts ONLY closed internal fixtures, never arbitrary style text.
        if request.kind not in PROMPTS or request.prompt != PROMPTS[request.kind]:
            raise FactoryError("Only internal dummy prompt templates are supported")
        if not 0 <= request.seed <= 2**32 - 1 or not 0 <= request.slot < 8:
            raise FactoryError("Invalid dummy request")
        if request.kind == "audio" and not 1 <= request.duration_seconds <= 1000:
            raise FactoryError("Unsupported dummy audio duration")

    def get_rights_evidence(self):
        return {
            "status": "blocked",
            "intended_for_testing_only": True,
            "intended_use": ["local_pipeline_testing"],
            "account_tier": "not_applicable",
            "terms_url": None,
            "terms_reviewed_at": None,
            "terms_snapshot_sha256": None,
            "evidence_paths": [],
            "restrictions": ["no_upload", "no_commercial_use", "no_content_id_registration"],
        }

    def generate(self, request, output):
        self.validate_request(request)
        output.parent.mkdir(parents=True, exist_ok=True)
        if request.kind == "text":
            rng = random.Random(request.seed)
            concept = {
                "schema_version": "1.0.0",
                "concept_id": f"dummy-{request.seed}",
                "audience": "developers",
                "use_case": "night coding",
                "mood": rng.choice(["calm", "warm", "reflective"]),
                "bpm_range": [72, 84],
                "genre": "algorithmic ambient test fixture",
                "visual_brief": "abstract night window",
                "seed": request.seed,
                "novelty_anchors": ["test signal only; originality not evaluated"],
                "track_names": TRACK_NAMES,
                "intended_for_testing_only": True,
            }
            write_json(output, concept)
        elif request.kind == "audio":
            self._audio(request, output)
        else:
            self._image(request, output)
        return {
            "schema_version": "1.0.0",
            "asset_id": output.stem,
            "kind": request.kind,
            "provider": "dummy",
            "model": "local-algorithmic-fixture",
            "model_version": "1.0.0",
            "request_id": object_hash(request.__dict__)[:24],
            "prompt": request.prompt,
            "negative_prompt": "vocals, speech, artist imitation",
            "seed": request.seed,
            "generated_at": now(),
            "source_sha256": digest(output),
            "terms_url": None,
            "usage": {"cost_usd": 0, "network_requests": 0},
            "intended_for_testing_only": True,
        }

    def _audio(self, request, output):
        rate = 48000
        frames = round(request.duration_seconds * rate)
        rng = random.Random(request.seed + request.slot * 1009)
        scale = np.array([0, 2, 4, 7, 9, 12])
        notes = np.array([rng.choice(scale) for _ in range(1024)])
        root = 45 + request.slot + request.seed % 5
        base = 440 * 2 ** ((root - 69) / 12)
        beat = 60 / (72 + request.slot)
        temporary = output.with_name(output.stem + ".partial.wav")
        with wave.open(str(temporary), "wb") as wav:
            wav.setparams((2, 2, rate, 0, "NONE", "not compressed"))
            for start in range(0, frames, rate * 8):
                t = np.arange(start, min(start + rate * 8, frames), dtype=np.float64) / rate
                # Continuous, slowly modulated pad; no repeated source-audio loop.
                pad = (
                    sum(
                        np.sin(2 * np.pi * base * ratio * t + 0.15 * np.sin(t * 0.11)) / (i + 1)
                        for i, ratio in enumerate([1, 1.5, 2])
                    )
                    * 0.065
                )
                step = np.floor(t / beat).astype(int)
                phase = t % beat
                freq = base * 2 ** ((notes[step % len(notes)] + 12) / 12)
                attack = np.minimum(phase / 0.03, 1)
                pluck = np.sin(2 * np.pi * freq * phase) * np.exp(-phase * 4) * attack * 0.035
                envelope = np.minimum(t / 0.15, 1) * np.minimum((frames / rate - t) / 0.15, 1)
                left = (pad + pluck) * envelope
                right = (pad + 0.93 * pluck) * envelope
                stereo = np.column_stack((left, right))
                wav.writeframes((stereo * 32767).astype("<i2").tobytes())
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        temporary.replace(output)

    def _image(self, request, output):
        # This is a programmatic fixture, not an AI artwork generation request.
        image = Image.new("RGB", (1280, 720), (15, 28, 40))
        draw = ImageDraw.Draw(image)
        rng = random.Random(request.seed)
        for y in range(720):
            draw.line((0, y, 1279, y), fill=(15 + y // 100, 28 + y // 65, 40 + y // 38))
        for _ in range(60):
            x, y = rng.randrange(600, 1230), rng.randrange(50, 630)
            draw.ellipse((x, y, x + 2, y + 2), fill=(104, 136, 155))
        draw.rounded_rectangle((70, 85, 520, 635), radius=25, fill=(23, 44, 56))
        font = ImageFont.load_default(size=54)
        small = ImageFont.load_default(size=25)
        draw.text((108, 160), "NIGHT\nWORK", font=font, fill=(211, 235, 192), spacing=14)
        draw.text(
            (108, 390), "INSTRUMENTAL\nPIPELINE TEST", font=small, fill=(179, 196, 204), spacing=10
        )
        draw.text(
            (108, 570),
            "DUMMY / NOT FOR UPLOAD",
            font=ImageFont.load_default(size=18),
            fill=(179, 196, 204),
        )
        image.save(output)
