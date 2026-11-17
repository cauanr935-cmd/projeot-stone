"""Relatório de progresso por etapas, compartilhado por CLI, web e MCP.

Cada etapa tem uma faixa de porcentagem; dentro da etapa o chamador informa
a fração concluída (0..1). O callback recebe um dicionário simples e nunca
deve quebrar o pipeline.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

log = logging.getLogger(__name__)

ProgressCallback = Callable[[dict], None]

# (chave, rótulo, faixa % inicial, faixa % final)
STAGES: list[tuple[str, str, int, int]] = [
    ("intake", "Recebendo os vídeos", 0, 10),
    ("analysis", "Analisando o material", 10, 22),
    ("plan", "Montando o roteiro do formato", 22, 28),
    ("voice", "Gerando a locução", 28, 42),
    ("music", "Criando a trilha e o ritmo", 42, 50),
    ("subtitles", "Preparando as legendas", 50, 55),
    ("render", "Renderizando o Reel", 55, 95),
    ("audit", "Conferindo qualidade técnica", 95, 100),
]
_BOUNDS = {key: (lo, hi) for key, _, lo, hi in STAGES}
_LABELS = {key: label for key, label, _, _ in STAGES}


def stage_catalog() -> list[dict]:
    return [{"key": key, "label": label, "start": lo, "end": hi} for key, label, lo, hi in STAGES]


class Reporter:
    """Converte (etapa, fração, mensagem) em eventos com porcentagem global."""

    def __init__(self, callback: ProgressCallback | None = None):
        self._callback = callback
        self._started = time.monotonic()

    def __call__(self, stage: str, fraction: float = 0.0, message: str | None = None) -> None:
        lo, hi = _BOUNDS[stage]
        fraction = min(1.0, max(0.0, fraction))
        event = {"stage": stage, "label": _LABELS[stage], "percent": round(lo + (hi - lo) * fraction, 1),
                 "message": message or _LABELS[stage], "elapsed_s": round(time.monotonic() - self._started, 1)}
        log.info("progress stage=%s percent=%s msg=%s", stage, event["percent"], event["message"])
        if self._callback is not None:
            try:
                self._callback(event)
            except Exception:  # progresso nunca pode derrubar o render
                log.exception("callback de progresso falhou")


def make_reporter(callback: ProgressCallback | None) -> Reporter:
    return callback if isinstance(callback, Reporter) else Reporter(callback)
