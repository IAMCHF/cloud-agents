"""沙箱应用预览：子域反代（HTTP + WebSocket）。

域名形如 `<session_id>--<port>.preview.<PREVIEW_BASE_DOMAIN>`；控制面按 Host 解析
会话与端口，用短期签名票据（查询参数或 HttpOnly Cookie）鉴权，再反代到沙箱 endpoint。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any, cast
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, WebSocket
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.requests import HTTPConnection
from websockets.typing import Subprotocol

from app.api.common import components_from, hub_from, running_record_by_token
from app.api.wsrelay import relay_websockets
from app.bootstrap import Components
from app.config import Settings
from app.sandbox import OpenSandboxError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["preview"])

COOKIE_NAME = "ca_preview"
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
_MIN_PORT = 1024
_MAX_PORT = 65535


class PreviewRequest(BaseModel):
    port: int = Field(ge=_MIN_PORT, le=_MAX_PORT)


def _settings(connection: HTTPConnection) -> Settings:
    settings = getattr(connection.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise HTTPException(status_code=503, detail="settings not configured")
    return settings


def preview_host(session_id: str, port: int, base_domain: str) -> str:
    return f"{session_id}--{port}.preview.{base_domain.strip('.')}"


def parse_preview_host(host_header: str, base_domain: str) -> tuple[str, int] | None:
    """解析 `<session>--<port>.preview.<base>`；非预览域名返回 None。"""
    base = base_domain.strip(".").lower()
    if not base:
        return None
    host = host_header.split(":", 1)[0].strip().lower().rstrip(".")
    suffix = f".preview.{base}"
    if not host.endswith(suffix):
        return None
    label = host[: -len(suffix)]
    session_id, separator, port_text = label.rpartition("--")
    if not separator or not session_id or not port_text.isdigit():
        return None
    port = int(port_text)
    if not _MIN_PORT <= port <= _MAX_PORT:
        return None
    return session_id, port


def _signing_key(settings: Settings) -> bytes | None:
    secret = settings.preview_token_secret or settings.p1_auth_token
    return secret.encode("utf-8") if secret else None


def mint_preview_token(settings: Settings, session_id: str, port: int) -> tuple[str, int]:
    key = _signing_key(settings)
    if key is None:
        raise HTTPException(status_code=503, detail="preview signing key not configured")
    expires_at = int(time.time()) + settings.preview_token_ttl_seconds
    raw = json.dumps(
        {"s": session_id, "p": port, "e": expires_at}, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    payload = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    signature = hmac.new(key, payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}", expires_at


def verify_preview_token(settings: Settings, token: str) -> tuple[str, int] | None:
    key = _signing_key(settings)
    if key is None or not token or "." not in token:
        return None
    payload, _, signature = token.partition(".")
    expected = hmac.new(key, payload.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        padded = payload + "=" * (-len(payload) % 4)
        data: Any = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    session_id, port, expires_at = data.get("s"), data.get("p"), data.get("e")
    if (
        not isinstance(session_id, str)
        or not isinstance(port, int)
        or not isinstance(expires_at, int)
    ):
        return None
    if expires_at < int(time.time()):
        return None
    return session_id, port


@router.post("/api/sessions/{session_id}/preview")
async def create_preview(
    session_id: str,
    request: Request,
    payload: PreviewRequest,
    token: str = Query(default=""),
) -> dict[str, Any]:
    components = components_from(request)
    await running_record_by_token(components, hub_from(request), session_id, token)
    settings = _settings(request)
    base = settings.preview_base_domain.strip(".")
    if not base:
        raise HTTPException(status_code=503, detail="preview disabled")
    preview_token, expires_at = mint_preview_token(settings, session_id, payload.port)
    scheme = "https" if settings.public_base_url.startswith("https://") else "http"
    host = preview_host(session_id, payload.port, base)
    return {
        "url": f"{scheme}://{host}/",
        "preview_token": preview_token,
        "expires_at": expires_at,
    }


async def _authorize_preview(
    connection: HTTPConnection, base: str
) -> tuple[Components, str, int, str]:
    """校验 Host + 票据 + 台账；返回组件、会话 ID、端口与 endpoint 主机。"""
    parsed = parse_preview_host(connection.headers.get("host", ""), base)
    if parsed is None:
        raise HTTPException(status_code=404, detail="not a preview host")
    session_id, port = parsed
    token = connection.query_params.get("preview_token", "") or connection.cookies.get(
        COOKIE_NAME, ""
    )
    claims = verify_preview_token(_settings(connection), token)
    if claims is None or claims != (session_id, port):
        raise HTTPException(status_code=401, detail="preview token invalid")
    components = components_from(connection)
    record = await components.ledger.get(session_id)
    if record is None or record.status != "running" or record.sandbox_id is None:
        raise HTTPException(status_code=409, detail="会话未运行，请先恢复会话")
    try:
        endpoint = await components.client.endpoint(record.sandbox_id, port)
    except OpenSandboxError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return components, session_id, port, endpoint


def _http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=None, follow_redirects=False)


def _forward_request_headers(request: Request, endpoint: str) -> dict[str, str]:
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in _HOP_BY_HOP | {"host", "accept-encoding", "cookie", "authorization"}
    }
    headers["host"] = endpoint
    headers["accept-encoding"] = "identity"
    cookie = _strip_preview_cookie(request.headers.get("cookie", ""))
    if cookie:
        headers["cookie"] = cookie
    origin = request.headers.get("origin")
    if origin:
        headers["origin"] = f"http://{endpoint}"
    return headers


def _strip_preview_cookie(cookie_header: str) -> str:
    parts = []
    for item in cookie_header.split(";"):
        name, separator, _ = item.strip().partition("=")
        if separator and name.strip() == COOKIE_NAME:
            continue
        if item.strip():
            parts.append(item.strip())
    return "; ".join(parts)


def _response_headers(
    response: httpx.Response, endpoint: str, preview: str
) -> tuple[dict[str, str], list[str]]:
    headers: dict[str, str] = {}
    cookies: list[str] = []
    for key, value in response.headers.multi_items():
        lowered = key.lower()
        if lowered in _HOP_BY_HOP:
            continue
        if lowered == "location":
            value = _rewrite_location(value, endpoint, preview)
            headers[key] = value
        elif lowered == "set-cookie":
            cookies.append(_strip_cookie_domain(value))
        else:
            headers[key] = value
    return headers, cookies


def _rewrite_location(location: str, endpoint: str, preview: str) -> str:
    for scheme in ("http://", "https://"):
        if location.startswith(scheme + endpoint):
            return location.replace(scheme + endpoint, f"http://{preview}", 1)
    return location


def _strip_cookie_domain(value: str) -> str:
    parts = [part.strip() for part in value.split(";") if part.strip()]
    kept = [part for part in parts if not part.lower().startswith("domain=")]
    return "; ".join(kept)


def _target_url(endpoint: str, path: str, query: list[tuple[str, str]]) -> str:
    url = f"http://{endpoint}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urlencode(query, doseq=True)}"
    return url


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def preview_http(request: Request, path: str) -> Any:
    settings = _settings(request)
    base = settings.preview_base_domain.strip(".")
    parsed = parse_preview_host(request.headers.get("host", ""), base)
    if parsed is None:
        return PlainTextResponse("not found", status_code=404)
    _components, session_id, port, endpoint = await _authorize_preview(request, base)
    preview = preview_host(session_id, port, base)
    query = [
        (key, value) for key, value in request.query_params.multi_items() if key != "preview_token"
    ]
    headers = _forward_request_headers(request, endpoint)
    body = await request.body()
    client = _http_client()
    upstream_request = client.build_request(
        request.method, _target_url(endpoint, path, query), headers=headers, content=body
    )
    try:
        upstream = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"沙箱服务不可达：{exc}") from exc

    response_headers, cookies = _response_headers(upstream, endpoint, preview)
    token = request.query_params.get("preview_token", "")
    if token:
        remaining = max(0, _token_expiry(token) - int(time.time()))
        secure = "; Secure" if settings.public_base_url.startswith("https://") else ""
        cookies.append(
            f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={remaining}{secure}"
        )

    async def stream_body() -> Any:
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    response = StreamingResponse(
        stream_body(), status_code=upstream.status_code, headers=response_headers
    )
    for cookie in cookies:
        response.raw_headers.append((b"set-cookie", cookie.encode("latin-1")))
    return response


def _token_expiry(token: str) -> int:
    payload = token.partition(".")[0]
    try:
        padded = payload + "=" * (-len(payload) % 4)
        data: Any = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return int(time.time())
    if isinstance(data, dict) and isinstance(data.get("e"), int):
        return int(data["e"])
    return int(time.time())


@router.websocket("/{path:path}")
async def preview_socket(websocket: WebSocket, path: str) -> None:
    settings = _settings(websocket)
    base = settings.preview_base_domain.strip(".")
    try:
        _components, session_id, port, endpoint = await _authorize_preview(websocket, base)
    except HTTPException as exc:
        await websocket.accept()
        await websocket.close(code=4401 if exc.status_code == 401 else 4409, reason=str(exc.detail))
        return

    query = [
        (key, value)
        for key, value in websocket.query_params.multi_items()
        if key != "preview_token"
    ]
    target = _target_url(endpoint, path, query).replace("http://", "ws://", 1)
    headers: dict[str, str] = {}
    origin = websocket.headers.get("origin")
    if origin:
        headers["origin"] = f"http://{endpoint}"
    cookie = _strip_preview_cookie(websocket.headers.get("cookie", ""))
    if cookie:
        headers["cookie"] = cookie
    subprotocols = [
        item.strip()
        for item in (websocket.headers.get("sec-websocket-protocol", "")).split(",")
        if item.strip()
    ]

    await websocket.accept()
    from websockets.asyncio.client import connect

    try:
        async with connect(
            target,
            additional_headers=headers,
            subprotocols=cast("list[Subprotocol] | None", subprotocols or None),
            max_size=None,
        ) as upstream:
            await relay_websockets(websocket, upstream)
    except Exception:
        logger.exception("预览 WebSocket 失败：%s:%s", session_id, port)
        await websocket.close(code=1011)
