# Estado atual da edição de criativos — Impulso Stone Reels

> Documento de **entrada para pesquisa** (deep research). Descreve, sem otimismo, como hoje geramos Reels
> (motion graphics e vídeo com cenas gravadas), com quais tecnologias, APIs e limites, e onde está a dor.
> Data do levantamento: 2026-11-24. Fonte: código do repositório (`src/`, `config/`, `.claude/skills/`).

---

## 1. Produto e restrições

- **O que é:** servidor MCP + CLI + site local em Python que recebe um pedido (texto/voz) e, opcionalmente, mídia bruta de um
  microempreendedor (MEI) e entrega um **Reel vertical** pronto para o Instagram.
- **Saída padrão:** 1080×1920, H.264, `yuv420p`, 30 fps CFR, AAC 44,1/48 kHz, loudness integrada entre −24 e −10 LUFS
  (alvo −14), duração típica 15–45 s.
- **Restrições de projeto (não negociáveis):**
  - **Custo operacional zero.** Toda dependência de nuvem é opcional; sem chave, cai em motor local.
  - **Uso comercial.** Só entram motores/ativos com `commercial_ok: true` (`config/licenses.yaml`). Sem AGPL/CC-NC por padrão.
  - **Privacidade.** Mídia do usuário é sensível: nunca vai para provedor que treina com entradas gratuitas.
  - **Público final leigo.** Interface por voz/texto simples, em português do Brasil.
- **Ambiente de build:** Linux, Python 3.12, ffmpeg 6.1.1 (CPU; sem GPU assumida), Node 24 disponível, `.venv` local.

## 2. Visão geral: três caminhos de geração

| # | Caminho | Quando é usado | Quem "edita" | Saída |
|---|---|---|---|---|
| A | **Sessão Claude Code** (`claude -p`) | Padrão do site (caixa "Deixar o Claude criar/editar o vídeo" marcada), com ou sem mídia | O próprio Claude, escrevendo código e rodando ffmpeg | `output/edicoes/<id>/` |
| B | **Motion graphics por molde** (`src/criativos/motion.py`) | Fluxo conversa → `CriativoSpec` → render, sem mídia do usuário | Código determinístico (Pillow + ffmpeg) | `output/pedidos/` |
| C | **Montador com mídia do usuário** (`src/director` + `src/renderer`) | Fluxo conversa com anexos, sem sessão Claude | Pipeline determinístico (jump-cuts, parallax, legenda ASS) | `output/pedidos/` |

Desde a última iteração, o caminho **A é o principal**: o usuário rejeitou o resultado "cru" e "de template" dos caminhos B e C
(texto parado em fundo liso, bolhas, mesmo layout em toda cena). B e C continuam no código como fallback e como biblioteca de
funções (TTS, SFX, música procedural, ASS, beat-sync).

## 3. Caminho A — Sessão Claude Code (principal)

**Arquivo:** `src/criativos/sessao_claude.py`.

### 3.1 Como funciona
1. O site (`src/web/estudio.html`) envia texto + anexos para `POST /api/edicao/iniciar`.
2. O servidor (`src/web_app.py`, `ThreadingHTTPServer`, só localhost) cria um job e chama `sessao_claude.editar`.
3. Roda **`claude -p "<prompt>" --output-format stream-json --verbose --permission-mode acceptEdits --allowedTools ...`**
   na raiz do projeto (por isso o Claude carrega `CLAUDE.md` e as skills do projeto). Sem `ANTHROPIC_API_KEY` por padrão
   (usa a sessão logada do usuário). Timeout 30 min (`REELS_CLAUDE_TIMEOUT`).
4. Os eventos `stream-json` viram a barra de progresso no site (cada `tool_use` = um passo; percentual estimado, não real).
5. Ao fim, o servidor exige `final.mp4` e devolve os arquivos da pasta. Em seguida registra o Reel na memória (seção 6).

