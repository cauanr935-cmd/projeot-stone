# Vídeo de 4 min: arquitetura do Impulso Stone Reels (público: devs / outros times)

Formato: roteiro + storyboard para gravar/editar por conta própria. Narração ≈ 620 palavras (≈ 150 palavras/min → 4:00).
Tela 16:9, diagramas simples (caixas e setas), um conceito por cena. Termos técnicos aparecem na tela com legenda curta.
Conferir antes de gravar: os números marcados com [CONFIRMAR] vêm de arquivos do repositório e podem ter mudado.

## Mapa do tempo

| Cena | Tempo | Tema |
|---|---|---|
| 1 | 0:00–0:25 | O problema e a promessa |
| 2 | 0:25–0:55 | Visão geral em 4 camadas |
| 3 | 0:55–1:35 | Três portas de entrada, um só núcleo |
| 4 | 1:35–2:15 | O pipeline: mídia → plano → render |
| 5 | 2:15–2:50 | Cascata de provedores: custo zero e licenças |
| 6 | 2:50–3:20 | O diretor: Claude por conversa e por ferramentas |
| 7 | 3:20–3:45 | Qualidade e sessões: o que garante o resultado |
| 8 | 3:45–4:00 | Como estender e fechamento |

---

## Cena 1 · 0:00–0:25 · O problema e a promessa
**Tela:** foto de uma bancada de confeitaria; um celular com vídeos soltos; texto "vídeos brutos → Reel pronto".
**Narração:**
"Um microempreendedor tem vídeos soltos no celular e nenhum tempo para editar. O Impulso Stone Reels recebe esse material bruto e entrega um Reel vertical, mil oitenta por mil novecentos e vinte, pronto para revisar e publicar. A regra de projeto é custo operacional zero: tudo roda local, e qualquer serviço pago é opcional."

## Cena 2 · 0:25–0:55 · Visão geral em 4 camadas
**Tela:** diagrama de 4 faixas empilhadas, acendendo uma a uma:
1. Entrada (estúdio web · CLI · MCP)
2. Núcleo (director + router)
3. Mídia (vision · animation · editing · renderer)
4. Verificação (ffprobe + verify_final_reel)
**Narração:**
"A solução é em Python e tem quatro camadas. Em cima, as entradas: um estúdio web, uma linha de comando e um servidor MCP. No meio, o núcleo: o diretor, que decide o que fazer, e o roteador, que decide com qual ferramenta fazer. Depois, os módulos de mídia: visão, animação, edição e renderização. E por fim uma camada de verificação que reprova o arquivo se ele não cumprir as regras."

## Cena 3 · 0:55–1:35 · Três portas de entrada, um só núcleo
**Tela:** três ícones (navegador, terminal, Claude Desktop) apontando para a mesma caixa "funções Python". Destaque em `src/web_app.py`, `src/main.py`, `src/mcp_server.py`.
**Narração:**
"Cada entrada é só uma casca. O estúdio web é um servidor HTTP da biblioteca padrão, com uma página única, que guarda sessões em JSON. A CLI roda o pipeline de ponta a ponta numa pasta de mídia. E o servidor MCP expõe as mesmas funções como ferramentas, prompts e recursos para o Claude Desktop ou o Claude Code. Como o núcleo é o mesmo, uma melhoria feita uma vez vale nas três portas. O servidor MCP só enxerga a pasta de trabalho configurada, o que limita o que a IA pode ler e escrever."

## Cena 4 · 1:35–2:15 · O pipeline: mídia → plano → render
**Tela:** fluxo horizontal com miniaturas: normalizar → detectar cenas → reenquadrar 9:16 → achar o gancho → plano de edição (JSON validado) → montagem → MP4.
**Narração:**
"O fluxo de mídia tem etapas pequenas e testáveis. Primeiro normaliza os arquivos. Detecta as cenas, reenquadra para vertical e procura o melhor gancho. Com isso, o diretor monta um plano de edição: um documento estruturado e validado com pydantic, que diz quais trechos entram, o ritmo dos cortes, a legenda palavra a palavra e a música. O montador lê o plano e chama o ffmpeg. Separar plano e render permite revisar a decisão antes de gastar tempo de processamento, e refazer o vídeo mudando só o plano."

