"""SPEC_05 — jump-cuts AST, MIR/ducking e legendas karaoke .ass (CONTRATO)."""
from __future__ import annotations

import re
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from acc_helpers import ROOT, audio_stream, decode_mono_wav, duration_s, ffmpeg_bin, stream_duration, video_stream

JOB = ROOT / "workspace" / "jobs" / "acceptance_spec05"
SR = 48000
TONE_GATES = [(0.0, 2.0), (3.0, 5.5), (6.5, 9.0), (10.2, 12.0)]  # bordas em cruzamentos de zero de 440 Hz
ROOM_TONE_RMS = 0.004  # ≈ -48 dBFS (pico gaussiano fica bem abaixo do limiar de -32 dB)


def _write_wav(path: Path, x: np.ndarray, sr: int = SR) -> Path:
    x16 = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(x16.tobytes())
    return path


def _speech_like(total: float, gates: list[tuple[float, float]], seed: int = 1) -> np.ndarray:
    t = np.arange(int(total * SR)) / SR
    rng = np.random.default_rng(seed)
    x = rng.normal(0.0, ROOM_TONE_RMS, t.size)
    for a, b in gates:
        m = (t >= a) & (t < b)
        x[m] += 0.3 * np.sin(2 * np.pi * 440 * t[m])
    return x


@pytest.fixture(scope="module")
def job():
    if JOB.exists():
        shutil.rmtree(JOB)
    JOB.mkdir(parents=True)
    return JOB


@pytest.fixture(scope="module")
def vertical_input(job) -> Path:
    wav = _write_wav(job / "speech.wav", _speech_like(12.0, TONE_GATES))
    out = job / "input_9_16.mp4"
    subprocess.run([ffmpeg_bin(), "-hide_banner", "-nostats", "-y",
                    "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=12",
                    "-i", str(wav), "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-b:a", "192k", str(out)], capture_output=True, check=True)
    return out


@pytest.fixture(scope="module")
def cuts(job, vertical_input):
    from src.editing.jumpcuts import build_ast_calibrated_jumpcuts

    res = {}
    for style in ("seamless", "overlapping"):
        res[style] = build_ast_calibrated_jumpcuts(vertical_input, job / f"cut_{style}.mp4", cut_style=style,
                                                   noise_db=-32, min_silence_dur=0.40)
    return res


# ----------------------------------------------------------------------------- jump-cuts
@pytest.mark.slow
def test_duration_shrinks(cuts, vertical_input):
    original = duration_s(vertical_input)
    seamless = duration_s(Path(cuts["seamless"]["output"]))
    overlapping = duration_s(Path(cuts["overlapping"]["output"]))
    assert seamless < original, (seamless, original)
    assert overlapping < seamless, "overlapping (PAD 0,015) deve comprimir mais que seamless (PAD 0,090)"
    assert cuts["seamless"]["pad"] == pytest.approx(0.090)
    assert cuts["overlapping"]["pad"] == pytest.approx(0.015)
    assert len(cuts["seamless"]["segments"]) == len(TONE_GATES), (
        "o trecho após o último silêncio (ou outro) foi perdido — bug da implementação de referência?")


@pytest.mark.slow
@pytest.mark.parametrize("style", ["seamless", "overlapping"])
def test_av_sync(cuts, style):
    out = Path(cuts[style]["output"])
    v = stream_duration(video_stream(out))
    a = stream_duration(audio_stream(out))
    assert abs(v - a) <= 0.040, f"{style}: vídeo {v:.3f}s vs áudio {a:.3f}s"
    vs = video_stream(out)
    assert (int(vs["width"]), int(vs["height"])) == (1080, 1920)


@pytest.mark.slow
def test_no_clicks_microfades(cuts):
    res = cuts["seamless"]
    out = Path(res["output"])
    x = decode_mono_wav(out)
    junctions = res["junctions_s"]
    assert len(junctions) == len(TONE_GATES) - 1

    def rms(a: float, b: float) -> float:
        seg = x[max(0, int(a * SR)):max(0, int(b * SR))]
        return float(np.sqrt(np.mean(seg ** 2))) if seg.size else 0.0

    for j in junctions:
        ref = rms(j - 0.080, j - 0.040)
        assert ref > 0.5 * ROOM_TONE_RMS, f"junção {j:.3f}s: janela de referência não é room tone ({ref:.4f})"
        frames = [rms(j + k * 0.002, j + (k + 1) * 0.002) for k in range(-12, 12)]
        dip = min(frames)
        assert dip < 0.5 * ref, f"junção {j:.3f}s sem micro-fade (mín {dip:.4f} vs ref {ref:.4f}) — risco de clique"


