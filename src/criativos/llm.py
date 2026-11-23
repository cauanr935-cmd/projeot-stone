"""Camada LangChain: gera o CriativoSpec com a IA do usuário (Claude ou Gemini) e cai nos templates se faltar chave.

Seleção (CRIATIVOS_LLM): auto (padrão) | anthropic | gemini | none.
Só se verifica a EXISTÊNCIA das chaves (ANTHROPIC_API_KEY, GOOGLE_API_KEY/GEMINI_API_KEY). Para a IA hospedada
(Claude Code, Gemini CLI) o caminho é via MCP: ela escreve o spec e chama `renderizar_criativo`
(ver src/criativos/ferramentas.py e src/mcp_server.py).
Privacidade: ao provedor vai só o material do perfil (config/perfis_prioritarios.yaml), nunca mídia do usuário.
"""
from __future__ import annotations

import json
import logging
import os

from src.core.config import get_format
from src.criativos.spec import CriativoSpec, Paleta, obter_perfil, spec_offline

log = logging.getLogger("criativos.llm")

REGRAS = """Você é diretor criativo de Reels para microempreendedores brasileiros (Impulso Stone).
Tom: próximo, acolhedor, simples, SEM promessa exagerada e sem jargão. PT-BR.
Crie um criativo em MOTION GRAPHICS (sem vídeo de câmera) no framework {formato}: {segmentos}.
Regras duras:
- hook_overlay (Frame Zero): no máximo 5 palavras, curiosidade/dor, sem clickbait enganoso.
- Primeira cena 'hook', última cena 'cta'; de 3 a 7 cenas; duração total de {dmin} a {dmax} s
  (fala ~2,6–3,2 palavras/s: narracao de cada cena deve caber em ~4–7 s).
- Tipos de cena: hook | pontos (2–4 itens curtos, icone 'check' ou 'x') | antes_depois (itens=[antes, depois])
  | numero (campo numero + rotulo) | cta.
- Itens com no máximo 6 palavras. Não invente preços, prazos ou garantias que não estejam no perfil.
- narracao é o texto falado; titulo/itens são o texto na tela.
- Mantenha perfil_id={perfil_id} e formato_id={formato_id}. Não altere cores da marca."""


def escolher_llm():
    """Retorna (nome, chat_model) ou (None, None) quando não há IA disponível (fallback offline)."""
    modo = os.getenv("CRIATIVOS_LLM", "auto").lower()
    if modo == "none" or os.getenv("REELS_OFFLINE", "0") == "1":
        return None, None
    tem_claude = os.getenv("ANTHROPIC_API_KEY") is not None
    tem_gemini = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")) is not None
    try:
        if modo in ("auto", "anthropic") and tem_claude:
            from langchain_anthropic import ChatAnthropic
            return "anthropic", ChatAnthropic(model=os.getenv("CRIATIVOS_CLAUDE_MODEL", "claude-sonnet-5-5"),
                                              temperature=0.7, max_tokens=2500)
        if modo in ("auto", "gemini") and tem_gemini:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return "gemini", ChatGoogleGenerativeAI(model=os.getenv("CRIATIVOS_GEMINI_MODEL", "gemini-2.5-flash"),
                                                    temperature=0.7,
                                                    google_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    except Exception as exc:
        log.info("LLM indisponível (%s); usando template_engine", exc)
    return None, None


def briefing(perfil_id: str, negocio: str | None = None, formato_id: int | None = None) -> dict:
    """Briefing completo (perfil + framework + regras + schema) — serve ao LangChain e ao MCP."""
    p = obter_perfil(perfil_id)
    fid = formato_id or p["format_id"]
    fmt = get_format(fid)
    seg = " → ".join(f"{s['name']} ({s['start']}–{s['end']} s)" for s in fmt["segments"])
    d = fmt["duration"]
    return {"perfil": {**p, "negocio": negocio or p["negocio"]}, "formato": {"id": fid, "name": fmt["name"], "segmentos": seg},
            "regras": REGRAS.format(formato=fmt["name"], segmentos=seg, dmin=d["min"], dmax=d["max"],
                                    perfil_id=perfil_id, formato_id=fid),
            "schema": CriativoSpec.model_json_schema()}


def _posprocessar(spec: CriativoSpec, perfil_id: str, fid: int, negocio: str | None, provedor: str) -> CriativoSpec:
    p = obter_perfil(perfil_id)
    dados = spec.model_dump()
    dados.update(perfil_id=perfil_id, formato_id=fid, negocio=negocio or p["negocio"],
                 paleta=Paleta(**p["paleta"]).model_dump(), cta_canal=p["cta_canal"], gerado_por=provedor)
    return CriativoSpec(**dados)  # revalida


def gerar_spec(perfil_id: str, negocio: str | None = None, formato_id: int | None = None,
               instrucoes: str | None = None) -> CriativoSpec:
    """LLM (LangChain, saída estruturada) com validação; qualquer falha ⇒ roteiro offline."""
    obter_perfil(perfil_id)
    nome, modelo = escolher_llm()
    fid = formato_id or obter_perfil(perfil_id)["format_id"]
    if modelo is None:
        log.info("modality=criativo tier=template provider=template_engine reason=sem_chave_ou_offline")
        return spec_offline(perfil_id, negocio, fid)
    try:
        from langchain_core.prompts import ChatPromptTemplate
        b = briefing(perfil_id, negocio, fid)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{regras}"),
            ("human", "Perfil (JSON):\n{perfil}\n\nGere o CriativoSpec.{extra}")])
        cadeia = prompt | modelo.with_structured_output(CriativoSpec)
        bruto = cadeia.invoke({"regras": b["regras"], "perfil": json.dumps(b["perfil"], ensure_ascii=False),
                               "extra": f"\nInstruções extras: {instrucoes}" if instrucoes else ""})
        spec = _posprocessar(bruto if isinstance(bruto, CriativoSpec) else CriativoSpec(**bruto),
                             perfil_id, fid, negocio, f"langchain:{nome}")
        log.info("modality=criativo tier=llm provider=%s reason=ok", nome)
        return spec
    except Exception as exc:
        log.warning("modality=criativo tier=template provider=template_engine reason=llm_falhou(%s)", str(exc)[:200])
        return spec_offline(perfil_id, negocio, fid)
