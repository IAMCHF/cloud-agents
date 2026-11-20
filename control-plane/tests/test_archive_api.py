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
HEADERS = {"Authorization": f"Bearer {OWNER_TOKEN}"}


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
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'archive-api.db'}",
        volume_backend="host",
        archive_enabled=True,
        archive_root=str(tmp_path / "archive"),
        archive_retention_days=0,
        archive_dry_run=True,
    )


def _client(tmp_path: Path, osb: FakeOpenSandbox) -> TestClient:
    settings = _settings(tmp_path)

    async def factory(resolved: Settings, hub: SessionHub) -> Components:
        return await build_test_components(resolved, hub, osb=osb)

    return TestClient(create_app(settings=settings, components_factory=factory))


def _create_ended_session(client: TestClient, tmp_path: Path) -> str:
    created = client.post("/api/sessions", headers=HEADERS)
    assert created.status_code == 200
    session_id = str(created.json()["session_id"])
    workspace = tmp_path / "volumes" / session_id
    state = tmp_path / "volumes" / f"{session_id}.state"
    workspace.mkdir(parents=True)
    state.mkdir(parents=True)
    (workspace / "hello.txt").write_text("hello", encoding="utf-8")
    (state / "state.txt").write_text("state", encoding="utf-8")
    assert client.delete(f"/api/sessions/{session_id}", headers=HEADERS).status_code == 204
    return session_id


def test_archive_requires_auth(tmp_path: Path) -> None:
    with _client(tmp_path, FakeOpenSandbox()) as client:
        assert client.get("/api/archive/plan").status_code == 401


def test_archive_plan_run_and_restore(tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    with _client(tmp_path, osb) as client:
        session_id = _create_ended_session(client, tmp_path)

        plan = client.get("/api/archive/plan", headers=HEADERS)
        assert plan.status_code == 200
        body = plan.json()
        assert body["dry_run"] is True
        assert [item["session_id"] for item in body["plans"]] == [session_id]
        assert body["plans"][0]["size_bytes"] == 10

        dry = client.post("/api/archive/run", headers=HEADERS, json={"dry_run": True})
        assert dry.status_code == 200
        assert dry.json()["dry_run"] is True
        assert dry.json()["archived"] == []

        run = client.post(
            "/api/archive/run",
            headers=HEADERS,
            json={"session_ids": [session_id], "dry_run": False},
        )
        assert run.status_code == 200
        assert run.json()["archived"] == [session_id]
        target = Path(run.json()["targets"][session_id])
        assert (target / "workspace.tar.gz").exists()
        assert (target / "state.tar.gz").exists()

        workspace = tmp_path / "volumes" / session_id
        (workspace / "hello.txt").write_text("broken", encoding="utf-8")
        restored = client.post(f"/api/archive/{session_id}/restore?force=true", headers=HEADERS)
        assert restored.status_code == 200
        assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"

        # 已归档会话不再出现在计划中。
        assert client.get("/api/archive/plan", headers=HEADERS).json()["plans"] == []


def test_restore_rejects_running_session(tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    with _client(tmp_path, osb) as client:
        created = client.post("/api/sessions", headers=HEADERS)
        session_id = str(created.json()["session_id"])
        response = client.post(f"/api/archive/{session_id}/restore", headers=HEADERS)
        assert response.status_code == 409
