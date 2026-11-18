"""Gera docs/base_de_dados.md a partir da base (números sempre em sincronia com os dados).

Uso: python -m src.base.documentar [--base dados/base] [--saida docs/base_de_dados.md]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src.base.schema import MOTIVOS, POSTS_SCHEMA
from src.core.config import load_coleta


def _md(df: pd.DataFrame) -> str:
    cab = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    linhas = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([cab, sep, *linhas])


def gerar(base: Path) -> str:
    cfg = load_coleta()
    posts = pd.read_parquet(base / "posts.parquet")
    perfis = pd.read_parquet(base / "perfis.parquet")
    excl = pd.read_parquet(base / "excluidos.parquet")
    lim = cfg["instagram"]["limite_padrao"]  # só referência; o limite real por lote está em `limites`
    na_base = perfis[perfis["status"] == "na_base"]

    tam = posts.groupby(["tamanho", "tipo_conta"]).agg(reels=("post_id", "count"), perfis=("username", "nunique")) \
        .reset_index()
    seg = posts.groupby("segmento").agg(reels=("post_id", "count"), perfis=("username", "nunique")) \
        .reset_index().sort_values("reels", ascending=False)
    motivos = excl.groupby("motivo").size().rename("posts").reset_index()
    motivos["por quê"] = motivos["motivo"].map(MOTIVOS)
    sem = perfis[perfis["status"] != "na_base"][["username", "tamanho", "tipo_conta", "n_reels_excluidos"]]
    por_perfil = perfis.assign(total=perfis["n_reels_base"] + perfis["n_reels_excluidos"])
    truncados = por_perfil[por_perfil["total"] >= 34]["username"].tolist()
    pf = na_base.sort_values(["tamanho", "seguidores"], ascending=[True, False])[
        ["username", "tamanho", "tipo_conta", "segmento", "seguidores", "n_reels_base"]]
    pf = pf.assign(seguidores=pf["seguidores"].astype("Int64"))
    cols = pd.DataFrame({"coluna": list(POSTS_SCHEMA) + ["hashtags"],
                         "tipo": list(POSTS_SCHEMA.values()) + ["list<string>"]})

    return f"""# Base de dados — Reels de conteúdo para MPEs

> Gerado por `python -m src.base.documentar`. Não edite os números à mão.

## 1. Origem e licença/termos
- **Plataforma:** Instagram (só Reels; YouTube Shorts ficou fora do escopo desta entrega).
- **Rota de coleta:** actors do Apify — `apify/instagram-reel-scraper` (Reels), `apify/instagram-profile-scraper`
  (seguidores e dados do perfil) e `apify/instagram-hashtag-scraper` (apenas descoberta de perfis candidatos).
- **Dados:** somente conteúdo e métricas **públicos** (legenda, curtidas, comentários, visualizações, data, duração).
  Vídeos/thumbnails baixados servem **exclusivamente** para análise interna (frames, transcrição); **não** devem ser
  redistribuídos nem republicados. A pasta `dados/` não é versionada no git.
- **Termos de Serviço:** a rota por scraping de terceiros precisa ser compatível com o que a organização do case
  definiu no kickoff (26/10/2026). **Pendente de confirmação humana** (`docs/HUMAN_DEPENDENCIES.md`).
- **LGPD:** perfis de pessoas físicas públicas aparecem com `username` e conteúdo público; nenhum dado privado é coletado.

## 2. Data, período e volume
- **Data da coleta:** {posts['data_coleta'].min():%d/%m/%Y} (UTC; todos os lotes em 17–18/11/2026).
- **Período dos posts:** {posts['data_post'].min():%d/%m/%Y} a {posts['data_post'].max():%d/%m/%Y} (janela de 12 meses,
  só posts com ≥ {cfg['instagram']['idade_minima_dias']} dias na coleta).
- **Volume final:** **{len(posts)} Reels de {posts['username'].nunique()} perfis** ({int(posts['elegivel_ranking'].sum())} aptos
  ao ranking; {int(posts['curtidas_ocultas'].sum())} com curtidas ocultas). Mídia baixada: {int(posts['video_ok'].fillna(False).sum())} vídeos.
