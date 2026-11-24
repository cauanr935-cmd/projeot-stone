"""Endpoints HTTP dos criativos (acoplados ao servidor de src/web_app.py)."""
from __future__ import annotations

import json
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from src.criativos.servico import SAIDA_PADRAO
from src.criativos.spec import carregar_perfis, carregar_perfis_todos

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
                     com_voz=bool(body.get("com_voz", False)))
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


def _progresso(job_id: str):
    def cb(ev: dict) -> None:
        with LOCK:
            j = JOBS[job_id]
            j["percent"] = max(j.get("percent", 0), ev["percent"])
            j["progress"] = ev["message"]
    return cb


def _rodar_pedido(job_id: str, briefing: dict, com_voz: bool, anexos: list[dict] | None = None) -> None:
    from src.criativos import conversa, midia_propria
    try:
        if anexos:
            r = midia_propria.gerar_com_midia(briefing, anexos, job_id[:12], _progresso(job_id), com_voz)
        else:
            r = conversa.gerar_pedido(briefing, com_voz, pedido_id=job_id[:12])
        try:
            from src.analise import legenda_hashtags
            from src.criativos import conversa as _cv
            leg = legenda_hashtags.gerar(briefing.get("negocio") or "Meu negócio", briefing.get("perfil_id", "negocio").replace("_", " "),
                                         briefing.get("oferta") or "nossa novidade", None, briefing.get("cta_canal"))
            (_cv.PASTA_PEDIDOS / f"pedido_{r['pedido_id']}.legenda.txt").write_text(leg["legenda"] + "\n", encoding="utf-8")
        except Exception:
            pass
        with LOCK:
            JOBS[job_id].update(status="done", trace=r["trace"], pedido_id=r["pedido_id"],
                                video=f"/api/pedidos/{r['pedido_id']}/video", legenda=f"/api/pedidos/{r['pedido_id']}/legenda")
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update(status="error", error=str(exc)[:400])


def iniciar_pedido(briefing: dict, com_voz: bool = False, anexos: list[dict] | None = None) -> str:
    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {"status": "running", "pedido_id": job_id[:12]}
    threading.Thread(target=_rodar_pedido, args=(job_id, briefing, com_voz, anexos), daemon=True).start()
    return job_id


def _rodar_carrossel(job_id: str, briefing: dict) -> None:
    from src.criativos import carrossel
    try:
        r = carrossel.gerar(briefing, job_id[:12])
        base = f"/api/carrosseis/{r['carrossel_id']}"
        with LOCK:
            JOBS[job_id].update(status="done", percent=100, carrossel_id=r["carrossel_id"], titulos=r["titulos"],
                                slides=[f"{base}/{n}" for n in r["slides"]], zip=f"{base}/carrossel.zip",
                                legenda=r["legenda"], gerado_por=r["gerado_por"])
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update(status="error", error=str(exc)[:400])


def iniciar_carrossel(briefing: dict) -> str:
    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {"status": "running", "progress": "Escrevendo e desenhando os slides…"}
    threading.Thread(target=_rodar_carrossel, args=(job_id, briefing), daemon=True).start()
    return job_id


def _rodar_edicao(job_id: str, texto: str, anexos: list[dict], continuar_de: str | None = None, conversa: str = "") -> None:
    from src.criativos import sessao_claude
    def atualizar(**kw):
        with LOCK:
            JOBS[job_id].update(kw)
    try:
        r = sessao_claude.editar(texto, anexos, job_id[:12], atualizar, continuar_de, conversa)
        with LOCK:
            JOBS[job_id].update(status="done", percent=100, pedido_id=job_id[:12], **r)
    except sessao_claude.Cancelado:
        sessao_claude.apagar_saida(job_id[:12])  # nada de arquivo pela metade
        with LOCK:
            JOBS[job_id].update(status="cancelado", progress="Geração cancelada.")
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update(status="error", error=str(exc)[:400])


