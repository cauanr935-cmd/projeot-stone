"""Extrai de cada vídeo: frames do gancho (0–3 s), frames do corpo e áudio 16 kHz (para faster-whisper).

Uso:
    python -m src.coleta.midia --pasta dados/midia [--apagar-video]
Depois disso o .mp4 pode ser apagado para economizar disco.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.core.config import load_coleta
from src.core.ffmpeg import run_ffmpeg
from src.core.logging import configure_logging

log = logging.getLogger(__name__)


def destino_frames(video: Path) -> Path:
    """Instagram: <id>/video.mp4 -> <id>/frames/ ; YouTube: <id>.mp4 -> <id>_frames/."""
    if video.name == "video.mp4":
        return video.parent / "frames"
    return video.parent / f"{video.stem}_frames"


def processar(video: Path, apagar: bool = False) -> bool:
    """Devolve True se extraiu agora, False se já estava processado."""
    m = load_coleta()["midia"]
    destino = destino_frames(video)
    destino.mkdir(parents=True, exist_ok=True)
    if any(destino.glob("*.jpg")):
        return False
    esc = f"scale={m['largura']}:-2"
    run_ffmpeg(["-y", "-i", video, "-t", m["gancho_segundos"], "-vf", f"fps={m['gancho_fps']},{esc}",
                destino / "gancho_%02d.jpg"])
    run_ffmpeg(["-y", "-i", video, "-vf", f"fps=1/{m['corpo_intervalo_s']},{esc}", destino / "corpo_%03d.jpg"])
    run_ffmpeg(["-y", "-i", video, "-vn", "-ac", 1, "-ar", m["audio_hz"], destino / "audio.wav"], check=False)
    if apagar:
        video.unlink()
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pasta", default=str(Path(load_coleta()["saida_padrao"]) / "midia"))
    ap.add_argument("--apagar-video", action="store_true")
    args = ap.parse_args(argv)
    configure_logging()
    videos = sorted(Path(args.pasta).rglob("*.mp4"))
    print(f"{len(videos)} vídeos")
    falhas = 0
    for i, v in enumerate(videos, start=1):
        try:
            processar(v, args.apagar_video)
        except Exception as e:  # noqa: BLE001
            falhas += 1
            log.error("falhou: %s (%s)", v, e)
        if i % 50 == 0:
            print(f"{i}/{len(videos)}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
