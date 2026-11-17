"""测试共享夹具：SQLite 台账。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.ledger import Database, Ledger


@pytest.fixture
async def ledger(tmp_path: Path) -> AsyncIterator[Ledger]:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'ledger.db'}")
    await database.create_schema()
    instance = Ledger(database, flush_interval=0.01)
    await instance.start()
    try:
        yield instance
    finally:
        await instance.stop()
        await database.dispose()
