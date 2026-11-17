# CLAUDE.md — Protocolo de Execução Autônoma · Impulso Stone Reels MCP

Você (Claude Code e seus subagentes) vai construir, **sozinho e do zero**, o
**Impulso Stone Reels MCP**: um servidor MCP + CLI em Python que recebe uma
pasta com vídeos/fotos/áudios brutos de um microempreendedor, pergunta qual
dos **5 formatos da pesquisa** (BAB, Product Demo + PAS, UGC Testimonial, PAS,
AIDA) ele quer e entrega `output/reel_final.mp4` (1080×1920, H.264, yuv420p,
AAC) pronto para o Instagram Reels — **com custo operacional zero**.

A referência técnica completa está em `docs/reference/ARQUITETURA_PESQUISA.md`.
O contexto do case Stone está em `docs/reference/CONTEXTO_IMPULSO_STONE.md`.

---

## 1. Regras de ouro (não negociáveis)

1. **Fluxo sequencial estrito.** Implemente uma spec por vez, na ordem
   `SPEC_00 → SPEC_07` (ver `specs/00_OVERVIEW.md`). É proibido iniciar a
   próxima spec antes de `bash scripts/gate.sh NN` terminar com `exit 0`
   **e** o subagente `spec-verifier` emitir `VEREDITO: PASS`.
2. **Autonomia total — nunca pare para pedir algo a um humano.** Não pergunte
   por chaves de API, contas, downloads ou confirmações. Toda dependência
   externa tem fallback local. Se algo exigir ação humana, **registre** em
   `docs/HUMAN_DEPENDENCIES.md` (formato na seção 5) e **continue**.
3. **Ausência de chave ⇒ fallback automático, nunca erro.** Se uma variável
   do `.env` não existir, o código pula aquele tier em silêncio (log `INFO`) e
   desce a cascata até o Tier local. Nenhum teste de aceitação pode depender
   de chave de API ou de rede externa para passar.
4. **Fonte única de verdade.** Números de formato, CNAE, provedores e
   licenças vivem em `config/*.yaml`. Código lê de lá. Nada de números
   mágicos duplicados.
5. **Testes de aceitação são contrato.** `tests/acceptance/*` e
   `tests/verify_final_reel.py` foram escritos junto com as specs. Você não
   pode enfraquecê-los, marcá-los como `skip`/`xfail` nem editar valores
   esperados para “fazer passar”. Exceção única: se um teste estiver
   **comprovadamente errado** (bug no próprio teste, não na sua
   implementação), corrija o mínimo necessário e registre em
   `docs/adr/ADR-900-emendas-aos-testes.md` com: teste, problema, prova,
   correção. O `spec-verifier` audita isso.
6. **Higiene de mídia.** Todo vídeo final passa por `ffprobe`: `1080x1920`,
   `yuv420p`, `h264`, CFR (`r_frame_rate == avg_frame_rate`), áudio `aac`
   ≥ 44,1 kHz, loudness integrada entre −24 e −10 LUFS.
7. **Guardrail jurídico e de privacidade.** Nenhum ativo/motor com
   `commercial_ok: false` em `config/licenses.yaml` entra em render comercial
   (padrão). Mídia do usuário é tratada como sensível por padrão e nunca vai
   para provedor com `trains_on_free_inputs: true`.
8. **Segredos.** Nunca leia, imprima, faça commit ou envie o conteúdo de
   `.env`. Verifique apenas a *existência* de variáveis (`os.getenv(...) is
   not None`). O `.env` está no `.gitignore`.
9. **Decisões documentadas.** Ao concluir cada spec, crie/atualize o ADR
   correspondente em `docs/adr/` (trade-offs, parâmetros calibrados,
   versões resolvidas, desvios da pesquisa).
10. **Sem invenção de fatos externos.** Versões de pacotes, nomes de modelos
    e limites de free tier citados na pesquisa podem estar desatualizados.
    Quando um valor não resolver (pacote inexistente, modelo 404), use a
    alternativa mais próxima que funcione, registre o valor real no ADR e
    siga em frente.

---

## 2. Loop de trabalho por spec