def iniciar_edicao(texto: str, anexos: list[dict], continuar_de: str | None = None, conversa: str = "") -> str:
    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {"status": "running", "pedido_id": job_id[:12], "progress": "Abrindo uma sessão do Claude…"}
    threading.Thread(target=_rodar_edicao, args=(job_id, texto, anexos, continuar_de, conversa), daemon=True).start()
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
    if h.path == "/api/claude/estado":
        from src.claude_conexao import consentimento
        h._json(200, consentimento.estado())
        return True
    if h.path == "/api/claude/historico":
        if not _so_local(h):
            return True
        from src.claude_conexao import chat
        h._json(200, {"mensagens": chat.historico()[-50:]})
        return True
    m = re.fullmatch(r"/api/pedidos/([a-f0-9]{12})(/video|/legenda)?", h.path)
    if m:
        from src.criativos import conversa
        pid, video = m.groups()
        mp4, rac = conversa.arquivos_pedido(pid)
        if video == "/legenda":
            leg = conversa.PASTA_PEDIDOS / f"pedido_{pid}.legenda.txt"
            h._servir_arquivo(leg, "text/plain; charset=utf-8", leg.name) if leg.is_file() else h._json(404, {"error": "Sem legenda."})
        elif video:
            h._servir_arquivo(mp4, "video/mp4", f"criativo-{pid}.mp4") if mp4 else h._json(404, {"error": "Ainda não gerado."})
        elif rac:
            d = json.loads(rac.read_text(encoding="utf-8"))
            d["video"] = f"/api/pedidos/{pid}/video" if mp4 else None
            h._json(200, d)
        else:
            h._json(404, {"error": "Pedido não encontrado."})
        return True
    m = re.fullmatch(r"/api/carrosseis/([a-f0-9]{12})/(slide_\d{2}\.png|carrossel\.zip|legenda\.txt)", h.path)
    if m:
        from src.criativos.carrossel import SAIDA as SAIDA_CARROSSEL
        arq = SAIDA_CARROSSEL / m.group(1) / m.group(2)
        tipo = {"png": "image/png", "zip": "application/zip", "txt": "text/plain; charset=utf-8"}[arq.suffix[1:]]
        h._servir_arquivo(arq, tipo, m.group(2)) if arq.is_file() else h._json(404, {"error": "Ainda não gerado."})
        return True
    if h.path == "/api/sessoes":
        from src.criativos import sessoes
        h._json(200, sessoes.listar())
        return True
    m = re.fullmatch(r"/api/sessoes/([a-f0-9]{12})/exportar", h.path)
    if m:
        from src.criativos import sessoes
        t = sessoes.exportar(m.group(1))
        h._json(200 if t else 404, {"texto": t} if t else {"error": "Sessão não encontrada."})
        return True
    m = re.fullmatch(r"/api/sessoes/([a-f0-9]{12})", h.path)
    if m:
        from src.criativos import sessoes
        s = sessoes.obter(m.group(1))
        h._json(200 if s else 404, s or {"error": "Sessão não encontrada."})
        return True
    if h.path == "/api/edicoes/ranking":
        from src.criativos import memoria_reels
        memoria_reels.pontuar_pendentes()
        h._json(200, memoria_reels.ranking())
        return True
    m = re.fullmatch(r"/api/edicoes/([a-z0-9_]{3,40})/capa_refs", h.path)
    if m:
        from src.criativos import memoria_reels
        h._json(200, memoria_reels.capa_referencias(m.group(1)))
        return True
    m = re.fullmatch(r"/api/edicoes/([a-f0-9]{12})/(final\.mp4|capa\.jpg|decupagem\.md|roteiro\.md|legenda\.txt|creditos_audio\.md|resumo\.md)", h.path)
    if m:
        from src.criativos.sessao_claude import SAIDA
        arq = SAIDA / m.group(1) / m.group(2)
        tipo = {"mp4": "video/mp4", "jpg": "image/jpeg", "md": "text/markdown; charset=utf-8", "txt": "text/plain; charset=utf-8"}[arq.suffix[1:]]
        h._servir_arquivo(arq, tipo, m.group(2)) if arq.is_file() else h._json(404, {"error": "Ainda não gerado."})
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


