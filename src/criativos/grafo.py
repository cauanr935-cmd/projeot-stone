"""Pipeline LangGraph do criativo, com rastro de raciocínio (o que o front exibe).

perfil → formato → referências → padrões → roteiro → validação ─┬→ (retry roteiro, 1x) ─┘
                                                               └→ renderização → fim
Cada nó acrescenta ao `trace` um passo {no, titulo, resumo, detalhes}. O roteiro usa a IA do usuário via LangChain
(Claude/Gemini) com as referências no prompt; sem chave, usa o template determinístico + motivos calculados da base.
"""
from __future__ import annotations

import json
import logging
import operator
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.core.config import get_format, load_cnae_profiles
from src.criativos import referencias as refs
from src.criativos.llm import _posprocessar, briefing, escolher_llm
from src.criativos.spec import Cena, CriativoSpec, obter_perfil, spec_do_roteiro, spec_offline

log = logging.getLogger("criativos.grafo")


class Estado(TypedDict, total=False):
    perfil_id: str
    perfil_override: dict | None
    roteiro_usuario: str | None
    nome_base: str | None
    negocio: str | None
    formato_id: int | None
    instrucoes: str | None
    com_voz: bool
    renderizar: bool
    pasta: str | None
    perfil: dict
    segmento: str
    referencias: list[dict]
    padroes: dict
    spec: dict
    erro_validacao: str | None
    tentativas: int
    saida: dict
    trace: Annotated[list[dict], operator.add]


def _passo(no: str, titulo: str, resumo: str, **detalhes: Any) -> list[dict]:
    return [{"no": no, "titulo": titulo, "resumo": resumo, "detalhes": detalhes}]


# --------------------------------------------------------------------------- nós
def n_perfil(s: Estado) -> dict:
    p = obter_perfil(s["perfil_id"])
    cnae = load_cnae_profiles()
    seg = p.get("segmento") or next((v["segment"] for k, v in cnae["profiles"].items() if k == p["cnae"]), "")
    p = {**p, **(s.get("perfil_override") or {}), "negocio": s.get("negocio") or p["negocio"]}
    return {"perfil": p, "segmento": seg, "tentativas": 0,
            "trace": _passo("perfil", "Entendi o negócio", f"{p['nome']}{' (CNAE ' + p['cnae'] + ')' if p.get('cnae') else ''}, dor central: {p['dor'].lower()}.",
                            cnae=p["cnae"], segmento=seg, dor=p["dor"], solucao=p["solucao"], cta=p["cta"])}


def n_formato(s: Estado) -> dict:
    p = s["perfil"]
    fid = s.get("formato_id") or p["format_id"]
    fmt = get_format(fid)
    pan = refs.panorama() if refs.base_disponivel() else []
    atual = next((x for x in pan if x["format_id"] == fid), None)
    if s.get("formato_id") and s["formato_id"] != p["format_id"]:
        porque = f"Formato {fmt['name']} escolhido manualmente (o padrão do segmento seria {get_format(p['format_id'])['name']})."
    else:
        porque = (f"A pesquisa mapeia o segmento '{s['segmento']}' ao formato {fmt['name']} ({fmt['focus']}).")
    if atual:
        porque += (f" Na base, esse formato aparece em {atual['pct']}% do top 10% (n={atual['n']}), com score relativo "
                   f"mediano de {atual['score_mediana']}.")
    else:
        porque += " (Base de Reels indisponível neste ambiente: justificativa só pela pesquisa.)"
    return {"formato_id": fid, "trace": _passo("formato", f"Escolhi o formato {fmt['name']}", porque, formato_id=fid,
                                              framework=[x["name"] for x in fmt["segments"]], panorama=pan)}


def n_referencias(s: Estado) -> dict:
    r = refs.buscar(s["formato_id"], s["segmento"], 3) if refs.base_disponivel() else []
    resumo = (f"Selecionei {len(r)} Reels do top 10% da base como referência de estrutura e gancho."
              if r else "Sem base local: criativo apoiado apenas no framework da pesquisa.")
    return {"referencias": r, "trace": _passo("referencias", "Referências usadas", resumo, referencias=r)}