### 3.2 Ferramentas liberadas ao Claude
`Read, Write, Edit, Glob, Grep, Skill`, `Bash(ffmpeg|ffprobe|python|.venv/bin/python|node|npx --no-install|mkdir|ls)`.
Sem rede (instrução no prompt; não há bloqueio técnico de rede além das ferramentas liberadas).

### 3.3 O que entra no prompt (montado por `montar_prompt`)
- **Tarefa** conforme o caso: (a) há vídeo gravado → usar a skill `edicao-video-reels-pessoas` (+ `herk-short-form-edit`, `add-zooms`,
  `video-effects`, `ffmpeg-skill`); (b) só fotos/áudios → animar fotos no ritmo da trilha; (c) nada → criar do zero com Python
  (PIL/numpy + ffmpeg) ou HyperFrames "só se `npx --no-install hyperframes --version` funcionar" (**hoje não funciona**: o pacote não está instalado).
- **Pedido do empreendedor** (até 4000 caracteres).
- **PLAYBOOK DA BASE** (`config/playbook_viral.yaml`): números extraídos de 636 Reels reais (ver seção 7).
- **Bloco DINAMISMO** (regras anti-"vídeo cru"): proibido texto parado em fundo liso, bolhas, mesmo layout em todas as cenas;
  ritmo pelos números da base; push-in/pull-out lentos; punch-zoom com parcimônia; texto cinético palavra a palavra com
  destaque; variedade de composição por cena; trilha com batida + SFX nos cortes + ducking de voz.
- **Memória dos Reels próprios** (melhores/piores já feitos, seção 6) e **capas de referência** (seção 6.3).
- **Regras de execução:** modo autônomo; 1080×1920/H.264/AAC/30 fps CFR; salvar `final.mp4`, `capa.jpg`, `capa_referencias.json`,
  `decupagem.md`, `legenda.txt`, `creditos_audio.md`, `resumo.md`; conferir com ffprobe e **extrair 6 quadros** para checar que as
  cenas são diferentes e há movimento.

### 3.4 Skills disponíveis ao Claude (`.claude/skills/`, instaladas e auditadas — ver `docs/skills-instaladas.md`)
- **Com gravação de pessoas:** `edicao-video-reels-pessoas` (própria, 10 etapas: briefing → ingestão → decupagem USAR/TALVEZ/DESCARTAR →
  roteiro de corte → corte/ritmo → áudio da fala → legendas → SFX → música → capa → exportação/verificação), `herk-cut-silences`,
  `herk-cut-mistakes`, `herk-short-form-edit`, `herk-edit-video`, `add-zooms` (punch-zoom e Ken Burns via `zoompan`), `video-effects`
  (51 efeitos que seguem o rosto; exige venv com mediapipe/opencv), `video-use`, `ffmpeg-skill`, `watch`.
- **Motion graphics:** `hyperframes`, `hyperframes-cli`, `hyperframes-registry` (~450 blocos), `media-use`, `remotion-to-hyperframes`,
  `reverse-any-video`, `style-sampling`, `slideshow`, `figma`.
- **Áudio via ElevenLabs** (TTS, música, SFX, isolamento de voz, STT): instaladas mas **bloqueadas para uso** — exigem chave e enviam mídia a terceiro.
- Pulados por licença AGPL/plataforma: OpenChatCut, OpenMontage, Clipify.

### 3.5 Limitações conhecidas do caminho A
- **Não determinístico:** a qualidade varia por execução; o mesmo pedido pode render vídeos bem diferentes.
- **Lento e caro em tempo:** minutos a dezenas de minutos por vídeo; progresso apenas aproximado.
- **HyperFrames não roda** (pacote npm ausente) → o "from scratch" cai em Pillow/numpy → ffmpeg, o que tende ao visual de molde.
- Sem rede, o Claude não consegue baixar fontes, ícones, imagens/B-roll de banco nem música; depende do que já está em disco.
- Autoavaliação limitada: o Claude olha 6 quadros e o ffprobe; não há critério objetivo de "ficou bom" no loop (a nota da seção 6.1 é só *a posteriori*).
- O Claude escolhe sozinho decisões criativas que a skill diz para perguntar ao usuário (modo autônomo).

