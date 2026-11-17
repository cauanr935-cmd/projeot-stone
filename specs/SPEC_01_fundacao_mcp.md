# SPEC_01 — Fundação, governança (ADRs), mídia sintética de teste e servidor MCP base

**Objetivo:** subir o servidor FastMCP com as 3 primitivas (Resources,
Prompts, Tools), o Resource de perfis CNAE, o gerador de mídia sintética que
permite testar todo o pipeline sem arquivos externos e os ADRs iniciais.

**Depende de:** SPEC_00. **Gate:** `bash scripts/gate.sh 01`.
**Referência:** `docs/reference/ARQUITETURA_PESQUISA.md` §“Topologia do
Servidor MCP” e §“Implementação Prática / 1”.

---

## 1. Entregáveis

### 1.1 `tests/fixtures/generate_test_media.py`
CLI: `python tests/fixtures/generate_test_media.py [--out-dir tests/fixtures] [--force]`.
Usa apenas ffmpeg (lavfi: `testsrc2`, `smptebars`, `color`, `aevalsrc`/`sine`,
`anoisesrc`) + Pillow + numpy. Idempotente: se os arquivos existem e batem
com `manifest.json`, não regera (salvo `--force`). Gera:

| Arquivo | Requisitos |
|---|---|
| `sample_raw.mp4` | 1920×1080 (16:9), 20–30 s, H.264 + AAC 48 kHz. **VFR real**: `r_frame_rate != avg_frame_rate` no ffprobe (ex.: descartar frames num padrão irregular com `select` + `-fps_mode vfr`). Vídeo com ≥ 3 cenas visualmente distintas (cortes secos) e um objeto de alto contraste em movimento. Áudio de “fala sintética”: rajadas vozeadas (harmônicos de f0 140–220 Hz com modulação de amplitude ~4 Hz, RMS ≈ −18 dBFS) separadas por **≥ 4 pausas** de 0,6–1,5 s em ruído ≤ −60 dBFS. |
| `img_1.jpg` | 1200×1600 (retrato). “Foto de produto” sintética: fundo texturizado (ruído + gradiente) e objeto central nítido com rótulo de texto (“IMPULSO”) e um logotipo circular — detalhes finos para o teste de deformação. |
| `img_2.jpg` | 1600×1200 (paisagem). Mesmo objeto, deslocado/rotacionado ~8° (simula outro ângulo). |
| `img_3.jpg` | 1080×1080. Mesmo objeto, outra perspectiva (transformação projetiva leve). |
| `mixed/` | `sample_raw.mp4`, `img_1.jpg`, `img_2.jpg` (cópias) — entrada do E2E da SPEC_07. |
| `manifest.json` | sha256 de cada arquivo + `speech_segments: [[start,end],...]` (verdade-terreno das rajadas) + `silences: [[start,end],...]`. |

### 1.2 `src/resources/cnae_profiles.py`
- `normalize_cnae(code: str) -> str`: aceita `9602-5/01`, `9602501`,
  `9602-5-01` → retorna `9602-5/01`.
- `get_cnae_marketing_profile(cnae_code: str) -> str` (JSON, `ensure_ascii=False`)
  montado a partir de `config/cnae_profiles.yaml` + `config/formats.yaml`,
  com as chaves: `cnae_code`, `ocupacao`, `segment`, `format_id`,
  `framework` (nome do formato), `cut_style`, `target_cuts_per_sec`,
  `reframe_preset`, `tts_voice`, `duration`, `segments`, `seamless_loop`,
  `parallax_strength`, `fallback` (bool). Aliases (ex.: `4321-5/01`)
  resolvem para o perfil canônico. Código desconhecido ⇒ perfil de
  `default_cnae` com `fallback: true`.

### 1.3 `src/mcp_server.py` (FastMCP, `mcp>=1.12,<2`)
- Instância global `mcp = FastMCP("ImpulsoStone-Reels-Engine", instructions=...)`.
- `python -m src.mcp_server` sobe em **stdio** (função `main()`); flag
  opcional `--http` para streamable-http em `127.0.0.1:8765`.
