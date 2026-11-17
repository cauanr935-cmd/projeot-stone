# ADR-005 — Bloqueio de licenças não comerciais em ativos de áudio e voz

**Status:** Aceito (base da pesquisa) · **Specs:** 02, 07

## Contexto
Planos gratuitos da ElevenLabs, Epidemic Sound e a API da Freesound proíbem
uso comercial; trials da Soundstripe aplicam marca d'água. Os Reels do
Impulso Stone são material comercial (podem ser impulsionados).

## Decisão
Bloquear essas fontes no schema de render (`validate_commercial_sources`,
`config/licenses.yaml`), fail-closed para fonte desconhecida, e restringir o
sistema a motores/ativos comercialmente livres ou próprios (Kokoro, Piper,
espeak-ng, Pixabay com cache de 24 h e sem Content ID, biblioteca CC0,
trilha procedural do projeto). Anexação nativa de música no ato da
publicação (Instagram/TikTok) fica fora do render local.

## Consequências
+ Todo Reel gerado pode ser impulsionado sem risco de licença conhecido.
− edge-tts é classificado como `review` (ver ADR-006): liberado com aviso
  até revisão jurídica.

## Atualizações
- 2026-11-07 — pacote de specs: lista em `config/licenses.yaml`.
