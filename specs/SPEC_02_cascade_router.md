# SPEC_02 — Motor de Roteamento em Cascata (`ZeroCostCascadeRouter`)

**Objetivo:** camada única de inferência que alterna entre free tiers de
nuvem e motores locais gratuitos, lendo cabeçalhos de rate limit em tempo
real, com cache em disco, circuit breaker de privacidade e guardrail de
licença comercial.

**Depende de:** SPEC_01. **Gate:** `bash scripts/gate.sh 02`.
**Referência:** pesquisa §“Motor de Roteamento Inteligente em Cascata”,
§“Matriz de Cascata por Modalidade” e §“Implementação Prática / 2”.
**Config:** `config/providers.yaml`, `config/licenses.yaml`.

---

## 1. Entregáveis

### 1.1 `src/router/cascade_router.py` — contrato (testado)
```python
class ZeroCostCascadeRouter:
    def __init__(self, *,
                 env: Mapping[str, str] | None = None,          # padrão: os.environ (+ .env via dotenv)
                 http_transport: httpx.AsyncBaseTransport | None = None,  # injeção p/ testes
                 local_engines: dict[str, "LocalEngine"] | None = None,  # "asr","tts","llm","vlm"
                 cache_dir: Path | None = None,                   # padrão: .cache/router
                 offline: bool | None = None,                     # padrão: env REELS_OFFLINE == "1"
                 providers: dict | None = None): ...

    async def transcribe_with_word_timestamps(self, audio_path: Path, lang: str = "pt",
                                              contains_sensitive_data: bool = True) -> dict
    # -> {"engine","tier","provider","segments":[{"start","end","text","words":[{"word","start","end"}]}],
    #     "cache_hit": bool}

    async def synthesize_ptbr_voiceover(self, text: str, output_mp3: Path, output_srt: Path,
                                        voice: str = "pt-BR-FranciscaNeural", rate: str = "+10%") -> dict
    # -> {"engine","tier","audio","subtitles","word_timestamps":[{"word","start","end"}],
    #     "duration_s","cache_hit","license_key","degraded": bool}

    async def complete_text(self, prompt: str, *, system: str | None = None,
                            contains_sensitive_data: bool = False, max_tokens: int = 800,
                            json_mode: bool = False) -> dict
    # -> {"engine","tier","provider","text": str | None,"cache_hit"}   (text None => usar templates)

    async def describe_images(self, image_paths: list[Path], prompt: str,
                              contains_sensitive_data: bool = True) -> dict
    # -> {"engine","tier","provider","text": str | None, "scores": dict | None}

    def status(self) -> dict          # usado pelo Resource stone-quota://router/status
    last_decisions: list[dict]        # [{modality, tier, provider, reason, elapsed_ms}] da última chamada

class CommercialLicenseViolationError(Exception): ...   # re-exportada de license_guard
```
`LocalEngine`: protocolo com `async def run(self, **kwargs) -> dict`. Quando
`local_engines` não é injetado, o router constrói os motores reais do Tier
local (abaixo). **Toda** requisição HTTP do router passa por um único
`httpx.AsyncClient(transport=http_transport)` — inclusive Ollama em
`localhost:11434`.

### 1.2 Regras de cascata
- Ordem por `tier` em `config/providers.yaml`; tiers sem as env vars
  exigidas são pulados (`reason="missing_env"`). `offline=True` pula todos os
  tiers de nuvem.
- **HTTP 429 / RESOURCE_EXHAUSTED / `x-ratelimit-remaining-* == 0`** ⇒ abre o
  circuito daquele provedor até `retry-after` (padrão 60 s) e desce
  imediatamente. O tempo entre receber o 429 e invocar o próximo tier deve
  ser **< 500 ms** (sem `sleep`, sem retry no mesmo provedor).
- Erro de rede/timeout/5xx ⇒ desce (circuito aberto por 30 s).
- **Privacidade:** se `contains_sensitive_data=True`, provedores com
  `trains_on_free_inputs` = `true` **ou** `unknown` são pulados
  (`reason="sensitive_data_blocked"`).
- LLM: prompt estimado > `long_prompt_threshold_tokens` (≈ len/4) ⇒ pula
  provedores com TPM ≤ 8.000.
- ASR: arquivo > `max_file_mb` ⇒ pula Groq (ou divide por VAD — opcional).
- TTS: edge-tts com latência > `edge_tts_latency_budget_s` ⇒ cancela e desce.
- Atualize contadores internos a partir dos headers
  (`x-ratelimit-remaining-requests/tokens`, `retry-after`) e exponha em
  `status()`.

