"""SPEC_00 — bootstrap e doctor (CONTRATO)."""
from __future__ import annotations

import json
import re
import shutil

from acc_helpers import PY, ROOT, run

REQUIRED_KEYS = {"python", "binaries", "ffmpeg_filters", "gpu", "network", "env_keys",
                 "python_packages", "models", "fonts", "engines_effective", "human_dependencies"}
ENGINE_KEYS = {"asr", "tts", "llm", "vlm", "music", "depth", "subject_detection"}


def _doctor_json() -> dict:
    proc = run([PY, "-m", "src.core.doctor", "--json"], timeout=120)
    return json.loads(proc.stdout)


def test_doctor_json_contract():
    data = _doctor_json()
    assert REQUIRED_KEYS <= set(data), f"faltam chaves: {REQUIRED_KEYS - set(data)}"
    assert data["binaries"]["ffmpeg"]["ok"] is True
    assert data["binaries"]["ffprobe"]["ok"] is True
    assert data["ffmpeg_filters"]["libx264"] is True, "ffmpeg sem libx264"
    assert data["ffmpeg_filters"]["ass"] is True, "ffmpeg sem libass (necessário p/ queimar .ass)"
    assert ENGINE_KEYS <= set(data["engines_effective"])
    assert isinstance(data["human_dependencies"], list)
    for item in data["human_dependencies"]:
        assert {"id", "priority", "spec", "action", "impact", "fallback", "verify"} <= set(item)


def test_doctor_never_leaks_secret_values():
    data = _doctor_json()
    assert data["env_keys"], "env_keys vazio — deveria listar as variáveis do .env.example"
    for name, value in data["env_keys"].items():
        assert isinstance(value, bool), f"env_keys[{name}] deve ser bool, não {type(value).__name__}"


def test_write_report_preserves_manual_sections(tmp_path):
    src_doc = ROOT / "docs" / "HUMAN_DEPENDENCIES.md"
    dst = tmp_path / "HUMAN_DEPENDENCIES.md"
    shutil.copy(src_doc, dst)
    original = dst.read_text(encoding="utf-8")
    before, _, rest = original.partition("<!-- AUTO:BEGIN -->")
    _, _, after = rest.partition("<!-- AUTO:END -->")

    run([PY, "-m", "src.core.doctor", "--write-report", "--docs-dir", str(tmp_path)], timeout=120)

    assert (tmp_path / "ENVIRONMENT_REPORT.md").stat().st_size > 0
    new = dst.read_text(encoding="utf-8")
    assert new.startswith(before), "texto antes de AUTO:BEGIN foi alterado"
    assert new.endswith(after), "texto depois de AUTO:END foi alterado"
    assert "<!-- AUTO:BEGIN -->" in new and "<!-- AUTO:END -->" in new


def test_config_loader():
    from src.core import config

    formats = config.load_formats()
    assert [f["id"] for f in formats] == [1, 2, 3, 4, 5]
    assert config.get_format("pas")["cut_style"] == "overlapping"
    assert config.get_format(5)["seamless_loop"] is True
    assert config.common()["output"]["width"] == 1080
    assert config.common()["output"]["height"] == 1920
    assert config.load_cnae_profiles()["profiles"]
    assert config.load_providers()["modalities"]["tts"]["tiers"]
    assert config.load_licenses()["entries"]["freesound"]["commercial_ok"] is False
    assert config.load_script_templates()["formats"]


def test_pyproject_pins_mcp_v1():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r"""["']mcp[^"']*["']""", text)
    assert m, "dependência mcp não declarada no pyproject.toml"
    assert "<2" in m.group(0), f"mcp deve ter limite <2 (FastMCP), encontrado: {m.group(0)}"
