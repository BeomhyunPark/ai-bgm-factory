"""Plan 8–12 sources in integer audio frames, including overlap loss."""

import math
from fractions import Fraction

from .config import FactoryError
from .schemas import validate


def plan_tracks(target_seconds, max_duration_seconds, *, min_tracks=8,
                crossfade_seconds=2, sample_rate=48000, min_duration_seconds=1):
    values = (target_seconds, max_duration_seconds, crossfade_seconds, min_duration_seconds)
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values):
        raise FactoryError("Track planning durations must be positive and finite")
    if type(min_tracks) is not int or not 8 <= min_tracks <= 12:
        raise FactoryError("Minimum track count must be between 8 and 12")
    if type(sample_rate) is not int or sample_rate <= 0:
        raise FactoryError("Invalid planning sample rate")
    target = Fraction(str(target_seconds)) * sample_rate
    fade = Fraction(str(crossfade_seconds)) * sample_rate
    if target.denominator != 1 or fade.denominator != 1:
        raise FactoryError("Target and crossfade must align to audio frames")
    target, fade = int(target), int(fade)
    maximum = math.floor(Fraction(str(max_duration_seconds)) * sample_rate)
    minimum = math.ceil(Fraction(str(min_duration_seconds)) * sample_rate)
    for count in range(min_tracks, 13):
        base, extra = divmod(target + fade * (count - 1), count)
        lengths = [base + (i < extra) for i in range(count)]
        # Two overlaps must not consume an entire interior source.
        if min(lengths) < minimum or min(lengths) <= 2 * fade:
            continue
        if max(lengths) > maximum:
            continue
        start = 0
        tracks = []
        for slot, frames in enumerate(lengths):
            tracks.append({"slot": slot, "frames": frames, "start_frame": start})
            start += frames - fade
        plan = {"schema_version": "1.0.0", "sample_rate": sample_rate,
                "target_frames": target, "crossfade_frames": fade,
                "max_source_frames": maximum, "min_source_frames": minimum,
                "tracks": tracks}
        validate("track_plan", plan)
        return plan
    raise FactoryError("Cannot cover target with 8–12 tracks within provider duration limits")
