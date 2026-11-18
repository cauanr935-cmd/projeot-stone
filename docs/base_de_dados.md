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
- **Volume final:** **1672 Reels de 76 perfis** (1517 aptos
  ao ranking; 155 com curtidas ocultas). Mídia baixada: 393 vídeos.
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
| grande | criador | 53 | 4 |
| grande | marca | 96 | 6 |
| medio | criador | 320 | 16 |
| medio | marca | 173 | 8 |
| pequeno | criador | 968 | 39 |
| pequeno | marca | 62 | 3 |

**Perfis por segmento (em Reels na base):**

| segmento | reels | perfis |
|---|---|---|
| contabilidade | 336 | 15 |
| gestao_financeira | 248 | 10 |
| contabilidade_mei | 232 | 11 |
| gestao_empresarial | 143 | 5 |
| educacao_empreendedora | 132 | 6 |
| alimentacao_delivery | 120 | 4 |
| vendas_marketing | 87 | 5 |
| bancos_fintechs | 82 | 5 |
| artesanato_varejo | 61 | 2 |
| precificacao | 61 | 3 |
| gestao_ferramentas | 54 | 2 |
| vendas_ecommerce | 47 | 2 |
| empreendedorismo_startups | 34 | 1 |
| varejo | 22 | 1 |
| precificacao_confeitaria | 10 | 1 |
| ideias_de_negocio | 2 | 2 |
| servicos_juridicos_financeiros | 1 | 1 |

