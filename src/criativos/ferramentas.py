"""Ferramentas LangChain (mesmos casos de uso do MCP) e agente opcional.

`criar_agente()` monta um agente LangChain que usa Claude/Gemini (chaves do usuário) e chama estas ferramentas.
Para usar o servidor MCP a partir de LangChain, veja docs/CRIATIVOS.md (langchain-mcp-adapters).
"""
from __future__ import annotations

import json

from langchain_core.tools import tool

from src.criativos import servico
from src.criativos.llm import briefing, escolher_llm
from src.criativos.spec import CriativoSpec, carregar_perfis


@tool
def listar_perfis() -> str:
    """Lista os 10 perfis prioritários de MPE (id, nome, CNAE, formato)."""
    return json.dumps([{"id": k, "nome": v["nome"], "cnae": v["cnae"], "formato": v["format_id"]}
                       for k, v in carregar_perfis().items()], ensure_ascii=False)


@tool
def briefing_perfil(perfil_id: str) -> str:
    """Briefing do perfil: material de marca, framework do formato, regras e JSON Schema do CriativoSpec."""
    return json.dumps(briefing(perfil_id), ensure_ascii=False)


@tool
def validar_criativo(spec_json: str) -> str:
    """Valida um CriativoSpec (JSON) sem renderizar; devolve 'ok' ou os erros."""
    try:
        CriativoSpec(**json.loads(spec_json))
        return "ok"
    except Exception as exc:
        return f"inválido: {exc}"


@tool
def renderizar_criativo_tool(spec_json: str) -> str:
    """Renderiza um CriativoSpec (JSON) em MP4 1080x1920 e devolve caminho e auditoria."""
    return json.dumps(servico.renderizar_json(spec_json), ensure_ascii=False, default=str)


FERRAMENTAS = [listar_perfis, briefing_perfil, validar_criativo, renderizar_criativo_tool]


def criar_agente():
    nome, modelo = escolher_llm()
    if modelo is None:
        raise RuntimeError("Nenhuma chave de IA configurada (ANTHROPIC_API_KEY ou GOOGLE_API_KEY); "
                           "use o modo offline (python -m src.criativos.gerar) ou conecte via MCP.")
    from langchain.agents import create_agent
    return create_agent(modelo, FERRAMENTAS,
                        system_prompt="Você cria Reels em motion graphics para MPEs. Fluxo: briefing_perfil → "
                                      "escreva o CriativoSpec → validar_criativo → renderizar_criativo_tool.")
