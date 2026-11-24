# Relatório final

Branch: `feat/skills-e-conexao-claude`.

## Fase 1: skills (Parte A)
Ver `docs/skills-instaladas.md`. Instaladas: video-use, ffmpeg-skill, skill-creator, watch, add-zooms, video-effects, 4 do Herk Edit Kit, 6 do ElevenLabs (bloqueadas sem chave). Puladas por AGPL: OpenChatCut, OpenMontage. Clipify pulado (só macOS). Não encontrados de forma inequívoca: Visual Skills, YouTube Agent, Motion Skills, Motion Graphics. Não instalados: Remotion, Video Shotcraft, Pexo, Video Toolkit.
Nenhuma skill foi executada num vídeo de teste ainda (só auditadas e copiadas); ffmpeg 6.1.1 está presente.

## Fases 2 e 3: conexão (Partes B e C)
Ver `docs/conexao-claude.md`. Feito e testado: consentimento com escopos, revogação, chat em streaming com laço de ferramentas (cliente simulado), erro/limite/cancelamento, chave fora do front, MCP remoto read-only com Bearer (200/401/401 verificados por HTTP). 12 testes em `tests/unit/test_claude_conexao.py`.
Bug achado pelos testes e corrigido: lista de escopos vazia conectava com todos.

## Fase 4
Skill de edição atualizada com o mapa de ferramentas (A.5). Ferramentas de escrita do MCP: não feito.

## Edição por sessão do Claude Code
`src/criativos/sessao_claude.py` + opção no chat (testada com `claude` simulado).

## Riscos
- Servidor local sem login: qualquer processo local pode usar as rotas de escrita.
- Skills de terceiros copiadas: revisar `ORIGEM.txt` de cada uma antes de atualizar.
- Falhas pré-existentes em `tests/unit/test_conversa.py` (arquivo já modificado antes desta spec).

## Pendências humanas
1. `ANTHROPIC_API_KEY` no servidor e teste real do chat.
2. Deploy do MCP com HTTPS e, se quiser claude.ai, OAuth 2.1.
3. Revisão do texto de consentimento (LGPD).
4. Chaves opcionais (ElevenLabs, Gemini, Groq); `yt-dlp`; venv do `video-effects`.
5. Decisão sobre AGPL e sobre os itens sem fonte clara.
