"""Coleta de posts do Instagram via Apify + download de mídia (vídeo, thumb, slides).

Uso:
    export APIFY_TOKEN=...            # ou no .env
    python -m src.coleta.instagram --desde 2026-01-01 --limite 10 --apenas user1,user2

Saídas (pasta --saida, padrão `dados/`):
    instagram_perfis.parquet, instagram_posts.parquet, midia/instagram/<shortCode>/, cache/
O cache guarda a resposta bruta e o custo de cada run; re-rodar não cobra de novo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.coleta.metricas import adicionar_metricas, filtrar_idade, numero
from src.core.config import load_coleta
from src.core.logging import configure_logging

log = logging.getLogger(__name__)


def _cfg() -> dict:
    return load_coleta()["instagram"]


# --------------------------------------------------------------------------- Apify
def _campo(run, *nomes):
    """Lê um campo do run: apify-client >= 3 devolve objeto pydantic; versões antigas, dict."""
    for n in nomes:
        v = run.get(n) if isinstance(run, dict) else getattr(run, n, None)
        if v is not None:
            return v
    return None


def rodar_actor(client, actor: str, entrada: dict, cache: Path) -> list[dict]:
    """Roda o actor só se não houver cache; grava custo do run em `<cache>.run.json`."""
    if cache.exists():
        log.info("cache hit: %s", cache.name)
        return json.loads(cache.read_text(encoding="utf-8"))
    run = client.actor(actor).call(run_input=entrada)
    itens = list(client.dataset(_campo(run, "default_dataset_id", "defaultDatasetId")).iterate_items())
    cache.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
    cache.with_suffix(".run.json").write_text(json.dumps({
        "actor": actor, "run_id": _campo(run, "id"), "itens": len(itens),
        "usageTotalUsd": _campo(run, "usage_total_usd", "usageTotalUsd"),
        "stats": _campo(run, "stats"),
    }, ensure_ascii=False, default=str), encoding="utf-8")
    return itens


def coletar_perfis(client, usernames: list[str], pasta_cache: Path, dia: str) -> pd.DataFrame:
    h = hashlib.sha1(",".join(sorted(usernames)).encode()).hexdigest()[:8]
    itens = rodar_actor(client, _cfg()["actor_perfis"], {"usernames": usernames},
                        pasta_cache / f"perfis_{dia}_{h}.json")
    linhas = [{
        "username": (p.get("username") or "").lower(),
        "nome": p.get("fullName"),
        "seguidores": numero(p.get("followersCount")),
        "seguindo": numero(p.get("followsCount")),
        "total_posts": numero(p.get("postsCount")),
        "verificado": p.get("verified"),
        "conta_comercial": p.get("isBusinessAccount"),
        "categoria_ig": p.get("businessCategoryName"),
        "bio": p.get("biography"),
        "erro": p.get("error"),
    } for p in itens]
    return pd.DataFrame(linhas)


def coletar_posts_perfil(client, username: str, desde: str, limite: int, pasta_cache: Path) -> list[dict]:
    """Um run por perfil. A chave do cache inclui `desde` e `limite` para não reaproveitar coleta diferente."""
    entrada = {
        "directUrls": [f"https://www.instagram.com/{username}/"],
        "resultsType": "posts",
        "resultsLimit": limite,
        "onlyPostsNewerThan": desde,
    }
    return rodar_actor(client, _cfg()["actor_posts"], entrada,
                       pasta_cache / f"posts_{username}_{desde}_{limite}.json")


# --------------------------------------------------------------------------- Download
def baixar(url: str | None, destino: Path, tentativas: int | None = None) -> bool:
    """Download com cache e backoff. URLs do Instagram expiram em ~1 dia: baixe logo após a coleta."""
    import requests

    dl = load_coleta()["download"]
    tentativas = tentativas or dl["tentativas"]
    if not url:
        return False
    if destino.exists() and destino.stat().st_size > 0:
        return True
    destino.parent.mkdir(parents=True, exist_ok=True)
    for i in range(tentativas):
        try:
            r = requests.get(url, stream=True, timeout=dl["timeout_s"])
            if r.status_code == 403:      # link expirado: precisa re-rodar o actor
                return False
            if r.status_code == 429:
                time.sleep(5 * 2 ** i)
                continue
            r.raise_for_status()
            tmp = destino.with_suffix(destino.suffix + ".part")
            with open(tmp, "wb") as f:
                f.writelines(r.iter_content(1 << 20))
            tmp.rename(destino)
            return True
        except requests.RequestException:
            time.sleep(2 * 2 ** i)
    return False


def mapear_tipo(tipo_apify: str | None) -> str | None:
    return _cfg()["tipos"].get(tipo_apify, tipo_apify)


def baixar_midia(post: dict, pasta: Path) -> dict:
    tipo = mapear_tipo(post.get("type"))
    status = {"thumb_ok": baixar(post.get("displayUrl"), pasta / "thumb.jpg"),
              "video_ok": False, "slides_baixados": 0}
    if tipo == "reels":
        status["video_ok"] = baixar(post.get("videoUrl"), pasta / "video.mp4")
    elif tipo == "carrossel":
        for i, filho in enumerate((post.get("childPosts") or [])[: _cfg()["max_slides"]], start=1):
            if baixar(filho.get("displayUrl"), pasta / f"slide_{i:02d}.jpg"):
                status["slides_baixados"] += 1
    return status


# --------------------------------------------------------------------------- Normalização
def normalizar_post(p: dict, data_coleta: datetime) -> dict:
    ts = pd.to_datetime(p.get("timestamp"), utc=True)
    views = numero(p.get("videoPlayCount"))
    if views is None:
        views = numero(p.get("videoViewCount"))
    return {
        "plataforma": "instagram",
        "post_id": p.get("shortCode"),
        "url": p.get("url"),
        "username": (p.get("ownerUsername") or "").lower(),
        "tipo_post": mapear_tipo(p.get("type")),
        "product_type": p.get("productType"),
        "legenda": p.get("caption"),
        "hashtags": p.get("hashtags"),
        "data_post": ts,
        "idade_dias": (pd.Timestamp(data_coleta) - ts).days if pd.notna(ts) else None,
        "curtidas": numero(p.get("likesCount")),
        "comentarios": numero(p.get("commentsCount")),
        "views": views,
        "duracao_s": p.get("videoDuration"),
        "n_slides": len(p.get("childPosts") or []),
        "collab": bool(p.get("coauthorProducers")),
        "publipost": p.get("isSponsored") or p.get("paidPartnership"),
        "data_coleta": data_coleta,
    }


def selecionar_top(df: pd.DataFrame, n: int) -> set[str]:
    """post_ids dos `n` mais acessados por tipo_post: views (reels) ou interações (carrossel/imagem)."""
    d = df.copy()
    d["_k"] = d["views"].where(d["tipo_post"] == "reels", d["curtidas"].fillna(0) + d["comentarios"].fillna(0))
    d["_k"] = d["_k"].fillna(0)
    return set(d.sort_values("_k", ascending=False).groupby("tipo_post").head(n)["post_id"])


# --------------------------------------------------------------------------- Perfis
def ler_perfis_csv(caminho: str | Path, plataforma: str,
                   apenas: list[str] | None = None, max_perfis: int | None = None) -> pd.DataFrame:
    tabela = pd.read_csv(caminho)
    tabela = tabela[tabela["plataforma"].str.lower() == plataforma].copy()
    tabela["username"] = tabela["username"].str.strip()
    if plataforma == "instagram":
        tabela["username"] = tabela["username"].str.lstrip("@").str.lower()
    if apenas:
        alvo = {a.strip().lstrip("@").lower() for a in apenas}
        tabela = tabela[tabela["username"].str.lstrip("@").str.lower().isin(alvo)]
    if max_perfis:
        tabela = tabela.head(max_perfis)
    return tabela.reset_index(drop=True)


def checar_custo(n_perfis: int, confirmo: bool) -> None:
    limite = load_coleta()["max_perfis_sem_confirmacao"]
    if n_perfis > limite and not confirmo:
        raise SystemExit(f"{n_perfis} perfis > {limite}: coleta paga exige --confirmo-custo "
                         "(confirme com o responsável antes).")


# --------------------------------------------------------------------------- Main
def main(argv: list[str] | None = None) -> int:
    cfg = load_coleta()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perfis", default=cfg["perfis_csv"])
    ap.add_argument("--desde", default=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                    help="só posts a partir desta data (AAAA-MM-DD)")
    ap.add_argument("--limite", type=int, default=cfg["instagram"]["limite_padrao"], help="máx. de posts por perfil")
    ap.add_argument("--apenas", help="usernames separados por vírgula (subconjunto do CSV)")
    ap.add_argument("--max-perfis", type=int)
    ap.add_argument("--saida", default=cfg["saida_padrao"])
    ap.add_argument("--top-midia", type=int, help="baixa mídia só dos N posts mais acessados por tipo")
    ap.add_argument("--sem-midia", action="store_true", help="coleta só os metadados")
    ap.add_argument("--confirmo-custo", action="store_true", help="libera coleta paga acima do limite de perfis")
    args = ap.parse_args(argv)

    configure_logging()
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("APIFY_TOKEN ausente (defina no .env)", file=sys.stderr)
        return 2
    from apify_client import ApifyClient

    tabela = ler_perfis_csv(args.perfis, "instagram", args.apenas.split(",") if args.apenas else None,
                            args.max_perfis)
    usernames = tabela["username"].tolist()
    checar_custo(len(usernames), args.confirmo_custo)
    print(f"{len(usernames)} perfis do Instagram")

    client = ApifyClient(token)
    saida = Path(args.saida)
    cache = saida / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    data_coleta = datetime.now(UTC)
    dia = data_coleta.strftime("%Y-%m-%d")

    perfis = coletar_perfis(client, usernames, cache, dia)
    perfis["data_coleta"] = data_coleta
    perfis = perfis.merge(tabela, on="username", how="left")
    perfis.to_parquet(saida / "instagram_perfis.parquet", index=False)

    linhas, brutos = [], {}
    for n, user in enumerate(usernames, start=1):
        try:
            posts = coletar_posts_perfil(client, user, args.desde, args.limite, cache)
        except Exception as e:  # um perfil com erro não derruba a coleta  # noqa: BLE001
            log.error("[%d/%d] %s: ERRO %s", n, len(usernames), user, e)
            continue
        print(f"[{n}/{len(usernames)}] {user}: {len(posts)} posts")
        for p in posts:
            if p.get("error") or not p.get("shortCode"):
                continue
            linha = normalizar_post(p, data_coleta)
            brutos[linha["post_id"]] = p
            if not args.sem_midia and args.top_midia is None:
                pasta = saida / "midia" / "instagram" / linha["post_id"]
                linha.update(baixar_midia(p, pasta))
                linha["pasta_midia"] = str(pasta)
            linhas.append(linha)

    if not linhas:
        print("nenhum post coletado")
        return 1
    df = pd.DataFrame(linhas).drop_duplicates("post_id")
    df = df.merge(perfis[["username", "seguidores", "tamanho", "tipo_conta", "segmento"]],
                  on="username", how="left")
    if not args.sem_midia and args.top_midia is not None:  # baixa logo (URLs expiram em ~1 dia)
        top = selecionar_top(df, args.top_midia)
        extras = []
        for pid in df["post_id"]:
            if pid in top:
                pasta = saida / "midia" / "instagram" / pid
                extras.append({**baixar_midia(brutos[pid], pasta), "pasta_midia": str(pasta)})
            else:
                extras.append({"thumb_ok": None, "video_ok": None, "slides_baixados": None, "pasta_midia": None})
        df = pd.concat([df.reset_index(drop=True), pd.DataFrame(extras)], axis=1)
    total = len(df)
    minimo = cfg["instagram"]["idade_minima_dias"]
    elegiveis = filtrar_idade(df, minimo)
    df.drop(elegiveis.index).to_parquet(saida / "instagram_posts_excluidos.parquet", index=False)  # < idade mínima
    df = adicionar_metricas(elegiveis)
    print(f"{total} posts coletados, {len(df)} com {minimo}+ dias")
    df.to_parquet(saida / "instagram_posts.parquet", index=False)
    if "video_ok" in df:
        reels = df["tipo_post"] == "reels"
        tentados = df.loc[reels, "video_ok"].notna()
        print(f"Vídeos baixados: {int(df.loc[reels, 'video_ok'].fillna(False).sum())}/{int(tentados.sum())} tentados "
              f"({int(reels.sum())} reels)")
    print("Pronto:", saida.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
