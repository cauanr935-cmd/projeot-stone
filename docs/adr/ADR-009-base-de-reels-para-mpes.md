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
