"""Busca de vídeos/Shorts do YouTube por palavra-chave via Apify (sem YouTube Data API).

Uso:
    python -m src.coleta.youtube_apify --consultas "bolo de pote,marketing para MEI" --max 15 --max-usd 0.5

Requer APIFY_TOKEN no .env. Roda com teto de custo (checa saldo antes) e cache em dados/cache.
Saída: dados/youtube_apify.parquet (ordenado por visualizações) + resumo no terminal.
Opcional: --baixar N baixa os N mais vistos com yt-dlp para dados/midia/youtube/.
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.coleta.instagram import rodar_actor
from src.coleta.metricas import numero
from src.core.config import load_coleta
from src.core.logging import configure_logging

log = logging.getLogger(__name__)

ACTOR_PADRAO = "streamers/youtube-scraper"
CONSULTAS_PADRAO = ["marketing para MEI", "como vender mais no instagram", "reels para pequenos negócios"]


def _primeiro(d: dict, *chaves):
    for k in chaves:
        if d.get(k) is not None:
            return d[k]
    return None


def duracao_s(v) -> float | None:
    """Aceita número, 'HH:MM:SS' ou 'MM:SS'."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        partes = [float(x) for x in str(v).split(":")]
    except ValueError:
        return None
    s = 0.0
    for p in partes:
        s = s * 60 + p
    return s


def normalizar(item: dict, consulta: str | None = None) -> dict | None:
    vid = _primeiro(item, "id", "videoId")
    url = _primeiro(item, "url", "videoUrl")
    if not vid and not url:
        return None
    dur = duracao_s(_primeiro(item, "duration", "durationSeconds"))
    return {
        "video_id": vid,
        "url": url or f"https://www.youtube.com/watch?v={vid}",
        "titulo": _primeiro(item, "title"),
        "canal": _primeiro(item, "channelName", "channel"),
        "canal_url": _primeiro(item, "channelUrl"),
        "inscritos": numero(_primeiro(item, "numberOfSubscribers", "channelTotalSubscribers", "subscribers")),
        "views": numero(_primeiro(item, "viewCount", "views")),
        "likes": numero(_primeiro(item, "likes", "likeCount")),
        "comentarios": numero(_primeiro(item, "commentsCount", "commentCount")),
        "duracao_s": dur,
        "publicado_em": _primeiro(item, "date", "uploadDate"),
        "short": bool(dur is not None and dur <= load_coleta()["youtube"]["short_max_segundos"]),
        "descricao": (_primeiro(item, "text", "description") or "")[:500],
        "consulta": _primeiro(item, "input") or consulta,
    }


def consultas_por_nicho(ids: list[str] | None = None) -> dict[str, str]:
    """Termos de busca dos 10 perfis prioritários de MPE: {consulta: perfil_id}. 2 termos por nicho."""
    from src.criativos.spec import carregar_perfis, _read

    sin = _read("perfis_prioritarios.yaml")["sinonimos"]
    refinados = load_coleta()["youtube"].get("termos_nicho", {})
    mapa: dict[str, str] = {}
    for pid in carregar_perfis():
        if ids and pid not in ids:
            continue
        if pid in refinados:
            for t in refinados[pid]:
                mapa[t] = pid
            continue
        termo = sin[pid][0]
        mapa[f"{termo} dicas para vender mais"] = pid
        mapa[f"{termo} antes e depois resultado"] = pid
    return mapa


def consultas_comerciais(ids: list[str] | None = None) -> dict[str, str]:
    """{consulta: perfil_id} com intenção comercial: 5 intenções × ramo de cada nicho."""
    from src.criativos.spec import carregar_perfis

    y = load_coleta()["youtube"]
    return {f"{i} {y['ramo_busca'][pid]}": pid for pid in carregar_perfis() if not ids or pid in ids
            for i in y["intencoes_comerciais"]}


def marcar_relevancia(df: pd.DataFrame) -> pd.DataFrame:
    """`relevante`: título/descrição/canal citam um sinônimo do nicho (tira Short de academia em 'professor')."""
    import re
    from src.criativos.spec import _read

    sin = _read("perfis_prioritarios.yaml")["sinonimos"]

    def ok(r) -> bool:
        txt = f"{r.titulo} {r.descricao} {r.canal} {r.consulta}".lower()
        return any(re.search(rf"\b{re.escape(w.lower())}", txt) for w in sin.get(r.nicho, []))

    df["relevante"] = df.apply(ok, axis=1)
    return df


def adicionar_viralidade(df: pd.DataFrame) -> pd.DataFrame:
    """views_por_inscrito = views / inscritos (viral = muito acima do tamanho do canal); score mistura as duas ideias."""
    import numpy as np

    ins = df["inscritos"].where(df["inscritos"] > 0)
    df["views_por_inscrito"] = (df["views"] / ins).round(2)
    df["engajamento"] = ((df["likes"].fillna(0) + df["comentarios"].fillna(0)) / df["views"].where(df["views"] > 0)).round(4)
    # log10(views) pesa o alcance absoluto; a razão views/inscritos (limitada a 50) premia o que estourou fora da bolha.
    razao = df["views_por_inscrito"].fillna(1).clip(upper=50)
    df["score_viral"] = (np.log10(df["views"].fillna(0) + 1) * (1 + np.log10(razao + 1))).round(2)
    return df


