import sqlite3
from pathlib import Path

from app.config import settings


def _resolve_sqlite_path() -> Path:
    db_url = settings.DATABASE_URL.strip()

    if not db_url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// DATABASE_URL is supported currently.")

    raw_path = db_url.replace("sqlite:///", "", 1)
    return Path(raw_path)


def get_connection() -> sqlite3.Connection:
    db_path = _resolve_sqlite_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