```
para NN em 00..07:
  1. Leia specs/SPEC_NN_*.md inteiro + ADRs anteriores + docs/PROGRESS.md.
  2. Marque a spec como IN_PROGRESS em docs/PROGRESS.md (com data/hora).
  3. Implemente os entregáveis (código + testes unitários próprios em tests/unit/).
  4. Rode:  bash scripts/gate.sh NN
       - falhou? leia o log, corrija, rode de novo.
       - falha de AMBIENTE (binário/pacote ausente)? tente instalar sozinho
         (pip, apt-get, pacotes "static-ffmpeg", download de pesos);
         se impossível, implemente o fallback previsto na spec.
  5. Delegue ao subagente `spec-verifier` (contexto limpo, somente leitura):
       "Verifique a SPEC_NN". Ele roda o gate de novo, audita os testes e
       devolve VEREDITO: PASS | FAIL com evidências.
       - FAIL ⇒ volte ao passo 3 com os achados.
  6. Atualize o ADR da spec e docs/HUMAN_DEPENDENCIES.md (seção automática:
       python -m src.core.doctor --write-report a partir da SPEC_00).
  7. Marque DONE em docs/PROGRESS.md com: comandos rodados, exit codes,
       tiers efetivamente usados (ex.: "TTS = edge-tts" ou "TTS = piper"),
       pendências humanas novas.
  8. git add -A && git commit -m "spec-NN: <resumo>"   (nunca git push)
```

**Único caso em que você pode parar:** depois de esgotar instalação +
fallback, um gate continua impossível por motivo de ambiente (ex.: sem
Python 3.11+, sem disco). Então: marque `BLOCKED` em `docs/PROGRESS.md`,
descreva o bloqueio e o comando exato que o humano deve rodar em
`docs/HUMAN_DEPENDENCIES.md` (prioridade `BLOQUEANTE`) e encerre com um
resumo. Falta de chave de API **nunca** é bloqueio.

Limite de tentativas: após 6 ciclos de correção sem progresso na mesma
falha, mude de abordagem (outra biblioteca, outro tier) e registre no ADR.

---

## 3. Convenções de código

- Python **3.11 ou 3.12** (evite 3.13 se algum pacote de ML não tiver wheel).
  Ambiente: `uv` se disponível, senão `python -m venv .venv`.
- Dependências em `pyproject.toml` com extras:
  `core` (obrigatório), `ml` (opcional: whisperx, faster-whisper, torch,
  mediapipe, transformers, kokoro-onnx, piper-tts), `dev` (pytest,
  pytest-asyncio, respx, ruff). Instale `core`+`dev` sempre; tente `ml` e
  registre o que falhar.
- **SDK MCP:** `mcp>=1.12,<2` e `from mcp.server.fastmcp import FastMCP`.
  O `mcp` 2.x renomeou FastMCP → `MCPServer` e quebra o código da pesquisa
  (ver ADR-001). Não migre para 2.x nesta entrega.
- Layout:
  ```
  src/
    core/        config.py (carrega config/*.yaml), doctor.py, ffmpeg.py (wrappers ffprobe/ffmpeg),
                 paths.py (roots/workspace), logging.py, errors.py
    resources/   cnae_profiles.py, media_resources.py
    router/      cascade_router.py, cache.py, license_guard.py, providers/*.py
    vision/      normalizer.py, scene_detector.py, reframe_9_16.py, hook_finder.py, pipeline.py
    animation/   parallax_2_5d.py, optical_flow_morph.py, depth.py
    editing/     jumpcuts.py, beat_sync.py, subtitles_ass.py, music.py
    director/    interactive_cli.py, edit_plan.py (pydantic), scripts.py
    renderer/    reel_assembler.py
    mcp_server.py
    main.py
  tests/
    acceptance/  (CONTRATO — não enfraquecer)
    unit/        (seus testes)
    fixtures/    generate_test_media.py + mídia gerada (gitignored)
  ```
- Todo módulo de pipeline expõe **função Python** + **CLI** (`python -m
  src.<pacote>.<modulo> --help`) com os argumentos exatos da spec.
- Chamadas a ffmpeg/ffprobe sempre via `src/core/ffmpeg.py` (lista de args,
  nunca `shell=True`), com `-hide_banner -nostats`, e erros com stderr
  anexado.
