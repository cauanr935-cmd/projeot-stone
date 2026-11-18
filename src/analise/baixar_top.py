"""Baixa os vídeos do top 10% que faltam em disco, a partir do cache bruto do Apify.

Uso:
    python -m src.analise.baixar_top [--base dados/base] [--cache dados/cache]
Links do Instagram expiram em ~1 dia: rode logo após a coleta (403 = re-coletar o perfil).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.coleta.instagram import baixar


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="dados/base")
    ap.add_argument("--cache", default="dados/cache")
    ap.add_argument("--midia", default="dados/midia/instagram")
    args = ap.parse_args(argv)
    rank = pd.read_parquet(Path(args.base) / "ranking.parquet")
    alvo = set(rank.loc[rank["alto_desempenho"], "post_id"])
    urls = {}
    for f in Path(args.cache).glob("reels_*[0-9].json"):
        for p in json.loads(f.read_text()):
            if isinstance(p, dict) and p.get("shortCode") in alvo and p.get("videoUrl"):
                urls[p["shortCode"]] = p["videoUrl"]
    falta = [i for i in alvo if not (Path(args.midia) / i / "video.mp4").exists()]
    ok = sum(baixar(urls.get(i), Path(args.midia) / i / "video.mp4") for i in falta)
    print(f"top10={len(alvo)} faltavam={len(falta)} baixados={ok} sem_link_ou_expirado={len(falta) - ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
