from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.bootstrap import Components
from app.bridge.hub import SessionHub
from app.config import Settings
from app.main import create_app
from tests.fakes.components import build_test_components


class _SseStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'data: {"delta":"hi"}\n\n'


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        public_base_url="http://cp:8000",
        opensandbox_base_url="http://osb",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'gateway.db'}",
        llm_upstream_base_url="http://upstream/v1",
        llm_api_key="real-key",
    )


def test_forwards_with_session_token_and_injects_real_key(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    hub = SessionHub()
    hub.create("s1", "session-token", "alice")
    captured: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_SseStream(),
        )

    async def factory(resolved: Settings, resolved_hub: SessionHub) -> Components:
        return await build_test_components(
            resolved, resolved_hub, llm_transport=httpx.MockTransport(upstream)
        )

    app = create_app(settings=settings, hub=hub, components_factory=factory)
    with TestClient(app) as client:
        response = client.post(
            "/llm/v1/chat/completions",
            headers={"Authorization": "Bearer session-token"},
            json={"model": "m", "stream": True},
            params={"trace": "1"},
        )
        assert response.status_code == 200
        assert response.text == 'data: {"delta":"hi"}\n\n'
        assert response.headers["content-type"].startswith("text/event-stream")

        rejected = client.post(
            "/llm/v1/chat/completions",
            headers={"Authorization": "Bearer wrong-token"},
            json={"model": "m"},
        )
        assert rejected.status_code == 401

    assert len(captured) == 1
    forwarded = captured[0]
    assert str(forwarded.url) == "http://upstream/v1/chat/completions?trace=1"
    assert forwarded.headers["authorization"] == "Bearer real-key"
    assert json.loads(forwarded.content) == {"model": "m", "stream": True}


def test_decompresses_gzip_upstream_stream(tmp_path: Path) -> None:
    import gzip

    settings = _settings(tmp_path)
    hub = SessionHub()
    hub.create("s1", "session-token", "alice")
    payload = b'data: {"delta":"hi"}\n\n'

    def upstream(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream", "content-encoding": "gzip"},
            content=gzip.compress(payload),
        )

    async def factory(resolved: Settings, resolved_hub: SessionHub) -> Components:
        return await build_test_components(
            resolved, resolved_hub, llm_transport=httpx.MockTransport(upstream)
        )

    app = create_app(settings=settings, hub=hub, components_factory=factory)
    with TestClient(app) as client:
        response = client.post(
            "/llm/v1/responses",
            headers={"Authorization": "Bearer session-token"},
            json={"model": "m", "stream": True},
        )
    assert response.status_code == 200
    assert response.content == payload
