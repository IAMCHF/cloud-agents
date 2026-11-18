from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.bridge.hub import CLOSE_CONFLICT, CLOSE_UNAUTHORIZED, SessionHub
from app.config import Settings
from app.ledger import Database
from app.main import create_app

TOKEN = "session-token"
APPROVAL = json.dumps(
    {
        "id": "approval-1",
        "method": "item/commandExecution/requestApproval",
        "params": {"threadId": "t", "turnId": "u", "itemId": "i", "startedAtMs": 0},
    }
)


def _client(hub: SessionHub) -> TestClient:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{Path(tempfile.mkdtemp()) / 'hub.db'}",
        public_base_url="http://127.0.0.1:1",
    )

    async def _init() -> None:
        database = Database(settings.database_url)
        await database.create_schema()
        await database.dispose()

    asyncio.run(_init())
    hub.create("s1", TOKEN, "alice")
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
        with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as web:
            with client.websocket_connect(f"/ws/bridge/s1?token={TOKEN}") as bridge:
                bridge.send_text('{"method":"turn/started","params":{"threadId":"t"}}')
                message: Any = json.loads(web.receive_text())
                assert message["method"] == "turn/started"

                web.send_text('{"id":7,"method":"initialize","params":{}}')
                forwarded: Any = json.loads(bridge.receive_text())
                assert forwarded["id"] == 7


def test_replays_pending_approval_on_client_connect() -> None:
    hub = SessionHub()
    with _client(hub) as client:
        with client.websocket_connect(f"/ws/bridge/s1?token={TOKEN}") as bridge:
            bridge.send_text(APPROVAL)
            _wait_pending(hub, "s1", "approval-1")

            with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as web:
                replayed: Any = json.loads(web.receive_text())
                assert replayed["id"] == "approval-1"
                web.send_text('{"id":"approval-1","result":{"decision":"accept"}}')
                _wait_no_pending(hub, "s1", "approval-1")


def test_second_client_is_rejected() -> None:
    hub = SessionHub()
    with _client(hub) as client:
        with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as first:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as second:
                    second.receive_text()
            assert exc_info.value.code == CLOSE_CONFLICT
            first.send_text('{"id":1,"method":"initialize","params":{}}')


def test_client_without_bridge_is_closed_with_try_again() -> None:
    hub = SessionHub()
    with _client(hub) as client:
        with client.websocket_connect(f"/ws/session/s1?token={TOKEN}") as web:
            web.send_text('{"id":1,"method":"initialize","params":{}}')
            with pytest.raises(WebSocketDisconnect) as exc_info:
                web.receive_text()
            assert exc_info.value.code == 1013
