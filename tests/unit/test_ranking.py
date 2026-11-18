import pandas as pd

from src.ranking.ranking import calcular_ranking, resumo


def _posts(scores, user="a", plat="instagram", apto=True):
    return pd.DataFrame({
        "plataforma": plat, "post_id": [f"{user}{i}" for i in range(len(scores))], "username": user,
        "tipo_post": "reels", "score_relativo": scores, "taxa_eng": [s / 10 for s in scores],
        "alcance": 1.0, "ressonancia": 0.1, "elegivel_ranking": apto})


def test_top10_por_plataforma_e_ordem():
    a = _posts([float(i) for i in range(1, 21)], "a")           # 20 posts
    r = calcular_ranking(a, 0.10, 5).set_index("post_id")
    top = r[r["alto_desempenho"]]
    assert len(top) == 2 and set(top.index) == {"a18", "a19"}
    assert r.loc["a19", "score_rank"] == 1


def test_plataformas_separadas():
    a, y = _posts([float(i) for i in range(1, 21)], "a"), _posts([float(i) for i in range(100, 120)], "y", "youtube")
    r = calcular_ranking(pd.concat([a, y], ignore_index=True), 0.10, 5)
    assert r.groupby("plataforma")["alto_desempenho"].sum().to_dict() == {"instagram": 2, "youtube": 2}


def test_curtidas_ocultas_e_perfil_com_poucos_reels_ficam_fora():
    a = _posts([float(i) for i in range(1, 21)], "a")
    a.loc[0, "elegivel_ranking"] = False
    b = _posts([1000.0, 2000.0], "b")                            # só 2 reels: mediana instável
    r = calcular_ranking(pd.concat([a, b], ignore_index=True), 0.10, 5).set_index("post_id")
    assert not r.loc["a0", "apto"] and not r.loc["b0", "apto"] and not r.loc["b1", "alto_desempenho"]
    assert r["alto_desempenho"].sum() >= 1


def test_score_extremo_sinalizado_nao_removido():
    a = _posts([1.0] * 19 + [500.0])
    r = calcular_ranking(a, 0.10, 5, score_extremo=20).set_index("post_id")
    assert bool(r.loc["a19", "score_extremo"]) and bool(r.loc["a19", "alto_desempenho"])


def test_resumo_visao_secundaria():
    a = _posts([float(i) for i in range(1, 21)])
    r = calcular_ranking(a, 0.10, 5)
    s = resumo(a.assign(elegivel_ranking=True), r)
    assert s["top_score"] == 2 and s["intersecao"] == 2
