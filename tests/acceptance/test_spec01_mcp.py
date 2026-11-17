"""SPEC_01 — fixtures, Resource CNAE e servidor MCP base (CONTRATO)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from PIL import Image

from acc_helpers import (CANONICAL_CNAE, FIXTURES, RESEARCH_TABLE, audio_stream, is_cfr, silences,
                         video_stream)


# ----------------------------------------------------------------------------- fixtures
def test_fixture_video(fixtures_ready):
    raw = FIXTURES / "sample_raw.mp4"
    assert raw.exists() and raw.stat().st_size > 0
    vs = video_stream(raw)
    assert (int(vs["width"]), int(vs["height"])) == (1920, 1080)
    assert not is_cfr(vs), "sample_raw.mp4 deve ser VFR (r_frame_rate != avg_frame_rate)"
    assert audio_stream(raw) is not None, "sample_raw.mp4 sem áudio"
    assert len(silences(raw, -32, 0.4)) >= 3, "esperado >= 3 pausas detectáveis a -32 dB / 0,4 s"


def test_fixture_images_and_mixed(fixtures_ready):
    expected = {"img_1.jpg": (1200, 1600), "img_2.jpg": (1600, 1200), "img_3.jpg": (1080, 1080)}
    for name, size in expected.items():
        p = FIXTURES / name
        assert p.exists() and p.stat().st_size > 0, name
        assert Image.open(p).size == size, f"{name}: {Image.open(p).size} != {size}"
    mixed = sorted(x.name for x in (FIXTURES / "mixed").iterdir())
    assert mixed == ["img_1.jpg", "img_2.jpg", "sample_raw.mp4"], mixed
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("speech_segments"), "manifest.json sem speech_segments"


# ----------------------------------------------------------------------------- CNAE
PROFILE_KEYS = {"cnae_code", "ocupacao", "segment", "format_id", "framework", "cut_style",
                "target_cuts_per_sec", "reframe_preset", "tts_voice", "duration", "segments",
                "seamless_loop", "parallax_strength", "fallback"}


@pytest.mark.parametrize("fmt_id", [1, 2, 3, 4, 5])
def test_cnae_profiles_match_research(fmt_id):
    from src.resources.cnae_profiles import get_cnae_marketing_profile

    exp = RESEARCH_TABLE[fmt_id]
    data = json.loads(get_cnae_marketing_profile(CANONICAL_CNAE[fmt_id]))
    assert PROFILE_KEYS <= set(data), f"faltam: {PROFILE_KEYS - set(data)}"
    assert data["format_id"] == fmt_id
    assert data["cut_style"] == exp["cut_style"]
    assert data["target_cuts_per_sec"] == pytest.approx(exp["cuts"])
    assert data["tts_voice"] == exp["voice"]
    assert data["reframe_preset"] == exp["preset"]
    assert data["seamless_loop"] is exp["loop"]
    assert data["fallback"] is False
    if fmt_id == 2:
        assert data["parallax_strength"] == 10


def test_cnae_alias_digits_and_fallback():
    from src.resources.cnae_profiles import get_cnae_marketing_profile, normalize_cnae

    assert normalize_cnae("9602501") == "9602-5/01"
    assert normalize_cnae("9602-5-01") == "9602-5/01"
    assert json.loads(get_cnae_marketing_profile("4321-5/01"))["format_id"] == 4
    assert json.loads(get_cnae_marketing_profile("9602501"))["format_id"] == 1
    unknown = json.loads(get_cnae_marketing_profile("0000-0/00"))
    assert unknown["fallback"] is True


# ----------------------------------------------------------------------------- MCP
def _text(contents) -> str:
    return "".join(getattr(c, "text", "") for c in contents)


async def test_mcp_primitives_in_memory():
    from mcp.shared.memory import create_connected_server_and_client_session

    from src.mcp_server import mcp

    async with create_connected_server_and_client_session(mcp) as client:
        templates = await client.list_resource_templates()
        uris = {t.uriTemplate for t in templates.resourceTemplates}
        assert "stone-cnae://profiles/{cnae_code}" in uris
        assert "stone-media://jobs/{job_id}/analysis_summary" in uris

        res = await client.read_resource("stone-cnae://profiles/9602501")
        profile = json.loads(_text(res.contents))
        assert profile["format_id"] == 1

        resources = await client.list_resources()
        assert "stone-formats://catalog" in {str(r.uri) for r in resources.resources}
        catalog = json.loads(_text((await client.read_resource("stone-formats://catalog")).contents))
        catalog_list = catalog["formats"] if isinstance(catalog, dict) else catalog
        assert [f["id"] for f in catalog_list] == [1, 2, 3, 4, 5]

        prompts = {p.name for p in (await client.list_prompts()).prompts}
        assert {"gerar_reel_impulso_stone", "reel_bab", "reel_product_demo_pas", "reel_ugc_testimonial",
                "reel_pas", "reel_aida"} <= prompts
        aida = await client.get_prompt("reel_aida", {"cnae_code": "8599699", "objetivo_venda": "vender aulas"})
        aida_text = " ".join(getattr(m.content, "text", "") for m in aida.messages).lower()
        assert "loop" in aida_text

        tools = {t.name for t in (await client.list_tools()).tools}
        assert {"ping", "list_formats"} <= tools
        pong = await client.call_tool("ping", {})
        assert not pong.isError
        assert "ok" in _text(pong.content).lower()


# ----------------------------------------------------------------------------- Roots
def test_resolve_allowed_path_blocks_escape(tmp_path):
    from src.core.paths import PathOutsideRootsError, resolve_allowed_path

    root = tmp_path / "root"
    (root / "ok").mkdir(parents=True)
    outside = tmp_path / "secret.txt"
    outside.write_text("x")
    assert resolve_allowed_path(root / "ok", [root]) == (root / "ok").resolve()
    with pytest.raises(PathOutsideRootsError):
        resolve_allowed_path(root / ".." / "secret.txt", [root])
    link = root / "link.txt"
    os.symlink(outside, link)
    with pytest.raises(PathOutsideRootsError):
        resolve_allowed_path(link, [root])
