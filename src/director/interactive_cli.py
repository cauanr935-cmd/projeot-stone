from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.core.config import load_formats
from src.director.edit_plan import build_edit_plan


def _inventory(path: Path) -> tuple[int, int, int]:
    video = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
    image = {".jpg", ".jpeg", ".png", ".webp"}
    audio = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    files = [p for p in path.iterdir() if p.is_file()]
    files += [p for d in path.iterdir() if d.is_dir() for p in d.iterdir() if p.is_file()]
    return (sum(p.suffix.lower() in video for p in files), sum(p.suffix.lower() in image for p in files),
            sum(p.suffix.lower() in audio for p in files))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", type=Path, required=True)
    ap.add_argument("--format", type=int, choices=range(1, 6))
    ap.add_argument("--cnae")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--business-name")
    ap.add_argument("--product")
    ap.add_argument("--cta-channel", default="WhatsApp")
    ap.add_argument("--job-id", default="job")
    args = ap.parse_args(argv)
    if not args.input_dir.is_dir():
        print(f"Pasta inexistente: {args.input_dir}", file=sys.stderr)
        return 2
    fmt_id = args.format
    if fmt_id is None:
        videos, images, audios = _inventory(args.input_dir)
        print(f"Encontrei: {videos} vídeo(s), {images} fotos, {audios} áudios em {args.input_dir}.")
        print("Qual formato de Reel você quer?")
        for fmt in load_formats():
            duration = fmt["duration"]
            span = f"{duration['target']} s" if duration["min"] == duration["max"] else \
                f"{duration['min']} a {duration['max']} s"
            print(f"  [{fmt['id']}] {fmt['name']} — {span} — {fmt['focus']}")
        attempts = 0
        while attempts < 3:
            print("Digite o número (1-5):", flush=True)
            answer = sys.stdin.readline()
            if answer == "":
                return 2
            try:
                candidate = int(answer.strip())
                if 1 <= candidate <= 5:
                    fmt_id = candidate
                    break
            except ValueError:
                pass
            attempts += 1
            print("Opção inválida. Escolha um número de 1 a 5.")
        if fmt_id is None:
            return 2
    out = args.out or Path("workspace/jobs") / args.job_id / "edit_plan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    plan = build_edit_plan(args.input_dir, fmt_id, args.cnae, args.job_id, args.business_name,
                           args.product, args.cta_channel)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
