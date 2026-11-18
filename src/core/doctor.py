from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

from src.core.config import ROOT
from src.core.ffmpeg import resolve_binaries


def _package(*names: str) -> str | None:
    for name in names:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def _binary(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {"ok": False, "path": None, "version": None}
    try:
        p = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=2)
        version = (p.stdout or p.stderr).splitlines()[0][:180]
    except Exception:
        version = None
    return {"ok": True, "path": path, "version": version}


def _network(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "impulso-stone-doctor/1"})
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception:
        return False


def _env_keys() -> dict[str, bool]:
    path = ROOT / ".env.example"
    keys = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*([A-Z][A-Z0-9_]*)\s*=", line)
            if m:
                keys.append(m.group(1))
    return {key: bool(os.getenv(key)) for key in keys}


def probe() -> dict[str, Any]:
    binaries = resolve_binaries()
    ffmpeg_ok, ffprobe_ok = bool(binaries["ffmpeg"]), bool(binaries["ffprobe"])
    filters = {name: False for name in ("libx264", "aac", "ass", "ebur128", "loudnorm",
                                         "silencedetect", "zoompan", "sidechaincompress")}
    if ffmpeg_ok:
        p = subprocess.run([binaries["ffmpeg"], "-hide_banner", "-filters"], capture_output=True, text=True,
                           timeout=3)
        text = p.stdout
        for name in filters:
            filters[name] = bool(re.search(rf"^\s*\S+\s+{re.escape(name)}\s", text, re.M))
        p = subprocess.run([binaries["ffmpeg"], "-hide_banner", "-encoders"], capture_output=True, text=True,
                           timeout=3)
        filters["libx264"] = filters["libx264"] or bool(re.search(r"^\s*V\S*\s+libx264\s", p.stdout, re.M))
        filters["aac"] = filters["aac"] or bool(re.search(r"^\s*A\S*\s+aac\s", p.stdout, re.M))
    version = tuple(sys.version_info[:2])
    python_ok = (3, 11) <= version < (3, 13)
    if version >= (3, 13):
        python_ok = True
    packages = {
        "mcp": _package("mcp"), "edge-tts": _package("edge-tts"), "scenedetect": _package("scenedetect"),
        "librosa": _package("librosa"), "pysubs2": _package("pysubs2"),
        "opencv": _package("opencv-python-headless", "opencv-python"), "whisperx": _package("whisperx"),
        "faster-whisper": _package("faster-whisper"), "mediapipe": _package("mediapipe"),
        "transformers": _package("transformers"), "kokoro-onnx": _package("kokoro-onnx"),
        "piper-tts": _package("piper-tts"), "torch": _package("torch"),
    }
    installed = lambda package: importlib.util.find_spec(package) is not None
    models_dir = ROOT / "models"
    has_piper = bool(os.getenv("PIPER_MODEL_PATH") and Path(os.getenv("PIPER_MODEL_PATH", "")).exists()) or \
        (models_dir / "piper" / "pt_BR-faber-medium.onnx").exists()
    has_cuda = False
    cuda_name = None
    try:
        import torch
        has_cuda = bool(torch.cuda.is_available())
        cuda_name = torch.cuda.get_device_name(0) if has_cuda else None
    except Exception:
        pass
    binaries_report = {name: _binary(name) for name in ("espeak-ng", "piper", "ollama")}
    binaries_report["ffmpeg"] = {"ok": ffmpeg_ok, "path": binaries["ffmpeg"] or None, "version": None}
    binaries_report["ffprobe"] = {"ok": ffprobe_ok, "path": binaries["ffprobe"] or None, "version": None}
    offline = os.getenv("REELS_OFFLINE", "0") == "1"
    from src.router import kokoro_tts
    allow_edge = os.getenv("ALLOW_NONCOMMERCIAL_EDGE_TTS", "0") == "1"
    if kokoro_tts.disponivel():
        tts = "kokoro"
    elif allow_edge and not offline and packages["edge-tts"]:
        tts = "edge-tts"
    elif binaries_report["espeak-ng"]["ok"]:
        tts = "espeak-ng"
    elif has_piper:
        tts = "piper"
    else:
        tts = "placeholder_tone"
    engines = {
        "asr": "faster_whisper" if packages["faster-whisper"] else "none",
        "tts": tts,
        "llm": "template_engine",
        "vlm": "heuristic_only",
        "music": "procedural_generator",
        "depth": "geometric",
        "subject_detection": "opencv_saliency" if packages["opencv"] else "center_fallback",
    }
    dependencies = []
    if tts == "placeholder_tone":
        dependencies.append({"id": "tts-local-engine", "priority": "RECOMENDADO", "spec": "02",
                             "action": "Instale espeak-ng ou configure um modelo Piper pt-BR.",
                             "impact": "Locução de teste tonal, sem voz natural.",
                             "fallback": "Gerador de áudio local determinístico.",
                             "verify": "python -m src.core.doctor --json"})
    if tts == "edge-tts":
        dependencies.append({"id": "legal-edge-tts", "priority": "JURÍDICO", "spec": "02",
                             "action": "edge-tts está habilitado (ALLOW_NONCOMMERCIAL_EDGE_TTS=1): sem assinatura Azure o uso comercial não é autorizado.",
                             "impact": "Risco legal em render comercial.",
                             "fallback": "Desabilitar a variável: o roteador usa Kokoro local (Apache-2.0).",
                             "verify": "python -m src.core.doctor --json"})
    for name, info in binaries_report.items():
        if name == "ollama" and not info["ok"]:
            dependencies.append({"id": "ollama-local", "priority": "OPCIONAL", "spec": "02",
                                 "action": "Instalar Ollama somente se desejar LLM/VLM local.",
                                 "impact": "Sem impacto: templates e heurísticas offline funcionam.",
                                 "fallback": "template_engine e heuristic_only",
                                 "verify": "ollama list"})
    return {
        "python": {"version": platform.python_version(), "ok": python_ok},
        "binaries": binaries_report, "ffmpeg_filters": filters,
        "gpu": {"cuda": has_cuda, "name": cuda_name},
        "network": {"pypi": _network("https://pypi.org"), "huggingface": _network("https://huggingface.co"),
                    "github": _network("https://github.com")},
        "env_keys": _env_keys(), "python_packages": packages,
        "models": {"piper_pt_br": has_piper, "kokoro": False, "depth_anything_v2_small": False,
                   "whisper_local": False, "ollama_llama3_2": False, "ollama_qwen2_5vl": False},
        "fonts": {"montserrat_extrabold": (ROOT / "assets/fonts/Montserrat-ExtraBold.ttf").exists(),
                  "path": str(ROOT / "assets/fonts/Montserrat-ExtraBold.ttf") if
                  (ROOT / "assets/fonts/Montserrat-ExtraBold.ttf").exists() else None,
                  "fallback": "DejaVu Sans Bold"},
        "engines_effective": engines, "human_dependencies": dependencies,
    }


