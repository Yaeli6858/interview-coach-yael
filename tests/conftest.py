import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from shared.store import Store  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "state")
