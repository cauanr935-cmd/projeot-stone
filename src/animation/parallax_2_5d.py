from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

from src.animation.depth import estimate_depth

WIDTH, HEIGHT = 1080, 1920


def _fit(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    scale = min(WIDTH / w, HEIGHT / h)
    resized = cv2.resize(image, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    x, y = (WIDTH - resized.shape[1]) // 2, (HEIGHT - resized.shape[0]) // 2
    canvas[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
    return canvas


def animate_static_image_2_5d(image_path: Path, output_path: Path, duration: float = 5.0, fps: int = 30,
                              strength: float | None = None, pivot_box: str = "auto") -> dict:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(image_path)
    base = _fit(image)
    depth, engine = estimate_depth(base)
    if pivot_box == "auto":
        x, y, w, h = 330, 510, 420, 700
    else:
        x, y, w, h = map(int, pivot_box.split(","))
    x, y = max(0, x), max(0, y)
    w, h = min(w, WIDTH - x), min(h, HEIGHT - y)
    strength = float(strength if strength is not None else 10)
    frames = round(duration * fps)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([shutil_which("ffmpeg"), "-hide_banner", "-nostats", "-y", "-f", "rawvideo",
                            "-pix_fmt", "bgr24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(fps), "-i", "-",
                            "-an", "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast",
                            "-pix_fmt", "yuv420p", "-fps_mode", "cfr", str(out)],
                           stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    pivot = base[y:y + h, x:x + w].copy()
    for i in range(frames):
        phase = 2 * np.pi * i / max(frames - 1, 1)
        dx, dy = strength * np.sin(phase), strength * np.cos(phase) - strength
        mat = np.float32([[1, 0, dx], [0, 1, dy]])
        frame = cv2.warpAffine(base, mat, (WIDTH, HEIGHT), borderMode=cv2.BORDER_REFLECT)
        frame[y:y + h, x:x + w] = pivot
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    stderr = proc.stderr.read().decode(errors="replace")
    if proc.wait():
        raise RuntimeError(stderr[-3000:])
    meta = {"pivot_box": {"x": x, "y": y, "w": w, "h": h}, "depth_engine": engine,
            "strength": strength, "canvas": [WIDTH, HEIGHT]}
    out.with_suffix(".pivot.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"output": str(out), **meta}


def shutil_which(name: str) -> str:
    import shutil
    return shutil.which(name) or name


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--duration", type=float, default=5)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--strength", type=float, default=None)
    ap.add_argument("--pivot-box", default="auto")
    a = ap.parse_args(argv)
    animate_static_image_2_5d(a.image, a.out, a.duration, a.fps, a.strength, a.pivot_box)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
