"""SPEC_07 — E2E dos 5 formatos, render_report e tools MCP (CONTRATO)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from acc_helpers import FIXTURES, PY, ROOT, project_env, run

OUT = ROOT / "output"
EXPECTED_TOOLS = {"ping", "list_formats", "get_router_status", "extract_multimodal_hooks",
                  "auto_reframe_vertical_9_16", "animate_static_image_2_5d", "synthesize_voiceover_ptbr",
                  "generate_karaoke_ass_subs", "build_edit_plan", "assemble_and_render_reel"}


def _effective_tts() -> str:
    proc = run([PY, "-m", "src.core.doctor", "--json"], timeout=120)
    return json.loads(proc.stdout)["engines_effective"]["tts"]


@pytest.fixture(scope="module")
def e2e_env():
    tts = _effective_tts()
    commercial = "0" if tts == "placeholder_tone" else "1"
    return project_env(REELS_OFFLINE="1", REELS_COMMERCIAL=commercial), commercial


@pytest.mark.slow
@pytest.mark.parametrize("fmt_id", [1, 2, 3, 4, 5])
def test_render_each_format(fmt_id, e2e_env, fixtures_ready):
    env, commercial = e2e_env
    OUT.mkdir(exist_ok=True)
    video = OUT / f"reel_format_{fmt_id}.mp4"
    video.unlink(missing_ok=True)
    job_id = f"acc07_fmt{fmt_id}"
    run([PY, "-m", "src.main", "--input-dir", str(FIXTURES / "mixed"), "--format", str(fmt_id),
         "--out", str(video), "--job-id", job_id, "--business-name", "Doces da Ana"],
        env=env, timeout=1800)

    audit = run([PY, "tests/verify_final_reel.py", "--video", str(video), "--format", str(fmt_id), "--json"],
                env=env, timeout=300, check=False)
    report = json.loads(audit.stdout)
    failed = [c for c in report["checks"] if not c["ok"]]
    assert audit.returncode == 0 and report["passed"], f"auditoria reprovou: {failed}"

    rr_path = ROOT / "workspace" / "jobs" / job_id / "render_report.json"
    rr = json.loads(rr_path.read_text(encoding="utf-8"))
    assert {"asr", "tts", "llm", "vlm", "music", "depth", "subject_detection"} <= set(rr["engines"])
    assert rr["license_keys"], "render_report sem license_keys"
    assert abs(rr["cuts"]["timeline"] - rr["cuts"]["planned"]) <= 1, rr["cuts"]
    assert rr["audit"]["passed"] is True
    assert str(rr["commercial"]).lower() in ({"true", "1"} if commercial == "1" else {"false", "0"})


async def test_mcp_tools_and_render_guardrail(tmp_path, fixtures_ready):
    from mcp.shared.memory import create_connected_server_and_client_session

    from src.mcp_server import mcp

    plan_path = tmp_path / "plan.json"
    run([PY, "-m", "src.director.interactive_cli", "--input-dir", str(FIXTURES / "mixed"), "--format", "1",
         "--out", str(plan_path), "--job-id", "acc07_guard"], env=project_env(REELS_OFFLINE="1"), timeout=600)
    target = tmp_path / "should_not_exist.mp4"

    async with create_connected_server_and_client_session(mcp) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        assert EXPECTED_TOOLS <= tools, f"faltam tools: {EXPECTED_TOOLS - tools}"
        res = await client.call_tool("assemble_and_render_reel", {
            "edit_plan_path": str(plan_path), "output_path": str(target),
            "commercial": True, "audio_sources": ["freesound"]})
        text = "".join(getattr(c, "text", "") for c in res.content)
        assert res.isError, "fonte não comercial deveria ser recusada pelo schema/guardrail"
        assert "CommercialLicenseViolation" in text, text
    assert not Path(target).exists(), "nada deveria ter sido renderizado"
