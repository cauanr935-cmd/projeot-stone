# Progresso do build (mantido pelos agentes)

Status: `TODO` → `IN_PROGRESS` → `DONE` (ou `BLOCKED` — só por ambiente, ver CLAUDE.md §2).
O script `scripts/run_autonomous.sh` lê a coluna Status para pular specs concluídas.

| Spec | Título | Status | Início | Fim | Gate (exit) | Verificador | Tiers usados / observações |
|---|---|---|---|---|---|---|---|
| SPEC_00 | Bootstrap e doctor | DONE | 2026-11-07 | 2026-11-07 | 0 | PASS | Python 3.12.3; FFmpeg/ffprobe com libx264/libass |
| SPEC_01 | Fundação, fixtures, MCP base | DONE | 2026-11-07 | 2026-11-07 | 0 | PASS | Fixtures sintéticas; MCP 1.30.0 |
| SPEC_02 | ZeroCostCascadeRouter | DONE | 2026-11-07 | 2026-11-07 | 0 | PASS | Edge TTS online; fallback placeholder em offline; templates |
| SPEC_03 | Visão, CFR, reframe, hooks | DONE | 2026-11-07 | 2026-11-07 | 0 | PASS | FFmpeg CFR; estratégia CENTER; hooks heurísticos |
| SPEC_04 | Animação 2.5D | DONE | 2026-11-07 | 2026-11-07 | 0 | PASS | OpenCV; profundidade geométrica; morph sem pesos |
| SPEC_05 | Jump-cuts, MIR, legendas | DONE | 2026-11-07 | 2026-11-07 | 0 | PASS | Silencedetect; música procedural; envelope RMS; pysubs2 |
| SPEC_06 | Diretor criativo | DONE | 2026-11-07 | 2026-11-07 | 0 | PASS | Templates determinísticos; planos para os 5 formatos |
| SPEC_07 | Orquestrador e render | DONE | 2026-11-07 | 2026-11-07 | 0 | PASS | 5 renders aprovados; auditoria H.264/AAC/LUFS/CFR |

## Fases do case de análise (coleta e padrões)

| Fase | Entrega | Status | Resultado |
|---|---|---|---|
| 1 | Coleta integrada em `src/coleta` (Instagram, YouTube, mídia) | DONE | Apify, só Reels (YouTube adiado) |
| 2 / 2b | Coleta por perfil e descoberta por hashtag | DONE | Lotes 1 a 3, ~US$ 8 de crédito gratuito |
| 3 | Base unificada (Parquet + DuckDB), exclusões com motivo | DONE | 1.843 Reels de 86 perfis na base (lote 4); 1.139 posts excluídos |
| 4 | Ranking por `score_relativo` e `taxa_eng` | DONE | 1.671 aptos; 168 no top 10% (55 perfis); 92 de consenso |
| 5 | Análise multimodal do top 10% (`src/analise`) | DONE | 168/168 transcritos, com frames e features; classificados nos 5 formatos (`docs/ANALISE_TOP10.md`) |
| 5b | TTS local Kokoro no roteador (ADR-010) | DONE | edge-tts desligado por padrão |
| Expansão | Base para 2.000+ Reels | PARCIAL | Lote 4 (12 perfis, +171 Reels, US$ ~0,79) usou o crédito restante; faltam ~157 Reels. H-CASE-03: token Graph API/cookies ou renovação do Apify em 17/12/2026 |

## Log
<!-- Uma entrada por ciclo: data/hora, spec, o que foi feito, comandos e exit codes, próximos passos. -->
- 2026-11-07 — Implementação completa; `bash scripts/gate.sh all` passou (53 testes, exit 0); MCP stdio iniciou e encerrou limpo com EOF.
- 2026-11-18 — Fase 5: manifesto (151/151 íntegros), faster-whisper small int8, cortes/frames/rosto (YuNet), classificação por regras, TTS Kokoro (ADR-010), ADR-009 corrigido, dossiê H-CASE-01. Expansão da base adiada por decisão do usuário.
- 2026-11-18 — Lote 4 (autorizado pelo usuário): 12 perfis, 307 Reels recebidos, 182 com 14+ dias; base 1.843 Reels/86 perfis; top 10% 168; vídeos novos baixados do cache e analisados. Saldo Apify ~US$ 0,18 até 17/12.
