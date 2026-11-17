"""
Coleta de posts do Instagram via Apify + download da mídia (vídeo, thumbnail, slides).

Uso:
    pip install -r requirements.txt
    export APIFY_TOKEN="seu_token"          # Apify Console > Settings > API & Integrations
    python coleta_instagram.py --perfis perfis.csv --desde 2025-11-01 --limite 150

Saídas (pasta --saida, padrão "dados/"):
    instagram_perfis.parquet   -> 1 linha por perfil (seguidores no dia da coleta)
    instagram_posts.parquet    -> 1 linha por post, já com taxa de engajamento e score relativo
    midia/instagram/<shortCode>/  -> video.mp4, thumb.jpg, slide_XX.jpg
    cache/                     -> respostas brutas do Apify (re-rodar não cobra de novo)
"""
import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
from apify_client import ApifyClient

ACTOR_POSTS = "apify/instagram-scraper"          # posts de todos os tipos (reels, carrossel, imagem)
ACTOR_PERFIS = "apify/instagram-profile-scraper"  # seguidores e dados do perfil
IDADE_MINIMA_DIAS = 14                            # regra do case: métricas estabilizadas
TIPOS = {"Video": "reels", "Sidecar": "carrossel", "Image": "imagem"}


# --------------------------------------------------------------------------- Apify
def rodar_actor(client: ApifyClient, actor: str, entrada: dict, cache: Path) -> list[dict]:
    """Roda o actor só se não existir cache. Evita pagar duas vezes pela mesma coleta."""
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    run = client.actor(actor).call(run_input=entrada)
    itens = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    cache.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
    return itens


def coletar_perfis(client, usernames, pasta_cache, dia):
    itens = rodar_actor(
        client, ACTOR_PERFIS, {"usernames": usernames},
        pasta_cache / f"perfis_{dia}.json",
    )
    linhas = []
    for p in itens:
        linhas.append({
            "username": (p.get("username") or "").lower(),
            "nome": p.get("fullName"),
            "seguidores": p.get("followersCount"),
            "seguindo": p.get("followsCount"),
            "total_posts": p.get("postsCount"),
            "verificado": p.get("verified"),
            "conta_comercial": p.get("isBusinessAccount"),
            "categoria_ig": p.get("businessCategoryName"),
            "bio": p.get("biography"),
            "erro": p.get("error"),
        })
    return pd.DataFrame(linhas)


def coletar_posts_perfil(client, username, desde, limite, pasta_cache):
    """Um run por perfil: se um falhar, você re-roda só ele."""
    entrada = {
        "directUrls": [f"https://www.instagram.com/{username}/"],
        "resultsType": "posts",
        "resultsLimit": limite,
        "onlyPostsNewerThan": desde,
    }
    return rodar_actor(client, ACTOR_POSTS, entrada, pasta_cache / f"posts_{username}.json")


# --------------------------------------------------------------------------- Download
def baixar(url: str | None, destino: Path, tentativas: int = 4) -> bool:
    """Download com cache e backoff. URLs do Instagram expiram em ~1 dia: baixe logo após a coleta."""
    if not url:
        return False
    if destino.exists() and destino.stat().st_size > 0:
        return True
    destino.parent.mkdir(parents=True, exist_ok=True)
    for i in range(tentativas):
        try:
            r = requests.get(url, stream=True, timeout=60)
            if r.status_code == 403:      # link expirado: precisa re-rodar o actor
                return False
            if r.status_code == 429:      # limite de requisição
                time.sleep(5 * 2 ** i)
                continue
            r.raise_for_status()
            tmp = destino.with_suffix(destino.suffix + ".part")
            with open(tmp, "wb") as f:
                for bloco in r.iter_content(1 << 20):
                    f.write(bloco)
            tmp.rename(destino)
            return True
        except requests.RequestException:
            time.sleep(2 * 2 ** i)
    return False


def baixar_midia(post: dict, pasta: Path, max_slides: int = 10) -> dict:
    tipo = TIPOS.get(post.get("type"), post.get("type"))
    status = {
        "thumb_ok": baixar(post.get("displayUrl"), pasta / "thumb.jpg"),
        "video_ok": False,
        "slides_baixados": 0,
    }
    if tipo == "reels":
        status["video_ok"] = baixar(post.get("videoUrl"), pasta / "video.mp4")
    elif tipo == "carrossel":
        for i, filho in enumerate((post.get("childPosts") or [])[:max_slides], start=1):
            if baixar(filho.get("displayUrl"), pasta / f"slide_{i:02d}.jpg"):
                status["slides_baixados"] += 1
    return status


# --------------------------------------------------------------------------- Normalização
def numero(v):
    """Instagram devolve None ou -1 quando o dono esconde as curtidas."""
    return None if v is None or v < 0 else v