## 4. Caminho B — Motion graphics por molde (código determinístico)

**Arquivos:** `src/criativos/{conversa,spec,grafo,llm,motion}.py`, `src/editing/{sfx,music}.py`, `src/router/`.

### 4.1 Pipeline
`pedido (voz/texto) → interpretar (regras + LLM opcional) → briefing → grafo LangGraph → CriativoSpec (pydantic) → render`.

- **`conversa.py`**: extrai ramo (perfil/CNAE), nome, preço, oferta, formato (1–5), tom, canal de CTA e roteiro pronto. Primeiro por
  regras/regex em PT-BR; LLM só complementa. Pergunta apenas o que falta.
- **`grafo.py` (LangGraph)**: nós `perfil → formato → referências → padrões → roteiro → validar → render` com laço de revalidação.
  Cada nó escreve um "trace" mostrado ao usuário ("por que cada cena foi escolhida").
- **`llm.py` (LangChain)**: gera o `CriativoSpec`. Seleção `CRIATIVOS_LLM`: `auto|anthropic|gemini|none`. Modelos: Claude
  (`claude-sonnet-5-5`, configurável) se houver `ANTHROPIC_API_KEY`; Gemini (`gemini-2.5-flash`) se houver chave; senão **template
  determinístico** (`config/script_templates.yaml`). `REELS_OFFLINE=1` força offline. Só o material do perfil vai ao LLM, nunca mídia.
- **`CriativoSpec`**: paleta (fundo1/fundo2/destaque/acento/texto), `hook_overlay` (≤5 palavras), 3–7 cenas dos tipos
  `hook | pontos | antes_depois | numero | cta`, cada uma com `titulo`, `itens`, `narracao`, `duracao`.

### 4.2 Renderização (`motion.py`)
- **Pillow + numpy** desenham cada quadro; os quadros RGB brutos vão por **pipe para ffmpeg** (`libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 -fps_mode cfr`, AAC 160 kbps, `+faststart`).
- **Fundo animado** (`Fundo`): gradiente que desliza + 1 de 3 estilos por perfil (listras diagonais, feixe de luz, painéis angulares) + halo + vinheta; calculado em 1/4 da resolução e ampliado.
- **Animação:** easings próprios (`out_cubic`, `out_back`), texto cinético, cartões, ícones (check/x), contador numérico, wipe antes/depois. Fade de 0,28 s entre cenas. Zona segura da UI do Reels (y 260–1480).
- **Fonte:** DejaVu Sans (do sistema). Não há fonte de marca embarcada neste caminho.
- **Duração:** cada cena ≥ duração da voz + 0,7 s; se o total ficar abaixo do mínimo do formato, as pausas são esticadas proporcionalmente.
- **Voz (TTS)** via `ZeroCostCascadeRouter` (`src/router/`), cascata por modalidade em `config/providers.yaml`:
  1. `edge-tts` (vozes neurais Microsoft `pt-BR-Francisca|Antonio|ThalitaMultilingual`; sem chave; sujeito a revisão jurídica) — orçamento de latência 3 s;
  2. Cloudflare MeloTTS (precisa de token);
  3. **Kokoro-82M ONNX local** (`models/kokoro`, Apache-2.0; vozes `pf_dora`, `pm_alex`, `pm_santa`) ou **Piper** `pt_BR-faber-medium`;
  4. `espeak-ng` (degradado); 5. tom sintético (só CI).
  Voz por cena, concatenada com `adelay` + `apad`; sem alinhamento por palavra no mix atual.
