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
from typing import Any, cast

from sqlalchemy import func, select, text, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.auth import Principal
from app.ledger.database import Database
from app.ledger.models import AuditEventRow, LlmUsageRow, SessionRow, TenantRow, UserRow

logger = logging.getLogger(__name__)

_BATCH_SIZE = 200
_QUEUE_SIZE = 10_000
# 计入并发配额的会话状态：创建中与运行中。
_ACTIVE_STATUSES = ("creating", "running")
# 全局准入事务锁键（任意固定 int64，仅用于串行化准入）。
_ADMISSION_LOCK_KEY = 0x434C4F55


class AdmissionRejectedError(RuntimeError):
    """准入拒绝：全局/租户/同属主活跃会话达到上限。"""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class SessionStateError(RuntimeError):
    """会话状态不允许当前操作（例如非 idle 会话执行 resume）。"""


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    owner: str
    tenant_id: str
    status: str
    sandbox_id: str | None
    created_at: datetime
    ended_at: datetime | None
    end_reason: str | None


@dataclass(frozen=True)
class TenantRecord:
    tenant_id: str
    name: str
    max_active_sessions: int
    monthly_token_budget: int
    created_at: datetime


@dataclass(frozen=True)
class UserRecord:
    subject: str
    tenant_id: str
    username: str | None
    email: str | None
    created_at: datetime
    last_seen_at: datetime


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

    async def create_session(
        self, *, session_id: str, owner: str, token: str, tenant_id: str
    ) -> None:
        async with self._database.session() as session, session.begin():
            session.add(
                SessionRow(
                    id=session_id,
                    owner=owner,
                    tenant_id=tenant_id,
                    status="creating",
                    token_hash=hash_token(token),
                )
            )

    async def admit_session(
        self,
        *,
        session_id: str,
        owner: str,
        token: str,
        tenant_id: str,
        max_active_sessions: int,
    ) -> None:
        """准入并落 creating 会话行：全局、租户、同属主三层校验在同一事务内完成。

        单进程由 Database.lock 串行化，多副本由 Postgres 事务级 advisory lock 串行化；
        SQLite（测试）没有 advisory lock，靠进程内锁即可。
        """
        async with self._database.lock, self._database.session() as session, session.begin():
            if self._database.dialect_name == "postgresql":
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"), {"key": _ADMISSION_LOCK_KEY}
                )
            if await self._count_sessions(session) >= max_active_sessions:
                raise AdmissionRejectedError("达到全局活跃会话上限（max_active_sessions）")
            tenant = await session.get(TenantRow, tenant_id)
            if tenant is not None and tenant.max_active_sessions > 0:
                tenant_active = await self._count_sessions(session, tenant_id=tenant_id)
                if tenant_active >= tenant.max_active_sessions:
                    raise AdmissionRejectedError(
                        f"租户 {tenant_id} 活跃会话达到上限（{tenant.max_active_sessions}）"
                    )
            if await self._count_sessions(session, owner=owner) > 0:
                raise AdmissionRejectedError("同用户已有活跃会话")
            session.add(
                SessionRow(
                    id=session_id,
                    owner=owner,
                    tenant_id=tenant_id,
                    status="creating",
                    token_hash=hash_token(token),
                )
            )

    async def begin_resume(
        self,
        *,
        session_id: str,
        token: str,
        max_active_sessions: int,
    ) -> SessionRecord:
        """把 idle 会话重新纳入准入并置 creating；配额校验与状态变更同一事务。"""
        async with self._database.lock, self._database.session() as session, session.begin():
            if self._database.dialect_name == "postgresql":
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"), {"key": _ADMISSION_LOCK_KEY}
                )
            row = await session.get(SessionRow, session_id)
            if row is None:
                raise LookupError(f"会话 {session_id} 不在台账中")
            if row.status != "idle":
                raise SessionStateError(f"会话状态 {row.status} 不可恢复")
            if await self._count_sessions(session) >= max_active_sessions:
                raise AdmissionRejectedError("达到全局活跃会话上限（max_active_sessions）")
            tenant = await session.get(TenantRow, row.tenant_id)
            if tenant is not None and tenant.max_active_sessions > 0:
                tenant_active = await self._count_sessions(
                    session, tenant_id=row.tenant_id, exclude_session_id=session_id
                )
                if tenant_active >= tenant.max_active_sessions:
                    raise AdmissionRejectedError(
                        f"租户 {row.tenant_id} 活跃会话达到上限（{tenant.max_active_sessions}）"
                    )
            if (
                await self._count_sessions(session, owner=row.owner, exclude_session_id=session_id)
                > 0
            ):
                raise AdmissionRejectedError("同用户已有活跃会话")
            row.status = "creating"
            row.token_hash = hash_token(token)
            row.sandbox_id = None
            row.ended_at = None
            row.end_reason = None
            record = _session_record(row)
        return record

    async def ensure_tenant(
        self, tenant_id: str, *, max_active_sessions: int, monthly_token_budget: int
    ) -> TenantRecord:
        """租户首次出现时按部署默认值建档；已存在则保留管理侧配额，不覆盖。"""
        async with self._database.session() as session, session.begin():
            row = await session.get(TenantRow, tenant_id)
            if row is None:
                row = TenantRow(
                    id=tenant_id,
                    name=tenant_id,
                    max_active_sessions=max_active_sessions,
                    monthly_token_budget=monthly_token_budget,
                )
                session.add(row)
            record = _tenant_record(row)
        return record

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        async with self._database.session() as session:
            row = await session.get(TenantRow, tenant_id)
            return None if row is None else _tenant_record(row)

    async def ensure_principal(
        self,
        principal: Principal,
        *,
        tenant_max_active_sessions: int,
        tenant_monthly_token_budget: int,
    ) -> UserRecord:
        """登录即建档：租户不存在按默认配额创建；用户按 subject upsert 并刷新 last_seen_at。"""
        async with self._database.session() as session, session.begin():
            if await session.get(TenantRow, principal.tenant_id) is None:
                session.add(
                    TenantRow(
                        id=principal.tenant_id,
                        name=principal.tenant_id,
                        max_active_sessions=tenant_max_active_sessions,
                        monthly_token_budget=tenant_monthly_token_budget,
                    )
                )
            now = datetime.now(UTC)
            row = await session.get(UserRow, principal.subject)
            if row is None:
                row = UserRow(
                    subject=principal.subject,
                    tenant_id=principal.tenant_id,
                    username=principal.username,
                    email=principal.email,
                    created_at=now,
                    last_seen_at=now,
                )
                session.add(row)
            else:
                row.tenant_id = principal.tenant_id
                row.username = principal.username
                row.email = principal.email
                row.last_seen_at = now
            record = _user_record(row)
        return record

    async def record_usage(
        self,
        *,
        session_id: str,
        tenant_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        async with self._database.session() as session, session.begin():
            session.add(
                LlmUsageRow(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )

    async def usage_total(self, tenant_id: str, *, since: datetime) -> int:
        """租户在 since 之后的 token 总量（输入+输出），用于月度预算判定。"""
        async with self._database.session() as session:
            result = await session.execute(
                select(
                    func.coalesce(func.sum(LlmUsageRow.input_tokens + LlmUsageRow.output_tokens), 0)
                ).where(LlmUsageRow.tenant_id == tenant_id, LlmUsageRow.created_at >= since)
            )
            return int(result.scalar_one())

    async def active_count(self) -> int:
        async with self._database.session() as session:
            return await self._count_sessions(session)

    async def active_count_for_tenant(self, tenant_id: str) -> int:
        async with self._database.session() as session:
            return await self._count_sessions(session, tenant_id=tenant_id)

    async def active_count_for_owner(self, owner: str) -> int:
        async with self._database.session() as session:
            return await self._count_sessions(session, owner=owner)

    async def _count_sessions(
        self,
        session: AsyncSession,
        *,
        tenant_id: str | None = None,
        owner: str | None = None,
        exclude_session_id: str | None = None,
    ) -> int:
        conditions: list[ColumnElement[bool]] = [SessionRow.status.in_(_ACTIVE_STATUSES)]
        if tenant_id is not None:
            conditions.append(SessionRow.tenant_id == tenant_id)
        if owner is not None:
            conditions.append(SessionRow.owner == owner)
        if exclude_session_id is not None:
            conditions.append(SessionRow.id != exclude_session_id)
        result = await session.execute(
            select(func.count()).select_from(SessionRow).where(*conditions)
        )
        return int(result.scalar_one())

    async def mark_running(self, session_id: str, sandbox_id: str) -> None:
        async with self._database.session() as session, session.begin():
            row = await session.get(SessionRow, session_id)
            if row is None:
                raise LookupError(f"会话 {session_id} 不在台账中")
            row.status = "running"
            row.sandbox_id = sandbox_id

    async def _transition(
        self,
        session_id: str,
        *,
        from_statuses: tuple[str, ...],
        to_status: str,
        sandbox_id: str | None = None,
        set_sandbox: bool = False,
        reason: str | None = None,
    ) -> bool:
        values: dict[str, Any] = {"status": to_status, "end_reason": reason}
        if set_sandbox:
            values["sandbox_id"] = sandbox_id
        async with self._database.session() as session, session.begin():
            result = cast(
                CursorResult[Any],
                await session.execute(
                    update(SessionRow)
                    .where(SessionRow.id == session_id, SessionRow.status.in_(from_statuses))
                    .values(**values)
                ),
            )
            return (result.rowcount or 0) > 0

    async def mark_sleeping(self, session_id: str, reason: str) -> bool:
        """running → sleeping：先退出活跃配额，再销毁沙箱。"""
        return await self._transition(
            session_id,
            from_statuses=("running",),
            to_status="sleeping",
            reason=reason,
        )

    async def mark_idle(self, session_id: str, reason: str) -> bool:
        """creating/running/sleeping → idle：沙箱已不存在，卷保留供冷恢复。"""
        return await self._transition(
            session_id,
            from_statuses=("creating", "running", "sleeping"),
            to_status="idle",
            sandbox_id=None,
            set_sandbox=True,
            reason=reason,
        )

    async def revert_to_running(self, session_id: str, sandbox_id: str) -> bool:
        return await self._transition(
            session_id,
            from_statuses=("sleeping",),
            to_status="running",
            sandbox_id=sandbox_id,
            set_sandbox=True,
        )

    async def list_sessions_by_status(self, status: str) -> list[SessionRecord]:
        async with self._database.session() as session:
            result = await session.execute(select(SessionRow).where(SessionRow.status == status))
            return [_session_record(row) for row in result.scalars().all()]

    async def mark_ended(self, session_id: str, reason: str) -> None:
        async with self._database.session() as session, session.begin():
            row = await session.get(SessionRow, session_id)
            if row is None or row.status == "ended":
                return
            row.status = "ended"
            row.ended_at = datetime.now(UTC)
            row.end_reason = reason

    async def end_stale_creating(self, *, older_than: datetime, reason: str) -> int:
        """控制面重启对账：只结束卡在 creating 且超过时限的会话；running 保留供 WS 重连重建。"""
        async with self._database.session() as session, session.begin():
            result = cast(
                CursorResult[Any],
                await session.execute(
                    update(SessionRow)
                    .where(SessionRow.status == "creating", SessionRow.created_at < older_than)
                    .values(status="ended", ended_at=datetime.now(UTC), end_reason=reason)
                ),
            )
            return result.rowcount or 0

    async def find_session_by_token(self, token: str) -> SessionRecord | None:
        """按会话 token 反查台账（LLM 网关鉴权与租户归因；多副本下无需本进程通道）。"""
        if not token:
            return None
        async with self._database.session() as session:
            result = await session.execute(
                select(SessionRow).where(SessionRow.token_hash == hash_token(token))
            )
            row = result.scalar_one_or_none()
            return None if row is None else _session_record(row)

    async def get(self, session_id: str) -> SessionRecord | None:
        async with self._database.session() as session:
            row = await session.get(SessionRow, session_id)
            if row is None:
                return None
            return _session_record(row)

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


def _session_record(row: SessionRow) -> SessionRecord:
    return SessionRecord(
        session_id=row.id,
        owner=row.owner,
        tenant_id=row.tenant_id,
        status=row.status,
        sandbox_id=row.sandbox_id,
        created_at=row.created_at,
        ended_at=row.ended_at,
        end_reason=row.end_reason,
    )


def _tenant_record(row: TenantRow) -> TenantRecord:
    return TenantRecord(
        tenant_id=row.id,
        name=row.name,
        max_active_sessions=row.max_active_sessions,
        monthly_token_budget=row.monthly_token_budget,
        created_at=row.created_at,
    )


def _user_record(row: UserRow) -> UserRecord:
    return UserRecord(
        subject=row.subject,
        tenant_id=row.tenant_id,
        username=row.username,
        email=row.email,
        created_at=row.created_at,
        last_seen_at=row.last_seen_at,
    )
