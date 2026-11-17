from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np


def generate_procedural_music(out_wav: Path, bpm: int = 120, duration_s: float = 45,
                              seed: int = 0) -> dict:
    if bpm <= 0 or duration_s <= 0:
        raise ValueError("bpm e duração devem ser positivos")
    sr = 48000
    count = round(duration_s * sr)
    audio = np.zeros(count, dtype=np.float64)
    beat_len = 60.0 / bpm
    rng = np.random.default_rng(seed)
    for beat in np.arange(0, duration_s, beat_len):
        i = int(beat * sr)
        n = min(count - i, int(.22 * sr))
        if n <= 0:
            continue
        t = np.arange(n) / sr
        kick = .75 * np.sin(2 * np.pi * (55 * t + 70 * t * np.exp(-18 * t))) * np.exp(-18 * t)
        audio[i:i + n] += kick
        beat_no = round(beat / beat_len)
        if beat_no % 4 in (1, 3):
            sn = min(count - i, int(.12 * sr))
            noise = rng.normal(0, 1, sn) * np.exp(-36 * np.arange(sn) / sr) * .12
            audio[i:i + sn] += noise
        chord_len = min(count - i, int(.4 * sr))
        ct = np.arange(chord_len) / sr
        notes = (110, 138.59, 164.81)
        chord = sum(np.sin(2 * np.pi * f * ct) for f in notes) / 3 * .075
        audio[i:i + chord_len] += chord * np.minimum(1, ct * 80)
    audio = np.clip(audio, -.95, .95)
    out = Path(out_wav)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    return {"output": str(out), "bpm": bpm, "duration_s": duration_s, "engine": "procedural_generator",
            "license_key": "procedural-music"}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--bpm", type=int, default=120)
    ap.add_argument("--duration", type=float, default=45)
    a = ap.parse_args(argv)
    generate_procedural_music(a.out, a.bpm, a.duration)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
