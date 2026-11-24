"""Classificação de formato por movimentos retóricos (src/analise/formato_copy.py)."""
from src.analise.formato_copy import classificar_formato

LONGO = " ".join(["palavra"] * 20)


def test_pas_dor_na_abertura():
    t = "Você posta o dia inteiro mas a agenda continua vazia. Esse é o problema e o erro de quem começa. " + LONGO
    fmt, _, _, ev = classificar_formato("Agenda vazia?", t)
    assert fmt == "pas" and any(e.startswith("dor:") for e in ev)


def test_bab_exige_contraste():
    t = "Eu saí do zero aos 100 mil de faturamento. Antes eu vendia pouco e hoje vendo todos os dias. " + LONGO
    assert classificar_formato("Do zero aos 100 mil", t)[0] == "bab"


def test_aida_lista_promessa_e_cta_no_fecho():
    t = "Vou te contar o segredo. Três dicas para vender mais. " + LONGO + " Siga o perfil e chama no whatsapp."
    fmt, _, conf, _ = classificar_formato("3 dicas", t)
    assert fmt == "aida" and conf != "baixa"


def test_cta_no_meio_nao_vale_como_fecho():
    t = "Siga o perfil e chama no whatsapp. " + LONGO * 6
    assert classificar_formato("x", t)[1]["aida"] < 1.5


def test_eu_e_meu_sozinhos_nao_viram_ugc():
    t = "Eu acho que o meu preço é o meu jeito. " + LONGO
    fmt, sc, conf, _ = classificar_formato("x", t)
    assert sc["ugc_testimonial"] < 1.5 and conf == "baixa"


def test_ugc_exige_varios_verbos_de_relato():
    t = "Eu comecei sem nada, vendi no WhatsApp, aprendi com os erros e consegui faturar. " + LONGO
    assert classificar_formato("minha história", t)[0] == "ugc_testimonial"


def test_sem_fala_tem_confianca_baixa():
    fmt, _, conf, ev = classificar_formato("Como vender mais", "")
    assert conf == "baixa" and "sem fala" in ev