def _claude_post(h) -> bool:
    from src.claude_conexao import chat, consentimento
    if not _so_local(h):
        return True
    d = _json_body(h, 20000)
    if h.path == "/api/claude/conectar":
        try:
            h._json(200, consentimento.conectar(d.get("escopos")))
        except ValueError as exc:
            h._json(400, {"error": str(exc)})
    elif h.path == "/api/claude/desconectar":
        h._json(200, consentimento.desconectar())
    elif h.path == "/api/claude/chat":
        try:
            fluxo = chat.conversar(str(d.get("texto", "")), cancelado=lambda: False)
            primeiro = next(fluxo, "")
        except chat.ChatIndisponivel as exc:
            h._json(409, {"error": str(exc)})
            return True
        h.send_response(200)
        h.send_header("Content-Type", "text/event-stream; charset=utf-8")
        h.send_header("Cache-Control", "no-store")
        h.send_header("X-Content-Type-Options", "nosniff")
        h.end_headers()
        enviar = lambda o: (h.wfile.write(b"data: " + json.dumps(o, ensure_ascii=False).encode() + b"\n\n"), h.wfile.flush())
        try:
            if primeiro:
                enviar({"t": primeiro})
            for pedaco in fluxo:
                enviar({"t": pedaco})
            enviar({"fim": True})
        except (BrokenPipeError, ConnectionResetError):
            fluxo.close()
        except chat.ChatIndisponivel as exc:
            try:
                enviar({"erro": str(exc)})
            except OSError:
                pass
    else:
        return False
    return True


def _anexos_info(ids) -> list[dict]:
    from src.criativos import midia_propria
    try:
        return midia_propria.resolver(ids) if ids else []
    except ValueError:
        return []


