# Visão geral das specs — Impulso Stone Reels MCP

## Objetivo do produto

Um microempreendedor do programa Impulso Stone (doceira, cabeleireira,
eletricista, lojista de moda, professor) coloca numa pasta o que tem —
vídeos gravados no celular, fotos de produto, áudios — e recebe um Reel
vertical pronto, editado com parâmetros de retenção calibrados pela pesquisa,
**sem pagar nada** e **sem saber editar**. O mesmo motor é exposto como
**servidor MCP** (Resources, Prompts, Tools) para qualquer cliente MCP
(Claude Desktop, Claude Code, Cursor) e como **CLI**.

## Ordem e dependências

```
SPEC_00 Bootstrap e sondagem de ambiente (doctor)
   │
SPEC_01 Fundação, ADRs, mídia sintética de teste, servidor MCP base
   │
SPEC_02 ZeroCostCascadeRouter (ASR, TTS, LLM, VLM, cache, guardrail jurídico)
   │
SPEC_03 Visão: normalização CFR, cenas, reframe 9:16, hook finder
   │
SPEC_04 Animação 2.5D de fotos (deformação zero) + fluxo óptico
   │
SPEC_05 Jump-cuts calibrados (AST), beat sync/ducking, legendas karaoke .ass
   │
SPEC_06 Diretor criativo: seletor interativo dos 5 formatos → edit_plan.json
   │
SPEC_07 Orquestrador end-to-end, render final, tools MCP completas, relatório final
```

A ordem é **serial**. Cada gate é cumulativo (roda os testes das specs
anteriores para pegar regressões).

## Mudanças em relação ao plano original (`docs/reference/PLANO_ORIGINAL_SPECS.txt`)

| # | Mudança | Motivo |
|---|---|---|
| 1 | Nova **SPEC_00** (bootstrap + `doctor`) | Autonomia: o agente precisa descobrir sozinho o que o ambiente tem (ffmpeg, GPU, rede, pesos) e gerar a seção automática de `HUMAN_DEPENDENCIES.md`. |
| 2 | `config/*.yaml` como fonte única | O plano espalhava números (0.517, PAD, vozes) por várias specs; risco de divergência. |
| 3 | `mcp>=1.12,<2` fixado | O SDK `mcp` 2.x renomeou `FastMCP` → `MCPServer`; o código da pesquisa quebraria. |
| 4 | Testes de aceitação entregues prontos | Evita que o agente escreva testes fáceis demais para o próprio código. |
| 5 | Tier extra offline em TTS (espeak-ng/placeholder), LLM (templates) e música (gerador procedural) | Garante que **nenhum** gate dependa de rede ou chave. |
| 6 | YOLOv11 (Ultralytics, AGPL-3.0) desligado por padrão; MediaPipe/Haar/saliência como padrão | Risco de licença para uso comercial pela Stone (ADR-006). |
| 7 | madmom (modelos CC-BY-NC-SA) e Depth Anything V2 Base/Large (CC-BY-NC) bloqueados; librosa e DA-V2 **Small** como padrão | Mesmo motivo. |
| 8 | Teste de “sem cliques” virou métrica numérica | “Sem cliques” não era verificável como escrito. |
| 9 | Regra “≤ 5 palavras no Frame Zero” definida operacionalmente | Se a fala tiver mais de 5 palavras em 0–3 s, mostra o `hook_overlay` e o karaoke começa em 3 s. |
| 10 | Cadência 5–10 palavras/s tratada como meta suave | Fala natural em PT-BR é ~2,5–3,5 palavras/s; a legenda não pode andar mais rápido que a fala. Teto duro: 10 palavras/s. |
| 11 | Bugs da implementação de referência listados nas specs | Ex.: jump-cut descarta o trecho após o último silêncio; punch-in aplicado sobre 16:9 distorce. |

## Contratos transversais

- **Workspace/Roots:** toda leitura/escrita de mídia fica sob
  `REELS_WORKSPACE` (padrão `./workspace`) ou sob diretórios explicitamente
  passados por CLI. O servidor MCP, quando o cliente informar Roots
  (`ctx.session.list_roots()`), recusa caminhos fora deles.
- **Job dir:** cada processamento cria `workspace/jobs/<job_id>/` com
  artefatos nomeados (`normalized.mp4`, `scenes.csv`, `output_9_16.mp4`,
  `multimodal_summary.json`, `edit_plan.json`, `voiceover.mp3`,
  `subs.ass`, `reel_final.mp4`, `render_report.json`).
- **render_report.json** (SPEC_07): engines/tiers usados por modalidade,
  avisos de licença `review`, flags `degraded_*`, métricas medidas.
- **Idempotência:** rodar a mesma etapa duas vezes com as mesmas entradas
  reaproveita cache e não corrompe o job dir.

## Matriz de aceitação (resumo)

| Spec | Gate | Critérios centrais |
|---|---|---|
| 00 | `bash scripts/gate.sh 00` | `doctor --json` válido; ffmpeg+ffprobe resolvidos; `ENVIRONMENT_REPORT.md` escrito; seção AUTO do HUMAN_DEPENDENCIES preenchida |
| 01 | `bash scripts/gate.sh 01` | fixtures geradas (vídeo VFR 16:9 com pausas, 3 imagens, pasta mixed); Resource CNAE com 9 chaves para os 5 perfis; MCP lista resources/prompts/tools via sessão em memória |
| 02 | `bash scripts/gate.sh 02` | 429 → tier local em < 500 ms; .mp3+.srt reais + `cache_hit=True` na 2ª chamada; `CommercialLicenseViolationError`; dado sensível nunca vai a provedor que treina |
| 03 | `bash scripts/gate.sh 03` | `output_9_16.mp4` 1080×1920 CFR; `scenes.csv`; `multimodal_summary.json` com ≥ 1 gancho pontuado |
| 04 | `bash scripts/gate.sh 04` | `parallax_move.mp4` 1080×1920, 150±2 frames, yuv420p; SSIM ≥ 0,90 na PIVOT_CENTER_BOX; morph 1080×1920 |
| 05 | `bash scripts/gate.sh 05` | duração pós-corte < original; sem saltos de amostra nas junções; `.ass` com PlayRes 1080×1920, ≤ 4 palavras/evento, ≤ 5 palavras em 0–3 s; BPM detectado |
| 06 | `bash scripts/gate.sh 06` | stdin 1..5 → `edit_plan.json` com segmentos, voz, cortes/s, estilo de corte e loop idênticos à tabela |
| 07 | `bash scripts/gate.sh 07` | 5 Reels (1 vídeo + 2 imagens) aprovados por `tests/verify_final_reel.py`; tools MCP completas; guardrail no schema de render |
