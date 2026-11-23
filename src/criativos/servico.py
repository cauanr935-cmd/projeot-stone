"""Casos de uso compartilhados por CLI, MCP e LangChain."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from src.core.config import ROOT
from src.criativos.llm import gerar_spec
from src.criativos.motion import renderizar_criativo
from src.criativos.spec import CriativoSpec, carregar_perfis

SAIDA_PADRAO = ROOT / "output" / "criativos"


def _auditar(video: Path, formato_id: int) -> dict:
    caminho = ROOT / "tests" / "verify_final_reel.py"
    spec = importlib.util.spec_from_file_location("verify_final_reel", caminho)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[spec.name] = mod  # type: ignore[union-attr]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    r = mod.audit_reel(video, formato_id)
    return {"passou": r["passed"], "reprovados": [c for c in r["checks"] if not c["ok"]]}


def renderizar_spec(spec: CriativoSpec, pasta: Path | None = None, com_voz: bool = True, auditar: bool = True,
                    nome_base: str | None = None) -> dict:
    pasta = Path(pasta or SAIDA_PADRAO)
    pasta.mkdir(parents=True, exist_ok=True)
    base = nome_base or f"{spec.perfil_id}_f{spec.formato_id}"
    (pasta / f"{base}.spec.json").write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    r = renderizar_criativo(spec, pasta / f"{base}.mp4", com_voz=com_voz)
    if auditar:
        r["auditoria"] = _auditar(Path(r["output"]), spec.formato_id)
    r["spec"] = str(pasta / f"{base}.spec.json")
    return r


def gerar_criativo(perfil_id: str, pasta: Path | None = None, negocio: str | None = None,
                   formato_id: int | None = None, instrucoes: str | None = None, com_voz: bool = True) -> dict:
    """Roda o grafo LangGraph (perfil→formato→referências→roteiro→validação→render) e devolve saída + raciocínio."""
    from src.criativos.grafo import executar
    r = executar(perfil_id, negocio, formato_id, instrucoes, pasta, com_voz)
    return {**r["saida"], "trace": r["trace"], "referencias": r["referencias"]}


def gerar_lote(perfis: list[str] | None = None, pasta: Path | None = None, com_voz: bool = True) -> list[dict]:
    resultados = []
    for pid in perfis or list(carregar_perfis()):
        try:
            resultados.append(gerar_criativo(pid, pasta, com_voz=com_voz))
        except Exception as exc:
            resultados.append({"perfil_id": pid, "erro": str(exc)})
    return resultados


def renderizar_json(spec_json: str | dict, pasta: Path | None = None, com_voz: bool = True) -> dict:
    dados = json.loads(spec_json) if isinstance(spec_json, str) else spec_json
    return renderizar_spec(CriativoSpec(**dados), pasta, com_voz)
