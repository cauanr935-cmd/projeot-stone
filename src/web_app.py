from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.core.config import ROOT, load_formats

load_dotenv(ROOT / ".env")

MAX_VIDEO_BYTES = 500 * 1024 * 1024
MAX_AUDIO_BYTES = 100 * 1024 * 1024
MAX_REQUEST_BYTES = 8 * 1024 * 1024
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
WORKSPACE = Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve()
WEB_DIR = ROOT / "src" / "web"
JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
UPLOADS: dict[str, Path] = {}
UPLOADS_LOCK = threading.Lock()
AUDIO_UPLOADS: dict[str, Path] = {}
AUDIO_UPLOADS_LOCK = threading.Lock()


class InvalidVideoURL(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise InvalidVideoURL("O link redireciona para outro endereço. Use um link direto para o arquivo de vídeo.")


def parse_video_urls(value: str) -> list[str]:
    urls = [line.strip() for line in value.splitlines() if line.strip()]
    if not urls:
        raise ValueError("Cole ao menos um link direto de vídeo.")
    if len(set(urls)) != len(urls):
        raise ValueError("Há links repetidos na lista.")
    for url in urls:
        _validate_public_http_url(url)
    return urls


def _validate_public_http_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise InvalidVideoURL("Use links HTTP/HTTPS diretos para arquivos de vídeo.")
    if parsed.username or parsed.password:
        raise InvalidVideoURL("O link não pode conter usuário ou senha.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise InvalidVideoURL("A porta do link é inválida.") from exc
    if port not in {None, 80, 443}:
        raise InvalidVideoURL("Só são aceitos links HTTP/HTTPS nas portas padrão.")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost") or host.endswith(".local"):
        raise InvalidVideoURL("Links para a própria máquina ou rede local não são permitidos.")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, port or (443 if parsed.scheme == "https" else 80),
                                               type=socket.SOCK_STREAM)
            }
        except socket.gaierror as exc:
            raise InvalidVideoURL("O domínio do link não pôde ser resolvido.") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise InvalidVideoURL("Links para endereços privados ou reservados não são permitidos.")


def download_video(url: str, destination: Path) -> None:
    _validate_public_http_url(url)
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "ImpulsoStoneReels/1.0"})
    try:
        with opener.open(request, timeout=20) as response:
            content_type = response.headers.get_content_type()
            if not (content_type.startswith("video/") or content_type == "application/octet-stream"):
                raise InvalidVideoURL("O endereço não respondeu com um arquivo de vídeo direto.")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_VIDEO_BYTES:
                raise InvalidVideoURL("O vídeo excede o limite de 500 MB.")
            total = 0
            with destination.open("wb") as target:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_VIDEO_BYTES:
                        raise InvalidVideoURL("O vídeo excede o limite de 500 MB.")
                    target.write(chunk)
    except (urllib.error.URLError, TimeoutError) as exc:
        destination.unlink(missing_ok=True)
        raise InvalidVideoURL(f"Não foi possível baixar o vídeo: {exc.reason if hasattr(exc, 'reason') else exc}") from exc
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    if total == 0:
        destination.unlink(missing_ok=True)
        raise InvalidVideoURL("O link retornou um arquivo vazio.")


def save_uploaded_video(filename: str, source, content_length: int) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in VIDEO_SUFFIXES:
        raise ValueError("Selecione um arquivo de vídeo MP4, MOV, M4V, WebM ou MKV.")
    if not 0 < content_length <= MAX_VIDEO_BYTES:
        raise ValueError("O arquivo está vazio ou excede o limite de 500 MB.")

    upload_id = uuid.uuid4().hex
    upload_dir = WORKSPACE / "uploads" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=False)
    destination = upload_dir / f"video{suffix}"
    remaining = content_length
    try:
        with destination.open("wb") as target:
            while remaining:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("O envio do arquivo foi interrompido antes de terminar.")
                target.write(chunk)
                remaining -= len(chunk)

        from src.core.ffmpeg import ffprobe_json
        probe = ffprobe_json(destination)
        if not any(stream.get("codec_type") == "video" for stream in probe.get("streams", [])):
            raise ValueError("O arquivo selecionado não contém uma faixa de vídeo válida.")
        with UPLOADS_LOCK:
            UPLOADS[upload_id] = destination
        return upload_id, Path(filename).name
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise


