"""Referências reais da base: top 10% de Reels (dados/analise_top10) por formato, com gancho, métricas e link."""
from __future__ import annotations

import json
import statistics as st
from functools import lru_cache

from src.core.config import ROOT, _read

DIR = ROOT / "dados" / "analise_top10"
FORMATO_KEY = {1: "bab", 2: "product_demo_pas", 3: "ugc_testimonial", 4: "pas", 5: "aida"}


@lru_cache(maxsize=1)
def _classificacao() -> list[dict]:
    f = DIR / "format_classification.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def base_disponivel() -> bool:
    return bool(_classificacao())


@lru_cache(maxsize=1)
def _urls() -> dict[str, str]:
    try:
        import pandas as pd
        p = pd.read_parquet(ROOT / "dados" / "base" / "posts.parquet", columns=["post_id", "url"])
        return dict(zip(p.post_id, p.url))
    except Exception:
        return {}


def _features(shortcode: str) -> dict:
    f = DIR / "features" / f"{shortcode}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def _med(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 2) if xs else None


def panorama() -> list[dict]:
    """Os 5 formatos na base: quantos Reels do top 10%, mediana de score e perfil de ritmo."""
    out = []
    todos = _classificacao()
    for fid, key in FORMATO_KEY.items():
        g = [x for x in todos if x["formato"] == key]
        out.append({"format_id": fid, "formato": key, "n": len(g), "pct": round(100 * len(g) / max(len(todos), 1), 1),
                    "score_mediana": _med([x["score_relativo"] for x in g]),
                    "duracao_mediana_s": _med([x["duration_sec"] for x in g]),
                    "wpm_mediana": _med([x["words_per_minute"] for x in g]),
                    "cortes_min_mediana": _med([x["cuts_per_minute"] for x in g])})
    return out


def padroes(format_id: int) -> dict:
    p = next((x for x in panorama() if x["format_id"] == format_id), {})
    g = [x for x in _classificacao() if x["formato"] == FORMATO_KEY[format_id]]
    hooks = [len((_features(x["shortcode"]).get("hook_transcript_3s") or "").split()) for x in g[:60]]
    primeiras = [_features(x["shortcode"]).get("first_word_timestamp_sec") for x in g[:60]]
    primeiras = [v for v in primeiras if v is not None]
    p["hook_palavras_mediana"] = _med([h for h in hooks if h])
    p["fala_inicia_em_0s_pct"] = round(100 * sum(v <= 0.5 for v in primeiras) / len(primeiras)) if primeiras else None
    return p


def buscar(format_id: int, segmento_cnae: str | None = None, n: int = 3) -> list[dict]:
    pref = set(_read("perfis_prioritarios.yaml").get("segmentos_base", {}).get(segmento_cnae or "", []))
    g = [x for x in _classificacao() if x["formato"] == FORMATO_KEY[format_id]]
    g.sort(key=lambda x: (x.get("is_consensus_80", False), x["segmento"] in pref, x["score_relativo"]), reverse=True)
    urls, out = _urls(), []
    for rank, x in enumerate(g[:n], 1):
        f = _features(x["shortcode"])
        motivos = [f"{rank}º entre {len(g)} Reels do formato por prioridade (consenso → segmento afim → score)"]
        if x.get("is_consensus_80"):
            motivos.append("classificação confirmada pelo núcleo de consenso")
        if x["segmento"] in pref:
            motivos.append(f"segmento '{x['segmento']}' é afim ao perfil")
        out.append({"shortcode": x["shortcode"], "url": urls.get(x["shortcode"]) or f"https://www.instagram.com/p/{x['shortcode']}/",
                    "perfil": x["profile"], "formato": x["formato"], "segmento": x["segmento"],
                    "score_relativo": round(x["score_relativo"], 1), "taxa_eng": round(x["taxa_eng"], 4),
                    "duracao_s": round(x["duration_sec"]), "wpm": round(x["words_per_minute"]),
                    "cortes_min": round(x["cuts_per_minute"], 1),
                    "gancho": (f.get("hook_transcript_3s") or "").strip(),
                    "trecho": (f.get("transcript_text") or "")[:260].strip(),
                    "por_que": "; ".join(motivos)})
    return out
