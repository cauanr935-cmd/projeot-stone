from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def auto_reframe_vertical_9_16(input_path: Path, output_path: Path, preset: str = "talking_head") -> dict:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-nostats", "-y",
                        "-i", str(input_path), "-vf",
                        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-ar", "48000", "-fps_mode", "cfr", str(output_path)],
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-3000:])
    return {"output": str(output_path), "strategy": "CENTER", "preset": preset}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--preset", default="talking_head")
    a = ap.parse_args(argv)
    auto_reframe_vertical_9_16(a.input, a.out, a.preset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
