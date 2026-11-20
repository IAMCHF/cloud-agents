"""Web 终端与文件树：execd 管理面代理（不属于 Codex 执行协议）。

- `WS /api/sessions/{id}/terminal?token=...`：浏览器 ↔ 控制面 ↔ execd PTY。
- `GET /api/sessions/{id}/files?path=...`：列目录。
- `GET /api/sessions/{id}/file?path=...`：读取文本文件（预览上限 512KiB）。
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from starlette.websockets import WebSocketState

from app.api.common import components_from, hub_from, running_record_by_token
from app.api.wsrelay import relay_websockets
from app.bridge.hub import CLOSE_CONFLICT, CLOSE_UNAUTHORIZED
from app.sandbox import OpenSandboxError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["terminal"])

_EXECD_PORT = 44772


def _strip_execd_frames(data: bytes) -> bytes | None:
    """execd PTY 二进制帧：0x01 数据去头，0x03 控制帧丢弃。"""
    if data[:1] == b"\x01":
        return data[1:]
    if data[:1] == b"\x03":
        return None
    return data


@router.get("/{session_id}/files")
async def list_files(
    session_id: str,
    request: Request,
    token: str = Query(default=""),
    path: str = Query("/workspace"),
) -> dict[str, Any]:
    components = components_from(request)
    record = await running_record_by_token(components, hub_from(request), session_id, token)
    if record.sandbox_id is None:  # pragma: no cover - 由 running_record_by_token 保证
        raise HTTPException(status_code=409, detail="会话未运行，请先恢复会话")
    try:
        entries = await components.client.execd_list_directory(record.sandbox_id, path)
    except OpenSandboxError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"path": path, "entries": entries}


@router.get("/{session_id}/file", response_class=PlainTextResponse)
async def read_file(
    session_id: str,
    request: Request,
    token: str = Query(default=""),
    path: str = Query(...),
) -> PlainTextResponse:
    components = components_from(request)
    record = await running_record_by_token(components, hub_from(request), session_id, token)
    if record.sandbox_id is None:  # pragma: no cover - 由 running_record_by_token 保证
        raise HTTPException(status_code=409, detail="会话未运行，请先恢复会话")
    try:
        content = await components.client.execd_read_file(record.sandbox_id, path)
    except OpenSandboxError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return PlainTextResponse(content.decode("utf-8", errors="replace"))


@router.websocket("/{session_id}/terminal")
async def terminal_socket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(default=""),
) -> None:
    hub = hub_from(websocket)
    components = components_from(websocket)
    try:
        record = await running_record_by_token(components, hub, session_id, token)
    except HTTPException as exc:
        await websocket.accept()
        code = CLOSE_UNAUTHORIZED if exc.status_code == 401 else CLOSE_CONFLICT
        await websocket.close(code=code, reason=str(exc.detail))
        return

    sandbox_id = record.sandbox_id
    if sandbox_id is None:  # pragma: no cover - 由 running_record_by_token 保证
        await websocket.accept()
        await websocket.close(code=CLOSE_CONFLICT, reason="session not running")
        return

    await websocket.accept()
    pty_id: str | None = None
    try:
        pty_id = await components.client.execd_create_pty(sandbox_id)
        endpoint = await components.client.endpoint(sandbox_id, _EXECD_PORT)
        base = endpoint if endpoint.startswith(("ws://", "wss://")) else f"ws://{endpoint}"
        headers = (
            {"X-EXECD-ACCESS-TOKEN": components.settings.execd_access_token}
            if components.settings.execd_access_token
            else {}
        )
        from websockets.asyncio.client import connect

        async with connect(
            f"{base.rstrip('/')}/pty/{pty_id}/ws",
            additional_headers=headers,
            max_size=None,
        ) as exec_ws:
            await relay_websockets(websocket, exec_ws, to_browser_bytes=_strip_execd_frames)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("终端代理失败：%s", session_id)
        if websocket.client_state == WebSocketState.CONNECTED:
            with contextlib.suppress(Exception):
                await websocket.close(code=1011)
    finally:
        if pty_id is not None:
            await components.client.execd_delete_pty(sandbox_id, pty_id)
