"""Manifesto dos Reels de CONTROLE (não virais) que já têm vídeo em disco, para validar o score viral.

Uso: python -m src.analise.manifesto_controle [--base dados/base] [--saida dados/analise_controle/manifesto_midia.json]
Mesmo formato de `manifesto.py`, para reutilizar `python -m src.analise.features --manifesto ... --saida ...`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.analise.manifesto import inspecionar_video


def construir(base: Path) -> dict:
    posts = pd.read_parquet(base / "posts.parquet")
    rank = pd.read_parquet(base / "ranking.parquet")
    ctl = rank[~rank["alto_desempenho"]].merge(posts[["post_id", "url", "pasta_midia"]], on="post_id", how="left")
    itens = []
    for r in ctl.itertuples():
        if pd.isna(r.pasta_midia):
            continue
        meta = inspecionar_video(Path(str(r.pasta_midia)) / "video.mp4")
        if meta is None:
            continue
        itens.append({"shortcode": r.post_id, "profile": r.username, "url": r.url,
                      "score_relativo": float(r.score_relativo), "taxa_eng": float(r.taxa_eng),
                      "score_percentil": float(r.score_percentil),
                      "video_path": str(Path(r.pasta_midia) / "video.mp4"), **meta})
    return {"total_controle": len(itens), "itens": itens}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="dados/base")
    ap.add_argument("--saida", default="dados/analise_controle/manifesto_midia.json")
    a = ap.parse_args(argv)
    m = construir(Path(a.base))
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(m, ensure_ascii=False, indent=1))
    print(f"controles com vídeo íntegro: {m['total_controle']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
