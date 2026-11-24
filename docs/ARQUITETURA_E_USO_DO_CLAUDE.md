# Impulso Stone Reels: arquitetura e uso do Claude

Documento de entrega do case. Explica como a solução é montada, como o Claude é usado, como o vídeo chega até ele,
como a base de dados melhora o resultado e como funciona a conversa criativa.

## 1. A ideia em um parágrafo

Um microempreendedor fala (ou escreve) o que quer divulgar e, se tiver, anexa vídeos, fotos e áudios. A solução devolve um
Reel vertical (1080×1920, H.264, AAC) pronto para revisar e publicar, com **custo operacional zero por vídeo**: tudo roda
no computador do usuário. O Claude é o "editor": ele recebe o material, decide os cortes e monta o vídeo com ferramentas
locais. A base de 2.715 Reels de 126 perfis (coletada para o case) funciona como o "repertório" do editor.
Nada é publicado nas redes sociais; a revisão final é sempre humana.

## 2. Visão geral da arquitetura

```
 Usuário (navegador)                       Claude Desktop / Claude Code
        │                                              │
        ▼                                              ▼  (texto exportado + MCP)
┌──────────────────────────────┐          ┌──────────────────────────┐
│ Estúdio web  (src/web)       │          │ Servidor MCP             │
│ página única, local          │          │ (src/mcp_server.py)      │
└──────────────┬───────────────┘          └────────────┬─────────────┘
               ▼                                       │
┌─────────────────────────────────────────────────────┴───────────┐
│ API local  src/web_app.py → src/criativos/api.py                │
│ uploads · sessões · jobs em segundo plano · cancelamento        │
└───────┬──────────────────┬──────────────────┬───────────────────┘
        ▼                  ▼                  ▼
 Diretor criativo     Claude que edita   Motores locais
 (conversa, sem       (sessão com        ffmpeg · Whisper (transcrição)
  ferramentas)        ferramentas)       Kokoro (voz) · Pillow
        │                  │
        └───────┬──────────┘
                ▼
   Enriquecimento (base de dados + sons + fotos)
   playbook · memória de Reels · efeitos · fotos · música
                ▼
   output/edicoes/<id>/  final.mp4 · capa · legenda · decupagem · créditos
```

Peças principais:

| Peça | Onde | Papel |
|---|---|---|
| Estúdio web | `src/web/estudio.html` | Tela única: chat, anexos, microfone, sessões, carrossel |
| API local | `src/web_app.py`, `src/criativos/api.py` | Servidor HTTP da biblioteca padrão (só escuta em 127.0.0.1) |
| Diretor criativo | `src/criativos/entrevista.py` | Conversa que escreve roteiro ou plano de edição |
| Claude que edita | `src/criativos/sessao_claude.py` | Executa a edição com ferramentas |
| Sessões | `src/criativos/sessoes.py` | Guarda conversas, arquivos e versões em `output/sessoes/` |
| Servidor MCP | `src/mcp_server.py` | Expõe as funções para o Claude Desktop / Claude Code |
| Base e know-how | `src/analise/`, `config/playbook_viral.yaml` | Padrões de edição extraídos da base |

## 3. Como o Claude é usado

O projeto usa o Claude de **duas formas diferentes**, de propósito:

1. **Diretor criativo (só conversa).** Roda como `claude -p` com **todas as ferramentas desligadas**. Ele não lê nem
   escreve arquivos: só recebe a conversa e devolve a próxima pergunta, o roteiro ou o plano de edição. Fala em português
   simples, faz **uma pergunta por vez** e no máximo 4 a 5 perguntas antes de mostrar um rascunho.
2. **Claude que edita (com ferramentas).** Roda como `claude -p` em modo autônomo, com permissão apenas para o necessário:
   ler/escrever arquivos, `ffmpeg`, `ffprobe`, Python do projeto e as ferramentas de som e imagem descritas abaixo.
   Ele trabalha em uma pasta própria por vídeo e **não pode alterar a mídia original** (só trabalha em cópias).

Por que separar? Quem conversa não mexe em arquivos (segurança), e quem edita recebe um plano claro (qualidade).
O Claude é chamado pelo próprio login do usuário, sem chave de API no projeto. Cada edição é um processo que pode ser
**cancelado** a qualquer momento (o estúdio encerra o grupo de processos inteiro) e tem tempo máximo de 30 minutos.

