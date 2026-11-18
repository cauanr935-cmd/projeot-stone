import json
import subprocess
from pathlib import Path

import pytest

from src.analise.manifesto import inspecionar_video

BASE = Path("dados/base")


def test_video_ausente_ou_pequeno(tmp_path):
    assert inspecionar_video(tmp_path / "nao_existe.mp4") is None
    pequeno = tmp_path / "v.mp4"
    pequeno.write_bytes(b"x" * 100)
    assert inspecionar_video(pequeno) is None


def test_video_valido(tmp_path):
    v = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=320x240:rate=30:duration=3", "-pix_fmt", "yuv420p", str(v)], check=True)
    meta = inspecionar_video(v)
    assert meta and meta["duration_sec"] > 1 and meta["width"] == 320


@pytest.mark.skipif(not (BASE / "ranking.parquet").exists(), reason="base local (gitignored) ausente")
def test_manifesto_real():
    from src.analise.manifesto import construir_manifesto
    m = construir_manifesto(BASE)
    import pandas as pd
    rank = pd.read_parquet(BASE / "ranking.parquet")
    n = int(rank["alto_desempenho"].sum())  # o tamanho do top 10% cresce a cada lote
    assert len(m["itens"]) == m["total_top10"] == n and not m["faltando"]
    assert len({i["shortcode"] for i in m["itens"]}) == n
    assert m["consenso"] == int(rank.loc[rank["alto_desempenho"], "alto_desempenho_taxa_eng"].sum())
