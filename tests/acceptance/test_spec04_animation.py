"""SPEC_04 — paralaxe 2.5D com deformação zero e morph por fluxo óptico (CONTRATO)."""
from __future__ import annotations

import json
import shutil

import numpy as np
import pytest

from acc_helpers import (FIXTURES, PY, ROOT, extract_gray_frame, extract_gray_frames_every, nb_frames, run, ssim,
                         video_stream)

JOB = ROOT / "workspace" / "jobs" / "acceptance_spec04"


@pytest.fixture(scope="module")
def outdir(fixtures_ready):
    if JOB.exists():
        shutil.rmtree(JOB)
    JOB.mkdir(parents=True)
    return JOB


@pytest.fixture(scope="module")
def parallax(outdir):
    out = outdir / "parallax_move.mp4"
    run([PY, "-m", "src.animation.parallax_2_5d", "--image", str(FIXTURES / "img_1.jpg"),
         "--out", str(out), "--duration", "5", "--fps", "30"], timeout=900)
    return out


@pytest.mark.slow
def test_parallax_format(parallax):
    vs = video_stream(parallax, count_frames=True)
    assert int(vs["width"]) == 1080 and int(vs["height"]) == 1920
    assert vs["pix_fmt"] == "yuv420p"
    assert abs(nb_frames(vs) - 150) <= 2, f"nb_frames={nb_frames(vs)} (esperado 150±2)"


@pytest.mark.slow
def test_parallax_zero_deformation_and_motion(parallax, outdir):
    meta = json.loads(parallax.with_suffix(".pivot.json").read_text(encoding="utf-8"))
    box = meta["pivot_box"]
    x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
    assert w >= 100 and h >= 100, "PIVOT_CENTER_BOX pequena demais para ser o produto"
    f0 = extract_gray_frame(parallax, 0, outdir / "f0.png")
    f75 = extract_gray_frame(parallax, 75, outdir / "f75.png")
    crop0, crop75 = f0[y:y + h, x:x + w], f75[y:y + h, x:x + w]
    score = ssim(crop0, crop75)
    assert score >= 0.90, f"SSIM na PIVOT_CENTER_BOX = {score:.3f} (mínimo 0,90)"

    mask = np.ones_like(f0, dtype=bool)
    mask[y:y + h, x:x + w] = False
    outside_diff = float(np.abs(f0[mask] - f75[mask]).mean())
    assert outside_diff > 1.0, f"fora do pivô quase não há movimento ({outside_diff:.2f}); vídeo estático?"


@pytest.mark.slow
def test_optical_flow_morph(outdir):
    out = outdir / "morph.mp4"
    run([PY, "-m", "src.animation.optical_flow_morph", "--images",
         str(FIXTURES / "img_1.jpg"), str(FIXTURES / "img_2.jpg"), str(FIXTURES / "img_3.jpg"),
         "--out", str(out), "--duration", "6", "--fps", "30", "--sway"], timeout=900)
    vs = video_stream(out, count_frames=True)
    assert int(vs["width"]) == 1080 and int(vs["height"]) == 1920
    assert vs["pix_fmt"] == "yuv420p"
    n = nb_frames(vs)
    assert abs(n - 180) <= 2, f"nb_frames={n} (esperado 180±2)"

    frames = extract_gray_frames_every(out, 3, outdir / "morph_frames")
    assert len(frames) >= 50
    first_last = float(np.abs(frames[0] - frames[-1]).mean())
    max_step = max(float(np.abs(a - b).mean()) for a, b in zip(frames, frames[1:]))
    assert first_last > 2.0, "primeiro e último frame quase iguais — morph não percorreu as fotos"
    assert max_step < 0.5 * first_last, (
        f"transição não é gradual (maior salto {max_step:.2f} vs total {first_last:.2f}) — parece corte seco")
