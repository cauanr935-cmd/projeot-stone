"""Manifesto de mídia do top 10%: confere cada vídeo em disco com ffprobe.

Uso:
    python -m src.analise.manifesto [--base dados/base] [--saida dados/analise_top10/manifesto_midia.json]

Não baixa nada: lista os ausentes/corrompidos em `faltando` para decisão humana
(download exige cookies de sessão de conta pessoal; ver docs/HUMAN_DEPENDENCIES.md).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.core.ffmpeg import ffprobe_json

MIN_DURACAO_S = 1.0
MIN_BYTES = 10_000


def inspecionar_video(video: Path) -> dict | None:
    """Metadados do vídeo se íntegro (duração > 1 s, > 10 kB, com fluxo de vídeo); senão None."""
    if not video.is_file() or video.stat().st_size <= MIN_BYTES:
        return None
    try:
        info = ffprobe_json(video)
    except Exception:  # noqa: BLE001
        return None
    stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    duracao = float(info.get("format", {}).get("duration") or 0)
    if stream is None or duracao <= MIN_DURACAO_S:
        return None
    num, _, den = str(stream.get("avg_frame_rate", "0/1")).partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return {"duration_sec": round(duracao, 3), "width": stream.get("width"), "height": stream.get("height"),
            "fps": round(fps, 3), "size_bytes": video.stat().st_size}


def construir_manifesto(base: Path) -> dict:
    posts = pd.read_parquet(base / "posts.parquet")
    rank = pd.read_parquet(base / "ranking.parquet")
    top = rank[rank["alto_desempenho"]].merge(
        posts[["post_id", "url", "pasta_midia"]], on="post_id", how="left")
    itens, faltando = [], []
    for r in top.itertuples():
        meta = inspecionar_video(Path(str(r.pasta_midia)) / "video.mp4") if pd.notna(r.pasta_midia) else None
        if meta is None:
            faltando.append(r.post_id)
            continue
        itens.append({
            "shortcode": r.post_id, "profile": r.username, "url": r.url,
            "score_relativo": float(r.score_relativo), "taxa_eng": float(r.taxa_eng),
            "is_consensus_80": bool(r.alto_desempenho_taxa_eng),
            "video_path": str(Path(r.pasta_midia) / "video.mp4"), "recovery_source": "cache_local", **meta,
        })
    return {"total_top10": len(top), "consenso": sum(i["is_consensus_80"] for i in itens),
            "itens": itens, "faltando": faltando}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="dados/base")
    ap.add_argument("--saida", default="dados/analise_top10/manifesto_midia.json")
    args = ap.parse_args(argv)
    m = construir_manifesto(Path(args.base))
    out = Path(args.saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, ensure_ascii=False, indent=2))
    print(f"top10={m['total_top10']} íntegros={len(m['itens'])} consenso={m['consenso']} faltando={len(m['faltando'])}")
    return 1 if m["faltando"] else 0


if __name__ == "__main__":
    sys.exit(main())
