from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class PathOutsideRootsError(ValueError):
    """Raised when a path escapes client-authorized filesystem roots."""


def resolve_allowed_path(path: str | Path, roots: list[str | Path]) -> Path:
    resolved = Path(path).expanduser().resolve()
    allowed = [Path(r).expanduser().resolve() for r in roots]
    if not any(resolved == root or root in resolved.parents for root in allowed):
        raise PathOutsideRootsError(f"caminho fora dos Roots autorizados: {resolved}")
    return resolved


async def get_roots(ctx: Any) -> list[Path]:
    try:
        roots = await ctx.session.list_roots()
        paths = [Path(str(root.uri).removeprefix("file://")).resolve() for root in roots.roots]
        if paths:
            return paths
    except Exception:
        pass
    return [Path(os.getenv("REELS_WORKSPACE", "./workspace")).resolve()]
