from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.bootstrap import Components
from app.bridge.hub import SessionHub
from app.config import Settings
from app.main import create_app
from tests.fakes.components import build_test_components
from tests.fakes.opensandbox import FakeOpenSandbox

OWNER_TOKEN = "owner-token"


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
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'sessions.db'}",
    )


def _client(tmp_path: Path, osb: FakeOpenSandbox) -> TestClient:
    settings = _settings(tmp_path)

    async def factory(resolved: Settings, hub: SessionHub) -> Components:
        return await build_test_components(resolved, hub, osb=osb)

    return TestClient(create_app(settings=settings, components_factory=factory))


def test_requires_owner_token(tmp_path: Path) -> None:
    with _client(tmp_path, FakeOpenSandbox()) as client:
        assert client.post("/api/sessions").status_code == 401


def test_create_get_and_delete_session(tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    headers = {"Authorization": f"Bearer {OWNER_TOKEN}"}
    with _client(tmp_path, osb) as client:
        created = client.post("/api/sessions", headers=headers)
        assert created.status_code == 200
        body = created.json()
        assert body["sandbox_id"] == "sb-1"
        assert body["ws_url"].startswith("ws://cp:8000/ws/session/")
        session_id = body["session_id"]

        status = client.get(f"/api/sessions/{session_id}", headers=headers)
        assert status.status_code == 200
        assert status.json()["status"] == "running"
        assert status.json()["sandbox_state"] == "Running"

        # P1 同用户单活跃：第二个会话被拒。
        second = client.post("/api/sessions", headers=headers)
        assert second.status_code == 429

        assert client.delete(f"/api/sessions/{session_id}", headers=headers).status_code == 204
        ended = client.get(f"/api/sessions/{session_id}", headers=headers)
        assert ended.json()["status"] == "ended"
        assert osb.deleted == ["sb-1"]


def test_unknown_session_returns_404(tmp_path: Path) -> None:
    headers = {"Authorization": f"Bearer {OWNER_TOKEN}"}
    with _client(tmp_path, FakeOpenSandbox()) as client:
        assert client.get("/api/sessions/missing", headers=headers).status_code == 404
        assert client.delete("/api/sessions/missing", headers=headers).status_code == 404
