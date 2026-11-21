"""卷归档服务：host 后端直接打包；PVC 后端用短生命周期沙箱 + 端口代理传输。"""

from __future__ import annotations

import asyncio
import logging
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import Settings
from app.ledger import Ledger, SessionRecord
from app.sandbox import OpenSandboxClient, OpenSandboxError, SandboxSpec

logger = logging.getLogger(__name__)

_ARCHIVE_PORT = 18081
_WORKSPACE_CLAIM_PREFIX = "ws-"
_STATE_CLAIM_PREFIX = "state-"
_CODEX_HOME = "/home/agent/.codex"
_AGENT_SOURCE = Path(__file__).with_name("agent.py").read_text(encoding="utf-8")


class ArchiveError(RuntimeError):
    """归档/恢复失败。"""


@dataclass(frozen=True)
class ArchivePlan:
    session_id: str
    owner: str
    tenant_id: str
    ended_at: datetime
    workspace: str
    state: str
    target: str
    size_bytes: int | None


@dataclass
class ArchiveReport:
    archived: list[str] = field(default_factory=list)
    dry_run: bool = True
    targets: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


class ArchiveService:
    def __init__(
        self,
        *,
        settings: Settings,
        ledger: Ledger,
        client: OpenSandboxClient,
    ) -> None:
        self._settings = settings
        self._ledger = ledger
        self._client = client

    async def plan(
        self, owner: str, *, now: datetime | None = None, limit: int = 50
    ) -> list[ArchivePlan]:
        if not self._settings.archive_root:
            raise ArchiveError("未配置 ARCHIVE_ROOT")
        current = now or datetime.now(UTC)
        older_than = current - timedelta(days=self._settings.archive_retention_days)
        records = await self._ledger.list_archive_candidates(
            older_than=older_than, owner=owner, limit=limit
        )
        return [self._plan(record) for record in records]

    def _plan(self, record: SessionRecord) -> ArchivePlan:
        target = str(Path(self._settings.archive_root) / record.tenant_id / record.session_id)
        if self._settings.volume_backend == "host":
            root = Path(self._settings.workspace_host_root)
            workspace = str(root / record.session_id)
            state = str(root / f"{record.session_id}.state")
            size_bytes: int | None = _dir_size(Path(workspace)) + _dir_size(Path(state))
        else:
            workspace = f"{_WORKSPACE_CLAIM_PREFIX}{record.session_id}"
            state = f"{_STATE_CLAIM_PREFIX}{record.session_id}"
            size_bytes = None
        return ArchivePlan(
            session_id=record.session_id,
            owner=record.owner,
            tenant_id=record.tenant_id,
            ended_at=record.ended_at or record.created_at,
            workspace=workspace,
            state=state,
            target=target,
            size_bytes=size_bytes,
        )

    async def archive(
        self, plans: list[ArchivePlan], *, dry_run: bool | None = None
    ) -> ArchiveReport:
        if not self._settings.archive_enabled:
            raise ArchiveError("归档未启用（ARCHIVE_ENABLED=false）")
        report = ArchiveReport(
            dry_run=self._settings.archive_dry_run if dry_run is None else dry_run
        )
        for plan in plans:
            report.targets[plan.session_id] = plan.target
            if report.dry_run:
                continue
            try:
                target = Path(plan.target)
                await asyncio.to_thread(target.mkdir, parents=True, exist_ok=True)
                if self._settings.volume_backend == "host":
                    await asyncio.to_thread(
                        _tar_dir, Path(plan.workspace), target / "workspace.tar.gz"
                    )
                    await asyncio.to_thread(_tar_dir, Path(plan.state), target / "state.tar.gz")
                else:
                    await self._archive_pvc(plan)
                await self._ledger.mark_archived(plan.session_id, plan.target)
                self._ledger.submit_event(
                    plan.session_id, "session.archived", {"path": plan.target}
                )
                report.archived.append(plan.session_id)
            except Exception as exc:
                report.errors[plan.session_id] = str(exc)
                logger.exception("归档失败：%s", plan.session_id)
        return report

    async def restore(self, record: SessionRecord, *, force: bool = False) -> str:
        if not self._settings.archive_enabled:
            raise ArchiveError("归档未启用（ARCHIVE_ENABLED=false）")
        if not record.archive_path:
            raise ArchiveError("会话没有归档路径")
        target = Path(record.archive_path)
        if not (target / "workspace.tar.gz").exists():
            raise ArchiveError(f"归档不存在：{target}")
        if self._settings.volume_backend == "host":
            self._restore_host(record, target, force=force)
        else:
            await self._restore_pvc(record, target)
        self._ledger.submit_event(record.session_id, "session.restored", {"path": str(target)})
        return str(target)

    def _restore_host(self, record: SessionRecord, target: Path, *, force: bool) -> None:
        root = Path(self._settings.workspace_host_root)
        workspace = root / record.session_id
        state = root / f"{record.session_id}.state"
        if not force and (
            (workspace.exists() and any(workspace.iterdir()))
            or (state.exists() and any(state.iterdir()))
        ):
            raise ArchiveError("目标卷非空；恢复会覆盖文件，需要 force=true")
        _extract_tar(target / "workspace.tar.gz", workspace)
        _extract_tar(target / "state.tar.gz", state)

    async def _archive_pvc(self, plan: ArchivePlan) -> None:
        spec = self._sandbox_spec(plan.session_id, mode="archive", create_if_missing=False)
        created = None
        try:
            created = await self._client.create(spec)
            await self._client.wait_until_running(
                created.id, timeout=self._settings.sandbox_start_timeout_seconds
            )
            target = Path(plan.target)
            await self._download_with_retry(
                created.id, "workspace.tar.gz", target / "workspace.tar.gz"
            )
            await self._download_with_retry(created.id, "state.tar.gz", target / "state.tar.gz")
        finally:
            if created is not None:
                await self._client.delete(created.id)

    async def _download_with_retry(self, sandbox_id: str, name: str, target: Path) -> None:
        last_error: Exception | None = None
        for _ in range(20):
            try:
                await self._client.proxy_download(sandbox_id, _ARCHIVE_PORT, name, target)
                return
            except OpenSandboxError as exc:
                last_error = exc
                await asyncio.sleep(1)
        raise ArchiveError(f"下载归档 {name} 失败：{last_error}")

    async def _restore_pvc(self, record: SessionRecord, target: Path) -> None:
        spec = self._sandbox_spec(record.session_id, mode="restore", create_if_missing=True)
        created = None
        try:
            created = await self._client.create(spec)
            await self._client.wait_until_running(
                created.id, timeout=self._settings.sandbox_start_timeout_seconds
            )
            await self._upload_with_retry(
                created.id, "workspace.tar.gz", target / "workspace.tar.gz"
            )
            await self._upload_with_retry(created.id, "state.tar.gz", target / "state.tar.gz")
            await self._wait_restore(created.id)
        finally:
            if created is not None:
                await self._client.delete(created.id)

    async def _upload_with_retry(self, sandbox_id: str, name: str, source: Path) -> None:
        last_error: Exception | None = None
        for _ in range(20):
            try:
                await self._client.proxy_upload(sandbox_id, _ARCHIVE_PORT, name, source)
                return
            except OpenSandboxError as exc:
                last_error = exc
                await asyncio.sleep(1)
        raise ArchiveError(f"上传归档 {name} 失败：{last_error}")

    async def _wait_restore(self, sandbox_id: str) -> None:
        for _ in range(int(self._settings.archive_timeout_seconds)):
            try:
                status = (
                    await self._client.proxy_get_text(sandbox_id, _ARCHIVE_PORT, "status")
                ).strip()
            except OpenSandboxError:
                await asyncio.sleep(1)
                continue
            if status == "done":
                return
            if status == "error":
                raise ArchiveError("恢复沙箱解压失败")
            await asyncio.sleep(1)
        raise ArchiveError("恢复沙箱超时")

    def _sandbox_spec(self, session_id: str, *, mode: str, create_if_missing: bool) -> SandboxSpec:
        volumes: list[dict[str, Any]] = [
            {
                "name": "workspace",
                "mountPath": "/workspace",
                "pvc": {
                    "claimName": f"{_WORKSPACE_CLAIM_PREFIX}{session_id}",
                    "createIfNotExists": create_if_missing,
                    "deleteOnSandboxTermination": False,
                },
            },
            {
                "name": "codex-state",
                "mountPath": _CODEX_HOME,
                "pvc": {
                    "claimName": f"{_STATE_CLAIM_PREFIX}{session_id}",
                    "createIfNotExists": create_if_missing,
                    "deleteOnSandboxTermination": False,
                },
            },
        ]
        return SandboxSpec(
            image=self._settings.sandbox_image,
            entrypoint=["python", "-c", _AGENT_SOURCE],
            env={"ARCHIVE_MODE": mode, "ARCHIVE_PORT": str(_ARCHIVE_PORT)},
            cpu=self._settings.archive_cpu,
            memory=self._settings.archive_memory,
            timeout_seconds=int(self._settings.archive_timeout_seconds),
            metadata={"purpose": "archive"},
            volumes=volumes,
            network_policy={"defaultAction": "deny", "egress": []},
        )


def _tar_dir(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=target.parent, suffix=".tmp") as handle:
        temporary = Path(handle.name)
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            if source.exists():
                archive.add(source, arcname=".")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def _extract_tar(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with tarfile.open(source, "r:gz") as archive:
        for member in archive.getmembers():
            target = (base / member.name).resolve()
            if target != base and base not in target.parents:
                raise ArchiveError(f"归档包含不安全路径：{member.name}")
        archive.extractall(base, filter="data")


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
