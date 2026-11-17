# SPEC_00 — Bootstrap do projeto e sondagem de ambiente (`doctor`)

**Objetivo:** deixar o repositório instalável e fazer o agente *descobrir
sozinho* o que o ambiente tem, para escolher tiers e registrar pendências
humanas sem perguntar nada a ninguém.

**Depende de:** nada. **Gate:** `bash scripts/gate.sh 00`.

---

## 1. Entregáveis

### 1.1 Estrutura e empacotamento
- `git init` (se ainda não houver) e commit inicial do pacote de specs.
- `pyproject.toml` (nome `impulso-stone-reels-mcp`, Python `>=3.11,<3.13`)
  com extras:
  - `core`: `mcp>=1.12,<2`, `pydantic>=2`, `pyyaml`, `httpx`, `python-dotenv`,
    `numpy`, `pillow`, `opencv-python-headless`, `scenedetect` (com backend
    OpenCV headless — use o pacote/extra que resolver; a pesquisa cita
    `scenedetect-headless==0.7.2`), `librosa`, `soundfile`, `pysubs2`,
    `edge-tts>=7,<8`, `scikit-image`, `static-ffmpeg` (fallback de binários).
  - `ml` (opcional): `faster-whisper`, `whisperx`, `torch` (CPU por padrão),
    `transformers` (Depth Anything V2 **Small**), `mediapipe`, `kokoro-onnx`,
    `piper-tts`.
  - `agpl` (opcional, desligado): `ultralytics`.
  - `dev`: `pytest`, `pytest-asyncio`, `respx`, `ruff`.
- Ambiente virtual em `.venv` (ou `uv`). Instale `core` + `dev`. **Tente**
  `ml`; para cada pacote que falhar, registre item `RECOMENDADO` em
  `docs/HUMAN_DEPENDENCIES.md` (com o erro resumido) e siga.
- `src/__init__.py` e subpacotes vazios conforme layout do `CLAUDE.md`.
- `pytest.ini` (ou seção no pyproject) com `asyncio_mode = auto` e os
  marcadores `slow`, `network`, `gpu`.

### 1.2 `src/core/config.py`
Carrega e valida (pydantic) os YAML de `config/`. API mínima (testada):
```python
load_formats() -> list[dict]                 # 5 formatos, ordenados por id
get_format(id_or_key: int | str) -> dict     # 1..5 ou "bab", "pas"...
load_cnae_profiles() -> dict
load_providers() -> dict
load_licenses() -> dict
load_script_templates() -> dict
common() -> dict                             # bloco `common` de formats.yaml
```
Erros de schema devem citar arquivo e campo.

### 1.3 `src/core/ffmpeg.py`
- `resolve_binaries() -> dict[str, str]`: procura `ffmpeg`/`ffprobe` no PATH;
  se faltar, tenta `static_ffmpeg.add_paths()`; se ainda faltar, tenta
  `apt-get install -y ffmpeg` (pode falhar sem root — tudo bem).
- `ffprobe_json(path) -> dict`, `run_ffmpeg(args: list[str]) -> CompletedProcess`
  (sem shell, com stderr no erro), `has_filter(name) -> bool`,
  `has_encoder(name) -> bool`.

### 1.4 `src/core/doctor.py` — CLI `python -m src.core.doctor`
Flags: `--json` (imprime JSON no stdout), `--write-report`,
`--docs-dir DIR` (padrão `docs`). Sondagens com timeout curto (≤ 3 s cada;
o total deve rodar em < 60 s):

