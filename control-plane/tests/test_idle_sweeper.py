"""空闲 sweeper 与审批超时测试。"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from starlette.websockets import WebSocket

from app.bridge.hub import SessionChannel, SessionHub
from app.config import Settings
from app.ledger import Database, Ledger
from app.metrics import Metrics
from app.sandbox import IdleSweeper, OpenSandboxClient, SandboxManager, SessionHandle
from tests.fakes.opensandbox import FakeOpenSandbox

APPROVAL = json.dumps(
    {
        "id": "approval-1",
        "method": "item/commandExecution/requestApproval",
        "params": {"threadId": "t", "turnId": "u", "itemId": "i", "startedAtMs": 0},
    }
)


class _FakeBridge:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed = False

    async def send_text(self, data: str) -> None:
        self.sent.append(data)

    async def close(self, code: int = 0, reason: str = "") -> None:
        self.closed = True


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'idle.db'}",
        public_base_url="http://127.0.0.1:1",
        workspace_host_root=str(tmp_path / "ws"),
        idle_timeout_seconds=10,
        idle_sweep_interval_seconds=60,
        approval_timeout_seconds=10,
    )


async def _ledger(settings: Settings) -> Ledger:
    database = Database(settings.database_url)
    await database.create_schema()
    ledger = Ledger(database, flush_interval=0.01)
    await ledger.start()
    return ledger


@asynccontextmanager
async def _env(
    tmp_path: Path,
) -> AsyncIterator[tuple[Settings, Ledger, SessionHub, FakeOpenSandbox, SandboxManager]]:
    settings = _settings(tmp_path)
    ledger = await _ledger(settings)
    hub = SessionHub()
    osb = FakeOpenSandbox()
    manager = SandboxManager(
        settings=settings,
        hub=hub,
        ledger=ledger,
        client=OpenSandboxClient(base_url="http://osb", transport=osb.transport()),
        detach_settle_seconds=0,
    )
    try:
        yield settings, ledger, hub, osb, manager
    finally:
        await ledger.stop()


async def _running_session(
    manager: SandboxManager, hub: SessionHub
) -> tuple[SessionHandle, SessionChannel]:
    handle = await manager.create_session("alice", "default")
    channel = hub.get(handle.session_id)
    assert channel is not None
    return handle, channel


def test_idle_candidates_require_bridge_silence_and_no_clients() -> None:
    hub = SessionHub()
    channel = hub.create("s1", "tok", "alice")
    channel.last_activity = time.monotonic() - 100
    assert hub.idle_candidates(timeout=10) == []

    bridge = _FakeBridge()
    channel.bridge = cast(WebSocket, bridge)
    assert [c.session_id for c in hub.idle_candidates(timeout=10)] == ["s1"]

    channel.active_turn = True
    assert hub.idle_candidates(timeout=10) == []

    channel.active_turn = False
    channel.pending["approval-1"] = APPROVAL
    channel.pending_since["approval-1"] = time.monotonic()
    assert hub.idle_candidates(timeout=10) == []


async def test_expire_pending_declines_with_original_id() -> None:
    hub = SessionHub()
    events: list[tuple[str, str, dict[str, object]]] = []
    hub.on_audit = lambda session_id, kind, payload: events.append((session_id, kind, payload))
    channel = hub.create("s1", "tok", "alice")
    bridge = _FakeBridge()
    channel.bridge = cast(WebSocket, bridge)
    channel.pending["approval-1"] = APPROVAL
    channel.pending_since["approval-1"] = time.monotonic() - 100

    assert await hub.expire_pending(channel, older_than=10) == 1

    assert channel.pending == {}
    assert channel.pending_since == {}
    payload = json.loads(bridge.sent[0])
    assert payload == {"id": "approval-1", "result": {"decision": "decline"}}
    assert (
        "s1",
        "approval.timeout",
        {"request_id": "approval-1", "method": "item/commandExecution/requestApproval"},
    ) in events


async def test_sweeper_sleeps_idle_session_and_emits_metric(tmp_path: Path) -> None:
    async with _env(tmp_path) as (settings, ledger, hub, osb, manager):
        handle, channel = await _running_session(manager, hub)
        channel.bridge = cast(WebSocket, _FakeBridge())
        channel.last_activity = time.monotonic() - 100
        metrics = Metrics()
        sweeper = IdleSweeper(hub=hub, manager=manager, settings=settings, metrics=metrics)

        assert await sweeper.sweep_once() == 1

        assert osb.deleted == ["sb-1"]
        record = await ledger.get(handle.session_id)
        assert record is not None and record.status == "idle"
        assert b'cloud_agents_idle_sessions_slept_total{reason="idle"} 1.0' in metrics.render()


async def test_sweeper_does_not_sleep_active_turn(tmp_path: Path) -> None:
    async with _env(tmp_path) as (settings, ledger, hub, osb, manager):
        handle, channel = await _running_session(manager, hub)
        channel.bridge = cast(WebSocket, _FakeBridge())
        channel.active_turn = True
        channel.last_activity = time.monotonic() - 100
        sweeper = IdleSweeper(hub=hub, manager=manager, settings=settings)

        assert await sweeper.sweep_once() == 0

        assert osb.deleted == []
        record = await ledger.get(handle.session_id)
        assert record is not None and record.status == "running"


async def test_sweeper_expires_approval_before_idle(tmp_path: Path) -> None:
    async with _env(tmp_path) as (settings, _ledger_record, hub, osb, manager):
        _handle, channel = await _running_session(manager, hub)
        bridge = _FakeBridge()
        channel.bridge = cast(WebSocket, bridge)
        channel.active_turn = True
        channel.pending["approval-1"] = APPROVAL
        channel.pending_since["approval-1"] = time.monotonic() - 100
        metrics = Metrics()
        sweeper = IdleSweeper(hub=hub, manager=manager, settings=settings, metrics=metrics)

        assert await sweeper.sweep_once() == 0

        assert channel.pending == {}
        assert json.loads(bridge.sent[0])["result"] == {"decision": "decline"}
        assert osb.deleted == []
        assert b"cloud_agents_approval_timeouts_total 1.0" in metrics.render()
