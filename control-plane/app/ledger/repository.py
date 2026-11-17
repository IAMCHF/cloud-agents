"""会话台账与审计写入。

审计事件走进程内队列 + 后台批量落库，避免 150 路流式事件逐条 INSERT。
P1 允许极端情况下丢弃事件并计数（日志告警），可靠投递待 P2 评估。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.ledger.database import Database
from app.ledger.models import AuditEventRow, SessionRow

logger = logging.getLogger(__name__)

_BATCH_SIZE = 200
_QUEUE_SIZE = 10_000


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    owner: str
    status: str
    sandbox_id: str | None
    created_at: datetime
    ended_at: datetime | None
    end_reason: str | None


@dataclass(frozen=True)
class _AuditRecord:
    session_id: str
    kind: str
    payload: dict[str, Any]


class Ledger:
    def __init__(self, database: Database, *, flush_interval: float = 0.2) -> None:
        self._database = database
        self._flush_interval = flush_interval
        self._queue: asyncio.Queue[_AuditRecord | None] = asyncio.Queue(maxsize=_QUEUE_SIZE)
        self._writer: asyncio.Task[None] | None = None
        self._dropped = 0

    @property
    def dropped_events(self) -> int:
        return self._dropped

    async def start(self) -> None:
        if self._writer is None:
            self._writer = asyncio.create_task(self._flush_loop(), name="ledger-audit")

    async def stop(self) -> None:
        writer = self._writer
        if writer is None:
            return
        self._writer = None
        await self._queue.put(None)
        await writer

    async def create_session(self, *, session_id: str, owner: str, token: str) -> None:
        async with self._database.session() as session, session.begin():
            session.add(
                SessionRow(
                    id=session_id,
                    owner=owner,
                    status="creating",
                    token_hash=hash_token(token),
                )
            )

    async def mark_running(self, session_id: str, sandbox_id: str) -> None:
        async with self._database.session() as session, session.begin():
            row = await session.get(SessionRow, session_id)
            if row is None:
                raise LookupError(f"会话 {session_id} 不在台账中")
            row.status = "running"
            row.sandbox_id = sandbox_id

    async def mark_ended(self, session_id: str, reason: str) -> None:
        async with self._database.session() as session, session.begin():
            row = await session.get(SessionRow, session_id)
            if row is None or row.status == "ended":
                return
            row.status = "ended"
            row.ended_at = datetime.now(UTC)
            row.end_reason = reason

    async def get(self, session_id: str) -> SessionRecord | None:
        async with self._database.session() as session:
            row = await session.get(SessionRow, session_id)
            if row is None:
                return None
            return SessionRecord(
                session_id=row.id,
                owner=row.owner,
                status=row.status,
                sandbox_id=row.sandbox_id,
                created_at=row.created_at,
                ended_at=row.ended_at,
                end_reason=row.end_reason,
            )

    async def event_count(self, session_id: str) -> int:
        async with self._database.session() as session:
            result = await session.execute(
                select(AuditEventRow.id).where(AuditEventRow.session_id == session_id)
            )
            return len(result.scalars().all())

    def submit_event(self, session_id: str, kind: str, payload: dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(_AuditRecord(session_id=session_id, kind=kind, payload=payload))
        except asyncio.QueueFull:
            self._dropped += 1
            if self._dropped % 100 == 1:
                logger.warning("审计队列已满，已丢弃 %s 条事件", self._dropped)

    async def _flush_loop(self) -> None:
        while True:
            batch: list[_AuditRecord] = []
            stopping = False
            try:
                first = await asyncio.wait_for(self._queue.get(), timeout=self._flush_interval)
            except TimeoutError:
                continue
            if first is None:
                stopping = True
            else:
                batch.append(first)
            while len(batch) < _BATCH_SIZE:
                try:
                    item = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if item is None:
                    stopping = True
                    break
                batch.append(item)
            if batch:
                await self._flush(batch)
            if stopping:
                return

    async def _flush(self, batch: list[_AuditRecord]) -> None:
        try:
            async with self._database.session() as session, session.begin():
                session.add_all(
                    [
                        AuditEventRow(
                            session_id=record.session_id,
                            kind=record.kind,
                            payload=record.payload,
                        )
                        for record in batch
                    ]
                )
        except Exception:
            self._dropped += len(batch)
            logger.exception("审计批量写入失败，丢弃 %s 条", len(batch))