| Chave JSON | Conteúdo |
|---|---|
| `python` | `{version, ok}` (ok = 3.11 ≤ v < 3.13; 3.13 => ok=true com aviso) |
| `binaries` | `ffmpeg`, `ffprobe`, `espeak-ng`, `piper`, `ollama` → `{ok, path, version}` |
| `ffmpeg_filters` | bools: `libx264`, `aac`, `ass` (libass), `ebur128`, `loudnorm`, `silencedetect`, `zoompan`, `sidechaincompress` |
| `gpu` | `{cuda: bool, name: str|null}` |
| `network` | bools: `pypi`, `huggingface`, `github` (HEAD com timeout) |
| `env_keys` | para cada variável de `.env.example`: **apenas** `true/false` (existência). Nunca valores. |
| `python_packages` | versões instaladas de `mcp`, `edge-tts`, `scenedetect`, `librosa`, `pysubs2`, `opencv`, `whisperx`, `faster-whisper`, `mediapipe`, `transformers`, `kokoro-onnx`, `piper-tts`, `torch` (null se ausente) |
| `models` | bools: `piper_pt_br`, `kokoro`, `depth_anything_v2_small`, `whisper_local`, `ollama_llama3_2`, `ollama_qwen2_5vl` |
| `fonts` | `{montserrat_extrabold: bool, path: str|null, fallback: "DejaVu Sans Bold"}` |
| `engines_effective` | engine que **seria** usado hoje para: `asr`, `tts`, `llm`, `vlm`, `music`, `depth`, `subject_detection` |
| `human_dependencies` | lista de `{id, priority, spec, action, impact, fallback, verify}` derivada das sondagens |

`--write-report`:
- escreve `<docs-dir>/ENVIRONMENT_REPORT.md` (tabelas legíveis do JSON);
- reescreve **somente** o trecho entre `<!-- AUTO:BEGIN -->` e
  `<!-- AUTO:END -->` de `<docs-dir>/HUMAN_DEPENDENCIES.md` com a tabela de
  `human_dependencies` (o resto do arquivo é preservado byte a byte).

Exit code do doctor: `0` se `ffmpeg` e `ffprobe` resolvidos e Python ≥ 3.11;
`1` caso contrário (é o único bloqueio real de ambiente).

### 1.5 Provisionamento automático (best-effort, nunca bloqueante)
O agente **tenta**, nesta ordem, e registra o resultado:
1. Fonte Montserrat ExtraBold (SIL OFL) → `assets/fonts/`:
   `https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf`
   (alternativa: variável em `google/fonts/ofl/montserrat`). Falhou ⇒ usar
   DejaVu Sans Bold e registrar `RECOMENDADO`.
2. Voz Piper `pt_BR-faber-medium` (`.onnx` + `.onnx.json`) do repositório
   `rhasspy/piper-voices` no Hugging Face → `models/piper/`. Leia o
   `MODEL_CARD` e atualize a licença em `config/licenses.yaml` (com ADR).
3. `espeak-ng` via `apt-get` (garante TTS offline mínimo).
4. Pesos `depth-anything/Depth-Anything-V2-Small-hf` (download sob demanda é
   aceitável; aqui só registre se a rede ao HF existe).
5. Ollama: **não** instalar (exige ação de sistema); apenas detectar e
   registrar `OPCIONAL`.

### 1.6 Documentos
- `docs/PROGRESS.md`: atualizar a tabela (já existe) — SPEC_00 DONE ao fim.
- `docs/adr/ADR-008-autonomia-e-fallbacks-offline.md`: completar com o que o
  doctor encontrou neste ambiente e as versões resolvidas.

---

## 2. Métricas de Autoverificação

```bash
bash scripts/gate.sh 00
```
O gate roda `python -m src.core.doctor --json` (exit 0 obrigatório) e
`tests/acceptance/test_spec00_bootstrap.py`, que verifica:
1. JSON do doctor com todas as chaves da tabela 1.4;
   `binaries.ffmpeg.ok` e `binaries.ffprobe.ok` verdadeiros;
   `ffmpeg_filters.libx264` e `ffmpeg_filters.ass` verdadeiros.
2. `env_keys` contém apenas booleanos (nenhum valor de segredo vaza).
3. `--write-report --docs-dir <tmp>` cria `ENVIRONMENT_REPORT.md` e preserva
   o texto fora dos marcadores AUTO.
4. `src.core.config`: 5 formatos com ids 1..5; `get_format("pas")["cut_style"]
   == "overlapping"`; `common()["output"]["width"] == 1080`.
5. `pyproject.toml` declara `mcp` com limite `<2`.

## 3. Armadilhas conhecidas
- `ffmpeg` do sistema sem `libass` não queima legendas `.ass` — o doctor deve
  detectar e o `resolve_binaries` deve preferir o binário do `static-ffmpeg`
  quando o do sistema não tiver `ass`/`libx264`.
- Python 3.13: vários pacotes de ML não têm wheel; prefira 3.11/3.12 se o
  ambiente oferecer (`uv python install 3.12` funciona sem root).
