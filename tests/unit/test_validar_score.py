import numpy as np

from src.analise.validar_score import CHAVES, matriz, validar


def _linhas(n, centro, perfil_prefixo, rng):
    return [{"profile": f"{perfil_prefixo}{i % 10}", **{k: float(rng.normal(centro, 1.0)) for k in CHAVES}} for i in range(n)]


def test_score_separa_classes_com_sinal():
    rng = np.random.default_rng(0)
    v, c = _linhas(120, 0.0, "p", rng), _linhas(160, 4.0, "p", rng)
    r = validar(v, c, repeticoes=1, k=4)
    assert r["score"]["roc_auc"] > 0.9


def test_score_sem_sinal_fica_perto_de_acaso():
    rng = np.random.default_rng(1)
    v, c = _linhas(120, 0.0, "p", rng), _linhas(160, 0.0, "p", rng)
    r = validar(v, c, repeticoes=1, k=4)
    assert 0.35 < r["score"]["roc_auc"] < 0.65


def test_matriz_confusao():
    m = matriz(np.array([1, 1, 0, 0]), np.array([1, 0, 0, 1]))
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (1, 1, 1, 1) and m["acuracia"] == 0.5
