"""API somente-leitura da base de Reels (dados/base/posts.parquet + dados/analise_top10) para a página /base."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.core.config import ROOT
from src.criativos import referencias as refs

NOMES_FORMATO = {"bab": "BAB", "product_demo_pas": "Demo + PAS", "ugc_testimonial": "UGC", "pas": "PAS", "aida": "AIDA"}
ID = re.compile(r"[A-Za-z0-9_-]{5,20}")


@lru_cache(maxsize=1)
def _df():
    import pandas as pd
    p = ROOT / "dados" / "base" / "posts.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df = df[df.tipo_post.eq("reels")] if "tipo_post" in df else df
    cls = {x["shortcode"]: x for x in refs._classificacao()}
    df = df.assign(top10=df.post_id.isin(cls), formato=df.post_id.map(lambda i: cls.get(i, {}).get("formato")))
    return df.sort_values("score_relativo", ascending=False, na_position="last").reset_index(drop=True)


def _num(v, nd=None):
    try:
        if v is None or v != v:
            return None
        return round(float(v), nd) if nd is not None else int(v)
    except (TypeError, ValueError):
        return None


def _midia(post_id: str, nome: str) -> Path | None:
    df = _df()
    if df is None or not ID.fullmatch(post_id or ""):
        return None
    r = df[df.post_id == post_id]
    if r.empty:
        return None
    base = ROOT / str(r.iloc[0].pasta_midia)
    f = base / nome
    if f.is_file() and f.resolve().is_relative_to((ROOT / "dados").resolve()):
        return f
    if nome == "thumb.jpg":  # alternativa: 1º quadro extraído na análise do top 10%
        fr = ROOT / "dados" / "analise_top10" / "frames" / post_id
        if fr.is_dir():
            return next(iter(sorted(fr.glob("*.jpg"))), None)
    return None


def resumo() -> dict:
    df = _df()
    if df is None:
        return {"disponivel": False}
    seg = df.segmento.value_counts().to_dict()
    return {"disponivel": True, "reels": len(df), "perfis": int(df.username.nunique()), "top10": int(df.top10.sum()),
            "segmentos": [{"id": k, "n": int(v)} for k, v in seg.items()],
            "formatos": [{"id": k, "nome": NOMES_FORMATO[k], "n": int(((df.formato == k)).sum())} for k in NOMES_FORMATO],
            "mediana_views": _num(df.views.median()), "mediana_eng": _num(df.taxa_eng.median(), 4),
            "coleta": str(df.data_coleta.max())[:10]}


def listar(query: str) -> dict:
    df = _df()
    if df is None:
        return {"itens": [], "total": 0}
    q = {k: v[0] for k, v in parse_qs(query).items()}
    if q.get("top10") == "1":
        df = df[df.top10]
    if q.get("formato") in NOMES_FORMATO:
        df = df[df.formato == q["formato"]]
    if q.get("segmento"):
        df = df[df.segmento == q["segmento"]]
    if q.get("q"):
        t = q["q"].lower()
        df = df[df.username.str.lower().str.contains(t, regex=False) | df.legenda.fillna("").str.lower().str.contains(t, regex=False)]
    ordem = {"views": "views", "eng": "taxa_eng", "recentes": "data_post"}.get(q.get("ordem", ""), "score_relativo")
    df = df.sort_values(ordem, ascending=False, na_position="last")
    pag, por = max(1, int(q.get("pagina", 1) or 1)), 24
    total = len(df)
    itens = []
    for r in df.iloc[(pag - 1) * por: pag * por].itertuples():
        f = refs._features(r.post_id) if r.top10 else {}
        itens.append({"id": r.post_id, "url": r.url, "perfil": r.username, "segmento": r.segmento, "views": _num(r.views),
                      "curtidas": _num(r.curtidas), "comentarios": _num(r.comentarios), "eng": _num(r.taxa_eng, 4),
                      "score": _num(r.score_relativo, 1), "duracao_s": _num(r.duracao_s), "seguidores": _num(r.seguidores),
                      "legenda": (r.legenda or "")[:220], "top10": bool(r.top10), "formato": r.formato,
                      "formato_nome": NOMES_FORMATO.get(r.formato), "gancho": (f.get("hook_transcript_3s") or "").strip(),
                      "thumb": _midia(r.post_id, "thumb.jpg") is not None, "video": _midia(r.post_id, "video.mp4") is not None})
    return {"itens": itens, "total": total, "pagina": pag, "paginas": max(1, -(-total // por))}


def tratar_get(h) -> bool:
    u = urlparse(h.path)
    if u.path == "/api/base/resumo":
        h._json(200, resumo())
        return True
    if u.path == "/api/base":
        h._json(200, listar(u.query))
        return True
    m = re.fullmatch(r"/api/base/([A-Za-z0-9_-]+)/(thumb|video)", u.path)
    if m:
        pid, kind = m.groups()
        f = _midia(pid, "thumb.jpg" if kind == "thumb" else "video.mp4")
        if f:
            h._servir_arquivo(f, "image/jpeg" if kind == "thumb" else "video/mp4", f"{pid}.{'jpg' if kind == 'thumb' else 'mp4'}")
        else:
            h._json(404, {"error": "Mídia indisponível."})
        return True
    return False