def n_padroes(s: Estado) -> dict:
    pad = refs.padroes(s["formato_id"]) if refs.base_disponivel() else {}
    if pad:
        txt = (f"No top 10% do formato: ~{pad['duracao_mediana_s']:.0f} s, {pad['wpm_mediana']:.0f} palavras/min, "
               f"{pad['cortes_min_mediana']} cortes/min, fala começa em 0 s em {pad['fala_inicia_em_0s_pct']}% dos Reels, "
               f"gancho de ~{pad['hook_palavras_mediana']:.0f} palavras. Adotei: gancho imediato (≤ 5 palavras na tela), "
               "ritmo visual mais rápido que o falado, 1 ideia por cena.")
    else:
        txt = "Sem padrões medidos; apliquei as regras da pesquisa (Frame Zero ≤ 5 palavras, CTA único)."
    return {"padroes": pad, "trace": _passo("padroes", "Padrões que aprendi", txt, padroes=pad)}


def _motivos(spec: CriativoSpec, s: Estado) -> CriativoSpec:
    pad, r, p = s.get("padroes") or {}, s.get("referencias") or [], s["perfil"]
    gancho_ref = next((x["gancho"] for x in r if x["gancho"]), "")
    base = {
        "hook": ("Gancho em poucas palavras no 1º segundo: " + (f"o Reel nº1 de referência abre com “{gancho_ref}”, "
                 if gancho_ref else "") + f"e {pad.get('fala_inicia_em_0s_pct', '~90')}% do formato começa a falar em 0 s. "
                 f"Fala direto com a dor: {p['dor'].lower()}."),
        "pontos": "Uma ideia por cartão, entrando em sequência para manter o ritmo; cada item vem do material real do perfil, "
                  "sem inventar prazo ou garantia.",
        "antes_depois": "Contraste visual é a prova mais rápida do formato BAB: o espectador entende a transformação sem ler.",
        "numero": "Um número grande dá concretude e reduz objeção (preço, prazo ou frequência) sem prometer resultado.",
        "cta": f"CTA único, no canal que o cliente já usa ({p['cta_canal']}), com a prova social logo antes para fechar a decisão.",
    }
    cenas = [c.model_copy(update={"motivo": c.motivo or base[c.tipo]}) for c in spec.cenas]
    return spec.model_copy(update={"cenas": cenas})


def n_roteiro(s: Estado) -> dict:
    nome, modelo = escolher_llm()
    tent = s.get("tentativas", 0) + 1
    spec, via = None, "template_engine"
    if s.get("roteiro_usuario") and tent == 1:
        try:
            spec, via = spec_do_roteiro(s["perfil_id"], s["roteiro_usuario"], s["perfil"]["negocio"], s["formato_id"], s["perfil"]), "roteiro_do_usuario"
        except ValueError as exc:
            log.info("roteiro do usuário não aproveitado (%s)", exc)
    if spec is None and modelo is not None and tent == 1:
        try:
            from langchain_core.prompts import ChatPromptTemplate
            b = briefing(s["perfil_id"], s["perfil"]["negocio"], s["formato_id"])
            ref_txt = json.dumps([{k: x[k] for k in ("gancho", "trecho", "duracao_s", "por_que")} for x in s["referencias"]],
                                 ensure_ascii=False)
            pad_txt = json.dumps(s.get("padroes") or {}, ensure_ascii=False)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "{regras}\nPreencha 'motivo' de cada cena explicando a decisão com base nas referências/padrões."),
                ("human", "Perfil:\n{perfil}\n\nReferências reais (top 10% da base):\n{refs}\n\nPadrões medidos:\n{pad}\n"
                          "{extra}\nGere o CriativoSpec.")])
            bruto = (prompt | modelo.with_structured_output(CriativoSpec)).invoke({
                "regras": b["regras"], "perfil": json.dumps(b["perfil"], ensure_ascii=False), "refs": ref_txt, "pad": pad_txt,
                "extra": f"Instruções extras: {s['instrucoes']}" if s.get("instrucoes") else ""})
            spec = _posprocessar(bruto if isinstance(bruto, CriativoSpec) else CriativoSpec(**bruto),
                                 s["perfil_id"], s["formato_id"], s["perfil"]["negocio"], f"langchain:{nome}")
            via = f"langchain:{nome}"
        except Exception as exc:
            log.warning("roteiro via LLM falhou (%s); usando template", str(exc)[:200])
    if spec is None:
        spec = spec_offline(s["perfil_id"], s["perfil"]["negocio"], s["formato_id"], s["perfil"])
    spec = _motivos(spec, s)
    return {"spec": spec.model_dump(), "tentativas": tent,
            "trace": _passo("roteiro", "Escrevi o roteiro",
                            f"{len(spec.cenas)} cenas via {via}" + (" (tentativa de correção)" if tent > 1 else "") + ".",
                            motor=via, cenas=[{"tipo": c.tipo, "titulo": c.titulo, "narracao": c.narracao, "motivo": c.motivo}
                                               for c in spec.cenas])}


