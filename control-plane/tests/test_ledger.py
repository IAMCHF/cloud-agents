from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.auth import Principal
from app.ledger import Ledger


async def _wait_events(ledger: Ledger, session_id: str, expected: int) -> None:
    for _ in range(100):
        if await ledger.event_count(session_id) >= expected:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("审计事件未在预期时间内落库")


async def test_session_lifecycle_and_audit(ledger: Ledger) -> None:
    await ledger.create_session(session_id="s1", owner="alice", token="tok", tenant_id="acme")
    record = await ledger.get("s1")
    assert record is not None
    assert record.status == "creating"
    assert record.tenant_id == "acme"

    await ledger.mark_running("s1", "sb-1")
    ledger.submit_event("s1", "session.created", {"sandbox_id": "sb-1"})
    ledger.submit_event("s1", "turn.started", {"turn_id": "t1"})
    await _wait_events(ledger, "s1", 2)

    await ledger.mark_ended("s1", "stopped")
    record = await ledger.get("s1")
    assert record is not None
    assert record.status == "ended"
    assert record.end_reason == "stopped"
    assert record.ended_at is not None


async def test_mark_ended_is_idempotent(ledger: Ledger) -> None:
    await ledger.create_session(session_id="s2", owner="alice", token="tok", tenant_id="default")
    await ledger.mark_ended("s2", "first")
    await ledger.mark_ended("s2", "second")

    record = await ledger.get("s2")
    assert record is not None
    assert record.end_reason == "first"


async def test_end_stale_sessions_marks_unfinished(ledger: Ledger) -> None:
    await ledger.create_session(session_id="s3", owner="alice", token="tok", tenant_id="default")
    await ledger.create_session(session_id="s4", owner="alice", token="tok", tenant_id="default")
    await ledger.mark_running("s4", "sb-1")
    await ledger.mark_ended("s1", "stopped")

    ended = await ledger.end_stale_sessions("control_plane_restart")

    assert ended == 2
    record = await ledger.get("s4")
    assert record is not None
    assert record.status == "ended"
    assert record.end_reason == "control_plane_restart"


async def test_ensure_principal_creates_tenant_and_updates_last_seen(ledger: Ledger) -> None:
    principal = Principal(
        subject="kc-alice", username="alice", tenant_id="acme", email="alice@example.com"
    )
    user = await ledger.ensure_principal(
        principal, tenant_max_active_sessions=3, tenant_monthly_token_budget=1000
    )
    assert user.tenant_id == "acme"
    assert user.username == "alice"
    assert user.email == "alice@example.com"

    tenant = await ledger.get_tenant("acme")
    assert tenant is not None
    assert tenant.max_active_sessions == 3
    assert tenant.monthly_token_budget == 1000

    # 再次登录只刷新用户信息；已建档租户的配额不被部署默认值覆盖。
    again = await ledger.ensure_principal(
        Principal(subject="kc-alice", username="alice2", tenant_id="acme"),
        tenant_max_active_sessions=99,
        tenant_monthly_token_budget=99,
    )
    assert again.username == "alice2"
    assert again.last_seen_at >= user.last_seen_at
    tenant = await ledger.get_tenant("acme")
    assert tenant is not None
    assert tenant.max_active_sessions == 3
    assert tenant.monthly_token_budget == 1000


async def test_record_usage_and_total_since(ledger: Ledger) -> None:
    now = datetime.now(UTC)
    await ledger.record_usage(
        session_id="s1", tenant_id="acme", model="m1", input_tokens=10, output_tokens=5
    )
    await ledger.record_usage(
        session_id="s2", tenant_id="acme", model="m1", input_tokens=1, output_tokens=2
    )

    assert await ledger.usage_total("acme", since=now - timedelta(minutes=1)) == 18
    assert await ledger.usage_total("acme", since=now + timedelta(minutes=1)) == 0
    assert await ledger.usage_total("other", since=now - timedelta(minutes=1)) == 0


async def test_active_counts_exclude_ended_sessions(ledger: Ledger) -> None:
    await ledger.create_session(session_id="a1", owner="alice", token="t", tenant_id="acme")
    await ledger.create_session(session_id="a2", owner="bob", token="t", tenant_id="acme")
    await ledger.create_session(session_id="a3", owner="alice", token="t", tenant_id="other")
    await ledger.mark_running("a1", "sb-1")
    await ledger.mark_ended("a3", "stopped")

    assert await ledger.active_count() == 2
    assert await ledger.active_count_for_tenant("acme") == 2
    assert await ledger.active_count_for_tenant("other") == 0
    assert await ledger.active_count_for_owner("alice") == 1