### 1.3 Tiers locais (motores reais)
- **ASR:** `whisperx` (alinhamento wav2vec2 por palavra) → `faster-whisper`
  (`word_timestamps=True`) → `none` (segments vazios + `degraded`, pipeline
  continua). Modelo `small` em CPU, `large-v3` com `HAS_CUDA=1`.
  Quando Groq responder, rodar alinhamento wav2vec2 local **se disponível**
  para corrigir drift (pesquisa); se não, usar os timestamps da Groq.
- **TTS:** edge-tts (nuvem sem chave; respeitar `REELS_OFFLINE`) →
  Cloudflare MeloTTS → Kokoro-82M (`kokoro-onnx`, vozes `pf_dora`/`pm_alex`)
  → Piper (`PIPER_MODEL_PATH`) → `espeak-ng -v pt-br` → `placeholder_tone`
  (só com `REELS_ALLOW_PLACEHOLDER_AUDIO=1`; marca `degraded=True`).
  Sempre entregar `.mp3` (ffmpeg, 48 kHz) **e** `.srt`: com word boundaries
  quando o motor fornece (edge-tts: verifique na versão instalada se é
  preciso `Communicate(..., boundary="WordBoundary")`); senão, estimar
  tempos proporcionalmente ao número de caracteres sobre a duração medida.
- **LLM:** Ollama (`/v1/chat/completions`) → `template_engine`
  (`text=None`; quem chama usa `config/script_templates.yaml`).
- **VLM:** Ollama `qwen2.5vl` → `heuristic_only` (`text=None`).

### 1.4 `src/router/cache.py`
Cache em disco SHA-256 (chave = modalidade + provedor + modelo + parâmetros
normalizados + digest do conteúdo de entrada). TTL mínimo 24 h (respostas de
TTS, ASR, Pixabay). Escrita atômica (arquivo temporário + rename). Segunda
chamada idêntica de TTS retorna `cache_hit=True` **sem** reprocessar e com
o mesmo áudio (mesmo sha256).

### 1.5 `src/router/license_guard.py`
```python
class CommercialLicenseViolationError(Exception): ...
class UnknownLicenseError(CommercialLicenseViolationError): ...
def validate_commercial_sources(sources: Iterable[str], *, commercial: bool = True,
                                env: Mapping[str, str] | None = None) -> list[str]:
    """Retorna avisos (itens 'review'). Levanta erro para commercial_ok=false,
    'agpl' sem REELS_ALLOW_AGPL=1, e fonte desconhecida (fail-closed) quando commercial=True."""
```
Todo motor/ativo usado num render registra sua `license_key`; o render
(SPEC_07) chama este validador antes de executar o ffmpeg.

### 1.6 Integração MCP
- `stone-quota://router/status` passa a devolver `router.status()`.
- Nova tool `get_router_status`.
- Instância do router criada sob demanda (lazy) — o servidor não pode
  depender de rede para subir.

---

## 2. Métricas de Autoverificação

```bash
bash scripts/gate.sh 02
```
`tests/acceptance/test_spec02_router.py`:
1. **429 → local < 500 ms:** `env={"GROQ_API_KEY": "test"}`, `offline=False`,
   transporte mock devolvendo 429 `RESOURCE_EXHAUSTED` com
   `x-ratelimit-remaining-requests: 0` e `retry-after: 30`; ASR local
   injetado (fake). Mede o tempo entre a resposta 429 e a chamada ao fake:
   < 500 ms. Segunda transcrição (outro arquivo) **não** chama a Groq de novo
   (circuito aberto).
2. **TTS real + cache:** `synthesize_ptbr_voiceover` gera `.mp3` (stream de
   áudio com duração > 0,5 s no ffprobe) e `.srt` (≥ 1 evento no
   `pysubs2.load`); 2ª chamada idêntica ⇒ `cache_hit=True` e mesmo sha256.
3. **Guardrail:** `freesound`, `elevenlabs-free`, `epidemicsound-free` ⇒
   `CommercialLicenseViolationError`; `ultralytics-yolo11` levanta sem
   `REELS_ALLOW_AGPL` e passa com ele; `edge-tts` passa com aviso; fonte
   desconhecida levanta; `commercial=False` não levanta.
4. **Privacidade:** com `GEMINI_API_KEY` definida, `complete_text(...,
   contains_sensitive_data=True)` não faz nenhuma requisição ao host do
   Gemini; com `False`, faz e usa a resposta.

## 3. Armadilhas conhecidas
- Não use `asyncio.sleep(retry_after)` antes de descer a cascata.
- O código de referência da pesquisa engole exceções com `pass` — logue o
  motivo (`last_decisions`) em vez disso.
- Nomes de modelos de nuvem na pesquisa (ex.: `qwen/qwen3.8-27b`,
  `gemini-3.8-flash`) podem não existir: o router tenta a lista em ordem e
  registra o primeiro que funcionar.
