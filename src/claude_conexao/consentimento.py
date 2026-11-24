"""Consentimento e token de acesso do "Conectar Claude" (fonte única de escopos: ESCOPOS).

Armazena em workspace/claude_conexao/estado.json: escopos aceitos, versão do texto, data e o HASH do token do MCP
(o token em si só aparece uma vez, na criação). Revogar apaga tudo e derruba o token na próxima chamada.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
from pathlib import Path

ESCOPOS = {
    "read:projetos": "Seus projetos (ramos de negócio) e a marca de cada um",
    "read:criativos": "Os criativos/Reels que você gerou e o raciocínio de cada um",
    "read:historico": "O histórico das suas conversas com o assistente",
}
ESCOPOS_PADRAO = list(ESCOPOS)
VERSAO_TEXTO = "2026-11-v1"
TEXTO = ("Ao conectar, o assistente (Claude, da Anthropic) poderá ler os dados marcados abaixo para responder melhor. "
         "Esses trechos são enviados à Anthropic para gerar cada resposta. Você pode desconectar a qualquer momento; "
         "isso apaga o acesso e o cache de contexto.")
_LOCK = threading.Lock()


def _arq() -> Path:
    d = Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve() / "claude_conexao"
    d.mkdir(parents=True, exist_ok=True)
    return d / "estado.json"


def _ler() -> dict:
    try:
        return json.loads(_arq().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def estado() -> dict:
    e = _ler()
    return {"conectado": bool(e.get("conectado")), "escopos": e.get("escopos", []), "desde": e.get("desde"),
            "versao_texto": e.get("versao_texto"), "texto": TEXTO, "versao_texto_atual": VERSAO_TEXTO,
            "escopos_disponiveis": ESCOPOS}


def conectar(escopos: list[str] | None = None) -> dict:
    """Registra o consentimento e emite um token novo para o MCP (devolvido uma única vez)."""
    escopos = [s for s in (ESCOPOS_PADRAO if escopos is None else escopos) if s in ESCOPOS]
    if not escopos:
        raise ValueError("Marque pelo menos um tipo de dado para compartilhar.")
    token = "isc_" + secrets.token_urlsafe(32)
    with _LOCK:
        _arq().write_text(json.dumps({"conectado": True, "escopos": escopos, "desde": int(time.time()),
                                      "versao_texto": VERSAO_TEXTO, "token_hash": _hash(token)}), encoding="utf-8")
    return {**estado(), "token_mcp": token}


def desconectar() -> dict:
    with _LOCK:
        _arq().write_text(json.dumps({"conectado": False}), encoding="utf-8")
    from src.claude_conexao import chat
    chat.apagar_historico()
    return estado()


def escopos_do_token(token: str) -> list[str] | None:
    """Escopos do token do MCP, ou None se inválido/revogado."""
    e = _ler()
    if not e.get("conectado") or not token or not secrets.compare_digest(e.get("token_hash", ""), _hash(token)):
        return None
    return list(e.get("escopos", []))


def exigir(escopo: str) -> None:
    if escopo not in estado()["escopos"] or not estado()["conectado"]:
        raise PermissionError(f"Sem consentimento para '{escopo}'. Conecte o Claude e marque esse dado.")
