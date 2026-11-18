from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.bridge.hub import (
    CLOSE_SLOW_CLIENT,
    CLOSE_UNAUTHORIZED,
    AuditHook,
    SessionHub,
)
from app.config import Settings
from app.ledger import Database, Ledger
from app.main import create_app

TOKEN = "session-token"
APPROVAL = json.dumps(
    {
        "id": "approval-1",
        "method": "item/commandExecution/requestApproval",
        "params": {"threadId": "t", "turnId": "u", "itemId": "i", "startedAtMs": 0},
    }
)
APPROVAL_RESPONSE = '{"id":"approval-1","result":{"decision":"accept"}}'


def _client(hub: SessionHub) -> TestClient:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{Path(tempfile.mkdtemp()) / 'hub.db'}",
        public_base_url="http://127.0.0.1:1",
    )
    hub.create("s1", TOKEN, "alice")
    return _client_with_settings(settings, hub)


def _client_with_settings(settings: Settings, hub: SessionHub) -> TestClient:
    async def _init() -> None:
        database = Database(settings.database_url)
        await database.create_schema()
        await database.dispose()

    asyncio.run(_init())
    return TestClient(create_app(settings=settings, hub=hub))


def _wait_pending(hub: SessionHub, session_id: str, request_id: str) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        channel = hub.get(session_id)
        if channel is not None and request_id in channel.pending:
            return
        time.sleep(0.01)
    raise AssertionError(f"未等到未决请求 {request_id}")


def _wait_no_pending(hub: SessionHub, session_id: str, request_id: str) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        channel = hub.get(session_id)
        if channel is None or request_id not in channel.pending:
            return
        time.sleep(0.01)
    raise AssertionError(f"未决请求 {request_id} 未被清除")


def _wait_event(events: list[tuple[str, str, dict[str, Any]]], kind: str) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if any(recorded == kind for _, recorded, _ in events):
            return
        time.sleep(0.01)
    raise AssertionError(f"未收到审计事件 {kind}")


def _wait_channel(hub: SessionHub, session_id: str) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        channel = hub.get(session_id)
        if channel is not None and channel.bridge is not None:
            return
        time.sleep(0.01)
    raise AssertionError(f"会话 {session_id} 通道/桥接未就绪")


def _wait_clients(hub: SessionHub, session_id: str, count: int) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        channel = hub.get(session_id)
        if channel is not None and len(channel.clients) == count:
            return
        time.sleep(0.01)
    raise AssertionError(f"客户端在线数未达到 {count}")


def _audit_sink(events: list[tuple[str, str, dict[str, Any]]]) -> AuditHook:
    def record(session_id: str, kind: str, payload: dict[str, Any]) -> None:
        events.append((session_id, kind, payload))

    return record


class _FakeWebSocket:
    """阻塞发送的 WebSocket 替身：用于制造慢客户端积压。"""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed: list[int] = []
        self._gate = asyncio.Event()

    async def send_text(self, frame: str) -> None:
        await self._gate.wait()
        self.sent.append(frame)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed.append(code)


def test_healthz() -> None:
    with _client(SessionHub()) as client:
        assert client.get("/healthz").json() == {"status": "ok"}


def test_unauthorized_client_is_closed() -> None:
    with _client(SessionHub()) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/session/s1?token=wrong") as websocket:
                websocket.receive_text()
    assert exc_info.value.code == CLOSE_UNAUTHORIZED


def test_relays_frames_between_bridge_and_client() -> None:
    hub = SessionHub()
    with _client(hub) as client:
        with client.websocket_connect(f"/ws/bridge/s1?token={TOKEN}") as bridge:
            with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as web:
                bridge.send_text('{"method":"turn/started","params":{"threadId":"t"}}')
                message: Any = json.loads(web.receive_text())
                assert message["method"] == "turn/started"

                web.send_text('{"id":7,"method":"initialize","params":{}}')
                forwarded: Any = json.loads(bridge.receive_text())
                assert forwarded["id"] == 7


def test_broadcasts_bridge_frames_to_all_clients() -> None:
    hub = SessionHub()
    with _client(hub) as client:
        with client.websocket_connect(f"/ws/bridge/s1?token={TOKEN}") as bridge:
            with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as first:
                with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as second:
                    _wait_clients(hub, "s1", 2)
                    bridge.send_text('{"method":"turn/started","params":{"threadId":"t"}}')
                    bridge.send_text('{"method":"item/agentMessage/delta","params":{"delta":"x"}}')
                    for web in (first, second):
                        methods = [json.loads(web.receive_text())["method"] for _ in range(2)]
                        assert methods == ["turn/started", "item/agentMessage/delta"]