def tratar_post(h) -> bool:
    if h.path.startswith("/api/claude/"):
        return _claude_post(h)
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
    m = re.fullmatch(r"/api/pedido/anexo/([a-f0-9]{32})/apagar", h.path)
    if m:
        if not _so_local(h):
            return True
        from src.criativos import midia_propria
        h._json(200, {"apagado": midia_propria.apagar_anexo(m.group(1))})
        return True
    m = re.fullmatch(r"/api/edicao/([a-f0-9]{32})/cancelar", h.path)
    if m:
        if not _so_local(h):
            return True
        from src.criativos import sessao_claude
        with LOCK:
            existe = JOBS.get(m.group(1), {}).get("status") == "running"
        if existe:
            sessao_claude.cancelar(m.group(1)[:12])
        h._json(200, {"cancelando": existe})
        return True
    if h.path.startswith("/api/pedido/anexo?"):
        if not _so_local(h):
            return True
        from urllib.parse import parse_qs, urlparse
        from src.criativos import midia_propria
        q = parse_qs(urlparse(h.path).query)
        nome = q.get("filename", [""])[0]
        try:
            h._json(201, midia_propria.salvar_anexo(nome, h.rfile, int(h.headers.get("Content-Length", "0")),
                                                    q.get("papel", [None])[0]))
        except (ValueError, OSError) as exc:
            h._json(400, {"error": str(exc)})
        return True
    m = re.fullmatch(r"/api/edicoes/([a-z0-9_]{3,40})/desempenho", h.path)
    if m:
        if not _so_local(h):
            return True
        from src.criativos import memoria_reels
        try:
            h._json(200, memoria_reels.registrar_desempenho(m.group(1), _json_body(h, 2000)))
        except ValueError as exc:
            h._json(400, {"error": str(exc)})
        return True
    if h.path == "/api/edicao/iniciar":
        if not _so_local(h):
            return True
        d = _json_body(h, 60000)
        from src.criativos import midia_propria, sessao_claude
        try:
            anexos = midia_propria.resolver(d.get("anexos") or [])
            sessao_claude.binario()
        except (ValueError, RuntimeError) as exc:
            h._json(400, {"error": str(exc)})
            return True
        if not str(d.get("texto", "")).strip() and not anexos:
            h._json(400, {"error": "Descreva o vídeo ou anexe material."})
            return True
        continuar = str(d.get("continuar_de") or "") or None
        if continuar and not re.fullmatch(r"[a-f0-9]{12}", continuar):
            h._json(400, {"error": "Vídeo anterior inválido."})
            return True
        conversa = ""
        if continuar and d.get("sessao_id"):
            from src.criativos import sessoes
            ses = sessoes.obter(str(d["sessao_id"])) if re.fullmatch(r"[a-f0-9]{12}", str(d["sessao_id"])) else None
            if ses:
                conversa = "\n".join(f"{'PESSOA' if m['papel'] == 'pessoa' else 'ASSISTENTE'}: {m['texto'][:1200]}"
                                     for m in ses["mensagens"][-8:])[-4000:]
        h._json(202, {"job_id": iniciar_edicao(str(d.get("texto", "")), anexos, continuar, conversa)})
        return True
    if h.path.startswith("/api/sessoes"):
        if not _so_local(h):
            return True
        from src.criativos import sessoes
        d = _json_body(h, 200000)
        m = re.fullmatch(r"/api/sessoes/([a-f0-9]{12})/(renomear|apagar|voltar)", h.path)
        try:
            if h.path == "/api/sessoes/salvar":
                h._json(200, sessoes.salvar(d.get("id") or None, str(d.get("tipo", "")), d.get("mensagens"),
                                            d.get("artefatos"), str(d.get("perfil", "")), str(d.get("titulo", "")),
                                            str(d.get("modo", "")), _anexos_info(d.get("anexos"))))
            elif m and m.group(2) == "voltar":
                h._json(200, sessoes.voltar(m.group(1), d.get("n", 2)))
            elif m and m.group(2) == "renomear":
                h._json(200, sessoes.renomear(m.group(1), str(d.get("titulo", ""))))
            elif m:
                sessoes.apagar(m.group(1))
                h._json(200, {"ok": True})
            else:
                return False
        except ValueError as exc:
            h._json(400, {"error": str(exc)})
        return True
    if h.path == "/api/entrevista/responder":
        if not _so_local(h):
            return True
        d = _json_body(h, 60000)
        from src.criativos import entrevista
        try:
            videos = ""
            transc = ""
            if d.get("anexos"):
                from src.criativos import midia_propria
                try:
                    vids = [x for x in midia_propria.resolver(d["anexos"]) if x["tipo"] == "video"]
                    videos = "; ".join(f"{x['nome']} ({x.get('duracao_s')} s)" for x in vids)
                    if str(d.get("modo")) == "edicao":
                        transc = entrevista.transcricao_videos(vids)
                except ValueError:
                    videos = ""
            h._json(200, {"resposta": entrevista.responder(d.get("historico") or [], str(d.get("perfil", "MPE")),
                                                           str(d.get("segmento", "")), str(d.get("contexto", "")),
                                                           str(d.get("modo", "motion")), videos, transc)})
        except (ValueError, RuntimeError) as exc:
            h._json(400, {"error": str(exc)})
        return True
    if h.path == "/api/carrossel/gerar":
        if not _so_local(h):
            return True
        b = _json_body(h, 20000).get("briefing") or {}
        if b.get("perfil_id") not in carregar_perfis_todos():
            h._json(400, {"error": "Falta o ramo do negócio (perfil_id)."})
            return True
        h._json(202, {"job_id": iniciar_carrossel(b)})
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
        if b.get("perfil_id") not in carregar_perfis_todos():
            h._json(400, {"error": "Falta o ramo do negócio (perfil_id)."})
            return True
        from src.criativos import midia_propria
        try:
            anexos = midia_propria.resolver(d.get("anexos") or [])
        except ValueError as exc:
            h._json(400, {"error": str(exc)})
            return True
        if anexos and not any(a["tipo"] in {"video", "imagem"} for a in anexos):
            h._json(400, {"error": "Anexe pelo menos um vídeo ou uma foto (áudio sozinho vira só a trilha)."})
            return True
        h._json(202, {"job_id": iniciar_pedido(b, bool(d.get("com_voz", False)), anexos)})
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