- Logs estruturados (`logging`, nível por `REELS_LOG_LEVEL`). Toda decisão
  de cascata loga `modality`, `tier`, `provider`, `reason`.
- Marcadores pytest: `slow`, `network`, `gpu`. Testes de aceitação **não**
  usam `network` nem `gpu`.

### Variáveis de ambiente do projeto

| Variável | Padrão | Efeito |
|---|---|---|
| `REELS_WORKSPACE` | `./workspace` | Raiz autorizada (Roots) para jobs e entradas |
| `REELS_COMMERCIAL` | `1` | Render comercial ⇒ guardrail de licenças ativo |
| `REELS_OFFLINE` | `0` | `1` força Tier local em todas as modalidades |
| `REELS_ALLOW_PLACEHOLDER_AUDIO` | `0` | `1` libera TTS tonal de teste (só CI; nunca comercial) |
| `REELS_ALLOW_AGPL` | `0` | `1` libera Ultralytics/Essentia (decisão humana, ADR-006) |
| `REELS_ENABLE_ZEROGPU` | `0` | `1` libera B-roll generativo no HF ZeroGPU |
| `HAS_CUDA` | auto | `1` usa GPU em WhisperX/Depth |
| `PIPER_MODEL_PATH` | `models/piper/pt_BR-faber-medium.onnx` | Voz Piper |
| `REELS_LOG_LEVEL` | `INFO` | Nível de log |

Chaves de nuvem (todas opcionais): ver `.env.example`.

---

## 4. Subagentes e comandos disponíveis

- `.claude/agents/spec-implementer.md` — implementa uma spec inteira.
- `.claude/agents/spec-verifier.md` — verificação independente, somente
  leitura; único que pode declarar uma spec PASS.
- `.claude/agents/license-privacy-auditor.md` — audita licenças e fluxo de
  dados sensíveis (rodar no fim das SPEC_02, 04, 05 e 07).
- `.claude/agents/media-qa.md` — inspeção de mídia (ffprobe, loudness,
  frames) quando um gate de vídeo falhar sem causa óbvia.
- Comandos: `/autopilot`, `/implement-spec NN`, `/verify-spec NN`,
  `/human-deps`.

Use subagentes para trabalho paralelizável dentro de uma spec (ex.: escrever
testes unitários enquanto implementa), mas **a ordem entre specs é serial**.

---

## 5. Formato obrigatório de `docs/HUMAN_DEPENDENCIES.md`

O arquivo tem uma parte manual (já preenchida) e uma seção automática entre
os marcadores `<!-- AUTO:BEGIN -->` e `<!-- AUTO:END -->`, reescrita por
`python -m src.core.doctor --write-report`. Itens que você adicionar à mão
vão em “Pendências registradas pelos agentes”, uma linha por item:

```
| ID | Prioridade | Spec | O que o humano precisa fazer | Por quê / impacto se não fizer | Fallback ativo hoje | Como verificar depois |
```

Prioridades: `BLOQUEANTE` (só ambiente), `RECOMENDADO` (melhora qualidade),
`OPCIONAL` (acelera/estende), `JURÍDICO` (revisão de licença/termos).

---

## 6. Definição de pronto (projeto inteiro)

- [ ] `bash scripts/gate.sh all` termina com `exit 0` num ambiente **sem
      nenhuma chave de API**.
- [ ] `python -m src.main --input-dir tests/fixtures/mixed --format N` gera
      Reel válido para N = 1..5 e `python tests/verify_final_reel.py` aprova.
- [ ] Servidor MCP sobe via `python -m src.mcp_server` (stdio) e expõe
      Resources, Prompts e Tools listados na SPEC_01/07.
- [ ] `docs/adr/` com ADR-001…ADR-008 atualizados; `docs/PROGRESS.md` com
      todas as specs DONE; `docs/HUMAN_DEPENDENCIES.md` atualizado.
- [ ] `README_PROJETO.md` (criado na SPEC_07) explicando instalação, uso via
      CLI, uso via Claude Desktop/Claude Code (MCP) e limitações conhecidas.
- [ ] `docs/FINAL_REPORT.md` com: o que foi entregue, tiers usados no
      ambiente de build, métricas medidas por formato, desvios da pesquisa.
