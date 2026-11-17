from __future__ import annotations

import os

from src.core.config import load_licenses


class CommercialLicenseViolationError(ValueError):
    pass


class UnknownLicenseError(ValueError):
    pass


def validate_commercial_sources(sources: list[str], commercial: bool = True,
                                env: dict[str, str] | None = None) -> list[str]:
    env = env if env is not None else os.environ
    entries = load_licenses()["entries"]
    warnings = []
    for source in sources:
        entry = entries.get(source)
        if entry is None:
            raise UnknownLicenseError(f"licença desconhecida: {source}")
        allowed = entry.get("commercial_ok", False)
        if not commercial:
            continue
        if allowed is False:
            raise CommercialLicenseViolationError(f"fonte bloqueada para uso comercial: {source}")
        if allowed == "agpl" and env.get("REELS_ALLOW_AGPL") != "1":
            raise CommercialLicenseViolationError(f"fonte AGPL bloqueada para uso comercial: {source}")
        if allowed == "review":
            warnings.append({"source": source, "license": entry.get("license"), "status": "review"})
    return warnings
