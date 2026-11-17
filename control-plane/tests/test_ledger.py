from __future__ import annotations

import asyncio

from app.ledger import Ledger


async def _wait_events(ledger: Ledger, session_id: str, expected: int) -> None:
    for _ in range(100):
        if await ledger.event_count(session_id) >= expected:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("审计事件未在预期时间内落库")


async def test_session_lifecycle_and_audit(ledger: Ledger) -> None:
    await ledger.create_session(session_id="s1", owner="alice", token="tok")
    record = await ledger.get("s1")
    assert record is not None
    assert record.status == "creating"

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
    await ledger.create_session(session_id="s2", owner="alice", token="tok")
    await ledger.mark_ended("s2", "first")
    await ledger.mark_ended("s2", "second")

    record = await ledger.get("s2")
    assert record is not None
    assert record.end_reason == "first"
