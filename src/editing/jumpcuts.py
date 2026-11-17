from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

from src.core.config import common
from src.core.ffmpeg import ffprobe_json


def _silence_spans(video_path: Path, noise_db: int, min_silence_dur: float) -> list[tuple[float, float]]:
    proc = subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-nostats", "-vn",
                           "-i", str(video_path), "-af",
                           f"silencedetect=noise={noise_db}dB:d={min_silence_dur}", "-f", "null", "-"],
                          capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", proc.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*(-?[\d.]+)", proc.stderr)]
    duration = float(ffprobe_json(video_path)["format"]["duration"])
    if len(ends) < len(starts):
        ends.append(duration)
    return list(zip(starts, ends))


def _segments(duration: float, silences: list[tuple[float, float]], pad: float) -> list[tuple[float, float]]:
    spans = []
    cursor = 0.0
    for start, end in silences:
        left, right = max(cursor, start + pad), min(duration, end - pad)
        if left - cursor >= .18:
            spans.append((cursor, left))
        cursor = max(cursor, right)
    if duration - cursor >= .18:
        spans.append((cursor, duration))
    return spans or [(0.0, duration)]


def build_ast_calibrated_jumpcuts(video_path: Path, output_path: Path, cut_style: str = "seamless",
                                  noise_db: int = -32, min_silence_dur: float = .40,
                                  punch_in: bool = True) -> dict:
    if cut_style not in ("seamless", "overlapping"):
        raise ValueError("cut_style deve ser seamless ou overlapping")
    video_path, output_path = Path(video_path), Path(output_path)
    info = ffprobe_json(video_path)
    duration = float(info["format"]["duration"])
    video = next(s for s in info["streams"] if s.get("codec_type") == "video")
    if punch_in and int(video["height"]) * 16 != int(video["width"]) * 9:
        # Punch-in is disabled for non-vertical input instead of distorting it.
        punch_in = False
    pad = common()["pads"][cut_style]
    segments = _segments(duration, _silence_spans(video_path, noise_db, min_silence_dur), pad)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filters, labels = [], []
    for i, (start, end) in enumerate(segments):
        length = end - start
        zoom = 1.08 if punch_in and i % 2 else 1.0
        vf = f"trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,scale=iw*{zoom}:ih*{zoom},crop=1080:1920,setsar=1,fps=30,format=yuv420p"
        filters.append(f"[0:v]{vf}[v{i}]")
        filters.append(f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS,"
                       f"afade=t=in:st=0:d=0.015,afade=t=out:st={max(0,length-.015):.6f}:d=0.015[a{i}]")
        labels.extend([f"[v{i}]", f"[a{i}]"])
    filters.append("".join(labels) + f"concat=n={len(segments)}:v=1:a=1[vout][aout]")
    args = [shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(video_path),
            "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-ar", "48000", "-b:a", "192k", "-fps_mode", "cfr", str(output_path)]
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-4000:])
    out_duration = float(ffprobe_json(output_path)["format"]["duration"])
    lengths = [b - a for a, b in segments]
    junctions, elapsed = [], 0.0
    for length in lengths[:-1]:
        elapsed += length
        junctions.append(elapsed)
    return {"output": str(output_path), "segments": [[round(a, 3), round(b, 3)] for a, b in segments],
            "junctions_s": junctions, "pad": pad, "input_duration": duration,
            "output_duration": out_duration, "removed_seconds": duration - out_duration,
            "audio_fades": len(segments) * 2}


def plan_pattern_interrupts(duration_s: float, target_cuts_per_sec: float,
                            existing_cuts_s: list[float], min_gap_s: float = 1.2) -> list[float]:
    target = round(duration_s * target_cuts_per_sec)
    existing = sorted(t for t in existing_cuts_s if 0 < t < duration_s)
    need = max(0, target - len(existing))
    if not need or duration_s <= 0:
        return []
    candidates = [duration_s * i / (need + 1) for i in range(1, need + 1)]
    extras = []
    for t in candidates:
        if all(abs(t - e) >= min_gap_s for e in existing + extras):
            extras.append(t)
    # Fill remaining slots using progressively shifted points when feasible.
    for i in range(1, max(need * 3, 10)):
        if len(extras) >= need:
            break
        t = duration_s * ((i * .61803398875) % 1)
        if 0 < t < duration_s and all(abs(t-e) >= min_gap_s for e in existing + extras):
            extras.append(t)
    return sorted(extras)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--style", choices=["seamless", "overlapping"], default="seamless")
    ap.add_argument("--noise-db", type=int, default=-32)
    ap.add_argument("--min-silence", type=float, default=.4)
    a = ap.parse_args(argv)
    build_ast_calibrated_jumpcuts(a.input, a.out, a.style, a.noise_db, a.min_silence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
