# SPEC_07 — Orquestrador end-to-end e renderizador final de Reels

**Objetivo:** integrar todos os subsistemas no comando CLI final e na tool
MCP `assemble_and_render_reel`, com validação pré-voo, guardrail jurídico no
schema e auditoria automática do vídeo entregue.

**Depende de:** SPEC_06. **Gate:** `bash scripts/gate.sh 07`.
**Referência:** pesquisa §“Edição Programática Local”, §“Checklist de
Governança”; `tests/verify_final_reel.py` (contrato do vídeo final).

---

## 1. Entregáveis

### 1.1 `src/main.py` — CLI (contrato testado)
```
python -m src.main --input-dir <dir> [--format 1-5] [--cnae <código>] [--out output/reel_final.mp4]
       [--job-id <id>] [--business-name <txt>] [--product <txt>] [--cta-channel WhatsApp]
       [--keep-source-audio]
```
Sem `--format` ⇒ usa o menu interativo da SPEC_06 (pergunta o formato).
Saída padrão: `output/reel_final.mp4`. Exit 0 só se o vídeo passar na
auditoria pós-render.

### 1.2 Fluxo (`src/renderer/reel_assembler.py`)
1. **Plano:** `edit_plan.json` (SPEC_06).
2. **Vídeos:** pipeline da SPEC_03 (CFR → cenas → 9:16 → ganchos) e
   jump-cuts da SPEC_05 com o `cut.style`/`pad` do plano.
3. **Fotos:** SPEC_04 conforme `animation.mode` (`parallax_2_5d` por foto;
   `optical_flow_morph` quando houver ≥ 2 fotos e o formato pedir).
4. **Roteiro + locução:** `script` do plano → `router.synthesize_ptbr_voiceover`
   com `tts.voice`/`tts.rate`. Se a locução passar de `duration.target − 0,5 s`,
   acelerar com `atempo` até 1,15×; se ainda passar, encurtar o roteiro pelo
   tier de texto (ou cortar a última frase não-CTA) e regenerar.
5. **Linha do tempo:** cada segmento preenchido exatamente em
   `[start, end]` com clipes dos assets atribuídos; o 1º segmento abre com o
   `selected_hook` quando houver vídeo; instantes de corte extras via
   `plan_pattern_interrupts` até `planned_cuts` (±1); segmentos
   `beat_aligned` têm cortes encaixados (`snap_to_beats`) nos
   beats/downbeats da trilha; BAB com `split_screen_compare` usa
   antes/depois lado a lado por ≥ 1 s na transição 8 s.
6. **Música:** Pixabay (se chave e endpoint válidos) → `assets/audio_cc0/` →
   `generate_procedural_music`; ducking sob a locução
   (`music.ducking_db`).
7. **Legendas:** `.ass` a partir dos *word timestamps* da locução
   (deslocados para a linha do tempo) com `hook_overlay` do plano.
8. **Áudio da fonte:** mudo por padrão (a locução conduz);
   `--keep-source-audio` mistura a −18 dB sob a locução.
9. **Pré-voo (preflight)** — falha cedo, antes do ffmpeg, com erro claro:
   schema do plano válido; todos os inputs existem e cobrem a duração;
   `.ass` carrega no pysubs2; fonte disponível (ou fallback registrado);
   diretório de saída gravável; **`validate_commercial_sources`** com as
   `license_key` de todos os motores/ativos usados (render comercial por
   padrão; `REELS_COMMERCIAL=0` desliga) — `placeholder_tone` nunca passa em
   modo comercial.
10. **Render** (um único `ffmpeg` com `filter_complex`): concat dos clipes
    1080×1920@30 → `ass=…:fontsdir=assets/fonts` → `-r 30 -fps_mode cfr`,
    `libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -movflags +faststart`;
    áudio: locução + trilha atenuada (+ fonte opcional) →
    `loudnorm=I=-14:TP=-1.5:LRA=11` → `aac 48 kHz 192k`; `-t duration.target`.
