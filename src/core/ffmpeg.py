from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def resolve_binaries() -> dict[str, str]:
    found = {name: shutil.which(name) or "" for name in ("ffmpeg", "ffprobe")}
    if not all(found.values()):
        try:
            import static_ffmpeg

            static_ffmpeg.add_paths()
        except Exception:
            pass
        found = {name: found[name] or shutil.which(name) or "" for name in found}
    return found


def _bin(name: str) -> str:
    path = resolve_binaries().get(name)
    if not path:
        raise FileNotFoundError(f"{name} não encontrado no PATH")
    return path


def run_ffmpeg(args: list[str], *, check: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
    cmd = [_bin("ffmpeg"), "-hide_banner", "-nostats", *map(str, args)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode:
        raise RuntimeError(f"ffmpeg falhou ({proc.returncode}): {proc.stderr[-4000:]}")
    return proc


def ffprobe_json(path: str | Path) -> dict:
    proc = subprocess.run([_bin("ffprobe"), "-v", "error", "-show_streams", "-show_format",
                           "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def _has(kind: str, name: str) -> bool:
    proc = subprocess.run([_bin("ffmpeg"), "-hide_banner", f"-{kind}"], capture_output=True, text=True)
    return any(line.split()[1:2] == [name] for line in proc.stdout.splitlines())


def has_filter(name: str) -> bool:
    return _has("filters", name)


def has_encoder(name: str) -> bool:
    proc = subprocess.run([_bin("ffmpeg"), "-hide_banner", "-encoders"], capture_output=True, text=True)
    return any(line.split()[1:2] == [name] for line in proc.stdout.splitlines())
