"""Transcrição de fala PT-BR → texto (só o texto importa: o pedido vira briefing). 100% local, custo zero.

Motor: faster-whisper (modelo `small` por padrão; `CRIATIVOS_WHISPER_MODEL` troca, ex.: `base` mais rápido, `medium` mais preciso).
O áudio do navegador (webm/ogg/mp4/wav) é convertido por ffmpeg para WAV 16 kHz mono. O áudio é apagado após a transcrição
e nunca sai da máquina. `PEDIDO_PROMPT` ajuda o modelo com vocabulário do domínio (MEI, Reels, WhatsApp...).
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
from pathlib import Path

log = logging.getLogger("criativos.transcricao")
PEDIDO_PROMPT = "Pedido de um microempreendedor para criar um Reel: negócio, produto, preço, promoção, WhatsApp, Instagram."
MAX_BYTES = 25 * 1024 * 1024
_MODELO = None
_LOCK = threading.Lock()


def _modelo():
    global _MODELO
    with _LOCK:
        if _MODELO is None:
            from faster_whisper import WhisperModel
            nome = os.getenv("CRIATIVOS_WHISPER_MODEL", "small")
            try:
                _MODELO = WhisperModel(nome, device="cpu", compute_type="int8", local_files_only=True)
            except Exception:
                log.info("modelo whisper '%s' não está em cache; baixando uma vez", nome)
                _MODELO = WhisperModel(nome, device="cpu", compute_type="int8")
        return _MODELO


def para_wav(origem: Path, destino: Path) -> None:
    from src.core.ffmpeg import run_ffmpeg
    run_ffmpeg(["-y", "-i", str(origem), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destino)])


def transcrever_arquivo(caminho: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="trans_") as tmp:
        wav = Path(tmp) / "fala.wav"
        para_wav(Path(caminho), wav)
        import wave
        import numpy as np
        with wave.open(str(wav), "rb") as w:  # decodificação própria: evita decode_audio (incompatível com alguns PyAV)
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        segs, info = _modelo().transcribe(audio, language="pt", vad_filter=True, beam_size=5,
                                          initial_prompt=PEDIDO_PROMPT, condition_on_previous_text=False)
        texto = " ".join(s.text.strip() for s in segs).strip()
    return {"texto": texto, "duracao_s": round(info.duration, 1), "idioma": info.language}


def transcrever_com_tempos(caminho: Path) -> dict:
    """Como transcrever_arquivo, mas com início/fim por frase e por palavra (para sincronizar cenas e legenda)."""
    with tempfile.TemporaryDirectory(prefix="trans_") as tmp:
        wav = Path(tmp) / "fala.wav"
        para_wav(Path(caminho), wav)
        import wave
        import numpy as np
        with wave.open(str(wav), "rb") as w:
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        segs, info = _modelo().transcribe(audio, language="pt", vad_filter=True, beam_size=5, word_timestamps=True,
                                          initial_prompt=PEDIDO_PROMPT, condition_on_previous_text=False)
        frases = [{"inicio": round(s.start, 2), "fim": round(s.end, 2), "texto": s.text.strip(),
                   "palavras": [{"p": w.word.strip(), "i": round(w.start, 2), "f": round(w.end, 2)} for w in (s.words or [])]}
                  for s in segs]
    return {"duracao_s": round(info.duration, 1), "frases": frases, "texto": " ".join(f["texto"] for f in frases)}


def transcrever_bytes(dados: bytes, sufixo: str = ".webm") -> dict:
    if not dados or len(dados) > MAX_BYTES:
        raise ValueError("Áudio vazio ou maior que 25 MB.")
    if sufixo not in {".webm", ".ogg", ".mp4", ".m4a", ".wav", ".mp3", ".oga"}:
        sufixo = ".webm"
    with tempfile.TemporaryDirectory(prefix="fala_") as tmp:
        f = Path(tmp) / f"entrada{sufixo}"
        f.write_bytes(dados)
        try:
            return transcrever_arquivo(f)
        except subprocess.CalledProcessError as exc:
            raise ValueError("Não consegui ler o áudio. Tente gravar de novo.") from exc
