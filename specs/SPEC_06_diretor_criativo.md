# SPEC_06 — Seletor interativo dos 5 formatos e Diretor Criativo (`edit_plan.json`)

**Objetivo:** inspecionar a pasta de conteúdos brutos, **perguntar
explicitamente** qual dos 5 formatos da pesquisa o usuário quer e gerar um
plano de edição determinístico e completo (`edit_plan.json`) que a SPEC_07
renderiza sem decisões adicionais.

**Depende de:** SPEC_05. **Gate:** `bash scripts/gate.sh 06`.
**Referência:** pesquisa §“Adaptação Setorial” (tabela dos 5 formatos);
`config/formats.yaml`; `config/script_templates.yaml`;
`docs/reference/CONTEXTO_IMPULSO_STONE.md` (tom de voz).

---

## 1. Menu obrigatório (texto exibido ao usuário)

```
Encontrei: 1 vídeo (24,1 s), 2 fotos, 0 áudios em <pasta>.
Qual formato de Reel você quer?
  [1] BAB (Before-After-Bridge) — 30 s — Beleza, Estética e Transformação Visual
  [2] Product Demo + PAS — 15 a 30 s — Alimentação, Confeitaria e Gastronomia
  [3] UGC Testimonial Flow — 21 a 35 s — Comércio Varejista, Moda e Artesanato
  [4] PAS (Problem-Agitate-Solution) — 20 a 30 s — Serviços Técnicos, Reparos e Logística
  [5] AIDA (Attention-Interest-Desire-Action) — 35 a 45 s — Ensino, Fitness, Pets e Serviços Locais
Sugestão: [2] (CNAE 5620-1/04)            ← quando houver CNAE ou só fotos
Digite o número (1-5):
```
Textos de nome/foco/duração vêm de `config/formats.yaml`.

## 2. Entregáveis

### 2.1 `src/director/interactive_cli.py` — CLI (contrato testado)
```
python -m src.director.interactive_cli --input-dir <dir> [--format 1-5] [--cnae <código>]
       [--out <edit_plan.json>] [--business-name <txt>] [--product <txt>] [--cta-channel WhatsApp]
       [--job-id <id>]
```
- Varre a pasta (não recursivo + 1 nível): vídeo `mp4 mov m4v webm mkv`,
  imagem `jpg jpeg png webp`, áudio `mp3 wav m4a aac ogg`; mede duração/
  resolução com ffprobe/Pillow; calcula sha256.
- Sem `--format`: imprime o menu e lê **uma linha do stdin**. Entrada
  inválida ⇒ mensagem e nova pergunta (até 3 tentativas); EOF ou 3 erros ⇒
  exit code 2 sem gerar plano.
- Com `--format N`: não pergunta (modo CI).
- Sugestão: CNAE → formato do perfil; só fotos → 2; só vídeo com fala → 3.
  A sugestão nunca substitui a pergunta.
- Escreve o plano em `--out` (padrão `workspace/jobs/<job_id>/edit_plan.json`)
  e imprime o caminho na última linha do stdout.

