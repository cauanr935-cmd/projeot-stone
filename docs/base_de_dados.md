# Base de dados — Reels de conteúdo para MPEs

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
- **Data da coleta:** 18/11/2026 (UTC; todos os lotes em 17–18/11/2026).
- **Período dos posts:** 18/11/2025 a 04/11/2026 (janela de 12 meses,
  só posts com ≥ 14 dias na coleta).
- **Volume final:** **776 Reels de 37 perfis** (697 aptos
  ao ranking; 79 com curtidas ocultas). Mídia baixada: 255 vídeos.
- **Meta do TAPI:** 2.000 a 5.000 publicações de ≥ 30 perfis. Atingimos o número de perfis, **não** o volume: o teto foi o
  crédito gratuito do Apify (US$ 5/mês).

## 3. Critérios de seleção dos perfis
Seleção **curada, não aleatória**: (1) marcas, bancos, fintechs e entidades do setor, verificadas manualmente no
Instagram; (2) criadores de conteúdo para MPE achados por **descoberta por hashtag**
(#mei, #microempreendedor, #pequenosnegocios, #empreendedorismo, #precificacao, #gestaofinanceira) e verificados pelo perfil (seguidores, bio).
Perfis com poucos seguidores ou bio sem relação com MPE foram descartados.

- **Tamanho:** pequeno < 50 mil seguidores; médio 50 mil–500 mil; grande > 500 mil (seguidores na data da coleta).
- **Tipo de conta:** `criador` (pessoa/consultor) ou `marca` (empresa, entidade, banco/fintech).
- **Segmento:** rótulo atribuído manualmente a partir da bio (ex.: contabilidade, gestão financeira, bancos/fintechs).

| tamanho | tipo_conta | reels | perfis |
|---|---|---|---|
| grande | criador | 1 | 1 |
| grande | marca | 96 | 6 |
| medio | criador | 126 | 7 |
| medio | marca | 108 | 5 |
| pequeno | criador | 383 | 15 |
| pequeno | marca | 62 | 3 |

**Perfis por segmento (em Reels na base):**

| segmento | reels | perfis |
|---|---|---|
| contabilidade | 190 | 8 |
| gestao_financeira | 88 | 3 |
| bancos_fintechs | 82 | 5 |
| contabilidade_mei | 72 | 3 |
| educacao_empreendedora | 67 | 3 |
| gestao_ferramentas | 54 | 2 |
| vendas_ecommerce | 47 | 2 |
| vendas_marketing | 47 | 3 |
| gestao_empresarial | 45 | 2 |
| empreendedorismo_startups | 34 | 1 |
| alimentacao_delivery | 32 | 1 |
| precificacao_confeitaria | 10 | 1 |
| precificacao | 6 | 1 |
| ideias_de_negocio | 1 | 1 |
| servicos_juridicos_financeiros | 1 | 1 |

## 4. Perfis na base (37)
| username | tamanho | tipo_conta | segmento | seguidores | n_reels_base |
|---|---|---|---|---|---|
| infinitepay | grande | marca | bancos_fintechs | 2466443 | 15 |
| sebrae | grande | marca | educacao_empreendedora | 2332169 | 13 |
| larissa.brandao.adv | grande | criador | servicos_juridicos_financeiros | 1179850 | 1 |
| pagbank | grande | marca | bancos_fintechs | 888981 | 4 |
| serasa | grande | marca | bancos_fintechs | 823295 | 18 |
| sicoob | grande | marca | bancos_fintechs | 581094 | 14 |
| sebraesp | grande | marca | educacao_empreendedora | 517169 | 32 |
| nuvemshop | medio | marca | vendas_ecommerce | 489108 | 12 |
| anajords | medio | criador | vendas_marketing | 399124 | 9 |
| rodrigofinancas | medio | criador | gestao_financeira | 376143 | 28 |
| chefamandasimao | medio | criador | precificacao_confeitaria | 336400 | 10 |
| contaazul | medio | marca | gestao_ferramentas | 334105 | 20 |
| ideiasquepagam25 | medio | criador | ideias_de_negocio | 240999 | 1 |
| wjrconsulting | medio | criador | gestao_financeira | 212908 | 25 |
| contabilizei | medio | marca | contabilidade | 210909 | 18 |
| getnetbrasil | medio | marca | bancos_fintechs | 128782 | 31 |
| carlosrochap | medio | criador | contabilidade | 84868 | 21 |
| carlaandradeconfeitaria | medio | criador | alimentacao_delivery | 78282 | 32 |
| cont.dm | medio | marca | contabilidade | 69396 | 27 |
| daniel.startups | pequeno | criador | empreendedorismo_startups | 40882 | 34 |
| contabilidadesfree | pequeno | criador | contabilidade | 33435 | 35 |
| bsuguino | pequeno | criador | contabilidade_mei | 31106 | 27 |
| cassia.feitosa.contadora | pequeno | criador | contabilidade | 25345 | 28 |
| brunameyercon | pequeno | criador | contabilidade | 22653 | 30 |
| yagolopesconsultor | pequeno | criador | gestao_empresarial | 20178 | 26 |
| _aislasantos | pequeno | criador | vendas_marketing | 19335 | 24 |
| cobraai.app | pequeno | marca | gestao_ferramentas | 18362 | 34 |
| chiavenato.rodrigo | pequeno | criador | gestao_empresarial | 15657 | 19 |
| gustavo.contabeis | pequeno | criador | contabilidade_mei | 14928 | 10 |
| contabilidadeparainiciante98 | pequeno | criador | contabilidade | 13654 | 8 |
| ribinosites | pequeno | criador | vendas_marketing | 5385 | 14 |
| impulsostone | pequeno | marca | educacao_empreendedora | 4283 | 22 |
| erick.rossine | pequeno | criador | vendas_ecommerce | 4188 | 35 |
| bettynaoficial | pequeno | criador | gestao_financeira | 3754 | 35 |
| contadoragabrielly_ | pequeno | criador | contabilidade | 2536 | 23 |
| precifysistema | pequeno | marca | precificacao | 1326 | 6 |
| contadoratainaraparanhos | pequeno | criador | contabilidade_mei | 1165 | 35 |

**Perfis coletados que ficaram sem Reels elegíveis (4):**

| username | tamanho | tipo_conta | n_reels_excluidos |
|---|---|---|---|
| pagseguro | medio | marca | 0 |
| dicasdeliverymelhor | medio | criador | 35 |
| papodevalor | pequeno | criador | 0 |
| monick_cosmeticos2 | pequeno | criador | 34 |

## 5. Posts excluídos e por quê
Total de posts excluídos: **515** (detalhe linha a linha em `excluidos.parquet`).

| motivo | posts | por quê |
|---|---|---|
| colaboracao_dono_diferente | 136 | Reel da grade do perfil, mas de outra conta (seguidores não são do dono) |
| fora_do_foco_reels | 42 | carrossel ou imagem (piloto do @impulsostone); a base é só de Reels |
| fora_janela_12m | 7 | publicado há mais de 12 meses da data da coleta (fora da janela de atividade) |
| menos_14_dias | 330 | publicado há menos de 14 dias na data da coleta (métricas não estabilizadas) |

## 6. Limitações
1. **Seguidores na data da coleta, não na do post.** `taxa_eng` usa o número atual; perfis que cresceram ou encolheram
   distorcem posts antigos.
2. **Viés de sobrevivência e de seleção.** Só vemos perfis que ainda existem e que achamos (hashtag + curadoria).
   Quem parou de postar ou apagou conteúdo fica de fora.
3. **Viés de descoberta por hashtag:** os criadores achados já apareciam em buscas de MPE (provavelmente mais engajados).
4. **Curtidas ocultas:** 79 Reels (10%) não têm curtidas;
   ficam na base mas **fora do ranking**.
5. **Cobertura limitada por perfil:** o scraper devolve os Reels mais recentes (teto de ~35 por perfil). Em perfis que
   postam muito, a janela efetiva é bem menor que 12 meses. Perfis possivelmente truncados:
   impulsostone, sebraesp, rodrigofinancas, chefamandasimao, dicasdeliverymelhor, carlosrochap, cassia.feitosa.contadora, yagolopesconsultor, brunameyercon, contabilidadesfree, _aislasantos, bettynaoficial, erick.rossine, contadoragabrielly_, contadoratainaraparanhos, larissa.brandao.adv, ideiasquepagam25, monick_cosmeticos2, cobraai.app, daniel.startups.
6. **Desbalanceamento:** a base é dominada por contabilidade e por contas pequenas; só 97 Reels vêm de
   contas grandes e há apenas **1** criador grande. Perfis com poucos Reels geram `score_relativo` instável.
7. **Métricas de 14 dias:** posts mais novos foram excluídos; ainda assim as métricas não são finais.
8. **Visualizações:** `views` = `videoPlayCount` (inclui replays); não são comparáveis a "alcance único".
9. **Sem dados da Stone** (Insights): o indicador de lead é indireto (CTA e comentários).

## 7. Schema da tabela `posts`
Arquivos: `posts.parquet`, `perfis.parquet`, `excluidos.parquet` e `base.duckdb` (view `reels_elegiveis`).

| coluna | tipo |
|---|---|
| plataforma | string |
| post_id | string |
| url | string |
| username | string |
| tipo_post | string |
| product_type | string |
| legenda | string |
| data_post | datetime64[ns, UTC] |
| data_coleta | datetime64[ns, UTC] |
| idade_dias | Int64 |
| curtidas | Int64 |
| comentarios | Int64 |
| views | Int64 |
| duracao_s | Float64 |
| n_slides | Int64 |
| collab | boolean |
| publipost | boolean |
| seguidores | Int64 |
| tamanho | string |
| tipo_conta | string |
| segmento | string |
| curtidas_ocultas | boolean |
| elegivel_ranking | boolean |
| taxa_eng | Float64 |
| score_relativo | Float64 |
| alcance | Float64 |
| ressonancia | Float64 |
| thumb_ok | boolean |
| video_ok | boolean |
| pasta_midia | string |
| grupo_midia | string |
| lote | string |
| hashtags | list<string> |

Métricas: `taxa_eng = (curtidas + comentarios) / seguidores`; `score_relativo = taxa_eng / mediana(taxa_eng do perfil)`;
`alcance = views / seguidores`; `ressonancia = (curtidas + comentarios) / views`.
(`limite_padrao` de referência: 150.)
