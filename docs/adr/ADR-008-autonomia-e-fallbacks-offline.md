# ADR-008 — Autonomia do build e fallbacks offline

**Status:** Aceito · **Specs:** 00–07

## Contexto
O projeto é construído por agentes do Claude Code sem intervenção humana.
Qualquer dependência de chave, conta, rede externa ou download manual
pararia o build.

## Decisão
- Cada modalidade termina num tier que não depende de nada externo:
  ASR → `none` (pipeline segue sem transcrição); TTS → espeak-ng →
  `placeholder_tone` (só CI, nunca comercial); LLM → `template_engine`
  (`config/script_templates.yaml`); VLM → `heuristic_only`; música →
  gerador procedural; profundidade → geométrica; sujeito → saliência/centro;
  ffmpeg → `static-ffmpeg`.
- `src/core/doctor.py` descobre o ambiente e reescreve a seção automática
  de `docs/HUMAN_DEPENDENCIES.md`.
- Gates rodam com `REELS_OFFLINE=1` por padrão; testes de aceitação não
  usam rede nem GPU.

## Ambiente de build encontrado
- Python 3.12.3; FFmpeg e ffprobe do sistema resolvidos.
- FFmpeg tem libx264, AAC, libass, ebur128, loudnorm, silencedetect,
  zoompan e sidechaincompress.
- Sem CUDA; PyPI, Hugging Face e GitHub responderam ao probe.
- Ollama está instalado, mas nenhum modelo foi provisionado.
- Sem pesos Piper/Kokoro/Whisper/Depth. Operação offline usa templates,
  áudio tonal de CI, profundidade geométrica, morph determinístico e música
  procedural.
- Não houve download de modelos opcionais.

## Versões resolvidas
MCP 1.30.0; edge-tts 7.3.1; PySceneDetect 0.7.2; librosa 1.0.0;
pysubs2 1.9.1; OpenCV 5.0.0.93. WhisperX, faster-whisper, MediaPipe,
Transformers, Kokoro, Piper e Torch não instalados. Ambiente isolado em
`.venv`; extras `ml` e `agpl` não foram instalados.

## Atualizações
- 2026-11-07 — implementação 00–07; gates de aceitação passaram.
