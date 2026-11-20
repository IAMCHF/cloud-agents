"""execd 管理面代理：文件树/文件预览/终端 WebSocket 转发。"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.bootstrap import Components
from app.bridge.hub import CLOSE_UNAUTHORIZED, SessionHub
from app.config import Settings
from app.main import create_app
from tests.fakes.components import build_test_components
from tests.fakes.opensandbox import FakeOpenSandbox

OWNER_TOKEN = "owner-token"
HEADERS = {"Authorization": f"Bearer {OWNER_TOKEN}"}
EXECD_TOKEN = "execd-secret"


class FakeExecd:
    """execd HTTP 端点替身；测试可按路径定制响应。"""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.routes: dict[str, Callable[[httpx.Request], httpx.Response]] = {}

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        handler = self.routes.get(request.url.path)
        if handler is None:
            return httpx.Response(404, text="not found")
        return handler(request)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        public_base_url="http://cp:8000",
        p1_auth_token=OWNER_TOKEN,
        p1_owner="alice",
        opensandbox_base_url="http://osb",
        sandbox_image="img:test",
        sandbox_start_timeout_seconds=5,
        max_active_sessions=4,
        workspace_host_root=str(tmp_path / "volumes"),
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'terminal-api.db'}",
        volume_backend="host",
        execd_access_token=EXECD_TOKEN,
    )


def _client(tmp_path: Path, osb: FakeOpenSandbox, execd: FakeExecd) -> TestClient:
    settings = _settings(tmp_path)

    async def factory(resolved: Settings, hub: SessionHub) -> Components:
        return await build_test_components(
            resolved, hub, osb=osb, execd_transport=execd.transport()
        )

    return TestClient(create_app(settings=settings, components_factory=factory))


def _create_session(client: TestClient) -> tuple[str, str]:
    created = client.post("/api/sessions", headers=HEADERS)
    assert created.status_code == 200
    body = created.json()
    return str(body["session_id"]), str(body["session_token"])


def _wait_for(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("等待条件超时")


def test_files_requires_session_token(tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    execd = FakeExecd()
    with _client(tmp_path, osb, execd) as client:
        session_id, _ = _create_session(client)
        response = client.get(f"/api/sessions/{session_id}/files?path=/workspace")
        assert response.status_code == 401


def test_list_files_and_read_file(tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    execd = FakeExecd()
    execd.routes["/directories/list"] = lambda _: httpx.Response(
        200, json=[{"path": "/workspace/a.txt", "type": "file", "size": 5}]
    )
    execd.routes["/files/download"] = lambda _: httpx.Response(200, content=b"hello")
    with _client(tmp_path, osb, execd) as client:
        session_id, token = _create_session(client)

        listing = client.get(
            f"/api/sessions/{session_id}/files", params={"token": token, "path": "/workspace"}
        )
        assert listing.status_code == 200
        assert listing.json() == {
            "path": "/workspace",
            "entries": [{"path": "/workspace/a.txt", "type": "file", "size": 5}],
        }
        assert execd.requests[-1].headers["X-EXECD-ACCESS-TOKEN"] == EXECD_TOKEN

        preview = client.get(
            f"/api/sessions/{session_id}/file", params={"token": token, "path": "/workspace/a.txt"}
        )
        assert preview.status_code == 200
        assert preview.text == "hello"


def test_file_errors_map_to_502(tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    execd = FakeExecd()
    execd.routes["/directories/list"] = lambda _: httpx.Response(500, text="boom")
    execd.routes["/files/download"] = lambda _: httpx.Response(200, content=b"x" * (512 * 1024 + 1))
    with _client(tmp_path, osb, execd) as client:
        session_id, token = _create_session(client)
        listing = client.get(
            f"/api/sessions/{session_id}/files", params={"token": token, "path": "/workspace"}
        )
        assert listing.status_code == 502
        preview = client.get(
            f"/api/sessions/{session_id}/file", params={"token": token, "path": "/workspace/big"}
        )
        assert preview.status_code == 502

        assert client.post(f"/api/sessions/{session_id}/sleep", headers=HEADERS).status_code == 204
        # 休眠后 token 仍在台账，但会话未运行，文件接口要求先恢复。
        asleep = client.get(
            f"/api/sessions/{session_id}/files", params={"token": token, "path": "/workspace"}
        )
        assert asleep.status_code == 409


def test_terminal_relays_text_bytes_and_drops_control_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    osb = FakeOpenSandbox()
    execd = FakeExecd()
    execd.routes["/pty"] = lambda _: httpx.Response(200, json={"session_id": "pty-1"})
    execd.routes["/pty/pty-1"] = lambda _: httpx.Response(204)
    holder: dict[str, FakeExecWebSocket] = {}
    connect_urls: list[str] = []

    def fake_connect(url: str, **kwargs: Any) -> FakeExecWebSocket:
        connect_urls.append(url)
        holder.setdefault("ws", FakeExecWebSocket())
        return holder["ws"]

    monkeypatch.setattr("websockets.asyncio.client.connect", fake_connect)

    with _client(tmp_path, osb, execd) as client:
        session_id, token = _create_session(client)
        with client.websocket_connect(f"/api/sessions/{session_id}/terminal?token={token}") as ws:
            _wait_for(lambda: "ws" in holder)
            exec_ws = holder["ws"]
            ws.send_text('{"type":"stdin","data":"echo hi\\n"}')
            _wait_for(lambda: bool(exec_ws.sent))
            assert exec_ws.sent == ['{"type":"stdin","data":"echo hi\\n"}']

            exec_ws.push(b"\x01hi\r\n")
            assert ws.receive_bytes() == b"hi\r\n"

            exec_ws.push(b"\x03ignored")
            exec_ws.push('{"type":"status"}')
            assert ws.receive_text() == '{"type":"status"}'

        _wait_for(lambda: bool(execd.requests) and execd.requests[-1].method == "DELETE")

    assert connect_urls == ["ws://execd.test:44772/pty/pty-1/ws"]
    assert execd.requests[-1].url.path == "/pty/pty-1"
    assert execd.requests[-1].headers["X-EXECD-ACCESS-TOKEN"] == EXECD_TOKEN


def test_terminal_rejects_bad_token(tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    execd = FakeExecd()
    with _client(tmp_path, osb, execd) as client:
        session_id, _ = _create_session(client)
        with client.websocket_connect(f"/api/sessions/{session_id}/terminal?token=wrong") as ws:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                ws.receive_text()
        assert excinfo.value.code == CLOSE_UNAUTHORIZED
        assert all(request.url.path != "/pty" for request in execd.requests)


class FakeExecWebSocket:
    """execd PTY WebSocket 替身：跨线程投递服务端帧。"""

    def __init__(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.sent: list[Any] = []
        self._incoming: asyncio.Queue[Any] = asyncio.Queue()

    async def send(self, message: Any) -> None:
        self.sent.append(message)

    def push(self, message: Any) -> None:
        self.loop.call_soon_threadsafe(self._incoming.put_nowait, message)

    def __aiter__(self) -> FakeExecWebSocket:
        return self

    async def __anext__(self) -> Any:
        return await self._incoming.get()

    async def __aenter__(self) -> FakeExecWebSocket:
        return self

    async def __aexit__(self, *_: Any) -> bool:
        return False
