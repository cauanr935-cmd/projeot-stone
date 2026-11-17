"""
Transforma cada vídeo baixado em: frames dos primeiros segundos (gancho) + frames ao longo
do vídeo + áudio 16 kHz para o faster-whisper. Depois disso, o .mp4 pode ser apagado
para economizar disco (3.000 vídeos ocupam facilmente 10-20 GB).

Requer ffmpeg instalado (Colab já tem; no Mac: brew install ffmpeg).

Uso:
    python extrair_midia.py --pasta dados/midia --apagar-video
"""
import argparse
import subprocess
from pathlib import Path


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def processar(video: Path, apagar: bool):
    # Instagram: midia/instagram/<id>/video.mp4 -> <id>/frames/
    # YouTube:   midia/youtube/<id>.mp4        -> <id>_frames/
    if video.name == "video.mp4":
        destino = video.parent / "frames"
    else:
        destino = video.parent / f"{video.stem}_frames"
    destino.mkdir(parents=True, exist_ok=True)
    if any(destino.glob("*.jpg")):
        return  # já processado

    # Gancho: 1 frame a cada 0,5 s nos primeiros 3 s
    ffmpeg("-i", str(video), "-t", "3", "-vf", "fps=2,scale=512:-2", str(destino / "gancho_%02d.jpg"))
    # Resto do vídeo: 1 frame a cada 3 s
    ffmpeg("-i", str(video), "-vf", "fps=1/3,scale=512:-2", str(destino / "corpo_%03d.jpg"))
    # Áudio para transcrição
    ffmpeg("-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(destino / "audio.wav"))

    if apagar:
        video.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", default="dados/midia")
    ap.add_argument("--apagar-video", action="store_true")
    args = ap.parse_args()

    videos = list(Path(args.pasta).rglob("*.mp4"))
    print(f"{len(videos)} vídeos")
    for i, v in enumerate(videos, start=1):
        try:
            processar(v, args.apagar_video)
        except subprocess.CalledProcessError as e:
            print(f"Falhou: {v} ({e})")
        if i % 50 == 0:
            print(f"{i}/{len(videos)}")


if __name__ == "__main__":
    main()
