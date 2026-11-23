"""Endpoints HTTP dos criativos (acoplados ao servidor de src/web_app.py)."""
from __future__ import annotations

import json
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from src.criativos.servico import SAIDA_PADRAO
from src.criativos.spec import carregar_perfis

JOBS: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()


def _arquivos(pid: str) -> tuple[Path | None, Path | None]:
    fid = carregar_perfis()[pid]["format_id"]
    base = SAIDA_PADRAO / f"{pid}_f{fid}"
    mp4, rac = base.with_suffix(".mp4"), SAIDA_PADRAO / f"{pid}_f{fid}.raciocinio.json"
    return (mp4 if mp4.is_file() else None, rac if rac.is_file() else None)


def listar() -> list[dict]:
    out = []
    for pid, p in carregar_perfis().items():
        mp4, rac = _arquivos(pid)
        item = {"id": pid, "nome": p["nome"], "negocio": p["negocio"], "cnae": p["cnae"], "format_id": p["format_id"],
                "paleta": p["paleta"], "gancho": p["gancho"], "dor": p["dor"], "gerado": mp4 is not None,
                "tem_raciocinio": rac is not None}
        if rac:
            r = json.loads(rac.read_text(encoding="utf-8"))
            item["duracao_s"] = (r.get("saida") or {}).get("duracao_s")
            item["motor"] = (r.get("spec") or {}).get("gerado_por")
        out.append(item)
    return out


def detalhe(pid: str) -> dict | None:
    if pid not in carregar_perfis():
        return None
    mp4, rac = _arquivos(pid)
    d = json.loads(rac.read_text(encoding="utf-8")) if rac else {"perfil_id": pid, "perfil": carregar_perfis()[pid], "trace": []}
    d["video"] = f"/api/criativos/{pid}/video" if mp4 else None
    d["gerado"] = mp4 is not None
    return d


def _rodar(job_id: str, pid: str, body: dict) -> None:
    from src.criativos.grafo import executar
    try:
        r = executar(pid, body.get("negocio") or None, body.get("formato_id"), body.get("instrucoes") or None,
                     com_voz=bool(body.get("com_voz", True)))
        with LOCK:
            JOBS[job_id].update(status="done", trace=r["trace"])
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update(status="error", error=str(exc)[:400])


def iniciar(pid: str, body: dict) -> str:
    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {"status": "running", "perfil_id": pid}
    threading.Thread(target=_rodar, args=(job_id, pid, body), daemon=True).start()
    return job_id


def _rodar_pedido(job_id: str, briefing: dict, com_voz: bool) -> None:
    from src.criativos import conversa
    try:
        r = conversa.gerar_pedido(briefing, com_voz, pedido_id=job_id[:12])
        with LOCK:
            JOBS[job_id].update(status="done", trace=r["trace"], pedido_id=r["pedido_id"],
                                video=f"/api/pedidos/{r['pedido_id']}/video")
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update(status="error", error=str(exc)[:400])


def iniciar_pedido(briefing: dict, com_voz: bool = True) -> str:
    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {"status": "running", "pedido_id": job_id[:12]}
    threading.Thread(target=_rodar_pedido, args=(job_id, briefing, com_voz), daemon=True).start()
    return job_id


def _json_body(h, limite: int = 20000) -> dict:
    n = int(h.headers.get("Content-Length", "0"))
    if not 0 < n <= limite:
        return {}
    try:
        d = json.loads(h.rfile.read(n))
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}


def tratar_get(h) -> bool:
    """Retorna True se tratou a rota."""
    m = re.fullmatch(r"/api/pedidos/([a-f0-9]{12})(/video)?", h.path)
    if m:
        from src.criativos import conversa
        pid, video = m.groups()
        mp4, rac = conversa.arquivos_pedido(pid)
        if video:
            h._servir_arquivo(mp4, "video/mp4", f"criativo-{pid}.mp4") if mp4 else h._json(404, {"error": "Ainda não gerado."})
        elif rac:
            d = json.loads(rac.read_text(encoding="utf-8"))
            d["video"] = f"/api/pedidos/{pid}/video" if mp4 else None
            h._json(200, d)
        else:
            h._json(404, {"error": "Pedido não encontrado."})
        return True
    if h.path == "/api/criativos":
        h._json(200, listar())
        return True
    m = re.fullmatch(r"/api/criativos/([a-z_]+)(/video)?", h.path)
    if m:
        pid, video = m.groups()
        if pid == "jobs":
            return False
        d = detalhe(pid)
        if d is None:
            h._json(404, {"error": "Perfil inexistente."})
        elif not video:
            h._json(200, d)
        else:
            mp4, _ = _arquivos(pid)
            h._servir_arquivo(mp4, "video/mp4", f"criativo-{pid}.mp4") if mp4 else h._json(404, {"error": "Ainda não gerado."})
        return True
    m = re.fullmatch(r"/api/criativos/jobs/([a-f0-9]{32})", h.path)
    if m:
        with LOCK:
            j = JOBS.get(m.group(1))
        h._json(200 if j else 404, j or {"error": "Job não encontrado."})
        return True
    return False


def _so_local(h) -> bool:
    if h.client_address[0] in {"127.0.0.1", "::1"}:
        return True
    h._json(403, {"error": "Somente conexões locais."})
    return False


def tratar_post(h) -> bool:
    if h.path == "/api/voz/transcrever":
        if not _so_local(h):
            return True
        from src.criativos import transcricao
        n = int(h.headers.get("Content-Length", "0"))
        if not 0 < n <= transcricao.MAX_BYTES:
            h._json(413, {"error": "Áudio vazio ou maior que 25 MB."})
            return True
        ctype = (h.headers.get("Content-Type") or "").lower()
        suf = next((v for k, v in (("webm", ".webm"), ("ogg", ".ogg"), ("mp4", ".mp4"), ("wav", ".wav"), ("mpeg", ".mp3")) if k in ctype), ".webm")
        try:
            h._json(200, transcricao.transcrever_bytes(h.rfile.read(n), suf))
        except (ValueError, OSError) as exc:
            h._json(400, {"error": str(exc)})
        return True
    if h.path == "/api/pedido/interpretar":
        from src.criativos import conversa
        d = _json_body(h)
        h._json(200, conversa.interpretar(str(d.get("texto", ""))[:4000], d.get("estado")))
        return True
    if h.path == "/api/pedido/gerar":
        if not _so_local(h):
            return True
        d = _json_body(h, 60000)
        b = d.get("briefing") or {}
        if b.get("perfil_id") not in carregar_perfis():
            h._json(400, {"error": "Falta o ramo do negócio (perfil_id)."})
            return True
        h._json(202, {"job_id": iniciar_pedido(b, bool(d.get("com_voz", True)))})
        return True
    m = re.fullmatch(r"/api/criativos/([a-z_]+)/gerar", h.path)
    if not m:
        return False
    if m.group(1) not in carregar_perfis():
        h._json(404, {"error": "Perfil inexistente."})
        return True
    if h.client_address[0] not in {"127.0.0.1", "::1"}:
        h._json(403, {"error": "Somente conexões locais."})
        return True
    n = int(h.headers.get("Content-Length", "0"))
    body = json.loads(h.rfile.read(n)) if 0 < n <= 20000 else {}
    h._json(202, {"job_id": iniciar(m.group(1), body)})
    return True
