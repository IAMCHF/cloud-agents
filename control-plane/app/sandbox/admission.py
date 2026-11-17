"""并发准入：全局活跃上限 + 同用户单活跃（P1 无租户配额时的兜底）。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


class AdmissionRejectedError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class AdmissionStatus:
    active: int
    max_active: int


class AdmissionController:
    """进程内准入；P1 单 uvicorn worker，因此与进程同生命周期即可。"""

    def __init__(self, *, max_active: int, single_active_per_owner: bool = True) -> None:
        if max_active < 1:
            raise ValueError("max_active 必须 >= 1")
        self._max_active = max_active
        self._single_active_per_owner = single_active_per_owner
        self._active: dict[str, str] = {}  # session_id -> owner
        self._lock = asyncio.Lock()

    @property
    def status(self) -> AdmissionStatus:
        return AdmissionStatus(active=len(self._active), max_active=self._max_active)

    def active_session_of(self, owner: str) -> str | None:
        for session_id, session_owner in self._active.items():
            if session_owner == owner:
                return session_id
        return None

    async def acquire(self, session_id: str, owner: str) -> None:
        async with self._lock:
            if session_id in self._active:
                return
            if len(self._active) >= self._max_active:
                raise AdmissionRejectedError("达到全局活跃会话上限（max_active_sessions）")
            if self._single_active_per_owner:
                current = self.active_session_of(owner)
                if current is not None:
                    raise AdmissionRejectedError(f"同用户已有活跃会话 {current}")
            self._active[session_id] = owner

    async def release(self, session_id: str) -> None:
        async with self._lock:
            self._active.pop(session_id, None)
