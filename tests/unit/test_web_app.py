import io
import shutil
import subprocess
import threading
import time
import urllib.request
import wave
from http.server import ThreadingHTTPServer

import numpy as np
import pytest

from src import web_app
from src.editing.beat_sync import select_high_energy_start
from src.web_app import InvalidVideoURL, parse_video_urls


def test_video_url_parser_accepts_public_direct_url():
    import socket
    from unittest.mock import patch

    public = ("93.184.216.34", 0)
    with patch("src.web_app.socket.getaddrinfo", return_value=[
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", public)
    ]):
        assert parse_video_urls("https://media.example/video.mp4") == [
            "https://media.example/video.mp4"
        ]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/video.mp4",
        "http://localhost/video.mp4",
        "http://192.168.1.10/video.mp4",
        "http://169.254.169.254/latest/meta-data",
    ],
)
def test_video_url_parser_rejects_local_or_non_http_urls(url):
    with pytest.raises(InvalidVideoURL):
        parse_video_urls(url)


def test_video_url_parser_rejects_empty_and_duplicate_links():
    with pytest.raises(ValueError, match="ao menos um"):
        parse_video_urls(" \n ")
    with pytest.raises(ValueError, match="repetidos"):
        parse_video_urls("https://media.example/a.mp4\nhttps://media.example/a.mp4")


def test_video_url_parser_has_no_fixed_count_limit():
    import socket
    from unittest.mock import patch

    links = [f"https://media{i}.example/a.mp4" for i in range(12)]
    with patch("src.web_app.socket.getaddrinfo", return_value=[
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
    ]):
        assert parse_video_urls("\n".join(links)) == links


def test_upload_saves_and_validates_video_file(tmp_path, monkeypatch):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg é necessário para validar um upload real")
    source_path = tmp_path / "source.mp4"
    subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
            "color=c=red:s=64x64:d=0.2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-y", str(source_path),
        ],
        check=True,
    )
    monkeypatch.setattr(web_app, "WORKSPACE", tmp_path / "workspace")
    monkeypatch.setattr(web_app, "UPLOADS", {})

    with source_path.open("rb") as source:
        upload_id, name = web_app.save_uploaded_video("my video.mp4", source, source_path.stat().st_size)

    saved = web_app.UPLOADS[upload_id]
    assert name == "my video.mp4"
    assert saved.suffix == ".mp4"
    assert saved.read_bytes() == source_path.read_bytes()


def test_upload_rejects_non_video_extensions_and_oversized_files(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "WORKSPACE", tmp_path / "workspace")
    with pytest.raises(ValueError, match="MP4"):
        web_app.save_uploaded_video("document.txt", io.BytesIO(b"data"), 4)
    with pytest.raises(ValueError, match="500 MB"):
        web_app.save_uploaded_video("video.mp4", io.BytesIO(b""), web_app.MAX_VIDEO_BYTES + 1)


def test_upload_saves_and_validates_custom_music(tmp_path, monkeypatch):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg é necessário para validar um upload real")
    source_path = tmp_path / "source.wav"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         "sine=frequency=440:duration=1", "-y", str(source_path)],
        check=True,
    )
    monkeypatch.setattr(web_app, "WORKSPACE", tmp_path / "workspace")
    monkeypatch.setattr(web_app, "AUDIO_UPLOADS", {})

    with source_path.open("rb") as source:
        upload_id, name = web_app.save_uploaded_audio("minha trilha.wav", source, source_path.stat().st_size)

    saved = web_app.AUDIO_UPLOADS[upload_id]
    assert name == "minha trilha.wav"
    assert saved.suffix == ".wav"
    assert saved.read_bytes() == source_path.read_bytes()
    assert web_app.validate_audio_upload_id(upload_id) == upload_id


def test_custom_music_upload_rejects_invalid_size_and_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "WORKSPACE", tmp_path / "workspace")
    with pytest.raises(ValueError, match="MP3"):
        web_app.save_uploaded_audio("document.txt", io.BytesIO(b"data"), 4)
    with pytest.raises(ValueError, match="100 MB"):
        web_app.save_uploaded_audio("music.mp3", io.BytesIO(b""), web_app.MAX_AUDIO_BYTES + 1)


def test_custom_music_prefers_the_high_energy_section(tmp_path):
    sample_rate = 8000
    parts = [
        np.sin(2 * np.pi * 440 * np.arange(sample_rate * seconds) / sample_rate) * amplitude
        for seconds, amplitude in ((5, 0.05), (5, 0.6), (5, 0.2))
    ]
    samples = np.concatenate(parts)
    path = tmp_path / "music.wav"
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes((samples * 32767).astype("<i2").tobytes())

    start = select_high_energy_start(path, segment_s=5)

    assert 4.5 <= start <= 5.5


def test_upload_ids_accept_more_than_five_files(monkeypatch, tmp_path):
    upload_ids = [f"{index:032x}" for index in range(12)]
    monkeypatch.setattr(web_app, "UPLOADS", {item: tmp_path / f"{item}.mp4" for item in upload_ids})

    assert web_app.validate_upload_ids(upload_ids) == upload_ids


def test_preview_endpoint_supports_inline_playback_and_byte_ranges(monkeypatch, tmp_path):
    job_id = "a" * 32
    job_dir = tmp_path / "jobs" / job_id
    job_dir.mkdir(parents=True)
    video_path = job_dir / "reel_final.mp4"
    video_path.write_bytes(b"0123456789")
    monkeypatch.setattr(web_app, "WORKSPACE", tmp_path)
    monkeypatch.setattr(web_app, "JOBS", {
        job_id: {"job_id": job_id, "status": "done", "output": str(video_path),
                "started_mono": time.monotonic(), "events": []}
    })
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_app.ReelRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/jobs/{job_id}/preview"
    try:
        request = urllib.request.Request(url, headers={"Range": "bytes=2-5"})
        with urllib.request.urlopen(request) as response:
            assert response.status == 206
            assert response.headers["Content-Type"] == "video/mp4"
            assert response.headers["Content-Disposition"].startswith("inline;")
            assert response.headers["Accept-Ranges"] == "bytes"
            assert response.headers["Content-Range"] == "bytes 2-5/10"
            assert response.read() == b"2345"

        with urllib.request.urlopen(url) as response:
            assert response.status == 200
            assert response.read() == b"0123456789"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_edit_plan_uses_user_context_and_audio_choices(tmp_path):
    from src.director.edit_plan import build_edit_plan

    video = tmp_path / "source.mp4"
    subprocess.run(
        [
            shutil.which("ffmpeg") or "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
            "-i", "color=c=red:s=64x64:d=0.2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-y", str(video),
        ],
        check=True,
    )
    plan = build_edit_plan(
        tmp_path, 2, job_id="web-context",
        context="Mostre os detalhes da costura feita à mão.",
        custom_script="Esta bolsa é costurada à mão. Peça a sua pelo WhatsApp.",
        speech_enabled=False, music_enabled=True,
    )

    assert plan["script"]["context"] == "Mostre os detalhes da costura feita à mão."
    assert plan["script"]["full_text"] == "Esta bolsa é costurada à mão. Peça a sua pelo WhatsApp."
    assert plan["audio"] == {
        "speech_enabled": False, "music_enabled": True, "keep_source_audio": False
    }
    assert plan["music"]["enabled"] is True
