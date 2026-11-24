"""Contexto somente leitura da plataforma (usado pelo chat e pelo MCP). Cada função exige o escopo correspondente."""
from __future__ import annotations

import json
import re
from typing import Any

from src.claude_conexao.consentimento import exigir
from src.criativos.spec import carregar_perfis

LIMITE = 20


def list_projects() -> list[dict]:
    exigir("read:projetos")
    return [{"id": pid, "nome": p["nome"], "negocio": p["negocio"], "cnae": p["cnae"]} for pid, p in carregar_perfis().items()]


def get_brand_guidelines(project_id: str) -> dict:
    exigir("read:projetos")
    p = carregar_perfis().get(project_id)
    if not p:
        raise KeyError("Projeto inexistente.")
    return {k: p.get(k) for k in ("nome", "negocio", "paleta", "gancho", "dor")}


def _criativo(pid: str) -> dict | None:
    from src.criativos import api
    try:
        return api.detalhe(pid)
    except KeyError:
        return None


def list_creatives(project_id: str | None = None, pagina: int = 0) -> list[dict]:
    exigir("read:criativos")
    from src.criativos import api
    itens = [i for i in api.listar() if i["gerado"] and (project_id in (None, "", i["id"]))]
    return itens[pagina * LIMITE:(pagina + 1) * LIMITE]


def get_item(item_id: str) -> dict:
    exigir("read:criativos")
    if not re.fullmatch(r"[a-z0-9_]{1,60}", item_id or ""):
        raise ValueError("Identificador inválido.")
    d = _criativo(item_id)
    if d is None:
        raise KeyError("Item não encontrado.")
    return json.loads(json.dumps(d, default=str))


def search_context(query: str, limite: int = 10) -> list[dict[str, Any]]:
    """Busca simples por palavras em projetos, criativos e histórico (apenas os escopos consentidos)."""
    from src.claude_conexao.consentimento import estado
    termos = [t for t in re.findall(r"\w+", (query or "").lower()) if len(t) > 2][:8]
    if not termos:
        return []
    ok = set(estado()["escopos"]) if estado()["conectado"] else set()
    achados: list[tuple[int, dict]] = []

    def pontua(txt: str) -> int:
        t = txt.lower()
        return sum(t.count(x) for x in termos)

    if "read:projetos" in ok:
        for p in list_projects():
            s = pontua(json.dumps(p, ensure_ascii=False))
            if s:
                achados.append((s, {"tipo": "projeto", **p}))
    if "read:criativos" in ok:
        for c in list_creatives():
            s = pontua(json.dumps(c, ensure_ascii=False, default=str))
            if s:
                achados.append((s, {"tipo": "criativo", "id": c["id"], "nome": c["nome"], "gancho": c.get("gancho")}))
    if "read:historico" in ok:
        from src.claude_conexao import chat
        for m in chat.historico()[-200:]:
            s = pontua(m["texto"])
            if s:
                achados.append((s, {"tipo": "conversa", "papel": m["papel"], "trecho": m["texto"][:300]}))
    achados.sort(key=lambda x: -x[0])
    return [a for _, a in achados[:min(limite, LIMITE)]]


FERRAMENTAS = {"search_context": search_context, "get_item": get_item, "list_projects": list_projects,
               "list_creatives": list_creatives, "get_brand_guidelines": get_brand_guidelines}
