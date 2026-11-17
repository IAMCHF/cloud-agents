"""OpenSandbox 生命周期 API 的最小异步客户端（REST，httpx）。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_STATE_RUNNING = "Running"


class OpenSandboxError(RuntimeError):
    """OpenSandbox 返回错误或能力不符。"""


@dataclass(frozen=True)
class SandboxSpec:
    image: str
    entrypoint: list[str]
    env: dict[str, str]
    cpu: str
    memory: str
    timeout_seconds: int
    metadata: dict[str, str] = field(default_factory=dict)
    volumes: list[dict[str, Any]] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "image": {"uri": self.image},
            "entrypoint": self.entrypoint,
            "env": self.env,
            "metadata": self.metadata,
            "timeout": self.timeout_seconds,
            "resourceLimits": {"cpu": self.cpu, "memory": self.memory},
        }
        if self.volumes:
            payload["volumes"] = self.volumes
        return payload


@dataclass(frozen=True)
class SandboxInfo:
    id: str
    state: str
    metadata: dict[str, str]

    @property
    def running(self) -> bool:
        return self.state == _STATE_RUNNING


class OpenSandboxClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"OPEN-SANDBOX-API-KEY": api_key} if api_key else {}
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def create(self, spec: SandboxSpec) -> SandboxInfo:
        response = await self._client.post("/v1/sandboxes", json=spec.to_payload())
        return _sandbox_info(_expect(response, {200, 201, 202}))

    async def get(self, sandbox_id: str) -> SandboxInfo:
        response = await self._client.get(f"/v1/sandboxes/{sandbox_id}")
        return _sandbox_info(_expect(response, {200}))

    async def delete(self, sandbox_id: str) -> None:
        response = await self._client.delete(f"/v1/sandboxes/{sandbox_id}")
        if response.status_code not in {200, 202, 204, 404}:
            raise OpenSandboxError(
                f"删除沙箱失败 HTTP {response.status_code}: {response.text[:200]}"
            )

    async def pause(self, sandbox_id: str) -> None:
        response = await self._client.post(f"/v1/sandboxes/{sandbox_id}/pause")
        _expect(response, {200, 202})

    async def resume(self, sandbox_id: str) -> None:
        response = await self._client.post(f"/v1/sandboxes/{sandbox_id}/resume")
        _expect(response, {200, 202})

    async def wait_until_running(
        self,
        sandbox_id: str,
        *,
        timeout: float = 90.0,
        interval: float = 0.5,
    ) -> SandboxInfo:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            info = await self.get(sandbox_id)
            if info.running:
                return info
            if info.state in {"Failed", "Terminated", "Stopping"}:
                raise OpenSandboxError(f"沙箱进入终止态：{info.state}")
            if loop.time() > deadline:
                raise OpenSandboxError(f"沙箱启动超时（最后状态 {info.state}）")
            await asyncio.sleep(interval)


def _expect(response: httpx.Response, allowed: set[int]) -> dict[str, Any]:
    if response.status_code not in allowed:
        raise OpenSandboxError(f"OpenSandbox HTTP {response.status_code}: {response.text[:200]}")
    if response.status_code == 204 or not response.content:
        return {}
    payload: Any = response.json()
    if not isinstance(payload, dict):
        raise OpenSandboxError("OpenSandbox 响应不是 JSON 对象")
    return payload


def _sandbox_info(payload: dict[str, Any]) -> SandboxInfo:
    sandbox_id = payload.get("id")
    status = payload.get("status")
    state = status.get("state") if isinstance(status, dict) else None
    metadata = payload.get("metadata")
    if not isinstance(sandbox_id, str) or not isinstance(state, str):
        raise OpenSandboxError(f"OpenSandbox 响应缺少 id/state: {payload}")
    return SandboxInfo(
        id=sandbox_id,
        state=state,
        metadata=metadata if isinstance(metadata, dict) else {},
    )