def normalizar_post(p: dict, data_coleta: datetime) -> dict:
    ts = pd.to_datetime(p.get("timestamp"), utc=True)
    return {
        "plataforma": "instagram",
        "post_id": p.get("shortCode"),
        "url": p.get("url"),
        "username": (p.get("ownerUsername") or "").lower(),
        "tipo_post": TIPOS.get(p.get("type"), p.get("type")),
        "product_type": p.get("productType"),
        "legenda": p.get("caption"),
        "hashtags": p.get("hashtags"),
        "data_post": ts,
        "idade_dias": (pd.Timestamp(data_coleta) - ts).days if pd.notna(ts) else None,
        "curtidas": numero(p.get("likesCount")),
        "comentarios": numero(p.get("commentsCount")),
        "views": numero(p.get("videoPlayCount") or p.get("videoViewCount")),
        "duracao_s": p.get("videoDuration"),
        "n_slides": len(p.get("childPosts") or []),
        "collab": bool(p.get("coauthorProducers")),
        "publipost": p.get("isSponsored") or p.get("paidPartnership"),
        "data_coleta": data_coleta,
    }


def adicionar_metricas(df: pd.DataFrame) -> pd.DataFrame:
    df["curtidas_ocultas"] = df["curtidas"].isna()
    df["taxa_eng"] = (df["curtidas"] + df["comentarios"]) / df["seguidores"]
    # Score relativo: quanto o post foi acima/abaixo do normal do próprio perfil
    mediana = df.groupby("username")["taxa_eng"].transform("median")
    df["score_relativo"] = df["taxa_eng"] / mediana
    # Reels: alcance (views/seguidores) e ressonância (interações/views)
    df["alcance"] = df["views"] / df["seguidores"]
    df["ressonancia"] = (df["curtidas"] + df["comentarios"]) / df["views"]
    return df


# --------------------------------------------------------------------------- Main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perfis", default="perfis.csv")
    ap.add_argument("--desde", default=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                    help="só posts publicados a partir desta data (AAAA-MM-DD)")
    ap.add_argument("--limite", type=int, default=150, help="máximo de posts por perfil")
    ap.add_argument("--saida", default="dados")
    ap.add_argument("--sem-midia", action="store_true", help="coleta só os metadados")
    args = ap.parse_args()

    client = ApifyClient(os.environ["APIFY_TOKEN"])
    saida = Path(args.saida)
    cache = saida / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    data_coleta = datetime.now(timezone.utc)
    dia = data_coleta.strftime("%Y-%m-%d")

    tabela = pd.read_csv(args.perfis)
    tabela = tabela[tabela["plataforma"].str.lower() == "instagram"].copy()
    tabela["username"] = tabela["username"].str.strip().str.lstrip("@").str.lower()
    usernames = tabela["username"].tolist()
    print(f"{len(usernames)} perfis do Instagram")

    # 1) Perfis (seguidores no dia da coleta)
    perfis = coletar_perfis(client, usernames, cache, dia)
    perfis["data_coleta"] = data_coleta
    perfis = perfis.merge(tabela, on="username", how="left")  # traz tamanho, tipo_conta, segmento
    perfis.to_parquet(saida / "instagram_perfis.parquet", index=False)

    # 2) Posts + mídia, perfil por perfil
    linhas = []
    for n, user in enumerate(usernames, start=1):
        try:
            posts = coletar_posts_perfil(client, user, args.desde, args.limite, cache)
        except Exception as e:  # um perfil com erro não derruba a coleta
            print(f"[{n}/{len(usernames)}] {user}: ERRO {e}")
            continue
        print(f"[{n}/{len(usernames)}] {user}: {len(posts)} posts")
        for p in posts:
            if p.get("error") or not p.get("shortCode"):
                continue
            linha = normalizar_post(p, data_coleta)
            if not args.sem_midia:
                pasta = saida / "midia" / "instagram" / linha["post_id"]
                linha.update(baixar_midia(p, pasta))
                linha["pasta_midia"] = str(pasta)
            linhas.append(linha)

    df = pd.DataFrame(linhas).drop_duplicates("post_id")
    df = df.merge(perfis[["username", "seguidores", "tamanho", "tipo_conta", "segmento"]],
                  on="username", how="left")

    total = len(df)
    df = df[df["idade_dias"] >= IDADE_MINIMA_DIAS]
    print(f"{total} posts coletados, {len(df)} com {IDADE_MINIMA_DIAS}+ dias")

    df = adicionar_metricas(df)
    df.to_parquet(saida / "instagram_posts.parquet", index=False)
    if "video_ok" in df:
        reels = df["tipo_post"] == "reels"
        print(f"Vídeos baixados: {df.loc[reels, 'video_ok'].sum()}/{reels.sum()}")
    print("Pronto:", saida.resolve())


if __name__ == "__main__":
    main()