def test_replays_pending_approval_on_client_connect() -> None:
    hub = SessionHub()
    with _client(hub) as client:
        with client.websocket_connect(f"/ws/bridge/s1?token={TOKEN}") as bridge:
            bridge.send_text(APPROVAL)
            _wait_pending(hub, "s1", "approval-1")

            with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as web:
                replayed: Any = json.loads(web.receive_text())
                assert replayed["id"] == "approval-1"
                web.send_text(APPROVAL_RESPONSE)
                _wait_no_pending(hub, "s1", "approval-1")


def test_pending_approval_reaches_every_client_and_first_response_wins() -> None:
    hub = SessionHub()
    events: list[tuple[str, str, dict[str, Any]]] = []
    with _client(hub) as client:
        # lifespan 装配会注入真实台账钩子，测试在其后覆盖为收集器。
        hub.on_audit = _audit_sink(events)
        with client.websocket_connect(f"/ws/bridge/s1?token={TOKEN}") as bridge:
            bridge.send_text(APPROVAL)
            _wait_pending(hub, "s1", "approval-1")

            with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as first:
                assert json.loads(first.receive_text())["id"] == "approval-1"
                with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as second:
                    assert json.loads(second.receive_text())["id"] == "approval-1"

                    second.send_text(APPROVAL_RESPONSE)
                    forwarded: Any = json.loads(bridge.receive_text())
                    assert forwarded == json.loads(APPROVAL_RESPONSE)
                    _wait_no_pending(hub, "s1", "approval-1")

                    # 重复响应丢弃：同一连接上的后续帧仍按序到达桥接。
                    first.send_text('{"id":"approval-1","result":{"decision":"decline"}}')
                    first.send_text('{"id":9,"method":"thread/list","params":{}}')
                    assert json.loads(bridge.receive_text())["id"] == 9

        _wait_event(events, "client.disconnected")
    kinds = [kind for _, kind, _ in events]
    assert kinds.count("client.connected") == 2
    assert "client.response" in kinds
    assert "client.response_duplicate" in kinds
    response = next(payload for _, kind, payload in events if kind == "client.response")
    assert response["actor"] == "alice"
    assert response["decision"] == "accept"
    assert response["method"] == "item/commandExecution/requestApproval"


def test_slow_client_is_dropped_without_blocking_others() -> None:
    hub = SessionHub()
    events: list[tuple[str, str, dict[str, Any]]] = []
    hub.on_audit = _audit_sink(events)
    channel = hub.create("s1", TOKEN, "alice")
    fake = _FakeWebSocket()

    async def _run() -> None:
        connection_id = await hub.attach_client(channel, cast(WebSocket, fake), actor="alice")
        for index in range(400):
            await hub.from_bridge(channel, f'{{"method":"delta","params":{{"n":{index}}}}}')
        await hub.detach_client(channel, connection_id)

    asyncio.run(_run())
    assert channel.clients == {}
    assert fake.closed == [CLOSE_SLOW_CLIENT]
    assert any(kind == "client.dropped" for _, kind, _ in events)


def test_rebuilds_channel_from_ledger_on_connect() -> None:
    """多副本/重启：本进程没有通道时，凭台账中的 running 会话重建（token 与会话必须匹配）。"""
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{Path(tempfile.mkdtemp()) / 'rebuild.db'}",
        public_base_url="http://127.0.0.1:1",
    )

    async def _seed() -> None:
        database = Database(settings.database_url)
        await database.create_schema()
        ledger = Ledger(database)
        await ledger.admit_session(
            session_id="s9",
            owner="alice",
            token="tok-9",
            tenant_id="default",
            max_active_sessions=10,
        )
        await ledger.admit_session(
            session_id="s10",
            owner="bob",
            token="tok-10",
            tenant_id="default",
            max_active_sessions=10,
        )
        await ledger.mark_ended("s10", "stopped")
        await database.dispose()

    asyncio.run(_seed())
    hub = SessionHub()
    with _client_with_settings(settings, hub) as client:
        assert hub.get("s9") is None
        with client.websocket_connect("/ws/bridge/s9?token=tok-9") as bridge:
            with client.websocket_connect("/ws/session/s9?token=tok-9") as web:
                _wait_channel(hub, "s9")
                channel = hub.get("s9")
                assert channel is not None
                assert channel.owner == "alice"
                bridge.send_text('{"method":"turn/started","params":{}}')
                assert json.loads(web.receive_text())["method"] == "turn/started"

        for path in ("/ws/session/s9?token=other", "/ws/session/s10?token=tok-10"):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect(path) as websocket:
                    websocket.receive_text()
            assert exc_info.value.code == CLOSE_UNAUTHORIZED


def test_client_without_bridge_is_rejected_before_upgrade() -> None:
    hub = SessionHub()
    with _client(hub) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/session/s1?token={TOKEN}"):
                pass
    assert exc_info.value.code == 1013
