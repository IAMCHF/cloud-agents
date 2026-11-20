"""OpenSandbox 服务端替身：记录请求，按可配置状态应答。"""

from __future__ import annotations

import json
from typing import Any

import httpx


class FakeOpenSandbox:
    def __init__(
        self,
        *,
        state: str = "Running",
        sandbox_id: str = "sb-1",
        endpoint_host: str = "execd.test",
    ) -> None:
        self.state = state
        self.sandbox_id = sandbox_id
        self.endpoint_host = endpoint_host
        self.created: list[dict[str, Any]] = []
        self.deleted: list[str] = []
        self.resumed: list[str] = []

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path == "/v1/sandboxes":
            self.created.append(json.loads(request.content))
            return httpx.Response(
                202,
                json={"id": self.sandbox_id, "status": {"state": "Pending"}},
            )
        if request.method == "GET" and path == f"/v1/sandboxes/{self.sandbox_id}":
            return httpx.Response(
                200,
                json={"id": self.sandbox_id, "status": {"state": self.state}},
            )
        if request.method == "DELETE" and path == f"/v1/sandboxes/{self.sandbox_id}":
            self.deleted.append(self.sandbox_id)
            return httpx.Response(204)
        if request.method == "POST" and path == f"/v1/sandboxes/{self.sandbox_id}/resume":
            self.resumed.append(self.sandbox_id)
            self.state = "Running"
            return httpx.Response(202)
        if request.method == "GET" and path.startswith(
            f"/v1/sandboxes/{self.sandbox_id}/endpoints/"
        ):
            port = path.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"endpoint": f"{self.endpoint_host}:{port}"})
        return httpx.Response(404, json={"error": "not found"})
