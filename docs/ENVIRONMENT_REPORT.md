# Relatório do ambiente

- Python: 3.12.3
- Engines efetivos: `{"asr": "faster_whisper", "tts": "kokoro", "llm": "template_engine", "vlm": "heuristic_only", "music": "procedural_generator", "depth": "geometric", "subject_detection": "opencv_saliency"}`

## Binários

| Binário | Disponível | Caminho |
|---|---:|---|
| espeak-ng | não | — |
| piper | não | — |
| ollama | sim | /usr/local/bin/ollama |
| ffmpeg | sim | /usr/bin/ffmpeg |
| ffprobe | sim | /usr/bin/ffprobe |

## Filtros FFmpeg

| Filtro/encoder | Disponível |
|---|---:|
| libx264 | sim |
| aac | sim |
| ass | sim |
| ebur128 | sim |
| loudnorm | sim |
| silencedetect | sim |
| zoompan | sim |
| sidechaincompress | sim |

## Pacotes Python

| Pacote | Versão |
|---|---|
| mcp | 1.30.0 |
| edge-tts | 7.3.1 |
| scenedetect | 0.7.2 |
| librosa | 1.0.0 |
| pysubs2 | 1.9.1 |
| opencv | 5.0.0.93 |
| whisperx | ausente |
| faster-whisper | 1.2.1 |
| mediapipe | ausente |
| transformers | ausente |
| kokoro-onnx | 0.6.1 |
| piper-tts | ausente |
| torch | ausente |