## Cena 5 · 2:15–2:50 · Cascata de provedores: custo zero e licenças
**Tela:** degraus de uma escada "nuvem → serviço gratuito → local". Um carimbo "commercial_ok" em verde ou vermelho. Cadeado em "sua mídia nunca vai a quem treina com ela".
**Narração:**
"A parte que mantém o custo em zero é o roteador em cascata. Para cada capacidade, como voz, transcrição ou imagem, ele tenta o melhor provedor disponível e desce até uma opção local se faltar chave ou rede. Sem nenhuma chave de API, tudo funciona: transcrição com Whisper, voz com Kokoro, música procedural. Antes de renderizar, um guarda de licenças consulta um arquivo de configuração e bloqueia qualquer ativo que não possa ser usado comercialmente. E a mídia do usuário é tratada como sensível: não vai para provedor que treine com ela."

## Cena 6 · 2:50–3:20 · O diretor: Claude por conversa e por ferramentas
**Tela:** duas caixas lado a lado.
- Esquerda: "Diretor (só conversa)" → plano de edição ou roteiro.
- Direita: "Claude que edita (com ferramentas)" → ffmpeg, legendas, cortes.
Seta do plano para o botão "Gerar a edição com este plano".
**Narração:**
"No estúdio há dois papéis para o Claude. O diretor só conversa: faz uma pergunta por vez, e no modo de edição trabalha sobre a transcrição do vídeo gravado para propor cortes e abertura. Quando o plano fecha, outro Claude, este com ferramentas, executa a edição. Essa separação é de segurança e de qualidade: quem conversa não mexe em arquivos, e quem edita recebe um plano claro. Pelo MCP, a mesma lógica pode rodar dentro do Claude Desktop, com os vídeos na pasta autorizada."

## Cena 7 · 3:20–3:45 · Qualidade e sessões
**Tela:** checklist animado: 1080×1920 · H.264 · yuv420p · CFR · AAC ≥ 44,1 kHz · loudness entre −24 e −10 LUFS. Ao lado, uma linha do tempo de uma sessão com versões "Vídeo", "Vídeo v2".
**Narração:**
"Nada sai sem passar pela verificação: resolução, codec, taxa de quadros constante, áudio e loudness medidos com ffprobe e ffmpeg. Se reprovar, o processo falha em vez de entregar um arquivo ruim. Cada conversa e cada edição ficam salvas como sessão, com versões, e dá para continuar de onde parou, desfazer ou cancelar uma etapa em andamento."

## Cena 8 · 3:45–4:00 · Como estender e fechamento
**Tela:** pastas `config/*.yaml` e `src/<módulo>/` com um "+" ; logotipo/nome do projeto.
**Narração:**
"Para estender, quase tudo é configuração: formatos, perfis, provedores e licenças vivem em arquivos YAML, e cada módulo expõe uma função e uma CLI. Impulso Stone Reels: da gravação bruta ao Reel pronto, sem custo por vídeo."

---

## Notas de produção
- Gravar com a tela do estúdio (aba Sessões e o botão do plano) por cima da cena 6 e 7 para dar prova visual.
- Mostrar o código só por 2 s em cada arquivo citado; o foco é o diagrama.
- Legendas na tela sempre (a maioria assiste sem som).
- [CONFIRMAR] Números citados: 1080×1920, faixa de loudness e fontes (Whisper, Kokoro) vêm de `CLAUDE.md`, `config/formats.yaml` e `docs/CRIATIVOS.md`.
- Se precisar de versão de 90 s: use as cenas 1, 2, 4 e 8.
