# Criativos em motion graphics para os 10 perfis prioritários

Foco atual do projeto: gerar **criativos prontos** (MP4 1080×1920, H.264/yuv420p/AAC, auditado por `tests/verify_final_reel.py`)
**sem precisar de mídia do cliente**. As animações são desenhadas em código (Pillow + ffmpeg): texto cinético, cartões, antes/depois,
contador e CTA. Voz PT-BR via Kokoro local (fallback do roteador) e trilha procedural própria, ambos sem custo e sem licença de terceiros.

## Os 10 perfis (`config/perfis_prioritarios.yaml`)
Premissa editável: 2 ocupações MEI por segmento, o que cobre os 5 formatos da pesquisa. O arquivo traz dor, solução, número de destaque,
prova social, CTA e paleta de cada perfil. Para trocar um perfil, edite o YAML; nada está duplicado no código.

| id | ocupação | CNAE | formato |
|---|---|---|---|
| cabeleireira, esteticista | Beleza | 9602-5/01, 9602-5/02 | 1 BAB |
| confeiteira, marmiteira | Alimentação | 1091-1/02, 5620-1/04 | 2 Demo + PAS |
| loja_roupas, bijuteria | Varejo/moda | 4781-4/00, 3212-4/00 | 3 UGC |
| eletricista, mecanico | Serviços técnicos | 4321-5/00, 4520-0/01 | 4 PAS |
| professor_particular, pet_banho_tosa | Ensino/locais | 8599-6/99, 9609-2/08 | 5 AIDA |

## Três formas de usar
1. **Offline (sem chave):** `python -m src.criativos.gerar --perfil all` (ou `--perfil eletricista --negocio "Eletro Seguro"`).
   Saída em `output/criativos/<perfil>_f<N>.mp4` + `.spec.json`.
2. **LangChain (Claude ou Gemini com chave sua):** `ANTHROPIC_API_KEY` ou `GOOGLE_API_KEY` no `.env`. `src/criativos/llm.py` monta
   `prompt | modelo.with_structured_output(CriativoSpec)`, revalida (hook ≤ 5 palavras, estrutura, cores da marca) e, se falhar,
   cai no template. `CRIATIVOS_LLM=auto|anthropic|gemini|none`; modelos via `CRIATIVOS_CLAUDE_MODEL` / `CRIATIVOS_GEMINI_MODEL`.
   `src.criativos.ferramentas.criar_agente()` entrega um agente LangChain com as 4 ferramentas.
3. **IA hospedada via MCP (Claude Code, Gemini CLI, Claude Desktop), sem chave no projeto:** registre o servidor
   (`config/mcp.example.json`) e peça "crie um criativo para o perfil eletricista". A própria IA chama `briefing_criativo`, escreve o
   `CriativoSpec` e chama `renderizar_criativo`. Prompt MCP: `criar_criativo_motion`. Tools: `listar_perfis_criativos`,
   `briefing_criativo`, `renderizar_criativo`, `gerar_criativo_perfil`, `gerar_criativos_lote`. Resource: `stone-criativos://perfis`.
   Para o caminho inverso (agente LangChain consumindo este MCP), use `langchain-mcp-adapters` (`MultiServerMCPClient`).

## Privacidade e licença
Ao provedor de LLM vai só o texto do perfil (YAML); nenhuma mídia. Fonte DejaVu (licença livre), trilha e animações próprias.

## Limitações conhecidas
- Visual é sempre gráfico (sem pessoas/produto reais); para Reels com a mídia do cliente use `src.main`.
- O loop contínuo do formato 5 (AIDA) não foi implementado no motion; a duração segue o texto, não o `duration` do formato (a auditoria avisa se sair da faixa).
- Os textos dos perfis são ilustrativos (negócios fictícios): revisar preços/prazos/garantias antes de publicar.
- Nomes de modelos LLM podem mudar; ajuste pelas variáveis de ambiente.

## Estúdio por voz (home `/`)
Página única estilo buscador: microfone grande, a pessoa fala o pedido e o Reel sai pronto. Abas: **Criar**, **Tutorial** (vídeo `src/web/tutorial.mp4`,
gerado por `python -m src.criativos.tutorial`), **Boas práticas** e **Galeria** (`/galeria`, os 10 perfis). O editor com mídia própria segue em `/editor`.

Fluxo: voz → `POST /api/voz/transcrever` (faster-whisper local, áudio apagado após o uso; `CRIATIVOS_WHISPER_MODEL=small|base|medium`)
→ `POST /api/pedido/interpretar` (`src/criativos/conversa.py`: regras em PT-BR + LLM LangChain se houver chave) extrai ramo, nome, oferta, preço, tom, formato e roteiro
→ se faltar algo, devolve `pergunta`, que o navegador **fala em voz alta** e já volta a ouvir (a gravação para sozinha após ~1,7 s de silêncio)
→ `pronto` ⇒ `POST /api/pedido/gerar` (grafo LangGraph com ajustes do pedido; roteiro ditado é aproveitado) → `/api/pedidos/<id>/video`.
"Pode seguir" dispensa perguntas; no máximo 2 rodadas (só o ramo é obrigatório). Saída em `output/pedidos/pedido_<id>.*`.

### MCP (Claude Desktop / Claude Code)
Novas tools: `interpretar_pedido(texto, estado)` → `gerar_criativo_pedido(briefing)` e `transcrever_audio(caminho)` (áudio no workspace).
No Claude: "Faça um Reel da minha confeitaria Doce Sonho, bolo de pote a R$ 12"; se faltar dado, a IA pergunta e chama de novo com o `estado`.

### Limitações
- Gravar exige HTTPS ou localhost; no Vercel o `/api` aponta para o backend (`vercel.json`) e a transcrição roda lá.
- A fala em voz alta usa o `speechSynthesis` do navegador (voz depende do sistema).
- Extração por regras é simples (o nome do negócio exige "chamada/se chama/nome é"); com chave Claude/Gemini fica mais flexível.
