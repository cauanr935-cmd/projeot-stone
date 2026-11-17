from __future__ import annotations

from src.core.config import load_script_templates


def build_script(format_cfg: dict, slots: dict | None = None, router=None) -> dict:
    slots = slots or {}
    templates = load_script_templates()
    cfg = templates["formats"][format_cfg["id"]]
    defaults = templates.get("slot_defaults", {})
    values = {**defaults, **slots}
    scripts = {name: text.format(**values) for name, text in cfg["segments"].items()}
    return {"engine": "template_engine", "hook_overlay": cfg["hook_overlay"],
            "segments": scripts, "full_text": " ".join(scripts.values()),
            "loop_tail": cfg.get("loop_tail") if format_cfg["id"] == 5 else None}