### 2.2 `src/director/edit_plan.py` — schema pydantic (contrato testado)
```json
{
  "schema_version": 1,
  "job_id": "…", "created_at": "ISO-8601", "commercial": true,
  "format": {"id": 2, "key": "product_demo_pas", "name": "Product Demo + PAS"},
  "cnae": {"code": "5620-1/04", "fallback": false},
  "duration": {"target": 30, "min": 15, "max": 30},
  "segments": [
    {"name": "feature_hook", "label": "…", "start": 0, "end": 5, "role": "feature_hook",
     "beat_aligned": false, "align_to": null, "script": "…", "assets": ["a1"]}
  ],
  "cut": {"style": "seamless", "pad": 0.09, "target_cuts_per_sec": 0.331, "planned_cuts": 10},
  "silence": {"noise_db": -32, "min_silence_dur": 0.4},
  "reframe": {"preset": "movie", "zoom": [1.0, 1.3], "split_screen_compare": false},
  "animation": {"mode": "parallax_2_5d", "parallax_strength": 10, "pivot": "PIVOT_CENTER_BOX", "handheld_sway": false},
  "tts": {"voice": "pt-BR-ThalitaMultilingualNeural", "rate": "+10%", "kokoro_voice": "pf_dora", "piper_model": "pt_BR-faber-medium"},
  "music": {"beat_sync": "downbeats", "ducking_db": -14, "source": "auto"},
  "subtitles": {"style": "ImpulsoKaraoke", "max_words_per_event": 4, "frame_zero_max_words": 5, "hook_overlay": "Olha essa textura"},
  "seamless_loop": false,
  "script": {"engine": "template_engine", "hook_overlay": "…", "full_text": "…", "loop_tail": null},
  "assets": [{"id": "a1", "path": "…", "kind": "video", "duration_s": 24.1, "width": 1920, "height": 1080, "sha256": "…"}],
  "output": {"width": 1080, "height": 1920, "fps": 30, "vcodec": "h264", "pix_fmt": "yuv420p", "acodec": "aac"}
}
```
- `planned_cuts = round(target_cuts_per_sec × duration.target)`.
- Todos os valores de formato **copiados de `config/formats.yaml`**.
- Validações do schema: `hook_overlay` ≤ 5 palavras; cada `script` de
  segmento com ≤ `ceil(3,5 × duração_do_segmento) + 2` palavras; segmentos
  contíguos cobrindo `[0, duration.target]`; todo segmento com ≥ 1 asset;
  se `seamless_loop`, o `script` do último segmento termina com um conector
  de `loop_connectors_allowed` e **sem** pontuação final, e `loop_tail` está
  preenchido.

### 2.3 `src/director/scripts.py`
`build_script(format_cfg, slots, router=None) -> dict` — tenta
`router.complete_text(json_mode=True)` com instruções de tom Impulso Stone
(próximo, acolhedor, simples, sem promessas exageradas) e valida contra as
regras acima; se o LLM não estiver disponível (`text=None`) ou a saída for
inválida, usa `config/script_templates.yaml` com os slots preenchidos
(`engine="template_engine"`). Com `REELS_OFFLINE=1` o resultado é 100%
determinístico.

### 2.4 Alocação de assets por segmento
Heurística determinística: vídeos com gancho (`selected_hook` da SPEC_03,
se o job já tiver sido analisado) vão para o 1º segmento; segmentos
`beat_aligned` recebem cortes de vídeo + clipes 2.5D; papéis
`after`/`discovery`/`walkthrough` priorizam fotos (2.5D/morph conforme
`animation.mode`); `cta`/`action_loop` reusam o melhor plano do sujeito.
Material insuficiente ⇒ reuso com enquadramento/zoom diferente (registrar
`reuse: true` no asset do segmento).

### 2.5 MCP
- Tool `build_edit_plan(input_dir, format_id=None, cnae_code=None, business_name=None, product=None, cta_channel="WhatsApp")`:
  sem `format_id` e com cliente que suporta **Elicitation** ⇒
  `ctx.elicit(...)` com enum dos 5 formatos; sem suporte ⇒ retorna
  `{"needs_format": true, "options": [...]}` para o modelo perguntar ao
  usuário. Nunca escolhe o formato sozinha.
- Prompts `reel_*` (SPEC_01) passam a instruir o modelo a chamar
  `build_edit_plan` e depois `assemble_and_render_reel`.

---

## 3. Métricas de Autoverificação

```bash
bash scripts/gate.sh 06
```
`tests/acceptance/test_spec06_director.py` (com `REELS_OFFLINE=1`):
1. Para cada opção 1..5 enviada via **stdin** (sem `--format`), o
   `edit_plan.json` aplica **exatamente** a divisão temporal, a voz TTS, a
   taxa de corte, o estilo de corte/PAD, a janela de duração, o modo de
   animação e a regra de Seamless Loop da tabela da pesquisa (valores
   esperados também fixados no próprio teste).
2. Entrada inválida (`9`, `abc`) seguida de `3` ⇒ plano do formato 3.
3. EOF sem resposta ⇒ exit code 2 e nenhum plano escrito.
4. `--format 2` não lê stdin.
5. Validações do schema (hook ≤ 5 palavras, palavras por segmento, todo
   segmento com asset, loop do AIDA).
