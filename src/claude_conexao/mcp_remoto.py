"""Servidor MCP remoto (HTTP streamable) da plataforma, somente leitura, protegido por token Bearer revogável.

Uso:  python -m src.claude_conexao.mcp_remoto --host 0.0.0.0 --port 8765
Claude Code:  claude mcp add --transport http impulso-plataforma https://SEU-HOST/mcp --header "Authorization: Bearer <token>"
O token é emitido ao clicar em "Conectar Claude" e invalidado em "Desconectar". (OAuth 2.1 completo: ver docs/conexao-claude.md.)
"""
from __future__ import annotations

import argparse
import contextvars
import os

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from src.claude_conexao import contexto
from src.claude_conexao.consentimento import escopos_do_token

URL_PUBLICA = os.getenv("MCP_PUBLIC_URL", "http://127.0.0.1:8765")
_ESCOPOS_DA_CHAMADA: contextvars.ContextVar[list[str]] = contextvars.ContextVar("escopos", default=[])


class VerificadorLocal(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        escopos = escopos_do_token(token)
        return None if escopos is None else AccessToken(token=token, client_id="claude", scopes=escopos)


def criar() -> FastMCP:
    mcp = FastMCP("ImpulsoStone-Plataforma", instructions="Contexto somente leitura da plataforma Impulso Stone do usuário.",
                  token_verifier=VerificadorLocal(),
                  auth=AuthSettings(issuer_url=AnyHttpUrl(URL_PUBLICA), resource_server_url=AnyHttpUrl(URL_PUBLICA + "/mcp"),
                                    required_scopes=[], validate_token_resource=False))
    for nome, fn in contexto.FERRAMENTAS.items():
        mcp.tool(name=nome, description=(fn.__doc__ or nome).strip().splitlines()[0])(fn)
    return mcp


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args(argv)
    m = criar()
    m.settings.host, m.settings.port = a.host, a.port
    m.run(transport="streamable-http")


if __name__ == "__main__":
    main()
