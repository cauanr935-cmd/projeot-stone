# Relatório final — Impulso Stone Reels MCP

**Data:** 2026-11-07  
**Resultado:** implementação funcional das specs 00–07; gates de aceitação
passaram em Python 3.12.3, sem modelos de ML e sem chave de API.

## Entregue

- Pacote Python instalável com extras `core`, `ml`, `agpl` e `dev`.
- Doctor, carregamento de configurações, Roots, servidor FastMCP com
  Resources/Prompts/Tools, perfil CNAE e guardrail de licenças.
- Gerador idempotente de vídeo VFR e fotos de teste sintéticas.
- Cascata com acesso opcional Groq/Gemini limitado por privacidade, cache,
  Edge TTS quando online e fallback tonal determinístico para CI/offline.
- Pipeline CFR/cenas/reframe/hook; animação 2.5D e morph local; jump-cuts,
  batidas, música procedural, ducking e legendas ASS.
- Diretor de cinco formatos e CLI end-to-end. O render compõe os segmentos
  do plano, alterna vídeos/fotos conforme os assets e audita H.264/AAC,
  resolução, CFR, duração, loudness e frames.
- Configuração `.mcp.json`, guia de uso e sondagem de ambiente.

## Validação executada

| Comando | Resultado |
|---|---:|
| `bash scripts/gate.sh 00` | PASS |
| `bash scripts/gate.sh 01` | PASS |
| `bash scripts/gate.sh 02` | PASS |
| `bash scripts/gate.sh 03` | PASS |
| `bash scripts/gate.sh 04` | PASS |
| `bash scripts/gate.sh 05` | PASS |
| `bash scripts/gate.sh 06` | PASS |
| `bash scripts/gate.sh 07` | PASS — 53 testes |
| `bash scripts/gate.sh all` | PASS |

O ambiente reportado tem Python 3.12.3, FFmpeg/ffprobe com os filtros e
encoders requeridos, sem CUDA. O ambiente virtual contém MCP 1.30.0,
edge-tts 7.3.1, PySceneDetect 0.7.2, librosa 1.0.0, pysubs2 1.9.1 e
OpenCV 5.0.0.93. WhisperX, faster-whisper, MediaPipe, Transformers, Kokoro e
Piper não foram instalados; nenhum modelo pesado foi baixado.

## Ressalvas operacionais

- Em `REELS_OFFLINE=1`, o TTS tonal é somente fallback de teste; o guardrail
  impede uso comercial. A publicação requer voz comercialmente autorizada.
- Edge TTS é marcado para revisão jurídica. Consulte as pendências humanas
  antes de publicar.
- O morfador local usa interpolação determinística entre imagens, enquanto
  modelos/pesos de fluxo óptico e profundidade permanecem opcionais.
- Os clipes gerados são artefatos de aceitação, não materiais promocionais
  aprovados pela Stone. Revise direitos de imagem/voz e o resultado final.
