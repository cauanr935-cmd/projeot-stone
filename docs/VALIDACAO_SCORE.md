# Validação do score viral

Amostra: **250 virais** (top 10%) vs **308 controles** (não virais dos mesmos perfis), 101 perfis. Prevalência de virais: 44.8%. Validação cruzada 5 dobras agrupada por perfil, 5 repetições, referência montada só com virais de treino (sem vazamento).

## Resultado do score (nota 0–100)

| Métrica | Valor |
|---|---|
| ROC-AUC | **0.566** (IC95% 0.518–0.614) |
| PR-AUC (acaso = 0.448) | 0.467 |
| p-valor (virais > controles, Mann-Whitney) | 0.0036 |
| AUC dentro do mesmo perfil (47 perfis) | 0.560 |
| Nota média: virais / controles | 84.8 / 81.2 |

AUC 0,5 = acaso; 1,0 = perfeito.

## Acerto nos cortes do app

| Corte | Acurácia | Acur. balanceada | Precisão | Revocação | Especificidade | F1 | TP | FP | FN | TN |
|---|---|---|---|---|---|---|---|---|---|---|
| nota ≥ 55 | 46.2% | 51.2% | 45.4% | 99.2% | 3.2% | 0.62 | 248 | 298 | 2 | 10 |
| nota ≥ 75 | 54.7% | 57.1% | 49.6% | 80.4% | 33.8% | 0.61 | 201 | 204 | 49 | 104 |

Melhor corte (maximiza acurácia balanceada, **otimista** porque é escolhido nos mesmos dados): nota ≥ 71 → acurácia balanceada 57.5%, precisão 49.4%, revocação 88.0%.

## Comparação com modelos de ML treinados (mesma CV, mesmas 8 features)

| Modelo | ROC-AUC (média ± dp) | PR-AUC |
|---|---|---|
| score (regra por faixas) | 0.566 ± 0.003 | 0.468 |
| logistica | 0.541 ± 0.024 | 0.499 |
| gradient_boosting | 0.543 ± 0.017 | 0.483 |

## Poder de cada feature isolada (AUC; 0,5 = não discrimina)

| Feature | AUC |
|---|---|
| tamanho do rosto (`max_face_area_pct`) | 0.585 |
| duração (`duration_sec`) | 0.566 |
| palavras por minuto (`words_per_minute`) | 0.565 |
| fala ativa (`speech_activity_ratio`) | 0.554 |
| presença de rosto (`face_detected_ratio`) | 0.547 |
| movimento nos 3s iniciais (`optical_flow_25d_score`) | 0.538 |
| contraste da legenda (`subtitle_zone_contrast`) | 0.529 |
| cortes por minuto (`cuts_per_minute`) | 0.519 |

## Como ler (e limites)

- "Viral" aqui = top 10% por engajamento relativo ao próprio perfil (`score_relativo`), não views absolutas.
- Os controles vêm dos mesmos perfis; a AUC dentro do perfil mostra que o score separa Reels bons de fracos *do mesmo criador*.
- A base é de microempreendedores brasileiros de nicho; o resultado não vale para outros nichos sem nova validação.
- Correlação com engajamento não prova causa: seguir o perfil de execução não garante viralização.
