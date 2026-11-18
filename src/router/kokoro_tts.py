"""TTS local Kokoro-82M (Apache-2.0) via kokoro-onnx: pt-BR, custo zero, 100% offline.

Pesos: models/kokoro/kokoro-v1.0.onnx e voices-v1.0.bin (override: KOKORO_MODEL_PATH / KOKORO_VOICES_PATH).
Download: https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
"""
from __future__ import annotations

import importlib.util
import os
import re
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

VOZES = {"pt-BR-FranciscaNeural": "pf_dora", "pt-BR-ThalitaMultilingualNeural": "pf_dora",
         "pt-BR-AntonioNeural": "pm_alex"}
SR = 24000


def caminhos(env: dict | None = None) -> tuple[Path, Path]:
    e = env if env is not None else os.environ
    return (Path(e.get("KOKORO_MODEL_PATH", "models/kokoro/kokoro-v1.0.onnx")),
            Path(e.get("KOKORO_VOICES_PATH", "models/kokoro/voices-v1.0.bin")))


def disponivel(env: dict | None = None) -> bool:
    modelo, vozes = caminhos(env)
    return importlib.util.find_spec("kokoro_onnx") is not None and modelo.is_file() and vozes.is_file()


@lru_cache(maxsize=1)
def _motor(modelo: str, vozes: str):
    from kokoro_onnx import Kokoro
    return Kokoro(modelo, vozes)


def frases(texto: str, max_chars: int = 220) -> list[str]:
    """Divide por pontuação (. ! ? ;) e quebra frases longas em vírgulas: o Kokoro limita fonemas por chamada."""
    partes = [p.strip() for p in re.split(r"(?<=[.!?;])\s+", texto.strip()) if p.strip()]
    saida: list[str] = []
    for p in partes:
        while len(p) > max_chars:
            corte = p.rfind(",", 0, max_chars)
            corte = corte if corte > 40 else p.rfind(" ", 0, max_chars)
            saida.append(p[:corte + 1].strip())
            p = p[corte + 1:].strip()
        if p:
            saida.append(p)
    return saida


def velocidade(rate: str) -> float:
    m = re.fullmatch(r"([+-]?\d+)%", rate.strip())
    return max(0.5, min(1.6, 1 + int(m.group(1)) / 100)) if m else 1.0


def sintetizar(texto: str, voice: str, rate: str, wav: Path, env: dict | None = None) -> list[tuple[str, float, float]]:
    """Escreve `wav` (24 kHz mono) e devolve [(palavra, inicio_s, fim_s)] (tempos estimados por frase)."""
    modelo, vozes = caminhos(env)
    k = _motor(str(modelo), str(vozes))
    voz = VOZES.get(voice, voice if voice in ("pf_dora", "pm_alex", "pm_santa") else "pf_dora")
    pausa = np.zeros(int(SR * 0.12), dtype=np.float32)
    trechos, palavras, t = [], [], 0.0
    for frase in frases(texto):
        audio, sr = k.create(frase, voice=voz, speed=velocidade(rate), lang="pt-br")
        audio = np.asarray(audio, dtype=np.float32)
        dur = len(audio) / sr
        ws = frase.split()
        peso = [max(len(w), 2) for w in ws]
        cursor = t
        for w, p in zip(ws, peso):
            fim = cursor + dur * p / sum(peso)
            palavras.append((w, cursor, fim))
            cursor = fim
        trechos += [audio, pausa]
        t += dur + len(pausa) / SR
    if not trechos:
        raise ValueError("texto vazio")
    pcm = np.clip(np.concatenate(trechos), -1, 1)
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((pcm * 32767).astype("<i2").tobytes())
    return palavras
