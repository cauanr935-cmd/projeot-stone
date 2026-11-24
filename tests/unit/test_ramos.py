"""Ramos fora dos 10 prioritários: padaria, genéricos por segmento e fallback 'geral' (a conversa nunca trava)."""
import pytest

from src.criativos import conversa
from src.criativos.spec import carregar_genericos, carregar_perfis, carregar_perfis_todos, spec_offline


@pytest.mark.parametrize("fala,esperado", [
    ("sou dono de uma padaria", "padaria"),
    ("tenho uma panificadora e vendo pão francês", "padaria"),
    ("trabalho com pão de queijo", "padaria"),
    ("tenho uma farmácia de bairro", "varejo_geral"),
    ("sou encanador", "servicos_tecnicos_geral"),
    ("sou personal trainer", "ensino_geral"),
    ("tenho uma pizzaria", "alimentacao_geral"),
    ("faço tatuagem", "beleza_geral"),
])
def test_ramos_fora_dos_dez_sao_reconhecidos(fala, esperado):
    assert conversa.detectar_perfil(fala) == esperado


@pytest.mark.parametrize("fala,esperado", [
    ("sou confeiteira", "confeiteira"),
    ("tenho um salão de cabeleireira", "cabeleireira"),
    ("sou mecânico", "mecanico"),
])
def test_prioritarios_continuam_ganhando(fala, esperado):
    assert conversa.detectar_perfil(fala) == esperado


def test_padaria_nao_e_rejeitada_e_pede_so_o_que_falta():
    r = conversa.interpretar("Sou dono da Padaria Pão Quente e quero divulgar bolo caseiro por R$ 12", usar_llm=False)
    assert r["briefing"]["perfil_id"] == "padaria"
    assert "perfil_id" not in r["faltando"]
    assert r["pronto"], r["faltando"]


def test_ramo_desconhecido_nao_gera_pergunta_infinita():
    r = conversa.interpretar("quero fazer um vídeo", usar_llm=False)
    assert "perfil_id" in r["faltando"]
    assert "padaria" in conversa._montar_pergunta(["perfil_id"], {})            # a pergunta convida a falar livremente
    r = conversa.interpretar("sou taxidermista", r["estado"], usar_llm=False)
    assert r["briefing"]["perfil_id"] == "geral" and r["briefing"]["ramo_livre"] == "taxidermista"
    assert "perfil_id" not in r["faltando"]
    assert "Ramo: taxidermista" in r["entendi"]


def test_sempre_termina_mesmo_sem_entender_nada():
    r = conversa.interpretar("hmm", usar_llm=False)
    for _ in range(4):
        if r["pronto"]:
            break
        r = conversa.interpretar("não sei dizer direito", r["estado"], usar_llm=False)
    assert r["pronto"], r["faltando"]


def test_generico_usa_a_fala_da_pessoa_no_gancho():
    b = {"perfil_id": "geral", "negocio": "Casa Nova", "oferta": "Chaveiro 24 horas na sua porta agora mesmo", "ramo_livre": "chaveiro"}
    a = conversa.aplicar_briefing(b)
    assert a["perfil_override"]["gancho"] == "Chaveiro 24 horas na sua"
    assert len(a["perfil_override"]["gancho"].split()) <= 5 and a["perfil_override"]["nome"] == "chaveiro"
    assert "chaveiro" in a["instrucoes"]


def test_dez_prioritarios_intactos_e_genericos_separados():
    assert len(carregar_perfis()) == 10
    gen = carregar_genericos()
    assert {"padaria", "geral"} <= set(gen) and not (set(gen) & set(carregar_perfis()))
    assert set(carregar_perfis_todos()) == set(carregar_perfis()) | set(gen)


@pytest.mark.parametrize("pid", list(carregar_genericos()))
def test_cada_generico_gera_spec_valido(pid):
    spec = spec_offline(pid)
    assert spec.cenas[0].tipo == "hook" and spec.cenas[-1].tipo == "cta"
    assert len(spec.hook_overlay.split()) <= 5


@pytest.mark.parametrize("fala,perfil,nome", [
    ("Sou dono da Padaria Pão Quente e quero divulgar bolo caseiro por R$ 12", "padaria", "Padaria Pão Quente"),
    ("minha padaria Pão Quente vende pão francês", "padaria", "Pão Quente"),
    ("Tenho a Farmácia Bem Estar e quero divulgar entrega grátis", "varejo_geral", "Farmácia Bem Estar"),
])
def test_ramo_dito_primeiro_vence_o_produto_e_o_nome_e_extraido(fala, perfil, nome):
    assert conversa.detectar_perfil(fala) == perfil
    assert conversa.extrair_nome(fala) == nome


def test_empate_vai_para_quem_foi_dito_primeiro():
    assert conversa.detectar_perfil("sou confeiteira e também vendo pão") == "confeiteira"
    assert conversa.detectar_perfil("tenho uma padaria e faço bolos") == "padaria"
