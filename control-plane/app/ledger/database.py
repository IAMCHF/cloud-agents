"""异步数据库装配（SQLAlchemy 2.0 + asyncpg / 测试用 aiosqlite）。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ledger.models import Base


class Database:
    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url, pool_pre_ping=True)
        self._sessionmaker = async_sessionmaker(self._engine, expire_on_commit=False)
        # 进程内准入串行化；跨副本一致性由 Postgres advisory lock 保证。
        self.lock = asyncio.Lock()

    @property
    def dialect_name(self) -> str:
        return self._engine.dialect.name

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessionmaker() as session:
            yield session

    async def create_schema(self) -> None:
        """开发/测试用建表；生产走 Alembic 迁移。"""
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self._engine.dispose()
