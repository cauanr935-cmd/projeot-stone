"""Anexos do chat: o usuário envia quantos vídeos, fotos e áudios quiser e o Reel é montado com a mídia dele.

Reaproveita o pipeline de mídia própria (src.director.edit_plan + src.renderer.reel_assembler) com os mesmos parâmetros
do antigo editor (formato, CNAE, nome do negócio, produto, canal, contexto, roteiro, fala/música), mas é independente
da página/endpoints do editor: ele pode ser removido sem afetar o chat.

Vídeos e fotos viram cenas; o 1º áudio enviado vira a trilha sonora. Privacidade: nada sai da máquina por aqui
(o pipeline local segue as regras de licença/privacidade do projeto).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any, Callable

from src.core.config import ROOT

TIPOS = {
    "video": ({".mp4", ".mov", ".m4v", ".webm", ".mkv"}, 500 * 1024 * 1024),
    "imagem": ({".jpg", ".jpeg", ".png", ".webp"}, 25 * 1024 * 1024),
    "audio": ({".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}, 100 * 1024 * 1024),
}
MAX_ANEXOS = 50
ANEXOS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


def workspace() -> Path:
    return Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve()


def tipo_do_arquivo(nome: str) -> str | None:
    suf = Path(nome).suffix.lower()
    return next((t for t, (exts, _) in TIPOS.items() if suf in exts), None)


def salvar_anexo(filename: str, source, length: int) -> dict:
    """Grava um arquivo enviado (corpo bruto) e valida; devolve {anexo_id, nome, tipo, duracao_s}."""
    nome = Path(filename or "").name
    tipo = tipo_do_arquivo(nome)
    if tipo is None:
        raise ValueError("Formato não aceito. Envie vídeo (MP4, MOV, WebM, MKV), foto (JPG, PNG, WebP) ou áudio (MP3, WAV, M4A).")
    limite = TIPOS[tipo][1]
    if not 0 < length <= limite:
        raise ValueError(f"O arquivo está vazio ou passa de {limite // (1024 * 1024)} MB.")
    with _LOCK:
        if len(ANEXOS) >= MAX_ANEXOS * 4:
            raise ValueError("Muitos arquivos enviados nesta sessão. Reinicie o servidor para limpar.")
    aid = uuid.uuid4().hex
    pasta = workspace() / "chat_anexos" / aid
    pasta.mkdir(parents=True, exist_ok=False)
    destino = pasta / f"arquivo{Path(nome).suffix.lower()}"
    try:
        restante = length
        with destino.open("wb") as f:
            while restante:
                bloco = source.read(min(1024 * 1024, restante))
                if not bloco:
                    raise ValueError("O envio foi interrompido antes de terminar.")
                f.write(bloco)
                restante -= len(bloco)
        duracao = None
        if tipo == "imagem":
            from PIL import Image
            with Image.open(destino) as im:
                im.verify()
        else:
            from src.core.ffmpeg import ffprobe_json
            probe = ffprobe_json(destino)
            streams = {s.get("codec_type") for s in probe.get("streams", [])}
            if ("video" if tipo == "video" else "audio") not in streams:
                raise ValueError("O arquivo não tem uma faixa de " + ("vídeo" if tipo == "video" else "áudio") + " válida.")
            duracao = round(float(probe.get("format", {}).get("duration", 0) or 0), 1)
            if tipo == "audio" and not 0 < duracao <= 900:
                raise ValueError("O áudio deve ter entre 1 segundo e 15 minutos.")
    except Exception as exc:
        shutil.rmtree(pasta, ignore_errors=True)
        if isinstance(exc, ValueError):
            raise
        raise ValueError("Não consegui ler esse arquivo. Confira se ele abre normalmente.") from exc
    info = {"anexo_id": aid, "nome": nome, "tipo": tipo, "duracao_s": duracao, "caminho": str(destino)}
    with _LOCK:
        ANEXOS[aid] = info
    return {k: v for k, v in info.items() if k != "caminho"}


def registrar_arquivo_local(caminho: Path) -> dict:
    """Registra um arquivo que já está no disco (usado pelo MCP, depois de validar Roots)."""
    nome = Path(caminho).name
    with open(caminho, "rb") as f:
        return salvar_anexo(nome, f, Path(caminho).stat().st_size)


def resolver(ids: list[str]) -> list[dict]:
    if not isinstance(ids, list) or len(ids) > MAX_ANEXOS:
        raise ValueError(f"Envie no máximo {MAX_ANEXOS} arquivos por pedido.")
    out = []
    with _LOCK:
        for i in ids:
            if not isinstance(i, str) or not re.fullmatch(r"[a-f0-9]{32}", i) or i not in ANEXOS:
                raise ValueError("Um arquivo enviado expirou. Anexe-o novamente.")
            out.append(ANEXOS[i])
    return out


def gerar_com_midia(briefing: dict, anexos: list[dict], pedido_id: str,
                    progresso: Callable[[dict], None] | None = None, com_voz: bool = False) -> dict:
    """Monta o Reel com a mídia do usuário. Retorna {pedido_id, saida, trace}; grava output/pedidos/pedido_<id>.*"""
    from src.core.progress import Reporter
    from src.criativos import conversa
    from src.criativos.spec import obter_perfil
    from src.director.edit_plan import build_edit_plan
    from src.renderer.reel_assembler import assemble_and_render_reel

    visuais = [a for a in anexos if a["tipo"] in {"video", "imagem"}]
    audios = [a for a in anexos if a["tipo"] == "audio"]
    if not visuais:
        raise ValueError("Anexe pelo menos um vídeo ou uma foto.")
    perfil = obter_perfil(briefing["perfil_id"])
    a = conversa.aplicar_briefing(briefing)
    report = Reporter(progresso)
    job_dir = workspace() / "jobs" / f"pedido_{pedido_id}"
    entradas = job_dir / "inputs"
    if job_dir.exists():
        shutil.rmtree(job_dir)
    entradas.mkdir(parents=True)
    report("intake", 0.0, f"Preparando {len(visuais)} arquivo(s)")
    for i, x in enumerate(visuais, 1):
        shutil.copy2(x["caminho"], entradas / f"midia_{i:02d}{Path(x['caminho']).suffix}")
        report("intake", i / len(visuais), f"Arquivo {i} de {len(visuais)} preparado")
    musica = None
    if audios:
        musica = job_dir / f"trilha{Path(audios[0]['caminho']).suffix}"
        shutil.copy2(audios[0]["caminho"], musica)
    formato = int(a["formato_id"] or perfil["format_id"])
    plano = build_edit_plan(entradas, formato, perfil["cnae"], f"pedido_{pedido_id}", a["negocio"], briefing.get("oferta"),
                            briefing.get("cta_canal") or perfil["cta_canal"], commercial=True, context=a["instrucoes"],
                            custom_script=a["roteiro_usuario"], speech_enabled=com_voz, music_enabled=True,
                            keep_source_audio=False, progress=report)
    saida_dir = ROOT / "output" / "pedidos"
    saida_dir.mkdir(parents=True, exist_ok=True)
    mp4 = saida_dir / f"pedido_{pedido_id}.mp4"
    rel = assemble_and_render_reel(plano, mp4, commercial=True, progress=report, music_path=musica)
    trace = [
        {"no": "midia", "titulo": "Usei a sua mídia",
         "resumo": f"{sum(x['tipo'] == 'video' for x in visuais)} vídeo(s) e {sum(x['tipo'] == 'imagem' for x in visuais)} foto(s)"
                   + (", mais o seu áudio como trilha." if musica else ".")},
        {"no": "formato", "titulo": f"Formato {plano['format']['name']}",
         "resumo": f"Escolhido para o ramo {perfil['nome']} (CNAE {perfil['cnae']}); duração alvo {plano['duration']['target']} s."},
        {"no": "roteiro", "titulo": "Roteiro", "resumo": ("Usei o roteiro que você deu." if a["roteiro_usuario"]
                                                      else "Montei o roteiro do formato com o seu negócio e oferta.")},
        {"no": "render", "titulo": "Renderizei e auditei", "resumo": "1080×1920, H.264, com voz, legenda e música locais."},
    ]
    (saida_dir / f"pedido_{pedido_id}.raciocinio.json").write_text(
        json.dumps({"briefing": briefing, "trace": trace, "origem": "midia_propria"}, ensure_ascii=False, indent=2), encoding="utf-8")
    saida = {"output": str(mp4), **{k: v for k, v in (rel or {}).items() if k in {"duration_s", "duracao_s", "passed", "audit"}}}
    return {"pedido_id": pedido_id, "saida": saida, "trace": trace}
