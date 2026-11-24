"""Sessões de criação: guardam a conversa (entrevista criativa, pedido de edição, carrossel) e os arquivos gerados.

Um JSON por sessão em output/sessoes/<id>.json:
  {id, titulo, tipo: entrevista|edicao|carrossel, perfil, criada_em, atualizada_em,
   mensagens: [{papel: pessoa|assistente, texto, t}], artefatos: [{tipo, url, rotulo, t}]}
Na primeira listagem, as edições que já existem em output/edicoes/ e output/pedidos/ são importadas
(pedido + resumo + vídeo); conversas antigas do navegador nunca foram gravadas e não podem ser recuperadas.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import ROOT

PASTA = ROOT / "output" / "sessoes"
LOCK = threading.Lock()
ID = re.compile(r"[a-f0-9]{12}")
TIPOS = {"entrevista", "edicao", "carrossel"}
MAX_MSGS, MAX_TEXTO = 300, 12000


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _arq(sid: str) -> Path:
    if not ID.fullmatch(sid):
        raise ValueError("Sessão inválida.")
    return PASTA / f"{sid}.json"


def _ler(sid: str) -> dict | None:
    try:
        return json.loads(_arq(sid).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _gravar(s: dict) -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    arq = _arq(s["id"])
    tmp = arq.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(arq)


def _titulo(msgs: list[dict]) -> str:
    for m in msgs:
        if m["papel"] == "pessoa":
            return " ".join(m["texto"].split())[:70]
    return "Nova sessão"


def salvar(sid: str | None, tipo: str, mensagens: list[dict] | None = None, artefatos: list[dict] | None = None,
           perfil: str = "", titulo: str = "", modo: str = "", anexos: list[dict] | None = None) -> dict:
    """Cria (sid vazio) ou acrescenta mensagens/artefatos a uma sessão. Devolve a sessão."""
    if tipo not in TIPOS:
        raise ValueError("Tipo de sessão inválido.")
    novas = [{"papel": "assistente" if m.get("papel") == "assistente" else "pessoa",
              "texto": str(m.get("texto", "")).strip()[:MAX_TEXTO], "t": _agora()}
             for m in (mensagens or []) if str(m.get("texto", "")).strip()]
    arts = [{"tipo": str(a.get("tipo", "arquivo"))[:20], "url": str(a.get("url", ""))[:300],
             "rotulo": str(a.get("rotulo", ""))[:80], "t": _agora()}
            for a in (artefatos or []) if str(a.get("url", "")).startswith("/api/")]
    with LOCK:
        s = _ler(sid) if sid else None
        if sid and not s:
            raise ValueError("Sessão não encontrada.")
        if not s:
            s = {"id": uuid.uuid4().hex[:12], "titulo": "", "tipo": tipo, "perfil": perfil, "criada_em": _agora(),
                 "mensagens": [], "artefatos": []}
        usados = [a["rotulo"] for a in s["artefatos"]]
        for a in arts:  # mesmo rótulo de novo = nova versão: "Vídeo" → "Vídeo v2" → "Vídeo v3"
            base = a["rotulo"]
            n = sum(1 for r in usados if r == base or r.startswith(base + " v")) if base else 0
            if n:
                a["rotulo"] = f"{base} v{n + 1}"
            usados.append(a["rotulo"])
        ja = {x.get("caminho") for x in s.get("anexos", [])}
        s["anexos"] = s.get("anexos", []) + [
            {"nome": str(x.get("nome", ""))[:120], "tipo": str(x.get("tipo", ""))[:12], "caminho": str(x["caminho"]),
             "duracao_s": x.get("duracao_s")} for x in (anexos or []) if x.get("caminho") and x["caminho"] not in ja]
        s["mensagens"] = (s["mensagens"] + novas)[-MAX_MSGS:]
        s["artefatos"] = s["artefatos"] + arts
        if perfil:
            s["perfil"] = perfil
        if modo in {"motion", "edicao"}:
            s["modo"] = modo
        s["titulo"] = (titulo.strip()[:100] or s["titulo"] or _titulo(s["mensagens"]))
        s["atualizada_em"] = _agora()
        _gravar(s)
    return s


def obter(sid: str) -> dict | None:
    return _ler(sid)


def voltar(sid: str, n: int) -> dict:
    """Remove as últimas n mensagens da sessão (desfazer na conversa). Não mexe nos arquivos gerados."""
    n = max(1, min(int(n), 20))
    with LOCK:
        s = _ler(sid)
        if not s:
            raise ValueError("Sessão não encontrada.")
        s["mensagens"] = s["mensagens"][:-n]
        s["atualizada_em"] = _agora()
        _gravar(s)
    return s


def renomear(sid: str, titulo: str) -> dict:
    with LOCK:
        s = _ler(sid)
        if not s or not titulo.strip():
            raise ValueError("Sessão não encontrada ou título vazio.")
        s["titulo"] = titulo.strip()[:100]
        _gravar(s)
    return s


def apagar(sid: str) -> None:
    with LOCK:
        _arq(sid).unlink(missing_ok=True)


def importar_existentes() -> int:
    """Uma vez: transforma edições/pedidos já gerados em sessões (id da sessão = id da edição, quando hex12)."""
    marca = PASTA / "_importado"
    if marca.exists():
        return 0
    from src.criativos import memoria_reels
    mem, n = memoria_reels._ler(), 0
    PASTA.mkdir(parents=True, exist_ok=True)
    for pasta in sorted((ROOT / "output" / "edicoes").glob("*/final.mp4")):
        eid = pasta.parent.name
        if not ID.fullmatch(eid) or _ler(eid):
            continue
        r = mem.get(eid, {})
        resumo = ""
        try:
            resumo = (pasta.parent / "resumo.md").read_text(encoding="utf-8").strip()
        except OSError:
            pass
        msgs = ([{"papel": "pessoa", "texto": r["pedido"]}] if r.get("pedido") else []) + \
               ([{"papel": "assistente", "texto": resumo}] if resumo else [])
        arts = [{"tipo": "video", "url": f"/api/edicoes/{eid}/final.mp4", "rotulo": "Vídeo"}]
        for nome, tipo, rot in (("capa.jpg", "imagem", "Capa"), ("legenda.txt", "texto", "Legenda"), ("decupagem.md", "texto", "Decupagem")):
            if (pasta.parent / nome).is_file():
                arts.append({"tipo": tipo, "url": f"/api/edicoes/{eid}/{nome}", "rotulo": rot})
        s = {"id": eid, "titulo": (r.get("pedido") or "Edição importada")[:70] + ("" if r.get("pedido") else f" ({eid[:6]})"),
             "tipo": "edicao", "perfil": "", "mensagens": [{**m, "t": r.get("criado_em", "")} for m in msgs],
             "artefatos": [{**a, "t": r.get("criado_em", "")} for a in arts],
             "criada_em": r.get("criado_em") or datetime.fromtimestamp(pasta.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
             "importada": True}
        s["atualizada_em"] = s["criada_em"]
        _gravar(s)
        n += 1
    marca.write_text(_agora(), encoding="utf-8")
    return n


def listar() -> list[dict]:
    importar_existentes()
    out = []
    for arq in PASTA.glob("*.json"):
        try:
            s = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append({k: s.get(k) for k in ("id", "titulo", "tipo", "perfil", "criada_em", "atualizada_em", "importada")}
                   | {"n_mensagens": len(s.get("mensagens", [])), "n_artefatos": len(s.get("artefatos", []))})
    return sorted(out, key=lambda x: x.get("atualizada_em") or "", reverse=True)


def exportar(sid: str) -> str | None:
    """Texto pronto para colar no Claude Desktop (com o MCP impulso-stone-reels): contexto, conversa, último plano e arquivos."""
    s = _ler(sid)
    if not s:
        return None
    msgs = s.get("mensagens") or []
    def _ult(rx):
        return next((m["texto"] for m in reversed(msgs) if m.get("papel") != "pessoa"
                     and re.search(rx, m.get("texto", ""), re.I)), "")
    plano = _ult(r"plano de edi[cç][aã]o") or _ult(r"ideia central|roteiro")
    conversa = "\n\n".join(f"{'PESSOA' if m.get('papel') == 'pessoa' else 'DIRETOR'}: {m.get('texto', '').strip()}"
                           for m in msgs)
    arqs = []
    for a in s.get("artefatos") or []:
        m = re.match(r"/api/edicoes/([a-f0-9]{12})/(.+)$", a.get("url", ""))
        arqs.append(f"- {a.get('rotulo') or a.get('tipo')}: {ROOT / 'output' / 'edicoes' / m.group(1) / m.group(2)}" if m
                    else f"- {a.get('rotulo') or a.get('tipo')}: {a.get('url')}")
    modo = "EDIÇÃO de vídeo já gravado" if s.get("modo") == "edicao" else "criação (motion graphic)"
    return (f"""# Continuar uma sessão do Impulso Stone Reels
Use o MCP `impulso-stone-reels` (tools como transcrever_audio, build_edit_plan, assemble_and_render_reel, briefing_criativo). Os arquivos listados abaixo já estão na pasta autorizada do MCP; não peça para copiar nada.
Sessão: {s.get('titulo')} · Perfil: {s.get('perfil') or 'MPE'} · Modo: {modo}

## O que fazer
Continue de onde paramos: siga o plano abaixo, transcreva os vídeos, edite e renderize em output/reel_final.mp4 (1080x1920). Não mude o que a pessoa disse. Se faltar algo, pergunte uma coisa por vez.

## Plano / roteiro mais recente
{plano or '(ainda não há plano fechado; use a conversa abaixo)'}

## Vídeos/áudios anexados (já estão na pasta autorizada; use estes caminhos direto)
{chr(10).join(f"- {x['nome']} ({x.get('tipo')}{', ' + str(x['duracao_s']) + ' s' if x.get('duracao_s') else ''}): {x['caminho']}" for x in s.get('anexos', [])) or '(nenhum registrado; peça o caminho ao usuário)'}

## Arquivos já gerados
{chr(10).join(arqs) or '(nenhum)'}

## Conversa completa (contexto)
{conversa}
""")
