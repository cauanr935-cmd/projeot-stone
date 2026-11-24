import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.claude_conexao import chat, consentimento as c, contexto


@pytest.fixture(autouse=True)
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("REELS_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CHAT_LIMITE_HORA", "100")
    chat._USO.clear()
    yield tmp_path


class _Stream:
    def __init__(self, pedacos, final):
        self.text_stream, self._f = iter(pedacos), final
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self): return self._f


class FakeCli:
    def __init__(self, *rodadas, erro=None):
        self.rodadas, self.erro, self.chamadas = list(rodadas), erro, []
        self.messages = self
    def stream(self, **kw):
        if self.erro:
            raise self.erro
        self.chamadas.append(kw)
        return _Stream(*self.rodadas.pop(0))


def final(stop="end_turn", content=()):
    return SimpleNamespace(stop_reason=stop, content=list(content))


def test_sem_consentimento_bloqueia():
    with pytest.raises(chat.ChatIndisponivel, match="Conecte"):
        list(chat.conversar("oi", cliente=FakeCli()))
    with pytest.raises(PermissionError):
        contexto.list_projects()


def test_conectar_revogar_e_token():
    r = c.conectar(["read:projetos"])
    assert r["conectado"] and r["token_mcp"].startswith("isc_")
    assert c.escopos_do_token(r["token_mcp"]) == ["read:projetos"]
    assert "token" not in json.dumps(c.estado())
    assert c.escopos_do_token("isc_errado") is None
    c.desconectar()
    assert c.escopos_do_token(r["token_mcp"]) is None
    assert not c.estado()["conectado"]


def test_escopo_vazio_recusado():
    with pytest.raises(ValueError):
        c.conectar(["inventado"])


def test_escopo_limita_ferramenta():
    c.conectar(["read:projetos"])
    assert contexto.list_projects()
    with pytest.raises(PermissionError):
        contexto.list_creatives()
    with pytest.raises(ValueError):
        c.conectar([])
    c.conectar()
    with pytest.raises(ValueError):
        contexto.get_item("../etc")


def test_stream_salva_historico_e_apaga_ao_desconectar():
    c.conectar()
    cli = FakeCli((["Olá", " mundo"], final()))
    assert "".join(chat.conversar("oi", cliente=cli)) == "Olá mundo"
    assert [m["papel"] for m in chat.historico()] == ["usuario", "assistente"]
    assert "ignore" in cli.chamadas[0]["system"].lower() and cli.chamadas[0]["tools"]
    c.desconectar()
    assert chat.historico() == []


def test_loop_de_ferramentas():
    c.conectar()
    uso = SimpleNamespace(type="tool_use", id="t1", name="list_projects", input={}, model_dump=lambda: {"type": "tool_use", "id": "t1", "name": "list_projects", "input": {}})
    cli = FakeCli(([], final("tool_use", [uso])), (["pronto"], final()))
    assert "".join(chat.conversar("quais projetos?", cliente=cli)) == "pronto"
    res = cli.chamadas[1]["messages"][-1]["content"][0]
    assert res["type"] == "tool_result" and "negocio" in res["content"]


def test_erro_da_api_nao_vaza_detalhe():
    c.conectar()
    with pytest.raises(chat.ChatIndisponivel) as e:
        list(chat.conversar("oi", cliente=FakeCli(erro=RuntimeError("sk-ant-SEGREDO"))))
    assert "SEGREDO" not in str(e.value)


def test_cancelamento():
    c.conectar()
    saida = list(chat.conversar("oi", cancelado=lambda: True, cliente=FakeCli((["a", "b"], final()))))
    assert saida == [] and chat.historico()[-1]["texto"].endswith("[interrompido]")


def test_limite_por_hora(monkeypatch):
    c.conectar()
    monkeypatch.setenv("CLAUDE_CHAT_LIMITE_HORA", "1")
    list(chat.conversar("a", cliente=FakeCli((["x"], final()))))
    with pytest.raises(chat.ChatIndisponivel, match="limite"):
        list(chat.conversar("b", cliente=FakeCli((["x"], final()))))


def _falso(tmp_path, corpo):
    import stat
    b = tmp_path / "claude"
    b.write_text("#!/usr/bin/env python3\nimport sys,json\n" + corpo)
    b.chmod(b.stat().st_mode | stat.S_IEXEC)
    return str(b)


def test_modo_assinatura_via_claude_code(tmp_path, monkeypatch):
    c.conectar(["read:projetos"])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    corpo = ("assert '--tools' in sys.argv and sys.argv[sys.argv.index('--tools')+1]==''\n"
             "for t in ['Oi','!']:\n"
             "    print(json.dumps({'type':'stream_event','event':{'delta':{'type':'text_delta','text':t}}}))\n"
             "print(json.dumps({'type':'result','result':'Oi!','is_error':False}))\n")
    monkeypatch.setenv("REELS_CLAUDE_BIN", _falso(tmp_path, corpo))
    assert chat.usa_assinatura()
    assert "".join(chat.conversar("oi")) == "Oi!"
    assert chat.historico()[-1]["texto"] == "Oi!"


def test_modo_assinatura_erro(tmp_path, monkeypatch):
    c.conectar()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("REELS_CLAUDE_BIN", _falso(tmp_path, "print(json.dumps({'type':'result','result':'x','is_error':True}))\n"))
    with pytest.raises(chat.ChatIndisponivel, match="logado"):
        list(chat.conversar("oi"))


def test_sem_chave_da_api(monkeypatch):
    c.conectar()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(chat, "_binario_cli", lambda: None)
    with pytest.raises(chat.ChatIndisponivel, match="Claude Code"):
        list(chat.conversar("oi"))


def test_chave_nunca_no_frontend():
    for f in Path("src/web").glob("*.html"):
        t = f.read_text(encoding="utf-8")
        assert "ANTHROPIC_API_KEY" not in t and "sk-ant" not in t


@pytest.mark.asyncio
async def test_verificador_mcp():
    from src.claude_conexao.mcp_remoto import VerificadorLocal, criar
    tok = c.conectar(["read:projetos"])["token_mcp"]
    v = VerificadorLocal()
    assert (await v.verify_token(tok)).scopes == ["read:projetos"]
    assert await v.verify_token("isc_x") is None
    nomes = {t.name for t in await criar().list_tools()}
    assert {"search_context", "get_item", "list_projects", "list_creatives", "get_brand_guidelines"} <= nomes