- **Trilha:** gerada proceduralmente (`_trilha_procedural`, `src/editing/music.py`) — sem licença de terceiros, mas é sintética e repetitiva.
- **SFX (`src/editing/sfx.py`):** sintetizados em numpy (whoosh, swipe, pop, tick, impact, riser, chime, erro) **ou** da biblioteca
  `assets/audio_cc0` (baixada do Openverse, só CC0, com checagem de licença e de qualidade `_reprova`). Eventos gerados por cena (`eventos_do_criativo`).
- **Mix:** voz sobre trilha com ducking (−14 dB sob a voz; cama a −20 dB), loudness alvo −14 LUFS.

### 4.3 Limitações
- Visual **reconhecível como template**: 5 tipos de cena, 3 estilos de fundo, paleta única por perfil, fonte padrão do sistema.
- Sem imagens, ícones ricos, mascotes, ilustrações, fotos de banco ou B-roll (tudo é tipografia + formas).
- Texto aparece por cena, **não sincronizado por palavra com a fala** (a voz do edge-tts tem timestamps, mas o mix não usa).
- Render CPU em Python puro por quadro: ~1 min por vídeo de 30 s.

## 5. Caminho C e módulos para vídeo gravado (pipeline determinístico)

**Arquivos:** `src/director/` (plano de edição), `src/vision/`, `src/animation/`, `src/editing/`, `src/renderer/reel_assembler.py`,
`config/formats.yaml` (fonte única dos 5 formatos), `config/cnae_profiles.yaml`.

### 5.1 Os 5 formatos (da pesquisa)
BAB (Before-After-Bridge, beleza), Product Demo + PAS (alimentação), UGC Testimonial (varejo/moda), PAS, AIDA. Cada um define em
`formats.yaml`: duração alvo/mín/máx, **segmentos temporais com papel** (ex.: antes 0–8 s, depois 8–20 s, ponte, CTA), estilo de corte
(`seamless`), `target_cuts_per_sec` (0,331–0,517, de Dost & Huang 2026), parâmetros de silêncio (−32 dB, 0,4 s), preset de reenquadramento,
modo de animação de fotos, voz TTS e regra de sincronia com a batida.

### 5.2 Etapas
1. **Normalização** (`vision/normalizer.py`): CFR 30 fps, yuv420p.
2. **Análise** (`vision/pipeline.py`): detecção de cenas (**PySceneDetect**), **hook finder** (melhor janela de ~3,2 s por energia/movimento).
3. **Reenquadramento 9:16** (`vision/reframe_9_16.py`): presets `talking_head` / `movie` com zoom 1,0–1,85×; rosto por **MediaPipe/OpenCV (YuNet)**.
4. **Jump-cuts** (`editing/jumpcuts.py`): remove silêncio via `silencedetect` com pads calibrados (seamless ≈ 0,09 s; overlapping ≈ 0,015 s) e microfade de 15 ms; punch-in 1,0↔1,08 alternado a cada corte; "pattern interrupts" para atingir `target_cuts_per_sec`.
5. **Animação de fotos** (`animation/`): parallax 2.5D com mapa de profundidade (**Depth-Anything-V2-small**, Apache-2.0; base/large são CC-BY-NC e ficam bloqueados) ou **morph por optical flow** (OpenCV) entre fotos.
6. **Legenda** (`editing/subtitles_ass.py`): karaokê **ASS** (pysubs2), fonte Montserrat ExtraBold (fallback DejaVu), 68 pt, ≤4 palavras por evento, palavra ativa em amarelo/escala 112%, margem vertical 350; Frame Zero ≤5 palavras nos primeiros 3 s.
7. **Áudio:** transcrição local (**faster-whisper/WhisperX**, `small` em CPU; Groq/Cloudflare Whisper se houver chave), **beat-sync** com `librosa` (`editing/beat_sync.py`: extrai batidas, escolhe trecho de maior energia, encaixa cortes ≤120 ms nas batidas), ducking da música sob a voz.
8. **Montagem** (`renderer/reel_assembler.py`): ffmpeg com `filter_complex`, auditoria final com ffprobe (resolução, pix_fmt, CFR, codec, loudness).
- **Roteiro:** `director/scripts.py` preenche slots do formato (LLM via router, ou template). Voz do roteiro por TTS (seção 4.2).