## 4. Perfis na base (76)
| username | tamanho | tipo_conta | segmento | seguidores | n_reels_base |
|---|---|---|---|---|---|
| infinitepay | grande | marca | bancos_fintechs | 2466443 | 15 |
| sebrae | grande | marca | educacao_empreendedora | 2332169 | 13 |
| larissa.brandao.adv | grande | criador | servicos_juridicos_financeiros | 1179850 | 1 |
| nathfinancas | grande | criador | gestao_financeira | 1101238 | 22 |
| laertejr_mkt | grande | criador | ideias_de_negocio | 983208 | 1 |
| pagbank | grande | marca | bancos_fintechs | 888981 | 4 |
| serasa | grande | marca | bancos_fintechs | 823295 | 18 |
| sicoob | grande | marca | bancos_fintechs | 581094 | 14 |
| sebraesp | grande | marca | educacao_empreendedora | 517169 | 32 |
| larice_ | grande | criador | precificacao | 503651 | 29 |
| nuvemshop | medio | marca | vendas_ecommerce | 489108 | 12 |
| anajords | medio | criador | vendas_marketing | 399124 | 9 |
| rodrigofinancas | medio | criador | gestao_financeira | 376143 | 28 |
| chefamandasimao | medio | criador | precificacao_confeitaria | 336400 | 10 |
| contaazul | medio | marca | gestao_ferramentas | 334105 | 20 |
| ideiasquepagam25 | medio | criador | ideias_de_negocio | 240999 | 1 |
| joaododelivery | medio | criador | alimentacao_delivery | 223839 | 22 |
| wjrconsulting | medio | criador | gestao_financeira | 212908 | 25 |
| mitjunior | medio | criador | gestao_financeira | 211214 | 15 |
| contabilizei | medio | marca | contabilidade | 210909 | 18 |
| sebraegoias | medio | marca | educacao_empreendedora | 192703 | 13 |
| getnetbrasil | medio | marca | bancos_fintechs | 128782 | 31 |
| welbertandradee | medio | criador | contabilidade | 120403 | 2 |
| karinasouza.pro | medio | criador | vendas_marketing | 119289 | 31 |
| sebraematogrosso | medio | marca | educacao_empreendedora | 108064 | 24 |
| gustavosaballoscontador | medio | criador | contabilidade | 100340 | 15 |
| scrapdalika | medio | criador | artesanato_varejo | 94093 | 33 |
| flui.cc | medio | marca | educacao_empreendedora | 90422 | 28 |
| carlosrochap | medio | criador | contabilidade | 84868 | 21 |
| carlaandradeconfeitaria | medio | criador | alimentacao_delivery | 78282 | 32 |
| cont.dm | medio | marca | contabilidade | 69396 | 27 |
| wmaciel.oficial | medio | criador | gestao_empresarial | 66164 | 36 |
| mpfempresas | medio | criador | gestao_financeira | 60097 | 9 |
| fiscalsemprejuizo | medio | criador | contabilidade_mei | 55627 | 31 |
| vivendodepresentes | pequeno | criador | artesanato_varejo | 47794 | 28 |
| eduardodetomini | pequeno | criador | precificacao | 46660 | 26 |
| tributos_simples_nacional | pequeno | criador | contabilidade | 43247 | 33 |
| daniel.startups | pequeno | criador | empreendedorismo_startups | 40882 | 34 |
| lelnobrega | pequeno | criador | gestao_financeira | 37051 | 32 |
| contabilidadesfree | pequeno | criador | contabilidade | 33435 | 35 |
| bsuguino | pequeno | criador | contabilidade_mei | 31106 | 27 |
| cassia.feitosa.contadora | pequeno | criador | contabilidade | 25345 | 28 |
| paulinhosanttoos | pequeno | criador | vendas_marketing | 24320 | 9 |
| brunameyercon | pequeno | criador | contabilidade | 22653 | 30 |
| yagolopesconsultor | pequeno | criador | gestao_empresarial | 20178 | 26 |
| _aislasantos | pequeno | criador | vendas_marketing | 19335 | 24 |
| cobraai.app | pequeno | marca | gestao_ferramentas | 18362 | 34 |
| prismacontabilidademg | pequeno | criador | contabilidade | 15829 | 9 |
| chiavenato.rodrigo | pequeno | criador | gestao_empresarial | 15657 | 19 |
| gustavo.contabeis | pequeno | criador | contabilidade_mei | 14928 | 10 |
| marlondomingoscontador | pequeno | criador | contabilidade_mei | 13773 | 3 |
| ericmariano.gestor | pequeno | criador | varejo | 13754 | 22 |
| contabilidadeparainiciante98 | pequeno | criador | contabilidade | 13654 | 8 |
| souminha.gestao | pequeno | criador | gestao_empresarial | 9060 | 33 |
| madelaine_doces | pequeno | criador | alimentacao_delivery | 8609 | 35 |
| kenia.contadora | pequeno | criador | contabilidade_mei | 7392 | 30 |
| delyciasdapri | pequeno | criador | alimentacao_delivery | 7100 | 31 |
| jocelaniocosta | pequeno | criador | contabilidade | 6351 | 30 |
| lleticiasantos | pequeno | criador | contabilidade_mei | 5683 | 15 |
| dominguesemotaconsultoria | pequeno | criador | gestao_financeira | 5666 | 34 |
| ribinosites | pequeno | criador | vendas_marketing | 5385 | 14 |
| scvconsultoriaemgestao | pequeno | criador | gestao_empresarial | 4585 | 29 |
| impulsostone | pequeno | marca | educacao_empreendedora | 4283 | 22 |
| erick.rossine | pequeno | criador | vendas_ecommerce | 4188 | 35 |
| gabybutzke.cont | pequeno | criador | contabilidade | 4129 | 36 |
| topmeiconsultoria.20 | pequeno | criador | contabilidade_mei | 3980 | 33 |
| elicelma_contabil | pequeno | criador | contabilidade_mei | 3948 | 2 |
| bettynaoficial | pequeno | criador | gestao_financeira | 3754 | 35 |
| ionaraklsantos | pequeno | criador | gestao_financeira | 3315 | 34 |
| nathaliasantoscontabil | pequeno | criador | contabilidade | 2959 | 21 |
| contadoragabrielly_ | pequeno | criador | contabilidade | 2536 | 23 |
| milenaf.contadora | pequeno | criador | contabilidade_mei | 2001 | 36 |
| precifysistema | pequeno | marca | precificacao | 1326 | 6 |
| mei.semcontador | pequeno | criador | contabilidade_mei | 1203 | 10 |
| contadoratainaraparanhos | pequeno | criador | contabilidade_mei | 1165 | 35 |
| moyrafinancas | pequeno | criador | gestao_financeira | 1154 | 14 |