## 4. Como o vídeo chega até o Claude

1. **Anexar.** No estúdio, o usuário anexa vídeos, fotos ou áudios (ou grava a própria voz/câmera com teleprompter).
   O navegador envia o arquivo ao servidor local, que o salva em `workspace/chat_anexos/<id>/` e confere o tipo e a
   duração com `ffprobe`. Se o usuário errar, pode **apagar** o anexo, cancelar o envio ou desfazer.
2. **Qualidade de entrada.** Para gravações de voz, o navegador mede volume e ruído antes de enviar ("lixo entra, lixo
   sai"). Áudios curtos (menos de 1 minuto) são aceitos.
3. **Transcrição local.** O Whisper (faster-whisper) transcreve a fala com **minutagem por frase e por palavra**. Isso
   serve para duas coisas: o diretor propõe cortes e abertura citando trechos reais (sem perguntar "em que minuto você
   fala X?"), e a legenda palavra a palavra fica sincronizada.
4. **Montagem do pedido.** O servidor monta um único prompt com: a tarefa (editar a gravação, usar fotos, ou criar do zero),
   os caminhos dos arquivos, o pedido do usuário, o playbook da base, as regras de dinamismo e as lições dos Reels
   anteriores (seção 5). O texto do usuário e as transcrições são tratados como **dado, nunca como instrução**.
5. **Execução em segundo plano.** O Claude trabalha em `output/edicoes/<id>/`. O estúdio mostra o progresso (cada passo
   do Claude) e o resultado: `final.mp4`, `capa.jpg`, `legenda.txt`, `decupagem.md`, `creditos_audio.md` e `resumo.md`.
6. **Ajustar sem refazer.** Na aba Sessões, "Ajustar o vídeo (continuar de onde parei)" abre a versão anterior como
   ponto de partida e o Claude aplica só a mudança pedida. Cada versão vira "Vídeo", "Vídeo v2"…

O mesmo fluxo pode ser feito pelo **Claude Desktop**: o estúdio exporta um texto pronto (contexto, plano, conversa e os
**caminhos dos arquivos já anexados**, que ficam na pasta autorizada do MCP), e o servidor MCP dá as ferramentas.

## 5. Como a base de dados enriquece o vídeo

A base (`dados/`, fora do git) reúne **2.715 Reels de 126 perfis** do Instagram (coleta de 18/11/2026, só conteúdo
público), usada apenas para análise interna. Dela saem cinco tipos de enriquecimento:

| O que | Como é feito | Onde entra |
|---|---|---|
| **Ritmo e câmera** | Análise automática de 636 Reels (top 10% × controle): cortes por minuto, duração do plano, primeiro corte, push-in/pull-out | `config/playbook_viral.yaml` → faixas p25/mediana/p75 no prompt |
| **Ganchos e CTA** | Tipos de gancho mais frequentes no top (ex.: número concreto, pergunta) com "molde" de frase; tipos de CTA | Prompt: o Claude escolhe **um** gancho e escreve no molde |
| **Legenda e hashtags** | Padrões de tamanho, hashtags e emojis da base | `src/analise/legenda_hashtags.py` gera a legenda do post |
| **Capas** | Capas da base de referência; o Claude declara em quais se inspirou | `capa_referencias.json` |
| **Memória dos próprios Reels** | Cada Reel produzido recebe uma nota de aderência ao top 10%; quando o usuário informa views/curtidas depois de postar, o desempenho real manda | Os melhores e piores entram no prompt do próximo vídeo |

Além do repertório de edição, o vídeo é "engordado" com material de apoio, sempre com a licença registrada:

- **Efeitos sonoros reais:** `src.editing.sfx_web` baixa efeitos **CC0** do OpenGameArt (respeita `robots.txt`, grava
  origem e licença ao lado de cada arquivo). Um efeito a cada 3-4 s: whoosh nos cortes, pop/tick nos textos, impacto
  no gancho.
- **Sons de meme (opcional, tom descontraído):** `src.editing.myinstants` mantém uma base local de sons de reação. São uploads
  de usuários, sem licença declarada, então a licença fica **bloqueada para render comercial automático**; na edição pelo
  Claude só entram como tempero e o resumo avisa do risco de bloqueio de áudio no Instagram.
- **Fotos de apoio:** `src.editing.imagens_web` busca fotos em Pixabay e Pexels (APIs oficiais, com chave gratuita) ou no
  Wikimedia Commons (CC0, sem chave). Foto de banco é só apoio de 1,5 a 3 s e **nunca vale como prova** (produto vendido,
  antes/depois, depoimento). Fotos do próprio empreendedor têm prioridade.
- **Música:** trilha procedural do projeto (ou trilhas CC0 em `assets/audio_cc0/`), baixa sob a voz, com redução de volume
  nas falas e fade no fim.

**Guardrails.** Todo ativo tem uma licença em `config/licenses.yaml`; render comercial recusa o que for `commercial_ok: false`.
A mídia do usuário nunca vai para serviços que treinam com ela. Chaves ausentes nunca geram erro: cada fonte tem fallback local.

## 6. A conversa criativa

A "Entrevista criativa" é o modo em que o Claude pergunta antes de criar. A ideia central: **criatividade nasce de atrito**.
Respostas genéricas geram roteiros genéricos, então o diretor pede uma cena real (pessoa, lugar, fala) e faz a pergunta
mais específica que a resposta anterior permite. Regras: uma pergunta por vez, linguagem de balcão (sem jargão), saída
fácil ("não sei" vira duas opções A/B), e nunca inventar número, resultado ou depoimento (`[CONFIRMAR: …]`).

Há **dois modos**, escolhidos no seletor da entrevista:

- **Eu vou criar um vídeo animado (conteúdo novo):** perguntas sobre cenas e situações → rascunho → uma contestação do
  próprio rascunho → versão final, com "texto para ler" (narração corrida) pronto para o teleprompter.
- **Eu vou editar um vídeo que já gravei:** o conteúdo já existe, então o diretor **só brainstorma a edição**: qual trecho
  abre nos 3 primeiros segundos, o que cortar, legenda, zooms, música, efeitos e **quais fotos usar** (ex.: confeitaria →
  brownie cortado mostrando o recheio, bandeja saindo do forno). Termina com um **Plano de edição** e o botão
  "Gerar a edição com este plano". Se um vídeo estiver anexado, esse modo é escolhido automaticamente.

A entrevista pode ser combinada com "Claude cria e edita o vídeo": o Claude edita **com base na conversa**. O usuário pode
gravar a própria voz lendo o roteiro (o vídeo é feito em cima da voz real, sem voz de IA genérica), desfazer mensagens e
cancelar uma resposta ou um vídeo em andamento.

## 7. Forma de exposição do projeto

| Porta | Para quem | Como |
|---|---|---|
| **Estúdio web local** | Empreendedor | `python -m src.web_app` → http://127.0.0.1:8000 (ou a porta de `REELS_WEB_PORT`). Cria, conversa, guarda sessões |
| **CLI** | Quem quer automatizar | `python -m src.main --input-dir <pasta> --format N` |
| **Servidor MCP** | Claude Desktop / Claude Code | Registrado em `.mcp.json`; ferramentas, prompts com nomes simples e recursos |
| **Exportar para o Claude Desktop** | Continuar uma sessão fora do estúdio | Botão na aba Sessões: texto com plano, conversa e caminhos dos arquivos |

Todas usam o mesmo núcleo, então uma melhoria vale nas quatro portas. A interface tem leitura das respostas em voz
alta e botão de acessibilidade; as opções de criação são apresentadas como cartões com uma frase de explicação.

## 8. Limites conhecidos

- O diretor **não assiste** ao vídeo: conhece nome, duração e a transcrição. O Claude que edita olha quadros e mede
  o áudio, mas **não ouve** o resultado: a revisão humana é obrigatória.
- Fotos e sons de terceiros (principalmente sons de meme) exigem atenção a direitos antes de publicar.
- A música automática é simples; uma biblioteca de trilhas livres melhora o resultado.
- Os padrões da base descrevem o que o top 10% faz, não provam causa.
- O estúdio roda localmente e foi pensado para um usuário por instalação (sem login).
