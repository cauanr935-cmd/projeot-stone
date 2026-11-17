# ADR-007 — Componentes adiados ou opcionais

**Status:** Aceito · **Specs:** 04, 07

## Contexto
A pesquisa cita Kinocut (87 ferramentas FFmpeg via MCP, Apache-2.0),
Remotion MCP App (player React no chat), HF ZeroGPU (I2V) e publicação
direta via Instagram Graph Audio API / TikTok Commercial Music Library.

## Decisão
- **Render v1 = FFmpeg direto** (`filter_complex` único). Kinocut e Remotion
  ficam fora da v1: adicionam dependências (Node/esbuild, servidor MCP
  extra) sem ser necessários para os critérios de aceite. Interfaces do
  assembler devem permitir plugá-los depois.
- **ZeroGPU**: não ativado; permanece opt-in futuro (`REELS_ENABLE_ZEROGPU=1`
  + `HF_TOKEN`), só B-roll atmosférico, nunca foto de produto.
- **Morph de fotos v1**: blend linear local sem modelos. O teste garante
  transição gradual e contagem de frames; DIS/ECC permanece melhoria futura.
- **Publicação/anexação de música nativa**: fora do escopo (exige contas
  Meta/TikTok for Business; o TAPI Stone também exclui publicação automática).

## Atualizações
- 2026-11-07 — implementação: FFmpeg direto, morph local determinístico;
  publicação automática continua fora do escopo.
