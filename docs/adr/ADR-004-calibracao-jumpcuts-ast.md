# ADR-004 — Calibração neuromarketing de jump-cuts (fluência vs. AST) e higiene A/V

**Status:** Aceito · **Specs:** 03, 05

## Contexto
Reter atenção na *Swipe Zone* (0–3 s) e evitar decaimento na *Pacing Slope*
(> 5 s) sem amputar fonemas. Dost & Huang (2026, N=242): cortes *seamless*
elevam Likes em frequência média/alta (0,331/0,517 cortes/s); cortes
*overlapping* elevam conclusão/rewatch em frequência baixa/média
(0,189/0,331), perdendo efeito em 0,517.

## Decisão
- `seamless`: PAD = 0,090 s (preserva ~180 ms, janela AST longa).
- `overlapping`: PAD = 0,015 s (pausa < 40 ms).
- Áudio cortado no milissegundo exato com `afade` de 15 ms; vídeo alinhado
  ao frame com difusão de erro; normalização prévia para CFR.
- Frequência por formato em `config/formats.yaml`; cortes extras (punch-in/
  B-roll) completam a frequência alvo.
- Hook score normativo: `S = 0.35·A + 0.30·F·(1−E) + 0.15·L + 0.20·V` (a
  fórmula original era imagem não recuperável no documento-fonte).
- Legendas: ≤ 4 palavras por evento; ≤ 5 palavras distintas em 0–3 s
  (senão `hook_overlay` + karaoke a partir de 3 s); 5–10 palavras/s é meta
  suave — fala natural PT-BR ≈ 2,5–3,5 palavras/s e a legenda não pode
  correr à frente da fala; teto duro 10 palavras/s (evento ≥ 100 ms).

## Parâmetros calibrados
- Detecção padrão: `silencedetect` a −32 dB por 0,40 s.
- PAD de `formats.yaml`: seamless 90 ms e overlapping 15 ms; fade de 15 ms.
- Cada plano deriva `planned_cuts` arredondando taxa do formato × duração.
- MIR offline usa transientes locais e estima o BPM sem pesos; fallback
  testado para 120 BPM. Ducking RMS reduz música durante voz com envelope
  suavizado.

## Desvios da pesquisa
- Punch-in `scale=1166:2074,crop=1080:1920` exige `setsar=1` antes do
  `concat` (verificado ao montar o pacote).
- Implementação de referência perdia o trecho após o último silêncio.
- A legenda agrupa palavras rápidas para respeitar 100 ms mínimos por evento;
  metas de leitura continuam suaves, conforme o critério operacional.

## Atualizações
- 2026-11-07 — implementação e gates de edição aprovados.
