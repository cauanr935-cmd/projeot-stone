# Dependências humanas — Impulso Stone Reels MCP

> **Nada aqui bloqueia o build.** Os agentes constroem e testam o projeto
> inteiro sem nenhuma chave, conta ou download manual — cada item abaixo tem
> fallback local ativo. Estes itens **melhoram a qualidade**, **aceleram** ou
> exigem **decisão jurídica/de negócio** que só uma pessoa pode tomar.
>
> Como usar: faça o que quiser da lista, depois rode
> `python -m src.core.doctor --write-report` — a seção automática no fim
> deste arquivo mostra o que já foi resolvido.

**Ordem sugerida (maior ganho por minuto):**
1. `GROQ_API_KEY` (transcrição e roteiro melhores, 5 min, sem cartão).
2. Revisões jurídicas da seção 3 (antes de qualquer Reel ir ao ar).
3. Ollama + modelos (seção 2) se a máquina tiver ≥ 16 GB de RAM.
4. Demais chaves só se você sentir falta.

---

## 1. Chaves de API gratuitas (OPCIONAL — padrão “Bring Your Own Free Key”)

Copie `.env.example` para `.env` e preencha só o que tiver. Limites abaixo
são os citados na pesquisa (out–nov/2026) e **podem ter mudado** — confira
no console de cada provedor.