- **Meta do TAPI:** 2.000 a 5.000 publicações de ≥ 30 perfis. Atingimos o número de perfis, **não** o volume: o teto foi o
  crédito gratuito do Apify (US$ 5/mês).

## 3. Critérios de seleção dos perfis
Seleção **curada, não aleatória**: (1) marcas, bancos, fintechs e entidades do setor, verificadas manualmente no
Instagram; (2) criadores de conteúdo para MPE achados por **descoberta por hashtag**
({', '.join('#' + h for h in cfg['descoberta']['hashtags'])}) e verificados pelo perfil (seguidores, bio).
Perfis com poucos seguidores ou bio sem relação com MPE foram descartados.

- **Tamanho:** pequeno < 50 mil seguidores; médio 50 mil–500 mil; grande > 500 mil (seguidores na data da coleta).
- **Tipo de conta:** `criador` (pessoa/consultor) ou `marca` (empresa, entidade, banco/fintech).
- **Segmento:** rótulo atribuído manualmente a partir da bio (ex.: contabilidade, gestão financeira, bancos/fintechs).

{_md(tam)}

**Perfis por segmento (em Reels na base):**

{_md(seg)}

## 4. Perfis na base ({len(na_base)})
{_md(pf)}

**Perfis coletados que ficaram sem Reels elegíveis ({len(sem)}):**

{_md(sem)}

## 5. Posts excluídos e por quê
Total de posts excluídos: **{len(excl)}** (detalhe linha a linha em `excluidos.parquet`).

{_md(motivos)}

## 6. Limitações
1. **Seguidores na data da coleta, não na do post.** `taxa_eng` usa o número atual; perfis que cresceram ou encolheram
   distorcem posts antigos.
2. **Viés de sobrevivência e de seleção.** Só vemos perfis que ainda existem e que achamos (hashtag + curadoria).
   Quem parou de postar ou apagou conteúdo fica de fora.
3. **Viés de descoberta por hashtag:** os criadores achados já apareciam em buscas de MPE (provavelmente mais engajados).
4. **Curtidas ocultas:** {int(posts['curtidas_ocultas'].sum())} Reels ({posts['curtidas_ocultas'].mean():.0%}) não têm curtidas;
   ficam na base mas **fora do ranking**.
5. **Cobertura limitada por perfil:** o scraper devolve os Reels mais recentes (teto de ~35 por perfil). Em perfis que
   postam muito, a janela efetiva é bem menor que 12 meses. Perfis possivelmente truncados:
   {', '.join(truncados) if truncados else 'nenhum'}.
6. **Desbalanceamento:** a base é dominada por contabilidade e por contas pequenas; só {int((posts['tamanho'] == 'grande').sum())} Reels vêm de
   contas grandes e há apenas **1** criador grande. Perfis com poucos Reels geram `score_relativo` instável.
7. **Métricas de 14 dias:** posts mais novos foram excluídos; ainda assim as métricas não são finais.
8. **Visualizações:** `views` = `videoPlayCount` (inclui replays); não são comparáveis a "alcance único".
9. **Sem dados da Stone** (Insights): o indicador de lead é indireto (CTA e comentários).

## 7. Schema da tabela `posts`
Arquivos: `posts.parquet`, `perfis.parquet`, `excluidos.parquet` e `base.duckdb` (view `reels_elegiveis`).

{_md(cols)}

Métricas: `taxa_eng = (curtidas + comentarios) / seguidores`; `score_relativo = taxa_eng / mediana(taxa_eng do perfil)`;
`alcance = views / seguidores`; `ressonancia = (curtidas + comentarios) / views`.
(`limite_padrao` de referência: {lim}.)
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="dados/base")
    ap.add_argument("--saida", default="docs/base_de_dados.md")
    args = ap.parse_args(argv)
    Path(args.saida).write_text(gerar(Path(args.base)), encoding="utf-8")
    print("escrito:", args.saida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
