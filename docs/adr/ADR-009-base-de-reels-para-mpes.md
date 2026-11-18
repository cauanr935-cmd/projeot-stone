# ADR-009 — Base de Reels para MPEs (case Stone × Inteli)

**Status:** Aceito · **Fase:** 1–3 do case de análise

## Decisões
- **Foco só em Reels** (pedido do usuário); YouTube Shorts adiado (sem chave da API). O código do YouTube existe em
  `src/coleta/youtube.py`, testado com mocks.
- **Actors:** `apify/instagram-reel-scraper` (US$ 0,0026/Reel, plano gratuito) em vez do scraper de posts, mais
  barato e só Reels. Hashtag scraper apenas para **descobrir** perfis; a base é coletada **por perfil** para permitir
  `score_relativo` (post ÷ mediana do próprio perfil).
- **Orçamento:** teto de cobrança por run (`max_total_charge_usd`) + checagem de saldo antes (`checar_orcamento`);
  gasto total ≈ US$ 4,30 de US$ 5.
- **Colaborações** (dono ≠ perfil coletado) excluídas: seguidores não pertencem ao dono do post.
- **Janela:** 12 meses e ≥ 14 dias de idade; métricas recalculadas após as exclusões.
- **Base:** Parquet + DuckDB (`dados/base/`), schema em `src/base/schema.py`.

## Desvios e riscos
- `onlyPostsNewerThan` do actor não filtra posts fixados antigos: o corte de 12 meses é refeito na unificação.
- O teto de ~35 Reels por perfil trunca a janela dos perfis que postam muito.
- Volume final de **1.672 Reels de 76 perfis** (17–18/11/2026; 776 foi o volume da primeira versão, antes dos lotes 2 e 3) abaixo da meta do TAPI (2.000–5.000): limitado pelo crédito gratuito (ver H-CASE-02). A análise da Fase 5 fecha com esta base; a expansão fica como pendência humana.

## Ranking (Fase 4)
- **Principal:** `score_relativo` (taxa_eng ÷ mediana do perfil); **secundária:** `taxa_eng` do case — ambas em `ranking.parquet`.
- **Alto desempenho:** top 10% (`config/coleta.yaml › ranking.top_fracao`) **por plataforma**, entre posts aptos:
  curtidas visíveis e perfil com ≥ 5 Reels aptos (`min_reels_perfil`; com n=1 o score é 1.0 por construção).
- **Resultado (18/11/2026, após lote 3):** 1.504 aptos → 151 no top (48 perfis); 155 fora por curtidas ocultas e 13 por
  perfil com poucos Reels. Os dois rankings coincidem em 80 dos 151 posts. Scores > 20 são sinalizados
  (`score_extremo`, 70 posts), não removidos.
- **Lote 3:** 42 perfis (US$ ~3,7). Base final **1.672 Reels de 76 perfis**, abaixo da meta de 2.000 (crédito esgotado).
- **Lote 4 (18/11/2026, scraping liberado pelo usuário):** 12 perfis de MPE ainda não coletados, 307 Reels recebidos (23 de dono diferente excluídos; 182 com 14+ dias), custo ~US$ 0,79 com teto de US$ 0,8. Base **1.843 Reels de 86 perfis na base**; 1.671 aptos → **168 no top 10% (55 perfis), 92 de consenso**; 1.139 excluídos. Para usar o saldo restante, a reserva do guardrail ficou configurável (`APIFY_RESERVA_USD`, padrão 0,50; usada 0,03). Ainda abaixo da meta de 2.000.
- **Lotes 5 e 6 (18/11/2026, nova chave Apify, autorizada pelo usuário):** nova descoberta por 8 hashtags (contabilidademei, abrirmei, dicasparamei, fluxodecaixa, marketingparapequenasempresas, vendasonline, empreendedorafeminina, gestaodenegocios; 240 Reels; US$ ~0,5), 70+45 perfis verificados pela bio e 43 curados. Lote 5: 28 perfis, 984 Reels (695 com 14+ dias); lote 6: 15 perfis, 287 Reels (192 com 14+ dias), teto de US$ 0,8. Base final **2.715 Reels de 126 perfis** (meta do TAPI atingida); top 10% = 250. Foco mantido: contabilidade/MEI, gestão financeira, precificação, vendas e bancos/fintechs para MPE.
- A mídia do top global é completada a partir do cache bruto enquanto as URLs não expiram (~1 dia).

## Fase 5 — análise do top 10% (18/11/2026)
- Base auditada: 1.672 Reels (1.504 aptos, 155 com curtidas ocultas, 13 de perfis com < 5 Reels aptos); 1.003 posts excluídos
  na triagem; 151 no top 10% (48 perfis); 80 de consenso entre `score_relativo` e `taxa_eng`; 393 vídeos em disco.
- Os 151 vídeos do top já estavam em disco (`video_ok`), então **não houve download** nem uso de cookies (`src/analise/manifesto.py`).
- Transcrição local (faster-whisper `small`, int8, CPU), cortes de cena e frames via FFmpeg, rosto via YuNet (OpenCV; o OpenCV 5 não
  traz os Haar XML). Classificação nos 5 formatos por regras léxicas (legenda + transcrição); LLM local opcional (`--ollama`).
- Limitações: parte dos Reels não tem trilha de áudio; os 5 formatos são frameworks de copy, então o rótulo é uma estimativa.
- Não implementado: `score_relativo_rolling` (não existe na base; fica para a expansão) e a Etapa 2 (expansão para 2.000+).
