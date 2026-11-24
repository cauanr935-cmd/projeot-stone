"""Valida exemplos/catalogo.yaml contra o projeto e gera exemplos/README.md.

Uso:  .venv/bin/python scripts/exemplos.py [--check]
--check só valida (exit 1 se algo citado não existir).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
STATUS = {
    "local": "Roda aqui, sem chave e sem rede",
    "rede": "Precisa de rede/instalação na 1ª vez",
    "chave": "Bloqueado: exige chave de API",
}
NIVEL = {1: "comece aqui", 2: "intermediário", 3: "avançado"}


def _nomes_decorados(arquivo: Path, decorador: str) -> set[str]:
    texto = arquivo.read_text(encoding="utf-8")
    achados: set[str] = set()
    for m in re.finditer(rf"@mcp\.{decorador}\(([^)]*)\)\s*\n(?:async )?def (\w+)", texto):
        arg = re.search(r'"([^"]+)"', m.group(1))
        achados.add(arg.group(1) if decorador == "prompt" and arg else m.group(2))
    return achados


def _tools_plataforma() -> set[str]:
    texto = (RAIZ / "src/claude_conexao/contexto.py").read_text(encoding="utf-8")
    return set(re.findall(r"def (search_context|get_item|list_projects|list_creatives|get_brand_guidelines)\b", texto))


def validar(cat: dict) -> list[str]:
    erros: list[str] = []
    tools = _nomes_decorados(RAIZ / "src/mcp_server.py", "tool") | _tools_plataforma()
    prompts = _nomes_decorados(RAIZ / "src/mcp_server.py", "prompt")
    skills = {p.name for p in (RAIZ / ".claude/skills").iterdir() if (p / "SKILL.md").exists()}
    perfis = {p["id"] for p in yaml.safe_load((RAIZ / "config/perfis_prioritarios.yaml").read_text("utf-8"))["perfis"]}
    ids: set[str] = set()
    for ex in cat["exemplos"]:
        i = ex["id"]
        if i in ids:
            erros.append(f"{i}: id duplicado")
        ids.add(i)
        if ex["grupo"] not in cat["grupos"]:
            erros.append(f"{i}: grupo desconhecido {ex['grupo']}")
        if ex["status"] not in STATUS:
            erros.append(f"{i}: status inválido {ex['status']}")
        usa = ex.get("usa", {})
        for t in usa.get("tools", []):
            if t not in tools:
                erros.append(f"{i}: tool inexistente {t}")
        for p in usa.get("prompts", []):
            if p not in prompts:
                erros.append(f"{i}: prompt MCP inexistente {p}")
        for s in usa.get("skills", []):
            if s not in skills:
                erros.append(f"{i}: skill não instalada {s}")
        for p in ex.get("perfis", []):
            if p not in perfis:
                erros.append(f"{i}: perfil inexistente {p}")
        for campo in ("entrada",):
            for caminho in re.findall(r"(?:tests|output)/[\w./-]+", ex.get(campo, "")):
                if not (RAIZ / caminho.rstrip(".,)")).exists():
                    erros.append(f"{i}: caminho de {campo} não existe: {caminho}")
        if "cli" in ex:
            m = re.search(r"python -m ([\w.]+)", ex["cli"])
            if m and not (RAIZ / (m.group(1).replace(".", "/") + ".py")).exists():
                erros.append(f"{i}: módulo do CLI não existe: {m.group(1)}")
        if not ex.get("prompt", "").strip():
            erros.append(f"{i}: sem prompt")
    return erros


def gerar_readme(cat: dict) -> str:
    L = [
        "# Base de exemplos: Claude + MCP + skills",
        "",
        "> Gerado por `python scripts/exemplos.py` a partir de `exemplos/catalogo.yaml`. Edite o catálogo, não este arquivo.",
        "> Como configurar tudo: [`docs/TUTORIAL_CLAUDE.md`](../docs/TUTORIAL_CLAUDE.md).",
        "",
        f"{len(cat['exemplos'])} exemplos. Copie o **Prompt** para o Claude Code aberto nesta pasta (o MCP `impulso-stone-reels` e as skills já são carregados do projeto).",
        "",
        "| Selo | Significado |", "|---|---|",
        *[f"| `{k}` | {v} |" for k, v in STATUS.items()],
        "",
        "## Índice",
        "",
        "| Exemplo | Nível | Selo | Usa |", "|---|---|---|---|",
    ]
    for ex in cat["exemplos"]:
        usa = ex.get("usa", {})
        itens = [*usa.get("tools", []), *[f"/{s}" for s in usa.get("skills", [])], *usa.get("prompts", [])]
        L.append(f"| [{ex['titulo']}](#{ex['id']}) | {NIVEL[ex['nivel']]} | `{ex['status']}` | {', '.join(f'`{x}`' for x in itens)} |")
    for g, titulo in cat["grupos"].items():
        L += ["", f"## {titulo}"]
        for ex in (e for e in cat["exemplos"] if e["grupo"] == g):
            L += ["", f'<a id="{ex["id"]}"></a>', f"### {ex['titulo']}", "",
                  f"**Resultado:** {ex['resultado']}  ", f"**Selo:** `{ex['status']}`, nível: {NIVEL[ex['nivel']]}", "",
                  "**Prompt:**", "", "```text", ex["prompt"].strip(), "```"]
            if ex.get("entrada"):
                L += ["", f"**Entrada:** {ex['entrada']}"]
            if ex.get("cli"):
                L += ["", "**Sem o Claude (CLI):**", "", "```bash", ex["cli"], "```"]
            if ex.get("saida"):
                L += ["", f"**Saída:** {ex['saida']}"]
            if ex.get("observacao"):
                L += ["", f"> {ex['observacao']}"]
    return "\n".join(L) + "\n"


def main() -> int:
    cat = yaml.safe_load((RAIZ / "exemplos/catalogo.yaml").read_text("utf-8"))
    erros = validar(cat)
    for e in erros:
        print("ERRO:", e)
    if erros:
        return 1
    print(f"OK: {len(cat['exemplos'])} exemplos válidos")
    if "--check" not in sys.argv:
        (RAIZ / "exemplos/README.md").write_text(gerar_readme(cat), encoding="utf-8")
        print("gerado exemplos/README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