### 5.3 Limitações
- Decisão de corte é **só acústica** (silêncio) + cena; não entende conteúdo (não escolhe "a melhor frase", não reordena a fala por narrativa).
- Sem B-roll automático, sem inserção de texto/emoji/sticker por contexto, sem seleção de take por qualidade.
- Parallax em fotos pode exibir artefatos; sem depth "base/large" por licença.
- Não há capa gerada neste caminho.

## 6. Memória, barema próprio e capas (novo)

**Arquivo:** `src/criativos/memoria_reels.py`; UI na aba "Meus Reels".

### 6.1 Barema de Reels próprios
- Cada Reel do caminho A é registrado em `output/memoria/reels.json` com **nota 0–100 de aderência ao top 10% da base**
  (`src/analise/score_viral.py`: compara duração, cortes/min, atividade de fala, rosto etc. com percentis p5/p25/p75/p95 de 250 Reels de referência).
- O usuário informa **métricas reais** depois de postar (views, curtidas, comentários, salvamentos, compartilhamentos). Com métrica real,
  o ranking usa engajamento (`interações/views`) + bônus logarítmico por alcance; sem ela, vale a nota.
- Os 3 melhores e os 2 piores entram no prompt do próximo vídeo como "o que repetir / o que evitar".
- **Limitação importante:** a nota mede *semelhança com a base*, não resultado real; o aprendizado de verdade depende do usuário preencher métricas. Não há integração com a API do Instagram.

### 6.2 Base de referência
- **641 Reels** coletados (Apify/Instagram + YouTube Data API como apoio), com views, curtidas, comentários, `taxa_eng`, `score_relativo`, segmento,
  transcrição, features de áudio/corte/rosto, frames e (quando disponível) vídeo e thumb em `dados/`. Top 10% classificado em formato (BAB/Demo+PAS/UGC/PAS/AIDA).
- Página `/base` navega, filtra e mostra miniatura/vídeo.

### 6.3 Capas
- O prompt entrega 8 capas do top 10% (perfis diferentes) como arquivos; o Claude as lê, escolhe 2–3 e registra em `capa_referencias.json`
  o que aproveitou de cada. O site mostra a capa gerada ao lado das miniaturas de inspiração (ids inexistentes são descartados).
- A capa em si é feita pelo Claude com Pillow/ffmpeg; não há modelo generativo de imagem.

## 7. Know-how extraído da base (`config/playbook_viral.yaml`, 636 Reels, top 10% × controle)

- **Ritmo:** cortes/min p25/mediana/p75 = 0 / 1,39 / 7,38; plano típico 4,25 / 11,25 / 35 s; 1º corte em 2,9 / 5,3 / 11,9 s; só 16,9% cortam nos 3 s iniciais.
- **Câmera:** 19,5% dos planos com push-in, 30,6% com pull-out; punch-in mediana 0/min (raro).
- **Ganchos (frequência no top, lift vs controle):** número/valor 23,8% (1,8×); pergunta 20,6% (1,4×); urgência/novidade 10,1% (1,32×);
  **segmentação ("Se você é X…") 9,5% (2,35×, maior lift)**; promessa+método 4,2% (0,93×). Fala já nos primeiros 0,5 s em 71,1%.
- **CTA:** "siga" 23,1% (1,66×); comente 14,4% (2,07×); salve/compartilhe 10,3%; direct/WhatsApp 7,2% (0,91×); link na bio 1,0% (2,07×).
- **Legenda:** mediana 396 caracteres, 4 hashtags (p75 = 5), emoji em 57,4%, CTA na legenda em 43,4%.
- **Atenção a vieses:** a base é majoritariamente de contas de contabilidade/gestão/empreendedorismo (hashtags dominantes), com falante em câmera;
  **não representa bem** salão, confeitaria, varejo/moda nem vídeo só de produto. O playbook é **correlacional** (top 10% por engajamento relativo), não causal.

