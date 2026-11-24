# Decisões autônomas

| Decisão | Motivo | Como reverter |
|---------|--------|---------------|
| Skills no nível do projeto (`.claude/skills/`) | Padrão da spec | Copiar para `~/.claude/skills/` |
| Hook SessionStart do /watch não instalado | Hooks executam código a cada sessão | Copiar `hooks/` do repositório original |
| AGPL (OpenChatCut, OpenMontage) pulados | `CLAUDE.md` e ADR-006 exigem decisão humana | `REELS_ALLOW_AGPL=1` + revisão jurídica |
| ElevenLabs instalado mas sem uso | Sem chave; não gastar crédito | Preencher `.env` |
| Itens com nome genérico marcados NÃO ENCONTRADO | Regra 1: não inventar fonte | Informar o repositório correto |
| Stack da plataforma: web_app.py (http.server) + FastMCP | Seguir o que já existe | n/d |
