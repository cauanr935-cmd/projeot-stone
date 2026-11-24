# Conectar Claude: descoberta, arquitetura e configuração

## B.0 Descoberta (o que o código tem hoje)
1. **Stack:** backend Python (`src/web_app.py`, `http.server`), front estático em `src/web/*.html`, MCP via FastMCP (`mcp` 1.30). Sem banco: dados em arquivos (`output/`, `workspace/`).
2. **Autenticação:** não existe. O app é local; escritas só aceitam `127.0.0.1`. Logo "usuário" = a instalação.
3. **Chat:** `estudio.html` + `/api/pedido/*` (interpretação por regras + LLM opcional) e `/api/edicao/*` (sessão do Claude Code para vídeo).
4. **Contexto útil:** projetos (`config/perfis*.yaml`), criativos (`output/criativos`, `output/pedidos`), marca (paleta, gancho, dor) e histórico do chat.
5. **Multi-tenant:** não. Isolamento entre usuários não se aplica hoje (ver riscos).
6. **URL pública HTTPS:** não há; é pendência de deploy.

## Arquitetura
- `src/claude_conexao/consentimento.py`: escopos (`read:projetos`, `read:criativos`, `read:historico`), registro do consentimento (versão do texto, data), token do MCP (só o hash fica salvo).
- `src/claude_conexao/contexto.py`: ferramentas somente leitura `search_context`, `get_item`, `list_projects`, `list_creatives`, `get_brand_guidelines`; cada uma exige o escopo aceito.
- `src/claude_conexao/chat.py`: Modo 1. API de Mensagens da Anthropic, streaming, laço de ferramentas, histórico, limite por hora, prompt que trata dados como dado.
- `src/claude_conexao/mcp_remoto.py`: Modo 2. Servidor MCP HTTP streamable com token Bearer revogável.
- Rotas: `GET /api/claude/estado`, `POST /api/claude/conectar|desconectar|chat` (SSE), `GET /api/claude/historico`. Escritas só de `127.0.0.1`.
- UI: botão **Conectar Claude** no menu do estúdio, modal de consentimento com escopos, opção "Conversar com o Claude".

## Configuração
| Variável | Padrão | Efeito |
|----------|--------|--------|
| `ANTHROPIC_API_KEY` | (vazio) | Chave da plataforma, só no servidor. Sem ela o chat avisa e nada quebra |
| `CLAUDE_CHAT_MODEL` | `claude-sonnet-5-5` | Modelo do chat |
| `CLAUDE_BILLING_MODE` | `platform` | A plataforma paga (única modalidade implementada) |
| `CLAUDE_CHAT_LIMITE_HORA` | `60` | Mensagens por hora |
| `MCP_PUBLIC_URL` | `http://127.0.0.1:8765` | URL pública do MCP |

## Usar no meu Claude (Parte C)
1. Clique em **Conectar Claude**, aceite; o token aparece uma única vez.
2. Suba o MCP: `python -m src.claude_conexao.mcp_remoto --host 0.0.0.0 --port 8765` atrás de HTTPS.
3. Claude Code: `claude mcp add --transport http impulso-plataforma https://SEU-HOST/mcp --header "Authorization: Bearer <token>"`.
4. Desconectar na plataforma invalida o token na próxima chamada (testado: 401).

## Limitações conhecidas (honestas)
- **OAuth 2.1/PKCE com registro dinâmico de clientes NÃO foi implementado.** Há token Bearer. Conectores personalizados do claude.ai exigem OAuth; por enquanto o caminho suportado é o Claude Code com `--header`.
- Sem contas de usuário: não há isolamento multiusuário; o teste de "dois usuários" não se aplica.
- Ferramentas de escrita (`MCP_WRITE_TOOLS`) não foram implementadas.
- Não foi testado contra a API real da Anthropic (sem chave); o chat foi testado com cliente simulado.
