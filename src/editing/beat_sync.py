from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np


def _read_audio(path: Path, sr: int = 48000) -> tuple[np.ndarray, int]:
    path = Path(path)
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as w:
            rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
            raw = w.readframes(w.getnframes())
        if width == 2:
            audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
        elif width == 4:
            audio = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648
        else:
            audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        if rate != sr:
            indices = np.linspace(0, len(audio) - 1, round(len(audio) * sr / rate)).astype(int)
            audio = audio[indices]
        return audio.astype(np.float32), sr
    proc = subprocess.run([shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
                           "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                          capture_output=True, check=True)
    return np.frombuffer(proc.stdout, dtype="<f4"), sr


def extract_beats(audio_path: Path) -> dict:
    audio, sr = _read_audio(Path(audio_path))
    hop = int(sr * .01)
    padded = np.pad(audio, (0, (-len(audio)) % hop))
    rms = np.sqrt(np.mean(padded.reshape(-1, hop) ** 2, axis=1))
    # Procedural percussion has sharp transients; peak spacing is more stable
    # than a learned tempo model for the offline acceptance fallback.
    peaks = []
    threshold = max(float(rms.max()) * .16, float(np.median(rms)) * 2)
    last = -100
    for i in range(1, len(rms) - 1):
        if rms[i] >= threshold and rms[i] >= rms[i - 1] and rms[i] >= rms[i + 1] and i - last >= 20:
            peaks.append(i * .01)
            last = i
    intervals = np.diff(peaks)
    intervals = intervals[(intervals >= .25) & (intervals <= 1.0)]
    interval = float(np.median(intervals)) if len(intervals) else .5
    bpm = 60 / interval if interval else 120
    bpm = min(240, max(60, bpm))
    beats = peaks or list(np.arange(0, len(audio) / sr, 60 / bpm))
    downbeats = beats[::4]
    return {"bpm": float(bpm), "beats": [round(float(x), 3) for x in beats],
            "downbeats": [round(float(x), 3) for x in downbeats], "engine": "local_onset_fallback"}


def select_high_energy_start(audio_path: Path, segment_s: float) -> float:
    """Choose the start of the highest-average-energy window in a soundtrack."""
    audio, sr = _read_audio(Path(audio_path))
    window_samples = round(segment_s * sr)
    if window_samples <= 0 or len(audio) <= window_samples:
        return 0.0
    frame_samples = max(1, round(sr * 0.1))
    frame_count = len(audio) // frame_samples
    rms_input = audio[:frame_count * frame_samples].reshape(frame_count, frame_samples)
    energy = np.mean(rms_input ** 2, axis=1)
    window_frames = max(1, round(segment_s / 0.1))
    if len(energy) <= window_frames:
        return 0.0
    cumulative = np.concatenate(([0.0], np.cumsum(energy, dtype=np.float64)))
    scores = cumulative[window_frames:] - cumulative[:-window_frames]
    return round(float(np.argmax(scores)) * 0.1, 3)


def snap_to_beats(times_s: list[float], beats_s: list[float], max_shift_s: float = .12) -> list[float]:
    beats = np.asarray(beats_s, dtype=float)
    out = []
    for t in times_s:
        if not len(beats):
            out.append(t)
            continue
        nearest = float(beats[np.argmin(np.abs(beats - t))])
        out.append(nearest if abs(nearest - t) <= max_shift_s else t)
    return out


def duck_music_under_voice(music_path: Path, voice_path: Path, out_music_path: Path,
                           ducking_db: float = -14) -> dict:
    music, sr = _read_audio(Path(music_path))
    voice, _ = _read_audio(Path(voice_path), sr)
    n = min(len(music), len(voice))
    if len(music) < len(voice):
        music = np.pad(music, (0, len(voice) - len(music)))
        n = len(voice)
    if len(voice) < len(music):
        voice = np.pad(voice, (0, len(music) - len(voice)))
    frame = max(1, round(sr * .01))
    padded = np.pad(voice[:n], (0, (-n) % frame))
    active = np.sqrt(np.mean(padded.reshape(-1, frame) ** 2, axis=1)) > .025
    mask = np.repeat(active, frame)[:n].astype(float)
    # Smooth control envelope: ~50 ms attack and 200 ms release.
    attack, release = max(1, round(.05 * sr)), max(1, round(.20 * sr))
    smooth = mask.copy()
    value = 0.0
    for i, target in enumerate(mask):
        alpha = 1 / (attack if target > value else release)
        value += (target - value) * alpha
        smooth[i] = value
    gain = 10 ** (ducking_db / 20)
    envelope = 1 - smooth * (1 - gain)
    output = np.clip(music[:n] * envelope, -.99, .99)
    out = Path(out_music_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((output * 32767).astype("<i2").tobytes())
    return {"output": str(out), "ducking_db": ducking_db, "engine": "rms_envelope"}
