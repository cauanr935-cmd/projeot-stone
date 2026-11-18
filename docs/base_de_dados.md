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
- **Volume final:** **2715 Reels de 126 perfis** (2524 aptos
  ao ranking; 191 com curtidas ocultas). Mídia baixada: 562 vídeos.
- **Meta do TAPI:** 2.000 a 5.000 publicações de ≥ 30 perfis. Meta atingida: 2715 Reels de 126 perfis. O teto de volume é o
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
| grande | criador | 88 | 7 |
| grande | marca | 96 | 6 |
| medio | criador | 608 | 30 |
| medio | marca | 205 | 9 |
| pequeno | criador | 1488 | 63 |
| pequeno | marca | 230 | 11 |

**Perfis por segmento (em Reels na base):**

| segmento | reels | perfis |
|---|---|---|
| contabilidade | 536 | 24 |
| gestao_financeira | 434 | 20 |
| contabilidade_mei | 395 | 20 |
| gestao_empresarial | 303 | 12 |
| vendas_ecommerce | 157 | 7 |
| educacao_empreendedora | 132 | 6 |
| vendas_marketing | 125 | 7 |
| alimentacao_delivery | 120 | 4 |
| bancos_fintechs | 114 | 6 |
| artesanato_varejo | 61 | 2 |
| precificacao | 61 | 3 |
| varejo | 58 | 2 |
| gestao_ferramentas | 54 | 2 |
| empreendedorismo | 49 | 3 |
| economia_negocios | 48 | 2 |
| empreendedorismo_startups | 34 | 1 |
| precificacao_confeitaria | 31 | 2 |
| ideias_de_negocio | 2 | 2 |
| servicos_juridicos_financeiros | 1 | 1 |

