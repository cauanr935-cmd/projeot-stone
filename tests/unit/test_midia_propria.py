import io
from pathlib import Path

import pytest

from src.criativos import midia_propria as m

FIX = Path("tests/fixtures/mixed")


@pytest.fixture(autouse=True)
def _ws(tmp_path, monkeypatch):
    monkeypatch.setenv("REELS_WORKSPACE", str(tmp_path))
    m.ANEXOS.clear()


def _salvar(nome, dados):
    return m.salvar_anexo(nome, io.BytesIO(dados), len(dados))


def test_tipo_do_arquivo():
    assert m.tipo_do_arquivo("a.MOV") == "video" and m.tipo_do_arquivo("b.png") == "imagem"
    assert m.tipo_do_arquivo("c.mp3") == "audio" and m.tipo_do_arquivo("d.exe") is None


def test_recusa_formato_e_arquivo_invalido():
    with pytest.raises(ValueError):
        _salvar("virus.exe", b"abc")
    with pytest.raises(ValueError):
        _salvar("falso.jpg", b"isto nao e uma imagem")
    with pytest.raises(ValueError):
        _salvar("falso.mp4", b"isto nao e um video")


def test_aceita_foto_e_resolve():
    r = _salvar("foto.jpg", (FIX / "img_1.jpg").read_bytes())
    assert r["tipo"] == "imagem" and "caminho" not in r
    assert m.resolver([r["anexo_id"]])[0]["nome"] == "foto.jpg"
    with pytest.raises(ValueError):
        m.resolver(["0" * 32])