**Perfis coletados que ficaram sem Reels elegíveis (7):**

| username | tamanho | tipo_conta | n_reels_excluidos |
|---|---|---|---|
| pagseguro | medio | marca | 0 |
| dicasdeliverymelhor | medio | criador | 35 |
| papodevalor | pequeno | criador | 0 |
| monick_cosmeticos2 | pequeno | criador | 34 |
| welitonmengali | pequeno | criador | 36 |
| resultoconsultoria1 | medio | criador | 1 |
| pedrodellanora | medio | criador | 33 |

## 5. Posts excluídos e por quê
Total de posts excluídos: **1003** (detalhe linha a linha em `excluidos.parquet`).

| motivo | posts | por quê |
|---|---|---|
| colaboracao_dono_diferente | 167 | Reel da grade do perfil, mas de outra conta (seguidores não são do dono) |
| fora_do_foco_reels | 42 | carrossel ou imagem (piloto do @impulsostone); a base é só de Reels |
| fora_janela_12m | 21 | publicado há mais de 12 meses da data da coleta (fora da janela de atividade) |
| menos_14_dias | 773 | publicado há menos de 14 dias na data da coleta (métricas não estabilizadas) |

## 6. Limitações
1. **Seguidores na data da coleta, não na do post.** `taxa_eng` usa o número atual; perfis que cresceram ou encolheram
   distorcem posts antigos.
2. **Viés de sobrevivência e de seleção.** Só vemos perfis que ainda existem e que achamos (hashtag + curadoria).
   Quem parou de postar ou apagou conteúdo fica de fora.
3. **Viés de descoberta por hashtag:** os criadores achados já apareciam em buscas de MPE (provavelmente mais engajados).
4. **Curtidas ocultas:** 155 Reels (9%) não têm curtidas;
   ficam na base mas **fora do ranking**.
5. **Cobertura limitada por perfil:** o scraper devolve os Reels mais recentes (teto de ~35 por perfil). Em perfis que
   postam muito, a janela efetiva é bem menor que 12 meses. Perfis possivelmente truncados:
   impulsostone, sebraesp, rodrigofinancas, chefamandasimao, dicasdeliverymelhor, carlosrochap, cassia.feitosa.contadora, yagolopesconsultor, brunameyercon, contabilidadesfree, _aislasantos, bettynaoficial, erick.rossine, contadoragabrielly_, contadoratainaraparanhos, larissa.brandao.adv, ideiasquepagam25, monick_cosmeticos2, cobraai.app, daniel.startups, mei.semcontador, milenaf.contadora, nathaliasantoscontabil, ionaraklsantos, topmeiconsultoria.20, gabybutzke.cont, scvconsultoriaemgestao, dominguesemotaconsultoria, jocelaniocosta, delyciasdapri, kenia.contadora, madelaine_doces, souminha.gestao, marlondomingoscontador, prismacontabilidademg, welitonmengali, paulinhosanttoos, lelnobrega, eduardodetomini, vivendodepresentes, fiscalsemprejuizo, wmaciel.oficial, scrapdalika, gustavosaballoscontador, karinasouza.pro, welbertandradee, mitjunior, joaododelivery, larice_, laertejr_mkt, moyrafinancas.
6. **Desbalanceamento:** a base é dominada por contabilidade e por contas pequenas; só 149 Reels vêm de
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