## 8. Infraestrutura comum

- **MCP:** `mcp>=1.12,<2` (`FastMCP`), `python -m src.mcp_server` (stdio); ferramentas como `renderizar_criativo`, `gerar_criativo_pedido`,
  `build_edit_plan`, `assemble_and_render_reel`, `synthesize_voiceover_ptbr`, `transcrever_audio`, `extract_multimodal_hooks`, `generate_karaoke_ass_subs`, etc.
- **Router de custo zero** (`src/router/cascade_router.py`): cascata por modalidade (ASR, TTS, LLM, VLM…), cache por hash, `license_guard`, circuit breaker de privacidade.
  Provedores opcionais com chave: Groq (Whisper, `gpt-oss`), Gemini Flash, Mistral, Cerebras, OpenRouter, Cloudflare Workers AI, NVIDIA NIM; local: Ollama, WhisperX/faster-whisper, Kokoro, Piper.
- **ffmpeg** sempre via `src/core/ffmpeg.py` (lista de args, sem `shell=True`).
- **Site:** HTML/JS puro (`src/web/estudio.html`), fala por Web Speech API (entrada e saída), upload de anexos para o workspace, polling de jobs.
- **Bibliotecas:** Pillow, numpy, OpenCV, scikit-image, librosa, soundfile, pysubs2, edge-tts, scenedetect, mediapipe, kokoro-onnx, piper-tts,
  faster-whisper, whisperx, torch/transformers (depth), LangChain/LangGraph, pydantic v2, pandas/pyarrow (base).

## 9. Onde dói hoje (hipóteses para a pesquisa)

1. **Estética:** o motion graphics ainda parece template (tipografia + gradiente). Falta linguagem visual moderna de Reels: ilustração/ícones,
   mascote, colagem, mockups de celular, stickers, transições de forma, câmera 2.5D, texto 3D, tipografia expressiva.
2. **Texto × fala:** legendas/títulos não acompanham a fala palavra a palavra no caminho B; no vídeo gravado o karaokê existe mas é simples.
3. **Escolha de conteúdo no vídeo gravado:** corte guiado por silêncio, não por narrativa; sem seleção de melhor take, sem reordenar para gancho forte, sem B-roll.
4. **Ferramenta de render de motion:** HyperFrames/Remotion não rodam no ambiente; o "from scratch" do Claude cai em Pillow.
5. **Voz:** `edge-tts` soa bom mas tem dúvida jurídica; Kokoro/Piper em pt-BR soam robóticos. ElevenLabs bloqueado por custo/privacidade.
6. **Música:** só procedural; faltam trilhas reais com licença comercial clara e sincronia com batida no caminho A.
7. **Avaliação automática:** não há métrica objetiva de qualidade *durante* a geração (só auditoria técnica e nota de aderência ao top 10%).
8. **Aprendizado:** sem integração com métricas do Instagram; o barema depende de input manual.
9. **Capa:** feita por código, sem tipografia/rosto de qualidade; sem teste A/B.

## 10. Perguntas que a deep research deveria responder

**Motion graphics (sem câmera)**
- Qual stack renderiza motion graphics de alta qualidade **em servidor Linux, sem GPU, gratuito/open-source e de uso comercial**
  (HyperFrames, Remotion — checar licença para uso comercial —, Motion Canvas, Manim, Lottie/rlottie, Skia/CanvasKit, Cairo, Blender headless, ffmpeg `filter_complex`)? Trade-offs de velocidade, qualidade, controle por um LLM.
- Como um LLM deve **especificar** o vídeo (DSL/JSON de cenas, timeline declarativa, HTML/CSS animado) para ser confiável e variado?
- Quais bibliotecas de **ícones, ilustrações, fontes, stickers, mockups** têm licença comercial e dá para empacotar offline?
- Quais padrões visuais dominam Reels de pequenos negócios brasileiros em 2025–2026 (tipografia cinética, colagem, "UI de app", memes, split, listas)? Quais têm melhor retenção?

