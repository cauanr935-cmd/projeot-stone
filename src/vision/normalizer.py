from src.vision.pipeline import analyze_video


def normalize_video(input_path, output_path, fps: int = 30):
    from pathlib import Path
    import subprocess
    import shutil

    p = subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-nostats", "-y",
                        "-i", str(input_path), "-vf", f"fps={fps}",
                        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-ar", "48000", str(output_path)], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-3000:])
    return {"output": str(Path(output_path).resolve())}
