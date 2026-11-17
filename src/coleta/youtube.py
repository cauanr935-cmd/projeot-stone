"""Coleta de vídeos/Shorts do YouTube via Data API v3 (playlist de uploads, sem search) + yt-dlp.

Uso:
    export YOUTUBE_API_KEY=...        # ou no .env
    python -m src.coleta.youtube --limite 10 --apenas @canal

Custo de quota: channels.list 1 + playlistItems.list 1/50 vídeos + videos.list 1/50 vídeos.
Saídas: youtube_perfis.parquet, youtube_posts.parquet, midia/youtube/<id>.mp4, cache/.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.coleta.instagram import ler_perfis_csv
from src.coleta.metricas import adicionar_metricas, filtrar_idade, numero
from src.core.config import load_coleta
from src.core.logging import configure_logging

log = logging.getLogger(__name__)


def _cfg() -> dict:
    return load_coleta()["youtube"]


def duracao_segundos(iso: str | None) -> float | None:
    """Converte duração ISO 8601 (PT1M5S) em segundos."""
    if not iso:
        return None
    import isodate
    try:
        return isodate.parse_duration(iso).total_seconds()
    except Exception:  # noqa: BLE001
        return None


def eh_short(duracao_s: float | None, limite: float | None = None) -> bool:
    """Heurística: Short = duração <= 180 s (a API não expõe o formato)."""
    limite = limite if limite is not None else _cfg()["short_max_segundos"]
    return duracao_s is not None and 0 < duracao_s <= limite


def _cached(path: Path, fn):
    if path.exists():
        log.info("cache hit: %s", path.name)
        return json.loads(path.read_text(encoding="utf-8"))
    valor = fn()
    path.write_text(json.dumps(valor, ensure_ascii=False), encoding="utf-8")
    return valor


def resolver_canal(yt, ident: str) -> dict:
    """Aceita @handle ou id UC...; devolve o item de channels.list."""
    ident = ident.strip()
    kw = {"id": ident} if ident.startswith("UC") else {"forHandle": ident if ident.startswith("@") else "@" + ident}
    resp = yt.channels().list(part="snippet,statistics,contentDetails", **kw).execute()
    items = resp.get("items") or []
    if not items:
        raise LookupError(f"canal não encontrado: {ident}")
    return items[0]


def listar_uploads(yt, playlist_id: str, limite: int) -> list[str]:
    ids, token = [], None
    while len(ids) < limite:
        resp = yt.playlistItems().list(part="contentDetails", playlistId=playlist_id,
                                       maxResults=min(50, limite - len(ids)), pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in resp.get("items", [])]
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids[:limite]


def detalhes_videos(yt, ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(ids), 50):
        resp = yt.videos().list(part="snippet,contentDetails,statistics", id=",".join(ids[i:i + 50])).execute()
        out += resp.get("items", [])
    return out


def normalizar_video(v: dict, canal: str, data_coleta: datetime) -> dict:
    sn, st = v.get("snippet", {}), v.get("statistics", {})
    dur = duracao_segundos(v.get("contentDetails", {}).get("duration"))
    ts = pd.to_datetime(sn.get("publishedAt"), utc=True)
    titulo, desc = sn.get("title") or "", sn.get("description") or ""
    return {
        "plataforma": "youtube",
        "post_id": v["id"],
        "url": f"https://www.youtube.com/shorts/{v['id']}" if eh_short(dur) else f"https://www.youtube.com/watch?v={v['id']}",
        "username": canal.lower(),
        "tipo_post": "short" if eh_short(dur) else "video",
        "product_type": None,
        "legenda": (titulo + "\n" + desc).strip(),
        "hashtags": sn.get("tags"),
        "data_post": ts,
        "idade_dias": (pd.Timestamp(data_coleta) - ts).days if pd.notna(ts) else None,
        "curtidas": numero(int(st["likeCount"])) if "likeCount" in st else None,  # ausente = ocultas
        "comentarios": numero(int(st["commentCount"])) if "commentCount" in st else None,
        "views": numero(int(st["viewCount"])) if "viewCount" in st else None,
        "duracao_s": dur,
        "n_slides": 0,
        "collab": False,
        "publipost": None,
        "data_coleta": data_coleta,
    }


def baixar_video(video_id: str, pasta: Path) -> bool:
    destino = pasta / f"{video_id}.mp4"
    if destino.exists() and destino.stat().st_size > 0:
        return True
    import yt_dlp
    pasta.mkdir(parents=True, exist_ok=True)
    opts = {"format": _cfg()["formato_ytdlp"], "outtmpl": str(destino), "quiet": True,
            "no_warnings": True, "retries": 4, "merge_output_format": "mp4"}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        return destino.exists()
    except Exception as e:  # noqa: BLE001
        log.warning("yt-dlp falhou para %s: %s", video_id, e)
        return False


def main(argv: list[str] | None = None) -> int:
    cfg = load_coleta()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perfis", default=cfg["perfis_csv"])
    ap.add_argument("--limite", type=int, default=_cfg()["limite_padrao"], help="vídeos inspecionados por canal")
    ap.add_argument("--apenas", help="canais (@handle ou UC...) separados por vírgula")
    ap.add_argument("--max-perfis", type=int)
    ap.add_argument("--saida", default=cfg["saida_padrao"])
    ap.add_argument("--sem-midia", action="store_true")
    ap.add_argument("--incluir-longos", action="store_true", help="não descarta vídeos > 180 s")
    args = ap.parse_args(argv)

    configure_logging()
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        print("YOUTUBE_API_KEY ausente (defina no .env)", file=sys.stderr)
        return 2
    from googleapiclient.discovery import build

    tabela = ler_perfis_csv(args.perfis, "youtube", args.apenas.split(",") if args.apenas else None, args.max_perfis)
    yt = build("youtube", "v3", developerKey=key, cache_discovery=False)
    saida = Path(args.saida)
    cache = saida / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    data_coleta = datetime.now(UTC)

    perfis, linhas = [], []
    for n, row in tabela.iterrows():
        handle = row["username"]
        slug = handle.lstrip("@").lower()
        try:
            canal = _cached(cache / f"yt_canal_{slug}.json", lambda: resolver_canal(yt, handle))  # noqa: B023
            uploads = canal["contentDetails"]["relatedPlaylists"]["uploads"]
            vids = _cached(cache / f"yt_videos_{slug}_{args.limite}.json",
                           lambda: detalhes_videos(yt, listar_uploads(yt, uploads, args.limite)))  # noqa: B023
        except Exception as e:  # noqa: BLE001
            log.error("%s: ERRO %s", handle, e)
            continue
        stats = canal.get("statistics", {})
        inscritos = None if stats.get("hiddenSubscriberCount") else numero(int(stats["subscriberCount"])) \
            if "subscriberCount" in stats else None
        perfis.append({"username": handle.lower(), "nome": canal["snippet"].get("title"),
                       "seguidores": inscritos, "total_posts": numero(int(stats.get("videoCount", -1))),
                       "data_coleta": data_coleta, **row.drop("username").to_dict()})
        for v in vids:
            linha = normalizar_video(v, handle, data_coleta)
            if linha["tipo_post"] != "short" and not args.incluir_longos:
                continue
            linha["seguidores"] = inscritos
            for c in ("tamanho", "tipo_conta", "segmento"):
                linha[c] = row[c]
            if not args.sem_midia and (linha["tipo_post"] == "short" or not _cfg()["baixar_apenas_shorts"]):
                linha["video_ok"] = baixar_video(linha["post_id"], saida / "midia" / "youtube")
            linhas.append(linha)
        print(f"[{n + 1}/{len(tabela)}] {handle}: {len(vids)} vídeos inspecionados")

    if not linhas:
        print("nenhum vídeo coletado")
        return 1
    pd.DataFrame(perfis).to_parquet(saida / "youtube_perfis.parquet", index=False)
    df = pd.DataFrame(linhas).drop_duplicates("post_id")
    total = len(df)
    minimo = _cfg()["idade_minima_dias"]
    elegiveis = filtrar_idade(df, minimo)
    df.drop(elegiveis.index).to_parquet(saida / "youtube_posts_excluidos.parquet", index=False)
    df = adicionar_metricas(elegiveis)
    df.to_parquet(saida / "youtube_posts.parquet", index=False)
    print(f"{total} shorts/vídeos, {len(df)} com {minimo}+ dias")
    if "video_ok" in df:
        print(f"Vídeos baixados: {int(df['video_ok'].fillna(False).sum())}/{len(df)}")
    print("Pronto:", saida.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
