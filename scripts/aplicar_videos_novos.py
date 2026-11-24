"""Troca os vídeos antigos (tutorial e exemplos) pelos refeitos em output/edicoes/ex_*/final.mp4, com backup.

Uso: python scripts/aplicar_videos_novos.py [--only tutorial pet_banho_tosa]
Só aplica se o vídeo novo passar em 1080x1920/yuv420p/CFR. Backup em output/backup_motion_antigo/.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOVOS = ROOT / "output" / "edicoes"
BACKUP = ROOT / "output" / "backup_motion_antigo"


def valido(mp4: Path) -> bool:
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,pix_fmt,r_frame_rate,avg_frame_rate", "-of", "json", str(mp4)],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    return (p["width"], p["height"], p["pix_fmt"]) == (1080, 1920, "yuv420p") and p["r_frame_rate"] == p["avg_frame_rate"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    BACKUP.mkdir(parents=True, exist_ok=True)
    for pasta in sorted(NOVOS.glob("ex_*")):
        nome = pasta.name[3:]
        novo = pasta / "final.mp4"
        if (a.only and nome not in a.only) or not novo.is_file():
            continue
        if not valido(novo):
            print(f"PULADO {nome}: vídeo novo fora do padrão")
            continue
        if nome == "tutorial":
            destino = ROOT / "src" / "web" / "tutorial.mp4"
            alvos = [destino, ROOT / "src" / "web" / "tutorial.jpg"]
        else:
            fid = json.loads(next((ROOT / "output" / "criativos").glob(f"{nome}_f*.spec.json")).read_text())["formato_id"]
            destino = ROOT / "output" / "criativos" / f"{nome}_f{fid}.mp4"
            alvos = [destino]
        for alvo in alvos:
            if alvo.exists() and not (BACKUP / alvo.name).exists():
                shutil.copy2(alvo, BACKUP / alvo.name)
        shutil.copy2(novo, destino)
        if nome == "tutorial":
            shutil.copy2(pasta / "capa.jpg", alvos[1])
        print(f"aplicado {nome} -> {destino.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