def save_uploaded_audio(filename: str, source, content_length: int) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in AUDIO_SUFFIXES:
        raise ValueError("Selecione uma música MP3, WAV, M4A, AAC, OGG ou FLAC.")
    if not 0 < content_length <= MAX_AUDIO_BYTES:
        raise ValueError("A música está vazia ou excede o limite de 100 MB.")

    upload_id = uuid.uuid4().hex
    upload_dir = WORKSPACE / "uploads" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=False)
    destination = upload_dir / f"music{suffix}"
    remaining = content_length
    try:
        with destination.open("wb") as target:
            while remaining:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("O envio da música foi interrompido antes de terminar.")
                target.write(chunk)
                remaining -= len(chunk)

        from src.core.ffmpeg import ffprobe_json
        probe = ffprobe_json(destination)
        if not any(stream.get("codec_type") == "audio" for stream in probe.get("streams", [])):
            raise ValueError("O arquivo selecionado não contém uma faixa de áudio válida.")
        duration = float(probe.get("format", {}).get("duration", 0) or 0)
        if not 0 < duration <= 900:
            raise ValueError("A música deve ter duração entre 1 segundo e 15 minutos.")
        with AUDIO_UPLOADS_LOCK:
            AUDIO_UPLOADS[upload_id] = destination
        return upload_id, Path(filename).name
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise


def validate_audio_upload_id(upload_id: Any) -> str:
    if not isinstance(upload_id, str) or not re.fullmatch(r"[a-f0-9]{32}", upload_id):
        raise ValueError("O identificador da música enviada é inválido.")
    with AUDIO_UPLOADS_LOCK:
        if upload_id not in AUDIO_UPLOADS:
            raise ValueError("A música enviada expirou. Selecione o arquivo novamente.")
    return upload_id


def validate_upload_ids(upload_ids: Any) -> list[str]:
    if not isinstance(upload_ids, list) or not upload_ids:
        raise ValueError("Selecione ao menos um vídeo ou pasta com arquivos de vídeo.")
    if not all(isinstance(item, str) and re.fullmatch(r"[a-f0-9]{32}", item) for item in upload_ids):
        raise ValueError("A lista de vídeos enviados é inválida.")
    if len(set(upload_ids)) != len(upload_ids):
        raise ValueError("A lista contém vídeos repetidos.")
    with UPLOADS_LOCK:
        if any(item not in UPLOADS for item in upload_ids):
            raise ValueError("Um arquivo enviado expirou. Selecione os vídeos novamente.")
    return upload_ids


def _update_job(job_id: str, **values: Any) -> None:
    with JOBS_LOCK:
        JOBS[job_id].update(values)


def _job_progress(job_id: str):
    """Callback que grava etapa, porcentagem e histórico de eventos no job."""
    def callback(event: dict) -> None:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["stage"] = event["stage"]
            job["percent"] = max(job.get("percent", 0), event["percent"])  # nunca regride
            job["progress"] = event["message"]
            events = job.setdefault("events", [])
            if not events or events[-1]["message"] != event["message"]:
                events.append({"t": event["elapsed_s"], "stage": event["stage"], "message": event["message"]})
                del events[:-200]
    return callback


