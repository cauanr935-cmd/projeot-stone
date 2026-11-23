"""Valida o score viral como se fosse um classificador: viral (top 10%) vs controle (mesmos perfis, não virais).

Protocolo (sem vazamento): validação cruzada estratificada AGRUPADA POR PERFIL. Em cada dobra a referência P5/P25/P75/P95
é montada só com os virais de treino; a nota é calculada para os Reels da dobra de teste (virais e controles).
Métricas: ROC-AUC, PR-AUC, acurácia/precisão/revocação nos cortes do app (55 e 75), acurácia balanceada, matriz de confusão,
IC95% por bootstrap, p-valor (Mann-Whitney), AUC dentro do mesmo perfil e AUC por feature. Um modelo de ML treinado
(regressão logística e gradient boosting, mesma CV) entra como teto de comparação.

Uso: python -m src.analise.validar_score [--virais dados/analise_top10/features] [--controles dados/analise_controle/features]
                                         [--saida docs/VALIDACAO_SCORE.md] [--repeticoes 5]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import mannwhitneyu
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.analise.score_viral import FEATURES, _nota_percentis

CHAVES = [f[0] for f in FEATURES]
ROTULOS = {f[0]: f[2] for f in FEATURES}
PESOS = {f[0]: f[1] for f in FEATURES}
CORTES_APP = (55, 75)


def carregar(pasta: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pasta.glob("*.json"))]


def _percentis(ref: list[dict]) -> dict[str, tuple[float, ...]]:
    out = {}
    for k in CHAVES:
        v = np.array([r[k] for r in ref if r.get(k) is not None], float)
        if len(v) >= 10:
            out[k] = tuple(np.percentile(v, [5, 25, 75, 95]))
    return out


def nota(feats: dict, perc: dict) -> float:
    s = p = 0.0
    for k, q in perc.items():
        if feats.get(k) is None:
            continue
        s += _nota_percentis(float(feats[k]), *q) * PESOS[k]
        p += PESOS[k]
    return s / p if p else float("nan")


def matriz(y: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(((y == 1) & (pred == 1)).sum()); fn = int(((y == 1) & (pred == 0)).sum())
    fp = int(((y == 0) & (pred == 1)).sum()); tn = int(((y == 0) & (pred == 0)).sum())
    rec = tp / (tp + fn) if tp + fn else 0.0
    esp = tn / (tn + fp) if tn + fp else 0.0
    prec = tp / (tp + fp) if tp + fp else 0.0
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "acuracia": (tp + tn) / len(y), "precisao": prec,
            "revocacao": rec, "especificidade": esp, "acuracia_balanceada": (rec + esp) / 2,
            "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0}


def _auc_perfil(y: np.ndarray, s: np.ndarray, perfis: np.ndarray) -> tuple[float, int]:
    """AUC média dentro de cada perfil que tem virais e controles (neutraliza 'perfil bom' vs 'perfil ruim')."""
    aucs, pesos = [], []
    for p in np.unique(perfis):
        m = perfis == p
        if 0 < y[m].sum() < m.sum():
            aucs.append(roc_auc_score(y[m], s[m])); pesos.append(m.sum())
    return (float(np.average(aucs, weights=pesos)) if aucs else float("nan")), len(aucs)


def _matriz_X(linhas: list[dict]) -> np.ndarray:
    return np.array([[np.nan if r.get(k) is None else float(r[k]) for k in CHAVES] for r in linhas], float)


def validar(virais: list[dict], controles: list[dict], repeticoes: int = 5, k: int = 5) -> dict:
    linhas = virais + controles
    y = np.array([1] * len(virais) + [0] * len(controles))
    perfis = np.array([r["profile"] for r in linhas])
    X = _matriz_X(linhas)
    modelos = {
        "logistica": lambda: make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                           LogisticRegression(max_iter=2000, class_weight="balanced")),
        "gradient_boosting": lambda: make_pipeline(SimpleImputer(strategy="median"),
                                                   GradientBoostingClassifier(n_estimators=150, max_depth=2, random_state=0)),
    }
    por_rep = {n: [] for n in ("score", *modelos)}
    oof_score = np.zeros((repeticoes, len(y)))
    for rep in range(repeticoes):
        cv = StratifiedGroupKFold(n_splits=k, shuffle=True, random_state=rep)
        oof = {n: np.zeros(len(y)) for n in por_rep}
        for tr, te in cv.split(X, y, perfis):
            perc = _percentis([linhas[i] for i in tr if y[i] == 1])
            oof["score"][te] = [nota(linhas[i], perc) for i in te]
            for n, f in modelos.items():
                m = f().fit(X[tr], y[tr])
                oof[n][te] = m.predict_proba(X[te])[:, 1]
        for n in por_rep:
            s = np.nan_to_num(oof[n], nan=np.nanmedian(oof[n]))
            por_rep[n].append({"roc_auc": roc_auc_score(y, s), "pr_auc": average_precision_score(y, s)})
        oof_score[rep] = np.nan_to_num(oof["score"], nan=np.nanmedian(oof["score"]))

    s = oof_score.mean(axis=0)  # nota média out-of-fold entre repetições
    rng = np.random.default_rng(0)
    boot = []
    for _ in range(1000):
        i = rng.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(i):
            boot.append(roc_auc_score(y[i], s[i]))
    u = mannwhitneyu(s[y == 1], s[y == 0], alternative="greater")
    auc_p, n_p = _auc_perfil(y, s, perfis)
    por_feature = {}
    for j, kf in enumerate(CHAVES):
        col = X[:, j]; ok = ~np.isnan(col)
        if ok.sum() > 30 and 0 < y[ok].sum() < ok.sum():
            por_feature[kf] = float(roc_auc_score(y[ok], col[ok]))
    cortes = {str(c): matriz(y, (s >= c).astype(int)) for c in CORTES_APP}
    ts = np.unique(np.round(s))
    youden = max(ts, key=lambda t: matriz(y, (s >= t).astype(int))["acuracia_balanceada"])
    resumo = {n: {m: [float(np.mean([r[m] for r in rs])), float(np.std([r[m] for r in rs]))] for m in ("roc_auc", "pr_auc")}
              for n, rs in por_rep.items()}
    return {
        "n_virais": len(virais), "n_controles": len(controles), "n_perfis": int(len(np.unique(perfis))),
        "k_dobras": k, "repeticoes": repeticoes, "prevalencia": float(y.mean()),
        "score": {"roc_auc": float(roc_auc_score(y, s)), "roc_auc_ic95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                  "pr_auc": float(average_precision_score(y, s)), "p_valor": float(u.pvalue),
                  "auc_dentro_do_perfil": auc_p, "perfis_com_as_duas_classes": n_p,
                  "nota_media_virais": float(s[y == 1].mean()), "nota_media_controles": float(s[y == 0].mean()),
                  "cortes_app": cortes, "melhor_corte_otimista": {"corte": float(youden), **matriz(y, (s >= youden).astype(int))}},
        "estabilidade_entre_repeticoes": resumo,
        "auc_por_feature": dict(sorted(por_feature.items(), key=lambda kv: -abs(kv[1] - 0.5))),
    }


def relatorio(r: dict) -> str:
    sc = r["score"]; est = r["estabilidade_entre_repeticoes"]
    pct = lambda v: f"{100 * v:.1f}%"  # noqa: E731
    L = ["# Validação do score viral", "",
         f"Amostra: **{r['n_virais']} virais** (top 10%) vs **{r['n_controles']} controles** (não virais dos mesmos perfis), "
         f"{r['n_perfis']} perfis. Prevalência de virais: {pct(r['prevalencia'])}. "
         f"Validação cruzada {r['k_dobras']} dobras agrupada por perfil, {r['repeticoes']} repetições, referência montada só com virais de treino (sem vazamento).",
         "", "## Resultado do score (nota 0–100)", "",
         "| Métrica | Valor |", "|---|---|",
         f"| ROC-AUC | **{sc['roc_auc']:.3f}** (IC95% {sc['roc_auc_ic95'][0]:.3f}–{sc['roc_auc_ic95'][1]:.3f}) |",
         f"| PR-AUC (acaso = {r['prevalencia']:.3f}) | {sc['pr_auc']:.3f} |",
         f"| p-valor (virais > controles, Mann-Whitney) | {sc['p_valor']:.2g} |",
         f"| AUC dentro do mesmo perfil ({sc['perfis_com_as_duas_classes']} perfis) | {sc['auc_dentro_do_perfil']:.3f} |",
         f"| Nota média: virais / controles | {sc['nota_media_virais']:.1f} / {sc['nota_media_controles']:.1f} |",
         "", "AUC 0,5 = acaso; 1,0 = perfeito.", "", "## Acerto nos cortes do app", "",
         "| Corte | Acurácia | Acur. balanceada | Precisão | Revocação | Especificidade | F1 | TP | FP | FN | TN |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c, m in sc["cortes_app"].items():
        L.append(f"| nota ≥ {c} | {pct(m['acuracia'])} | {pct(m['acuracia_balanceada'])} | {pct(m['precisao'])} | {pct(m['revocacao'])} | "
                 f"{pct(m['especificidade'])} | {m['f1']:.2f} | {m['tp']} | {m['fp']} | {m['fn']} | {m['tn']} |")
    b = sc["melhor_corte_otimista"]
    L += ["", f"Melhor corte (maximiza acurácia balanceada, **otimista** porque é escolhido nos mesmos dados): nota ≥ {b['corte']:.0f} → "
          f"acurácia balanceada {pct(b['acuracia_balanceada'])}, precisão {pct(b['precisao'])}, revocação {pct(b['revocacao'])}.",
          "", "## Comparação com modelos de ML treinados (mesma CV, mesmas 8 features)", "",
          "| Modelo | ROC-AUC (média ± dp) | PR-AUC |", "|---|---|---|"]
    for n, m in est.items():
        L.append(f"| {'score (regra por faixas)' if n == 'score' else n} | {m['roc_auc'][0]:.3f} ± {m['roc_auc'][1]:.3f} | {m['pr_auc'][0]:.3f} |")
    L += ["", "## Poder de cada feature isolada (AUC; 0,5 = não discrimina)", "", "| Feature | AUC |", "|---|---|"]
    for k, v in r["auc_por_feature"].items():
        L.append(f"| {ROTULOS[k]} (`{k}`) | {v:.3f} |")
    L += ["", "## Como ler (e limites)", "",
          "- \"Viral\" aqui = top 10% por engajamento relativo ao próprio perfil (`score_relativo`), não views absolutas.",
          "- Os controles vêm dos mesmos perfis; a AUC dentro do perfil mostra que o score separa Reels bons de fracos *do mesmo criador*.",
          "- A base é de microempreendedores brasileiros de nicho; o resultado não vale para outros nichos sem nova validação.",
          "- Correlação com engajamento não prova causa: seguir o perfil de execução não garante viralização.",
          ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--virais", default="dados/analise_top10/features")
    ap.add_argument("--controles", default="dados/analise_controle/features")
    ap.add_argument("--saida", default="docs/VALIDACAO_SCORE.md")
    ap.add_argument("--json", default="dados/analise_controle/validacao.json")
    ap.add_argument("--repeticoes", type=int, default=5)
    a = ap.parse_args(argv)
    r = validar(carregar(Path(a.virais)), carregar(Path(a.controles)), a.repeticoes)
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(r, ensure_ascii=False, indent=2))
    Path(a.saida).write_text(relatorio(r), encoding="utf-8")
    print(relatorio(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
