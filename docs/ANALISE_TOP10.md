# Análise do top 10% de Reels — padrões e formatos (Fase 5)

**Data:** 18/11/2026 · **Base:** 1.843 Reels de 86 perfis (lote 4 incluído) · **Amostra analisada:** 168 Reels do top 10% (55 perfis), 92 de consenso.

## Achados
- **Nenhum formato se destaca estatisticamente:** os intervalos de confiança (95%, bootstrap da mediana do `score_relativo`) se sobrepõem em todos os pares.
  Com n = 168 e rótulos estimados, a análise descreve o top 10%, não prova que um formato vence outro.
- **Retrato do top 10%:** duração mediana de 57 s, cerca de 166 palavras por minuto e apenas ~1 corte de cena por minuto, em Reels falados e com rosto
  (127 de 168 têm rosto em ≥ 60% dos frames). A 1ª palavra costuma começar em 0 s: o gancho é falado de imediato.
- **Formato dominante:** `ugc_testimonial` (58 Reels, 35%), seguido de BAB (34), PAS (34), AIDA (26) e Product Demo + PAS (16). O rótulo UGC é o mais
  frágil, porque as regras reagem a primeira pessoa ("eu", "minha").
- **Contas grandes** são só 9 dos 168 Reels, então o recorte por porte é praticamente descritivo.

## Limitações
- 19 dos 168 Reels não têm trilha de áudio; a classificação deles usa só a legenda do post (13 Reels ficaram com confiança baixa).
- Os 5 formatos são frameworks de copy; o classificador é um léxico determinístico, sem verdade de campo para validar. O refinamento por LLM local
  (`--ollama`) existe, mas não foi usado nesta rodada.
- `score_relativo` extremo (> 20) é comum no top 10% e puxa as médias; use a mediana e o IQR.
- `score_relativo_rolling` não foi implementado (depende de uma base maior).

## Tabelas

### Top 10% completo (n = 151)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 24 | 15.9 | 14.75 | 114.65 | 41.25 | [10.29; 26.27] | 0.0488 | 20.9 | 168.4 | 0.0 |
| bab | 29 | 19.2 | 20.5 | 53.69 | 52.25 | [12.39; 41.94] | 0.0656 | 62.2 | 175.9 | 1.4 |
| pas | 28 | 18.5 | 21.1 | 100.72 | 38.67 | [13.78; 35.48] | 0.0897 | 54.9 | 174.8 | 0.7 |
| product_demo_pas | 16 | 10.6 | 23.28 | 88.1 | 49.93 | [14.05; 66.55] | 0.073 | 59.9 | 171.7 | 1.5 |
| ugc_testimonial | 54 | 35.8 | 13.67 | 388.62 | 48.15 | [11.51; 30.06] | 0.0713 | 58.7 | 160.4 | 1.8 |

### Núcleo de consenso (n = 80)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 10 | 12.5 | 59.71 | 253.38 | 114.24 | [12.19; 165.87] | 1.55 | 26.1 | 196.2 | 0.0 |
| bab | 16 | 20.0 | 53.05 | 82.22 | 90.9 | [14.25; 102.60] | 0.1106 | 62.6 | 169.1 | 1.2 |
| pas | 17 | 21.2 | 26.82 | 152.41 | 58.54 | [18.05; 76.59] | 0.2923 | 69.1 | 175.7 | 0.0 |
| product_demo_pas | 8 | 10.0 | 56.45 | 150.71 | 94.76 | [8.41; 133.70] | 0.2715 | 60.8 | 208.8 | 1.5 |
| ugc_testimonial | 29 | 36.2 | 49.73 | 704.63 | 125.37 | [13.35; 104.47] | 0.2606 | 48.3 | 176.2 | 1.8 |

### Estratificado por porte da conta

#### grande (n = 9)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 1 | 11.1 | 8.65 | 8.65 | 0.0 | n/d | 0.0177 | 11.8 | 0.0 | 0.0 |
| bab | 1 | 11.1 | 29.64 | 29.64 | 0.0 | n/d | 0.1026 | 224.7 | 173.1 | 0.0 |
| pas | 1 | 11.1 | 21.71 | 21.71 | 0.0 | n/d | 0.0443 | 14.0 | 104.4 | 4.3 |
| ugc_testimonial | 6 | 66.7 | 39.13 | 68.64 | 50.07 | [10.70; 156.09] | 0.0302 | 84.0 | 70.7 | 1.2 |

#### pequena/media (n = 142)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 23 | 16.2 | 16.0 | 119.26 | 43.58 | [11.05; 26.27] | 0.0521 | 24.1 | 169.6 | 0.0 |
| bab | 28 | 19.7 | 18.08 | 54.54 | 53.61 | [12.22; 48.66] | 0.0644 | 61.0 | 176.7 | 1.4 |
| pas | 27 | 19.0 | 20.5 | 103.64 | 38.94 | [12.25; 39.21] | 0.0924 | 57.6 | 175.2 | 0.6 |
| product_demo_pas | 16 | 11.3 | 23.28 | 88.1 | 49.93 | [14.05; 66.55] | 0.073 | 59.9 | 171.7 | 1.5 |
| ugc_testimonial | 48 | 33.8 | 13.55 | 428.62 | 42.89 | [10.79; 28.66] | 0.0767 | 56.6 | 163.0 | 1.8 |


### Estratificado por nicho

#### contabilidade (n = 48)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 12 | 25.0 | 23.53 | 196.79 | 37.93 | [11.90; 53.78] | 0.2485 | 16.3 | 178.5 | 0.2 |
| bab | 6 | 12.5 | 12.59 | 16.55 | 8.81 | [9.13; 27.93] | 0.072 | 40.9 | 183.0 | 0.5 |
| pas | 14 | 29.2 | 20.13 | 28.27 | 20.45 | [10.74; 31.75] | 0.0564 | 55.0 | 170.1 | 0.0 |
| product_demo_pas | 7 | 14.6 | 18.76 | 32.14 | 26.48 | [14.05; 52.99] | 0.0581 | 65.4 | 170.9 | 0.0 |
| ugc_testimonial | 9 | 18.8 | 13.35 | 17.9 | 4.75 | [8.77; 33.90] | 0.0215 | 68.5 | 127.6 | 0.0 |

#### demais (n = 103)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 12 | 11.7 | 11.47 | 32.51 | 20.76 | [8.41; 39.31] | 0.0276 | 27.7 | 160.8 | 0.0 |
| bab | 23 | 22.3 | 25.73 | 63.37 | 71.34 | [12.39; 68.94] | 0.0656 | 83.2 | 174.1 | 1.4 |
| pas | 14 | 13.6 | 23.77 | 173.17 | 60.6 | [11.48; 72.06] | 0.1756 | 50.3 | 192.9 | 2.7 |
| product_demo_pas | 9 | 8.7 | 27.02 | 131.63 | 97.76 | [8.41; 133.70] | 0.1066 | 59.8 | 194.2 | 2.0 |
| ugc_testimonial | 45 | 43.7 | 15.66 | 462.76 | 60.43 | [11.77; 32.36] | 0.098 | 57.3 | 163.2 | 2.5 |