def _render_job(job_id: str, data: dict[str, Any], urls: list[str], upload_ids: list[str],
                music_upload_id: str | None = None) -> None:
    job_dir = WORKSPACE / "jobs" / job_id
    inputs_dir = job_dir / "inputs"
    from src.core.progress import Reporter
    report = Reporter(_job_progress(job_id))
    try:
        _update_job(job_id, status="downloading")
        report("intake", 0.0, "Baixando vídeos dos links" if urls else "Preparando vídeos enviados")
        inputs_dir.mkdir(parents=True, exist_ok=False)
        if upload_ids:
            upload_paths = []
            with UPLOADS_LOCK:
                for upload_id in upload_ids:
                    upload_path = UPLOADS.pop(upload_id, None)
                    if upload_path is None:
                        raise ValueError("Um dos arquivos enviados expirou. Selecione os vídeos novamente.")
                    upload_paths.append(upload_path)
            for index, upload_path in enumerate(upload_paths, 1):
                destination = inputs_dir / f"video_{index:02d}{upload_path.suffix}"
                shutil.copy2(upload_path, destination)
                shutil.rmtree(upload_path.parent, ignore_errors=True)
                report("intake", index / len(upload_paths), f"Vídeo {index} de {len(upload_paths)} preparado")
        else:
            for index, url in enumerate(urls, 1):
                parsed_path = urllib.parse.urlsplit(url).path
                suffix = Path(parsed_path).suffix.lower()
                if suffix not in VIDEO_SUFFIXES:
                    suffix = ".mp4"
                destination = inputs_dir / f"video_{index:02d}{suffix}"
                report("intake", (index - 1) / len(urls), f"Baixando vídeo {index} de {len(urls)}")
                download_video(url, destination)
                report("intake", index / len(urls), f"Vídeo {index} de {len(urls)} baixado")

        report("intake", 1.0, "Vídeos recebidos")
        music_path = None
        if music_upload_id:
            with AUDIO_UPLOADS_LOCK:
                uploaded_music = AUDIO_UPLOADS.pop(music_upload_id, None)
            if uploaded_music is None:
                raise ValueError("A música enviada expirou. Selecione o arquivo novamente.")
            music_dir = job_dir / "music_input"
            music_dir.mkdir(parents=True, exist_ok=False)
            music_path = music_dir / f"soundtrack{uploaded_music.suffix}"
            shutil.copy2(uploaded_music, music_path)
            shutil.rmtree(uploaded_music.parent, ignore_errors=True)
            report("intake", 1.0, "Trilha sonora recebida")
        _update_job(job_id, status="planning")
        from src.director.edit_plan import build_edit_plan
        plan = build_edit_plan(
            inputs_dir,
            int(data["format_id"]),
            data.get("cnae_code"),
            job_id,
            data.get("business_name"),
            data.get("product"),
            data.get("cta_channel") or "WhatsApp",
            commercial=bool(data.get("commercial", True)),
            context=data.get("context"),
            custom_script=data.get("custom_script"),
            speech_enabled=bool(data.get("speech_enabled", True)),
            music_enabled=bool(data.get("music_enabled", True)),
            keep_source_audio=bool(data.get("keep_source_audio", False)),
            progress=report,
        )
        _update_job(job_id, status="rendering")
        from src.renderer.reel_assembler import assemble_and_render_reel
        output_path = job_dir / "reel_final.mp4"
        report = assemble_and_render_reel(plan, output_path, commercial=bool(data.get("commercial", True)),
                                         progress=report, music_path=music_path)
        _update_job(job_id, status="done", progress="Reel pronto.", percent=100, output=str(output_path),
                    download_url=f"/api/jobs/{job_id}/download", report=report)
    except Exception as exc:
        _update_job(job_id, status="error", progress="A geração falhou.", error=str(exc))
        with JOBS_LOCK:
            JOBS[job_id].setdefault("events", []).append(
                {"t": round(time.monotonic() - JOBS[job_id]["started_mono"], 1),
                 "stage": JOBS[job_id].get("stage", "intake"), "message": f"Erro: {exc}"[:400]})


