from __future__ import annotations

import json
import re

from src.core.config import get_format, load_cnae_profiles


def normalize_cnae(code: str) -> str:
    digits = re.sub(r"\D", "", str(code))
    if len(digits) != 7:
        return str(code).strip()
    return f"{digits[:4]}-{digits[4]}/{digits[5:]}"


def get_cnae_marketing_profile(cnae_code: str) -> str:
    cfg = load_cnae_profiles()
    normalized = normalize_cnae(cnae_code)
    profiles = cfg.get("profiles", {})
    found_key = next((key for key, value in profiles.items()
                      if normalize_cnae(key) == normalized or
                      any(normalize_cnae(alias) == normalized for alias in value.get("aliases", []))), None)
    fallback = found_key is None
    if fallback:
        found_key = cfg["default_cnae"]
    profile = profiles[found_key]
    segment = profile["segment"]
    fmt_id = cfg["segments"][segment]["format_id"]
    fmt = get_format(fmt_id)
    result = {
        "cnae_code": found_key, "ocupacao": profile["ocupacao"], "segment": segment,
        "format_id": fmt_id, "framework": fmt["name"], "cut_style": fmt["cut_style"],
        "target_cuts_per_sec": fmt["target_cuts_per_sec"], "reframe_preset": fmt["reframe"]["preset"],
        "tts_voice": fmt["tts"]["voice"], "duration": fmt["duration"], "segments": fmt["segments"],
        "seamless_loop": fmt["seamless_loop"],
        "parallax_strength": fmt["animation"]["parallax_strength"], "fallback": fallback,
    }
    return json.dumps(result, ensure_ascii=False)