## 4. Perfis na base (126)
| username | tamanho | tipo_conta | segmento | seguidores | n_reels_base |
|---|---|---|---|---|---|
| infinitepay | grande | marca | bancos_fintechs | 2466443 | 15 |
| sebrae | grande | marca | educacao_empreendedora | 2332169 | 13 |
| larissa.brandao.adv | grande | criador | servicos_juridicos_financeiros | 1179850 | 1 |
| nathfinancas | grande | criador | gestao_financeira | 1101238 | 22 |
| laertejr_mkt | grande | criador | ideias_de_negocio | 983208 | 1 |
| pagbank | grande | marca | bancos_fintechs | 888981 | 4 |
| serasa | grande | marca | bancos_fintechs | 823295 | 18 |
| nayradelduca | grande | criador | contabilidade_mei | 782969 | 1 |
| cassauara | grande | criador | vendas_ecommerce | 700985 | 21 |
| sicoob | grande | marca | bancos_fintechs | 581094 | 14 |
| sebraesp | grande | marca | educacao_empreendedora | 517169 | 32 |
| alinenunesvendas | grande | criador | vendas_marketing | 510186 | 13 |
| larice_ | grande | criador | precificacao | 503651 | 29 |
| nuvemshop | medio | marca | vendas_ecommerce | 489108 | 12 |
| anajords | medio | criador | vendas_marketing | 399124 | 9 |
| vitoresprega | medio | criador | empreendedorismo | 396248 | 25 |
| rodrigofinancas | medio | criador | gestao_financeira | 376143 | 28 |
| chefamandasimao | medio | criador | precificacao_confeitaria | 336400 | 10 |
| contaazul | medio | marca | gestao_ferramentas | 334105 | 20 |
| rafaelafreitascs | medio | criador | vendas_ecommerce | 328037 | 35 |
| souromilsoncosta | medio | criador | gestao_empresarial | 317661 | 13 |
| rogertoshi | medio | criador | gestao_financeira | 306271 | 22 |
| thiagofranco | medio | criador | vendas_ecommerce | 275834 | 3 |
| digymaiscontabilidade | medio | criador | contabilidade | 272553 | 32 |
| igorlopesecom | medio | criador | vendas_ecommerce | 264479 | 18 |
| ideiasquepagam25 | medio | criador | ideias_de_negocio | 240999 | 1 |
| btgpactualempresas | medio | marca | bancos_fintechs | 225848 | 32 |
| joaododelivery | medio | criador | alimentacao_delivery | 223839 | 22 |
| wjrconsulting | medio | criador | gestao_financeira | 212908 | 25 |
| mitjunior | medio | criador | gestao_financeira | 211214 | 15 |
| contabilizei | medio | marca | contabilidade | 210909 | 18 |
| sebraegoias | medio | marca | educacao_empreendedora | 192703 | 13 |
| alinenasvendas | medio | criador | vendas_marketing | 184873 | 25 |
| gerenciandodocerias | medio | criador | precificacao_confeitaria | 177250 | 21 |
| bruhcams | medio | criador | gestao_financeira | 167581 | 5 |
| gui_nonato | medio | criador | vendas_ecommerce | 156595 | 33 |
| getnetbrasil | medio | marca | bancos_fintechs | 128782 | 31 |
| welbertandradee | medio | criador | contabilidade | 120403 | 2 |
| karinasouza.pro | medio | criador | vendas_marketing | 119289 | 31 |
| nadapodenosparar_npnp | medio | criador | gestao_empresarial | 108829 | 17 |
| sebraematogrosso | medio | marca | educacao_empreendedora | 108064 | 24 |
| gustavosaballoscontador | medio | criador | contabilidade | 100340 | 15 |
| scrapdalika | medio | criador | artesanato_varejo | 94093 | 33 |
| flui.cc | medio | marca | educacao_empreendedora | 90422 | 28 |
| delmateodoraconsultora | medio | criador | gestao_empresarial | 88342 | 36 |
| carlosrochap | medio | criador | contabilidade | 84868 | 21 |
| carlaandradeconfeitaria | medio | criador | alimentacao_delivery | 78282 | 32 |
| cont.dm | medio | marca | contabilidade | 69396 | 27 |
| thioliveira.oficial | medio | criador | empreendedorismo | 67104 | 3 |
| wmaciel.oficial | medio | criador | gestao_empresarial | 66164 | 36 |
| mpfempresas | medio | criador | gestao_financeira | 60097 | 9 |
| fiscalsemprejuizo | medio | criador | contabilidade_mei | 55627 | 31 |
| vivendodepresentes | pequeno | criador | artesanato_varejo | 47794 | 28 |
| eduardodetomini | pequeno | criador | precificacao | 46660 | 26 |
| raphael_belloni | pequeno | criador | gestao_financeira | 43583 | 28 |
| tributos_simples_nacional | pequeno | criador | contabilidade | 43247 | 33 |
| nolucrocnn | pequeno | marca | economia_negocios | 43101 | 17 |
| daniel.startups | pequeno | criador | empreendedorismo_startups | 40882 | 34 |
| lelnobrega | pequeno | criador | gestao_financeira | 37051 | 32 |
| contabilidadesfree | pequeno | criador | contabilidade | 33435 | 35 |
| raquel.holler | pequeno | criador | gestao_financeira | 32696 | 31 |
| nexoeconomia | pequeno | marca | economia_negocios | 32262 | 31 |
| bsuguino | pequeno | criador | contabilidade_mei | 31106 | 27 |
| celiofurtado84 | pequeno | criador | varejo | 25640 | 36 |
| cassia.feitosa.contadora | pequeno | criador | contabilidade | 25345 | 28 |
| paulinhosanttoos | pequeno | criador | vendas_marketing | 24320 | 9 |
| euarmandorocha | pequeno | criador | contabilidade | 23603 | 9 |
| brunameyercon | pequeno | criador | contabilidade | 22653 | 30 |
| yagolopesconsultor | pequeno | criador | gestao_empresarial | 20178 | 26 |
| _aislasantos | pequeno | criador | vendas_marketing | 19335 | 24 |
| cobraai.app | pequeno | marca | gestao_ferramentas | 18362 | 34 |
| prismacontabilidademg | pequeno | criador | contabilidade | 15829 | 9 |
| chiavenato.rodrigo | pequeno | criador | gestao_empresarial | 15657 | 19 |
| gustavo.contabeis | pequeno | criador | contabilidade_mei | 14928 | 10 |
| fernando.ercoli | pequeno | criador | gestao_empresarial | 14872 | 18 |
| marlondomingoscontador | pequeno | criador | contabilidade_mei | 13773 | 3 |
| ericmariano.gestor | pequeno | criador | varejo | 13754 | 22 |
| contabilidadeparainiciante98 | pequeno | criador | contabilidade | 13654 | 8 |
| aguiacontabilidade | pequeno | marca | contabilidade | 12952 | 34 |
| rogeriosaffi | pequeno | criador | gestao_empresarial | 12783 | 18 |
| biancaleal.c | pequeno | criador | gestao_empresarial | 12023 | 28 |
| administradoracamila | pequeno | criador | gestao_financeira | 10174 | 15 |
| contadoramayaranery | pequeno | criador | contabilidade_mei | 10171 | 7 |
| souminha.gestao | pequeno | criador | gestao_empresarial | 9060 | 33 |
| madelaine_doces | pequeno | criador | alimentacao_delivery | 8609 | 35 |
| kenia.contadora | pequeno | criador | contabilidade_mei | 7392 | 30 |
| delyciasdapri | pequeno | criador | alimentacao_delivery | 7100 | 31 |
| jocelaniocosta | pequeno | criador | contabilidade | 6351 | 30 |
| cactoscontabilidade | pequeno | marca | contabilidade | 6009 | 17 |
| giovannaesanttos | pequeno | criador | contabilidade_mei | 5807 | 21 |
| lleticiasantos | pequeno | criador | contabilidade_mei | 5683 | 15 |
| dominguesemotaconsultoria | pequeno | criador | gestao_financeira | 5666 | 34 |
| ribinosites | pequeno | criador | vendas_marketing | 5385 | 14 |
| scvconsultoriaemgestao | pequeno | criador | gestao_empresarial | 4585 | 29 |
| granapratica13 | pequeno | criador | gestao_financeira | 4507 | 13 |
| impulsostone | pequeno | marca | educacao_empreendedora | 4283 | 22 |
| erick.rossine | pequeno | criador | vendas_ecommerce | 4188 | 35 |
| gabybutzke.cont | pequeno | criador | contabilidade | 4129 | 36 |
| _foconomei | pequeno | criador | contabilidade_mei | 4105 | 2 |
| topmeiconsultoria.20 | pequeno | criador | contabilidade_mei | 3980 | 33 |
| elicelma_contabil | pequeno | criador | contabilidade_mei | 3948 | 2 |
| estelia.mei | pequeno | criador | gestao_financeira | 3811 | 12 |
| ideale_contabilidade | pequeno | marca | contabilidade_mei | 3767 | 15 |
| bettynaoficial | pequeno | criador | gestao_financeira | 3754 | 35 |
| hm_vanellidomingues | pequeno | criador | gestao_financeira | 3751 | 15 |
| graciellecontabeis | pequeno | criador | contabilidade_mei | 3634 | 34 |
| costaaraujocontabeis | pequeno | marca | contabilidade_mei | 3398 | 31 |
| contadoratatimartins | pequeno | criador | contabilidade | 3393 | 35 |
| contabilidade.hope | pequeno | criador | contabilidade_mei | 3324 | 14 |
| ionaraklsantos | pequeno | criador | gestao_financeira | 3315 | 34 |
| mariana.fernandes.ceo | pequeno | criador | empreendedorismo | 3105 | 21 |
| alineferraracontabilidade | pequeno | criador | contabilidade | 3017 | 16 |
| orival.jr | pequeno | criador | gestao_financeira | 2963 | 18 |
| nathaliasantoscontabil | pequeno | criador | contabilidade | 2959 | 21 |
| sandrareiscontadora | pequeno | criador | contabilidade_mei | 2675 | 38 |
| contadoragabrielly_ | pequeno | criador | contabilidade | 2536 | 23 |
| narahrank | pequeno | criador | gestao_empresarial | 2443 | 30 |
| milenaf.contadora | pequeno | criador | contabilidade_mei | 2001 | 36 |
| diegofigueiredon | pequeno | criador | contabilidade | 1995 | 34 |
| amandaoliveirafinancas | pequeno | criador | gestao_financeira | 1440 | 27 |
| precifysistema | pequeno | marca | precificacao | 1326 | 6 |
| mei.semcontador | pequeno | criador | contabilidade_mei | 1203 | 10 |
| contadoratainaraparanhos | pequeno | criador | contabilidade_mei | 1165 | 35 |
| moyrafinancas | pequeno | criador | gestao_financeira | 1154 | 14 |
| saldbempresarial | pequeno | marca | contabilidade | 1019 | 7 |
| jbcontabilidadeegestao | pequeno | marca | contabilidade | 1018 | 16 |

