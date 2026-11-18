"""Testes da unificação da base: dedupe, exclusões com motivo, janela de 12 meses, métricas e schema."""
import pandas as pd
import pytest

from src.base.schema import POSTS_SCHEMA
from src.base.unificar import construir_base, tabela_perfis

COLETA = pd.Timestamp("2026-11-18", tz="UTC")


def _linha(pid, user="a", dias=60, curtidas=100, com=0, seg=1000, tipo="reels", views=1000):
    ts = COLETA - pd.Timedelta(days=dias)
    return {"plataforma": "instagram", "post_id": pid, "url": f"u/{pid}", "username": user, "tipo_post": tipo,
            "legenda": "x", "hashtags": ["mei"], "data_post": ts, "data_coleta": COLETA, "idade_dias": dias,
            "curtidas": curtidas, "comentarios": com, "views": views, "duracao_s": 20.0, "n_slides": 0,
            "collab": False, "publipost": None, "seguidores": seg, "tamanho": "pequeno",
            "tipo_conta": "criador", "segmento": "x"}


def test_schema_estavel_e_tipos():
    posts, _ = construir_base({"l1": pd.DataFrame([_linha("1")])}, [])
    assert list(posts.columns) == [*POSTS_SCHEMA, "hashtags"]
    assert str(posts["curtidas"].dtype) == "Int64" and str(posts["taxa_eng"].dtype) == "Float64"
    assert posts.loc[0, "hashtags"] == ["mei"]


def test_dedup_prioriza_primeiro_lote():
    a = pd.DataFrame([_linha("1", curtidas=10)])
    b = pd.DataFrame([_linha("1", curtidas=999), _linha("2")])
    posts, _ = construir_base({"l1": a, "l2": b}, [])
    assert sorted(posts["post_id"]) == ["1", "2"]
    assert posts.set_index("post_id").loc["1", "lote"] == "l1"


def test_exclui_fora_de_reels_e_fora_da_janela_com_motivo():
    df = pd.DataFrame([_linha("ok"), _linha("car", tipo="carrossel"), _linha("velho", dias=400)])
    posts, excl = construir_base({"l1": df}, [])
    assert posts["post_id"].tolist() == ["ok"]
    assert dict(zip(excl["post_id"], excl["motivo"])) == {"car": "fora_do_foco_reels", "velho": "fora_janela_12m"}


def test_exclui_menos_de_14_dias_e_mantem_excluidos_da_coleta():
    df = pd.DataFrame([_linha("ok"), _linha("novo", dias=5)])
    ja = pd.DataFrame([_linha("colab", user="outro")])
    posts, excl = construir_base({"l1": df}, [("l1", "colaboracao_dono_diferente", ja)])
    assert posts["post_id"].tolist() == ["ok"]
    assert dict(zip(excl["post_id"], excl["motivo"])) == {"colab": "colaboracao_dono_diferente"}


def test_janela_de_fato_corta_e_reaproveita_mediana_recalculada():
    # a mediana do perfil deve ser recalculada sem o post removido pela janela
    df = pd.DataFrame([_linha("1", curtidas=100), _linha("2", curtidas=300), _linha("velho", curtidas=10000, dias=500)])
    posts, _ = construir_base({"l1": df}, [])
    s = posts.set_index("post_id")["score_relativo"].astype(float)
    assert s["1"] == pytest.approx(0.5) and s["2"] == pytest.approx(1.5)  # mediana 0.2 (média de 0.1 e 0.3)


def test_curtidas_ocultas_ficam_na_base_mas_fora_do_ranking():
    df = pd.DataFrame([_linha("1"), _linha("2", curtidas=None)])
    posts, _ = construir_base({"l1": df}, [])
    p = posts.set_index("post_id")
    assert bool(p.loc["2", "curtidas_ocultas"]) and not bool(p.loc["2", "elegivel_ranking"])
    assert bool(p.loc["1", "elegivel_ranking"])


def test_tabela_perfis_marca_sem_reels():
    posts, excl = construir_base({"l1": pd.DataFrame([_linha("1", user="a")])}, [])
    csv = pd.DataFrame({"plataforma": "instagram", "username": ["a", "b"], "tamanho": "pequeno",
                        "tipo_conta": "criador", "segmento": "x"})
    raw = pd.DataFrame({"username": ["a", "b"], "nome": "n", "seguidores": 1, "verificado": False,
                        "conta_comercial": False, "categoria_ig": None, "bio": "", "data_coleta": COLETA})
    p = tabela_perfis(csv, raw, posts, excl).set_index("username")
    assert p.loc["a", "status"] == "na_base" and p.loc["b", "status"] == "sem_reels_elegiveis"
