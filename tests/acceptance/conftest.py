"""Fixtures dos testes de aceitação (CONTRATO). Helpers ficam em acc_helpers.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from acc_helpers import FIXTURES, PY, run


@pytest.fixture(scope="session")
def fixtures_ready() -> Path:
    if not (FIXTURES / "sample_raw.mp4").exists():
        run([PY, "tests/fixtures/generate_test_media.py"])
    return FIXTURES
