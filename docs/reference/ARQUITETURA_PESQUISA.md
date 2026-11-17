> **Versão só-texto** da pesquisa de referência (imagens base64 removidas para leitura por agentes).
> Original completo com imagens: `docs/reference/original/Arquitetura_MCP_Gratuita_para_Reels.md`.
> As fórmulas do Hook Rate, do score S(c_i) e de créditos da Creatomate eram imagens; a forma normativa
> do score está na SPEC_03 / ADR-004.

# **Arquitetura de Software Open-Source e Custo Zero para Geração Automatizada de Reels via MCP (Impulso Stone)**

A viabilização de uma arquitetura de software **100% gratuita (custo operacional zero)** e *open-source* para a produção automatizada de vídeos curtos verticais (Reels, TikTok e YouTube Shorts) exige a substituição de APIs comerciais de edição e geração de vídeo por uma topologia híbrida fundamentada no **Model Context Protocol (MCP)**1. Projetada para o programa **Impulso Stone** — iniciativa social gratuita do Instituto Stone Impacto voltada à inclusão produtiva e ao desenvolvimento de microempreendedores da base da pirâmide socioeconómica no Brasil4 —, esta arquitetura desacopla o raciocínio agêntico do processamento pesado de média. O sistema combina execução local determinística para tarefas intensivas de CPU e GPU (deteção de cenas via PySceneDetect, reenquadramento vertical 9:16 via YOLOv11-seg e MediaPipe, animação 2.5D de fotos estáticas via Depth Anything V2 e OpenCV DIS, e renderização via Kinocut/FFmpeg e Remotion) com um **Motor de Roteamento em Cascata (*Cascade Router*)** que agrega uma estimativa documentada de **1,94 mil milhões de tokens gratuitos mensais** (distribuídos por 50 *pools* de *free tiers* segundo o levantamento do projeto OmniRoute em junho de 2026\) e quotas recorrentes de APIs de visão, áudio (Groq Whisper, Cloudflare Workers AI) e síntese de voz (edge-tts, Kokoro-82M, Piper TTS)3.  
O desenho técnico responde diretamente às restrições financeiras e operacionais dos pequenos negócios brasileiros. Segundo dados da Receita Federal compilados pelo Sebrae (publicados em janeiro de 2026), o Brasil registou um recorde de **4,9 milhões de pequenos negócios abertos em 2025** (96% do total de 5,1 milhões de novas empresas), sendo **77% Microempreendedores Individuais (MEI)** e tendo o setor de Serviços na liderança com quase 64% dos registos (3,2 milhões), seguido pelo Comércio (1 milhão)14. Dado que **7 em cada 10 pequenos negócios online são compostos por apenas uma pessoa**16, o microempreendedor do Impulso Stone — seja doceiro, cabeleireiro, eletricista ou comerciante de vestuário17 — não dispõe de orçamento para subscrever APIs de edição em nuvem (cujos planos pagos variam entre US\$ 39 e US\$ 649 mensais)20 nem de tempo para operar editores manuais. Para garantir operação gratuita sem infrações legais ou interrupções de serviço, a arquitetura estabelece três salvaguardas estruturais:

> 1. **Restrições de Licenciamento Comercial em Free Tiers**: Planos gratuitos de serviços populares como **ElevenLabs** (10.000 créditos/mês), **Epidemic Sound API** (50 transferências de avaliação) e **Freesound API** proíbem explicitamente o uso comercial nos seus termos de serviço gratuitos22. O roteador MCP bloqueia estas rotas para ativos finais de marketing comercial, priorizando motores com licença comercial gratuita ou domínio público (edge-tts, Piper TTS CC0, Kokoro-82M, Pixabay API e anexação nativa via Instagram Audio API e TikTok Commercial Music Library)12.  
> 2. **Privacidade e Treino de Dados em APIs Gratuitas**: O *Free Tier* da **Google Gemini API** (gemini-3.8-flash, gemini-3.6-flash) utiliza os conteúdos submetidos para melhorar os produtos da Google9. A arquitetura isola vídeos ou áudios com dados sensíveis do negócio, desviando-os automaticamente para inferência local privada via **Ollama** (qwen2.5vl:latest) e **WhisperX**9.  
> 3. **Volatilidade de Quotas e Descontinuação de Serviços**: O ecossistema de *free tiers* sofreu restrições severas ao longo de 2026 — incluindo a reforma definitiva do **GitHub Models** a 30 de julho de 2026, a exclusão da Gemini API dos créditos de boas-vindas de US\$ 300 do Google Cloud a partir de março de 2026, a retirada dos modelos Llama 3.1/3.3 do plano gratuito da Groq e a redução do limite gratuito do OpenRouter para 50 requisições diárias (RPD) em contas sem compra de créditos8. O orquestrador de fallback mitiga esta instabilidade inspecionando cabeçalhos HTTP (x-ratelimit-remaining-\*, retry-after) em tempo real e comutando instantaneamente para modelos locais quantizados9.

## **Topologia do Servidor MCP: Primitivas, Fluxo de Estado e Orquestração Agêntica**

O **Model Context Protocol (MCP)** é um padrão aberto baseado em JSON-RPC 2.0 que substitui integrações ad-hoc por uma sessão com estado (*stateful session*) entre uma aplicação anfitriã (como Claude Desktop, Cursor, OpenCode ou uma interface web própria do Impulso Stone) e servidores de contexto locais ou remotos2. Um erro estrutural frequente na construção de servidores MCP é expor exclusivamente *Tools* (ferramentas executáveis), deixando dois terços do protocolo inutilizados e forçando o modelo de linguagem (LLM) a queimar chamadas de inferência e tokens de contexto para procurar dados estáticos que deveriam ter sido anexados diretamente pelo cliente1.  
Para preservar as quotas gratuitas de TPM (*Tokens Per Minute*) e RPD (*Requests Per Day*)9, a arquitetura do **Impulso Stone Reels MCP Server** divide estritamente as operações entre as três primitivas de servidor (Prompts, Resources e Tools) e as três primitivas de cliente (Roots, Sampling e Elicitation) definidas na especificação do protocolo1.  
![imagem omitida — ver original][image1]

### **Mapeamento das Primitivas do Servidor e do Cliente MCP**

A tabela abaixo especifica como cada primitiva do protocolo MCP é implementada na arquitetura para eliminar chamadas redundantes de LLM e garantir isolamento de segurança no sistema de ficheiros local1:

| Primitiva MCP | Superfície de Controlo | Função na Arquitetura Impulso Stone | Implementação Técnica e Exemplos de URIs / Schemas |
| :---- | :---- | :---- | :---- |
| **Prompts** (prompts/list, prompts/get) | **Controlada pelo Utilizador** (Comandos / ou seleção de menu na UI)1 | Empacota modelos de roteiro e estruturas de conversão validados (PAS, AIDA, BAB, UGC, Demo) parametrizados pelo segmento CNAE do MEI1. | /reel\_transformacao\_bab (argumentos: cnae, dor\_cliente, arquivos\_brutos), /reel\_oferta\_pas, /reel\_catalogo\_fotos. Suporta anexação direta de ImageContent, AudioContent (base64) e EmbeddedResources34. |
| **Resources** (resources/list, resources/read, resources/subscribe) | **Controlada pela Aplicação / Cliente** (Anexação direta ao contexto sem gastar *tool calls*)1 | Expõe dados de leitura obrigatória: transcrições com *timestamps*, listas de cenas detetadas, mapas de batidas musicais e diretrizes pedagógicas do Impulso Stone1. | stone-cnae://profiles/{cnae\_id} (priority: 1.0, audience: \["assistant"\]), stone-media://jobs/{job\_id}/transcript.json, stone-media://jobs/{job\_id}/scenes.csv, stone-quota://router/status (com subscribe: true para alertas de quota)35. |
| **Tools** (tools/list, tools/call) | **Controlada pelo Modelo (LLM)** (Invocação autónoma para computação pesada ou escrita)1 | Executa operações de escrita, transformações de ficheiros, inferência de visão computacional e renderização final de vídeo com validação prévia (*preflight*)1. | extract\_multimodal\_hooks, auto\_reframe\_vertical\_9\_16, animate\_static\_image\_2\_5d, synthesize\_voiceover\_ptbr, generate\_karaoke\_ass\_subs, render\_kinocut\_timeline, update\_remotion\_overlay3. |
| **Sampling** (sampling/createMessage) | **Iniciada pelo Servidor → Executada pelo Cliente**2 | Permite que um *worker* do servidor MCP solicite ao LLM anfitrião uma análise semântica aninhada (ex.: escolher o melhor gancho num trecho transcrito) sem que o servidor precise gerir chaves de API próprias2. | O servidor envia um pedido createMessage contendo os candidatos de corte e metadados acústicos; o cliente encaminha ao modelo ativo na sessão (ou ao roteador) e devolve o JSON estruturado2. |
| **Roots & Elicitation** | **Controlada pelo Cliente / Utilizador**2 | Define fronteiras estritas de segurança no sistema de ficheiros (Roots) e solicita confirmação humana (Elicitation) antes de publicar ou sobrescrever edições2. | file:///workspace/impulso\_stone/user\_{id}/ impede que o agente leia ou modifique ficheiros fora do diretório do projeto; Elicitation apresenta o pré-visualizador (Remotion Player View) para aprovação2. |

### **Fluxo de Sessão e Prevenção de Desperdício de Contexto**

Quando um microempreendedor anexa um vídeo bruto ou um conjunto de fotografias na interface, o cliente MCP regista os ficheiros dentro da raiz autorizada (Roots) e dispara um pipeline de pré-processamento local assíncrono (ffprobe \+ PySceneDetect \+ Silero VAD)2. Em vez de o LLM invocar repetidamente ferramentas do tipo get\_transcript\_by\_id ou get\_scene\_list — um anti-padrão identificado em análises do gateway MCP da Archestra por desperdiçar chamadas de API em dados que deveriam ser entregues diretamente1 —, o servidor emite uma notificação notifications/resources/updated35. O cliente anexa automaticamente o recurso stone-media://jobs/{job\_id}/summary.json (anotado com "audience": \["assistant"\] e "priority": 0.9) à janela de contexto antes mesmo da primeira geração de tokens do modelo35.

## **Motor de Roteamento Inteligente em Cascata (Free-Tier Aggregation & Fallback Local)**

Para operar com **custo zero absoluto** sem sofrer interrupções por limites de taxa (*rate limits*), a camada de inferência incorpora um motor de roteamento baseado na metodologia de agregação **OmniRoute**, que mapeou em junho de 2026 um orçamento recorrente estimado em **\~1,94 mil milhões de tokens gratuitos por mês** através de 50 *pools* de *free tiers* e 530 modelos (podendo atingir \~2,53 mil milhões no primeiro mês se contabilizados créditos únicos de registo em plataformas como DeepSeek ou BytePlus, embora a arquitetura Impulso Stone dependa exclusivamente de quotas **recorrentes** para sustentabilidade contínua)8.

### **Regras de Engenharia para o Panorama de Free Tiers em 2026**

A construção do roteador segundo as especificações documentadas até outubro e novembro de 2026 exige contornar limitações operacionais severas nos fornecedores de nuvem:  
A primeira regra diz respeito à **extinção e restrição de fornecedores**. O serviço **GitHub Models** foi totalmente descontinuado a **30 de julho de 2026** (encerrando o playground, catálogo de modelos, API de inferência e suporte BYOK)9. Adicionalmente, a plataforma **Chutes** encerrou o seu nível gratuito a 15 de março de 2026, a **DeepInfra** removeu os créditos gratuitos de registo (exigindo cartão/pré-pagamento) e a **Amazon Q** descontinuou novos registos gratuitos8.  
A segunda regra governa a **gestão de quotas por projeto na Google Gemini API**. Na Gemini API (verificada em outubro de 2026), os limites de RPM (*Requests Per Minute*), TPM (*Tokens Per Minute* de entrada) e RPD (*Requests Per Day*, que reiniciam diariamente à meia-noite no horário do Pacífico — PT) são aplicados **por projeto e não por chave de API**9. Criar múltiplas chaves dentro do mesmo projeto Google AI Studio não multiplica a quota31. Além disso, a partir de março de 2026, o crédito de boas-vindas de US\$ 300 do Google Cloud deixou de cobrir custos da Gemini API, e qualquer requisição que falhe com erro HTTP 400 ou 500 não gera cobrança financeira, mas **desconta da quota diária (RPD)**31.  
A terceira regra reflete as **mudanças no catálogo gratuito da Groq**. Conforme a tabela de limites da Groq de outubro de 2026, os modelos Llama 3.3 70B e Llama 3.1 8B deixaram de fazer parte do plano gratuito (passando a exclusivos *Enterprise*)32. O plano gratuito da Groq centra-se nos modelos abertos openai/gpt-oss-120b, openai/gpt-oss-20b e qwen/qwen3.8-27b (todos com 30 RPM, 1.000 RPD, 8.000 TPM e 200.000 TPD), bem como nos modelos de transcrição acústica whisper-large-v3 e whisper-large-v3-turbo (20 RPM, 2.000 RPD, **7.200 segundos de áudio por hora \[ASH\]** e **28.800 segundos de áudio por dia \[ASD\]**, equivalentes a 8 horas diárias de áudio transcrito gratuitamente, com limite de 25 MB por anexo direto)9.  
A quarta regra gere a **contabilização em Neurónios na Cloudflare Workers AI**. O plano *Workers Free* inclui **10.000 Neurónios por dia** sem custo (reiniciando às 00:00 UTC)9. O roteador monitoriza o consumo exato em neurónios por modelo: transcrever 1 minuto de áudio com @cf/openai/whisper-large-v3-turbo consome apenas **46,63 neurónios** (ou 41,14 neurónios no @cf/openai/whisper, permitindo mais de 214 minutos/dia se dedicado a áudio), enquanto a síntese de voz com @cf/myshell-ai/melotts consome **18,63 neurónios por minuto de áudio** e o modelo multimodal @cf/meta/llama-3.2-11b-vision-instruct consome 4.410 neurónios por milhão de tokens de entrada e 61.493 neurónios por milhão de tokens de saída9. Modelos de fronteira como Kimi K2.6, GLM 5.2/5.3 e DeepSeek V4 Flash exigem método de pagamento e estão excluídos da alocação diária gratuita9.  
Por fim, o roteador aplica **compressão de contexto (*RTK \+ Caveman compression*)** nas comunicações internas entre agentes, alcançando uma poupança documentada de **15% a 95% de tokens** para preservar o limite de 8.000 TPM da Groq e os 50 RPD do OpenRouter (onde tentativas falhadas também descontam do limite diário)8.  
![imagem omitida — ver original][image2]