**Perfis coletados que ficaram sem Reels elegíveis (12):**

| username | tamanho | tipo_conta | n_reels_excluidos |
|---|---|---|---|
| pagseguro | medio | marca | 0 |
| dicasdeliverymelhor | medio | criador | 35 |
| papodevalor | pequeno | criador | 0 |
| monick_cosmeticos2 | pequeno | criador | 34 |
| welitonmengali | pequeno | criador | 36 |
| resultoconsultoria1 | medio | criador | 1 |
| pedrodellanora | medio | criador | 33 |
| pablovelasques | pequeno | criador | 3 |
| rendup365 | pequeno | criador | 11 |
| contabilizando.ia | pequeno | marca | 15 |
| licoesdedono | pequeno | criador | 21 |
| marcelogermanoeag | grande | criador | 11 |

## 5. Posts excluídos e por quê
Total de posts excluídos: **1596** (detalhe linha a linha em `excluidos.parquet`).

| motivo | posts | por quê |
|---|---|---|
| colaboracao_dono_diferente | 248 | Reel da grade do perfil, mas de outra conta (seguidores não são do dono) |
| fora_do_foco_reels | 42 | carrossel ou imagem (piloto do @impulsostone); a base é só de Reels |
| fora_janela_12m | 47 | publicado há mais de 12 meses da data da coleta (fora da janela de atividade) |
| menos_14_dias | 1259 | publicado há menos de 14 dias na data da coleta (métricas não estabilizadas) |