**Vídeo com cenas gravadas**
- Melhores práticas de decupagem **por conteúdo**: usar transcrição + LLM (e/ou VLM) para escolher takes, remover repetições, reordenar o gancho,
  definir B-roll — qual pipeline open-source existe (ex.: abordagens tipo "edit by transcript")?
- Legendas animadas estilo Reels/TikTok: bibliotecas e parâmetros (palavra destacada, emoji, posição, contraste), alinhamento por palavra em pt-BR (WhisperX, MFA).
- Cortes e ritmo: evidência (estudos, dados de plataforma) sobre cortes/minuto, zoom, 1º corte, duração de plano por objetivo (venda, educação, depoimento). Como nossos números (seção 7) se comparam?
- Melhoria de áudio com ferramentas gratuitas/comerciais-ok: denoise, de-reverb, loudness, ducking (DeepFilterNet, RNNoise, Demucs, `loudnorm`).
- Reenquadramento 9:16 e rastreamento de rosto/objeto de qualidade; estabilização; correção de cor/LUT; upscale leve.

**Áudio**
- TTS pt-BR **de uso comercial, gratuito e natural**: comparar Kokoro, Piper, XTTS/F5-TTS/Chatterbox/Fish (licenças!), edge-tts (risco ToS), APIs com free tier.
- Fontes de **música e SFX** com licença comercial clara para Reels (e risco de Content ID no Instagram), e como sincronizar corte à batida.

**Capas e CTA**
- Anatomia de capas que performam no Reels/grade do perfil; geração/ajuste automático (tipografia, rosto, contraste, regra dos terços).
- Texto de gancho, legenda e hashtags: evidências de efeito de cada elemento no alcance (distinguir correlação de causalidade).

**Aprendizado contínuo**
- Como fechar o ciclo com dados reais: Instagram Graph API (insights de Reels para contas profissionais), métricas que importam (retenção, saves, shares, 3-second plays), desenho de A/B com pequenas contas, e como transformar isso em "preferências" aplicáveis a um LLM (few-shot de melhores casos, regras aprendidas).

**Restrições a respeitar nas recomendações:** custo zero de operação; licença comercial; mídia do usuário não vai para provedores que treinam com ela; roda em CPU Linux;
usuário final é leigo (um pedido por voz → um Reel pronto em poucos minutos); idioma pt-BR.

---

### Apêndice — mapa rápido de arquivos
| Assunto | Caminho |
|---|---|
| Sessão Claude (prompt, ferramentas, timeout) | `src/criativos/sessao_claude.py` |
| Memória/barema/capas | `src/criativos/memoria_reels.py` |
| Conversa → briefing | `src/criativos/conversa.py` |
| Grafo LangGraph / LLM / Spec | `src/criativos/{grafo,llm,spec}.py` |
| Render motion graphics | `src/criativos/motion.py` |
| Montador com mídia do usuário | `src/criativos/midia_propria.py`, `src/director/`, `src/renderer/reel_assembler.py` |
| Corte, legenda, beat, SFX, música | `src/editing/` |
| Visão (cenas, reframe, hook) / animação 2.5D | `src/vision/`, `src/animation/` |
| Router e provedores | `src/router/`, `config/providers.yaml` |
| Formatos, licenças, playbook | `config/formats.yaml`, `config/licenses.yaml`, `config/playbook_viral.yaml` |
| Skill de edição com pessoas | `.claude/skills/edicao-video-reels-pessoas/SKILL.md` |
| Skills instaladas (auditoria) | `docs/skills-instaladas.md` |
| Análise do top 10% | `docs/ANALISE_TOP10.md`, `docs/KNOWHOW_VIRAL.md`, `docs/base_de_dados.md` |
