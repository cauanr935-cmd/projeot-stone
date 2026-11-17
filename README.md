# Impulso Stone Reels MCP — pacote de specs para execução autônoma no Claude Code

Este pacote contém as specs e a implementação funcional do servidor MCP +
CLI que transforma vídeos e fotos brutos de um microempreendedor em um Reel
1080×1920 nos 5 formatos da pesquisa (BAB, Product Demo + PAS, UGC
Testimonial, PAS, AIDA). Consulte [`README_PROJETO.md`](README_PROJETO.md)
para instalação e uso do produto; as specs e gates de aceitação permanecem
como contratos.

## Como rodar

**Pré-requisitos:** Claude Code instalado e autenticado, Python 3.11/3.12,
git e ~10 GB livres (pesos opcionais). ffmpeg ajuda, mas os agentes
conseguem instalá-lo sozinhos.

```bash
unzip impulso-stone-reels-mcp-spec.zip && cd impulso-stone-reels-mcp
git init && git add -A && git commit -m "pacote de specs"
```

Escolha um modo:

| Modo | Comando | Quando usar |
|---|---|---|
| Interativo | `claude` → digite `/autopilot` | Você quer acompanhar e pode aprovar algum comando fora da allowlist |
| Headless seguro | `bash scripts/run_autonomous.sh` | Roda sozinho com `acceptEdits` + allowlist de `.claude/settings.json` |
| Headless total | `UNSAFE_SKIP_PERMISSIONS=1 bash scripts/run_autonomous.sh` | **Só** em container/VM descartável, sem segredos na máquina |

Para uma spec isolada: `/implement-spec 03` e `/verify-spec 03`.

## O que acontece

1. Os agentes seguem `CLAUDE.md` e implementam `specs/SPEC_00` → `SPEC_07` em
   ordem estrita.
2. Cada spec só é liberada quando `bash scripts/gate.sh NN` passa **e** o
   subagente independente `spec-verifier` (somente leitura) aprova.
3. Nenhuma chave de API é exigida: cada modalidade tem fallback local. O que
   exigir ação humana vai para `docs/HUMAN_DEPENDENCIES.md` e o trabalho
   continua.
4. Ao final: `docs/FINAL_REPORT.md`, `README_PROJETO.md` (uso do produto),
   ADRs atualizados e Reels de teste em `output/`.

## Mapa do pacote

```
CLAUDE.md                     Protocolo de execução autônoma (regras de ouro, loop, convenções)
specs/00_OVERVIEW.md          Ordem, dependências, mudanças vs. plano original, matriz de aceite
specs/SPEC_00..07_*.md        Specs com contratos de CLI/API e métricas de autoverificação
config/formats.yaml           Fonte única dos 5 formatos (segmentos, cortes/s, PAD, vozes, loop)
config/cnae_profiles.yaml     CNAE → formato
config/providers.yaml         Cascata de provedores (free tiers → local), limites, privacidade
config/licenses.yaml          Guardrail jurídico (bloqueado / review / AGPL)
config/script_templates.yaml  Roteiros PT-BR offline no tom Impulso Stone
tests/acceptance/             Testes de aceitação por spec (contrato — os agentes não podem afrouxar)
tests/verify_final_reel.py    Auditor do Reel final (ffprobe + loudness + duração + não-congelado)
scripts/gate.sh               Gate cumulativo por spec
scripts/run_autonomous.sh     Execução headless de todas as specs
.claude/agents/               spec-implementer, spec-verifier, license-privacy-auditor, media-qa
.claude/commands/             /autopilot, /implement-spec, /verify-spec, /human-deps
.claude/settings.json         Allowlist de comandos e bloqueio de leitura do .env
docs/HUMAN_DEPENDENCIES.md    Chaves opcionais, provisionamento, revisões jurídicas e de negócio
docs/adr/                     ADR-001…008 + índice + emendas aos testes (ADR-900)
docs/reference/               Pesquisa (versão só-texto + original), plano original, contexto Stone
```

## Antes de publicar qualquer Reel

Leia a seção 3 de `docs/HUMAN_DEPENDENCIES.md` (revisões jurídicas: uso
comercial do edge-tts, licença da voz Piper, LGPD de imagem de clientes,
AGPL). O código já vem com padrões conservadores, mas a decisão é humana.
