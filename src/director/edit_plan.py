from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from src.core.config import common
from src.director.scripts import build_script
from src.resources.cnae_profiles import get_cnae_marketing_profile


class EditPlan(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: int
    job_id: str
    format: dict
    segments: list[dict]
    assets: list[dict]


def build_edit_plan(input_dir: Path, format_id: int, cnae_code: str | None = None,
                    job_id: str = "job", business_name: str | None = None,
                    product: str | None = None, cta_channel: str = "WhatsApp",
                    commercial: bool = True, context: str | None = None,
                    custom_script: str | None = None, speech_enabled: bool = True,
                    music_enabled: bool = True, keep_source_audio: bool = False,
                    progress=None) -> dict:
    import hashlib
    from src.core.progress import make_reporter
    report = make_reporter(progress)
    from PIL import Image
    from src.core.config import get_format
    from src.core.ffmpeg import ffprobe_json

    input_dir = Path(input_dir).resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(f"pasta de entrada inexistente: {input_dir}")
    fmt = get_format(format_id)
    if not cnae_code:
        cnae_code = fmt["canonical_cnae"]
    profile = __import__("json").loads(get_cnae_marketing_profile(cnae_code))
    video_ext = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
    image_ext = {".jpg", ".jpeg", ".png", ".webp"}
    audio_ext = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
    paths = sorted(p for p in input_dir.iterdir() if p.is_file())
    paths += sorted(p for child in input_dir.iterdir() if child.is_dir() for p in child.iterdir() if p.is_file())
    assets = []
    media_paths = [p for p in paths if p.suffix.lower() in video_ext | image_ext | audio_ext]
    for path in media_paths:
        ext = path.suffix.lower()
        report("analysis", len(assets) / max(len(media_paths), 1),
               f"Analisando {path.name} ({len(assets) + 1} de {len(media_paths)})")
        kind = "video" if ext in video_ext else "image" if ext in image_ext else "audio"
        w = h = 0
        duration_s = 0.0
        if kind == "image":
            with Image.open(path) as im:
                w, h = im.size
        elif kind in ("video", "audio"):
            info = ffprobe_json(path)
            duration_s = float(info["format"].get("duration", 0))
            stream = next((s for s in info["streams"] if s.get("codec_type") == ("video" if kind == "video" else "audio")), {})
            w, h = int(stream.get("width", 0)), int(stream.get("height", 0))
        assets.append({"id": f"a{len(assets)+1}", "path": str(path.resolve()), "kind": kind,
                       "duration_s": round(duration_s, 3), "width": w, "height": h,
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    if not assets:
        raise ValueError(f"nenhuma mídia compatível em {input_dir}")
    report("analysis", 1.0, f"{len(assets)} arquivo(s) analisado(s)")
    report("plan", 0.3, f"Montando o roteiro do formato {fmt['name']}")
    templates = build_script(fmt, {"negocio": business_name or "nosso cantinho",
                                   "servico": product or "esse serviço", "produto": product or "esse produto",
                                   "cta_canal": cta_channel})
    context = (context or "").strip()
    custom_script = (custom_script or "").strip()
    user_text = " ".join((custom_script or context).split())
    if user_text:
        templates["full_text"] = user_text
        templates["engine"] = "user_provided"
    hook = " ".join(templates["hook_overlay"].split()[:5])
    if user_text:
        hook = " ".join(user_text.split()[:5])
    format_segments = fmt["segments"]
    plan_segments = []
    available = [a for a in assets if a["kind"] in {"video", "image"}] or assets
    for idx, seg in enumerate(format_segments):
        chosen = available[min(idx, len(available)-1)]
        if seg["role"] in {"after", "discovery", "walkthrough", "desire"}:
            images = [a for a in available if a["kind"] == "image"]
            if images:
                chosen = images[idx % len(images)]
        script = templates["segments"].get(seg["name"], templates["full_text"])
        max_words = math.ceil(3.5 * (seg["end"] - seg["start"])) + 2
        words = script.split()
        if len(words) > max_words:
            script = " ".join(words[:max_words])
        plan_segments.append({"name": seg["name"], "label": seg["label"], "start": seg["start"],
                              "end": seg["end"], "role": seg["role"], "beat_aligned": seg.get("beat_aligned", False),
                              "align_to": seg.get("align_to"), "script": script, "assets": [chosen["id"]]})
    if fmt["seamless_loop"]:
        # Last sentence must connect to the first, without terminal punctuation.
        tail = templates["loop_tail"] or "porque"
        plan_segments[-1]["script"] = tail.rstrip(".!?…")
    planned = round(fmt["target_cuts_per_sec"] * fmt["duration"]["target"])
    result = {
        "schema_version": 1, "job_id": job_id, "created_at": datetime.now(timezone.utc).isoformat(),
        "commercial": commercial, "format": {"id": fmt["id"], "key": fmt["key"], "name": fmt["name"]},
        "cnae": {"code": profile["cnae_code"], "fallback": profile["fallback"]},
        "duration": fmt["duration"], "segments": plan_segments,
        "cut": {"style": fmt["cut_style"], "pad": common()["pads"][fmt["cut_style"]],
                "target_cuts_per_sec": fmt["target_cuts_per_sec"], "planned_cuts": planned},
        "silence": fmt["silence"], "reframe": fmt["reframe"], "animation": fmt["animation"],
        "tts": fmt["tts"], "music": {**fmt["music"], "ducking_db": common()["music"]["ducking_db"],
                                      "source": "auto", "enabled": music_enabled},
        "audio": {"speech_enabled": speech_enabled, "music_enabled": music_enabled,
                  "keep_source_audio": keep_source_audio},
        "subtitles": {"style": common()["subtitles"]["style_name"], "max_words_per_event": 4,
                      "frame_zero_max_words": 5, "hook_overlay": hook},
        "seamless_loop": fmt["seamless_loop"],
        "script": {**templates, "hook_overlay": hook, "context": context,
                   "user_provided": bool(user_text)},
        "assets": assets,
        "output": {"width": 1080, "height": 1920, "fps": 30, "vcodec": "h264",
                   "pix_fmt": "yuv420p", "acodec": "aac"},
    }
    EditPlan.model_validate(result)
    return result
