import numpy as np

from src.analise import edicao_padroes as ep
from src.analise import legenda_hashtags as lh


def _ruido(seed, n=2):
    r = np.random.default_rng(seed)
    base = (r.random((ep.LH, ep.LW)) * 255).astype(np.uint8)
    return base


def test_detecta_corte_entre_cenas_diferentes():
    a, b = _ruido(1), np.clip(255 - _ruido(2), 0, 255).astype(np.uint8)
    q = np.stack([a] * 12 + [b] * 12)
    assert ep.detectar_cortes(q) == [12]


def test_sem_corte_em_video_estatico():
    assert ep.detectar_cortes(np.stack([_ruido(3)] * 20)) == []


def test_punch_in_reconhecido():
    import cv2
    x = cv2.GaussianBlur(_ruido(4), (0, 0), 2)
    assert ep.punch_no_corte(x, ep._escala(x, 1.3))
    assert not ep.punch_no_corte(x, cv2.GaussianBlur(_ruido(5), (0, 0), 2))


def test_classifica_ganchos_e_ctas():
    assert {"pergunta", "numero_valor"} <= set(ep.classificar("Você sabe quanto custa R$ 50 por mês?", ep.GANCHOS))
    assert "erro_dor" in ep.classificar("O erro que faz você perder dinheiro", ep.GANCHOS)
    assert "link_bio" in ep.classificar("clica no link na bio", ep.CTAS)
    assert ep.classificar("", ep.GANCHOS) == []


def test_legenda_estrutura_e_hashtags():
    r = lh.gerar("Doce Sonho", "confeitaria", "bolo de pote por R$ 12", gancho="R$ 12 e esse bolo é seu?", cidade="Santos")
    linhas = r["legenda"].split("\n")
    assert linhas[0].startswith("R$ 12") and "#confeitaria" in r["legenda"] and "#docesonho" in r["legenda"]
    assert 5 <= len(r["hashtags"]) <= 10 and len(set(r["hashtags"])) == len(r["hashtags"])
    assert "#santos" in r["legenda"]


def test_prompt_inclui_playbook_e_legenda(tmp_path):
    from src.criativos import sessao_claude as sc
    p = sc.montar_prompt("x", [], tmp_path)
    assert "legenda.txt" in p and "legenda_hashtags" in p
