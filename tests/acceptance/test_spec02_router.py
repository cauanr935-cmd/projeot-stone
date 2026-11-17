"""SPEC_02 — ZeroCostCascadeRouter (CONTRATO)."""
from __future__ import annotations

import hashlib
import math
import struct
import time
import wave
from pathlib import Path

import httpx
import pytest

from acc_helpers import audio_stream, stream_duration


def _write_wav(path: Path, seconds: float = 1.5, freq: float = 220.0, sr: int = 16000) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * i / sr)))
                          for i in range(int(seconds * sr)))
        w.writeframes(frames)
    return path


class FakeLocalASR:
    def __init__(self):
        self.calls: list[float] = []

    async def run(self, **kwargs) -> dict:
        self.calls.append(time.perf_counter())
        return {"segments": [{"start": 0.0, "end": 1.0, "text": "olá",
                              "words": [{"word": "olá", "start": 0.1, "end": 0.6}]}]}


# ----------------------------------------------------------------------------- 1. 429 -> local
async def test_429_switches_to_local_under_500ms(tmp_path):
    from src.router.cascade_router import ZeroCostCascadeRouter

    hits = {"groq": 0, "t_429": []}

    def handler(request: httpx.Request) -> httpx.Response:
        if "groq.com" in request.url.host:
            hits["groq"] += 1
            hits["t_429"].append(time.perf_counter())
            return httpx.Response(429, headers={"x-ratelimit-remaining-requests": "0", "retry-after": "30"},
                                  json={"error": {"code": 429, "status": "RESOURCE_EXHAUSTED",
                                                  "message": "quota exceeded"}})
        return httpx.Response(503, json={"error": "unexpected host in test"})

    fake = FakeLocalASR()
    router = ZeroCostCascadeRouter(env={"GROQ_API_KEY": "test-key"}, offline=False,
                                   http_transport=httpx.MockTransport(handler),
                                   local_engines={"asr": fake}, cache_dir=tmp_path / "cache")

    r1 = await router.transcribe_with_word_timestamps(_write_wav(tmp_path / "a.wav", freq=220), lang="pt",
                                                      contains_sensitive_data=False)
    assert hits["groq"] == 1, "a Groq (tier 1) deveria ter sido tentada uma vez"
    assert fake.calls, "o tier local não foi acionado após o 429"
    switch_ms = (fake.calls[0] - hits["t_429"][0]) * 1000
    assert switch_ms < 500, f"comutação levou {switch_ms:.0f} ms (limite 500 ms)"
    assert r1["tier"] == 3 and r1["segments"], r1

    await router.transcribe_with_word_timestamps(_write_wav(tmp_path / "b.wav", freq=330), lang="pt",
                                                 contains_sensitive_data=False)
    assert hits["groq"] == 1, "circuito deveria estar aberto (retry-after=30) e não chamar a Groq de novo"
    assert len(fake.calls) == 2


# ----------------------------------------------------------------------------- 2. TTS real + cache
async def test_tts_real_mp3_srt_and_cache(tmp_path):
    import pysubs2

    from src.router.cascade_router import ZeroCostCascadeRouter

    router = ZeroCostCascadeRouter(cache_dir=tmp_path / "cache")
    text = "Olá! Hoje eu vou te mostrar como fazer um bolo de cenoura fofinho."
    mp3, srt = tmp_path / "vo.mp3", tmp_path / "vo.srt"
    r1 = await router.synthesize_ptbr_voiceover(text, mp3, srt, voice="pt-BR-FranciscaNeural", rate="+10%")
    assert r1["cache_hit"] is False
    assert mp3.exists() and mp3.stat().st_size > 1000
    a = audio_stream(mp3)
    assert a is not None and stream_duration(a) > 0.5
    assert srt.exists() and len(pysubs2.load(str(srt))) >= 1
    digest1 = hashlib.sha256(mp3.read_bytes()).hexdigest()

    mp3b, srtb = tmp_path / "vo2.mp3", tmp_path / "vo2.srt"
    r2 = await router.synthesize_ptbr_voiceover(text, mp3b, srtb, voice="pt-BR-FranciscaNeural", rate="+10%")
    assert r2["cache_hit"] is True, "segunda chamada idêntica deveria vir do cache"
    assert hashlib.sha256(mp3b.read_bytes()).hexdigest() == digest1
    assert r1["engine"] == r2["engine"]


# ----------------------------------------------------------------------------- 3. guardrail
@pytest.mark.parametrize("src", ["freesound", "elevenlabs-free", "epidemicsound-free"])
def test_blocked_sources_raise(src):
    from src.router.cascade_router import CommercialLicenseViolationError
    from src.router.license_guard import validate_commercial_sources

    with pytest.raises(CommercialLicenseViolationError):
        validate_commercial_sources(["edge-tts", src], commercial=True, env={})
    validate_commercial_sources([src], commercial=False, env={})  # não comercial: não levanta


def test_agpl_review_and_unknown():
    from src.router.license_guard import (CommercialLicenseViolationError, UnknownLicenseError,
                                          validate_commercial_sources)

    with pytest.raises(CommercialLicenseViolationError):
        validate_commercial_sources(["ultralytics-yolo11"], commercial=True, env={})
    validate_commercial_sources(["ultralytics-yolo11"], commercial=True, env={"REELS_ALLOW_AGPL": "1"})
    warnings = validate_commercial_sources(["edge-tts"], commercial=True, env={})
    assert warnings, "edge-tts é 'review' e deveria gerar aviso"
    with pytest.raises(UnknownLicenseError):
        validate_commercial_sources(["fonte-inventada-xyz"], commercial=True, env={})


# ----------------------------------------------------------------------------- 4. privacidade
async def test_sensitive_data_never_reaches_training_provider(tmp_path):
    from src.router.cascade_router import ZeroCostCascadeRouter

    hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        if "generativelanguage.googleapis.com" in request.url.host:
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "roteiro gemini"}]}}]})
        return httpx.Response(503, json={"error": "indisponível no teste"})

    router = ZeroCostCascadeRouter(env={"GEMINI_API_KEY": "test-key"}, offline=False,
                                   http_transport=httpx.MockTransport(handler), cache_dir=tmp_path / "c1")
    r = await router.complete_text("Escreva um gancho para um bolo.", contains_sensitive_data=True)
    assert not any("generativelanguage" in h for h in hosts), f"dado sensível enviado ao Gemini: {hosts}"
    assert r["provider"] != "gemini_flash"

    hosts.clear()
    router2 = ZeroCostCascadeRouter(env={"GEMINI_API_KEY": "test-key"}, offline=False,
                                    http_transport=httpx.MockTransport(handler), cache_dir=tmp_path / "c2")
    r2 = await router2.complete_text("Escreva um gancho para um bolo.", contains_sensitive_data=False)
    assert any("generativelanguage" in h for h in hosts), "sem dado sensível, o Gemini deveria ser usado"
    assert r2["text"] == "roteiro gemini"