## 6. Limitações
1. **Seguidores na data da coleta, não na do post.** `taxa_eng` usa o número atual; perfis que cresceram ou encolheram
   distorcem posts antigos.
2. **Viés de sobrevivência e de seleção.** Só vemos perfis que ainda existem e que achamos (hashtag + curadoria).
   Quem parou de postar ou apagou conteúdo fica de fora.
3. **Viés de descoberta por hashtag:** os criadores achados já apareciam em buscas de MPE (provavelmente mais engajados).
4. **Curtidas ocultas:** 191 Reels (7%) não têm curtidas;
   ficam na base mas **fora do ranking**.
5. **Cobertura limitada por perfil:** o scraper devolve os Reels mais recentes (teto de ~35 por perfil). Em perfis que
   postam muito, a janela efetiva é bem menor que 12 meses. Perfis possivelmente truncados:
   impulsostone, sebraesp, rodrigofinancas, chefamandasimao, dicasdeliverymelhor, carlosrochap, cassia.feitosa.contadora, yagolopesconsultor, brunameyercon, contabilidadesfree, _aislasantos, bettynaoficial, erick.rossine, contadoragabrielly_, contadoratainaraparanhos, larissa.brandao.adv, ideiasquepagam25, monick_cosmeticos2, cobraai.app, daniel.startups, mei.semcontador, milenaf.contadora, nathaliasantoscontabil, ionaraklsantos, topmeiconsultoria.20, gabybutzke.cont, scvconsultoriaemgestao, dominguesemotaconsultoria, jocelaniocosta, delyciasdapri, kenia.contadora, madelaine_doces, souminha.gestao, marlondomingoscontador, prismacontabilidademg, welitonmengali, paulinhosanttoos, lelnobrega, eduardodetomini, vivendodepresentes, fiscalsemprejuizo, wmaciel.oficial, scrapdalika, gustavosaballoscontador, karinasouza.pro, welbertandradee, mitjunior, joaododelivery, larice_, laertejr_mkt, moyrafinancas, granapratica13, raphael_belloni, nexoeconomia, biancaleal.c, graciellecontabeis, digymaiscontabilidade, gerenciandodocerias, narahrank, rafaelafreitascs, raquel.holler, sandrareiscontadora, administradoracamila, aguiacontabilidade, alinenasvendas, alinenunesvendas, amandaoliveirafinancas, bruhcams, btgpactualempresas, cactoscontabilidade, contabilidade.hope, contadoratatimartins, costaaraujocontabeis, delmateodoraconsultora, diegofigueiredon, gui_nonato, celiofurtado84.
6. **Desbalanceamento:** a base é dominada por contabilidade e por contas pequenas; só 184 Reels vêm de
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
