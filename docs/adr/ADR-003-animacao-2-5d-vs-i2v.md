# ADR-003 — Animação determinística 2.5D local vs. vídeo generativo (I2V)

**Status:** Aceito (base da pesquisa) · **Spec:** 04

## Contexto
APIs comerciais de vídeo generativo cobram por segundo (US$ 0,015–0,42/s na
pesquisa) e modelos de difusão re-sintetizam pixels, deformando logotipos,
rótulos e texturas de produtos reais (bolos, roupas, peças).

## Decisão
Pipeline local 2.5D: profundidade monocular (Depth Anything V2 **Small**, ou
fallback geométrico) + paralaxe com PIVOT_CENTER_BOX de deslocamento zero;
para N ≥ 2 fotos, interpolação por OpenCV DIS Optical Flow + *handheld
sway*. ZeroGPU (I2V) só para B-roll atmosférico, opt-in, nunca para o
produto.

## Consequências
+ Custo zero e deformação zero verificável (SSIM ≥ 0,90 no pivô).
− Movimento limitado a paralaxe/órbita curta; sem “ação” sintetizada.

## Parâmetros calibrados
- `PARALLAX_STRENGTH`: 6 (sem halos) a 16; formato 2 = 10.
_(preencher na SPEC_04: SSIM medido, motor de profundidade usado, tempo por clipe)_

## Desvios da pesquisa
_(preencher)_

## Atualizações
- 2026-11-07 — pacote de specs: proibido zoom global sobre o pivô (derruba SSIM).