11. **Pós-render:** roda a mesma auditoria de `tests/verify_final_reel.py`
    (importar a lógica, não duplicar) e grava `render_report.json` no job
    dir:
    ```json
    {"job_id","format_id","output","duration_s","engines":{"asr","tts","llm","vlm","music","depth","subject_detection"},
     "license_keys":[…],"license_warnings":[…],"degraded":[…],"commercial":true,
     "cuts":{"planned":16,"timeline":16},"audit":{…saída do verify…},"elapsed_s":…}
    ```

### 1.3 Tools MCP completas (`src/mcp_server.py`)
`ping`, `list_formats`, `get_router_status`, `extract_multimodal_hooks`,
`auto_reframe_vertical_9_16`, `animate_static_image_2_5d`,
`synthesize_voiceover_ptbr`, `generate_karaoke_ass_subs`,
`build_edit_plan`, `assemble_and_render_reel`.

`assemble_and_render_reel(edit_plan_path: str | None = None, edit_plan: dict | None = None,
output_path: str | None = None, commercial: bool = True, audio_sources: list[str] | None = None)`:
- `audio_sources` (license keys de áudios externos fornecidos pelo
  cliente) passa pelo guardrail **antes** de qualquer processamento; fonte
  bloqueada ⇒ erro de tool contendo `CommercialLicenseViolationError`.
- Valida caminhos contra Roots; usa `ctx.report_progress` por etapa;
  pede confirmação via Elicitation antes de **sobrescrever** um arquivo
  existente quando o cliente suportar (sem suporte ⇒ grava com sufixo).

### 1.4 Integração e documentação final
- `config/mcp.example.json` → instruções em `README_PROJETO.md` para
  registrar o servidor no Claude Desktop e no Claude Code
  (`.mcp.json` do projeto com `"command": ".venv/bin/python", "args": ["-m","src.mcp_server"]`).
  Criar o `.mcp.json` real **só depois** que `python -m src.mcp_server`
  subir sem erro.
- `README_PROJETO.md`, `docs/FINAL_REPORT.md`, ADRs 001–008 finais,
  `docs/HUMAN_DEPENDENCIES.md` atualizado (rodar o doctor).

---

## 2. Métricas de Autoverificação Final

```bash
bash scripts/gate.sh 07      # e no fim: bash scripts/gate.sh all
```
`tests/acceptance/test_spec07_e2e.py`:
1. Para **cada formato 1..5**, `python -m src.main --input-dir
   tests/fixtures/mixed --format N --out output/reel_format_N.mp4` (1 vídeo
   bruto + 2 fotos) termina com exit 0 e `python tests/verify_final_reel.py
   --video output/reel_format_N.mp4 --format N` aprova:
   - `codec_name == "h264"`, `pix_fmt == "yuv420p"`, `1080×1920`, CFR;
   - áudio `aac`, `sample_rate ≥ 44100`, loudness integrada entre −24 e
     −10 LUFS;
   - duração dentro da janela do formato (`duration.min` … `duration.max +
     0,5 s`);
   - vídeo não está em branco/congelado (amostragem de frames).
2. `render_report.json` presente com `engines`, `license_keys`, `cuts`
   (`timeline` a ±1 de `planned`) e `audit.passed == true`.
3. `REELS_COMMERCIAL=1` é usado sempre que o TTS efetivo não for
   `placeholder_tone`.
4. Sessão MCP em memória: `list_tools` contém as 10 tools; chamar
   `assemble_and_render_reel` com `audio_sources=["freesound"]` retorna erro
   com `CommercialLicenseViolationError` sem renderizar nada.

Tempo: o E2E dos 5 formatos deve caber em ~15 min em CPU de 4 vCPU
(`-preset veryfast`, cache do router, reuso das análises por sha256).

## 3. Armadilhas conhecidas
- `ass` exige ffmpeg com libass (ver SPEC_00).
- `loudnorm` em uma passada pode estourar a janela de LUFS com locução muito
  curta — se falhar, use duas passadas (medir → aplicar).
- `-t` deve casar com a soma dos clipes; garanta que o último clipe cubra
  até `duration.target` para não terminar em preto.
