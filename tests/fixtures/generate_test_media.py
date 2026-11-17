#!/usr/bin/env python3
"""Generate deterministic, non-commercial media for acceptance and local demos."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]


def _ffmpeg() -> str:
    return shutil.which("ffmpeg") or "ffmpeg"


def _make_product(path: Path, size: tuple[int, int], angle: float, shift: float) -> None:
    w, h = size
    rng = np.random.default_rng(42 + w)
    yy, xx = np.mgrid[0:h, 0:w]
    grad = np.zeros((h, w, 3), dtype=np.uint8)
    grad[:, :, 0] = np.clip(223 - yy * 0.035 + rng.normal(0, 7, (h, w)), 0, 255)
    grad[:, :, 1] = np.clip(197 - yy * 0.025 + rng.normal(0, 7, (h, w)), 0, 255)
    grad[:, :, 2] = np.clip(165 - yy * 0.018 + rng.normal(0, 7, (h, w)), 0, 255)
    im = Image.fromarray(grad, "RGB").filter(ImageFilter.GaussianBlur(0.35))
    d = ImageDraw.Draw(im)
    cx = int(w * (0.50 + shift))
    cy = int(h * 0.51)
    bw, bh = int(min(w, h) * 0.48), int(min(w, h) * 0.68)
    box = Image.new("RGBA", (bw, bh), (250, 246, 232, 255))
    bd = ImageDraw.Draw(box)
    bd.rounded_rectangle((4, 4, bw - 5, bh - 5), radius=max(12, bw // 12),
                         fill=(247, 239, 218), outline=(90, 70, 50), width=7)
    bd.rounded_rectangle((bw * .12, bh * .18, bw * .88, bh * .82), radius=20,
                         fill=(190, 62, 47), outline=(120, 35, 29), width=5)
    font_candidates = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    font_path = next((p for p in font_candidates if Path(p).exists()), None)
    font = ImageFont.truetype(font_path, max(20, bw // 12)) if font_path else ImageFont.load_default()
    bd.text((bw * .2, bh * .43), "IMPULSO", fill="white", font=font, stroke_width=1)
    box = box.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    im.paste(box, (cx - box.width // 2, cy - box.height // 2), box)
    d = ImageDraw.Draw(im)
    radius = int(min(w, h) * .045)
    d.ellipse((cx + bw // 4 - radius, cy - bh // 3 - radius,
               cx + bw // 4 + radius, cy - bh // 3 + radius),
              fill=(238, 189, 58), outline=(104, 67, 25), width=5)
    im.save(path, quality=94, subsampling=0)


def _make_audio(path: Path, duration: float = 24.0) -> list[list[float]]:
    sr = 48000
    segments = [[1.0, 3.2], [5.0, 7.4], [9.0, 11.6], [13.2, 15.5], [17.0, 19.8], [21.0, 23.2]]
    t = np.arange(round(duration * sr), dtype=np.float64) / sr
    x = np.zeros_like(t)
    for start, end in segments:
        m = (t >= start) & (t < end)
        tm = t[m]
        amp = 0.16 * (0.8 + 0.2 * np.sin(2 * np.pi * 4 * tm))
        x[m] = amp * (np.sin(2 * np.pi * 165 * tm) + .35 * np.sin(2 * np.pi * 330 * tm)
                      + .15 * np.sin(2 * np.pi * 495 * tm))
    pcm = (np.clip(x, -0.99, .99) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return segments


def generate(out_dir: Path, force: bool = False) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    names = ["sample_raw.mp4", "img_1.jpg", "img_2.jpg", "img_3.jpg"]
    manifest_path = out_dir / "manifest.json"
    if not force and manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if all((out_dir / n).exists() and old.get("sha256", {}).get(n) ==
               hashlib.sha256((out_dir / n).read_bytes()).hexdigest() for n in names):
            return old

    _make_product(out_dir / "img_1.jpg", (1200, 1600), 0, 0)
    _make_product(out_dir / "img_2.jpg", (1600, 1200), -8, .08)
    _make_product(out_dir / "img_3.jpg", (1080, 1080), 5, -.04)
    audio = out_dir / "synthetic_speech.wav"
    speech = _make_audio(audio)
    video = out_dir / "sample_raw.mp4"
    cmd = [_ffmpeg(), "-hide_banner", "-nostats", "-y", "-f", "lavfi", "-i",
           "testsrc2=size=1920x1080:rate=30:duration=24", "-i", str(audio),
           "-vf", "hue=h='if(lt(mod(t,8),4),0,100)':s=1,select='not(mod(n,5))'",
           "-fps_mode", "vfr", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
           "-shortest", str(video)]
    subprocess.run(cmd, capture_output=True, check=True)
    audio.unlink(missing_ok=True)
    mixed = out_dir / "mixed"
    mixed.mkdir(exist_ok=True)
    for name in ("sample_raw.mp4", "img_1.jpg", "img_2.jpg"):
        shutil.copy2(out_dir / name, mixed / name)
    data = {"sha256": {name: hashlib.sha256((out_dir / name).read_bytes()).hexdigest() for name in names},
            "speech_segments": speech,
            "silences": [[speech[i][1], speech[i + 1][0]] for i in range(len(speech) - 1)]}
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    generate(args.out_dir, args.force)
    print(f"Fixtures prontos em {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
