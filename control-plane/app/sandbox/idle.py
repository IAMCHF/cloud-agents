"""空闲会话 sweeper：审批超时自动拒绝 + 无客户端/无进行中 turn 的会话销毁沙箱。"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from app.bridge.hub import SessionHub
from app.config import Settings
from app.ledger import SessionStateError
from app.metrics import Metrics
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)


class IdleSweeper:
    """周期性清理：先处理无人响应的审批，再把真正空闲的会话转入 idle。"""

    def __init__(
        self,
        *,
        hub: SessionHub,
        manager: SandboxManager,
        settings: Settings,
        metrics: Metrics | None = None,
    ) -> None:
        self._hub = hub
        self._manager = manager
        self._settings = settings
        self._metrics = metrics
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if not self._settings.idle_sweeper_enabled or self._task is not None:
            return
        self._task = asyncio.create_task(self._loop(), name="idle-sweeper")

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._settings.idle_sweep_interval_seconds)
            try:
                await self.sweep_once()
            except Exception:
                logger.exception("空闲 sweeper 执行失败")

    async def sweep_once(self) -> int:
        for channel in self._hub.channels():
            declined = await self._hub.expire_pending(
                channel, older_than=self._settings.approval_timeout_seconds
            )
            if declined:
                if self._metrics is not None:
                    self._metrics.observe_approval_timeout(declined)
                logger.info("会话 %s 审批超时自动拒绝 %s 个", channel.session_id, declined)

        slept = 0
        for channel in self._hub.idle_candidates(timeout=self._settings.idle_timeout_seconds):
            try:
                changed = await self._manager.sleep_session(channel.session_id, reason="idle")
            except SessionStateError:
                continue
            except Exception:
                logger.exception("空闲销毁失败：%s", channel.session_id)
                continue
            if changed:
                slept += 1
                if self._metrics is not None:
                    self._metrics.observe_idle_slept("idle")
        return slept
