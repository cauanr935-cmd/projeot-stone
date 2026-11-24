"""Efeitos sonoros (src/editing/sfx.py): cascata local → procedural, linha do tempo, trava de licença. Sem rede."""
import json
import wave
from types import SimpleNamespace

import numpy as np
import pytest

from src.editing import sfx


def _cena(tipo, itens=()):
    return SimpleNamespace(tipo=tipo, itens=list(itens))


CENAS = [_cena("hook"), _cena("pontos", ["a", "b", "c"]), _cena("numero"), _cena("cta")]
DURS = [3.0, 4.0, 3.0, 4.0]


@pytest.fixture(autouse=True)
def _isolado(tmp_path, monkeypatch):
    monkeypatch.setattr(sfx, "BIBLIOTECA", tmp_path / "lib")   # biblioteca vazia: tudo cai no procedural
    sfx._CACHE.clear()
    yield
    sfx._CACHE.clear()


@pytest.mark.parametrize("nome", list(sfx.GERADORES))
def test_geradores_sao_validos(nome):
    x = sfx.GERADORES[nome]()
    assert x.dtype == np.float32 and x.size > 0 and np.isfinite(x).all()
    assert 0.5 < np.abs(x).max() <= 0.95          # normalizado, sem clipping


def test_eventos_seguem_a_animacao():
    ev = sfx.eventos_do_criativo(CENAS, DURS)
    assert [e.t for e in ev] == sorted(e.t for e in ev)
    assert sum(e.nome == "pop" for e in ev if 3.0 <= e.t < 7.0) == 3          # 1 pop por item da cena 'pontos'
    assert sum(e.nome in ("whoosh", "swipe") for e in ev if e.t not in (0,)) >= len(CENAS) - 1   # 1 transição por troca de cena
    assert any(e.nome == "sucesso" for e in ev) and any(e.nome in ("boom", "impact") and e.t < 1 for e in ev)
    assert all(e.t < sum(DURS) for e in ev)


def test_trilha_wav_e_proveniencia(tmp_path):
    info = sfx.gerar_trilha_sfx(CENAS, DURS, tmp_path / "fx.wav", commercial=True)
    with wave.open(info["arquivo"]) as w:
        assert w.getframerate() == sfx.SR and w.getnchannels() == 1 and w.getnframes() > sum(DURS) * sfx.SR
    assert info["eventos"] > 5
    assert {m["tier"] for m in info["efeitos"].values()} == {"procedural"}
    assert info["avisos_licenca"] == []


def test_biblioteca_local_tem_prioridade(tmp_path, monkeypatch):
    lib = tmp_path / "lib"
    lib.mkdir()
    tom = (np.sin(2 * np.pi * 440 * np.arange(sfx.SR // 4) / sfx.SR) * 32767 * 0.5).astype("<i2")
    with wave.open(str(lib / "pop_01.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(sfx.SR)
        w.writeframes(tom.tobytes())
    (lib / "pop_01.wav.json").write_text(json.dumps({"license_key": "local-cc0", "licenca": "CC0-1.0"}))
    _, meta = sfx.resolver("pop")
    assert meta["tier"] == "local_cc0_library" and meta["license_key"] == "local-cc0"
    assert sfx.resolver("tick")[1]["tier"] == "procedural"                    # sem arquivo: procedural


def test_arquivo_corrompido_cai_no_procedural(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "whoosh_01.wav").write_bytes(b"isto nao e audio")
    assert sfx.resolver("whoosh")[1]["tier"] == "procedural"


def test_openverse_bloqueia_freesound_sem_liberacao(monkeypatch):
    fake = [{"id": "1", "title": "x", "license": "cc0", "duration": 500, "url": "http://x/a.mp3", "source": "freesound"},
            {"id": "2", "title": "y", "license": "cc0", "duration": 500, "url": "http://x/b.mp3", "source": "wikimedia"}]

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"results": fake}).encode()

    monkeypatch.setattr(sfx.urllib.request, "urlopen", lambda *a, **k: R())
    monkeypatch.delenv("REELS_ALLOW_FREESOUND_CC0", raising=False)
    permitidos = {c["origem"]: c["permitido"] for c in sfx.buscar_openverse("x")}
    assert permitidos == {"freesound": False, "wikimedia": True}
    monkeypatch.setenv("REELS_ALLOW_FREESOUND_CC0", "1")
    assert all(c["permitido"] for c in sfx.buscar_openverse("x"))


def test_fonte_openverse_gera_aviso_de_revisao(tmp_path):
    from src.router.license_guard import validate_commercial_sources
    avisos = validate_commercial_sources(["openverse-cc0", "procedural-sfx", "local-cc0"], True)
    assert [a["source"] for a in avisos] == ["openverse-cc0"]


def test_variantes_em_rodizio(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    for k, f in enumerate((300, 600, 900), 1):
        tom = (np.sin(2 * np.pi * f * np.arange(sfx.SR // 5) / sfx.SR) * 32767 * 0.5).astype("<i2")
        with wave.open(str(lib / f"pop_{k:02d}.wav"), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(sfx.SR)
            w.writeframes(tom.tobytes())
    sons = [sfx.resolver("pop", k)[0] for k in range(4)]
    assert not np.allclose(sons[0][:2000], sons[1][:2000]) and not np.allclose(sons[1][:2000], sons[2][:2000])
    assert np.allclose(sons[0], sons[3])                                     # a 4ª volta recomeça da 1ª
    ev = [e for e in sfx.eventos_do_criativo([_cena("pontos", list("abc"))], [5.0]) if e.nome == "pop"]
    assert [e.variante for e in ev] == [0, 1, 2]                             # cada item pega uma variante diferente


def test_prefixo_nao_confunde_nomes(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "ticket_01.wav").write_bytes(b"x")
    (lib / "tick_01.wav").write_bytes(b"x")
    assert [a.name for a in sfx.arquivos_da_biblioteca("tick")] == ["tick_01.wav"]


def test_aparar_remove_silencio_inicial():
    x = np.concatenate([np.zeros(sfx.SR // 2), np.ones(sfx.SR // 10) * 0.8]).astype(np.float32)
    y = sfx._aparar(x)
    assert y.size < sfx.SR // 5 and np.abs(y[: int(0.02 * sfx.SR)]).max() > 0.1     # o som começa no instante zero


def test_controle_de_qualidade():
    assert sfx._reprova(np.zeros(sfx.SR, dtype=np.float32)) == "quase mudo"
    assert sfx._reprova(np.ones(10, dtype=np.float32)) == "curto demais"
    assert sfx._reprova(sfx.pop()) is None
    assert not sfx._titulo_ok("Epic music loop") and sfx._titulo_ok("Swipe Whoosh")


def test_nomes_com_alias_tem_fallback_procedural():
    for nome in sfx.NOMES:
        assert sfx.resolver(nome)[1]["tier"] == "procedural"
