import json
import stat

import pytest

from src.criativos import sessao_claude as sc


def _falso(tmp_path, corpo: str):
    b = tmp_path / "claude"
    b.write_text("#!/usr/bin/env python3\nimport sys,json,pathlib\n" + corpo)
    b.chmod(b.stat().st_mode | stat.S_IEXEC)
    return str(b)


ANEXO = [{"tipo": "video", "caminho": "/tmp/x/arquivo.mp4", "nome": "a.mp4", "duracao_s": 12.0}]


def test_prompt_cita_skill_arquivos_e_pasta(tmp_path):
    p = sc.montar_prompt("quero cortes", ANEXO, tmp_path)
    assert sc.SKILL in p and "/tmp/x/arquivo.mp4" in p and str(tmp_path) in p


def test_edicao_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SAIDA", tmp_path / "out")
    corpo = (
        "d=pathlib.Path(sys.argv[sys.argv.index('--add-dir')+1]); (d/'final.mp4').write_bytes(b'x')\n"
        "print(json.dumps({'type':'assistant','message':{'content':[{'type':'tool_use','name':'Bash','input':{'command':'ffmpeg'}}]}}))\n"
        "print(json.dumps({'type':'result','result':'cortei 3 pausas','is_error':False}))\n")
    monkeypatch.setenv("REELS_CLAUDE_BIN", _falso(tmp_path, corpo))
    eventos = []
    r = sc.editar("oi", ANEXO, "abc123abc123", lambda **k: eventos.append(k))
    assert r["video"].endswith("/final.mp4") and "cortei" in r["resumo"] and eventos[0]["progress"].startswith("Bash")


def test_edicao_sem_final_falha(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "SAIDA", tmp_path / "out")
    monkeypatch.setenv("REELS_CLAUDE_BIN", _falso(tmp_path, "print(json.dumps({'type':'result','result':'ok','is_error':False}))\n"))
    with pytest.raises(RuntimeError, match="final.mp4"):
        sc.editar("oi", ANEXO, "abc123abc123", lambda **k: None)


def test_sem_binario(monkeypatch):
    monkeypatch.delenv("REELS_CLAUDE_BIN", raising=False)
    monkeypatch.setattr(sc.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="Claude Code"):
        sc.binario()
