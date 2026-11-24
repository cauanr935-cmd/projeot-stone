"""Memória dos Reels produzidos: o próprio histórico vira barema para os próximos.

Cada Reel de output/edicoes/<id>/ ganha um registro em output/memoria/reels.json com:
- `nota`: aderência ao padrão do top 10% da base (src.analise.score_viral), calculada localmente;
- `desempenho`: métricas reais informadas pelo usuário depois de postar (views, curtidas, ...).
Quando há desempenho real, ele manda no ranking; sem ele, vale a nota. Os melhores (e os piores)
entram no prompt da próxima edição como "o que funcionou / o que evitar".

Também resolve `capa_referencias.json`: as capas da base em que o Claude declarou ter se inspirado.
"""
from __future__ import annotations

import json
import logging
import math
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from src.core.config import ROOT

log = logging.getLogger(__name__)
EDICOES = ROOT / "output" / "edicoes"
ARQ = ROOT / "output" / "memoria" / "reels.json"
LOCK = threading.Lock()
ID = re.compile(r"[a-z0-9_]{3,40}")
METRICAS = ("views", "curtidas", "comentarios", "salvamentos", "compartilhamentos")
_pontuando = False


def _ler() -> dict:
    try:
        return json.loads(ARQ.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar(d: dict) -> None:
    ARQ.parent.mkdir(parents=True, exist_ok=True)
    tmp = ARQ.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ARQ)


def taxa_engajamento(d: dict) -> float | None:
    v = d.get("views") or 0
    if v <= 0:
        return None
    inter = sum(d.get(k) or 0 for k in ("curtidas", "comentarios", "salvamentos", "compartilhamentos"))
    return round(inter / v, 4)


def _primeira_linha(arq: Path) -> str:
    try:
        for ln in arq.read_text(encoding="utf-8").splitlines():
            if ln.strip() and not ln.startswith("#"):
                return ln.strip()[:200]
    except OSError:
        pass
    return ""


