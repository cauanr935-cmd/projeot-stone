# Base de exemplos: Claude + MCP + skills

> Gerado por `python scripts/exemplos.py` a partir de `exemplos/catalogo.yaml`. Edite o catálogo, não este arquivo.
> Como configurar tudo: [`docs/TUTORIAL_CLAUDE.md`](../docs/TUTORIAL_CLAUDE.md).

18 exemplos. Copie o **Prompt** para o Claude Code aberto nesta pasta (o MCP `impulso-stone-reels` e as skills já são carregados do projeto).

| Selo | Significado |
|---|---|
| `local` | Roda aqui, sem chave e sem rede |
| `rede` | Precisa de rede/instalação na 1ª vez |
| `chave` | Bloqueado: exige chave de API |

## Índice

| Exemplo | Nível | Selo | Usa |
|---|---|---|---|
| [Criativo pronto para um perfil (eletricista)](#ex01-criativo-perfil) | comece aqui | `local` | `listar_perfis_criativos`, `gerar_criativo_perfil` |
| [Pedido em linguagem livre (confeitaria)](#ex02-pedido-livre) | comece aqui | `local` | `interpretar_pedido`, `gerar_criativo_pedido` |
| [Pedido falado (áudio do WhatsApp)](#ex03-pedido-por-audio) | intermediário | `local` | `transcrever_audio`, `interpretar_pedido`, `gerar_criativo_pedido` |
| [O próprio Claude escreve o roteiro (sem chave de API no projeto)](#ex04-claude-escreve-o-spec) | intermediário | `local` | `briefing_criativo`, `renderizar_criativo`, `criar_criativo_motion` |
| [Galeria completa (10 perfis, 5 formatos)](#ex05-lote-10-perfis) | intermediário | `local` | `gerar_criativos_lote`, `list_formats` |
| [Reel a partir de vídeos e fotos do cliente](#ex06-reel-com-midia-do-cliente) | intermediário | `local` | `build_edit_plan`, `assemble_and_render_reel`, `reel_product_demo_pas` |
| [Reenquadrar vídeo para 9:16 e animar uma foto (parallax 2.5D)](#ex07-reenquadrar-e-animar-foto) | intermediário | `local` | `auto_reframe_vertical_9_16`, `animate_static_image_2_5d` |
| [Locução PT-BR e legenda estilo karaokê](#ex08-voz-e-legenda-karaoke) | avançado | `local` | `synthesize_voiceover_ptbr`, `generate_karaoke_ass_subs`, `get_router_status` |
| [Assistir e resumir um vídeo de referência](#ex09-analisar-referencia) | comece aqui | `local` | `/watch` |
| [Auditar e preparar o arquivo final para o Instagram](#ex10-checar-e-exportar) | comece aqui | `local` | `/ffmpeg-skill` |
| [Limpar uma gravação de pessoa falando (silêncios, gagueira, repetições)](#ex11-cortar-silencios-e-erros) | intermediário | `local` | `/herk-cut-silences`, `/herk-cut-mistakes`, `/edicao-video-reels-pessoas` |
| [Zooms de ênfase em clipe já cortado](#ex12-punch-zoom) | intermediário | `local` | `/add-zooms` |
| [Efeitos que seguem o rosto (51 efeitos)](#ex13-efeitos-no-rosto) | avançado | `rede` | `/video-effects` |
| [Motion graphics sob medida em HTML (exemplo da padaria)](#ex14-motion-hyperframes-padaria) | intermediário | `rede` | `/hyperframes`, `/hyperframes-cli`, `/hyperframes-registry`, `/media-use` |
| [Refazer um vídeo seu em HTML editável](#ex15-copiar-estilo-de-video) | avançado | `rede` | `/reverse-any-video` |
| [Novo episódio num estilo pronto (explainer)](#ex16-episodio-em-estilo) | avançado | `rede` | `/style-sampling` |
| [Perguntar à plataforma sobre projetos e criativos](#ex17-contexto-da-marca) | comece aqui | `local` | `list_projects`, `list_creatives`, `get_brand_guidelines`, `search_context`, `get_item` |
| [Voz, música, efeitos e isolamento de voz (ElevenLabs)](#ex18-elevenlabs) | avançado | `chave` | `/elevenlabs-text-to-speech`, `/elevenlabs-music`, `/elevenlabs-sound-effects`, `/elevenlabs-speech-to-text`, `/elevenlabs-voice-isolator` |

## A. Servidor MCP do projeto (criativos e Reels prontos)

<a id="ex01-criativo-perfil"></a>
### Criativo pronto para um perfil (eletricista)

**Resultado:** MP4 1080x1920 em motion graphics, sem precisar de mídia do cliente.  
**Selo:** `local`, nível: comece aqui

**Prompt:**

```text
Liste os perfis de criativo disponíveis e gere o criativo do perfil eletricista
com o nome de negócio "Eletro Seguro". Sem voz.
```

**Sem o Claude (CLI):**

```bash
python -m src.criativos.gerar --perfil eletricista --negocio "Eletro Seguro" --sem-voz
```

**Saída:** output/criativos/eletricista_f4.mp4 (+ .spec.json)

> Formato 4 (PAS). Textos dos perfis são ilustrativos; revise preço, prazo e garantia antes de publicar.

<a id="ex02-pedido-livre"></a>
### Pedido em linguagem livre (confeitaria)

**Resultado:** A IA entende o pedido, pergunta só o que faltar e gera o Reel.  
**Selo:** `local`, nível: comece aqui

**Prompt:**

```text
Sou confeiteira, minha loja se chama Doce Sonho e quero divulgar bolo de pote
por R$ 12. Faça um Reel. Se faltar algum dado, me pergunte.
```

**Saída:** output/pedidos/pedido_<id>.mp4 (+ .spec.json e .raciocinio.json)

> O nome do negócio só é extraído por regras se vier como "se chama / chamada / nome é".

<a id="ex03-pedido-por-audio"></a>
### Pedido falado (áudio do WhatsApp)

**Resultado:** Transcrição local do áudio vira briefing e depois Reel.  
**Selo:** `local`, nível: intermediário

**Prompt:**

```text
O áudio workspace/uploads/pedido.ogg é a minha descrição do negócio. Transcreva,
interprete e gere o Reel.
```

**Entrada:** um áudio de fala PT-BR dentro de workspace/ (faster-whisper local; o áudio não sai da máquina)

**Saída:** output/pedidos/pedido_<id>.mp4

<a id="ex04-claude-escreve-o-spec"></a>
### O próprio Claude escreve o roteiro (sem chave de API no projeto)

**Resultado:** Roteiro criativo e original, com a marca do perfil, renderizado e auditado.  
**Selo:** `local`, nível: intermediário

**Prompt:**

```text
Use o prompt criar_criativo_motion para o perfil cabeleireira. Leia o briefing,
escreva você mesmo o CriativoSpec (gancho de até 5 palavras, cores da marca) e
renderize com renderizar_criativo.
```

**Saída:** output/criativos/ ou output/pedidos/ (o renderizar_criativo devolve o caminho)

> É o caminho que usa a sua assinatura do Claude no lugar de ANTHROPIC_API_KEY.

<a id="ex05-lote-10-perfis"></a>
### Galeria completa (10 perfis, 5 formatos)

**Resultado:** Um criativo por perfil prioritário, para comparar os 5 formatos da pesquisa.  
**Selo:** `local`, nível: intermediário

**Prompt:**

```text
Gere o lote dos criativos para os perfis cabeleireira, confeiteira, loja_roupas,
mecanico e professor_particular, sem voz, e me diga qual formato cada um usou.
```

**Sem o Claude (CLI):**

```bash
python -m src.criativos.gerar --perfil all --sem-voz
```

**Saída:** output/criativos/<perfil>_f<N>.mp4

<a id="ex06-reel-com-midia-do-cliente"></a>
### Reel a partir de vídeos e fotos do cliente

**Resultado:** Plano de edição + render em um dos 5 formatos, auditado por ffprobe/loudness.  
**Selo:** `local`, nível: intermediário

**Prompt:**

```text
Com a pasta tests/fixtures/mixed, monte o plano de edição no formato 2
(Product Demo + PAS) para a loja "Doces da Ana", produto "bolo de cenoura",
mostre o plano e depois renderize.
```

**Entrada:** tests/fixtures/mixed (vídeo + fotos de teste)

**Sem o Claude (CLI):**

```bash
python -m src.main --input-dir tests/fixtures/mixed --format 2 --out output/meu_reel.mp4 --business-name "Doces da Ana" --product "bolo de cenoura"
```

**Saída:** output/meu_reel.mp4

> Sem voz local instalada vale o tier de teste (tom), que não é permitido em render comercial.

<a id="ex07-reenquadrar-e-animar-foto"></a>
### Reenquadrar vídeo para 9:16 e animar uma foto (parallax 2.5D)

**Resultado:** Dois ativos prontos para usar em qualquer edição.  
**Selo:** `local`, nível: intermediário

**Prompt:**

```text
Reenquadre o vídeo de exemplo para 9:16 com o preset talking_head e anime a
foto img_1.jpg por 5 segundos em parallax.
```

**Entrada:** tests/fixtures/sample_raw.mp4 e tests/fixtures/img_1.jpg (dentro de workspace/ ou copiados para lá)

**Saída:** arquivos escolhidos em output_path

<a id="ex08-voz-e-legenda-karaoke"></a>
### Locução PT-BR e legenda estilo karaokê

**Resultado:** Áudio de locução (+ SRT) e arquivo ASS com palavra destacada.  
**Selo:** `local`, nível: avançado

**Prompt:**

```text
Veja o status do roteador, depois sintetize esta locução: "Seu bolo de pote
chega fresquinho, peça pelo WhatsApp". Gere também a legenda karaokê.
```

> A cascata tenta Kokoro local e só depois serviços online. Confira get_router_status antes de assumir a voz.

## B. Edição de vídeo gravado (skills)

<a id="ex09-analisar-referencia"></a>
### Assistir e resumir um vídeo de referência

**Resultado:** Frames com timestamp e transcrição; o Claude descreve estrutura, gancho e ritmo.  
**Selo:** `local`, nível: comece aqui

**Prompt:**

```text
/watch output/criativos/eletricista_f4.mp4 — descreva o gancho, a estrutura e o CTA.
```

> Engine local (frames + transcrição). Para URL o yt-dlp está em .venv/bin. Sem GEMINI_API_KEY o vídeo não é enviado a ninguém.

<a id="ex10-checar-e-exportar"></a>
### Auditar e preparar o arquivo final para o Instagram

**Resultado:** Relatório de resolução, codec, CFR e loudness; export para Reels.  
**Selo:** `local`, nível: comece aqui

**Prompt:**

```text
Use a ffmpeg-skill para checar output/criativos/eletricista_f4.mp4 (probe, check
e loudness) e me diga se serve para Reels 1080x1920, H.264, AAC, entre -24 e -10 LUFS.
```

**Sem o Claude (CLI):**

```bash
python tests/verify_final_reel.py --video output/criativos/eletricista_f4.mp4 --format 4
```

**Saída:** relatório no terminal

<a id="ex11-cortar-silencios-e-erros"></a>
### Limpar uma gravação de pessoa falando (silêncios, gagueira, repetições)

**Resultado:** Lista de cortes aprovada por você e vídeo enxuto.  
**Selo:** `local`, nível: intermediário

**Prompt:**

```text
Edite workspace/uploads/depoimento.mp4 para Reels: corte silêncios, depois proponha
os cortes de erros para eu aprovar. Transcreva com o whisper local, não com ElevenLabs.
```

**Entrada:** gravação própria em workspace/ (a fala é a estrutura; nada é inventado)

> As skills herk citam ElevenLabs para transcrever; peça explicitamente o whisper local (faster-whisper está instalado).

<a id="ex12-punch-zoom"></a>
### Zooms de ênfase em clipe já cortado

**Resultado:** Punch-zoom nas palavras fortes e push suave nas falas importantes.  
**Selo:** `local`, nível: intermediário

**Prompt:**

```text
/add-zooms workspace/uploads/depoimento_cortado.mp4 — renderize e mostre o mapa de zooms.
```

> Usa o whisper CLI (instalado) + ffmpeg zoompan. Funciona melhor em talking-head estático.

<a id="ex13-efeitos-no-rosto"></a>
### Efeitos que seguem o rosto (51 efeitos)

**Resultado:** Efeitos tipo spotlight, widgets de vidro e pop-ups atrás da cabeça.  
**Selo:** `rede`, nível: avançado

**Prompt:**

```text
Use a skill video-effects para aplicar "spotlight" neste clipe.
```

> Precisa do venv da skill (mediapipe não está instalado). Rode antes - bash .claude/skills/video-effects/scripts/setup.sh

## C. Motion graphics sob medida (HyperFrames)

<a id="ex14-motion-hyperframes-padaria"></a>
### Motion graphics sob medida em HTML (exemplo da padaria)

**Resultado:** Vídeo 1080x1920 editável (HTML + GSAP) com a identidade da marca.  
**Selo:** `rede`, nível: intermediário

**Prompt:**

```text
Use a skill hyperframes. Abra o projeto output/prototipos/padaria_hyperframes como
referência e crie uma versão para a minha marca (cores, nome e oferta nas variáveis),
rode o check e mostre o preview antes de renderizar.
```

**Entrada:** output/prototipos/padaria_hyperframes/index.html (projeto de referência já pronto)

> O CLI roda por npx e baixa o pacote hyperframes na 1ª vez (npm). Ele envia uma nota de uso e a skill avisa antes; diga não para pular.

<a id="ex15-copiar-estilo-de-video"></a>
### Refazer um vídeo seu em HTML editável

**Resultado:** Projeto HyperFrames que reproduz o vídeo original quadro a quadro.  
**Selo:** `rede`, nível: avançado

**Prompt:**

```text
Use reverse-any-video em output/criativos/eletricista_f4.mp4 para reconstruir como
projeto editável.
```

> Só com vídeos que você tem direito de usar.

<a id="ex16-episodio-em-estilo"></a>
### Novo episódio num estilo pronto (explainer)

**Resultado:** Vídeo explicativo no estilo escolhido sobre o seu tema.  
**Selo:** `rede`, nível: avançado

**Prompt:**

```text
Use style-sampling para fazer um Finance Explainer de 45 segundos sobre "como separar
o dinheiro da empresa do dinheiro de casa" para MEI.
```

> Nunca usa rosto, voz ou logo de terceiros.

## D. Contexto da plataforma

<a id="ex17-contexto-da-marca"></a>
### Perguntar à plataforma sobre projetos e criativos

**Resultado:** Claude lê (somente leitura) marca, projetos e criativos já gerados.  
**Selo:** `local`, nível: comece aqui

**Prompt:**

```text
Pelo impulso-plataforma, liste os meus projetos e criativos e me mostre as diretrizes
de marca do projeto da confeitaria.
```

> Tools do servidor impulso-plataforma (MCP HTTP em 127.0.0.1:8765, escopos aceitos no Conectar Claude).

## E. Disponível, mas bloqueado por chave

<a id="ex18-elevenlabs"></a>
### Voz, música, efeitos e isolamento de voz (ElevenLabs)

**Resultado:** Qualidade de estúdio, mas a mídia vai para a ElevenLabs.  
**Selo:** `chave`, nível: avançado

**Prompt:**

```text
(Não execute sem decisão sua.) Gere uma trilha instrumental de 20 segundos com a skill elevenlabs-music.
```

> Exige ELEVENLABS_API_KEY (não configurada). Regra 7 do CLAUDE.md - mídia do cliente não vai para provedor que treina com entradas gratuitas. Use só com decisão consciente.
