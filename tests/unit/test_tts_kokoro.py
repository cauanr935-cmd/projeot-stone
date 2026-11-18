import asyncio

import pytest

from src.router import kokoro_tts
from src.router.cascade_router import ZeroCostCascadeRouter


def test_frases_e_velocidade():
    assert kokoro_tts.frases("Oi! Tudo bem? Sim; claro.") == ["Oi!", "Tudo bem?", "Sim;", "claro."]
    assert all(len(f) <= 220 for f in kokoro_tts.frases("palavra, " * 80))
    assert kokoro_tts.velocidade("+10%") == pytest.approx(1.1) and kokoro_tts.velocidade("x") == 1.0


def test_edge_tts_desligado_por_padrao(monkeypatch):
    monkeypatch.setattr(kokoro_tts, "disponivel", lambda env=None: False)
    r = ZeroCostCascadeRouter(env={}, offline=False)
    assert r.effective_tts_engine == "placeholder_tone"  # sem opt-in, nunca chama o serviço Microsoft


def test_edge_tts_so_com_optin(monkeypatch):
    monkeypatch.setattr(kokoro_tts, "disponivel", lambda env=None: False)
    r = ZeroCostCascadeRouter(env={"ALLOW_NONCOMMERCIAL_EDGE_TTS": "1"}, offline=False)
    assert r.effective_tts_engine in ("edge-tts", "placeholder_tone")
    assert ZeroCostCascadeRouter(env={"ALLOW_NONCOMMERCIAL_EDGE_TTS": "1"}, offline=True
                                 ).effective_tts_engine == "placeholder_tone"


@pytest.mark.skipif(not kokoro_tts.disponivel(), reason="pesos Kokoro (gitignored) ausentes")
def test_kokoro_sintese_real(tmp_path):
    from src.core.ffmpeg import ffprobe_json
    r = ZeroCostCascadeRouter(env={}, offline=True, cache_dir=tmp_path / "c")
    assert r.effective_tts_engine == "kokoro"
    mp3, srt = tmp_path / "v.mp3", tmp_path / "v.srt"
    info = asyncio.run(r.synthesize_ptbr_voiceover("Olá! Esta é uma voz local, gratuita.", mp3, srt))
    assert info["engine"] == "kokoro" and info["tier"] == 3
    assert float(ffprobe_json(mp3)["format"]["duration"]) > 1.0 and srt.read_text().count("-->") >= 6
