# Análise do top 10% de Reels — padrões e formatos (Fase 5)

**Data:** 18/11/2026 · **Base:** 2.715 Reels de 126 perfis (lotes 4 a 6 incluídos) · **Amostra analisada:** 250 Reels do top 10% (82 perfis), 143 de consenso.

## Achados
- **Nenhum formato se destaca estatisticamente:** os intervalos de confiança (95%, bootstrap da mediana do `score_relativo`) se sobrepõem em todos os pares.
  Com n = 250 e rótulos estimados, a análise descreve o top 10%, não prova que um formato vence outro.
- **Retrato do top 10%:** duração mediana de 54 s, cerca de 172 palavras por minuto e apenas ~1,2 corte de cena por minuto, em Reels falados e com rosto
  (203 de 250 têm rosto em ≥ 60% dos frames). A 1ª palavra costuma começar em 0 s: o gancho é falado de imediato.
- **Formato dominante:** `ugc_testimonial` (87 Reels, 35%), seguido de BAB (52), PAS (51), AIDA (39) e Product Demo + PAS (21). O rótulo UGC é o mais
  frágil, porque as regras reagem a primeira pessoa ("eu", "minha").
- **Contas grandes** são só 12 dos 250 Reels, então o recorte por porte é praticamente descritivo.

## Limitações
- 25 dos 250 Reels não têm trilha de áudio; a classificação deles usa só a legenda do post (18 Reels ficaram com confiança baixa).
- Os 5 formatos são frameworks de copy; o classificador é um léxico determinístico, sem verdade de campo para validar. O refinamento por LLM local
  (`--ollama`) existe, mas não foi usado nesta rodada.
- `score_relativo` extremo (> 20) é comum no top 10% e puxa as médias; use a mediana e o IQR.
- `score_relativo_rolling` não foi implementado (depende de uma base maior).

## Tabelas

### Top 10% completo (n = 250)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 39 | 15.6 | 22.75 | 97.87 | 49.04 | [13.30; 39.85] | 0.0627 | 16.2 | 160.8 | 0.0 |
| bab | 52 | 20.8 | 32.19 | 294.2 | 91.78 | [15.33; 58.37] | 0.0852 | 70.7 | 171.2 | 1.3 |
| pas | 51 | 20.4 | 26.82 | 282.07 | 84.63 | [18.05; 58.62] | 0.1462 | 57.8 | 174.3 | 0.6 |
| product_demo_pas | 21 | 8.4 | 32.78 | 106.56 | 66.07 | [18.76; 58.52] | 0.1066 | 61.8 | 179.2 | 1.0 |
| ugc_testimonial | 87 | 34.8 | 15.66 | 567.06 | 41.91 | [11.82; 22.40] | 0.0354 | 56.0 | 171.3 | 2.3 |

### Núcleo de consenso (n = 143)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 21 | 14.7 | 37.61 | 157.22 | 114.18 | [17.35; 93.21] | 0.253 | 16.0 | 188.2 | 0.0 |
| bab | 30 | 21.0 | 62.33 | 486.26 | 232.66 | [32.19; 113.59] | 0.1789 | 80.3 | 171.5 | 0.5 |
| pas | 36 | 25.2 | 52.96 | 383.81 | 131.7 | [20.50; 94.56] | 0.3703 | 71.5 | 175.4 | 0.7 |
| product_demo_pas | 16 | 11.2 | 54.72 | 135.23 | 91.1 | [26.16; 111.61] | 0.1924 | 63.6 | 179.6 | 1.0 |
| ugc_testimonial | 40 | 28.0 | 44.64 | 1205.46 | 143.08 | [19.07; 87.24] | 0.2608 | 48.5 | 181.1 | 1.8 |

### Estratificado por porte da conta

### grande (n = 12)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 1 | 8.3 | 8.65 | 8.65 | 0.0 | n/d | 0.0177 | 11.8 | 0.0 | 0.0 |
| bab | 1 | 8.3 | 29.64 | 29.64 | 0.0 | n/d | 0.1026 | 224.7 | 173.1 | 0.0 |
| pas | 1 | 8.3 | 21.71 | 21.71 | 0.0 | n/d | 0.0443 | 14.0 | 104.4 | 4.3 |
| ugc_testimonial | 9 | 75.0 | 26.28 | 58.43 | 58.19 | [10.20; 90.16] | 0.0195 | 80.1 | 118.5 | 2.5 |

### pequena/media (n = 238)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 38 | 16.0 | 23.53 | 100.22 | 48.64 | [13.40; 39.92] | 0.0637 | 16.3 | 164.6 | 0.0 |
| bab | 51 | 21.4 | 34.74 | 299.39 | 94.24 | [15.22; 60.51] | 0.079 | 64.0 | 170.9 | 1.4 |
| pas | 50 | 21.0 | 28.92 | 287.28 | 88.45 | [17.03; 60.50] | 0.1533 | 58.9 | 174.8 | 0.3 |
| product_demo_pas | 21 | 8.8 | 32.78 | 106.56 | 66.07 | [18.76; 58.52] | 0.1066 | 61.8 | 179.2 | 1.0 |
| ugc_testimonial | 78 | 32.8 | 15.23 | 625.75 | 37.96 | [11.77; 21.96] | 0.0394 | 54.3 | 175.9 | 2.1 |


### Estratificado por nicho

### contabilidade (n = 71)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 18 | 25.4 | 31.94 | 156.4 | 42.81 | [14.75; 53.78] | 0.1019 | 15.4 | 168.4 | 0.2 |
| bab | 8 | 11.3 | 14.26 | 43.11 | 13.56 | [9.86; 35.37] | 0.1106 | 54.5 | 183.0 | 0.5 |
| pas | 22 | 31.0 | 23.66 | 159.06 | 44.19 | [13.25; 50.88] | 0.0982 | 82.6 | 170.1 | 0.0 |
| product_demo_pas | 8 | 11.3 | 25.77 | 35.18 | 36.27 | [14.05; 56.46] | 0.0594 | 71.1 | 170.8 | 0.4 |
| ugc_testimonial | 15 | 21.1 | 13.59 | 31.04 | 17.61 | [9.00; 33.90] | 0.0341 | 48.8 | 113.6 | 0.0 |

### demais (n = 179)

| formato | n | pct | score_mediana | score_media | score_iqr | score_mediana_IC95 | taxa_eng_mediana | duracao_mediana_s | wpm_mediana | cortes_min_mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| aida | 21 | 11.7 | 13.3 | 47.69 | 49.97 | [9.76; 28.05] | 0.061 | 16.4 | 156.9 | 0.0 |
| bab | 44 | 24.6 | 40.72 | 339.85 | 98.97 | [16.93; 64.15] | 0.074 | 80.3 | 170.6 | 1.4 |
| pas | 29 | 16.2 | 49.87 | 375.39 | 92.26 | [15.30; 81.75] | 0.2049 | 50.2 | 181.3 | 1.0 |
| product_demo_pas | 13 | 7.3 | 50.7 | 150.49 | 116.32 | [13.84; 130.17] | 0.1103 | 60.0 | 203.2 | 1.9 |
| ugc_testimonial | 72 | 40.2 | 16.48 | 678.73 | 49.84 | [11.80; 26.77] | 0.0358 | 57.7 | 176.2 | 2.9 |
