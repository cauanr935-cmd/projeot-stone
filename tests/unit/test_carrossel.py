from src.criativos import carrossel
from src.criativos.spec import carregar_perfis_todos


def test_todos_os_perfis_geram_carrossel_valido(tmp_path):
    for pid in carregar_perfis_todos():
        spec = carrossel.spec_offline(pid, {"negocio": "Loja Teste", "oferta": "promoção de verão"})
        assert carrossel.validar(spec) == [], pid
    r = carrossel.renderizar(spec, tmp_path)
    assert len(r["slides"]) == len(spec.slides) and (tmp_path / "carrossel.zip").is_file()


def test_validar_rejeita_capa_longa_e_cta_duplo():
    spec = carrossel.spec_offline("geral")
    spec.slides[0].titulo = "uma capa com palavras demais para aparecer legível no feed do celular"
    spec.slides[1].tipo = "cta"
    erros = " ".join(carrossel.validar(spec))
    assert "capa" in erros and "único slide de CTA" in erros
