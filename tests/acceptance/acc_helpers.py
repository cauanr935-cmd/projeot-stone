"""Helpers compartilhados dos testes de aceitação (CONTRATO — não enfraquecer).

Os helpers usam ffmpeg/ffprobe diretamente e leem config/*.yaml sem passar pelo
código do projeto, para que a verificação seja independente da implementação.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import wave
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
PY = sys.executable

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# --------------------------------------------------------------------------- binários
def _resolve_bin(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    try:  # fallback previsto na SPEC_00
        import static_ffmpeg  # type: ignore

        static_ffmpeg.add_paths()
        found = shutil.which(name)
        if found:
            return found
    except Exception:
        pass
    pytest.fail(f"binário '{name}' não encontrado (SPEC_00 deveria resolvê-lo)")


FFMPEG = None
FFPROBE = None


def ffmpeg_bin() -> str:
    global FFMPEG
    FFMPEG = FFMPEG or _resolve_bin("ffmpeg")
    return FFMPEG


def ffprobe_bin() -> str:
    global FFPROBE
    FFPROBE = FFPROBE or _resolve_bin("ffprobe")
    return FFPROBE


# --------------------------------------------------------------------------- execução
def project_env(**overrides: str) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}"
    env.setdefault("REELS_WORKSPACE", str(ROOT / "workspace"))
    env.update({k: str(v) for k, v in overrides.items()})
    return env


def run(args: list[str], *, timeout: int = 900, input: str | None = None, env: dict | None = None,
        check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                          input=input, env=env or project_env())
    if check and proc.returncode != 0:
        raise AssertionError(
            f"comando falhou ({proc.returncode}): {' '.join(map(str, args))}\n"
            f"--- stdout ---\n{proc.stdout[-4000:]}\n--- stderr ---\n{proc.stderr[-4000:]}")
    return proc


# --------------------------------------------------------------------------- ffprobe
def ffprobe_json(path: Path, count_frames: bool = False) -> dict:
    extra = ["-count_frames"] if count_frames else []
    out = subprocess.run([ffprobe_bin(), "-v", "error", "-show_streams", "-show_format",
                          *extra, "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def video_stream(path: Path, count_frames: bool = False) -> dict:
    info = ffprobe_json(path, count_frames=count_frames)
    vs = [s for s in info["streams"] if s.get("codec_type") == "video"]
    assert vs, f"{path} sem stream de vídeo"
    return vs[0]


def audio_stream(path: Path) -> dict | None:
    info = ffprobe_json(path)
    a = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    return a[0] if a else None


def duration_s(path: Path) -> float:
    return float(ffprobe_json(path)["format"]["duration"])


def stream_duration(stream: dict) -> float:
    if stream.get("duration") not in (None, "N/A"):
        return float(stream["duration"])
    tags = stream.get("tags", {})
    if "DURATION" in tags:
        h, m, s = tags["DURATION"].split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    raise AssertionError("stream sem duração")


def is_cfr(stream: dict) -> bool:
    return Fraction(stream["r_frame_rate"]) == Fraction(stream["avg_frame_rate"])


def nb_frames(stream: dict) -> int:
    for key in ("nb_read_frames", "nb_frames"):
        v = stream.get(key)
        if v not in (None, "N/A"):
            return int(v)
    raise AssertionError("não foi possível contar frames")


# --------------------------------------------------------------------------- áudio
def decode_mono_wav(path: Path, sr: int = 48000) -> np.ndarray:
    tmp = Path(str(path) + f".{sr}.mono.wav")
    subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-y", "-i", str(path), "-vn",
                    "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", str(tmp)],
                   capture_output=True, check=True)
    with wave.open(str(tmp), "rb") as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    tmp.unlink(missing_ok=True)
    return data


def integrated_lufs(path: Path) -> float:
    proc = subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-i", str(path),
                           "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                          capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+)\s+LUFS", proc.stderr)
    assert m, f"ebur128 sem leitura para {path}"
    return float(m[-1])


def silences(path: Path, noise_db: int = -32, d: float = 0.4) -> list[tuple[float, float]]:
    proc = subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-vn", "-i", str(path),
                           "-af", f"silencedetect=noise={noise_db}dB:d={d}", "-f", "null", "-"],
                          capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", proc.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", proc.stderr)]
    return list(zip(starts, ends))


# --------------------------------------------------------------------------- frames
def extract_gray_frame(path: Path, index: int, out_png: Path) -> np.ndarray:
    from PIL import Image

    subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-y", "-i", str(path),
                    "-vf", f"select=eq(n\\,{index})", "-vframes", "1", str(out_png)],
                   capture_output=True, check=True)
    return np.asarray(Image.open(out_png).convert("L"), dtype=np.float64)


def extract_gray_frames_every(path: Path, step: int, out_dir: Path) -> list[np.ndarray]:
    """Extrai 1 a cada `step` frames numa única decodificação."""
    from PIL import Image

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("fr_*.png"):
        old.unlink()
    subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-y", "-i", str(path),
                    "-vf", f"select=not(mod(n\\,{step}))", "-fps_mode", "passthrough",
                    str(out_dir / "fr_%05d.png")], capture_output=True, check=True)
    return [np.asarray(Image.open(p).convert("L"), dtype=np.float64) for p in sorted(out_dir.glob("fr_*.png"))]


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    try:
        from skimage.metrics import structural_similarity

        return float(structural_similarity(a, b, data_range=255.0))
    except ImportError:  # implementação de referência (janela global gaussiana simplificada)
        c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
        mu_a, mu_b = a.mean(), b.mean()
        va, vb = a.var(), b.var()
        cov = ((a - mu_a) * (b - mu_b)).mean()
        return float(((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / ((mu_a**2 + mu_b**2 + c1) * (va + vb + c2)))


# --------------------------------------------------------------------------- config
def load_yaml(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / name).read_text(encoding="utf-8"))


def formats_by_id() -> dict[int, dict]:
    return {f["id"]: f for f in load_yaml("formats.yaml")["formats"]}


# Tabela da pesquisa, fixada aqui de propósito (não lida do YAML) para detectar
# alteração indevida de config/formats.yaml.
RESEARCH_TABLE = {
    1: dict(segments=[(0, 8), (8, 20), (20, 27), (27, 30)], voice="pt-BR-FranciscaNeural",
            cut_style="seamless", cuts=0.517, window=(28, 30), loop=False, animation="parallax_2_5d",
            preset="talking_head"),
    2: dict(segments=[(0, 5), (5, 18), (18, 24), (24, 30)], voice="pt-BR-ThalitaMultilingualNeural",
            cut_style="seamless", cuts=0.331, window=(15, 30), loop=False, animation="parallax_2_5d",
            preset="movie", parallax_strength=10),
    3: dict(segments=[(0, 4), (4, 12), (12, 22), (22, 30)], voice="pt-BR-ThalitaMultilingualNeural",
            cut_style="seamless", cuts=0.331, window=(21, 35), loop=False, animation="optical_flow_morph",
            preset="talking_head"),
    4: dict(segments=[(0, 5), (5, 18), (18, 25), (25, 30)], voice="pt-BR-AntonioNeural",
            cut_style="overlapping", cuts=0.331, window=(20, 30), loop=False, animation="parallax_2_5d",
            preset="cars"),
    5: dict(segments=[(0, 5), (5, 18), (18, 35), (35, 45)], voice="pt-BR-FranciscaNeural",
            cut_style="seamless", cuts=0.331, window=(35, 45), loop=True, animation="parallax_2_5d",
            preset="talking_head"),
}
PADS = {"seamless": 0.090, "overlapping": 0.015}
CANONICAL_CNAE = {1: "9602-5/01", 2: "5620-1/04", 3: "4781-4/00", 4: "4321-5/00", 5: "8599-6/99"}


