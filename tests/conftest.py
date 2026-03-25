import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.schema import init_db
from app.main import app


@pytest.fixture
def test_db_path(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_mnemosyne.db"
        monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{test_db.as_posix()}")
        init_db()
        yield test_db


@pytest.fixture
def client(test_db_path):
    return TestClient(app)
