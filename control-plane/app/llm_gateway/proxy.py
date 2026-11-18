"""最小 LLM 网关：OpenAI 兼容路径透传，校验会话 token；真 key 只存在于控制面。"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from app.bridge.hub import SessionHub
from app.metrics import Metrics

logger = logging.getLogger(__name__)

_HOP_HEADERS = {
    "host",
    "authorization",
    "x-api-key",
    "content-length",
    "connection",
    "transfer-encoding",
    "accept-encoding",
}
_PASSTHROUGH_RESPONSE_HEADERS = {"content-type", "cache-control", "openai-processing-ms"}


class LlmGateway:
    def __init__(
        self,
        *,
        upstream_base_url: str,
        api_key: str,
        hub: SessionHub,
        timeout: float = 600.0,
        transport: httpx.AsyncBaseTransport | None = None,
        metrics: Metrics | None = None,
    ) -> None:
        self._upstream_base_url = upstream_base_url.rstrip("/")
        self._api_key = api_key
        self._hub = hub
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport)
        self._metrics = metrics
        self._requests = 0

    @property
    def request_count(self) -> int:
        return self._requests

    @property
    def configured(self) -> bool:
        return bool(self._upstream_base_url)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def forward(self, request: Request, path: str) -> Response:
        token = _extract_token(request)
        channel = self._hub.authorize_token(token)
        if channel is None:
            return _json_error(401, "invalid session token")
        if not self.configured:
            return _json_error(503, "LLM upstream not configured")

        url = f"{self._upstream_base_url}/{path.lstrip('/')}"
        headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() not in _HOP_HEADERS
        }
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        body = await request.body()
        upstream_request = self._client.build_request(
            request.method,
            url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
        self._requests += 1
        if self._metrics is not None:
            self._metrics.llm_requests.inc()
        try:
            upstream_response = await self._client.send(upstream_request, stream=True)
        except httpx.HTTPError as exc:
            logger.warning("LLM 上游连接失败：%s", exc)
            return _json_error(502, "LLM upstream unavailable")

        response_headers = {
            name: value
            for name, value in upstream_response.headers.items()
            if name.lower() in _PASSTHROUGH_RESPONSE_HEADERS
        }
        # 必须用解压后的字节流：raw 会把 gzip 压缩体直接透传，客户端按 UTF-8 解析即失败。
        return StreamingResponse(
            upstream_response.aiter_bytes(),
            status_code=upstream_response.status_code,
            headers=response_headers,
            background=BackgroundTask(upstream_response.aclose),
        )


def _extract_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-api-key", "").strip()


def _json_error(status: int, message: str) -> Response:
    payload: dict[str, Any] = {"error": {"message": message, "type": "gateway_error"}}
    return Response(
        content=json.dumps(payload),
        status_code=status,
        media_type="application/json",
    )


def build_router() -> APIRouter:
    router = APIRouter(prefix="/llm/v1")

    @router.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def proxy(path: str, request: Request) -> Response:
        gateway = getattr(request.app.state, "llm_gateway", None)
        if not isinstance(gateway, LlmGateway):
            raise HTTPException(status_code=503, detail="LLM gateway not configured")
        return await gateway.forward(request, path)

    return router
