import pandas as pd
import pytest

from src.analise.classificar import classificar_regras, md, resumo
from src.core.config import load_formats

CHAVES = {f["key"] for f in load_formats()}
F0 = {"face_detected_ratio": .5, "max_face_area_pct": 5, "subtitle_zone_contrast": .01}


def test_sempre_devolve_formato_valido():
    for txt in ["", "bom dia", "antes eu perdia tempo, depois do sistema mudou tudo", "cuidado com a multa do MEI"]:
        assert classificar_regras(txt, F0)[0] in CHAVES


def test_regras_basicas():
    assert classificar_regras("Cuidado: esse erro gera multa e prejuizo. Evite!", F0)[0] == "pas"
    assert classificar_regras("Antes era assim, depois mudou. Transformacao total", F0)[0] == "bab"
    assert classificar_regras("Voce sabia? Link na bio, comente quero!", F0)[0] == "aida"


def test_sem_evidencia_baixa_confianca():
    assert classificar_regras("", F0)[2] == "baixa"


def test_resumo_fecha_contagem():
    df = pd.DataFrame({"formato": ["pas", "pas", "aida"], "score_relativo": [2., 3., 1.], "taxa_eng": [.1, .2, .3],
                       "duration_sec": [30, 40, 20], "has_audio": [True, False, True],
                       "words_per_minute": [150., 0., 170.], "cuts_per_minute": [5., 6., 2.]})
    r = resumo(df)
    assert r.n.sum() == 3 and not r.drop(columns=["wpm_mediana"]).isna().any().any()
    assert "| pas |" in md(r)


def test_classificacao_real_fecha_contagens():
    import json
    from pathlib import Path
    p = Path("dados/analise_top10/format_classification.json")
    if not p.exists():
        pytest.skip("análise local (gitignored) ausente")
    rows = json.loads(p.read_text())
    import pandas as pd
    rank = pd.read_parquet("dados/base/ranking.parquet")
    top = rank[rank["alto_desempenho"]]
    assert len(rows) == len(top) and sum(r["is_consensus_80"] for r in rows) == int(top["alto_desempenho_taxa_eng"].sum())
    assert {r["formato"] for r in rows} <= CHAVES
