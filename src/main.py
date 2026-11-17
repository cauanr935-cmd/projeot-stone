from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from src.director.edit_plan import build_edit_plan
from src.director.interactive_cli import main as director_main
from src.renderer.reel_assembler import assemble_and_render_reel


def _print_progress(event: dict) -> None:
    bar = "█" * int(event["percent"] // 5) + "░" * (20 - int(event["percent"] // 5))
    print(f"\r[{bar}] {event['percent']:5.1f}%  {event['message'][:60]:<60}", end="", file=sys.stderr, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Crie um Reel vertical para Impulso Stone.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--format", type=int, choices=range(1, 6))
    parser.add_argument("--cnae")
    parser.add_argument("--out", type=Path, default=Path("output/reel_final.mp4"))
    parser.add_argument("--job-id", default="reel_job")
    parser.add_argument("--business-name")
    parser.add_argument("--product")
    parser.add_argument("--cta-channel", default="WhatsApp")
    parser.add_argument("--keep-source-audio", action="store_true")
    args = parser.parse_args(argv)
    fmt_id = args.format
    if fmt_id is None:
        rc = director_main(["--input-dir", str(args.input_dir), "--cnae", args.cnae or "",
                            "--job-id", args.job_id, "--business-name", args.business_name or "",
                            "--product", args.product or "", "--cta-channel", args.cta_channel,
                            "--out", str(Path(os.getenv("REELS_WORKSPACE", "./workspace")) /
                                          "jobs" / args.job_id / "edit_plan.json")])
        if rc:
            return rc
        plan = json.loads((Path(os.getenv("REELS_WORKSPACE", "./workspace")) /
                           "jobs" / args.job_id / "edit_plan.json").read_text(encoding="utf-8"))
    else:
        plan = build_edit_plan(args.input_dir, fmt_id, args.cnae, args.job_id,
                               args.business_name, args.product, args.cta_channel,
                               os.getenv("REELS_COMMERCIAL", "1") != "0", progress=_print_progress)
    assemble_and_render_reel(plan, args.out, os.getenv("REELS_COMMERCIAL", "1") != "0",
                              args.keep_source_audio, progress=_print_progress)
    print(file=sys.stderr)
    print(args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
