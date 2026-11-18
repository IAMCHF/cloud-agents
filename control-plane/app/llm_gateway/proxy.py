"""最小 LLM 网关：OpenAI 兼容路径透传，校验会话 token；真 key 只存在于控制面。

P2 起鉴权与租户归因以台账为准（多副本可查），并旁路解析响应里的 usage 计量：
- Responses API：`response.completed` 事件的 `response.usage`（input_tokens/output_tokens）
- Chat Completions：流式末块或非流式体的 `usage`（prompt_tokens/completion_tokens）
租户月度 token 预算耗尽时在转发前返回 429。
"""

from __future__ import annotations

import codecs
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from app.ledger import Ledger, SessionRecord
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

# 计入计量的会话状态：结束的会话 token 不再可用于调用上游。
_METERED_STATUSES = ("creating", "running")
# 非流式响应最多缓存多少字节用于解析 usage；超限放弃解析，不影响转发。
_MAX_JSON_TAP_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


class UsageTap:
    """旁路解析响应体 usage：SSE 按事件切分增量解析，非流式 JSON 整包解析。"""

    def __init__(self, content_type: str) -> None:
        self._sse = "text/event-stream" in content_type.lower()
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._buffer = ""
        self._json_body: bytearray | None = None if self._sse else bytearray()
        self.usage: Usage | None = None

    def feed(self, chunk: bytes) -> None:
        if self._sse:
            # 统一换行后再切分事件，兼容跨 chunk 的 CRLF。
            self._buffer = (self._buffer + self._decoder.decode(chunk)).replace("\r\n", "\n")
            self._drain_events()
            return
        if self._json_body is not None:
            self._json_body.extend(chunk)
            if len(self._json_body) > _MAX_JSON_TAP_BYTES:
                self._json_body = None

    def finish(self) -> None:
        if self._sse:
            self._buffer = (self._buffer + self._decoder.decode(b"", final=True)).replace(
                "\r\n", "\n"
            )
            self._drain_events(flush=True)
            return
        body, self._json_body = self._json_body, None
        if not body:
            return
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return
        if isinstance(data, dict):
            self.usage = _usage_from_payload(data) or self.usage

    def _drain_events(self, *, flush: bool = False) -> None:
        while True:
            index = self._buffer.find("\n\n")
            if index < 0:
                break
            event, self._buffer = self._buffer[:index], self._buffer[index + 2 :]
            self._consume_event(event)
        if flush and self._buffer.strip():
            event, self._buffer = self._buffer, ""
            self._consume_event(event)

    def _consume_event(self, event: str) -> None:
        for line in event.split("\n"):
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                usage = _usage_from_payload(data)
                if usage is not None:
                    self.usage = usage


class LlmGateway:
    def __init__(
        self,
        *,
        upstream_base_url: str,
        api_key: str,
        ledger: Ledger,
        timeout: float = 600.0,
        transport: httpx.AsyncBaseTransport | None = None,
        metrics: Metrics | None = None,
    ) -> None:
        self._upstream_base_url = upstream_base_url.rstrip("/")
        self._api_key = api_key
        self._ledger = ledger
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
        record = await self._ledger.find_session_by_token(token)
        if record is None or record.status not in _METERED_STATUSES:
            return _json_error(401, "invalid session token")
        if not self.configured:
            return _json_error(503, "LLM upstream not configured")
        rejection = await self._check_budget(record.tenant_id)
        if rejection is not None:
            return rejection

        url = f"{self._upstream_base_url}/{path.lstrip('/')}"
        headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() not in _HOP_HEADERS
        }
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        body = await request.body()
        model = _request_model(body)
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
        tap = UsageTap(upstream_response.headers.get("content-type", ""))
        settled = False

        async def metered_stream() -> AsyncIterator[bytes]:
            nonlocal settled
            try:
                # 必须用解压后的字节流：raw 会把 gzip 压缩体直接透传，客户端按 UTF-8 解析即失败。
                async for chunk in upstream_response.aiter_bytes():
                    tap.feed(chunk)
                    yield chunk
            finally:
                if not settled:
                    settled = True
                    tap.finish()
                    await self._settle_usage(record, model, tap.usage)

        return StreamingResponse(
            metered_stream(),
            status_code=upstream_response.status_code,
            headers=response_headers,
            background=BackgroundTask(upstream_response.aclose),
        )

    async def _check_budget(self, tenant_id: str) -> Response | None:
        """租户月度 token 预算（0 = 不限）：已用量达到预算即拒绝转发。"""
        tenant = await self._ledger.get_tenant(tenant_id)
        if tenant is None or tenant.monthly_token_budget <= 0:
            return None
        used = await self._ledger.usage_total(tenant_id, since=_month_start())
        if used < tenant.monthly_token_budget:
            return None
        if self._metrics is not None:
            self._metrics.observe_budget_rejection(tenant_id)
        return _json_error(429, "tenant monthly token budget exhausted")

    async def _settle_usage(self, record: SessionRecord, model: str, usage: Usage | None) -> None:
        if usage is None or (usage.input_tokens == 0 and usage.output_tokens == 0):
            return
        try:
            await self._ledger.record_usage(
                session_id=record.session_id,
                tenant_id=record.tenant_id,
                model=model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
        except Exception:
            logger.exception("LLM 用量写入失败：%s", record.session_id)
            return
        if self._metrics is not None:
            self._metrics.observe_llm_usage(
                record.tenant_id, usage.input_tokens, usage.output_tokens
            )


def _extract_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("x-api-key", "").strip()


def _request_model(body: bytes) -> str:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return ""
    if isinstance(data, dict):
        model = data.get("model")
        if isinstance(model, str):
            return model
    return ""


def _month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _usage_from_payload(data: dict[str, Any]) -> Usage | None:
    if data.get("type") == "response.completed":
        response = data.get("response")
        if isinstance(response, dict):
            return _usage_from_dict(response.get("usage"))
    return _usage_from_dict(data.get("usage"))


def _usage_from_dict(value: object) -> Usage | None:
    if not isinstance(value, dict):
        return None
    input_tokens = value.get("input_tokens", value.get("prompt_tokens"))
    output_tokens = value.get("output_tokens", value.get("completion_tokens"))
    if input_tokens is None and output_tokens is None:
        return None
    return Usage(input_tokens=_to_int(input_tokens), output_tokens=_to_int(output_tokens))


def _to_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


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
