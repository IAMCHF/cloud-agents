"""沙箱生命周期编排。

启动时序：准入 → 建沙箱（挂会话级卷 + 注入会话 token/控制面地址）→ 等 Running →
沙箱内 entrypoint 起桥接，桥接再拉起 codex → 台账置 running。
销毁：DELETE 沙箱 → 释放准入 → 台帐置 ended。P1 不做空闲销毁与预热池（P3）。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import uuid
from dataclasses import dataclass

from app.bridge.hub import SessionHub
from app.config import Settings
from app.ledger import Ledger
from app.sandbox.admission import AdmissionController
from app.sandbox.client import OpenSandboxClient, OpenSandboxError, SandboxInfo, SandboxSpec

logger = logging.getLogger(__name__)

_WORKSPACE_VOLUME = "workspace"
_CODEX_HOME = "/home/agent/.codex"


@dataclass(frozen=True)
class SessionHandle:
    session_id: str
    session_token: str
    owner: str
    sandbox_id: str


class SandboxManager:
    def __init__(
        self,
        *,
        settings: Settings,
        hub: SessionHub,
        ledger: Ledger,
        client: OpenSandboxClient,
        admission: AdmissionController | None = None,
        detach_settle_seconds: float = 1.0,
    ) -> None:
        self._settings = settings
        self._hub = hub
        self._ledger = ledger
        self._client = client
        self._detach_settle_seconds = detach_settle_seconds
        self._admission = admission or AdmissionController(max_active=settings.max_active_sessions)

    @property
    def admission(self) -> AdmissionController:
        return self._admission

    async def create_session(self, owner: str) -> SessionHandle:
        session_id = f"s-{uuid.uuid4().hex}"
        token = secrets.token_urlsafe(32)

        await self._admission.acquire(session_id, owner)
        self._hub.create(session_id, token, owner)
        sandbox_id: str | None = None
        try:
            created = await self._client.create(self._spec(session_id, token))
            sandbox_id = created.id
            await self._client.wait_until_running(
                created.id, timeout=self._settings.sandbox_start_timeout_seconds
            )
            await self._ledger.create_session(session_id=session_id, owner=owner, token=token)
            await self._ledger.mark_running(session_id, created.id)
        except BaseException:
            if sandbox_id is not None:
                with contextlib.suppress(OpenSandboxError):
                    await self._client.delete(sandbox_id)
            self._hub.remove(session_id)
            await self._admission.release(session_id)
            raise

        self._ledger.submit_event(session_id, "session.created", {"sandbox_id": sandbox_id})
        return SessionHandle(
            session_id=session_id,
            session_token=token,
            owner=owner,
            sandbox_id=sandbox_id,
        )

    async def stop_session(self, session_id: str, *, reason: str = "stopped") -> None:
        record = await self._ledger.get(session_id)
        if record is None:
            raise LookupError(f"会话 {session_id} 不存在")
        if record.sandbox_id is not None:
            with contextlib.suppress(OpenSandboxError):
                await self._client.delete(record.sandbox_id)
        self._hub.remove(session_id)
        await self._admission.release(session_id)
        await self._ledger.mark_ended(session_id, reason)
        self._ledger.submit_event(session_id, "session.stopped", {"reason": reason})

    async def sandbox_status(self, session_id: str) -> SandboxInfo:
        record = await self._ledger.get(session_id)
        if record is None or record.sandbox_id is None:
            raise LookupError(f"会话 {session_id} 没有沙箱")
        return await self._client.get(record.sandbox_id)

    async def resume_session(self, session_id: str) -> SandboxInfo:
        """P1 resume = 重连同一沙箱（空闲销毁与跨沙箱挂卷恢复属 P3）。"""
        info = await self.sandbox_status(session_id)
        if info.state == "Paused":
            await self._client.resume(info.id)
            info = await self._client.wait_until_running(
                info.id, timeout=self._settings.sandbox_start_timeout_seconds
            )
        if not info.running:
            raise OpenSandboxError(f"沙箱不可恢复：{info.state}")
        return info

    async def on_bridge_detached(self, session_id: str) -> None:
        """桥接断开 → 查沙箱状态：仍 Running 视为网络抖动，已退出则结束会话。

        codex 退出会让容器 entrypoint 退出，沙箱转 Terminated；P1 不自动重启，
        恢复路径是重新开会话 + thread/resume（P3 再做跨沙箱恢复）。
        """
        record = await self._ledger.get(session_id)
        if record is None or record.status == "ended" or record.sandbox_id is None:
            return
        await asyncio.sleep(self._detach_settle_seconds)  # 等沙箱状态收敛
        try:
            info = await self._client.get(record.sandbox_id)
        except OpenSandboxError:
            logger.warning("会话 %s 沙箱状态查询失败，按退出处理", session_id)
            info = None
        if info is not None and info.running:
            return
        await self._ledger.mark_ended(session_id, "sandbox_exited")
        await self._admission.release(session_id)
        self._hub.remove(session_id)
        self._ledger.submit_event(
            session_id,
            "session.exited",
            {"sandbox_state": info.state if info is not None else "unknown"},
        )

    def _spec(self, session_id: str, token: str) -> SandboxSpec:
        settings = self._settings
        if settings.volume_backend != "host":
            raise OpenSandboxError("P1 仅验证 host 卷挂载；pvc 字段待 P2 按实际集群复核")
        if not settings.workspace_host_root:
            raise OpenSandboxError("未配置 workspace_host_root，无法挂载用户卷")
        host_path = f"{settings.workspace_host_root.rstrip('/')}/{session_id}"
        return SandboxSpec(
            image=settings.sandbox_image,
            entrypoint=["python", "-m", "app.bridge"],
            env={
                "CONTROL_PLANE_URL": settings.websocket_base_url,
                "SESSION_ID": session_id,
                "SESSION_TOKEN": token,
                "WORKSPACE_DIR": settings.workspace_mount_path,
                "CODEX_HOME": _CODEX_HOME,
                "OPENAI_BASE_URL": settings.llm_public_base_url,
                "OPENAI_API_KEY": token,
            },
            volumes=[
                {
                    "name": _WORKSPACE_VOLUME,
                    "mountPath": settings.workspace_mount_path,
                    "host": {"path": host_path},
                }
            ],
            cpu=settings.sandbox_cpu,
            memory=settings.sandbox_memory,
            timeout_seconds=settings.sandbox_timeout_seconds,
            metadata={"session_id": session_id, "kind": "cloud-agent"},
        )
