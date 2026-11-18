from __future__ import annotations

import gzip
import json
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.bootstrap import Components
from app.bridge.hub import SessionHub
from app.config import Settings
from app.main import create_app
from tests.fakes.components import build_test_components

SESSION_TOKEN = "session-token"


class _SseStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self._chunks = chunks if chunks is not None else [b'data: {"delta":"hi"}\n\n']

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        public_base_url="http://cp:8000",
        opensandbox_base_url="http://osb",
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'gateway.db'}",
        llm_upstream_base_url="http://upstream/v1",
        llm_api_key="real-key",
    )


def _build_app(
    tmp_path: Path,
    upstream: Callable[[httpx.Request], httpx.Response],
    *,
    budget: int = 0,
    used: int = 0,
) -> FastAPI:
    settings = _settings(tmp_path)
    hub = SessionHub()

    async def factory(resolved: Settings, resolved_hub: SessionHub) -> Components:
        components = await build_test_components(
            resolved, resolved_hub, llm_transport=httpx.MockTransport(upstream)
        )
        await components.ledger.ensure_tenant(
            "default", max_active_sessions=10, monthly_token_budget=budget
        )
        await components.ledger.admit_session(
            session_id="s1",
            owner="alice",
            token=SESSION_TOKEN,
            tenant_id="default",
            max_active_sessions=100,
        )
        if used:
            await components.ledger.record_usage(
                session_id="s1",
                tenant_id="default",
                model="m",
                input_tokens=used,
                output_tokens=0,
            )
        return components

    return create_app(settings=settings, hub=hub, components_factory=factory)


def test_forwards_with_session_token_and_injects_real_key(tmp_path: Path) -> None:
    captured: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=_SseStream(),
        )

    app = _build_app(tmp_path, upstream)
    with TestClient(app) as client:
        response = client.post(
            "/llm/v1/chat/completions",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
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
    payload = b'data: {"delta":"hi"}\n\n'

    def upstream(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream", "content-encoding": "gzip"},
            content=gzip.compress(payload),
        )

    app = _build_app(tmp_path, upstream)
    with TestClient(app) as client:
        response = client.post(
            "/llm/v1/responses",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json={"model": "m", "stream": True},
        )
    assert response.status_code == 200
    assert response.content == payload


def test_meters_responses_usage_and_enforces_tenant_budget(tmp_path: Path) -> None:
    captured: list[httpx.Request] = []
    body = (
        b'data: {"type":"response.created","response":{"id":"r1"}}\n\n'
        b"event: response.completed\n"
        b'data: {"type":"response.completed","response":{"id":"r1",'
        b'"usage":{"input_tokens":12,"output_tokens":7,"total_tokens":19}}}\n\n'
        b"data: [DONE]\n\n"
    )

    def upstream(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    # 预算 = 本次用量（12+7）：第一次放行并计量，第二次即被预算拒绝。
    app = _build_app(tmp_path, upstream, budget=19)
    with TestClient(app) as client:
        first = client.post(
            "/llm/v1/responses",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json={"model": "gpt-test", "stream": True},
        )
        assert first.status_code == 200
        assert first.content == body

        metrics = app.state.metrics.render().decode()
        assert 'cloud_agents_llm_tokens_total{direction="input",tenant="default"} 12.0' in metrics
        assert 'cloud_agents_llm_tokens_total{direction="output",tenant="default"} 7.0' in metrics

        second = client.post(
            "/llm/v1/responses",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json={"model": "gpt-test", "stream": True},
        )
        assert second.status_code == 429
        assert 'cloud_agents_llm_budget_rejections_total{tenant="default"} 1.0' in (
            app.state.metrics.render().decode()
        )

    assert len(captured) == 1


def test_meters_chat_completions_usage_from_json(tmp_path: Path) -> None:
    def upstream(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"choices": [], "usage": {"prompt_tokens": 3, "completion_tokens": 4}},
        )

    app = _build_app(tmp_path, upstream, budget=7)
    with TestClient(app) as client:
        response = client.post(
            "/llm/v1/chat/completions",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json={"model": "m"},
        )
        assert response.status_code == 200

        rejected = client.post(
            "/llm/v1/chat/completions",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json={"model": "m"},
        )
        assert rejected.status_code == 429

    metrics: Any = app.state.metrics.render().decode()
    assert 'cloud_agents_llm_tokens_total{direction="input",tenant="default"} 3.0' in metrics
    assert 'cloud_agents_llm_tokens_total{direction="output",tenant="default"} 4.0' in metrics


def test_rejects_when_monthly_usage_already_at_budget(tmp_path: Path) -> None:
    captured: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, headers={"content-type": "application/json"}, json={})

    app = _build_app(tmp_path, upstream, budget=10, used=10)
    with TestClient(app) as client:
        response = client.post(
            "/llm/v1/chat/completions",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
            json={"model": "m"},
        )
    assert response.status_code == 429
    assert captured == []
