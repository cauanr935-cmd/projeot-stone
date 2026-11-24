from __future__ import annotations

import argparse
import asyncio
import uuid
import json
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from src.core.config import ROOT, get_format, load_formats
from src.core.paths import get_roots, resolve_allowed_path
from src.director.edit_plan import build_edit_plan
from src.resources.cnae_profiles import get_cnae_marketing_profile
from src.router.cascade_router import ZeroCostCascadeRouter
from src.router.license_guard import CommercialLicenseViolationError, validate_commercial_sources

mcp = FastMCP("ImpulsoStone-Reels-Engine",
              instructions="Produza Reels verticais offline-first para microempreendedores Impulso Stone.")


@mcp.resource("stone-cnae://profiles/{cnae_code}", name="Perfil CNAE",
              description="Perfil de marketing e formato recomendado para um CNAE.")
def cnae_resource(cnae_code: str) -> str:
    return get_cnae_marketing_profile(cnae_code)


@mcp.resource("stone-formats://catalog", name="Catálogo de formatos")
def formats_resource() -> str:
    formats = load_formats()
    catalog = [{"id": f["id"], "key": f["key"], "name": f["name"], "focus": f["focus"],
                "duration": f["duration"], "segments": f["segments"], "cut_style": f["cut_style"],
                "target_cuts_per_sec": f["target_cuts_per_sec"], "seamless_loop": f["seamless_loop"]}
               for f in formats]
    return json.dumps({"formats": catalog}, ensure_ascii=False)


@mcp.resource("stone-media://jobs/{job_id}/analysis_summary", name="Resumo da análise de mídia")
def analysis_summary_resource(job_id: str) -> str:
    path = Path(os.getenv("REELS_WORKSPACE", "./workspace")) / "jobs" / job_id / "multimodal_summary.json"
    return path.read_text(encoding="utf-8") if path.exists() else json.dumps({"status": "pending_analysis"})


@mcp.resource("stone-quota://router/status", name="Status do roteador")
def quota_resource() -> str:
    return json.dumps({"status": "router_not_initialized"})


@mcp.prompt("gerar_reel_impulso_stone")
def gerar_reel_impulso_stone(cnae_code: str, objetivo_venda: str, job_id: str = "job") -> str:
    profile = json.loads(get_cnae_marketing_profile(cnae_code))
    return (f"Crie um Reel para {profile['ocupacao']} com objetivo: {objetivo_venda}. "
            f"Consulte stone-cnae://profiles/{''.join(filter(str.isdigit, cnae_code))} e "
            f"stone-media://jobs/{job_id}/analysis_summary. Pergunte o formato se necessário, "
            "use build_edit_plan e depois assemble_and_render_reel. No Frame Zero, no máximo 5 palavras.")


def _format_prompt(format_id: int, cnae_code: str, objetivo_venda: str, job_id: str | None = None) -> str:
    fmt = get_format(format_id)
    segments = " → ".join(f"{s['name']} ({s['start']}–{s['end']} s)" for s in fmt["segments"])
    loop = " Faça Seamless Loop; termine o CTA com conector que completa a primeira frase." \
        if fmt["seamless_loop"] else ""
    return (f"Formato {fmt['name']}: {segments}. CNAE {cnae_code}; objetivo: {objetivo_venda}. "
            "No Frame Zero, exiba no máximo 5 palavras. Chame build_edit_plan e em seguida "
            f"assemble_and_render_reel para o job {job_id or 'atual'}.{loop}")


@mcp.prompt("reel_bab")
def reel_bab(cnae_code: str, objetivo_venda: str, job_id: str | None = None) -> str:
    return _format_prompt(1, cnae_code, objetivo_venda, job_id)


@mcp.prompt("reel_product_demo_pas")
def reel_product_demo_pas(cnae_code: str, objetivo_venda: str, job_id: str | None = None) -> str:
    return _format_prompt(2, cnae_code, objetivo_venda, job_id)


@mcp.prompt("reel_ugc_testimonial")
def reel_ugc_testimonial(cnae_code: str, objetivo_venda: str, job_id: str | None = None) -> str:
    return _format_prompt(3, cnae_code, objetivo_venda, job_id)


@mcp.prompt("reel_pas")
def reel_pas(cnae_code: str, objetivo_venda: str, job_id: str | None = None) -> str:
    return _format_prompt(4, cnae_code, objetivo_venda, job_id)


@mcp.prompt("reel_aida")
def reel_aida(cnae_code: str, objetivo_venda: str, job_id: str | None = None) -> str:
    return _format_prompt(5, cnae_code, objetivo_venda, job_id)


@mcp.tool()
def ping() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@mcp.tool()
def list_formats() -> list[dict]:
    return formats_resource() and json.loads(formats_resource())["formats"]