def buscar(client, consultas: list[str], max_por_consulta: int, cache_dir: Path, max_usd: float,
           so_shorts: bool, actor: str = ACTOR_PADRAO) -> pd.DataFrame:
    h = hashlib.sha1(("|".join(sorted(consultas)) + f"{max_por_consulta}{so_shorts}").encode()).hexdigest()[:8]
    entrada = {
        "searchQueries": consultas,
        "maxResults": 0 if so_shorts else max_por_consulta,
        "maxResultsShorts": max_por_consulta,
        "maxResultStreams": 0,
        "downloadSubtitles": False,
    }
    itens = rodar_actor(client, actor, entrada, cache_dir / f"youtube_busca_{h}.json", max_usd)
    linhas = [r for r in (normalizar(i) for i in itens) if r]
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    df = df.drop_duplicates("url")
    df = adicionar_viralidade(df).sort_values("score_viral", ascending=False, na_position="last")
    return df.reset_index(drop=True)


def selecionar_por_nicho(df: pd.DataFrame, por_nicho: int) -> pd.DataFrame:
    """Top N por nicho pelo score viral, só entre os relevantes (e Shorts)."""
    base = df[df["short"] & df.get("relevante", True)]
    return base.sort_values("score_viral", ascending=False).groupby("nicho").head(por_nicho)


def baixar_top(df: pd.DataFrame, n: int, pasta: Path) -> list[Path]:
    import yt_dlp

    pasta.mkdir(parents=True, exist_ok=True)
    fmt = load_coleta()["youtube"]["formato_ytdlp"]
    saidas = []
    for _, r in df.head(n).iterrows():
        destino = pasta / f"{r['video_id']}.mp4"
        if destino.exists() and destino.stat().st_size > 0:
            saidas.append(destino)
            continue
        opts = {"format": fmt, "outtmpl": str(destino), "quiet": True, "no_warnings": True, "retries": 4, "noprogress": True,
                "merge_output_format": "mp4"}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([r["url"]])
            if destino.exists():
                saidas.append(destino)
        except Exception as e:  # noqa: BLE001 - um vídeo ruim não derruba o lote
            log.warning("falha ao baixar %s: %s", r["url"], e)
    return saidas


def main(argv: list[str] | None = None) -> int:
    cfg = load_coleta()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--consultas", default=",".join(CONSULTAS_PADRAO), help="termos de busca separados por vírgula")
    ap.add_argument("--nichos", nargs="?", const="todos", help="usa os perfis prioritários de MPE (todos, ou ids separados por vírgula)")
    ap.add_argument("--comercial", action="store_true", help="com --nichos: busca por intenção comercial (como vender, quanto cobrar...)")
    ap.add_argument("--max", type=int, default=10, help="vídeos por consulta")
    ap.add_argument("--max-usd", type=float, default=0.5, help="teto de gasto do run")
    ap.add_argument("--incluir-longos", action="store_true", help="além dos Shorts, traz vídeos longos")
    ap.add_argument("--baixar", type=int, default=0, help="baixa os N mais virais (yt-dlp)")
    ap.add_argument("--baixar-por-nicho", type=int, default=0, help="com --nichos: baixa os N mais virais RELEVANTES de cada nicho")
    ap.add_argument("--saida", default=cfg["saida_padrao"])
    args = ap.parse_args(argv)

    configure_logging()
    from dotenv import load_dotenv
    load_dotenv(".env")
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("APIFY_TOKEN ausente (defina no .env)", file=sys.stderr)
        return 2
    from apify_client import ApifyClient

    saida = Path(args.saida)
    cache = saida / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    mapa: dict[str, str] = {}
    if args.nichos:
        ids = None if args.nichos == "todos" else args.nichos.split(",")
        mapa = consultas_comerciais(ids) if args.comercial else consultas_por_nicho(ids)
        consultas = list(mapa)
    else:
        consultas = [c.strip() for c in args.consultas.split(",") if c.strip()]
    df = buscar(ApifyClient(token), consultas, args.max, cache, args.max_usd, not args.incluir_longos)
    if df.empty:
        print("nenhum vídeo retornado")
        return 1
    destino = saida / "youtube_apify.parquet"
    if mapa:
        df["nicho"] = df["consulta"].map(mapa)
        df["comercial"] = args.comercial
    df["coletado_em"] = datetime.now(UTC).isoformat()
    if destino.exists() and mapa:  # acumula runs de nichos diferentes; o run mais novo vence em caso de repetição
        ant = pd.read_parquet(destino)
        df = pd.concat([df, ant], ignore_index=True).drop_duplicates("url", keep="first")
        df = df.sort_values("score_viral", ascending=False).reset_index(drop=True)
    if mapa:
        df = marcar_relevancia(df)
    df.to_parquet(destino, index=False)
    print(f"{len(df)} vídeos → {destino}")
    cols = (["nicho"] if mapa else []) + ["titulo", "canal", "views", "inscritos", "score_viral", "url"]
    print(df[cols].head(25).to_string(index=False, max_colwidth=50))
    if args.baixar_por_nicho and mapa:
        sel = selecionar_por_nicho(df[df["comercial"].fillna(False).astype(bool)] if args.comercial else df, args.baixar_por_nicho)
        arqs = baixar_top(sel, len(sel), saida / "midia" / "youtube")
        sel.assign(arquivo=lambda d: d["video_id"].map(lambda v: f"midia/youtube/{v}.mp4")).to_csv(
            saida / ("youtube_selecionados_comercial.csv" if args.comercial else "youtube_selecionados.csv"), index=False)
        print(f"{len(arqs)}/{len(sel)} vídeos baixados em {saida / 'midia' / 'youtube'}")
    elif args.baixar:
        arqs = baixar_top(df, args.baixar, saida / "midia" / "youtube")
        print(f"{len(arqs)} vídeos baixados em {saida / 'midia' / 'youtube'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
