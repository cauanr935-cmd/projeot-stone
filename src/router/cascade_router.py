from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import time
import wave
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from src.router import kokoro_tts
from src.router.license_guard import CommercialLicenseViolationError, UnknownLicenseError


class ZeroCostCascadeRouter:
    def __init__(self, env: dict[str, str] | None = None, offline: bool | None = None,
                 http_transport: httpx.AsyncBaseTransport | None = None,
                 local_engines: dict[str, Any] | None = None, cache_dir: Path | None = None):
        self.env = env if env is not None else os.environ
        self.offline = (self.env.get("REELS_OFFLINE", "0") == "1") if offline is None else offline
        self.transport = http_transport
        self.local_engines = local_engines or {}
        self.cache_dir = Path(cache_dir or ".cache/router").resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._blocked_until: dict[str, float] = {}
        self._tts_cache: dict[str, tuple[bytes, bytes, dict]] = {}
        # Ordem (custo zero + licença comercial): Kokoro local (Apache-2.0) > edge-tts (só com opt-in explícito,
        # uso comercial não autorizado pela Microsoft sem Azure; ADR-010) > placeholder de CI.
        allow_edge = self.env.get("ALLOW_NONCOMMERCIAL_EDGE_TTS", "0") == "1"
        if kokoro_tts.disponivel(self.env):
            self.effective_tts_engine = "kokoro"
        elif allow_edge and not self.offline and importlib.util.find_spec("edge_tts") is not None:
            self.effective_tts_engine = "edge-tts"
        else:
            self.effective_tts_engine = "placeholder_tone"
        self.last_engines = {"asr": "none", "tts": "placeholder_tone", "llm": "template_engine",
                             "vlm": "heuristic_only", "music": "procedural_generator",
                             "depth": "geometric", "subject_detection": "opencv_saliency"}

    async def transcribe_with_word_timestamps(self, audio_path: Path, lang: str = "pt",
                                               contains_sensitive_data: bool = True) -> dict:
        audio_path = Path(audio_path)
        key = self.env.get("GROQ_API_KEY")
        if key and not self.offline and time.monotonic() >= self._blocked_until.get("groq", 0):
            try:
                timeout = httpx.Timeout(30)
                async with httpx.AsyncClient(transport=self.transport, timeout=timeout) as client:
                    with audio_path.open("rb") as f:
                        res = await client.post("https://api.groq.com/openai/v1/audio/transcriptions",
                                                headers={"Authorization": f"Bearer {key}"},
                                                data={"model": "whisper-large-v3-turbo", "language": lang},
                                                files={"file": (audio_path.name, f, "audio/wav")})
                if res.status_code == 429:
                    self._blocked_until["groq"] = time.monotonic() + float(res.headers.get("retry-after", "30"))
                elif res.is_success:
                    payload = res.json()
                    result = {"segments": payload.get("segments", []), "tier": 1, "provider": "groq"}
                    self.last_engines["asr"] = "groq_whisper"
                    return result
            except Exception:
                pass
        local = self.local_engines.get("asr")
        if local:
            result = await local.run(audio_path=audio_path, lang=lang)
            result.update({"tier": 3, "provider": "local"})
            self.last_engines["asr"] = "local"
            return result
        return {"segments": [], "tier": 3, "provider": "none", "warning": "ASR local indisponível"}

    @staticmethod
    def _render_tone(text: str, mp3: Path, srt: Path) -> None:
        words = re.findall(r"\S+", text)
        duration = max(1.0, min(25.0, len(words) * 0.32))
        sr = 24000
        total = round(duration * sr)
        t = np.arange(total) / sr
        audio = np.zeros(total, dtype=np.float64)
        per_word = duration / max(1, len(words))
        for i in range(len(words)):
            start = int(i * per_word * sr)
            end = min(total, int((i + 1) * per_word * sr))
            if end <= start:
                continue
            local_t = np.arange(end - start) / sr
            envelope = np.minimum(1, local_t * 20) * np.minimum(1, (end - start - np.arange(end - start)) / (sr * .02))
            freq = 175 + (i % 5) * 23
            audio[start:end] += 0.20 * envelope * (np.sin(2 * np.pi * freq * local_t) +
                                                       0.35 * np.sin(2 * np.pi * freq * 2 * local_t))
        wav = mp3.with_suffix(".wav")
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((np.clip(audio, -.95, .95) * 32767).astype("<i2").tobytes())
        proc = subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-nostats", "-y",
                               "-i", str(wav), "-codec:a", "libmp3lame", "-b:a", "128k", str(mp3)],
                              capture_output=True, text=True)
        wav.unlink(missing_ok=True)
        if proc.returncode:
            raise RuntimeError(proc.stderr[-2000:])
        lines = []
        for i, word in enumerate(words):
            st, en = i * per_word, min(duration, (i + 1) * per_word)
            def stamp(s: float) -> str:
                ms = round(s * 1000)
                return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
            lines.extend([str(i + 1), f"{stamp(st)} --> {stamp(max(st + .1, en))}", word, ""])
        srt.write_text("\n".join(lines), encoding="utf-8")

    async def synthesize_ptbr_voiceover(self, text: str, mp3_path: Path, srt_path: Path,
                                        voice: str = "pt-BR-FranciscaNeural", rate: str = "+0%") -> dict:
        mp3_path, srt_path = Path(mp3_path), Path(srt_path)
        mp3_path.parent.mkdir(parents=True, exist_ok=True)
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        engine = self.effective_tts_engine
        cache_key = hashlib.sha256(json.dumps([text, voice, rate, engine], ensure_ascii=False).encode()).hexdigest()
        if cache_key in self._tts_cache:
            audio, subtitles, info = self._tts_cache[cache_key]
            mp3_path.write_bytes(audio)
            srt_path.write_bytes(subtitles)
            return {**info, "cache_hit": True}
        temp = self.cache_dir / f"{cache_key}.mp3"
        temp_srt = self.cache_dir / f"{cache_key}.srt"
        if not temp.exists() or not temp_srt.exists():
            generated = False
            if engine == "kokoro":
                try:
                    wav = temp.with_suffix(".kokoro.wav")
                    palavras = await asyncio.to_thread(kokoro_tts.sintetizar, text, voice, rate, wav, self.env)
                    proc = subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-nostats", "-y", "-i",
                                           str(wav), "-codec:a", "libmp3lame", "-b:a", "128k", str(temp)],
                                          capture_output=True, text=True)
                    wav.unlink(missing_ok=True)
                    if proc.returncode:
                        raise RuntimeError(proc.stderr[-500:])
                    def stamp(sec: float) -> str:
                        ms = round(sec * 1000)
                        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
                    temp_srt.write_text("\n".join(
                        f"{i}\n{stamp(a)} --> {stamp(max(a + .1, b))}\n{w}\n" for i, (w, a, b) in enumerate(palavras, 1)),
                        encoding="utf-8")
                    generated = True
                except Exception:
                    engine = "placeholder_tone"
            elif engine == "edge-tts":
                try:
                    import edge_tts
                    communicate = edge_tts.Communicate(text, voice, rate=rate)
                    audio_chunks, boundaries = [], []
                    async for chunk in communicate.stream():
                        if chunk.get("type") == "audio":
                            audio_chunks.append(chunk["data"])
                        elif chunk.get("type") == "WordBoundary":
                            boundaries.append(chunk)
                    if audio_chunks:
                        temp.write_bytes(b"".join(audio_chunks))
                        lines = []
                        for i, boundary in enumerate(boundaries, 1):
                            start = int(boundary["offset"] / 10_000)
                            end = int((boundary["offset"] + boundary["duration"]) / 10_000)
                            def stamp(ms: int) -> str:
                                return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
                            lines.extend([str(i), f"{stamp(start)} --> {stamp(max(start + 100, end))}",
                                          boundary["text"], ""])
                        temp_srt.write_text("\n".join(lines), encoding="utf-8")
                        generated = True
                except Exception:
                    engine = "placeholder_tone"
            if not generated:
                self._render_tone(text, temp, temp_srt)
        audio, subtitles = temp.read_bytes(), temp_srt.read_bytes()
        mp3_path.write_bytes(audio)
        srt_path.write_bytes(subtitles)
        tier = {"edge-tts": 1, "kokoro": 3}.get(engine, 5)
        info = {"engine": engine, "tier": tier}
        self._tts_cache[cache_key] = (audio, subtitles, info)
        self.last_engines["tts"] = engine
        return {**info, "cache_hit": False}

    async def complete_text(self, prompt: str, json_mode: bool = False,
                            contains_sensitive_data: bool = True, **_: Any) -> dict:
        key = self.env.get("GEMINI_API_KEY")
        if key and not self.offline and not contains_sensitive_data:
            try:
                model = "gemini-3.5-flash-lite"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                async with httpx.AsyncClient(transport=self.transport, timeout=8) as client:
                    response = await client.post(url + f"?key={key}",
                        json={"contents": [{"parts": [{"text": prompt}]}]})
                if response.is_success:
                    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                    self.last_engines["llm"] = "gemini_flash"
                    return {"text": text, "provider": "gemini_flash", "tier": 1}
            except Exception:
                pass
        self.last_engines["llm"] = "template_engine"
        return {"text": None, "provider": "template_engine", "tier": 4}
