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

---

## Atualização 18/11/2026 — case de análise de Reels para MPEs

- **Base:** 2.715 Reels de 126 perfis após os lotes 5 e 6 (meta do TAPI de 2.000+ e ≥ 30 perfis **atingida**). 2.500 aptos ao ranking;
  250 no top 10% de 82 perfis; 143 de consenso entre `score_relativo` e `taxa_eng`; 1.596 posts excluídos.
- **Análise do top 10%:** 250 vídeos (os novos baixados do cache bruto com `src.analise.baixar_top`); transcrição local (faster-whisper small int8), cortes, frames e rosto;
  classificação nos 5 formatos por regras. Resultado e limitações em `docs/ANALISE_TOP10.md`: nenhum formato se destaca com significância.
  Retrato do top: ~54 s, ~172 palavras/min, ~1,2 corte/min, rosto presente.
- **TTS:** Kokoro-82M local (Apache-2.0) substitui o edge-tts como padrão (ADR-010). Pendência jurídica: GPL do `phonemizer`/espeak-ng.
- **Documentação:** ADR-009 corrigido (1.672, não 776) e ADR-010 novo; dossiê `docs/COMPLIANCE_H_CASE_01.md` com minuta para a organização.
- **Desvios da proposta de custo zero:** expansão feita só com o Apify gratuito (descoberta por hashtag + coleta por perfil, lotes 5–6; US$ ~4,5); detector de rosto YuNet no lugar de Haar; áudio decodificado via ffmpeg por
  incompatibilidade do `av`; `score_relativo_rolling`, Ollama/VLM e sherpa-onnx não implementados.
