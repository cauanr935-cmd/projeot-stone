from src.criativos import conversa
from src.criativos.spec import spec_do_roteiro


def _i(t, e=None):
    return conversa.interpretar(t, e, usar_llm=False)


def test_pedido_completo_fica_pronto():
    r = _i("Tenho uma confeitaria chamada Doce Sonho e quero divulgar bolo de pote por R$ 12 no WhatsApp")
    b = r["briefing"]
    assert r["pronto"] and b["perfil_id"] == "confeiteira" and b["negocio"] == "Doce Sonho"
    assert b["preco"] == "R$ 12" and b["cta_canal"] == "WhatsApp"


def test_pergunta_e_resposta_curta():
    r = _i("quero um vídeo sobre meu trabalho")
    assert not r["pronto"] and "perfil_id" in r["faltando"] and r["pergunta"]
    r = _i("sou eletricista", r["estado"])
    assert r["faltando"] == ["negocio"]
    r = _i("Eletro Seguro", r["estado"])
    assert r["pronto"] and r["briefing"]["negocio"] == "Eletro Seguro"


def test_pular_pergunta():
    r = _i("sou cabeleireira, meu salão se chama Studio Luz")
    assert r["faltando"] == ["oferta"]
    assert _i("pode seguir", r["estado"])["pronto"]


def test_nunca_prende_apos_duas_rodadas_sem_ramo_obrigatorio():
    r = _i("oi")
    r = _i("hum", r["estado"])
    r = _i("sei lá", r["estado"])
    assert r["faltando"] == ["perfil_id"]


def test_aplicar_briefing_ajusta_perfil():
    a = conversa.aplicar_briefing({"perfil_id": "confeiteira", "negocio": "X", "oferta": "bolo de pote", "preco": "R$ 12"})
    assert a["perfil_override"]["destaque"]["valor"] == "R$ 12" and a["perfil_override"]["solucao"][0] == "bolo de pote"


def test_roteiro_do_usuario_vira_cenas():
    s = spec_do_roteiro("confeiteira", "Cansou de bolo seco? Meu bolo é úmido. Feito na hora. Entrega no bairro. Chame no WhatsApp.")
    assert s.cenas[0].tipo == "hook" and s.cenas[-1].tipo == "cta" and s.gerado_por == "roteiro_do_usuario"
