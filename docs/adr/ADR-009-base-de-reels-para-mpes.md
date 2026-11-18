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
- Volume (776) abaixo da meta do TAPI (2.000–5.000): limitado pelo crédito gratuito (ver H-CASE-02).

## Ranking (Fase 4)
- **Principal:** `score_relativo` (taxa_eng ÷ mediana do perfil); **secundária:** `taxa_eng` do case — ambas em `ranking.parquet`.
- **Alto desempenho:** top 10% (`config/coleta.yaml › ranking.top_fracao`) **por plataforma**, entre posts aptos:
  curtidas visíveis e perfil com ≥ 5 Reels aptos (`min_reels_perfil`; com n=1 o score é 1.0 por construção).
- **Resultado (18/11/2026, após lote 3):** 1.504 aptos → 151 no top (48 perfis); 155 fora por curtidas ocultas e 13 por
  perfil com poucos Reels. Os dois rankings coincidem em 80 dos 151 posts. Scores > 20 são sinalizados
  (`score_extremo`, 70 posts), não removidos.
- **Lote 3:** 42 perfis (US$ ~3,7). Base final **1.672 Reels de 76 perfis**, abaixo da meta de 2.000 (crédito esgotado).
- A mídia do top global é completada a partir do cache bruto enquanto as URLs não expiram (~1 dia).
