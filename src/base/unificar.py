"""Unifica os lotes coletados numa base única (Parquet + DuckDB) e registra o que foi excluído e por quê.

Uso:
    python -m src.base.unificar [--dados dados] [--saida dados/base]
Gera: posts.parquet, perfis.parquet, excluidos.parquet, base.duckdb (tabelas e view `reels_elegiveis`).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from src.base.schema import EXCLUIDOS_COLS, aplicar_schema
from src.coleta.metricas import adicionar_metricas, filtrar_idade
from src.core.config import load_coleta
from src.core.logging import configure_logging

log = logging.getLogger(__name__)
_DERIVADAS = ["curtidas_ocultas", "taxa_eng", "score_relativo", "alcance", "ressonancia"]


def _excl(df: pd.DataFrame, motivo: str, lote: str) -> pd.DataFrame:
    d = df.copy()
    d["motivo"], d["lote"] = motivo, lote
    for c in EXCLUIDOS_COLS:
        if c not in d:
            d[c] = None
    return d[EXCLUIDOS_COLS]


def construir_base(lotes: dict[str, pd.DataFrame], excluidos: list[tuple[str, str, pd.DataFrame]],
                   janela_dias: int = 365, idade_minima_dias: int = 14) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`lotes`: nome -> posts elegíveis (ordem = prioridade na deduplicação).
    `excluidos`: (lote, motivo, df) já descartados na coleta. Devolve (posts, excluidos)."""
    excl = [_excl(df, motivo, lote) for lote, motivo, df in excluidos if len(df)]
    partes = []
    for nome, df in lotes.items():
        d = df.copy()
        d["lote"] = nome
        partes.append(d)
    posts = pd.concat(partes, ignore_index=True).drop_duplicates("post_id", keep="first")

    fora = posts["tipo_post"] != "reels"
    if fora.any():
        excl.append(_excl(posts[fora], "fora_do_foco_reels", "multi"))
    posts = posts[~fora]

    posts["data_post"] = pd.to_datetime(posts["data_post"], utc=True)
    posts["data_coleta"] = pd.to_datetime(posts["data_coleta"], utc=True)
    limite = posts["data_coleta"] - pd.Timedelta(days=janela_dias)
    velho = posts["data_post"] < limite
    if velho.any():
        excl.append(_excl(posts[velho], "fora_janela_12m", "multi"))
    posts = posts[~velho]
    posts = filtrar_idade(posts, idade_minima_dias)

    # métricas recalculadas sobre o conjunto final (a mediana do perfil muda com as exclusões)
    posts = adicionar_metricas(posts.drop(columns=[c for c in _DERIVADAS if c in posts]))
    posts["elegivel_ranking"] = posts["taxa_eng"].notna() & posts["score_relativo"].notna()
    posts = aplicar_schema(posts.reset_index(drop=True))
    excluidos_df = pd.concat(excl, ignore_index=True) if excl else pd.DataFrame(columns=EXCLUIDOS_COLS)
    excluidos_df = excluidos_df.drop_duplicates(["post_id", "motivo"]).reset_index(drop=True)
    return posts, excluidos_df


def tabela_perfis(perfis_csv: pd.DataFrame, perfis_raw: pd.DataFrame, posts: pd.DataFrame,
                  excluidos: pd.DataFrame) -> pd.DataFrame:
    p = perfis_csv.merge(perfis_raw[["username", "nome", "seguidores", "verificado", "conta_comercial",
                                     "categoria_ig", "bio", "data_coleta"]], on="username", how="left")
    n = posts.groupby("username").size().rename("n_reels_base")
    x = excluidos.groupby("username").size().rename("n_reels_excluidos")
    p = p.merge(n, on="username", how="left").merge(x, on="username", how="left")
    p[["n_reels_base", "n_reels_excluidos"]] = p[["n_reels_base", "n_reels_excluidos"]].fillna(0).astype(int)
    p["status"] = p["n_reels_base"].map(lambda v: "na_base" if v > 0 else "sem_reels_elegiveis")
    return p


def _ler(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def main(argv: list[str] | None = None) -> int:
    cfg = load_coleta()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dados", default=cfg["saida_padrao"])
    ap.add_argument("--saida", default=None)
    ap.add_argument("--lotes", default="instagram,instagram_lote2,instagram_lote3", help="prefixos dos lotes, em ordem de prioridade")
    args = ap.parse_args(argv)
    configure_logging()

    dados = Path(args.dados)
    saida = Path(args.saida) if args.saida else dados / "base"
    saida.mkdir(parents=True, exist_ok=True)
    prefixos = [p.strip() for p in args.lotes.split(",")]

    lotes, excl, perfis_raw = {}, [], []
    for pre in prefixos:
        posts = _ler(dados / f"{pre}_posts.parquet")
        if posts.empty:
            log.warning("lote sem posts: %s", pre)
            continue
        lotes[pre] = posts
        excl.append((pre, "menos_14_dias", _ler(dados / f"{pre}_posts_excluidos.parquet")))
        excl.append((pre, "colaboracao_dono_diferente", _ler(dados / f"{pre}_reels_excluidos_dono_diferente.parquet")))
        perfis_raw.append(_ler(dados / f"{pre}_perfis.parquet"))
    piloto = _ler(dados / "instagram_posts_piloto_impulsostone.parquet")
    if len(piloto):  # carrosséis/imagens do piloto: fora do foco (os Reels vieram de novo no lote 1)
        excl.append(("piloto", "fora_do_foco_reels", piloto[piloto["tipo_post"] != "reels"]))

    posts, excluidos = construir_base(lotes, excl, janela_dias=cfg["base"]["janela_dias"],
                                      idade_minima_dias=cfg["instagram"]["idade_minima_dias"])
    base_csv = cfg["perfis_csv"].replace(".csv", "")
    csvs = [pd.read_csv(p) for p in (f"{base_csv}.csv", f"{base_csv}_lote2.csv", f"{base_csv}_lote3.csv") if Path(p).exists()]
    perfis = tabela_perfis(pd.concat(csvs, ignore_index=True), pd.concat(perfis_raw, ignore_index=True)
                           .drop_duplicates("username"), posts, excluidos)

    # fonte de verdade da mídia: o que existe em disco (vídeos baixados depois da coleta também contam)
    pasta = dados / "midia" / "instagram"
    tem = posts["post_id"].map(lambda i: (pasta / str(i) / "video.mp4").exists()).astype("boolean")
    posts["video_ok"] = tem.where(tem | posts["video_ok"].notna(), other=pd.NA).where(~tem, other=True)
    posts.loc[tem, "pasta_midia"] = posts.loc[tem, "post_id"].map(lambda i: str(pasta / str(i)))

    posts.to_parquet(saida / "posts.parquet", index=False)
    perfis.to_parquet(saida / "perfis.parquet", index=False)
    excluidos.to_parquet(saida / "excluidos.parquet", index=False)

    import duckdb
    db = saida / "base.duckdb"
    db.unlink(missing_ok=True)
    con = duckdb.connect(str(db))
    for nome in ("posts", "perfis", "excluidos"):
        con.execute(f"CREATE TABLE {nome} AS SELECT * FROM read_parquet('{(saida / (nome + '.parquet')).as_posix()}')")
    con.execute("CREATE VIEW reels_elegiveis AS SELECT * FROM posts WHERE elegivel_ranking")
    con.close()
    print(f"posts: {len(posts)} | perfis na base: {int((perfis.status == 'na_base').sum())}/{len(perfis)} | "
          f"excluídos: {len(excluidos)} {excluidos.motivo.value_counts().to_dict()}")
    print("Pronto:", saida.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