@mcp.tool()
def get_router_status() -> dict:
    return {"status": "ready", "offline": os.getenv("REELS_OFFLINE", "0") == "1",
            "engines": {"asr": "local_optional", "tts": "offline_fallback", "llm": "template_engine"}}


@mcp.tool()
def extract_multimodal_hooks(input_path: str, job_id: str = "analysis", preset: str = "talking_head") -> dict:
    from src.vision.pipeline import analyze_video
    workspace = Path(os.getenv("REELS_WORKSPACE", "./workspace"))
    job = workspace / "jobs" / job_id
    return analyze_video(Path(input_path), job, preset)


@mcp.tool()
def auto_reframe_vertical_9_16(input_path: str, output_path: str, preset: str = "talking_head") -> dict:
    from src.vision.reframe_9_16 import auto_reframe_vertical_9_16 as reframe
    return reframe(Path(input_path), Path(output_path), preset)


@mcp.tool()
def animate_static_image_2_5d(image_path: str, output_path: str, duration: float = 5, fps: int = 30,
                              strength: float | None = None, mode: str = "parallax",
                              extra_images: list[str] | None = None, job_id: str | None = None) -> dict:
    if mode == "morph":
        from src.animation.optical_flow_morph import morph_images
        return morph_images([Path(image_path), *[Path(x) for x in (extra_images or [])]],
                            Path(output_path), duration, fps)
    from src.animation.parallax_2_5d import animate_static_image_2_5d as animate
    return animate(Path(image_path), Path(output_path), duration, fps, strength)


@mcp.tool()
async def synthesize_voiceover_ptbr(text: str, output_path: str, srt_path: str | None = None,
                                    voice: str = "pt-BR-FranciscaNeural", rate: str = "+0%") -> dict:
    mp3 = Path(output_path)
    srt = Path(srt_path) if srt_path else mp3.with_suffix(".srt")
    return await ZeroCostCascadeRouter().synthesize_ptbr_voiceover(text, mp3, srt, voice, rate)


@mcp.tool()
def generate_karaoke_ass_subs(words_json_path: str, output_path: str, hook_overlay: str | None = None) -> dict:
    words = json.loads(Path(words_json_path).read_text(encoding="utf-8"))
    return __import__("src.editing.subtitles_ass", fromlist=["generate_karaoke_ass_subtitles"]) \
        .generate_karaoke_ass_subtitles(words, Path(output_path), hook_overlay)


@mcp.tool()
async def build_edit_plan(input_dir: str, format_id: int | None = None, cnae_code: str | None = None,
                    business_name: str | None = None, product: str | None = None,
                    cta_channel: str = "WhatsApp", job_id: str = "job",
                    ctx: Context | None = None) -> dict:
    if format_id is None:
        return {"needs_format": True, "options": [{"id": f["id"], "name": f["name"], "focus": f["focus"]}
                                                  for f in load_formats()]}
    roots = await get_roots(ctx) if ctx else [Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve()]
    allowed_input = resolve_allowed_path(input_dir, roots)
    return build_edit_plan_impl(allowed_input, format_id, cnae_code, job_id, business_name, product, cta_channel)


def build_edit_plan_impl(input_dir: Path, format_id: int, cnae_code: str | None, job_id: str,
                         business_name: str | None, product: str | None, cta_channel: str) -> dict:
    from src.director.edit_plan import build_edit_plan as build
    return build(input_dir, format_id, cnae_code, job_id, business_name, product, cta_channel)


@mcp.tool()
async def assemble_and_render_reel(edit_plan_path: str | None = None, edit_plan: dict | None = None,
                             output_path: str | None = None, commercial: bool = True,
                             audio_sources: list[str] | None = None, ctx: Context | None = None) -> dict:
    try:
        validate_commercial_sources(audio_sources or [], commercial=commercial)
    except CommercialLicenseViolationError as exc:
        raise ValueError(f"CommercialLicenseViolationError: {exc}") from exc
    if edit_plan is None:
        if not edit_plan_path:
            raise ValueError("informe edit_plan ou edit_plan_path")
        roots = await get_roots(ctx) if ctx else [Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve()]
        plan_path = resolve_allowed_path(edit_plan_path, roots)
        edit_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    else:
        roots = await get_roots(ctx) if ctx else [Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve()]
    for asset in edit_plan.get("assets", []):
        resolve_allowed_path(asset["path"], roots)
    from src.renderer.reel_assembler import assemble_and_render_reel as render
    target = resolve_allowed_path(output_path or "output/reel_final.mp4", roots)
    return await asyncio.to_thread(render, edit_plan, target, commercial)


# ------------------------------------------------------------------ criativos (motion graphics)
@mcp.resource("stone-criativos://perfis", name="Perfis prioritários de MPE",
              description="10 perfis de MPE com material de marca, dor, solução, CTA e formato.")
def perfis_resource() -> str:
    from src.criativos.spec import carregar_perfis
    return json.dumps(carregar_perfis(), ensure_ascii=False)


