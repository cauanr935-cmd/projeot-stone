from __future__ import annotations

import csv
from pathlib import Path

from src.core.ffmpeg import ffprobe_json


def detect_scenes(video_path: Path, output_csv: Path | None = None) -> list[dict]:
    info = ffprobe_json(video_path)
    video = next(s for s in info["streams"] if s.get("codec_type") == "video")
    duration = float(info["format"]["duration"])
    points = [0.0, duration * .25, duration * .5, duration * .75, duration]
    scenes = [{"scene": i, "start_s": a, "end_s": b, "start_frame": round(a * 30), "end_frame": round(b * 30)}
              for i, (a, b) in enumerate(zip(points, points[1:]), 1)]
    if output_csv:
        with Path(output_csv).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["scene", "start_s", "end_s", "start_frame", "end_frame"])
            writer.writeheader()
            writer.writerows(scenes)
    return scenes
