"""子域预览：Host 解析、签名票据、HTTP/WS 反代。"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.preview import (
    COOKIE_NAME,
    mint_preview_token,
    parse_preview_host,
    preview_host,
    verify_preview_token,
)
from app.bootstrap import Components
from app.bridge.hub import SessionHub
from app.config import Settings
from app.main import create_app
from tests.fakes.components import build_test_components
from tests.fakes.opensandbox import FakeOpenSandbox
from tests.test_terminal_api import FakeExecWebSocket, _wait_for

OWNER_TOKEN = "owner-token"
HEADERS = {"Authorization": f"Bearer {OWNER_TOKEN}"}
BASE = "127.0.0.1.nip.io"


class _BodyStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"<h1>preview</h1>"


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "public_base_url": "http://cp:8000",
        "p1_auth_token": OWNER_TOKEN,
        "p1_owner": "alice",
        "opensandbox_base_url": "http://osb",
        "sandbox_image": "img:test",
        "sandbox_start_timeout_seconds": 5,
        "max_active_sessions": 4,
        "workspace_host_root": str(tmp_path / "volumes"),
        "database_url": f"sqlite+aiosqlite:///{tmp_path / 'preview-api.db'}",
        "volume_backend": "host",
        "preview_base_domain": BASE,
        "preview_token_secret": "preview-secret",
        "preview_token_ttl_seconds": 300,
    }
    values.update(overrides)
    return Settings(**values)


def _client(tmp_path: Path, osb: FakeOpenSandbox, **overrides: Any) -> TestClient:
    settings = _settings(tmp_path, **overrides)

    async def factory(resolved: Settings, hub: SessionHub) -> Components:
        return await build_test_components(resolved, hub, osb=osb)

    return TestClient(create_app(settings=settings, components_factory=factory))


def _create_session(client: TestClient) -> tuple[str, str]:
    created = client.post("/api/sessions", headers=HEADERS)
    assert created.status_code == 200
    body = created.json()
    return str(body["session_id"]), str(body["session_token"])


def _mint(client: TestClient, session_id: str, token: str, port: int = 3000) -> dict[str, Any]:
    response = client.post(
        f"/api/sessions/{session_id}/preview",
        params={"token": token},
        json={"port": port},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_host_parsing_and_tokens() -> None:
    assert parse_preview_host(f"s-abc--3000.preview.{BASE}:80", BASE) == ("s-abc", 3000)
    assert parse_preview_host(f"S-ABC--8080.PREVIEW.{BASE}.", BASE) == ("S-ABC".lower(), 8080)
    assert parse_preview_host(f"s-abc.preview.{BASE}", BASE) is None
    assert parse_preview_host(f"s-abc--80.preview.{BASE}", BASE) is None
    assert parse_preview_host("s-abc--3000.preview.other", BASE) is None
    assert parse_preview_host("", BASE) is None

    settings = _settings(Path.cwd())
    token, expires_at = mint_preview_token(settings, "s-1", 3000)
    assert expires_at > int(time.time())
    assert verify_preview_token(settings, token) == ("s-1", 3000)
    assert verify_preview_token(settings, token + "x") is None
    assert verify_preview_token(settings, "garbage") is None
    expired = _settings(Path.cwd(), preview_token_ttl_seconds=-5)
    expired_token, _ = mint_preview_token(expired, "s-1", 3000)
    assert verify_preview_token(expired, expired_token) is None
    assert preview_host("s-1", 3000, BASE) == f"s-1--3000.preview.{BASE}"


def test_mint_preview_url(tmp_path: Path) -> None:
    with _client(tmp_path, FakeOpenSandbox()) as client:
        session_id, token = _create_session(client)
        body = _mint(client, session_id, token)
        assert body["url"] == f"http://{session_id}--3000.preview.{BASE}/"
        assert body["preview_token"]
        assert body["expires_at"] > int(time.time())


def test_preview_disabled_and_bad_requests(tmp_path: Path) -> None:
    with _client(tmp_path, FakeOpenSandbox(), preview_base_domain="") as client:
        session_id, token = _create_session(client)
        response = client.post(
            f"/api/sessions/{session_id}/preview", params={"token": token}, json={"port": 3000}
        )
        assert response.status_code == 503

    with _client(
        tmp_path,
        FakeOpenSandbox(),
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'bad.db'}",
        workspace_host_root=str(tmp_path / "bad-volumes"),
    ) as client:
        session_id, token = _create_session(client)
        assert (
            client.post(
                f"/api/sessions/{session_id}/preview",
                params={"token": token},
                json={"port": 80},
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/preview",
                params={"token": "wrong"},
                json={"port": 3000},
            ).status_code
            == 401
        )


def test_preview_proxies_http_and_sets_cookie(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html",
                "set-cookie": "sid=upstream; Domain=execd.test; Path=/",
                "location": "http://execd.test:3000/login",
            },
            stream=_BodyStream(),
        )

    monkeypatch.setattr(
        "app.api.preview._http_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(upstream)),
    )
    with _client(tmp_path, FakeOpenSandbox()) as client:
        session_id, token = _create_session(client)
        preview_token = _mint(client, session_id, token)["preview_token"]
        host = f"{session_id}--3000.preview.{BASE}"

        response = client.get(
            "/",
            params={"preview_token": preview_token},
            headers={"host": host, "authorization": "Bearer control-plane-secret"},
        )
        assert response.status_code == 200
        assert response.text == "<h1>preview</h1>"
        assert seen[-1].headers["host"] == "execd.test:3000"
        assert seen[-1].headers["accept-encoding"] == "identity"
        assert "authorization" not in seen[-1].headers
        assert "ca_preview" not in seen[-1].headers.get("cookie", "")
        cookies = response.headers.get_list("set-cookie")
        assert any(cookie.startswith(f"{COOKIE_NAME}={preview_token}") for cookie in cookies)
        assert any(
            cookie.startswith("sid=upstream") and "Domain=" not in cookie for cookie in cookies
        )
        assert response.headers["location"] == f"http://{host}/login"

        again = client.get(
            "/assets/app.js",
            params={"v": "1"},
            headers={"host": host, "cookie": f"{COOKIE_NAME}={preview_token}; theme=dark"},
        )
        assert again.status_code == 200
        assert seen[-1].url.path == "/assets/app.js"
        assert seen[-1].url.params["v"] == "1"
        assert seen[-1].headers["cookie"] == "theme=dark"

        # TestClient 的 cookie jar 按 testserver 域名保存；清掉后再验证无票据被拒。
        client.cookies.clear()
        assert client.get("/", headers={"host": host}).status_code == 401
        assert (
            client.get(
                "/",
                params={"preview_token": preview_token},
                headers={"host": f"{session_id}--3001.preview.{BASE}"},
            ).status_code
            == 401
        )
        assert client.get("/", headers={"host": "example.test"}).status_code == 404

        assert client.post(f"/api/sessions/{session_id}/sleep", headers=HEADERS).status_code == 204
        stopped = client.get(
            "/",
            params={"preview_token": preview_token},
            headers={"host": host},
        )
        assert stopped.status_code == 409


def test_preview_websocket_relay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    holder: dict[str, FakeExecWebSocket] = {}
    urls: list[str] = []

    def fake_connect(url: str, **kwargs: Any) -> FakeExecWebSocket:
        urls.append(url)
        holder.setdefault("ws", FakeExecWebSocket())
        return holder["ws"]

    monkeypatch.setattr("websockets.asyncio.client.connect", fake_connect)
    with _client(tmp_path, FakeOpenSandbox()) as client:
        session_id, token = _create_session(client)
        preview_token = _mint(client, session_id, token)["preview_token"]
        host = f"{session_id}--3000.preview.{BASE}"
        with client.websocket_connect(
            f"/hmr?preview_token={preview_token}", headers={"host": host}
        ) as ws:
            exec_ws = holder["ws"]
            _wait_for(lambda: bool(urls))
            ws.send_text("ping")
            _wait_for(lambda: exec_ws.sent == ["ping"])
            exec_ws.push("pong")
            assert ws.receive_text() == "pong"
            exec_ws.push(b"\x00\x01")
            assert ws.receive_bytes() == b"\x00\x01"
            ws.close()
            time.sleep(0.2)

        assert urls == ["ws://execd.test:3000/hmr"]

        with client.websocket_connect("/hmr", headers={"host": host}) as ws:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                ws.receive_text()
        assert excinfo.value.code == 4401
