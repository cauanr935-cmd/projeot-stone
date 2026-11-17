#!/usr/bin/env python3
"""Auditoria do Reel final (CONTRATO da SPEC_07 — não enfraquecer).

Uso:
    python tests/verify_final_reel.py --video output/reel_final.mp4 --format 2 [--json]

Exit 0 = aprovado. Exit 1 = reprovado (motivos no stdout). Exit 2 = erro de uso.
A lógica fica em `audit_reel()` para que o renderizador a importe em vez de duplicar.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LUFS_RANGE = (-24.0, -10.0)


def _bin(name: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    try:
        import static_ffmpeg  # type: ignore

        static_ffmpeg.add_paths()
        path = shutil.which(name)
    except Exception:
        path = None
    if not path:
        raise SystemExit(f"{name} não encontrado")
    return path


def _probe(video: Path) -> dict:
    out = subprocess.run([_bin("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json",
                          str(video)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _lufs(video: Path) -> float | None:
    proc = subprocess.run([_bin("ffmpeg"), "-hide_banner", "-nostats", "-i", str(video), "-vn",
                           "-af", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+)\s+LUFS", proc.stderr)
    return float(m[-1]) if m else None


def _frame_stats(video: Path, duration: float, samples: int = 8) -> tuple[list[tuple[float, float]], list[float]]:
    """(desvio-padrão, média) de luminância em frames amostrados — detecta vídeo em branco/congelado."""
    import numpy as np

    stats, prev, diffs = [], None, []
    for k in range(samples):
        t = duration * (k + 0.5) / samples
        raw = subprocess.run([_bin("ffmpeg"), "-hide_banner", "-nostats", "-ss", f"{t:.3f}", "-i", str(video),
                              "-frames:v", "1", "-vf", "scale=108:192,format=gray", "-f", "rawvideo", "-"],
                             capture_output=True, check=True).stdout
        if len(raw) < 108 * 192:
            continue
        fr = np.frombuffer(raw[:108 * 192], dtype=np.uint8).astype(float)
        stats.append((float(fr.std()), float(fr.mean())))
        if prev is not None:
            diffs.append(float(np.abs(fr - prev).mean()))
        prev = fr
    return stats, diffs


def load_format(format_id: int) -> dict:
    cfg = yaml.safe_load((ROOT / "config" / "formats.yaml").read_text(encoding="utf-8"))
    for f in cfg["formats"]:
        if f["id"] == format_id:
            return {**f, "_tolerance": cfg["common"]["output"]["duration_tolerance_s"]}
    raise SystemExit(f"formato {format_id} inexistente")


def audit_reel(video: Path, format_id: int) -> dict:
    fmt = load_format(format_id)
    checks: list[dict] = []

    def check(name: str, ok: bool, value) -> None:
        checks.append({"check": name, "ok": bool(ok), "value": value})

    if not video.exists() or video.stat().st_size == 0:
        return {"passed": False, "checks": [{"check": "file_exists", "ok": False, "value": str(video)}]}

    info = _probe(video)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    duration = float(info["format"]["duration"])

    check("video_stream", v is not None, bool(v))
    if v:
        check("codec_h264", v.get("codec_name") == "h264", v.get("codec_name"))
        check("pix_fmt_yuv420p", v.get("pix_fmt") == "yuv420p", v.get("pix_fmt"))
        check("resolution_1080x1920", (int(v["width"]), int(v["height"])) == (1080, 1920),
              f"{v['width']}x{v['height']}")
        check("cfr", Fraction(v["r_frame_rate"]) == Fraction(v["avg_frame_rate"]),
              f"{v['r_frame_rate']} vs {v['avg_frame_rate']}")
    check("audio_stream", a is not None, bool(a))
    if a:
        check("codec_aac", a.get("codec_name") == "aac", a.get("codec_name"))
        check("sample_rate_ge_44100", int(a.get("sample_rate", 0)) >= 44100, a.get("sample_rate"))
        lufs = _lufs(video)
        check("loudness_lufs_-24_-10", lufs is not None and LUFS_RANGE[0] <= lufs <= LUFS_RANGE[1], lufs)

    lo, hi = fmt["duration"]["min"], fmt["duration"]["max"] + fmt["_tolerance"]
    check(f"duration_{lo}_{hi}", lo <= duration <= hi, round(duration, 3))

    stats, diffs = _frame_stats(video, duration)
    check("not_blank", bool(stats) and max(s[0] for s in stats) > 5.0, [round(s[0], 1) for s in stats])
    check("not_frozen", bool(diffs) and max(diffs) > 1.0, [round(d, 2) for d in diffs])

    return {"passed": all(c["ok"] for c in checks), "video": str(video), "format_id": format_id,
            "duration_s": round(duration, 3), "checks": checks}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--format", required=True, type=int, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = audit_reel(args.video, args.format)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for c in report["checks"]:
            print(f"[{'OK' if c['ok'] else 'FALHA'}] {c['check']}: {c['value']}")
        print("APROVADO" if report["passed"] else "REPROVADO")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