def write_report(data: dict[str, Any], docs_dir: Path) -> None:
    docs_dir.mkdir(parents=True, exist_ok=True)
    rows = ["# Relatório do ambiente", "", f"- Python: {data['python']['version']}",
            f"- Engines efetivos: `{json.dumps(data['engines_effective'], ensure_ascii=False)}`", "",
            "## Binários", "", "| Binário | Disponível | Caminho |", "|---|---:|---|"]
    for name, info in data["binaries"].items():
        rows.append(f"| {name} | {'sim' if info['ok'] else 'não'} | {info['path'] or '—'} |")
    rows += ["", "## Filtros FFmpeg", "", "| Filtro/encoder | Disponível |", "|---|---:|"]
    rows += [f"| {name} | {'sim' if ok else 'não'} |" for name, ok in data["ffmpeg_filters"].items()]
    rows += ["", "## Pacotes Python", "", "| Pacote | Versão |", "|---|---|"]
    rows += [f"| {name} | {version or 'ausente'} |" for name, version in data["python_packages"].items()]
    (docs_dir / "ENVIRONMENT_REPORT.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    deps_path = docs_dir / "HUMAN_DEPENDENCIES.md"
    if deps_path.exists():
        text = deps_path.read_text(encoding="utf-8")
        begin, end = "<!-- AUTO:BEGIN -->", "<!-- AUTO:END -->"
        if begin in text and end in text and text.index(begin) < text.index(end):
            table = ["", "### Itens detectados automaticamente", "",
                     "| ID | Prioridade | Spec | Ação | Impacto | Fallback | Verificação |",
                     "|---|---|---:|---|---|---|---|"]
            for d in data["human_dependencies"]:
                esc = lambda x: str(x).replace("|", "\\|").replace("\n", " ")
                table.append("| " + " | ".join(esc(d[k]) for k in
                                              ("id", "priority", "spec", "action", "impact", "fallback", "verify")) + " |")
            text = text[:text.index(begin) + len(begin)] + "\n" + "\n".join(table) + "\n" + \
                text[text.index(end):]
            deps_path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--docs-dir", type=Path, default=ROOT / "docs")
    args = parser.parse_args(argv)
    data = probe()
    if args.json:
        print(json.dumps(data, ensure_ascii=False))
    elif args.write_report:
        print("Sondagem concluída.")
    if args.write_report:
        write_report(data, args.docs_dir)
    return 0 if data["python"]["ok"] and data["binaries"]["ffmpeg"]["ok"] and data["binaries"]["ffprobe"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