def test_pattern_interrupts():
    from src.editing.jumpcuts import plan_pattern_interrupts

    extra = plan_pattern_interrupts(30.0, 0.517, [])
    assert abs(len(extra) - 16) <= 1, len(extra)
    s = sorted(extra)
    assert all(b - a >= 1.2 - 1e-6 for a, b in zip(s, s[1:]))
    assert all(0 < t < 30 for t in s)


# ----------------------------------------------------------------------------- MIR
@pytest.mark.slow
def test_beats_on_procedural_music(job):
    from src.editing.beat_sync import extract_beats
    from src.editing.music import generate_procedural_music

    wav = job / "music120.wav"
    generate_procedural_music(wav, bpm=120, duration_s=20, seed=0)
    res = extract_beats(wav)
    bpm = res["bpm"]
    assert any(abs(bpm - t) <= tol for t, tol in ((120, 4), (60, 2), (240, 8))), bpm
    assert res["downbeats"] and set(np.round(res["downbeats"], 3)) <= set(np.round(res["beats"], 3))


@pytest.mark.slow
def test_ducking(job):
    from src.editing.beat_sync import duck_music_under_voice
    from src.editing.music import generate_procedural_music

    music = job / "music_bed.wav"
    generate_procedural_music(music, bpm=100, duration_s=12, seed=3)
    voice_gates = [(1.0, 3.0), (5.0, 7.0), (9.0, 11.0)]
    voice = _write_wav(job / "voice.wav", _speech_like(12.0, voice_gates, seed=5))
    out = job / "music_ducked.wav"
    duck_music_under_voice(music, voice, out, ducking_db=-14)
    y = decode_mono_wav(out)

    def rms_db(spans):
        parts = [y[int(a * SR):int(b * SR)] for a, b in spans]
        seg = np.concatenate(parts)
        return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)

    inside = rms_db([(a + 0.35, b - 0.1) for a, b in voice_gates])
    outside = rms_db([(3.5, 4.6), (7.5, 8.6), (11.4, 11.9)])
    assert outside - inside >= 6.0, f"ducking insuficiente: dentro {inside:.1f} dB, fora {outside:.1f} dB"


# ----------------------------------------------------------------------------- legendas
TAG = re.compile(r"\{[^}]*\}")


def _words(text: str) -> list[str]:
    return TAG.sub("", text).replace("\\N", " ").split()


def _gen(words, path, hook=None):
    from src.editing.subtitles_ass import generate_karaoke_ass_subtitles

    return generate_karaoke_ass_subtitles(words, path, hook_overlay=hook)


def _check_common(subs):
    assert int(subs.info["PlayResX"]) == 1080 and int(subs.info["PlayResY"]) == 1920
    assert "ImpulsoKaraoke" in subs.styles
    for ev in subs.events:
        assert ev.end - ev.start >= 100, f"evento de {ev.end - ev.start} ms (< 100 ms)"
        if ev.style == "ImpulsoKaraoke":
            assert len(_words(ev.text)) <= 4, ev.text
    early = {w.upper() for ev in subs.events if ev.start < 3000 for w in _words(ev.text)}
    assert len(early) <= 5, f"{len(early)} palavras distintas em 0–3 s: {early}"


def test_ass_slow_speech(tmp_path):
    import pysubs2

    vocab = "você sabe quanto custa fazer um bolo caseiro de verdade hoje aqui no bairro com carinho".split()
    words = [{"word": vocab[i % len(vocab)], "start": 1.0 + 0.5 * i, "end": 1.0 + 0.5 * i + 0.4} for i in range(24)]
    res = _gen(words, tmp_path / "slow.ass")
    subs = pysubs2.load(str(tmp_path / "slow.ass"))
    _check_common(subs)
    assert res["mode"] == "karaoke"
    assert any(r"\c&H34C9FC&" in ev.text for ev in subs.events), "palavra ativa sem destaque de cor"


def test_ass_fast_frame_zero_uses_hook(tmp_path):
    import pysubs2

    vocab = "olha essa textura saiu agora do forno quentinho e cheiroso pra você provar hoje".split()
    words = [{"word": vocab[i % len(vocab)], "start": 0.2 + 0.35 * i, "end": 0.2 + 0.35 * i + 0.3} for i in range(30)]
    res = _gen(words, tmp_path / "fast.ass", hook="Olha essa textura")
    subs = pysubs2.load(str(tmp_path / "fast.ass"))
    _check_common(subs)
    assert res["mode"] == "hook_then_karaoke"
    assert any(ev.style == "ImpulsoHook" for ev in subs.events)


def test_ass_very_fast_words_are_grouped(tmp_path):
    import pysubs2

    words = [{"word": f"p{i}", "start": 4.0 + i * 0.066, "end": 4.0 + (i + 1) * 0.066} for i in range(40)]
    _gen(words, tmp_path / "vfast.ass")
    _check_common(pysubs2.load(str(tmp_path / "vfast.ass")))
