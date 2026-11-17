from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


@lru_cache(maxsize=None)
def _read(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{path}: não foi possível carregar YAML: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: esperado objeto YAML")
    return value


def load_formats() -> list[dict]:
    cfg = _read("formats.yaml")
    formats = cfg.get("formats")
    if not isinstance(formats, list) or [f.get("id") for f in formats] != [1, 2, 3, 4, 5]:
        raise ValueError(f"{CONFIG_DIR / 'formats.yaml'}: campo formats deve conter ids 1..5")
    return formats


def get_format(id_or_key: int | str) -> dict:
    for fmt in load_formats():
        if fmt["id"] == id_or_key or fmt["key"].lower() == str(id_or_key).lower():
            return fmt
    raise KeyError(f"formato inexistente: {id_or_key}")


def common() -> dict:
    return _read("formats.yaml").get("common", {})


def load_cnae_profiles() -> dict:
    return _read("cnae_profiles.yaml")


def load_providers() -> dict:
    return _read("providers.yaml")


def load_licenses() -> dict:
    return _read("licenses.yaml")


def load_script_templates() -> dict:
    return _read("script_templates.yaml")