def registrar(edicao_id: str, pedido: str = "") -> dict | None:
    """Cria/atualiza o registro do Reel e calcula a nota local. Nunca levanta (o Reel já está pronto)."""
    pasta = EDICOES / edicao_id
    final = pasta / "final.mp4"
    if not ID.fullmatch(edicao_id) or not final.is_file():
        return None
    try:
        from src.analise.score_viral import pontuar_video
        s = pontuar_video(final, com_fala=False)
    except Exception as exc:  # noqa: BLE001 - nota é opcional
        log.info("memoria: sem nota para %s (%s)", edicao_id, exc)
        s = {}
    with LOCK:
        d = _ler()
        r = d.get(edicao_id, {})
        r.update(id=edicao_id, criado_em=r.get("criado_em") or datetime.fromtimestamp(final.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                 pedido=(pedido or r.get("pedido") or "")[:300], resumo=_primeira_linha(pasta / "resumo.md"),
                 nota=s.get("nota", r.get("nota")), faixa=s.get("faixa", r.get("faixa")),
                 melhorias=s.get("melhorias", r.get("melhorias", [])),
                 detalhes={x["feature"]: x["valor"] for x in s.get("detalhes", [])} or r.get("detalhes", {}))
        d[edicao_id] = r
        _gravar(d)
    return r


def registrar_desempenho(edicao_id: str, dados: dict) -> dict:
    if not ID.fullmatch(edicao_id or "") or not (EDICOES / edicao_id / "final.mp4").is_file():
        raise ValueError("Reel não encontrado.")
    des = {}
    for k in METRICAS:
        try:
            v = int(float(dados.get(k) or 0))
        except (TypeError, ValueError):
            raise ValueError(f"Valor inválido em '{k}'.") from None
        if not 0 <= v <= 10**10:
            raise ValueError(f"Valor fora do intervalo em '{k}'.")
        des[k] = v
    if des["views"] <= 0:
        raise ValueError("Informe as visualizações (maior que zero).")
    des["taxa_eng"] = taxa_engajamento(des)
    des["informado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    registrar(edicao_id)
    with LOCK:
        d = _ler()
        d.setdefault(edicao_id, {"id": edicao_id})["desempenho"] = des
        _gravar(d)
        return d[edicao_id]


def _pontos(r: dict) -> float:
    """Pontuação para o ranking: desempenho real (engajamento, com bônus leve por alcance) > nota local."""
    des = r.get("desempenho")
    if des and des.get("taxa_eng") is not None:
        return 100 + 100 * des["taxa_eng"] + math.log10(max(des["views"], 1))
    return float(r.get("nota") or 0)


def _todos() -> list[dict]:
    d = _ler()
    for p in sorted(EDICOES.glob("*/final.mp4")) if EDICOES.is_dir() else []:
        d.setdefault(p.parent.name, {"id": p.parent.name, "criado_em": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")})
    return list(d.values())


def pontuar_pendentes() -> None:
    """Calcula em segundo plano a nota dos Reels antigos que ainda não têm (1 por vez)."""
    global _pontuando
    with LOCK:
        if _pontuando:
            return
        _pontuando = True

    def _run() -> None:
        global _pontuando
        try:
            for r in _todos():
                if r.get("nota") is None and ID.fullmatch(r["id"]):
                    registrar(r["id"])
        finally:
            _pontuando = False

    threading.Thread(target=_run, daemon=True).start()


def ranking() -> list[dict]:
    """Reels próprios do melhor para o pior (com posição), prontos para a página 'Meus Reels'."""
    out = [dict(r, pontos=round(_pontos(r), 2), tem_capa=(EDICOES / r["id"] / "capa.jpg").is_file(),
                fonte="desempenho real" if (r.get("desempenho") or {}).get("taxa_eng") is not None else "nota local")
           for r in _todos() if not str(r["id"]).startswith("ex_")]
    out.sort(key=lambda r: r["pontos"], reverse=True)
    for i, r in enumerate(out, 1):
        r["posicao"] = i
    return out


def licoes_para_prompt(n_melhores: int = 3, n_piores: int = 2) -> str:
    """Bloco do prompt: os melhores Reels já feitos viram o barema; os piores, o que evitar."""
    rk = [r for r in ranking() if r.get("nota") is not None or r.get("desempenho")]
    if not rk:
        return ""

    def linha(r: dict) -> str:
        des, d = r.get("desempenho"), r.get("detalhes", {})
        met = (f"{des['views']} views, engajamento {100 * des['taxa_eng']:.1f}%" if des and des.get("taxa_eng") is not None
               else f"nota {r.get('nota')}/100 vs top 10% da base (sem métrica real ainda)")
        forma = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in list(d.items())[:4])
        return (f"  - {r['id']}: {met}. Pedido: \"{r.get('pedido') or r.get('resumo') or '-'}\". {forma}. "
                f"Material em output/edicoes/{r['id']}/ (decupagem.md, capa.jpg).")

    melhores = rk[:n_melhores]
    piores = [r for r in rk[n_melhores:][-n_piores:] if _pontos(r) < _pontos(melhores[-1])]
    txt = ("MEMÓRIA DOS SEUS REELS (barema próprio; vale mais que regras genéricas quando houver métrica real):\n"
           "Melhores até agora (leia a decupagem deles e repita o que funcionou: tipo de gancho, ritmo, estrutura, capa; "
           "não copie o conteúdo):\n" + "\n".join(linha(r) for r in melhores))
    if piores:
        txt += "\nPiores (evite repetir):\n" + "\n".join(linha(r) for r in piores)
    melh = sorted({m for r in melhores for m in r.get("melhorias", [])})[:3]
    if melh:
        txt += "\nPontos que a nota local ainda acusa nos melhores: " + "; ".join(melh) + "."
    return txt


def candidatas_capas(n: int = 8) -> list[dict]:
    """Capas de Reels do top 10% da base (com arquivo local), de perfis diferentes, para o Claude se inspirar."""
    try:
        from src.criativos import base_api
        df = base_api._df()
        if df is None:
            return []
        out, vistos = [], set()
        for r in df[df.top10].itertuples():
            if r.username in vistos:
                continue
            f = base_api._midia(r.post_id, "thumb.jpg")
            if f:
                vistos.add(r.username)
                out.append({"id": r.post_id, "perfil": r.username, "formato": r.formato, "score": base_api._num(r.score_relativo, 1),
                            "arquivo": str(f)})
            if len(out) >= n:
                break
        return out
    except Exception as exc:  # noqa: BLE001
        log.info("memoria: sem capas candidatas (%s)", exc)
        return []


def bloco_capa(pasta: Path) -> str:
    cand = candidatas_capas()
    if not cand:
        return "- `capa.jpg`: crie uma capa legível (texto grande, rosto/produto em destaque, contraste alto)."
    lista = "\n".join(f"    · {c['id']} (@{c['perfil']}, {c['formato'] or 'formato n/d'}, score {c['score']}): {c['arquivo']}" for c in cand)
    return (f"- CAPA: abra (Read) 3 a 5 destas capas de Reels de alto desempenho da base e escolha as 2 ou 3 que mais combinam com este vídeo:\n{lista}\n"
            f"  Faça a `capa.jpg` inspirada nelas (composição, texto grande, contraste), sem copiar a imagem. Registre as escolhidas em "
            f"{pasta}/capa_referencias.json no formato [{{\"id\": \"<id acima>\", \"o_que_aproveitei\": \"<1 frase: composição, cor, texto...>\"}}].")


ARQUIVO_REFS = "capa_referencias.json"


def capa_referencias(edicao_id: str) -> list[dict]:
    """Referências declaradas pelo Claude, validadas contra a base e enriquecidas (perfil, link, miniatura)."""
    f = EDICOES / edicao_id / ARQUIVO_REFS
    if not ID.fullmatch(edicao_id or "") or not f.is_file():
        return []
    try:
        brutas = json.loads(f.read_text(encoding="utf-8"))
        from src.criativos import base_api
        df = base_api._df()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for b in brutas[:6] if isinstance(brutas, list) else []:
        pid = str((b or {}).get("id", ""))
        if df is None or not base_api.ID.fullmatch(pid):
            continue
        r = df[df.post_id == pid]
        if r.empty:
            continue  # id inventado: não mostra
        r = r.iloc[0]
        out.append({"id": pid, "perfil": r.username, "url": r.url, "formato": base_api.NOMES_FORMATO.get(r.get("formato")),
                    "views": base_api._num(r.views), "eng": base_api._num(r.taxa_eng, 4),
                    "o_que_aproveitei": str(b.get("o_que_aproveitei", ""))[:200],
                    "thumb": f"/api/base/{pid}/thumb" if base_api._midia(pid, "thumb.jpg") else None})
    return out
