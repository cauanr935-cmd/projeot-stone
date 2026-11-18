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
| 3 | Base unificada (Parquet + DuckDB), exclusões com motivo | DONE | 1.672 Reels de 76 perfis; 1.003 posts excluídos |
| 4 | Ranking por `score_relativo` e `taxa_eng` | DONE | 1.504 aptos; 151 no top 10% (48 perfis); 80 de consenso |
| 5 | Análise multimodal do top 10% (`src/analise`) | DONE | 151/151 transcritos, com frames e features; classificados nos 5 formatos (`docs/ANALISE_TOP10.md`) |
| 5b | TTS local Kokoro no roteador (ADR-010) | DONE | edge-tts desligado por padrão |
| Expansão | Base para 2.000+ Reels | PENDENTE (humano) | H-CASE-03: precisa de token Graph API/cookies/crédito Apify |

## Log
<!-- Uma entrada por ciclo: data/hora, spec, o que foi feito, comandos e exit codes, próximos passos. -->
- 2026-11-07 — Implementação completa; `bash scripts/gate.sh all` passou (53 testes, exit 0); MCP stdio iniciou e encerrou limpo com EOF.
- 2026-11-18 — Fase 5: manifesto (151/151 íntegros), faster-whisper small int8, cortes/frames/rosto (YuNet), classificação por regras, TTS Kokoro (ADR-010), ADR-009 corrigido, dossiê H-CASE-01. Expansão da base adiada por decisão do usuário.
