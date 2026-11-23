import json

import pytest
from pydantic import ValidationError

from src.criativos import llm
from src.criativos.spec import CriativoSpec, carregar_perfis, spec_offline


def test_dez_perfis_cobrem_os_cinco_formatos():
    perfis = carregar_perfis()
    assert len(perfis) == 10
    assert {p["format_id"] for p in perfis.values()} == {1, 2, 3, 4, 5}


@pytest.mark.parametrize("pid", list(carregar_perfis()))
def test_spec_offline_valido_e_estrutura(pid):
    s = spec_offline(pid)
    assert s.cenas[0].tipo == "hook" and s.cenas[-1].tipo == "cta"
    assert len(s.hook_overlay.split()) <= 5
    CriativoSpec(**json.loads(s.model_dump_json()))


def test_hook_com_mais_de_5_palavras_reprova():
    d = spec_offline("eletricista").model_dump()
    d["hook_overlay"] = "um dois tres quatro cinco seis"
    with pytest.raises(ValidationError):
        CriativoSpec(**d)


def test_sem_chave_cai_no_template(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert llm.escolher_llm() == (None, None)
    assert llm.gerar_spec("pet_banho_tosa").gerado_por == "template_engine"


def test_offline_forca_template_mesmo_com_chave(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("REELS_OFFLINE", "1")
    assert llm.escolher_llm() == (None, None)


def test_llm_falho_cai_no_template(monkeypatch):
    class Quebrado:
        def with_structured_output(self, *_):
            raise RuntimeError("boom")
    monkeypatch.setattr(llm, "escolher_llm", lambda: ("anthropic", Quebrado()))
    assert llm.gerar_spec("eletricista").gerado_por == "template_engine"


def test_briefing_traz_schema_e_regras():
    b = llm.briefing("confeiteira")
    assert "hook_overlay" in json.dumps(b["schema"]) and "Frame Zero" in b["regras"]


def test_frames_renderizam_todas_as_cenas():
    from src.criativos.motion import Fundo, _quadro_cena
    s = spec_offline("cabeleireira")
    f = Fundo(s)
    for c in s.cenas:
        img = _quadro_cena(s, f, c, 1.5, 4.0, 1.5, 20.0)
        assert img.size == (1080, 1920)


def test_grafo_traz_rastro_completo_sem_render(tmp_path):
    from src.criativos.grafo import executar
    r = executar("eletricista", pasta=tmp_path, com_voz=False, renderizar=False)
    assert [t["no"] for t in r["trace"]] == ["perfil", "formato", "referencias", "padroes", "roteiro", "validacao"]
    assert all(c["motivo"] for c in r["spec"]["cenas"])
    assert (tmp_path / "eletricista_f4.raciocinio.json").is_file()


def test_grafo_refaz_roteiro_invalido(monkeypatch, tmp_path):
    from src.criativos import grafo
    chamadas = {"n": 0}
    original = grafo.n_roteiro

    def ruim(s):
        chamadas["n"] += 1
        out = original(s)
        if chamadas["n"] == 1:
            out["spec"] = {**out["spec"], "hook_overlay": "um dois tres quatro cinco seis"}
        return out
    monkeypatch.setattr(grafo, "n_roteiro", ruim)
    r = grafo.executar("confeiteira", pasta=tmp_path, com_voz=False, renderizar=False)
    assert chamadas["n"] >= 1 and len(r["spec"]["hook_overlay"].split()) <= 5


def test_referencias_ordenadas_e_com_url():
    from src.criativos import referencias as refs
    if not refs.base_disponivel():
        pytest.skip("base local indisponível")
    r = refs.buscar(4, "servicos_tecnicos", 3)
    assert len(r) == 3 and all(x["url"].startswith("https://") and x["por_que"] for x in r)