### **Matriz de Cascata por Modalidade e Condições de Disparo (*Circuit Breaker*)**

A tabela seguinte define a cadeia de prioridade do roteador para cada uma das cinco modalidades exigidas pela produção de Reels, especificando os limites documentados em outubro e novembro de 2026 e os gatilhos de comutação8:

| Modalidade | Tier 1: Cloud Primário (Custo US\$ 0\) | Tier 2: Cloud Secundário (Custo US\$ 0\) | Tier 3: Fallback Local Open-Source (Ilimitado / Offline) | Gatilhos de Comutação (Circuit Breaker) e Regras de ToS |
| :---- | :---- | :---- | :---- | :---- |
| **1\. Visão e Análise Multimodal (Vídeo / Frames)** | **Google Gemini Free Tier** (gemini-3.8-flash, gemini-3.6-flash, gemini-3.5-flash-lite) — Contexto até 1M tokens; vídeo a 1 FPS \= 258 tokens/s; imagem \= 560 tokens9. | **NVIDIA NIM** (nvidia/nemotron-3.5-super-vl-120b-a12b, deepseek-ai/deepseek-v4.1-flash a 40 RPM) → **Cloudflare AI** (@cf/meta/llama-3.2-11b-vision-instruct ou @cf/moondream/moondream3.1-9B-A2B)8. | **Ollama Local** executando qwen2.5vl:latest (7B) com codificação explícita de tempo absoluto e fusão MRoPE (2 frames por token temporal)9. | Se o vídeo contiver dados privados do MEI (bloqueio de ToS do Gemini Free Tier, que treina nos inputs)9, ou se ocorrer HTTP 429 RESOURCE\_EXHAUSTED, comuta imediatamente para NVIDIA NIM / Ollama Qwen2.5-VL9. |
| **2\. Transcrição de Áudio (ASR / STT)** | **Groq Free Plan** (whisper-large-v3-turbo e whisper-large-v3) — 20 RPM, 2.000 RPD, **7.200 seg/hora (ASH)**, **28.800 seg/dia (ASD)**; ficheiro máx. 25 MB9. | **Cloudflare Workers AI** (@cf/openai/whisper-large-v3-turbo a 46,63 neurónios/minuto ou @cf/openai/whisper a 41,14 neurónios/minuto, até \~214 min/dia no teto de 10k neurónios)9. | **WhisperX Local (v3.8.6)** sobre backend faster-whisper (CTranslate2 INT8/FP16, \<8 GB VRAM) \+ Silero VAD \+ alinhamento fonético forçado wav2vec229. | Se x-ratelimit-remaining-requests \== 0, áudio \>25 MB (dividido via VAD local) ou ASH \> 7.000s, comuta para Cloudflare/WhisperX9. **Nota**: Mesmo usando Groq no Tier 1, o alinhamento wav2vec2 do WhisperX corre localmente para obter *timestamps* exatos ao milissegundo por palavra29. |
| **3\. Síntese de Voz Neural (TTS PT-BR)** | **Microsoft Edge TTS (edge-tts v7.3.1)** — Sem chave de API, sem cobrança; vozes neurais nativas pt-BR-FranciscaNeural, pt-BR-AntonioNeural e pt-BR-ThalitaMultilingualNeural; gera .mp3 e .srt sincronizado13. | **Cloudflare Workers AI** (@cf/myshell-ai/melotts a 18,63 neurónios/min ou @cf/deepgram/aura-1 a 1.363,64 neurónios/1k chars)9. *(ElevenLabs Free 10k chars excluído de anúncios comerciais por restrição de licença)*24. | **Kokoro-82M PT-BR** (cristianoaredes/kokoro-pt-br ONNX fp32 / MediaPipe TTS vozes pf\_dora, pm\_alex, pm\_santa) → **Piper TTS** (Trelis/piper-pt-br-faber-medium, 63 MB ONNX, licença CC0)12. | Se o endpoint online do edge-tts apresentar indisponibilidade ou latência \>3 s, comuta diretamente para Kokoro-82M local (que também devolve word\_timestamps nativos via MediaPipe) ou Piper TTS em CPU pura12. |
| **4\. Raciocínio, Roteiro e Copywriting (LLM)** | **Groq Free Plan** (openai/gpt-oss-120b e qwen/qwen3.8-27b: 30 RPM, 1.000 RPD, 8.000 TPM, 200.000 TPD) \+ **Gemini 3.8 Flash**9. | **Mistral Free Experiment** (1B tokens/mês, 2 RPM, 500K TPM) → **Cerebras** (gpt-oss-120b: 5 RPM, 30K TPM, 1M TPD) → **OpenRouter** (modelos :free, 20 RPM, 50 RPD)8. | **Ollama Local** (llama3.2, qwen2.5-coder ou gemma-4 local via http\://localhost:11434/v1) sem limites de RPM/TPD9. | Monitoriza x-ratelimit-remaining-tokens na Groq (o teto de 8K TPM é atingido antes do RPD)9. Em prompts longos (\>6.000 tokens), desvia preventivamente para Mistral (500K TPM) ou Gemini Flash (1M contexto)8. |
| **5\. Animação de Imagens e Áudio/SFX** | **Animação**: **Motor Local 2.5D (Depth Anything V2 \+ OpenCV DIS)** como padrão determinístico para produtos11. **Áudio/SFX**: **Pixabay API** (100 req/min, licença comercial gratuita, cache 24h obrigatório)28. | **Animação Generativa**: **Hugging Face Spaces ZeroGPU** via gradio\_client (Lightricks/ltx-video-distilled ou Wan 2.1/2.2, quota gratuita de **5 min \[300s\]/dia**)46. | **Animação**: Filtros matemáticos FFmpeg (zoompan \+ displace por mapa de profundidade)59. **Áudio**: Biblioteca local curada de faixas CC0 \+ extração de batidas via madmom60. | No ZeroGPU, a plataforma verifica a duração reservada @spaces.GPU(duration=N) antes da execução46. Se o saldo diário for inferior a N (erro ZeroGPU quota exceeded), o roteador bloqueia a chamada cloud e executa o pipeline 2.5D local46. |

## **Pipeline de Análise Multimodal de Vídeos Brutos e Neuromarketing Aplicado**

Quando um empreendedor do Impulso Stone envia um vídeo bruto gravado no telemóvel (por exemplo, um vídeo de 3 minutos mostrando os bastidores de uma confeitaria ou uma explicação sobre manutenção elétrica), o sistema seleciona os momentos de gancho (*hook*), clímax e ritmo de corte (*pacing*) com base em estudos empíricos de atenção visual, carga cognitiva e perceção acústica63.

### **A Ciência da Retenção: Visão Foveal, Carga Cognitiva e Calibração de Jump-Cuts**

De acordo com os resultados científicos reportados pela Alpha.One (agosto de 2026\) com base na investigação de Karen Nelson-Field sobre impressões digitais, **84% dos anúncios em vídeo digital não conseguem atingir sequer 2,5 segundos de atenção contínua**, que representa o limiar mínimo para reforçar ativos de marca e construir disponibilidade mental de longo prazo64. Em contrapartida, ultrapassar o limiar de **3 segundos de atenção foveal contínua** está associado a um **aumento de 40% na força publicitária de curto prazo (STAS / *Short-Term Advertising Strength*)**64. Adicionalmente, pesquisas comparativas da Dentsu sobre a economia da atenção indicam que o tempo de atenção ativa correlaciona-se fortemente com o aumento de vendas (r \= 0,78), enquanto a simples taxa de conclusão do vídeo (*Video Completion Rate* — VCR, que pode ocorrer em ambiente silenciado ou num ecrã não observado) apresenta uma correlação muito baixa (r \= 0,12)64.  
Para superar a *Swipe Zone* (segundos 0 a 3, onde ocorre a queda mais acentuada de retenção)66, o pipeline de visão computacional concilia duas descobertas complementares sobre atenção visual. Por um lado, a aplicação da **Teoria da Carga Cognitiva** (Sweller) ao rastreamento ocular mostra que uma elevada complexidade visual nos frames de abertura sobrecarrega a memória de trabalho e provoca um **aumento de 45% na aversão ao olhar (*gaze aversion*) nos primeiros 2 segundos**, levando à desistência precoce do espectador63. Por outro lado, análises de retenção de vídeo indicam que vídeos com **3 ou mais mudanças dinâmicas de cena nos primeiros 3 segundos** registam taxas de conclusão **58% superiores** (estudo de atenção visual da Nielsen de 2021 citado na literatura da área) e que capturar a atenção nos primeiros 3 segundos eleva a conclusão em **65%** segundo dados do Facebook67.  
A síntese arquitetural implementada no servidor MCP resolve esta tensão aplicando **"Movimento Dinâmico com Baixa Entropia Visual"**: o algoritmo seleciona para o *Frame Zero* um plano com fundo simplificado e um único ponto focal (preferencialmente um rosto humano em contacto visual direto ou o produto em ação, guiando a visão foveal sem sobrecarga periférica), aplicando um corte dinâmico ou *zoom-in* imediato acompanhado de uma sobreposição de texto concisa de **5 palavras ou menos** no gancho inicial (e mantendo uma cadência de exibição de **5 a 10 palavras por segundo** ao longo do vídeo, conforme recomendação oficial do TikTok Creative Center)64.

#### **Calibração Matemática de Jump-Cuts: Cortes Suaves (*Seamless*) vs. Sobrepostos (*Overlapping*)**

Após os primeiros 3 segundos (e especialmente após os 6 segundos, onde o *Hold Rate* cai acentuadamente em todas as plataformas)69, o vídeo entra na fase de *Pacing Slope*, na qual um vídeo estático de *talking head* sofre decaimento severo após 5 segundos se não forem introduzidas quebras de padrão (*pattern interrupts* como zooms de câmara, B-roll contextual ou gráficos) a cada **3 a 5 segundos**64. Para automatizar o ritmo exato dos cortes via FFmpeg, a arquitetura incorpora os parâmetros do estudo experimental de **Dost & Huang (2026)** (N \= 242), que calibrou via PySceneDetect a frequência real de cortes de 50 vídeos informativos de alto desempenho no TikTok (média de **0,37 cortes/s**, DP \= 0,17, intervalo de 0,13 a 0,82 cortes/s) em três referenciais operacionais65:

* **Frequência Baixa (Percentil 16\)**: **0,189 cortes/segundo** (aproximadamente 1 corte a cada 5,29 segundos)65.  
* **Frequência Média / Mediana (Percentil 50\)**: **0,331 cortes/segundo** (aproximadamente 1 corte a cada 3,02 segundos)65.  
* **Frequência Alta (Percentil 84\)**: **0,517 cortes/segundo** (aproximadamente 1 corte a cada 1,93 segundos)65.

O estudo de Dost & Huang demonstra uma **dupla rota cognitiva de engajamento** que orienta os presets de edição do servidor MCP (face ao grupo de controlo sem edição, cuja linha de base foi de 3,171 para engajamento interativo e 2,471 para engajamento sustentado numa escala de 7 pontos)65:  
Na **Rota da Fluência de Processamento para Engajamento Interativo (Likes e Reações Positivas)**, os **cortes suaves (*Seamless Cuts*)** aceleram a entrega removendo silêncios e redundâncias, mas preservam a continuidade natural, as micro-pausas e os ataques acústicos (*audio onsets*) das palavras65. Isso eleva a fluência percetual e gera afeto positivo, aumentando significativamente a probabilidade de *Likes* quando aplicados em frequência **Média (0,331 cortes/s: estimativa \= \+0,829, p \< 0,05)** ou **Alta (0,517 cortes/s: estimativa \= \+0,843, p \< 0,05)**, mas sem efeito estatisticamente significativo em frequência Baixa (0,189 cortes/s: estimativa \= \+0,358, p \= ns)65.  
Na **Rota do Erro de Predição e Modelo AST (*Asymmetric Sampling in Time*) para Engajamento Sustentado (Conclusão e Revisualização)**, a perceção humana da fala apoia-se em janelas temporais de integração curtas (\~20–40 ms) e longas (\~150–250 ms)65. Os **cortes sobrepostos (*Overlapping Cuts*)** introduzem micro-disrupções ao cortar ligeiramente os ataques acústicos e eliminar micro-pausas, violando estas janelas temporais e gerando sinais *bottom-up* de atualização de predição que capturam e sustentam a atenção do espectador65. Os cortes sobrepostos aumentam significativamente a conclusão e o *rewatch* em frequência **Baixa (0,189 cortes/s: estimativa \= \+1,396, p \< 0,05)** e **Média (0,331 cortes/s: estimativa \= \+1,602, p \< 0,05)**65. Todavia, em frequência **Alta (0,517 cortes/s)**, a vantagem dos cortes sobrepostos desaparece e perde significância estatística (estimativa \= \+0,329, p \= ns), pois o excesso acumulado de quebras empurra o espectador para uma sobrecarga de recursos cognitivos65.  
![imagem omitida — ver original][image3]

### **Deteção de Cenas (PySceneDetect) e Reenquadramento Vertical 9:16 (YOLOv11-seg \+ MediaPipe)**

A ingestão do vídeo bruto anexado pelo utilizador percorre três estágios computacionais locais antes de qualquer chamada a um LLM.  
No primeiro estágio, ocorre a **normalização de stream e deteção de cortes via PySceneDetect (v0.7.2, licença BSD-3-Clause)**70. Como gravações de telemóvel ou transferências da web apresentam frequentemente Taxa de Quadros Variável (*Variable Frame Rate* — VFR) e deslocamentos (*offsets*) iniciais entre vídeo e áudio, o *worker* executa primeiro o ffprobe para detetar VFR e forçar a conversão para Taxa de Quadros Constante (-vsync cfr), compensando o *offset* de áudio para evitar perda de sincronia labial43. Para ambientes de servidor sem interface gráfica, utiliza-se o pacote scenedetect-headless (baseado em opencv-python-headless)71. Uma vez que o gargalo do PySceneDetect reside na descodificação de vídeo pelo OpenCV em CPU, ativa-se o parâmetro downscale\_factor=2, reduzindo para metade o tempo de processamento em vídeos 1080p (correndo mais rápido que o tempo real em máquinas com 4 vCPUs e 8 GB de RAM) com variação máxima de um a dois frames na fronteira do corte72. O pipeline combina o ContentDetector (que converte frames RGB para HSV e suporta deteção de bordas com pesos \--weights 1.0 0.5 1.0 0.2 \-t 32\) para cortes rápidos e o AdaptiveDetector (detetor de duas passagens que utiliza uma média móvel window\_width dos scores adjacentes e exige min\_scene\_len="0.6s"), essencial para mitigar falsos positivos durante movimentos rápidos de câmara70. O ficheiro CSV de estatísticas gerado é exposto como um Resource MCP para a etapa seguinte35.  
No segundo estágio, realiza-se o **reenquadramento vertical inteligente 9:16 (auto-vertical-reframe / Autocrop-vertical)**10. Caso o utilizador anexe um vídeo horizontal (16:9), o pipeline verthor (auto-vertical-reframe) converte-o para 9:16 (1080×1920) rastreando dinamicamente o sujeito principal10. Em cada cena isolada pelo PySceneDetect, o motor executa o modelo **YOLOv11-seg (yolo11n-seg.pt)** acoplado ao rastreador **ByteTrack** (biblioteca lap) para segmentar e manter os identificadores de pessoas, produtos ou veículos ao longo dos frames10. Simultaneamente, o **MediaPipe (v0.10.14)** extrai caixas delimitadoras faciais e pontos de pose corporal (*face/pose cues*), combinados com modelos de saliência visual (handcrafted por padrão para cenas simples ou deepgazemr para cenas complexas) e um classificador *Haar Cascade* do OpenCV como *fallback* secundário de deteção facial10. O algoritmo pontua os candidatos e aplica uma trajetória de câmara virtual suavizada na estratégia **TRACK** (centrando no rosto com limites de zoom de 1.05–1.85 no preset talking\_head) ou recorre à estratégia **LETTERBOX** quando múltiplos sujeitos estão demasiado espalhados no quadro horizontal para permitir um corte fechado sem amputar elementos relevantes10.  
No terceiro estágio, aplica-se a **heurística de pontuação multimodal de ganchos (Hook & Climax Finder)**. Para identificar automaticamente os melhores segmentos de 3 a 5 segundos para o Gancho — otimizando o *Hook Rate*, definido como:  
![imagem omitida — ver original][image4]  
cujo benchmark em 2026 situa-se entre **30% e 45% no Instagram Reels** e entre **30% e 50% no TikTok** (e 25% a 40% no feed geral da Meta)69 —, o servidor MCP propõe uma função de pontuação composta ![imagem omitida — ver original][image5] para cada segmento candidato ![imagem omitida — ver original][image6]:  
![imagem omitida — ver original][image7]  
Nesta formulação arquitetural, ![imagem omitida — ver original][image8] representa a intensidade média do envelope de ataque acústico extraída via librosa.onset.onset\_strength60; ![imagem omitida — ver original][image9] quantifica a presença de rosto humano no *Frame Zero* (via MediaPipe) ponderada inversamente pela complexidade visual de fundo (para evitar os 45% de aversão ao olhar)10; ![imagem omitida — ver original][image10] mede a presença de termos de abertura direta na segunda pessoa (*"Você está..."*) ou indicadores numéricos extraídos das *word-level timestamps* do WhisperX37; e ![imagem omitida — ver original][image11] é a avaliação atribuída pelo VLM (Gemini 3.8 Flash ou Ollama Qwen2.5-VL) aos *keyframes* da cena quanto à capacidade de demonstrar o produto em ação (*feature hook*)9.

## **Animação de Imagens Estáticas a Custo Zero (Síntese 2.5D Local e Cloud ZeroGPU)**

Muitos microempreendedores do Impulso Stone — especialmente nos segmentos de confeitaria (1091-1/02), comércio de vestuário, bijuterias e artesanato16 — dispõem apenas de fotografias estáticas dos seus produtos tiradas para divulgação no WhatsApp4. Transformar imagens estáticas em vídeos dinâmicos sem violar a restrição de **custo zero** exige substituir APIs comerciais pagas de geração de vídeo (*Image-to-Video* — I2V) por motores locais de síntese geométrica 2.5D complementados por execução oportunista em GPUs partilhadas gratuitas.

### **Inviabilidade das APIs Comerciais de Vídeo Generativo no Modelo Custo Zero**

Conforme o levantamento comparativo de preços de APIs de geração de vídeo verificado em outubro de 2026 (cobrindo 14 fornecedores e 64 modelos)9, as plataformas comerciais de vídeo generativo operam exclusivamente sob faturação paga por segundo, por vídeo ou por unidade/token:

* **Alibaba Cloud (wan2.6-i2v-flash e wan2.2-i2v-flash)**: Apresenta os preços mais baixos por segundo do mercado — **US\$ 0,015/s** em 480p (wan2.2-i2v-flash sem áudio), **US\$ 0,025/s** em 720p (wan2.6-i2v-flash sem áudio; US\$ 0,05/s com áudio) e **US\$ 0,0375/s** em 1080p (wan2.6-i2v-flash sem áudio; US\$ 0,075/s com áudio) —, mas requer conta faturada76.  
* **fal.ai / Kling AI / MiniMax**: Na fal.ai, os modelos minimax/h3-max/image-to-video e text-to-video custam **US\$ 0,05/s** (h3-max-turbo/text-to-video a US\$ 0,025/s), o kling-video/v2.5-turbo/pro/image-to-video custa **US\$ 0,07/s** e o kling-video/v3 custa **US\$ 0,14/s**76. Na API direta da Kling AI (onde 1 Unidade \= US\$ 0,14), o Kling 3.0 sem áudio nativo custa 0,6 Unidades (**US\$ 0,084/s**) em 720p, 0,8 Unidades (**US\$ 0,112/s**) em 1080p e 3,0 Unidades (**US\$ 0,42/s**) em 4K76.  
* **Runway / Luma AI / Google Gemini Omni**: A Runway cobra **US\$ 0,05/s** (5 créditos/s) no Gen-4 Turbo e **US\$ 0,12/s** (12 créditos/s) no Gen-4.576; a Luma AI (Ray 3.2 SDR) cobra **US\$ 0,30** (720p) e **US\$ 1,20** (1080p) por vídeo de 5 segundos76; e o modelo Gemini Omni 1.2 Flash (gemini-omni-1.2-flash) não possui *free tier*, faturando 5.792 tokens por segundo de vídeo em 720p (\~**US\$ 0,07/s** no preço padrão de US\$ 12/1M tokens de vídeo, ou **US\$ 0,104/s** em 1080p com *upsampling*)9.

Além da barreira do custo, modelos difusores generativos re-sintetizam os píxeis da imagem, podendo deformar logótipos, embalagens e texturas reais de produtos físicos11.

### **Motor Primário Local: Pipeline de Paralaxe 2.5D e Morfologia por Fluxo Óptico (Depth Anything V2 \+ OpenCV DIS)**

Para assegurar **deformação zero do produto real** e **custo operacional nulo**, a arquitetura adota como motor padrão o pipeline aberto depth-parallax-pipeline combinado com Depth Anything V2 / Video Depth Anything, desenhado para correr localmente em GPUs de 8 GB (como uma RTX 4060\) ou em CPU para fotografias individuais11.  
O processo inicia-se com a **estimativa de profundidade monocular via Depth Anything V2**11. A partir de uma única foto RGB, o modelo prevê um mapa denso de profundidade relativa por pixel preservando bordas nítidas e estruturas finas graças ao seu treino professor-aluno sobre imagens sintéticas e reais59. O modelo oferece codificadores *ViT-Small* (28,4M parâmetros), *ViT-Base* (113,1M) e *ViT-Large* (381,8M); na versão temporalmente consistente Video-Depth-Anything-Small (destaque na CVPR 2025), a latência é de apenas **7,5 ms em FP16** (9,1 ms em FP32) consumindo 6,8 GB de VRAM numa GPU A10059. Após gerar o mapa de profundidade, os pesos são libertados da VRAM antes da fase de renderização11.  
De seguida, realiza-se a **ancoragem no plano de pivô (PIVOT\_CENTER\_BOX) para garantir deformação zero**11. A região que contém o produto principal é delimitada por PIVOT\_CENTER\_BOX e bloqueada sobre o plano de pivô da câmara virtual11. Isso resulta em **deslocamento líquido zero (*zero net displacement*) para o produto**: como são utilizados os píxeis reais da fotografia sem re-síntese generativa, o produto nunca deforma11. A sensação tridimensional de movimento de câmara em redor do objeto é produzida pelo deslocamento diferencial de paralaxe entre o primeiro plano próximo (*foreground*) e o fundo distante (*sky/background*), controlado pelos parâmetros PARALLAX\_STRENGTH (ajustado para 6 para eliminar halos de borda ou 12–16 para maior separação 3D) e DEPTH\_SIGN11.  
Quando o empreendedor fornece N ≥ 2 fotografias reais do produto capturadas em ângulos sucessivos (ex.: esquerda, três-quartos e frente), o sistema aplica **morfologia de perspetiva por fluxo óptico (OpenCV DIS) em CPU**, interpolando a transição real de perspetiva ao longo do arco da câmara sem efeito fantasma (*ghosting*), finalizando com uma oscilação subtil de câmara de mão (*handheld sway*) para conferir naturalidade orgânica ao ficheiro parallax\_move.mp411.

### **Motor Secundário Cloud: Geração I2V via Hugging Face Spaces ZeroGPU (gradio\_client)**

Para cenas puramente atmosféricas ou *B-roll* ilustrativo onde a síntese generativa seja desejável, o servidor MCP conecta-se programaticamente via gradio\_client a espaços públicos **Hugging Face ZeroGPU** — infraestrutura partilhada que aloca dinamicamente GPUs **NVIDIA RTX Pro 6000 Blackwell** (em fatias large de 48 GB com custo de quota 1×, ou xlarge de 96 GB com custo de quota 2×) — executando modelos abertos rápidos como **Lightricks/ltx-video-distilled** ou **Dream-Wan 2.2 Faster Pro**46.  
Para operar dentro das restrições gratuitas do ZeroGPU sem sofrer erros de bloqueio, o roteador MCP aplica três regras de engenharia baseadas no funcionamento interno da plataforma46:

> 1. **Orçamento Diário de 300 Segundos**: Uma conta gratuita na Hugging Face possui um teto diário de **5 minutos (300 segundos) de GPU** (que reinicia 24 horas após o primeiro uso; contas PRO dispõem de 8× mais quota, ou 40 minutos/dia)46.  
> 2. **Mitigação da Inflação de Reserva (ZeroGPU quota exceeded)**: Quando uma função decorada com @spaces.GPU(duration=N) é chamada, o ZeroGPU verifica antecipadamente se a quota restante do visitante é maior ou igual à reserva declarada N (o padrão é 60s, mas muitos Spaces públicos declaram 180s para tarefas que duram \~40s)46. Se o visitante tiver 50 segundos restantes e o Space solicitar 60 segundos, a chamada falha imediatamente com ZeroGPU quota exceeded (*"60s requested vs. 30s left"*), e chamadas que falhem a meio também descontam a reserva46.  
> 3. **Hospedagem de 2 Spaces Próprios Calibrados**: Como contas pessoais gratuitas em situação regular (e-mail verificado e conta com mais de 30 dias) podem **hospedar gratuitamente até 2 ZeroGPU Spaces**46, a arquitetura clona o Space de vídeo para a própria conta, mantendo size="large" (48 GB, custo 1×) e ajustando o decorador @spaces.GPU para duration \= round(measured\_max \* 1.4) (ou passando uma função *callable* dinâmica), maximizando a prioridade na fila e aproveitando integralmente os 300 segundos diários46.

## **Edição Programática Local, Sincronização Musical (MIR) e Legendagem Dinâmica**

A fase de montagem combina os cortes reenquadrados, as animações 2.5D, a locução em português, a trilha sonora e as legendas estilo karaoke num ficheiro .mp4 (1080×1920, yuv420p, H.264) pronto para publicação10.

### **Comparativo Económico: APIs de Edição na Nuvem vs. Renderização Local Open-Source**

As APIs comerciais de edição e renderização em nuvem operam sob modelos de créditos ou minutos que inviabilizam o custo zero, aplicando marcas d'água ou limites severos de resolução nos planos gratuitos (dados verificados em setembro–novembro de 2026\)20:

* **Shotstack**: Concede apenas 10 créditos gratuitos no registo (válidos por 30 dias e com marca d'água)3. No modelo *Pay-as-you-go*, cobra US\$ 10 por 50 minutos (**US\$ 0,20/minuto**, 1080p máx.); no plano *Starter*, cobra **US\$ 39/mês** para 250 minutos (**US\$ 0,156/minuto**); e no plano *Scale*, cobra **US\$ 199/mês** para 2.000 minutos (**US\$ 0,10/minuto**)20.  
* **Creatomate**: O plano gratuito oferece 50 créditos únicos, mas restringe a saída a pequenas pré-visualizações de até **480 píxeis**21. O consumo de créditos escala diretamente com a resolução e taxa de quadros segundo a fórmula documentada20:

![imagem omitida — ver original][image12]  
Enquanto 1 minuto em 720p a 25 fps consome \~14 créditos (6,91 créditos para um Short de 30s), renderizar 1 minuto em Full HD (1080p a 25 fps) consome ⌈(1920 × 1080 × 25 × 60\) / 100.000.000⌉ \= ⌈31,104⌉ \= **32 créditos**20. No plano *Essential* (2.000 créditos/mês, faturado a US\$ 45/mês no ciclo anual de US\$ 540/ano ou US\$ 54/mês no ciclo mensal), o custo efetivo em 1080p atinge **\~US\$ 0,864 por minuto exportado** (e \~US\$ 0,413/minuto no plano *Growth 10K* de US\$ 129/mês mensal ou US\$ 108/mês anual)20.

* **JSON2Video**: O nível gratuito fornece 600 créditos (a uma taxa fixa de 1 crédito \= 1 segundo de vídeo renderizado, ou 10 minutos), mas inclui **marca d'água obrigatória**21. Os planos sem marca d'água custam US\$ 49,95 (pagamento único pré-pago para 120 minutos, **\~US\$ 0,416/minuto**), US\$ 49,95/mês no plano *Professional* para 200 minutos (**\~US\$ 0,250/minuto**) ou US\$ 99,95/mês no plano *Startup* para 500 minutos (**\~US\$ 0,200/minuto**)20.  
* **Plainly Videos**: Baseado na renderização de templates de After Effects na nuvem, não possui plano gratuito (apenas 14 dias de teste) e cobra **US\$ 69/mês** para 50 minutos (**US\$ 1,38/minuto**) no plano *Starter*, **US\$ 134/mês** para 100 minutos no *Explorer* e **US\$ 649/mês** para 600 minutos (**\~US\$ 1,082/minuto**) no *Pro*20.  
* **Remotion & Editframe (Licenciamento Local Custo Zero)**: Enquanto o *Remotion for Automators* na nuvem exige um mínimo de US\$ 100/mês (US\$ 0,01/render \+ \~US\$ 0,017 por vídeo de 1 minuto em AWS Lambda us-east-1 com 2048 MB RAM)21 e o *Editframe Cloud* cobra US\$ 99/mês \+ US\$ 0,02/minuto em 1080p83, **tanto o Remotion quanto o Editframe (via Client-Side SDK / WebCodecs) oferecem licença 100% gratuita (US\$ 0\) para indivíduos e equipas de até 3 colaboradores que renderizem nos seus próprios computadores**7.

![imagem omitida — ver original][image13]

### **Arquitetura do Motor de Edição Local: Kinocut \+ FFmpeg \+ Remotion MCP App**

A montagem programática é executada por quatro subsistemas locais coordenados pelo servidor MCP.  
O primeiro subsistema gere as **operações de ficheiro e timeline com guardrails via Kinocut e FFmpeg**. O **Kinocut** (anteriormente mcp-video, licenciado sob **Apache-2.0**) funciona como servidor MCP local e cliente Python/CLI, disponibilizando **87 ferramentas construídas sobre o FFmpeg** que cobrem cortes, concatenação, redimensionamento, *split-screens*, *picture-in-picture*, sobreposições, legendas e transições3. Ao contrário de servidores minimalistas como o ffmpeg-mcp-lite (que expõe 8 ferramentas básicas)84, o Kinocut incorpora **validação pré-voo (*preflight validation*) e pontos de controlo de qualidade** para impedir que o agente produza silenciosamente ficheiros corrompidos3. Quanto à conformidade legal do FFmpeg, a biblioteca base é licenciada sob **LGPLv2.1** (passando a **GPLv2+** se compilada com \--enable-gpl para incluir módulos como libx264)21. Para uso privado local não há restrições; caso o software seja distribuído empacotado, compilar o FFmpeg sem \--enable-gpl e sem \--enable-nonfree, utilizando ligação dinâmica (.dll/.so) e codificadores de hardware do sistema (h264\_videotoolbox ou NVENC), assegura conformidade estrita com a LGPLv2.110.  
O segundo subsistema realiza a **remoção automática de silêncios e engenharia de jump-cuts (FFmpeg silencedetect e auto-editor)**. Os parâmetros padrão do filtro silencedetect do FFmpeg (noise=-60dB:d=2) falham em gravações reais porque o piso de ruído (*noise floor*) de um microfone condensador em escritório doméstico situa-se perto de \-38 dBFS a \-40 dBFS e o de chamadas remotas perto de \-35 dBFS85. O pipeline executa primeiro uma passagem de deteção **desativando a descodificação de vídeo com a flag \-vn** (ffmpeg \-hide\_banner \-nostats \-vn \-i input.mp4 \-af silencedetect=noise=-32dB:d=0.4 \-f null \-), o que reduz o tempo de análise de um ficheiro 1080p de 58 minutos de \~80 segundos para cerca de **9 segundos**86. O limiar é ajustado conforme a fonte: \-32dB:d=0.4 para escritório doméstico/telemóvel, \-45dB:d=0.5 para estúdio tratado e \-50dB:d=0.25 para locução sintética de TTS (onde o silêncio é zero digital absoluto)85. Para evitar que a fala soe robótica ou que consoantes fricativas (*s*, *f*) sejam cortadas, o script inverte a lista de silêncios preservando uma margem de respiração (PAD de 0,06s a 0,20s, ou \--margin 0.2sec no auto-editor, que também permite cortar imobilidade visual via \--edit motion:threshold=0.02)85. Na junção dos segmentos (trim e atrim), apenas a imagem é alinhada ao frame inteiro; **o áudio preserva o tempo exato ao milissegundo** (evitando amputar até 20 ms de uma palavra) e recebe micro-fades de **15 ms** (afade=t=in:d=0.015 e afade=t=out:d=0.015), alternando um *punch-in zoom* subtil nas junções visuais e mantendo os últimos 5 segundos fixos no orador85.  
O terceiro subsistema executa a **sincronização rítmica e deteção de batidas musicais (MIR)**. Como o alinhamento audiovisual impulsiona a retenção (um estudo da Universidade de Baylor de 2022 citado na literatura da área indica que áudios rápidos de tendência elevam os níveis de dopamina em 35% face a músicas comuns)67, a arquitetura combina três bibliotecas Python *open-source* de *Music Information Retrieval*60. Para análise offline de alta precisão, utiliza-se o **madmom**, que alia Redes Neurais Recorrentes (RNNBeatProcessor) a uma Rede Bayesiana Dinâmica (DBNBeatTrackingProcessor(fps=100)) para extrair batidas e *downbeats* com excelente precisão em ritmos complexos, pop e música eletrónica60. Para fluxos que exijam baixa latência (\<50ms) e menor uso de memória que o madmom, emprega-se o **BeatNet** (modelo CRNN com filtragem de partículas para rastreamento conjunto de batida, *downbeat*, tempo e compasso), complementado pelo **librosa** (librosa.onset.onset\_strength) e pelo **Essentia** (RhythmExtractor2013 nos modos multifeature ou degara e BpmHistogramDescriptors)60.  
O quarto subsistema encarrega-se da **legendagem dinâmica estilo karaoke (pysubs2 \+ FFmpeg ASS) e dos gráficos interativos React (Remotion MCP App)**. A partir das *word-level timestamps* geradas pelo alinhamento wav2vec2 do WhisperX (ou do MediaPipe Kokoro TTS), a biblioteca **pysubs2** (compatível com Python 3.12+, licença MIT, sem dependências externas) gera um ficheiro **.ass (Advanced SubStation Alpha)**39. O formato .ass permite injetar tags de transformação e cor palavra a palavra (e efeitos de borda arredondada via SubTextHighlight), exibindo blocos curtos de 3 a 5 palavras para respeitar a taxa de leitura de **5 a 10 palavras por segundo**39. Para sobreposições animadas em React, o servidor acopla o **remotion-mcp-app** (mcp-use/remotion-mcp-app), que compila o código com esbuild em menos de um segundo e disponibiliza um reprodutor interativo embutido no chat (Remotion Player View) com a ferramenta efémera update\_video, permitindo que o agente edite apenas os ficheiros alterados em tempo real (sendo gratuito para indivíduos e empresas com até 3 colaboradores)7.

### **Conformidade de Direitos Autorais em Música e Efeitos Sonoros (SFX)**

Para proteger os microempreendedores do Impulso Stone contra reivindicações de direitos autorais ou violações de licença, a arquitetura audita rigorosamente as fontes de áudio. As APIs comerciais de catálogo musical — como a **Epidemic Sound API** (cujo plano *Free* de US\$ 0/mês com 50 transferências e acesso a 55.000 faixas e 250.000 SFX **cobre apenas prototipagem e testes, excluindo uso comercial ou em produção**)22 e a **Soundstripe API** (cuja chave de teste de 30 dias aplica **marca d'água de áudio**)95 — não podem ser usadas gratuitamente em vídeos publicados. Da mesma forma, APIs de monitorização de tendências do TikTok como **Soundcharts** (a partir de US\$ 50/mês para 10k requisições, com sandbox limitado a 1.000 chamadas)96, **Chartmetric** (a partir de US\$ 350/mês no plano fixo ou US\$ 0,01/crédito com US\$ 5 de teste)99 e **Apify TikTok Trending Sounds** (a partir de US\$ 2,40 por 1.000 resultados)101 são pagas e fornecem apenas metadados analíticos, não licenças de sincronização de áudio102. Além disso, na **Freesound API** (que hospeda mais de 430.000 sons sob licenças CC0, CC-BY e CC-BY-NC), os Termos de Uso determinam que **o uso gratuito da API é permitido apenas para fins não-comerciais**25.  
Para garantir **custo zero e conformidade comercial total**, o servidor MCP adota uma estratégia dupla:

> 1. **Música e Efeitos Sonoros Embutidos via Pixabay API e Biblioteca Local CC0**: A API da Pixabay é **100% gratuita para uso comercial e não-comercial** sem exigência de atribuição sob a *Pixabay Content License* (e CC0 para conteúdos publicados antes de 9 de janeiro de 2019), permitindo **100 requisições por minuto** (com limite de 500 resultados acessíveis por consulta)28. O servidor cumpre a regra obrigatória da Pixabay de **armazenar as respostas em cache durante pelo menos 24 horas**, evita faixas marcadas com o ícone de escudo (registadas no *YouTube Content ID*) ou guarda automaticamente o certificado de licença disponibilizado pela plataforma47.  
> 2. **Anexação Nativa no Momento da Publicação (Instagram Audio API e TikTok Commercial Music Library)**: Quando o utilizador publica diretamente através de uma conta profissional, o sistema utiliza a **Instagram Graph Audio API** (que pesquisa e anexa áudios originais e músicas diretamente ao Reel na publicação)26 e o endpoint **/v1.3/business/music/list/ da TikTok Commercial Music Library (CML)** — um catálogo global pré-licenciado de **1 milhão de músicas gratuitas para uso comercial em contas de negócios** — vinculando o parâmetro song\_clip\_id ao vídeo sem incorrer em custos de licenciamento27.

## **Adaptação Setorial para o Público Impulso Stone (Mapeamento CNAE e Frameworks de Conversão)**

O programa **Impulso Stone** estrutura a capacitação do microempreendedor em módulos práticos (*01\. Como sair do zero*, *02\. Venda mais de um jeito simples via WhatsApp e redes sociais*, *03\. Planejamento financeiro*, *04\. Mentoria com mais de 400 colaboradores da Stone*, *05\. Precificação correta* e *06\. Apoio financeiro orientado a microcrédito*), acolhendo tanto negócios formalizados quanto empreendedores informais que estão a começar em casa4.  
Para automatizar a direção criativa sem exigir conhecimentos técnicos do utilizador, o servidor MCP cruza os setores líderes de abertura de MEI e MPE no Brasil (segundo os levantamentos do Sebrae e da Receita Federal de 2025/2026)14 com os **5 Frameworks Estruturais de Vídeo de Resposta Direta** (PAS, AIDA, BAB, UGC Testimonial Flow e Product Demo, conforme sistematizados pela Benly em março de 2026\)37:

| Segmento de Negócio (Público Impulso Stone) | Principais CNAEs MEI / MPE (Dados Sebrae 2025/2026) | Framework de Roteiro e Divisão Temporal (Segundos) | Configuração Técnica Automática no Servidor MCP (Preset Visão, Estilo de Corte e Voz) |
| :---- | :---- | :---- | :---- |
| **1\. Beleza, Estética e Cuidados Pessoais** (52% recebem via Pix)16 | 9602-5/01 (Manicure/Pedicure, Cabeleireiros: **13.108 aberturas MEI** em 2025), 9602-5/02 (Maquiador)15. | **BAB (*Before-After-Bridge*) — 30s**37: • **0–8s (Antes)**: Estado inicial do cabelo/unha/pele. • **8–20s (Depois)**: Transformação aspiracional revelada no *downbeat*. • **20–27s (Ponte)**: Demonstração rápida da técnica/produto. • **27–30s (CTA)**: Agendamento via WhatsApp/Pix4. | • **Reframe**: Preset talking\_head (zoom 1.05–1.85) \+ *split-screen* comparativo via Kinocut10. • **Corte**: *Seamless Cuts* a **0,517 cortes/s** (alta frequência para maximizar *Likes* e reações positivas)65. • **Voz TTS**: pt-BR-FranciscaNeural (rate=+10%) ou pf\_dora (Kokoro-82M)13. |
| **2\. Alimentação, Confeitaria e Marmitaria** (+81 mil novos negócios de panificação em 2026\)113 | 5620-1/04 (Doceiro / Marmiteiro), 1091-1/02 (Confeiteiro), 1091-1/01 (Padeiro), Restaurantes (**8.855 MEI** \+ **7.068 Catering/Bufê** em 2025\)15. | **Product Demo \+ PAS — 15s a 30s**37: • **0–5s (Feature Hook)**: *Close-up* cinético de alta textura (*apelo visual gastronómico* / corte do bolo). • **5–18s (Walkthrough)**: Montagem passo a passo sincronizada à batida. • **18–24s (Diferencial)**: Ingredientes frescos / porção generosa. • **24–30s (Prova \+ CTA)**: Encomendas via WhatsApp4. | • **Animação 2.5D**: Depth Anything V2 com PIVOT\_CENTER\_BOX bloqueado no prato (deformação zero do alimento) \+ PARALLAX\_STRENGTH=1011. • **MIR**: Cortes cravados nos *downbeats* via madmom60. • **SFX**: Sons ambiente via Pixabay API106. |
| **3\. Comércio Varejista de Vestuário, Moda e Artesanato** (62–63% vendas via Pix)16 | Comércio varejista de artigos do vestuário e acessórios (**7.894 aberturas MEI** e **1.203 MPE** em 2025), 1412-6/02 (Costureiro), Fabricantes de bijuterias15. | **UGC Testimonial Flow — 21s a 35s** (associado a \+26% de conversão segundo dados da Shopify)37: • **0–4s (Gancho Pessoal)**: Início a meio da história (*"Preciso de vos mostrar como veste..."*). • **4–12s (Contexto)**: Dificuldade em achar caimento/preço. • **12–22s (Descoberta)**: Demonstração das peças. • **22–30s (Prova \+ Recomendação)**: Chamada direta casual37. | • **Animação de Catálogo**: Fluxo óptico OpenCV DIS entre 3 fotos do produto (frente, três-quartos, detalhe) \+ oscilação *handheld sway*11. • **Corte**: *Seamless Cuts* a **0,331 cortes/s** (mediana natural de criadores)65. • **Voz TTS**: pt-BR-ThalitaMultilingualNeural13. |
| **4\. Serviços Técnicos, Reparos, Construção e Logística** | 4321-5/01 (Eletricista), 4520-0/01 (Mecânico), 4399-1/03 (Pedreiro), 4330-4/04 (Pintor), Entregas/Malote (**20.732 MEI**) e Cargas (**19.516 MEI** em 2025\)15. | **PAS (*Problem-Agitate-Solution*) — 20s a 30s** (ideal para tráfego frio)37: • **0–5s (Problema)**: Mostra o defeito real (curto-circuito, infiltração, peça gasta). • **5–18s (Agitação)**: Custo e risco de ignorar o problema. • **18–25s (Solução)**: Execução limpa do serviço. • **25–30s (CTA)**: Orçamento rápido com urgência37. | • **Reframe**: YOLOv11-seg rastreando ferramentas/veículos \+ preset cars (zoom 1.00–1.30) ou talking\_head10. • **Corte**: **Overlapping Cuts a 0,331 cortes/s** (viola janelas AST de 150–250ms para sustentar a atenção até ao fim da explicação técnica, estimativa \+1,602)65. • **Voz TTS**: pt-BR-AntonioNeural ou Piper pt\_BR-faber-medium12. |
| **5\. Ensino, Treino, Beleza/Fitness e Serviços Locais** | Atividades de ensino (**8.909 aberturas MEI** e **1.369 MPE** em 2025), 8599-6/99 (Professor particular), 9609-2/08 (*Pet sitter* / Adestrador), Publicidade (**14.165 MEI**)15. | **AIDA (*Attention-Interest-Desire-Action*) — 35s a 45s** (um vídeo de 40s com 60% de retenção supera um de 20s com 70% em tempo total de visualização)37: • **0–5s (Atenção)**: Afirmação contraintuitiva. • **5–18s (Interesse)**: Dado prático ou dica rápida. • **18–35s (Desejo)**: Benefício e transformação. • **35–45s (Ação \+ Loop)**: Convite com *seamless loop*37. | • **Edição**: Remoção de silêncios \>0,4 s para 0,2 s \+ *punch-in zoom* alternado a cada corte \+ legendas .ass com destaque por palavra39. • **Loop**: A última frase conecta-se sintaticamente com os primeiros 3 segundos para impulsionar APV \>100%66. |

## **Implementação Prática: Contratos MCP, Roteador de Fallback e Grafo FFmpeg**

Os blocos de código seguintes apresentam a implementação de referência em Python (compatível com Python 3.11/3.12+) integrando o servidor MCP, o roteador em cascata com leitura de cabeçalhos HTTP e o construtor de grafos FFmpeg calibrado para retenção.

### **1\. Servidor MCP com Primitivas Completas (Prompts, Resources, Tools)**

Python  
import asyncio  
import json  
from pathlib import Path  
from mcp.server.fastmcp import FastMCP, Context

\# Inicialização do Servidor MCP Impulso Stone  
mcp \= FastMCP(  
    "ImpulsoStone-Reels-Engine",  
    dependencies=\["scenedetect\[opencv-headless\]", "whisperx", "pysubs2", "edge-tts", "librosa"\]  
)

WORKSPACE\_ROOT \= Path("/workspace/impulso\_stone")

\# \=====================================================================  
\# 1\. PRIMITIVA: RESOURCES (Leitura controlada pelo Cliente, Custo 0 LLM)  
\# \=====================================================================  
@mcp.resource("stone-cnae://profiles/{cnae\_code}")  
def get\_cnae\_marketing\_profile(cnae\_code: str) \-\> str:  
    """Retorna o perfil de conversão, tom de voz e preset técnico por CNAE MEI."""  
    profiles \= {  
        "9602-5/01": {  
            "ocupacao": "Cabeleireiro / Manicure e Pedicure",  
            "framework": "BAB (Before-After-Bridge)",  
            "cut\_style": "seamless",  
            "target\_cuts\_per\_sec": 0.517,  
            "reframe\_preset": "talking\_head",  
            "tts\_voice": "pt-BR-FranciscaNeural"  
        },  
        "5620-1/04": {  
            "ocupacao": "Doceiro / Marmiteiro Independente",  
            "framework": "Product Demo \+ PAS",  
            "cut\_style": "seamless",  
            "target\_cuts\_per\_sec": 0.331,  
            "reframe\_preset": "movie",  
            "parallax\_strength": 10,  
            "tts\_voice": "pt-BR-ThalitaMultilingualNeural"  
        },  
        "4321-5/01": {  
            "ocupacao": "Eletricista / Serviços Técnicos",  
            "framework": "PAS (Problem-Agitate-Solution)",  
            "cut\_style": "overlapping",  
            "target\_cuts\_per\_sec": 0.331,  
            "reframe\_preset": "talking\_head",  
            "tts\_voice": "pt-BR-AntonioNeural"  
        }  
    }  
    return json.dumps(profiles.get(cnae\_code, profiles\["5620-1/04"\]), ensure\_ascii=False)

@mcp.resource("stone-media://jobs/{job\_id}/analysis\_summary")  
def get\_job\_multimodal\_summary(job\_id: str) \-\> str:  
    """Expõe o JSON consolidado de cenas (PySceneDetect), transcrição (WhisperX) e batidas (Madmom)."""  
    summary\_path \= WORKSPACE\_ROOT / job\_id / "multimodal\_summary.json"  
    if not summary\_path.exists():  
        return json.dumps({"status": "pending\_analysis"})  
    return summary\_path.read\_text(encoding="utf-8")

\# \=====================================================================  
\# 2\. PRIMITIVA: PROMPTS (Templates invocados explicitamente pelo MEI)  
\# \=====================================================================  
@mcp.prompt("gerar\_reel\_impulso\_stone")  
def prompt\_gerar\_reel(cnae\_code: str, objetivo\_venda: str, job\_id: str) \-\> str:  
    """Template estruturado que guia o agente na criação do Reel sem desperdiçar chamadas."""  
    return (  
        f"Você é o Diretor Criativo Automatizado do programa Impulso Stone.\\n"  
        f"1. Leia os recursos anexados 'stone-cnae://profiles/{cnae\_code}' e 'stone-media://jobs/{job\_id}/analysis\_summary'.\\n"  
        f"2. Objetivo do microempreendedor: {objetivo\_venda}.\\n"  
        f"3. Selecione o gancho (0-3s) com maior índice foveal/onset e estruture o roteiro seguindo o framework do CNAE.\\n"  
        f"4. Garanta que o texto de sobreposição no Frame Zero tenha no máximo 5 palavras e que a frase final "  
        f"conecte sintaticamente ao início (Seamless Loop).\\n"  
        f"5. Invoque a tool 'assemble\_and\_render\_reel' passando o plano de edição JSON validado."  
    )

### **2\. Roteador Inteligente em Cascata (ZeroCostCascadeRouter)**

Python  
import os  
import subprocess  
import httpx  
import edge\_tts  
from pathlib import Path

class ZeroCostCascadeRouter:  
    """  
    Gere a rotação automática entre Free Tiers de APIs (Groq, Cloudflare, Gemini, Edge-TTS, ZeroGPU)  
    e motores locais open-source (WhisperX, Ollama Qwen2.5-VL, Kokoro-82M, Piper TTS, Depth Anything V2).  
    """  
    def \_\_init\_\_(self):  
        self.groq\_remaining\_rpd \= 2000  
        self.groq\_remaining\_tpm \= 8000  
        self.cf\_neurons\_used\_today \= 0  
        self.cf\_neuron\_daily\_cap \= 10000  
        self.zerogpu\_seconds\_left \= 300  \# 5 minutos/dia no plano Free Hugging Face

    async def transcribe\_with\_word\_timestamps(self, audio\_path: Path, lang: str \= "pt") \-\> dict:  
        """  
        Cascata ASR:  
        Tier 1: Groq Free Plan (whisper-large-v3-turbo, limite 25MB, 7.200s/h, 28.800s/d)  
        Tier 2: Cloudflare Workers AI (@cf/openai/whisper-large-v3-turbo, 46.63 neurónios/min)  
        Tier 3: Local WhisperX (faster-whisper INT8/FP16 \+ Silero VAD \+ wav2vec2 forced alignment)  
        """  
        file\_size\_mb \= audio\_path.stat().st\_size / (1024 \* 1024)  
        groq\_key \= os.getenv("GROQ\_API\_KEY")

        \# Tentativa Tier 1: Groq API (se ficheiro \<= 25 MB e houver quota)  
        if groq\_key and file\_size\_mb \<= 24.5 and self.groq\_remaining\_rpd \> 5:  
            try:  
                async with httpx.AsyncClient(timeout=30.0) as client:  
                    with open(audio\_path, "rb") as f:  
                        resp \= await client.post(  
                            "https\://api.groq.com/openai/v1/audio/transcriptions",  
                            headers={"Authorization": f"Bearer {groq\_key}"},  
                            files={"file": (audio\_path.name, f, "audio/wav")},  
                            data={  
                                "model": "whisper-large-v3-turbo",  
                                "language": lang,  
                                "response\_format": "verbose\_json",  
                                "timestamp\_granularities\[\]": \["word", "segment"\]  
                            }  
                        )  
                    \# Atualiza estado a partir dos cabeçalhos oficiais da Groq  
                    self.groq\_remaining\_rpd \= int(resp.headers.get("x-ratelimit-remaining-requests", 100))  
                    if resp.status\_code \== 200:  
                        raw\_transcript \= resp.json()  
                        \# Executa alinhamento fonético local wav2vec2 para corrigir drift de timestamps  
                        return self.\_run\_local\_wav2vec2\_alignment(audio\_path, raw\_transcript, lang)  
            except Exception:  
                pass  \# Comuta silenciosamente para o próximo nível

        \# Fallback Determinístico Local: WhisperX completo (VAD \+ Faster-Whisper \+ Wav2Vec2)  
        return self.\_run\_local\_whisperx\_full(audio\_path, lang)

    def \_run\_local\_whisperx\_full(self, audio\_path: Path, lang: str) \-\> dict:  
        import whisperx  
        device \= "cuda" if os.getenv("HAS\_CUDA") \== "1" else "cpu"  
        compute\_type \= "float16" if device \== "cuda" else "int8"  
        model \= whisperx.load\_model("large-v3", device, compute\_type=compute\_type, language=lang)  
        audio \= whisperx.load\_audio(str(audio\_path))  
        result \= model.transcribe(audio, batch\_size=8)  
        model\_a, metadata \= whisperx.load\_align\_model(language\_code=lang, device=device)  
        aligned \= whisperx.align(result\["segments"\], model\_a, metadata, audio, device, return\_char\_alignments=False)  
        return aligned

    def \_run\_local\_wav2vec2\_alignment(self, audio\_path: Path, groq\_json: dict, lang: str) \-\> dict:  
        import whisperx  
        device \= "cuda" if os.getenv("HAS\_CUDA") \== "1" else "cpu"  
        audio \= whisperx.load\_audio(str(audio\_path))  
        model\_a, metadata \= whisperx.load\_align\_model(language\_code=lang, device=device)  
        return whisperx.align(groq\_json.get("segments", \[\]), model\_a, metadata, audio, device)

    async def synthesize\_ptbr\_voiceover(  
        self, text: str, output\_mp3: Path, output\_srt: Path, voice: str \= "pt-BR-FranciscaNeural", rate: str \= "+10%"  
    ) \-\> dict:  
        """  
        Cascata TTS PT-BR (100% Comercialmente Segura e Gratuita):  
        Tier 1: Microsoft Edge-TTS (pt-BR-FranciscaNeural / AntonioNeural / ThalitaMultilingualNeural)  
        Tier 2: Local Kokoro-82M PT-BR (vozes pf\_dora, pm\_alex via ONNX / MediaPipe)  
        Tier 3: Local Piper TTS ONNX (Trelis/piper-pt-br-faber-medium, Licença CC0)  
        """  
        try:  
            communicate \= edge\_tts.Communicate(text, voice, rate=rate)  
            submaker \= edge\_tts.SubMaker()  
            with open(output\_mp3, "wb") as audio\_file:  
                async for chunk in communicate.stream():  
                    if chunk\["type"\] \== "audio":  
                        audio\_file.write(chunk\["data"\])  
                    elif chunk\["type"\] \== "WordBoundary":  
                        submaker.feed(chunk)  
            output\_srt.write\_text(submaker.get\_srt(), encoding="utf-8")  
            return {"engine": "edge-tts", "audio": str(output\_mp3), "subtitles": str(output\_srt)}  
        except Exception:  
            \# Fallback Local Imediato: Piper TTS PT-BR (CC0 Public Domain) em CPU  
            wav\_out \= output\_mp3.with\_suffix(".wav")  
            subprocess.run(  
                \["piper", "--model", "/models/pt\_BR-faber-medium.onnx", "--output\_file", str(wav\_out)\],  
                input\=text.encode("utf-8"),  
                check=True  
            )  
            subprocess.run(\["ffmpeg", "-y", "-i", str(wav\_out), str(output\_mp3)\], check=True)  
            return {"engine": "piper-local-cc0", "audio": str(output\_mp3), "subtitles": None}

### **3\. Motor de Corte Calibrado (AST / Fluência), Legendas Karaoke .ASS e Ducking via FFmpeg**

Python  
import re  
import subprocess  
import pysubs2  
from pathlib import Path

def build\_ast\_calibrated\_jumpcuts(  
    video\_path: Path,  
    output\_path: Path,  
    cut\_style: str \= "seamless",  \# "seamless" (Likes) ou "overlapping" (Conclusão/AST)  
    noise\_db: int \= \-32,          \# \-32dB para home office/telemóvel; \-50dB para TTS  
    min\_silence\_dur: float \= 0.40  
) \-\> Path:  
    """  
    Executa deteção rápida de silêncio (-vn), inverte para segmentos de fala mantendo respiração  
    calibrada segundo Dost & Huang (2026) e aplica micro-fades de 15ms sem cortar sílabas.  
    """  
    \# Passo 1: Passagem rápida apenas no áudio (-vn evita descodificar vídeo desnecessariamente)  
    cmd\_detect \= \[  
        "ffmpeg", "-hide\_banner", "-nostats", "-vn", "-i", str(video\_path),  
        "-af", f"silencedetect=noise={noise\_db}dB:d={min\_silence\_dur}",  
        "-f", "null", "-"  
    \]  
    log \= subprocess.run(cmd\_detect, stderr=subprocess.PIPE, text=True).stderr

    starts \= \[float(x) for x in re.findall(r"silence\_start: (-?\[\\d.\]+)", log)\]  
    ends \= \[float(x) for x in re.findall(r"silence\_end: (-?\[\\d.\]+)", log)\]  
    ends \+= \[None\] \* (len(starts) \- len(ends))  \# Proteção caso o ficheiro termine em silêncio

    \# Calibração da margem de respiração conforme o objetivo neuromarketing:  
    \# Seamless: preserva \~180ms de janela temporal AST (PAD=0.09s em cada lado)  
    \# Overlapping: comprime a pausa para \<40ms (PAD=0.015s), gerando erro de predição bottom-up  
    pad \= 0.090 if cut\_style \== "seamless" else 0.015

    keep\_segments, cursor \= \[\], 0.0  
    for s, e in zip(starts, ends):  
        if s \+ pad \> cursor:  
            keep\_segments.append((cursor, s \+ pad))  
        if e is None:  
            cursor \= None  
            break  
        cursor \= max(0.0, e \- pad)

    \# Passo 2: Construção do filter\_complex com punch-in zoom alternado e afade de 15ms  
    filter\_parts, concat\_inputs \= \[\], \[\]  
    for idx, (st, en) in enumerate(keep\_segments):  
        dur \= en \- st  
        if dur \< 0.18:  
            continue  
        fade\_out\_st \= max(0.0, dur \- 0.015)  
        \# Alterna subtilmente entre escala 1.0 e punch-in 1.08 para esconder jump-cuts  
        zoom\_filter \= ",scale=1166:2074,crop=1080:1920" if idx % 2 \== 1 else ",scale=1080:1920"  
        filter\_parts.append(  
            f"\[0:v\]trim={st:.3f}:{en:.3f},setpts=PTS-STARTPTS{zoom\_filter}\[v{idx}\];"  
            f"\[0:a\]atrim={st:.3f}:{en:.3f},asetpts=PTS-STARTPTS,"  
            f"afade=t=in:st=0:d=0.015,afade=t=out:st={fade\_out\_st:.3f}:d=0.015\[a{idx}\];"  
        )  
        concat\_inputs.append(f"\[v{idx}\]\[a{idx}\]")

    n\_segs \= len(concat\_inputs)  
    filter\_graph \= "".join(filter\_parts) \+ f"{''.join(concat\_inputs)}concat=n={n\_segs}:v=1:a=1\[outv\]\[outa\]"

    subprocess.run(\[  
        "ffmpeg", "-y", "-i", str(video\_path),  
        "-filter\_complex", filter\_graph,  
        "-map", "\[outv\]", "-map", "\[outa\]",  
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix\_fmt", "yuv420p",  
        "-c:a", "aac", "-b:a", "192k", str(output\_path)  
    \], check=True)  
    return output\_path

def generate\_karaoke\_ass\_subtitles(aligned\_segments: list, ass\_output\_path: Path) \-\> Path:  
    """  
    Converte os word-level timestamps do WhisperX num ficheiro .ASS com destaque dinâmico  
    de palavra ativa e cadência de 5-10 palavras por segundo (TikTok Creative Center standard).  
    """  
    subs \= pysubs2.SSAFile()  
    subs.info\["PlayResX"\] \= "1080"  
    subs.info\["PlayResY"\] \= "1920"

    style \= pysubs2.SSAStyle(  
        fontname="Montserrat ExtraBold",  
        fontsize=68,  
        primarycolor=pysubs2.Color(255, 255, 255, 0),   \# Branco para palavras inativas  
        secondarycolor=pysubs2.Color(252, 201, 52, 0),  \# Amarelo vibrante para destaque  
        outlinecolor=pysubs2.Color(17, 17, 17, 0),  
        backcolor=pysubs2.Color(0, 0, 0, 128),  
        bold=True,  
        outline=4.5,  
        shadow=2.0,  
        alignment=pysubs2.Alignment.MIDDLE\_CENTER,  
        marginv=350  
    )  
    subs.styles\["ImpulsoKaraoke"\] \= style

    \# Agrupa palavras em blocos curtos (máx. 4 palavras por exibição para baixa carga cognitiva)  
    words \= \[w for seg in aligned\_segments for w in seg.get("words", \[\]) if "start" in w and "end" in w\]  
    chunk\_size \= 4  
    for i in range(0, len(words), chunk\_size):  
        chunk \= words\[i:i \+ chunk\_size\]  
        for active\_idx, active\_word in enumerate(chunk):  
            start\_ms \= int(active\_word\["start"\] \* 1000)  
            end\_ms \= int(active\_word\["end"\] \* 1000)  
            formatted\_tokens \= \[\]  
            for j, w in enumerate(chunk):  
                clean\_w \= w\["word"\].strip().upper()  
                if j \== active\_idx:  
                    \# Destaca a palavra ativa em Amarelo/Ciano com leve pop de escala (112%)  
                    formatted\_tokens.append(r"{\\c\&H34C9FC&\\fscx112\\fscy112}" \+ clean\_w \+ r"{\\c\&HFFFFFF&\\fscx100\\fscy100}")  
                else:  
                    formatted\_tokens.append(clean\_w)  
            line \= pysubs2.SSAEvent(start=start\_ms, end=end\_ms, text=" ".join(formatted\_tokens), style="ImpulsoKaraoke")  
            subs.events.append(line)

    subs.save(str(ass\_output\_path), encoding="utf-8")  
    return ass\_output\_path

## **Checklist de Governança, Resiliência e Operação em Produção**

Para manter a operação 100% gratuita, estável e protegida contra alterações súbitas nos fornecedores externos, a implantação da arquitetura no ecossistema Impulso Stone segue cinco diretrizes operacionais permanentes:

> 1. **Fixação de Versões e Cache de Ativos Sintetizados**: Fixar explicitamente no requirements.txt as versões testadas das bibliotecas críticas (scenedetect-headless==0.7.2, whisperx==3.8.6, edge-tts==7.3.1, mediapipe==0.10.14, pysubs2) e armazenar em cache local (por *hash* SHA-256 do texto/parâmetros) todos os áudios gerados por TTS e respostas da Pixabay API (mínimo obrigatório de 24 horas), evitando chamadas repetidas durante edições iterativas no Remotion Player View7.  
> 2. **Isolamento de Projetos e Contas de API**: Dado que os limites da Google Gemini API são partilhados por projeto e os da Groq/Cerebras por organização9, na modalidade distribuída (onde cada mentor ou empreendedor executa o cliente MCP), a arquitetura utiliza o padrão *Bring Your Own Free Key* (gerada gratuitamente sem cartão no Google AI Studio e na Groq Console) combinada com o servidor local Ollama \+ WhisperX, garantindo que o volume de um utilizador nunca esgote a quota de outro9.  
> 3. **Recalibração Dinâmica de Duração no ZeroGPU**: Antes de invocar qualquer Space público de geração de vídeo via gradio\_client, o *worker* inspeciona a assinatura do endpoint para verificar o parâmetro duration e nunca envia chamadas quando o contador local de quota diária da conta gratuita estiver abaixo da reserva solicitada, comutando preventivamente para o pipeline 2.5D local (Depth Anything V2 \+ OpenCV DIS)11.  
> 4. **Higiene de Sincronização Áudio/Vídeo**: Nunca aplicar quantização de tempo ao nível do frame na faixa de áudio durante cortes de silêncio; manter o corte acústico no milissegundo exato com afade de 15 ms, normalizar entradas VFR com \-vsync cfr no ffprobe/FFmpeg e aplicar atenuação dinâmica (*audio ducking*) na música de fundo sempre que houver atividade vocal detetada pelo Silero VAD42.  
> 5. **Auditoria de Direitos Comerciais na Saída**: Bloquear ao nível do schema da ferramenta MCP (assemble\_and\_render\_reel) qualquer tentativa de embutir áudios provenientes de planos gratuitos restritos (como ElevenLabs Free, Epidemic Sound Free ou Freesound CC-BY-NC) em vídeos marcados com finalidade comercial, assegurando que 100% dos Reels gerados pelos empreendedores do Impulso Stone possam ser monetizados e impulsionados em anúncios sem risco jurídico23.

#### **Referências citadas**

> 1. MCP tools, resources, prompts: the three primitives explained \| Blog, [https\://archestra.ai/blog/mcp-tools-resources-prompts](https://archestra.ai/blog/mcp-tools-resources-prompts)  
> 2. Model Context Protocol (MCP) explained: A practical ... \- CodiLime, [https\://codilime.com/blog/model-context-protocol-explained/](https://codilime.com/blog/model-context-protocol-explained/)  
> 3. Best MCP Server for Video Editing Tools in 2026 \- Wireflow, [https\://www\.wireflow.ai/blog/best-mcp-server-for-video-editing-tools-in-2026](https://www.wireflow.ai/blog/best-mcp-server-for-video-editing-tools-in-2026)  
> 4. Impulso Stone, [https\://www\.impulsostone.com.br/](https://www.impulsostone.com.br/)  
> 5. O Programa Impulso Stone \| Educação e Mentoria Gratuita, [https\://www\.impulsostone.com.br/programa](https://www.impulsostone.com.br/programa)  
> 6. Instituto Stone Impacto \| Educação e Empreendedorismo, [https\://www\.impulsostone.com.br/sobre-nos](https://www.impulsostone.com.br/sobre-nos)  
> 7. MCP App for creating animated Remotion video ... \- GitHub, [https\://github.com/mcp-use/remotion-mcp-app](https://github.com/mcp-use/remotion-mcp-app)  
> 8. [https\://github.com/cheaper-inference/OmniRoute/wiki/Free-Tiers](https://github.com/cheaper-inference/OmniRoute/wiki/Free-Tiers)  
> 9. [https\://flatkey.ai/blog/free-llm-apis-2026](https://flatkey.ai/blog/free-llm-apis-2026)  
> 10. [https\://github.com/KazKozDev/auto-vertical-reframe](https://github.com/KazKozDev/auto-vertical-reframe)  
> 11. GitHub \- LeoRToro/depth-parallax-pipeline: Camera-moving-around, [https\://github.com/HackM3nt3/depth-parallax-pipeline](https://github.com/HackM3nt3/depth-parallax-pipeline)  
> 12. Trelis/piper-pt-br-faber-medium \- Hugging Face, [https\://huggingface.co/Trelis/piper-pt-br-faber-medium](https://huggingface.co/Trelis/piper-pt-br-faber-medium)  
> 13. Narração de vídeos com voz neural de graça: edge-tts como, [https\://www\.alissonlimadev.com/blog/narracao-de-videos-com-voz-neural-de-graca-edge-tts-como-alternativa-ao-azure](https://www.alissonlimadev.com/blog/narracao-de-videos-com-voz-neural-de-graca-edge-tts-como-alternativa-ao-azure)  
> 14. Abertura de Pequenos Negócios no Brasil, [https\://inteligencia.sebraemg.com.br/estudo/abertura-de-pequenos-negocios-no-brasil](https://inteligencia.sebraemg.com.br/estudo/abertura-de-pequenos-negocios-no-brasil)  
> 15. Brasil registrou abertura de 4,9 milhões de pequenos negócios em, [https\://www\.seudinheiro.com/2026/seu-negocio/recorde-brasil-registrou-abertura-de-49-milhoes-de-pequenos-negocios-em-2025-confira-os-setores-que-lideraram-cbcb/](https://www.seudinheiro.com/2026/seu-negocio/recorde-brasil-registrou-abertura-de-49-milhoes-de-pequenos-negocios-em-2025-confira-os-setores-que-lideraram-cbcb/)  
> 16. Veja os 10 setores mais escolhidos por quem abriu micro ou, [https\://exame.com/bussola/veja-os-10-setores-mais-escolhidos-por-quem-abriu-micro-ou-pequena-empresa-em-2023/](https://exame.com/bussola/veja-os-10-setores-mais-escolhidos-por-quem-abriu-micro-ou-pequena-empresa-em-2023/)  
> 17. Perguntas Frequentes \- Impulso Stone \| FAQ, [https\://www\.impulsostone.com.br/faq](https://www.impulsostone.com.br/faq)  
> 18. Ocupação principal MEI: lista de atividades 2026 \- iDinheiro, [https\://www\.idinheiro.com.br/negocios/atividades-mei/](https://www.idinheiro.com.br/negocios/atividades-mei/)  
> 19. Atividades Permitidas no MEI em 2027: Lista Completa CNAE, [https\://www\.contaagil.com/contabilidade-digital/atividades-permitidas-no-mei-em-2026-veja-a-lista-completa-e-saiba-se-voce-pode-se-formalizar/](https://www.contaagil.com/contabilidade-digital/atividades-permitidas-no-mei-em-2026-veja-a-lista-completa-e-saiba-se-voce-pode-se-formalizar/)  
> 20. [https\://zvid.io/benchmarks/pricing](https://zvid.io/benchmarks/pricing)  
> 21. Video Editing APIs Compared (2026): Automate at Scale \- Loopdesk, [https\://loopdesk.ai/blog/video-editing-api-comparison](https://loopdesk.ai/blog/video-editing-api-comparison)  
> 22. Epidemic Sound Developer Portal, [https\://developers.epidemicsound.com/](https://developers.epidemicsound.com/)  
> 23. index \| Epidemic Sound API Documentation, [https\://developers.epidemicsound.com/docs/](https://developers.epidemicsound.com/docs/)  
> 24. ElevenLabs pricing 2026: plans, credits, and API \| Cartesia, [https\://www\.cartesia.ai/learn/elevenlabs-pricing](https://www.cartesia.ai/learn/elevenlabs-pricing)  
> 25. Terms of Use — Freesound API documentation, [https\://freesound.org/docs/api/terms\_of\_use.html](https://freesound.org/docs/api/terms_of_use.html)  
> 26. Instagram Audio API \| Meta for Developers \- Facebook, [https\://developers.facebook.com/documentation/instagram-platform/content-publishing/audio-api](https://developers.facebook.com/documentation/instagram-platform/content-publishing/audio-api)  
> 27. About the Commercial Music Library \- TikTok Ads, [https\://ads.tiktok.com/resources/help/article/commercial-music-library?lang=en](https://ads.tiktok.com/resources/help/article/commercial-music-library?lang=en)  
> 28. Pixabay Plans Pricing \- APIs.io, [https\://apis.io/plans/pixabay/pixabay-plans-pricing/](https://apis.io/plans/pixabay/pixabay-plans-pricing/)  
> 29. WhisperX 2026: Word Timestamps \+ Speaker Diarization Guide, [https\://localaimaster.com/blog/whisperx-guide](https://localaimaster.com/blog/whisperx-guide)  
> 30. qwen2.5vl \- Ollama, [https\://ollama.com/library/qwen2.5vl:latest](https://ollama.com/library/qwen2.5vl:latest)  
> 31. Gemini API Free Tier in 2026: Limits, Models, and When You Get, [https\://apidog.com/blog/gemini-api-free-tier/](https://apidog.com/blog/gemini-api-free-tier/)  
> 32. [https\://byoklist.com/guides/groq-api-key](https://byoklist.com/guides/groq-api-key)  
> 33. Introducing the Model Context Protocol \- Anthropic, [https\://www\.anthropic.com/news/model-context-protocol](https://www.anthropic.com/news/model-context-protocol)  
> 34. Prompts \- What is the Model Context Protocol (MCP)?, [https\://modelcontextprotocol.io/specification/2025-06-18/server/prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)  
> 35. Resources \- Model Context Protocol, [https\://modelcontextprotocol.io/specification/2025-06-18/server/resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)  
> 36. Overview \- What is the Model Context Protocol (MCP)?, [https\://modelcontextprotocol.io/specification/draft/server](https://modelcontextprotocol.io/specification/draft/server)  
> 37. [https\://benly.ai/learn/ad-creative/video-ad-structure-frameworks](https://benly.ai/learn/ad-creative/video-ad-structure-frameworks)  
> 38. Tools \- What is the Model Context Protocol (MCP)?, [https\://modelcontextprotocol.io/specification/2026-07-28/server/tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)  
> 39. pysubs2 — pysubs2 1.9.0 documentation, [https\://pysubs2.readthedocs.io/](https://pysubs2.readthedocs.io/)  
> 40. Best Video Editing MCP Servers in 2026: Compared \- Reap, [https\://reap.video/blog/video-editing-mcp-servers](https://reap.video/blog/video-editing-mcp-servers)  
> 41. PySceneDetect: Home, [https\://www\.scenedetect.com/](https://www.scenedetect.com/)  
> 42. faster-whisper \- PyPI, [https\://pypi.org/project/faster-whisper/](https://pypi.org/project/faster-whisper/)  
> 43. [https\://github.com/kamilstanuch/Autocrop-vertical](https://github.com/kamilstanuch/Autocrop-vertical)  
> 44. Gemini API Free Tier in 2026: What Is Free and What to Check, [https\://www\.aifreeapi.com/en/posts/google-gemini-api-free-tier](https://www.aifreeapi.com/en/posts/google-gemini-api-free-tier)  
> 45. Groq Pricing (2026): Free Tier and API Costs \- Omid Saffari, [https\://omidsaffari.com/blog/groq-pricing](https://omidsaffari.com/blog/groq-pricing)  
> 46. Hugging Face ZeroGPU Alternatives for Gradio Demos \- Cerebrium, [https\://cerebrium.ai/resources/hugging-face-zerogpu-alternatives-gradio-serverless-gpu](https://cerebrium.ai/resources/hugging-face-zerogpu-alternatives-gradio-serverless-gpu)  
> 47. How to get a free Pixabay API key, [https\://publicapis.io/pixabay-api](https://publicapis.io/pixabay-api)  
> 48. Gemini API Pricing and Quotas: Complete 2026 Guide with Cost, [https\://www\.aifreeapi.com/en/posts/gemini-api-pricing-and-quotas](https://www.aifreeapi.com/en/posts/gemini-api-pricing-and-quotas)  
> 49. Dynamic Absolute Time Enhancement for Long Video Understanding, [https\://arxiv.org/html/2509.09263v1](https://arxiv.org/html/2509.09263v1)  
> 50. Rate limits \- Gemini API \| Google AI Studio, [https\://aistudio.google.com/docs/rate-limits](https://aistudio.google.com/docs/rate-limits)  
> 51. GitHub \- 3manifold/whisperX-silero-vad, [https\://github.com/3manifold/whisperX-silero-vad](https://github.com/3manifold/whisperX-silero-vad)  
> 52. edge-tts \- PyPI, [https\://pypi.org/project/edge-tts/](https://pypi.org/project/edge-tts/)  
> 53. ElevenLabs API Pricing Explained: Rates, Free Tier and Limits (2026), [https\://www\.goodvibecode.com/text-to-speech/elevenlabs-api-pricing-explained](https://www.goodvibecode.com/text-to-speech/elevenlabs-api-pricing-explained)  
> 54. Text-to-speech guide for Python \| Google AI Edge, [https\://developers.google.com/edge/mediapipe/solutions/audio/text\_to\_speech/python](https://developers.google.com/edge/mediapipe/solutions/audio/text_to_speech/python)  
> 55. cristianoaredes/kokoro-pt-br \- Hugging Face, [https\://huggingface.co/cristianoaredes/kokoro-pt-br](https://huggingface.co/cristianoaredes/kokoro-pt-br)  
> 56. Groq API Free Tier: Real Rate Limits and Free Models, [https\://localaimaster.com/blog/groq-api-free-guide](https://localaimaster.com/blog/groq-api-free-guide)  
> 57. Hugging Face Spaces \- teach your agent how to create ... \- Github-Gist, [https\://gist.github.com/apolinario/feae34f89fd00278e9ce8f9215190e95](https://gist.github.com/apolinario/feae34f89fd00278e9ce8f9215190e95)  
> 58. LTX Video Fast \- a Hugging Face Space by Lightricks, [https\://huggingface.co/spaces/Lightricks/ltx-video-distilled](https://huggingface.co/spaces/Lightricks/ltx-video-distilled)  
> 59. Depth Anything V2 in Python: Image, Video & Webcam \- Rizwan AI, [https\://www\.rizwanai.com/blog/depth-estimation-with-depth-anything-v2-python](https://www.rizwanai.com/blog/depth-estimation-with-depth-anything-v2-python)  
> 60. Open-Source Beat Detection Models Compared (madmom, BeatNet, [https\://biff.ai/a-rundown-of-open-source-beat-detection-models/](https://biff.ai/a-rundown-of-open-source-beat-detection-models/)  
> 61. Pixabay API \- GitHub, [https\://github.com/dderevjanik/pixabay-api](https://github.com/dderevjanik/pixabay-api)  
> 62. Hugging Face ZeroGPU \- Optimize ML Demos \- Get Claude Skills, [https\://www\.getclaudeskills.com/skills/hugging-face-zerogpu-huggingface](https://www.getclaudeskills.com/skills/hugging-face-zerogpu-huggingface)  
> 63. The Impact of Short-Form Video Consumption on Students' Attention, [https\://www\.researchgate.net/publication/416470871\_The\_Impact\_of\_Short-Form\_Video\_Consumption\_on\_Students'\_Attention\_Span\_and\_Academic\_Engagement](https://www.researchgate.net/publication/416470871_The_Impact_of_Short-Form_Video_Consumption_on_Students'_Attention_Span_and_Academic_Engagement)  
> 64. From Attention to Retention: The Science Behind ... \- alpha.one Blog, [https\://www\.alpha.one/blog/from-attention-to-retention-the-science-behind-retention-and-why-getting-noticed-is-not-enough](https://www.alpha.one/blog/from-attention-to-retention-the-science-behind-retention-and-why-getting-noticed-is-not-enough)  
> 65. Jump Cut Editing Style and Transition Frequency Differentially Affect, [https\://archives.marketing-trends-congress.com/2026/pages/PDF/paper\_professor\_DOST\_HUANG.pdf](https://archives.marketing-trends-congress.com/2026/pages/PDF/paper_professor_DOST_HUANG.pdf)  
> 66. Optimal Short Form Video Length for Retention (2026 Analysis), [https\://www\.bytecap.io/blog/optimal-short-form-video-length-retention-analysis](https://www.bytecap.io/blog/optimal-short-form-video-length-retention-analysis)  
> 67. Swipe, Scroll, Repeat: How Short-Form Video Wins Attention, [https\://dennismfrancis.medium.com/swipe-scroll-repeat-how-short-form-video-wins-attention-36a1800f6caf](https://dennismfrancis.medium.com/swipe-scroll-repeat-how-short-form-video-wins-attention-36a1800f6caf)  
> 68. Creative best practices for performance ads \- TikTok Ads, [https\://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en](https://ads.tiktok.com/resources/help/article/creative-best-practices?lang=en)  
> 69. Video Ad Hook Rate and Hold Rate Benchmarks \- Increditors, [https\://increditors.com/video-ad-hook-hold-benchmarks/](https://increditors.com/video-ad-hook-hold-benchmarks/)  
> 70. PySceneDetect/scenedetect/detectors/adaptive\_detector.py at main, [https\://github.com/Breakthrough/PySceneDetect/blob/main/scenedetect/detectors/adaptive\_detector.py](https://github.com/Breakthrough/PySceneDetect/blob/main/scenedetect/detectors/adaptive_detector.py)  
> 71. scenedetect \- PyPI, [https\://pypi.org/project/scenedetect/](https://pypi.org/project/scenedetect/)  
> 72. Building a shot-detection worker for an upload pipeline with, [https\://dev.to/masonwritescode/building-a-shot-detection-worker-for-an-upload-pipeline-with-pyscenedetect-07-21n6](https://dev.to/masonwritescode/building-a-shot-detection-worker-for-an-upload-pipeline-with-pyscenedetect-07-21n6)  
> 73. Python API \- PySceneDetect, [https\://www\.scenedetect.com/api/](https://www.scenedetect.com/api/)  
> 74. Real-Time Face Landmark Detection in Python \- YouTube, [https\://www\.youtube.com/watch?v=loEZnF7Z-Zk](https://www.youtube.com/watch?v=loEZnF7Z-Zk)  
> 75. tabela CNAE MEI e atividades permitidas em 2026 \- Contabilizei, [https\://www\.contabilizei.com.br/contabilidade-online/atividades-mei-tabela/](https://www.contabilizei.com.br/contabilidade-online/atividades-mei-tabela/)  
> 76. [https\://www\.developersdigest.tech/models/video-generation/fal](https://www.developersdigest.tech/models/video-generation/fal)  
> 77. DepthAnything/Video-Depth-Anything: \[CVPR 2025 ... \- GitHub, [https\://github.com/DepthAnything/Video-Depth-Anything](https://github.com/DepthAnything/Video-Depth-Anything)  
> 78. Spaces ZeroGPU: Dynamic GPU Allocation for Spaces \- Hugging Face, [https\://huggingface.co/docs/hub/spaces-zerogpu](https://huggingface.co/docs/hub/spaces-zerogpu)  
> 79. Tired of waiting 10 minutes per video on Wan 2.2? My Space does it, [https\://www\.reddit.com/r/huggingface/comments/1svfb93/tired\_of\_waiting\_10\_minutes\_per\_video\_on\_wan\_22/](https://www.reddit.com/r/huggingface/comments/1svfb93/tired_of_waiting_10_minutes_per_video_on_wan_22/)  
> 80. Best Video Editing MCP Servers for AI Agents \- ChatCut, [https\://chatcut.io/blog/best-video-editing-mcp-servers](https://chatcut.io/blog/best-video-editing-mcp-servers)  
> 81. Plainly Pricing 2026 \- Capterra, [https\://www\.capterra.com/p/10026817/Plainly/pricing/](https://www.capterra.com/p/10026817/Plainly/pricing/)  
> 82. Plainly Videos: Details, Pricing, Features, & Integration in 2026, [https\://www\.softwaresuggest.com/plainly](https://www.softwaresuggest.com/plainly)  
> 83. Pricing \| Editframe, [https\://editframe.com/pricing](https://editframe.com/pricing)  
> 84. The Best MCP Servers for Video Editing in 2026 (Claude, ChatGPT, [https\://www\.tella.com/blog/best-mcp-servers-for-video-editing](https://www.tella.com/blog/best-mcp-servers-for-video-editing)  
> 85. Remove Silence and Jump Cut Video With Claude \- Sprites.ai, [https\://www\.sprites.ai/claude-video-editing/remove-silence](https://www.sprites.ai/claude-video-editing/remove-silence)  
> 86. Trim Silence From Video Automatically with FFmpeg (API), [https\://www\.ffmpeg-micro.com/blog/trim-silence-from-video-automatically-with-ffmpeg-api](https://www.ffmpeg-micro.com/blog/trim-silence-from-video-automatically-with-ffmpeg-api)  
> 87. auto-editor \- PyPI, [https\://pypi.org/project/auto-editor/](https://pypi.org/project/auto-editor/)  
> 88. Using jumpcutter to trim silence from videos \- Github-Gist, [https\://gist.github.com/esa1975/46ca1151f2a2ee2725aa20b61fe3e67a](https://gist.github.com/esa1975/46ca1151f2a2ee2725aa20b61fe3e67a)  
> 89. librosa — librosa 1.0.0 documentation, [https\://librosa.org/](https://librosa.org/)  
> 90. Essentia Python examples, [https\://essentia.upf.edu/python\_examples.html](https://essentia.upf.edu/python_examples.html)  
> 91. madmom: A New Python Audio and Music Signal Processing Library, [https\://www\.researchgate.net/publication/308841812\_madmom\_A\_New\_Python\_Audio\_and\_Music\_Signal\_Processing\_Library](https://www.researchgate.net/publication/308841812_madmom_A_New_Python_Audio_and_Music_Signal_Processing_Library)  
> 92. Essentia Python examples, [https\://essentia.upf.edu/essentia\_python\_examples.html](https://essentia.upf.edu/essentia_python_examples.html)  
> 93. GitHub \- moonlitmarigold/SubtitleFX: Easy Python Tool to Style and, [https\://github.com/kalterBebapKacke/SubTextHighlight](https://github.com/kalterBebapKacke/SubTextHighlight)  
> 94. Try the Epidemic Sound API Free tier, [https\://www\.epidemicsound.com/blog/free-api/](https://www.epidemicsound.com/blog/free-api/)  
> 95. Music API for Platforms & Products \- Soundstripe, [https\://www\.soundstripe.com/api](https://www.soundstripe.com/api)  
> 96. Soundcharts Pricing \| Plans for Artists, Teams & API Access, [https\://soundcharts.com/en/pricing/dashboard](https://soundcharts.com/en/pricing/dashboard)  
> 97. Pricing \- Soundcharts API, [https\://developers.soundcharts.com/pricing](https://developers.soundcharts.com/pricing)  
> 98. Getting started \- Soundcharts API, [https\://developers.soundcharts.com/api/getting-started](https://developers.soundcharts.com/api/getting-started)  
> 99. Pricing \| Chartmetric, [https\://chartmetric.com/pricing](https://chartmetric.com/pricing)  
> 100. Chartmetric API, Build on Music Data, [https\://chartmetric.com/plans/api](https://chartmetric.com/plans/api)  
> 101. TikTok Trending Songs & Sounds API \| Daily Charts API \- Apify, [https\://apify.com/trendingtiktoksongs/tiktok-trending-sounds-history/api](https://apify.com/trendingtiktoksongs/tiktok-trending-sounds-history/api)  
> 102. How Music Licensing Is Priced for Platforms \- Soundstripe, [https\://www\.soundstripe.com/blogs/how-music-licensing-is-priced-for-platforms](https://www.soundstripe.com/blogs/how-music-licensing-is-priced-for-platforms)  
> 103. Help \- Frequently Asked Questions \- Freesound, [https\://freesound.org/help/faq/](https://freesound.org/help/faq/)  
> 104. An Introduction to Freesound \- Creative Commons Open Source, [https\://opensource.creativecommons.org/blog/entries/freesound-intro/](https://opensource.creativecommons.org/blog/entries/freesound-intro/)  
> 105. Quick connect guide \- Integrate Pixabay with Webflow, [https\://webflow.com/integrations/pixabay](https://webflow.com/integrations/pixabay)  
> 106. Pixabay Music and Sound Effects Alternatives in 2026 (Licenses, [https\://sonilo.com/blog/comparisons/pixabay-music-sound-effects-alternatives-2026](https://sonilo.com/blog/comparisons/pixabay-music-sound-effects-alternatives-2026)  
> 107. Pixabay API \- Documentation & Integration \- API Tracker, [https\://apitracker.io/a/pixabay](https://apitracker.io/a/pixabay)  
> 108. Instagram API for scheduling posts, Reels, Stories, and carousels, [https\://bundle.social/instagram-api](https://bundle.social/instagram-api)  
> 109. Get the music list \| TikTok API for Business, [https\://business-api.tiktok.com/portal/docs/get-the-music-list/v1.3](https://business-api.tiktok.com/portal/docs/get-the-music-list/v1.3)  
> 110. TikTok Commercial Music Library API \- bundle.social, [https\://bundle.social/tiktok-commercial-music-library](https://bundle.social/tiktok-commercial-music-library)  
> 111. TikTok Music Library for Creators and Brands (2026) \- Soundstripe, [https\://www\.soundstripe.com/blogs/tiktok-music-library-explained](https://www.soundstripe.com/blogs/tiktok-music-library-explained)  
> 112. TikTok Trending Sounds: How to Find and Use Them Legally, [https\://www\.zolyp.com/blog/tiktok-trending-sounds](https://www.zolyp.com/blog/tiktok-trending-sounds)  
> 113. Perfil dos pequenos negócios no Brasil \| ASN Nacional, [https\://agenciasebrae.com.br/dados/perfil-dos-pequenos-negocios-no-brasil/](https://agenciasebrae.com.br/dados/perfil-dos-pequenos-negocios-no-brasil/)  
> 114. TikTok's 3-Second Rule: Why the Algorithm Kills Most Videos Before, [https\://www\.launchpointhq.com/blog/ugc-influencer-report](https://www.launchpointhq.com/blog/ugc-influencer-report)  
> 115. Gemini API Free Tier 2026: Limits, Free Models, and Free API Keys, [https\://archive.org/download/cloudz\_202610/gemini-api-free-tier-api-keys.pdf](https://archive.org/download/cloudz_202610/gemini-api-free-tier-api-keys.pdf)