class ReelRequestHandler(BaseHTTPRequestHandler):
    server_version = "ImpulsoReelsWeb/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, data: Any) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            body = (WEB_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/formats":
            self._json(200, [{"id": item["id"], "name": item["name"], "focus": item["focus"],
                              "duration": item["duration"]} for item in load_formats()])
            return
        if self.path == "/api/stages":
            from src.core.progress import stage_catalog
            self._json(200, stage_catalog())
            return
        match = re.fullmatch(r"/api/jobs/([a-f0-9]{32})(/download|/preview)?", self.path)
        if match:
            job_id, action = match.groups()
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                self._json(404, {"error": "Job não encontrado neste servidor."})
                return
            if not action:
                with JOBS_LOCK:
                    snapshot = {key: value for key, value in job.items() if key not in {"report", "started_mono"}}
                    snapshot["events"] = list(job.get("events", []))
                    snapshot["elapsed_s"] = round(time.monotonic() - job["started_mono"], 1)
                if job.get("report"):
                    snapshot["audit"] = job["report"].get("audit")
                    snapshot["viral"] = job["report"].get("viral")
                self._json(200, snapshot)
                return
            output_path = Path(job.get("output", "")).resolve()
            jobs_root = (WORKSPACE / "jobs").resolve()
            if job["status"] != "done" or jobs_root not in output_path.parents or not output_path.is_file():
                self._json(404, {"error": "A prévia do Reel ainda não está disponível."})
                return
            file_size = output_path.stat().st_size
            start, end = 0, file_size - 1
            status = 200
            range_header = self.headers.get("Range") if action == "/preview" else None
            if range_header:
                match_range = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
                if not match_range or not any(match_range.groups()) or file_size == 0:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                first, last = match_range.groups()
                if first:
                    start = int(first)
                    end = min(int(last), file_size - 1) if last else file_size - 1
                else:
                    suffix_length = int(last)
                    if suffix_length <= 0:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{file_size}")
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                    start = max(0, file_size - suffix_length)
                if start >= file_size or end < start:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status = 206
            content_length = end - start + 1
            self.send_response(status)
            self.send_header("Content-Type", "video/mp4")
            disposition = "inline" if action == "/preview" else "attachment"
            self.send_header("Content-Disposition", f'{disposition}; filename="reel-{job_id[:8]}.mp4"')
            self.send_header("Content-Length", str(content_length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-store")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            with output_path.open("rb") as source:
                source.seek(start)
                remaining = content_length
                while remaining and (chunk := source.read(min(1024 * 1024, remaining))):
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            return
        self._json(404, {"error": "Endpoint não encontrado."})

    def do_POST(self) -> None:
        if self.path.startswith("/api/uploads?"):
            self._receive_upload()
            return
        if self.path != "/api/jobs":
            self._json(404, {"error": "Endpoint não encontrado."})
            return
        if self.client_address[0] not in {"127.0.0.1", "::1"}:
            self._json(403, {"error": "A interface aceita conexões somente da própria máquina."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise ValueError("A solicitação está vazia ou excede o limite permitido.")
            data = json.loads(self.rfile.read(length))
            urls_text = str(data.get("video_urls", "")).strip()
            upload_ids = data.get("upload_ids", [])
            if urls_text and upload_ids:
                raise ValueError("Use arquivos selecionados ou links, não os dois ao mesmo tempo.")
            if urls_text:
                urls = parse_video_urls(urls_text)
            elif upload_ids:
                upload_ids = validate_upload_ids(upload_ids)
                urls = []
            else:
                raise ValueError("Selecione um ou mais arquivos MP4, ou cole links diretos.")
            music_upload_id = data.get("music_upload_id")
            if music_upload_id:
                if not bool(data.get("music_enabled", True)):
                    raise ValueError("Ative a opção de música para usar a trilha enviada.")
                music_upload_id = validate_audio_upload_id(music_upload_id)
            format_id = int(data.get("format_id", 0))
            if format_id not in {item["id"] for item in load_formats()}:
                raise ValueError("Escolha um dos cinco formatos disponíveis.")
            data["format_id"] = format_id
        except (ValueError, json.JSONDecodeError, InvalidVideoURL) as exc:
            self._json(400, {"error": str(exc)})
            return
        job_id = uuid.uuid4().hex
        job_dir = WORKSPACE / "jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        with JOBS_LOCK:
            JOBS[job_id] = {"job_id": job_id, "status": "queued", "progress": "Aguardando processamento.",
                            "percent": 0, "stage": "intake", "events": [], "started_mono": time.monotonic()}
        threading.Thread(target=_render_job,
                         args=(job_id, data, urls, upload_ids, music_upload_id), daemon=True).start()
        self._json(202, {"job_id": job_id, "status": "queued", "status_url": f"/api/jobs/{job_id}"})

    def _receive_upload(self) -> None:
        if self.client_address[0] not in {"127.0.0.1", "::1"}:
            self._json(403, {"error": "A interface aceita conexões somente da própria máquina."})
            return
        kind = "video"
        try:
            parsed = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            filename = query.get("filename", [""])[0]
            kind = query.get("kind", ["video"])[0]
            if kind == "music":
                if not filename or Path(filename).suffix.lower() not in AUDIO_SUFFIXES:
                    raise ValueError("Selecione uma música MP3, WAV, M4A, AAC, OGG ou FLAC.")
                length = int(self.headers.get("Content-Length", "0"))
                upload_id, safe_name = save_uploaded_audio(filename, self.rfile, length)
                self._json(201, {"upload_id": upload_id, "filename": safe_name})
                return
            if kind != "video":
                raise ValueError("Tipo de arquivo enviado inválido.")
            if not filename or Path(filename).suffix.lower() not in VIDEO_SUFFIXES:
                raise ValueError("Selecione um arquivo MP4, MOV, M4V, WebM ou MKV.")
            length = int(self.headers.get("Content-Length", "0"))
            upload_id, safe_name = save_uploaded_video(filename, self.rfile, length)
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            if isinstance(exc, subprocess.CalledProcessError):
                message = ("Não foi possível ler a música. Confira se o arquivo contém áudio válido."
                           if kind == "music"
                           else "Não foi possível ler o arquivo como vídeo. Confira se ele é um MP4 válido.")
            else:
                message = str(exc)
            self._json(400, {"error": message})
            return
        self._json(201, {"upload_id": upload_id, "filename": safe_name})


def main() -> None:
    host = os.getenv("REELS_WEB_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise ValueError("A interface web só pode escutar no localhost.")
    port = int(os.getenv("REELS_WEB_PORT", "8000"))
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), ReelRequestHandler)
    print(f"Impulso Reels: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
