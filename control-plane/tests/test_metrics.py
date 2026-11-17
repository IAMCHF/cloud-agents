from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.bootstrap import Components
from app.bridge.hub import SessionHub
from app.config import Settings
from app.main import create_app
from tests.fakes.components import build_test_components
from tests.fakes.opensandbox import FakeOpenSandbox

OWNER_TOKEN = "owner-token"


class _EmptyStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"{}"


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
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'metrics.db'}",
        llm_upstream_base_url="http://upstream/v1",
        llm_api_key="real-key",
        cors_allow_origins="http://example.test",
    )


def test_metrics_and_cors(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    async def factory(resolved: Settings, hub: SessionHub) -> Components:
        return await build_test_components(
            resolved,
            hub,
            osb=FakeOpenSandbox(),
            llm_transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=_EmptyStream())),
        )

    headers = {"Authorization": f"Bearer {OWNER_TOKEN}"}
    with TestClient(create_app(settings=settings, components_factory=factory)) as client:
        created = client.post("/api/sessions", headers=headers).json()
        session_token = str(created["session_token"])

        # 第二个会话被准入拒绝，计入拒绝计数。
        assert client.post("/api/sessions", headers=headers).status_code == 429
        # 一次 LLM 转发，计入网关计数。
        forwarded = client.post(
            "/llm/v1/chat/completions",
            headers={"Authorization": f"Bearer {session_token}"},
            json={"model": "m"},
        )
        assert forwarded.status_code == 200

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        body = metrics.text
        assert "cloud_agents_active_sessions 1.0" in body
        assert "cloud_agents_admission_rejections_total{" in body
        assert "cloud_agents_llm_requests_total 1.0" in body

        preflight = client.options(
            "/healthz",
            headers={"Origin": "http://example.test", "Access-Control-Request-Method": "GET"},
        )
        assert preflight.headers["access-control-allow-origin"] == "http://example.test"
