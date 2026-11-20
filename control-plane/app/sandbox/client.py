"""OpenSandbox 生命周期 API 的最小异步客户端（REST，httpx）。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_STATE_RUNNING = "Running"


class OpenSandboxError(RuntimeError):
    """OpenSandbox 返回错误或能力不符。"""


class SandboxNotFoundError(OpenSandboxError):
    """沙箱不存在（已被运行时回收）。"""


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
    network_policy: dict[str, Any] | None = None

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
        if self.network_policy is not None:
            payload["networkPolicy"] = self.network_policy
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
        execd_token: str = "",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
        execd_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {"OPEN-SANDBOX-API-KEY": api_key} if api_key else {}
        self._execd_token = execd_token
        self._execd_transport = execd_transport
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
        if response.status_code == 404:
            raise SandboxNotFoundError(f"沙箱 {sandbox_id} 不存在")
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

    async def proxy_download(self, sandbox_id: str, port: int, path: str, target: Path) -> int:
        """通过 OpenSandbox 端口代理下载沙箱内文件（归档用）。"""
        url = f"/v1/sandboxes/{sandbox_id}/proxy/{port}/{path.lstrip('/')}"
        async with self._client.stream("GET", url, timeout=None) as response:
            if response.status_code != 200:
                body = await response.aread()
                raise OpenSandboxError(f"代理下载失败 HTTP {response.status_code}: {body[:200]!r}")
            total = 0
            with target.open("wb") as handle:
                async for chunk in response.aiter_bytes():
                    handle.write(chunk)
                    total += len(chunk)
            return total

    async def proxy_upload(self, sandbox_id: str, port: int, path: str, source: Path) -> None:
        """通过 OpenSandbox 端口代理上传文件（恢复用）。"""
        url = f"/v1/sandboxes/{sandbox_id}/proxy/{port}/{path.lstrip('/')}"

        async def body() -> Any:
            with source.open("rb") as handle:
                while chunk := handle.read(1 << 20):
                    yield chunk

        response = await self._client.put(url, content=body(), timeout=None)
        if response.status_code not in {200, 201, 204}:
            raise OpenSandboxError(
                f"代理上传失败 HTTP {response.status_code}: {response.text[:200]}"
            )

    async def proxy_get_text(self, sandbox_id: str, port: int, path: str) -> str:
        url = f"/v1/sandboxes/{sandbox_id}/proxy/{port}/{path.lstrip('/')}"
        response = await self._client.get(url, timeout=None)
        if response.status_code != 200:
            raise OpenSandboxError(
                f"代理请求失败 HTTP {response.status_code}: {response.text[:200]}"
            )
        return response.text

    async def endpoint(self, sandbox_id: str, port: int) -> str:
        response = await self._client.get(f"/v1/sandboxes/{sandbox_id}/endpoints/{port}")
        payload = _expect(response, {200})
        endpoint = payload.get("endpoint")
        if not isinstance(endpoint, str) or endpoint == "":
            raise OpenSandboxError("OpenSandbox endpoint 响应缺少 endpoint")
        return endpoint

    async def _execd_request(
        self,
        sandbox_id: str,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> httpx.Response:
        endpoint = await self.endpoint(sandbox_id, 44772)
        base_url = (
            endpoint if endpoint.startswith(("http://", "https://")) else f"http://{endpoint}"
        )
        headers = {"X-EXECD-ACCESS-TOKEN": self._execd_token} if self._execd_token else {}
        async with httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=self._execd_transport,
        ) as client:
            return await client.request(method, path, params=params, json=json_body)

    async def execd_list_directory(self, sandbox_id: str, path: str) -> list[dict[str, Any]]:
        response = await self._execd_request(
            sandbox_id, "GET", "/directories/list", params={"path": path}
        )
        if response.status_code != 200:
            raise OpenSandboxError(f"列目录失败 HTTP {response.status_code}: {response.text[:200]}")
        payload: Any = response.json()
        if not isinstance(payload, list):
            raise OpenSandboxError("列目录响应不是数组")
        return [item for item in payload if isinstance(item, dict)]

    async def execd_read_file(
        self, sandbox_id: str, path: str, *, max_bytes: int = 512 * 1024
    ) -> bytes:
        response = await self._execd_request(
            sandbox_id, "GET", "/files/download", params={"path": path}, timeout=60.0
        )
        if response.status_code != 200:
            raise OpenSandboxError(
                f"读取文件失败 HTTP {response.status_code}: {response.text[:200]}"
            )
        content = response.content
        if len(content) > max_bytes:
            raise OpenSandboxError(f"文件超过预览上限 {max_bytes} 字节")
        return content

    async def execd_create_pty(self, sandbox_id: str) -> str:
        response = await self._execd_request(sandbox_id, "POST", "/pty", json_body={})
        if response.status_code not in {200, 201}:
            raise OpenSandboxError(
                f"创建终端失败 HTTP {response.status_code}: {response.text[:200]}"
            )
        payload: Any = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("session_id"), str):
            raise OpenSandboxError("终端创建响应缺少 session_id")
        return str(payload["session_id"])

    async def execd_delete_pty(self, sandbox_id: str, pty_id: str) -> None:
        with contextlib.suppress(OpenSandboxError):
            await self._execd_request(sandbox_id, "DELETE", f"/pty/{pty_id}")

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
