"""测试共享夹具：SQLite 台账。"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.ledger import Database, Ledger

# 测试一律直连（testserver/127.0.0.1），不读系统代理：Windows 代理 bypass 含带括号
# IPv6（如 [::1]）时，httpx 0.28.1 会解析出非法 mount 模式，客户端构造即崩。
# 固定 NO_PROXY 使门禁不依赖开发机代理设置；运行时 trust_env 行为不变（部署约束见方案 §6）。
os.environ["NO_PROXY"] = "*"


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
