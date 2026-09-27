import json
import math
import wave

import numpy as np
from PIL import Image

from .config import FactoryError
from .util import command, probe


def audio_qc(path, asset_id):
    peak = total = count = silent_run = longest = 0
    with wave.open(str(path), "rb") as wav:
        rate, channels, frames = wav.getframerate(), wav.getnchannels(), wav.getnframes()
        if channels != 2 or wav.getsampwidth() != 2 or rate != 48000:
            raise FactoryError("Invalid fixture audio format")
        while data := wav.readframes(rate):
            values = np.frombuffer(data, "<i2").astype(np.float64) / 32768
            peak = max(peak, float(np.max(np.abs(values))))
            total += float(values @ values)
            count += len(values)
            silent = np.max(np.abs(values.reshape(-1, channels)), axis=1) < 10 ** (-60 / 20)
            boundaries = np.flatnonzero(np.diff(np.r_[False, silent, False].astype(int)))
            for a, b in zip(boundaries[::2], boundaries[1::2], strict=True):
                length = int(b - a) + (silent_run if a == 0 else 0)
                longest = max(longest, length)
            if len(boundaries) and silent[-1]:
                a = int(boundaries[-2])
                silent_run = len(silent) - a + (silent_run if a == 0 else 0)
            else:
                silent_run = 0
    rms_dbfs = 20 * math.log10(max(math.sqrt(total / max(count, 1)), 1e-12))
    failures = []
    if peak >= 0.999:
        failures.append("clipping")
    if longest / rate > 3 or rms_dbfs < -60:
        failures.append("unexpected_silence")
    return {
        "schema_version": "1.0.0",
        "asset_id": asset_id,
        "status": "failed" if failures else "passed",
        "scope": "dummy_technical_only",
        "measurements": {
            "duration_seconds": frames / rate,
            "sample_peak_dbfs": 20 * math.log10(max(peak, 1e-12)),
            "rms_dbfs": rms_dbfs,
            "max_silence_seconds": longest / rate,
            "vocal_probability": None,
            "max_similarity": None,
        },
        "thresholds_version": "dummy-1.0.0",
        "not_evaluated": ["vocal_classifier", "spectral_anomaly", "audio_similarity"],
        "failures": failures,
    }


def measure_loudness(path):
    result = command(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostdin",
            "-threads",
            "2",
            "-i",
            path,
            "-af",
            "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ]
    )
    start = result.stderr.rfind("{\n")
    if start < 0:
        raise FactoryError("FFmpeg did not report loudness measurements")
    # FFmpeg can append progress/statistics after the loudnorm JSON object.
    try:
        measured, _ = json.JSONDecoder().raw_decode(result.stderr[start:])
        required = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
        if not all(math.isfinite(float(measured[key])) for key in required):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise FactoryError("FFmpeg reported invalid loudness measurements") from None
    return measured


def master_audio(paths, reports, output, duration, crossfade):
    args = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-filter_complex_threads",
        "1",
        "-threads",
        "2",
    ]
    for p in paths:
        args += ["-i", p]
    filters = [
        f"[{i}:a]volume={-20 - r['measurements']['rms_dbfs']:.8f}dB[a{i}]"
        for i, r in enumerate(reports)
    ]
    last = "a0"
    for i in range(1, len(paths)):
        filters.append(f"[{last}][a{i}]acrossfade=d={crossfade}:c1=tri:c2=tri[m{i}]")
        last = f"m{i}"
    fade_start = max(0, duration - 1)
    filters.append(f"[{last}]apad,atrim=duration={duration},afade=t=out:st={fade_start}:d=1[out]")
    pre = output.parent / "premaster.wav"
    command(
        args
        + [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[out]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            pre,
        ]
    )
    measured = measure_loudness(pre)
    normalize = (
        "loudnorm=I=-14:TP=-1:LRA=11:linear=true:"
        f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}"
    )
    command(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-threads",
            "2",
            "-i",
            pre,
            "-af",
            normalize,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            output,
        ]
    )
    final = measure_loudness(output)
    if not abs(float(final["input_i"]) + 14) <= 1 or float(final["input_tp"]) > -1:
        raise FactoryError("Master loudness/true-peak gate failed")
    return {
        "schema_version": "1.0.0",
        "status": "passed",
        "integrated_lufs": float(final["input_i"]),
        "true_peak_dbtp": float(final["input_tp"]),
        "normalization": "two_pass_loudnorm",
        "source_gain_target_rms_dbfs": -20,
        "crossfade_seconds": crossfade,
        "pre_measurements": measured,
    }


def render(master, background, output, duration, *, inject_failure=False):
    tmp = output.with_name("final.partial.mp4")
    command(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-filter_threads",
            "1",
            "-loop",
            "1",
            "-framerate",
            "1",
            "-i",
            background,
            "-i",
            master,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-t",
            str(2 if inject_failure else duration),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "stillimage",
            "-profile:v",
            "baseline",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "2",
            "-crf",
            "24",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            tmp,
        ]
    )
    if inject_failure:
        raise FactoryError("Injected render interruption after partial MP4 creation")
    report = validate_video(tmp, duration)
    tmp.replace(output)
    return report


def validate_video(path, target, full_decode=True):
    info = probe(path)
    videos = [s for s in info["streams"] if s["codec_type"] == "video"]
    audios = [s for s in info["streams"] if s["codec_type"] == "audio"]
    if len(videos) != 1 or len(audios) != 1:
        raise FactoryError("Video/audio stream count mismatch")
    video, audio = videos[0], audios[0]
    vd, ad = float(video["duration"]), float(audio["duration"])
    conditions = [
        video["codec_name"] == "h264",
        video["width"] * 9 == video["height"] * 16,
        audio["codec_name"] == "aac",
        audio["channels"] == 2,
        audio["sample_rate"] == "48000",
        abs(vd - ad) <= 0.1,
        abs(float(info["format"]["duration"]) - target) <= 1,
    ]
    if not all(conditions):
        raise FactoryError("Video format/duration/A-V gate failed")
    if full_decode:
        command(
            [
                "ffmpeg",
                "-v",
                "error",
                "-xerror",
                "-nostdin",
                "-threads",
                "2",
                "-i",
                path,
                "-map",
                "0:v",
                "-map",
                "0:a",
                "-f",
                "null",
                "-",
            ]
        )
    return {
        "schema_version": "1.0.0",
        "status": "passed",
        "duration_seconds": float(info["format"]["duration"]),
        "video_duration": vd,
        "audio_duration": ad,
        "av_delta_seconds": abs(vd - ad),
        "video_codec": video["codec_name"],
        "audio_codec": audio["codec_name"],
        "width": video["width"],
        "height": video["height"],
        "full_decode_passed": full_decode,
    }


def validate_thumbnail(path):
    with Image.open(path) as image:
        if image.format != "JPEG" or image.size != (1280, 720):
            raise FactoryError("Thumbnail size/format mismatch")
        image.verify()
    if path.stat().st_size >= 2 * 1024 * 1024:
        raise FactoryError("Thumbnail exceeds fixture size limit")