| Variável | Onde obter | Passo a passo | Para que serve | Limite gratuito (pesquisa) | Se ficar vazia (fallback) | Cuidado |
|---|---|---|---|---|---|---|
| `GROQ_API_KEY` | https://console.groq.com/keys | Criar conta → API Keys → Create | ASR `whisper-large-v3-turbo` (Tier 1) e LLM de roteiro | 2.000 req/dia; 28.800 s de áudio/dia; 8.000 TPM no LLM | WhisperX/faster-whisper local + templates/Ollama | — |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey | Login Google → Get API key → criar em projeto | Análise multimodal de vídeo e roteiro | Quota **por projeto** (zera 00:00 PT); várias chaves no mesmo projeto não somam | Ollama `qwen2.5vl` / heurística | **O free tier usa os dados para treino.** O router bloqueia este provedor para mídia do MEI automaticamente. |
| `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | https://dash.cloudflare.com/profile/api-tokens | Create Token → modelo “Workers AI” → copiar; Account ID aparece na home do dashboard | Tier 2 de ASR, TTS (MeloTTS) e visão | 10.000 Neurons/dia (zera 00:00 UTC) | Tier local | — |
| `PIXABAY_API_KEY` | https://pixabay.com/api/docs/ | Login → a chave aparece na própria página da documentação | Música/SFX com licença comercial | 100 req/min, cache obrigatório de 24 h | Biblioteca `assets/audio_cc0/` + trilha procedural | Ver item J3: confirmar se a API pública cobre música. |
| `HF_TOKEN` | https://huggingface.co/settings/tokens | New token (read) | B-roll generativo no ZeroGPU (também exige `REELS_ENABLE_ZEROGPU=1`) | 300 s de GPU/dia (conta free) | Paralaxe 2.5D local | Nunca usado para foto de produto. |
| `MISTRAL_API_KEY` | https://console.mistral.ai/api-keys | Plano gratuito “Experiment” → criar chave | LLM para prompts longos | 2 RPM; 500K TPM | Ollama / templates | Política de dados do plano free: confirmar (tratado como sensível-bloqueado até lá). |
| `CEREBRAS_API_KEY` | https://cloud.cerebras.ai | Criar conta → API Keys | LLM rápido | 5 RPM; 1M tokens/dia | Ollama / templates | Idem. |
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys | Create key | Modelos `:free` | 50 req/dia sem créditos | Ollama / templates | Idem. |
| `NVIDIA_API_KEY` | https://build.nvidia.com | Login → Get API Key em qualquer modelo | VLM Tier 2 | 40 RPM (pesquisa) | Ollama / heurística | Idem. |

Nenhuma conta de rede social é necessária para gerar o `.mp4`.

---

## 2. Provisionamento local (RECOMENDADO — os agentes tentam sozinhos e registram o resultado)

| Item | Por que | Como (humano) | O que os agentes fazem sem você |
|---|---|---|---|
| **ffmpeg + ffprobe com libx264 e libass** | Render e legendas `.ass` | Linux: `sudo apt-get install -y ffmpeg` · macOS: `brew install ffmpeg` · Windows: `winget install Gyan.FFmpeg` | Usam o pacote `static-ffmpeg` (baixa binários completos) |
| **Python 3.11 ou 3.12** | Wheels de ML (torch, mediapipe) | `uv python install 3.12` ou instalador oficial | Tentam `uv`; com 3.13 seguem com aviso |
| **Fonte Montserrat ExtraBold** (SIL OFL) | Estilo de legenda fiel ao spec | Baixar em fonts.google.com/specimen/Montserrat e instalar | Tentam baixar para `assets/fonts/`; senão DejaVu Sans Bold |
| **Ollama** + `ollama pull llama3.2` e `ollama pull qwen2.5vl` | LLM/VLM local de qualidade (Tier 3) | https://ollama.com/download | Detectam; sem Ollama usam templates/heurística |
| **Voz Piper `pt_BR-faber-medium`** (`.onnx` + `.onnx.json`) | TTS offline natural | Baixar de `rhasspy/piper-voices` no Hugging Face para `models/piper/` | Tentam baixar; senão Kokoro → espeak-ng |
| **espeak-ng** | TTS offline mínimo | `sudo apt-get install -y espeak-ng` | Tentam via apt |
| **GPU NVIDIA + CUDA** (opcional) | WhisperX `large-v3` e profundidade mais rápidos | Drivers + `HAS_CUDA=1` no `.env` | CPU com modelos menores |

---

## 3. Revisões jurídicas (JURÍDICO — só uma pessoa pode decidir)

| ID | Questão | Por que importa | Estado padrão no código |
|---|---|---|---|
| J1 | **edge-tts em uso comercial**: a biblioteca usa um endpoint não documentado do Microsoft Edge; não há concessão explícita de uso comercial. | A pesquisa trata como “comercialmente seguro”; a Stone deve confirmar antes de impulsionar Reels com essa voz. | Liberado com aviso (`review`). Para bloquear: mude `edge-tts` para `commercial_ok: false` em `config/licenses.yaml`. |
| J2 | **Licença da voz Piper `pt_BR-faber-medium`** (pesquisa diz CC0). | Cada voz Piper tem licença própria no MODEL_CARD. | `review` até confirmação. |
| J3 | **Pixabay para música**: a documentação pública da API cobre imagens e vídeos; confirmar se há endpoint oficial de música e as regras de Content ID. | A pesquisa pressupõe música via API. | Tier marcado `unverified`; trilha procedural/CC0 é usada. |
| J4 | **AGPL (Ultralytics YOLOv11, Essentia)**: aceitar obrigações AGPL num serviço da Stone? | Rastreamento de sujeito melhor vs. obrigação de abrir código. | Desligado (`REELS_ALLOW_AGPL=0`). |
| J5 | **Llama 3.2 Community License** (Ollama local). | Licença condicional. | `review`. |
| J6 | **Distribuição empacotada com FFmpeg GPL (libx264)**. | Uso interno OK; distribuir binários exige conformidade GPL/LGPL. | Uso local apenas. |
| J7 | **LGPD — imagem de terceiros**: vídeos do MEI podem mostrar clientes (rostos, voz, placas). | Publicação exige consentimento; processamento em nuvem amplia o risco. | Mídia tratada como sensível; nunca vai para provedor que treina com dados. Consentimento é responsabilidade do MEI/Stone. |
| J8 | **Gemini free tier**: a Stone permite usar com *qualquer* dado (mesmo não sensível)? | Política de dados do programa. | Permitido só para texto não sensível. Para proibir de vez: remova `GEMINI_API_KEY`. |

---

## 4. Validações de negócio (RECOMENDADO)

| ID | O que validar | Onde |
|---|---|---|
| N1 | Lista de CNAEs × formatos (a pesquisa usa `4321-5/01`; a subclasse oficial é `4321-5/00`, mantida como alias). Conferir contra a tabela CNAE/IBGE e as ocupações MEI do Portal do Empreendedor. | `config/cnae_profiles.yaml` |
| N2 | Roteiros padrão PT-BR (tom Impulso Stone: próximo, acolhedor, sem promessas exageradas). | `config/script_templates.yaml` |
| N3 | Durações, vozes e frequências de corte por formato (marcados `DEFAULT-SPEC` onde a pesquisa não definia). | `config/formats.yaml` |
| N4 | Revisão humana de uma amostra de Reels antes de publicar (o sistema não publica nada). | `output/` |

---

## 5. Pendências registradas pelos agentes

| ID | Prioridade | Spec | O que o humano precisa fazer | Por quê / impacto se não fizer | Fallback ativo hoje | Como verificar depois |
|---|---|---|---|---|---|---|
| H-CASE-01 | JURÍDICO | Case | Confirmar com a organização do case (Stone/Inteli) que a coleta de Reels via actors do Apify é a rota de extração combinada no kickoff de 26/10/2026 e que o uso da mídia baixada é só para análise interna | O TAPI coloca fora do escopo qualquer scraping que viole os Termos de Serviço das plataformas | Base já coletada; mídia não é versionada nem redistribuída | Resposta registrada em `docs/base_de_dados.md` §1 |
| H-CASE-02 | OPCIONAL | Case | Aumentar o crédito do Apify (ou aguardar a renovação mensal em 17/12/2026; a conta atual renova em 17/12/2026) para ampliar a base de 1.843 para 2.000+ Reels (o lote 4 já consumiu o crédito do ciclo; saldo ~US$ 0,18) e cobrir perfis truncados | A meta do TAPI é 2.000–5.000 publicações; o teto de US$ 5/mês limitou o volume | Análises com `confidence_flag` para suportes baixos | `python -m src.base.unificar` e conferir `docs/base_de_dados.md` §2 |
| H-CASE-03 | RECOMENDADO | Case | Expandir a base de vídeos (token Creator da Graph API `business_discovery`, ou cookies de sessão para yt-dlp/gallery-dl, ou renovação do Apify em 17/12/2026) e rodar `python -m src.analise.manifesto && python -m src.analise.features && python -m src.analise.classificar` | A análise fecha com 1.843 Reels (abaixo da meta de 2.000) | Análise do top 10% sobre os 168 vídeos já em disco | `python -m src.base.unificar` e conferir `docs/base_de_dados.md` §2 |
| legal-kokoro-phonemizer | JURÍDICO | 02 | Revisar a licença GPL de `phonemizer`/`espeak-ng` (dependências do `kokoro-onnx`) antes de distribuir o pacote | O áudio gerado não herda a licença, mas a redistribuição do código pode | Kokoro roda localmente; edge-tts desligado por padrão | Parecer registrado no ADR-010 |
| H-CASE-04 | JURÍDICO | Case | Enviar à organização a minuta de confirmação em `docs/COMPLIANCE_H_CASE_01.md` | Registro formal exigido pelo TAPI | Dossiê técnico pronto | Resposta anexada ao ADR-009 |

---

## 6. Estado do ambiente (seção automática — gerada pelo `doctor`)

<!-- AUTO:BEGIN -->

### Itens detectados automaticamente

| ID | Prioridade | Spec | Ação | Impacto | Fallback | Verificação |
|---|---|---:|---|---|---|---|
<!-- AUTO:END -->
