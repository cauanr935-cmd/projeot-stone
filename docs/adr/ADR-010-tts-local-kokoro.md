# ADR-010 — TTS local Kokoro-82M no lugar do edge-tts

**Status:** Aceito · **Spec:** 02 · **Data:** 2026-11-18

## Decisão
- Ordem do roteador de TTS: **Kokoro-82M local** (`kokoro-onnx` 0.6.1, pesos Apache-2.0, vozes pt-BR `pf_dora`/`pm_alex`/`pm_santa`)
  → edge-tts **somente** com `ALLOW_NONCOMMERCIAL_EDGE_TTS=1` e online → placeholder tonal (CI).
- Motivo: o edge-tts usa um endpoint da Microsoft sem direito de uso comercial fora de uma assinatura Azure; o mantenedor da biblioteca
  também desaconselha uso comercial. O Kokoro roda offline, a ~1,3× o tempo real em CPU (4,7 s de áudio em 3,5 s, medido).
- Pesos em `models/kokoro/` (gitignored): `kokoro-v1.0.onnx` (310 MB) e `voices-v1.0.bin` (27 MB).
- As legendas SRT têm tempos **estimados** por frase (o Kokoro não devolve timestamps por palavra).

## Riscos
- `kokoro-onnx` depende de `phonemizer` e `espeakng-loader` (espeak-ng), ambos **GPL**. O áudio gerado não herda a licença do código,
  mas distribuir o pacote junto exige revisão (pendência JURÍDICO `legal-kokoro-phonemizer`).
- `piper-tts` ≥ 1.8 migrou para GPL-3.0; não foi adotado como tier de contingência nesta entrega (sherpa-onnx fica como opção futura).
