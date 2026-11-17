# ADR-006 — Licenças de pesos e bibliotecas (AGPL, CC-BY-NC) e padrões seguros

**Status:** Aceito · **Specs:** 02–05

## Contexto
A pesquisa trata a pilha como “100% open-source e custo zero”, mas parte
dela tem licenças incompatíveis com uso comercial ou com obrigações fortes
para um serviço operado por uma empresa:
- **Ultralytics YOLOv11** — AGPL-3.0 (código e pesos).
- **madmom** — código BSD, mas **modelos pré-treinados CC-BY-NC-SA-4.0**.
- **Essentia** — AGPL-3.0.
- **Depth Anything V2 Base/Large** — CC-BY-NC-4.0 (só o **Small** é Apache-2.0).
- **edge-tts** — biblioteca LGPL-3.0 que usa um endpoint não documentado da
  Microsoft; não há concessão explícita de uso comercial.
- **Piper** — o projeto migrou para `piper1-gpl` (GPL-3.0) e cada voz tem
  licença própria no MODEL_CARD.
- **FFmpeg com libx264** — GPL; ok para uso interno, revisar para distribuição.

## Decisão
- Padrões: MediaPipe/OpenCV Haar/saliência para sujeito; librosa para MIR;
  Depth Anything V2 **Small**; fallback geométrico de profundidade.
- AGPL só com `REELS_ALLOW_AGPL=1` (decisão humana registrada em
  HUMAN_DEPENDENCIES, prioridade JURÍDICO).
- `commercial_ok: review` para edge-tts, voz Piper, Llama 3.2, LTX-Video e
  alinhador wav2vec2 PT até um humano confirmar.
- O agente lê LICENSE/MODEL_CARD ao baixar cada peso e corrige
  `config/licenses.yaml` com registro aqui.

## Consequências
+ Uso comercial pela Stone sem surpresas de licença conhecidas.
− Detecção de sujeito e beat tracking padrão podem ser menos precisos que
  YOLO/madmom.

## Ambiente verificado
- Não foram baixados modelos. Profundidade geométrica e TTS tonal ficam
  restritos a uso de teste; placeholder_tone é bloqueado em render comercial.
- `edge-tts` está disponível como tier de rede, mas permanece em revisão
  jurídica; render comercial registra o aviso.
- FFmpeg local tem libx264/libass; a licença do binário distribuído não faz
  parte deste pacote.

## Atualizações
- 2026-11-07 — implementação: guardrail ativado; nenhum modelo de licença
  não comercial foi provisionado.
