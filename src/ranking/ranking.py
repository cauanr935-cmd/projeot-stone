"""Ranking dos Reels. Métrica principal: `score_relativo` = taxa_eng ÷ mediana da taxa_eng do perfil.
Visão secundária (métrica do case): taxa_eng = (curtidas + comentários) ÷ seguidores.

Alto desempenho = top `top_fracao` (padrão 10%) POR PLATAFORMA, entre posts aptos: curtidas visíveis e perfil com
pelo menos `min_reels_perfil` Reels aptos (senão a mediana do perfil não é confiável).

Uso: python -m src.ranking.ranking [--base dados/base] [--top 0.10]
Gera `ranking.parquet` (post_id + colunas de ranking) e recria `base.duckdb` com a tabela `ranking`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.core.config import load_coleta


def calcular_ranking(posts: pd.DataFrame, top_fracao: float = 0.10, min_reels_perfil: int = 5,
                     score_extremo: float = 20.0) -> pd.DataFrame:
    df = posts[["plataforma", "post_id", "username", "tipo_post", "score_relativo", "taxa_eng", "alcance",
                "ressonancia", "elegivel_ranking"]].copy()
    for c in ("score_relativo", "taxa_eng", "alcance", "ressonancia"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n_aptos = df[df["elegivel_ranking"].astype(bool)].groupby(["plataforma", "username"])["post_id"].transform("size")
    df["n_reels_perfil"] = n_aptos.reindex(df.index)
    df["perfil_estavel"] = df["n_reels_perfil"] >= min_reels_perfil
    df["apto"] = df["elegivel_ranking"].astype(bool) & df["perfil_estavel"].fillna(False)

    out = df.assign(score_rank=pd.NA, score_percentil=pd.NA, taxa_eng_rank=pd.NA,
                    alto_desempenho=False, alto_desempenho_taxa_eng=False)
    for _, idx in df[df["apto"]].groupby("plataforma").groups.items():
        sub = df.loc[idx]
        corte = sub["score_relativo"].quantile(1 - top_fracao)
        corte_taxa = sub["taxa_eng"].quantile(1 - top_fracao)
        out.loc[idx, "score_rank"] = sub["score_relativo"].rank(ascending=False, method="min")
        out.loc[idx, "taxa_eng_rank"] = sub["taxa_eng"].rank(ascending=False, method="min")
        out.loc[idx, "score_percentil"] = sub["score_relativo"].rank(pct=True)
        out.loc[idx, "alto_desempenho"] = sub["score_relativo"] >= corte
        out.loc[idx, "alto_desempenho_taxa_eng"] = sub["taxa_eng"] >= corte_taxa
    out["score_extremo"] = df["score_relativo"] > score_extremo
    return out.drop(columns=["elegivel_ranking"])


def resumo(posts: pd.DataFrame, r: pd.DataFrame) -> dict:
    m = posts.merge(r[["post_id", "alto_desempenho", "alto_desempenho_taxa_eng"]], on="post_id")
    top, top2 = m[m["alto_desempenho"]], m[m["alto_desempenho_taxa_eng"]]
    inter = len(set(top["post_id"]) & set(top2["post_id"]))
    return {"aptos": int(r["apto"].sum()), "fora_curtidas_ocultas": int((~posts["elegivel_ranking"].astype(bool)).sum()),
            "fora_perfil_pouco_dado": int((posts["elegivel_ranking"].astype(bool) & ~r["perfil_estavel"].fillna(False)).sum()),
            "top_score": len(top), "top_taxa_eng": len(top2), "intersecao": inter,
            "perfis_no_top": int(top["username"].nunique()), "score_extremo": int(r["score_extremo"].sum())}


def main(argv: list[str] | None = None) -> int:
    cfg = load_coleta()["ranking"]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="dados/base")
    ap.add_argument("--top", type=float, default=cfg["top_fracao"])
    args = ap.parse_args(argv)
    base = Path(args.base)
    posts = pd.read_parquet(base / "posts.parquet")
    r = calcular_ranking(posts, args.top, cfg["min_reels_perfil"], cfg["score_extremo"])
    r.to_parquet(base / "ranking.parquet", index=False)
    import duckdb
    con = duckdb.connect(str(base / "base.duckdb"))
    con.execute(f"CREATE OR REPLACE TABLE ranking AS SELECT * FROM read_parquet('{(base / 'ranking.parquet').as_posix()}')")
    con.execute("CREATE OR REPLACE VIEW top_reels AS SELECT p.*, r.score_rank, r.score_percentil, r.score_extremo "
                "FROM posts p JOIN ranking r USING (post_id) WHERE r.alto_desempenho")
    con.close()
    for k, v in resumo(posts, r).items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
