"""Descoberta de perfis por hashtag (só para ACHAR candidatos; a base é coletada por perfil).

Uso:
    python -m src.coleta.descoberta --hashtags mei,pequenosnegocios --por-hashtag 50 [--verificar 40]
Gera `dados/descoberta_candidatos.csv` (1 linha por dono de Reel) e, com --verificar N, confere
seguidores/bio dos N candidatos mais frequentes. Hashtags enviesam para posts já em destaque:
por isso o score_relativo da Fase 4 continua sendo calculado sobre a coleta por perfil.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.coleta.instagram import coletar_perfis, rodar_actor
from src.core.config import load_coleta
from src.core.logging import configure_logging

log = logging.getLogger(__name__)


def agregar_por_dono(itens: list[dict]) -> pd.DataFrame:
    """Um item por Reel -> um registro por dono, com contagem, hashtags em que apareceu e views."""
    linhas = []
    for p in itens:
        dono = (p.get("ownerUsername") or "").lower()
        if not dono or p.get("error"):
            continue
        linhas.append({"username": dono, "hashtag": (p.get("hashtag") or "").lower(),
                       "views": p.get("videoPlayCount") or p.get("videoViewCount"),
                       "url": p.get("url")})
    if not linhas:
        return pd.DataFrame(columns=["username", "n_reels", "n_hashtags", "views_max", "exemplo"])
    df = pd.DataFrame(linhas)
    g = df.groupby("username").agg(n_reels=("url", "count"), n_hashtags=("hashtag", "nunique"),
                                   views_max=("views", "max"), exemplo=("url", "first")).reset_index()
    return g.sort_values(["n_hashtags", "n_reels"], ascending=False).reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    cfg = load_coleta()
    d = cfg["descoberta"]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hashtags", default=",".join(d["hashtags"]))
    ap.add_argument("--por-hashtag", type=int, default=d["reels_por_hashtag"])
    ap.add_argument("--verificar", type=int, default=0, help="confere seguidores dos N candidatos mais frequentes")
    ap.add_argument("--saida", default=cfg["saida_padrao"])
    args = ap.parse_args(argv)

    configure_logging()
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("APIFY_TOKEN ausente", file=sys.stderr)
        return 2
    from apify_client import ApifyClient

    client = ApifyClient(token)
    saida = Path(args.saida)
    cache = saida / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    tags = [t.strip().lstrip("#").lower() for t in args.hashtags.split(",") if t.strip()]
    entrada = {"hashtags": tags, "resultsType": "reels", "resultsLimit": args.por_hashtag}
    itens = rodar_actor(client, d["actor_hashtag"], entrada,
                        cache / f"hashtags_{'-'.join(tags)}_{args.por_hashtag}.json", d["teto_usd_run"])
    cand = agregar_por_dono(itens)
    print(f"{len(itens)} reels -> {len(cand)} donos distintos")

    if args.verificar and len(cand):
        top = cand.head(args.verificar)["username"].tolist()
        dia = datetime.now(UTC).strftime("%Y-%m-%d")
        perfis = coletar_perfis(client, top, cache, dia, d["teto_usd_verificacao"])
        perfis = perfis[perfis["erro"].isna() & (perfis["seguidores"] >= d["seguidores_min"])]
        cand = cand.merge(perfis[["username", "nome", "seguidores", "verificado", "conta_comercial",
                                  "categoria_ig", "bio"]], on="username", how="left")
    cand.to_csv(saida / "descoberta_candidatos.csv", index=False)
    print(cand.head(60).to_string(index=False, max_colwidth=50))
    return 0


if __name__ == "__main__":
    sys.exit(main())
