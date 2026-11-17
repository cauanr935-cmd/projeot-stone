"""SPEC_03 — normalização CFR, cenas, reframe 9:16 e hook finder (CONTRATO)."""
from __future__ import annotations

import csv
import json
import shutil

import pytest

from acc_helpers import FIXTURES, PY, ROOT, audio_stream, duration_s, is_cfr, run, video_stream

JOB = ROOT / "workspace" / "jobs" / "acceptance_spec03"


@pytest.fixture(scope="module")
def job_dir(fixtures_ready):
    if JOB.exists():
        shutil.rmtree(JOB)
    JOB.mkdir(parents=True)
    run([PY, "-m", "src.vision.pipeline", "--input", str(FIXTURES / "sample_raw.mp4"),
         "--job-dir", str(JOB), "--preset", "talking_head"], timeout=1200)
    return JOB


@pytest.mark.slow
def test_normalized_is_cfr(job_dir):
    vs = video_stream(job_dir / "normalized.mp4")
    assert is_cfr(vs), f"normalized.mp4 não é CFR: {vs['r_frame_rate']} vs {vs['avg_frame_rate']}"


@pytest.mark.slow
def test_output_9_16(job_dir):
    out = job_dir / "output_9_16.mp4"
    vs = video_stream(out)
    assert int(vs["width"]) == 1080 and int(vs["height"]) == 1920
    assert is_cfr(vs), f"output_9_16.mp4 não é CFR: {vs['r_frame_rate']} vs {vs['avg_frame_rate']}"
    assert vs["codec_name"] == "h264" and vs["pix_fmt"] == "yuv420p"
    assert audio_stream(out) is not None, "output_9_16.mp4 perdeu o áudio"
    assert abs(duration_s(out) - duration_s(job_dir / "normalized.mp4")) <= 0.25


@pytest.mark.slow
def test_scenes_csv(job_dir):
    with open(job_dir / "scenes.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["scene", "start_s", "end_s", "start_frame", "end_frame"]
    assert len(rows) - 1 >= 2, "esperado >= 2 cenas no vídeo sintético (que tem >= 3)"


@pytest.mark.slow
def test_multimodal_summary(job_dir):
    data = json.loads((job_dir / "multimodal_summary.json").read_text(encoding="utf-8"))
    for key in ("job_id", "source", "normalized", "scenes", "hooks", "selected_hook", "reframe", "created_at"):
        assert key in data, f"summary sem '{key}'"
    assert data["source"]["was_vfr"] is True
    hooks = data["hooks"]
    assert len(hooks) >= 1
    for h in hooks:
        assert 0.0 <= h["score"] <= 1.0
        assert 2.5 <= h["end"] - h["start"] <= 5.05, h
        assert {"A", "F", "E", "L", "V"} <= set(h["components"])
    assert data["selected_hook"]["score"] == pytest.approx(max(h["score"] for h in hooks))
    assert data["reframe"]["strategy"] in {"TRACK", "LETTERBOX", "CENTER"}