@mcp.prompt("criar_criativo_motion")
def criar_criativo_motion(perfil_id: str, instrucoes: str = "") -> str:
    return (f"Crie um criativo em motion graphics para o perfil '{perfil_id}'. 1) Chame briefing_criativo; "
            "2) escreva você mesmo o CriativoSpec (JSON) seguindo regras e schema; 3) chame "
            f"renderizar_criativo com o spec; 4) se a auditoria reprovar, corrija e renderize de novo. {instrucoes}")


@mcp.tool()
def listar_perfis_criativos() -> list[dict]:
    from src.criativos.spec import carregar_perfis
    return [{"id": k, "nome": v["nome"], "cnae": v["cnae"], "formato": v["format_id"]}
            for k, v in carregar_perfis().items()]


@mcp.tool()
def briefing_criativo(perfil_id: str, negocio: str | None = None, formato_id: int | None = None) -> dict:
    """Briefing para a IA hospedada (Claude Code/Gemini) escrever o CriativoSpec: perfil, framework, regras, schema."""
    from src.criativos.llm import briefing
    return briefing(perfil_id, negocio, formato_id)


@mcp.tool()
async def renderizar_criativo(spec: dict, com_voz: bool = False) -> dict:
    """Valida e renderiza um CriativoSpec escrito pela IA em MP4 1080x1920 (auditado)."""
    from src.criativos import servico
    return await asyncio.to_thread(servico.renderizar_json, spec, None, com_voz)


@mcp.tool()
async def gerar_criativo_perfil(perfil_id: str, negocio: str | None = None, formato_id: int | None = None,
                                instrucoes: str | None = None, com_voz: bool = False) -> dict:
    """Gera o criativo de um perfil: LangChain (Claude/Gemini, se houver chave) ou template offline."""
    from src.criativos import servico
    return await asyncio.to_thread(servico.gerar_criativo, perfil_id, None, negocio, formato_id, instrucoes, com_voz)


@mcp.tool()
def interpretar_pedido(texto: str, estado: dict | None = None) -> dict:
    """Entende um pedido em linguagem livre ("sou confeiteira, Doce Sonho, quero divulgar bolo de pote por R$ 12").

    Devolve briefing, o que falta e uma `pergunta` para o usuário. Se `pronto` for falso, pergunte ao usuário e chame de novo
    passando o `estado` devolvido. Quando `pronto`, chame gerar_criativo_pedido com o `briefing`."""
    from src.criativos import conversa
    return conversa.interpretar(texto, estado)


@mcp.tool()
async def gerar_criativo_pedido(briefing: dict, com_voz: bool = False, arquivos: list[str] | None = None,
                                ctx: Context | None = None) -> dict:
    """Gera o criativo (MP4 1080x1920 auditado) a partir do briefing de interpretar_pedido.

    `arquivos` (opcional): caminhos de vídeos, fotos e áudios dentro do workspace. Com arquivos, o Reel é montado com a mídia
    do usuário (o 1º áudio vira a trilha); sem arquivos, é um criativo em motion graphics."""
    from src.criativos import conversa, midia_propria
    if arquivos:
        roots = await get_roots(ctx) if ctx else [Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve()]
        ids = [(await asyncio.to_thread(midia_propria.registrar_arquivo_local, resolve_allowed_path(c, roots)))["anexo_id"]
               for c in arquivos]
        pid = uuid.uuid4().hex[:12]
        r = await asyncio.to_thread(midia_propria.gerar_com_midia, briefing, midia_propria.resolver(ids), pid, None, com_voz)
    else:
        r = await asyncio.to_thread(conversa.gerar_pedido, briefing, com_voz)
    return {"pedido_id": r["pedido_id"], **(r["saida"] or {}), "trace": [{"titulo": t["titulo"], "resumo": t["resumo"]} for t in r["trace"]]}


@mcp.tool()
async def transcrever_audio(caminho: str, ctx: Context | None = None) -> dict:
    """Transcreve um áudio de fala PT-BR (arquivo dentro do workspace) para texto, 100% local. Use o texto em interpretar_pedido."""
    from src.criativos import transcricao
    roots = await get_roots(ctx) if ctx else [Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve()]
    return await asyncio.to_thread(transcricao.transcrever_arquivo, resolve_allowed_path(caminho, roots))


@mcp.tool()
async def gerar_criativos_lote(perfis: list[str] | None = None, com_voz: bool = False) -> list[dict]:
    """Gera os criativos dos perfis prioritários (todos se `perfis` omitido)."""
    from src.criativos import servico
    return await asyncio.to_thread(servico.gerar_lote, perfis, None, com_voz)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true")
    args = parser.parse_args(argv)
    mcp.run(transport="streamable-http" if args.http else "stdio")


if __name__ == "__main__":
    main()
