"""卷归档 host 后端 round-trip 测试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.archive import ArchiveError, ArchiveService
from app.archive import agent as archive_agent
from app.config import Settings
from app.ledger import Ledger
from app.sandbox import OpenSandboxClient
from tests.fakes.opensandbox import FakeOpenSandbox


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, Any] = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path / 'archive.db'}",
        "public_base_url": "http://127.0.0.1:1",
        "volume_backend": "host",
        "workspace_host_root": str(tmp_path / "ws"),
        "archive_enabled": True,
        "archive_root": str(tmp_path / "archive"),
        "archive_dry_run": False,
        "archive_retention_days": 0,
    }
    values.update(overrides)
    return Settings(**values)


async def test_host_archive_and_restore_round_trip(ledger: Ledger, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    await ledger.admit_session(
        session_id="s-archive",
        owner="alice",
        token="tok",
        tenant_id="default",
        max_active_sessions=10,
    )
    await ledger.mark_ended("s-archive", "test")

    workspace = tmp_path / "ws" / "s-archive"
    state = tmp_path / "ws" / "s-archive.state"
    workspace.mkdir(parents=True)
    state.mkdir(parents=True)
    (workspace / "hello.txt").write_text("hello", encoding="utf-8")
    (state / "state.txt").write_text("state", encoding="utf-8")

    service = ArchiveService(
        settings=settings,
        ledger=ledger,
        client=OpenSandboxClient(base_url="http://osb", transport=FakeOpenSandbox().transport()),
    )

    plans = await service.plan("alice")
    assert [plan.session_id for plan in plans] == ["s-archive"]
    assert plans[0].size_bytes == 10

    report = await service.archive(plans, dry_run=False)
    assert report.archived == ["s-archive"]
    target = Path(plans[0].target)
    assert (target / "workspace.tar.gz").exists()
    assert (target / "state.tar.gz").exists()

    record = await ledger.get("s-archive")
    assert record is not None and record.archived_at is not None
    assert record.archive_path == str(target)
    assert await service.plan("alice") == []

    (workspace / "hello.txt").write_text("broken", encoding="utf-8")
    (state / "state.txt").unlink()

    await service.restore(record, force=True)

    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert (state / "state.txt").read_text(encoding="utf-8") == "state"


async def test_archive_requires_root_and_enabled(ledger: Ledger, tmp_path: Path) -> None:
    no_root = _settings(tmp_path, archive_enabled=False, archive_root="")
    service = ArchiveService(
        settings=no_root,
        ledger=ledger,
        client=OpenSandboxClient(base_url="http://osb", transport=FakeOpenSandbox().transport()),
    )
    with pytest.raises(ArchiveError, match="ARCHIVE_ROOT"):
        await service.plan("alice")

    disabled = _settings(tmp_path, archive_enabled=False)
    service = ArchiveService(
        settings=disabled,
        ledger=ledger,
        client=OpenSandboxClient(base_url="http://osb", transport=FakeOpenSandbox().transport()),
    )
    with pytest.raises(ArchiveError, match="ARCHIVE_ENABLED"):
        await service.archive([], dry_run=False)


async def test_plan_can_be_dry_run(ledger: Ledger, tmp_path: Path) -> None:
    settings = _settings(tmp_path, archive_dry_run=True)
    await ledger.admit_session(
        session_id="s-dry",
        owner="alice",
        token="tok",
        tenant_id="default",
        max_active_sessions=10,
    )
    await ledger.mark_ended("s-dry", "test")
    service = ArchiveService(
        settings=settings,
        ledger=ledger,
        client=OpenSandboxClient(base_url="http://osb", transport=FakeOpenSandbox().transport()),
    )

    plans = await service.plan("alice")
    report = await service.archive(plans)

    assert report.dry_run is True
    assert report.archived == []
    assert report.targets["s-dry"].endswith("s-dry")
    record = await ledger.get("s-dry")
    assert record is not None and record.archived_at is None


def test_agent_tar_and_extract_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(archive_agent, "OUT", tmp_path / "out")
    workspace = tmp_path / "workspace"
    state = tmp_path / "state"
    workspace.mkdir()
    state.mkdir()
    (workspace / "hello.txt").write_text("hello", encoding="utf-8")
    (state / "state.txt").write_text("state", encoding="utf-8")

    archive_agent._tar("workspace.tar.gz", workspace)
    archive_agent._tar("state.tar.gz", state)
    (workspace / "hello.txt").unlink()
    archive_agent._extract("workspace.tar.gz", workspace)

    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"


async def test_pvc_plan_and_sandbox_spec(ledger: Ledger, tmp_path: Path) -> None:
    settings = _settings(tmp_path, volume_backend="pvc", sandbox_runtime="kubernetes")
    await ledger.admit_session(
        session_id="s-pvc",
        owner="alice",
        token="tok",
        tenant_id="default",
        max_active_sessions=10,
    )
    await ledger.mark_ended("s-pvc", "test")
    service = ArchiveService(
        settings=settings,
        ledger=ledger,
        client=OpenSandboxClient(base_url="http://osb", transport=FakeOpenSandbox().transport()),
    )

    plans = await service.plan("alice")

    assert [plan.session_id for plan in plans] == ["s-pvc"]
    assert plans[0].workspace == "ws-s-pvc"
    assert plans[0].state == "state-s-pvc"
    assert plans[0].size_bytes is None

    spec = service._sandbox_spec("s-pvc", mode="archive", create_if_missing=False)
    assert spec.volumes[0]["pvc"]["claimName"] == "ws-s-pvc"
    assert spec.volumes[1]["pvc"]["claimName"] == "state-s-pvc"
    assert spec.volumes[1]["mountPath"] == "/home/agent/.codex"
    assert spec.network_policy == {"defaultAction": "deny", "egress": []}
    assert spec.entrypoint[:2] == ["python", "-c"]
