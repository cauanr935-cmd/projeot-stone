"""SPEC_06 — seletor interativo dos 5 formatos e edit_plan.json (CONTRATO)."""
from __future__ import annotations

import json
import math
import re

import pytest

from acc_helpers import FIXTURES, PADS, PY, RESEARCH_TABLE, load_yaml, project_env, run

ENV = project_env(REELS_OFFLINE="1")


def _plan_via_stdin(tmp_path, answer: str, name: str = "plan.json"):
    out = tmp_path / name
    proc = run([PY, "-m", "src.director.interactive_cli", "--input-dir", str(FIXTURES / "mixed"),
                "--out", str(out), "--job-id", f"acc06_{name.split('.')[0]}"],
               input=answer, env=ENV, timeout=600, check=False)
    return proc, out


@pytest.mark.parametrize("fmt_id", [1, 2, 3, 4, 5])
def test_stdin_choice_builds_exact_plan(tmp_path, fmt_id, fixtures_ready):
    proc, out = _plan_via_stdin(tmp_path, f"{fmt_id}\n", f"plan{fmt_id}.json")
    assert proc.returncode == 0, proc.stderr[-3000:]
    menu = proc.stdout
    for i in range(1, 6):
        assert f"[{i}]" in menu, "menu deve listar as 5 opções numeradas"
    plan = json.loads(out.read_text(encoding="utf-8"))
    exp = RESEARCH_TABLE[fmt_id]

    assert plan["schema_version"] == 1
    assert plan["format"]["id"] == fmt_id
    assert [(s["start"], s["end"]) for s in plan["segments"]] == exp["segments"]
    assert plan["tts"]["voice"] == exp["voice"]
    assert plan["cut"]["style"] == exp["cut_style"]
    assert plan["cut"]["pad"] == pytest.approx(PADS[exp["cut_style"]])
    assert plan["cut"]["target_cuts_per_sec"] == pytest.approx(exp["cuts"])
    target = plan["duration"]["target"]
    assert plan["cut"]["planned_cuts"] == round(exp["cuts"] * target)
    assert (plan["duration"]["min"], plan["duration"]["max"]) == exp["window"]
    assert target == exp["segments"][-1][1]
    assert plan["seamless_loop"] is exp["loop"]
    assert plan["animation"]["mode"] == exp["animation"]
    assert plan["reframe"]["preset"] == exp["preset"]
    if fmt_id == 2:
        assert plan["animation"]["parallax_strength"] == 10
    if fmt_id == 3:
        assert plan["animation"]["handheld_sway"] is True
    assert plan["output"]["width"] == 1080 and plan["output"]["height"] == 1920

    # Regras de roteiro / assets
    hook = plan["subtitles"]["hook_overlay"]
    assert 1 <= len(hook.split()) <= 5, hook
    kinds = {a["kind"] for a in plan["assets"]}
    assert kinds == {"video", "image"}, kinds
    for seg in plan["segments"]:
        assert seg["assets"], f"segmento {seg['name']} sem asset"
        limit = math.ceil(3.5 * (seg["end"] - seg["start"])) + 2
        assert len(seg["script"].split()) <= limit, f"{seg['name']}: roteiro longo demais para {seg['end']-seg['start']} s"

    if exp["loop"]:
        connectors = load_yaml("script_templates.yaml")["formats"][5]["loop_connectors_allowed"]
        last = plan["segments"][-1]["script"].strip()
        assert not re.search(r"[.!?…]$", last), "último trecho do AIDA não pode ter pontuação final (loop)"
        assert any(last.lower().endswith(" " + c) for c in connectors), last
        assert plan["script"]["loop_tail"]


def test_invalid_then_valid_input(tmp_path, fixtures_ready):
    proc, out = _plan_via_stdin(tmp_path, "9\nabc\n3\n", "retry.json")
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert json.loads(out.read_text(encoding="utf-8"))["format"]["id"] == 3


def test_eof_exits_2_without_plan(tmp_path, fixtures_ready):
    proc, out = _plan_via_stdin(tmp_path, "", "eof.json")
    assert proc.returncode == 2
    assert not out.exists()


def test_format_flag_does_not_read_stdin(tmp_path, fixtures_ready):
    out = tmp_path / "flag.json"
    proc = run([PY, "-m", "src.director.interactive_cli", "--input-dir", str(FIXTURES / "mixed"),
                "--format", "2", "--out", str(out), "--cnae", "5620-1/04", "--job-id", "acc06_flag"],
               input="5\n", env=ENV, timeout=600)
    plan = json.loads(out.read_text(encoding="utf-8"))
    assert plan["format"]["id"] == 2, "com --format a entrada do stdin deve ser ignorada"
    assert plan["cnae"]["code"] == "5620-1/04"
    assert str(out) in proc.stdout.strip().splitlines()[-1]
