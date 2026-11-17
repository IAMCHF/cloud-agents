from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

BASE = Path(__file__).resolve().parents[1]


def test_upgrade_creates_ledger_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_path = tmp_path / "migrated.db"
    config = Config(str(BASE / "alembic.ini"))
    config.set_main_option("script_location", str(BASE / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path}")

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        indexes = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
    assert {"sessions", "audit_events"} <= tables
    assert "ix_sessions_owner" in indexes
    assert "ix_audit_events_session_id" in indexes
