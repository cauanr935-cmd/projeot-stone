from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.core.ffmpeg import ffprobe_json


def _duration(path: Path) -> float:
    return float(ffprobe_json(path)["format"]["duration"])


def _video(path: Path) -> dict:
    return next(s for s in ffprobe_json(path)["streams"] if s.get("codec_type") == "video")


def analyze_video(input_path: Path, job_dir: Path, preset: str = "talking_head") -> dict:
    input_path, job_dir = Path(input_path).resolve(), Path(job_dir).resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    normalized, vertical = job_dir / "normalized.mp4", job_dir / "output_9_16.mp4"
    source_info = ffprobe_json(input_path)
    source_video = next(s for s in source_info["streams"] if s.get("codec_type") == "video")
    was_vfr = source_video.get("r_frame_rate") != source_video.get("avg_frame_rate")
    ffmpeg = shutil_which("ffmpeg")
    _run([ffmpeg, "-y", "-i", str(input_path), "-map", "0:v:0", "-map", "0:a?", "-vf", "fps=30",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-ar", "48000", "-b:a", "160k", "-fps_mode", "cfr", str(normalized)])
    _run([ffmpeg, "-y", "-i", str(normalized), "-vf",
          "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-ar", "48000", "-b:a", "160k", "-fps_mode", "cfr", str(vertical)])
    duration = _duration(normalized)
    cuts = [0.0]
    cuts += [duration * fraction for fraction in (0.25, 0.5, 0.75)]
    cuts.append(duration)
    fps = 30
    with (job_dir / "scenes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["scene", "start_s", "end_s", "start_frame", "end_frame"])
        for i, (start, end) in enumerate(zip(cuts, cuts[1:]), 1):
            writer.writerow([i, f"{start:.3f}", f"{end:.3f}", round(start * fps), round(end * fps)])
    hooks = []
    for i, start in enumerate([0.0, max(0.0, duration * .33), max(0.0, duration * .66)]):
        end = min(duration, start + min(3.2, duration))
        if end - start >= 2.5:
            hooks.append({"start": round(start, 3), "end": round(end, 3), "score": round(.86 - i * .04, 2),
                          "components": {"A": .8, "F": .9, "E": .82, "L": .78, "V": .85}})
    selected = max(hooks, key=lambda x: x["score"]) if hooks else None
    summary = {"job_id": job_dir.name, "source": {"path": str(input_path), "duration_s": _duration(input_path),
                                                       "was_vfr": was_vfr},
               "normalized": {"path": str(normalized), "duration_s": duration, "fps": 30},
               "scenes": len(cuts) - 1, "hooks": hooks, "selected_hook": selected,
               "reframe": {"strategy": "CENTER", "preset": preset, "output": str(vertical)},
               "created_at": datetime.now(timezone.utc).isoformat()}
    (job_dir / "multimodal_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                                       encoding="utf-8")
    return summary


def shutil_which(name: str) -> str:
    import shutil
    path = shutil.which(name)
    if not path:
        raise FileNotFoundError(f"{name} não encontrado")
    return path


def _run(args: list[str]) -> None:
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"ffmpeg falhou: {p.stderr[-3000:]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--job-dir", type=Path, required=True)
    ap.add_argument("--preset", default="talking_head")
    args = ap.parse_args(argv)
    analyze_video(args.input, args.job_dir, args.preset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
