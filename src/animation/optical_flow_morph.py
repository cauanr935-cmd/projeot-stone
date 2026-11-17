from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np

from src.animation.parallax_2_5d import HEIGHT, WIDTH, _fit, shutil_which


def morph_images(images: list[Path], output: Path, duration: float = 6, fps: int = 30, sway: bool = False) -> dict:
    if len(images) < 2:
        raise ValueError("são necessárias ao menos duas imagens")
    canvases = []
    for path in images:
        image = cv2.imread(str(path))
        if image is None:
            raise FileNotFoundError(path)
        canvases.append(_fit(image))
    count = round(duration * fps)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen([shutil_which("ffmpeg"), "-hide_banner", "-nostats", "-y", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(fps), "-i", "-",
                          "-an", "-frames:v", str(count), "-c:v", "libx264", "-preset", "veryfast",
                          "-pix_fmt", "yuv420p", "-fps_mode", "cfr", str(out)],
                         stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    spans = len(canvases) - 1
    for i in range(count):
        pos = (i / max(count - 1, 1)) * spans
        segment = min(int(pos), spans - 1)
        alpha = pos - segment
        frame = cv2.addWeighted(canvases[segment], 1 - alpha, canvases[segment + 1], alpha, 0)
        if sway:
            dx = int(4 * np.sin(i * 2 * np.pi / max(count, 1)))
            frame = cv2.warpAffine(frame, np.float32([[1, 0, dx], [0, 1, 2 * np.sin(i / 20)]]),
                                   (WIDTH, HEIGHT), borderMode=cv2.BORDER_REFLECT)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    err = p.stderr.read().decode(errors="replace")
    if p.wait():
        raise RuntimeError(err[-3000:])
    return {"output": str(out), "frames": count, "engine": "opencv_linear_morph"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", nargs="+", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--duration", type=float, default=6)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--sway", action="store_true")
    a = ap.parse_args(argv)
    morph_images(a.images, a.out, a.duration, a.fps, a.sway)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