def n_validar(s: Estado) -> dict:
    try:
        spec = CriativoSpec(**s["spec"])
        palavras = sum(len(c.narracao.split()) for c in spec.cenas)
        return {"erro_validacao": None, "trace": _passo("validacao", "Validei contra as regras",
                f"Estrutura ok, Frame Zero com {len(spec.hook_overlay.split())} palavras, {palavras} palavras narradas.",
                hook_overlay=spec.hook_overlay, palavras_narradas=palavras)}
    except Exception as exc:
        return {"erro_validacao": str(exc)[:300], "spec": spec_offline(s["perfil_id"], s["perfil"]["negocio"], s["formato_id"], s["perfil"]).model_dump(),
                "trace": _passo("validacao", "Roteiro reprovado; refazendo", str(exc)[:300])}


def rota_validacao(s: Estado) -> str:
    return "roteiro" if s.get("erro_validacao") and s.get("tentativas", 0) < 2 else ("render" if s.get("renderizar", True) else "fim")


def n_render(s: Estado) -> dict:
    from src.criativos import servico
    spec = CriativoSpec(**s["spec"])
    pasta = Path(s["pasta"]) if s.get("pasta") else None
    out = servico.renderizar_spec(spec, pasta, s.get("com_voz", True), nome_base=s.get("nome_base"))
    aud = out.get("auditoria", {})
    return {"saida": out, "trace": _passo("render", "Renderizei e auditei",
            f"{out['duracao_s']} s, 1080×1920, voz={'sim' if out['voz'] else 'não'}; auditoria {'aprovada' if aud.get('passou') else 'com ressalvas'}.",
            duracao_s=out["duracao_s"], auditoria=aud)}


def construir():
    g = StateGraph(Estado)
    for nome, fn in [("perfil", n_perfil), ("formato", n_formato), ("referencias", n_referencias), ("padroes", n_padroes),
                     ("roteiro", n_roteiro), ("validar", n_validar), ("render", n_render)]:
        g.add_node(nome, fn)
    g.add_edge(START, "perfil")
    for a, b in [("perfil", "formato"), ("formato", "referencias"), ("referencias", "padroes"), ("padroes", "roteiro"),
                 ("roteiro", "validar")]:
        g.add_edge(a, b)
    g.add_conditional_edges("validar", rota_validacao, {"roteiro": "roteiro", "render": "render", "fim": END})
    g.add_edge("render", END)
    return g.compile()


def executar(perfil_id: str, negocio: str | None = None, formato_id: int | None = None, instrucoes: str | None = None,
             pasta: Path | None = None, com_voz: bool = True, renderizar: bool = True,
             perfil_override: dict | None = None, roteiro_usuario: str | None = None, nome_base: str | None = None) -> dict:
    """Roda o grafo; devolve {spec, trace, referencias, padroes, saida} e grava <perfil>_f<N>.raciocinio.json."""
    obter_perfil(perfil_id)
    final = construir().invoke({"perfil_id": perfil_id, "negocio": negocio, "formato_id": formato_id, "instrucoes": instrucoes,
                                "pasta": str(pasta) if pasta else None, "com_voz": com_voz, "renderizar": renderizar,
                                "perfil_override": perfil_override, "roteiro_usuario": roteiro_usuario, "nome_base": nome_base,
                                "trace": []})
    resultado = {"perfil_id": perfil_id, "formato_id": final["formato_id"], "perfil": final["perfil"],
                 "referencias": final["referencias"], "padroes": final["padroes"], "spec": final["spec"],
                 "trace": final["trace"], "saida": final.get("saida")}
    from src.criativos.servico import SAIDA_PADRAO
    d = Path(pasta or SAIDA_PADRAO)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{nome_base or perfil_id + '_f' + str(final['formato_id'])}.raciocinio.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return resultado