- **Roots:** `src/core/paths.py` com
  `resolve_allowed_path(path, roots) -> Path` (resolve symlinks e `..`; fora
  dos roots ⇒ `PathOutsideRootsError`) e
  `async get_roots(ctx) -> list[Path]` (usa `ctx.session.list_roots()` quando
  o cliente suportar; senão `[REELS_WORKSPACE]`).
- **Resources** (nesta spec):

  | URI | Conteúdo |
  |---|---|
  | `stone-cnae://profiles/{cnae_code}` | perfil CNAE (template). **Atenção:** a barra de `9602-5/01` quebra o template de URI — clientes usam a forma só-dígitos `9602501`; o handler normaliza. |
  | `stone-formats://catalog` | JSON com os 5 formatos (id, key, name, focus, duration, segments, cut_style, target_cuts_per_sec, seamless_loop) |
  | `stone-media://jobs/{job_id}/analysis_summary` | conteúdo de `workspace/jobs/<job_id>/multimodal_summary.json` ou `{"status":"pending_analysis"}` |
  | `stone-quota://router/status` | nesta spec: `{"status":"router_not_initialized"}` (SPEC_02 substitui) |

  Annotations quando suportado: `audience=["assistant"]`, `priority` 1.0
  (cnae) e 0.9 (summary).
- **Prompts** (nesta spec): `gerar_reel_impulso_stone(cnae_code,
  objetivo_venda, job_id)` (texto da pesquisa, adaptado para citar URIs
  só-dígitos) e um por formato: `reel_bab`, `reel_product_demo_pas`,
  `reel_ugc_testimonial`, `reel_pas`, `reel_aida` (args: `cnae_code`,
  `objetivo_venda`, `job_id` opcional). Cada prompt descreve a divisão
  temporal do formato lida de `config/formats.yaml`, a regra de ≤ 5 palavras
  no Frame Zero e, no AIDA, a regra de Seamless Loop.
- **Tools** (nesta spec): `ping() -> {"status":"ok","version":...}` e
  `list_formats() -> list[dict]`. As tools pesadas entram nas specs 03–07.

### 1.4 ADRs iniciais
Revisar e completar `docs/adr/ADR-001` … `ADR-005` (já existem como base)
com o que foi implementado aqui (versão do `mcp` resolvida, decisão sobre
URIs só-dígitos, estratégia de Roots). Manter `docs/adr/ARCHITECTURE_DECISIONS.md`
(índice) atualizado.

---

## 2. Métricas de Autoverificação

```bash
bash scripts/gate.sh 01
```
`tests/acceptance/test_spec01_mcp.py` verifica:
1. Fixtures: `sample_raw.mp4` > 0 bytes, 1920×1080, VFR, com áudio;
   `silencedetect=noise=-32dB:d=0.4` encontra ≥ 3 silêncios;
   `img_{1..3}.jpg` com as dimensões da tabela; `mixed/` com 3 arquivos;
   `manifest.json` com `speech_segments`.
2. `get_cnae_marketing_profile` retorna JSON válido com todas as chaves para
   os 5 CNAEs canônicos (`9602-5/01`, `5620-1/04`, `4781-4/00`, `4321-5/00`,
   `8599-6/99`) com os valores exatos da pesquisa (formato, estilo de corte,
   cortes/s, preset, voz, loop); alias `4321-5/01` → formato 4; código
   inexistente → `fallback: true`.
3. Sessão MCP em memória (`mcp.shared.memory.create_connected_server_and_client_session`):
   `list_resource_templates` contém `stone-cnae://profiles/{cnae_code}`;
   `read_resource("stone-cnae://profiles/9602501")` devolve o perfil BAB;
   `list_resources` contém `stone-formats://catalog`; `list_prompts` contém
   os 6 prompts; `get_prompt("reel_aida", ...)` menciona “loop”;
   `call_tool("ping")` retorna status ok.
4. `resolve_allowed_path` recusa `../` e symlink para fora do root.

## 3. Armadilhas conhecidas
- O código da pesquisa usa `@mcp.prompt("nome")` — em `mcp` 1.x o primeiro
  argumento posicional é `name`; confirme na versão instalada.
- Não leia mídia no import do módulo do servidor (o `list_tools` precisa ser
  instantâneo).
