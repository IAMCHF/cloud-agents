"""Web 终端与文件树：execd 管理面代理（不属于 Codex 执行协议）。

- `WS /api/sessions/{id}/terminal?token=...`：浏览器 ↔ 控制面 ↔ execd PTY。
- `GET /api/sessions/{id}/files?path=...`：列目录。
- `GET /api/sessions/{id}/file?path=...`：读取文本文件（预览上限 512KiB）。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from starlette.websockets import WebSocketState

from app.bootstrap import Components
from app.bridge.hub import CLOSE_CONFLICT, CLOSE_UNAUTHORIZED, SessionHub
from app.sandbox import OpenSandboxError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["terminal"])

_EXECD_PORT = 44772


def _components(request: Any) -> Components:
    components = getattr(request.app.state, "components", None)
    if not isinstance(components, Components):
        raise HTTPException(status_code=503, detail="components not configured")
    return components


def _hub(websocket: Any) -> SessionHub:
    hub = getattr(websocket.app.state, "bridge_hub", None)
    if not isinstance(hub, SessionHub):
        raise HTTPException(status_code=503, detail="bridge hub not configured")
    return hub


async def _running_record(
    components: Components, hub: SessionHub, session_id: str, token: str
) -> Any:
    """按台账校验会话 token：多副本下文件/终端请求可落在任意实例。"""
    if not token:
        raise HTTPException(status_code=401, detail="session token invalid")
    record = await components.ledger.find_session_by_token(token)
    if record is None or record.session_id != session_id or record.status == "ended":
        raise HTTPException(status_code=401, detail="session token invalid")
    if record.status in {"creating", "running"}:
        hub.ensure(session_id, token, record.owner)
    if record.status != "running" or record.sandbox_id is None:
        raise HTTPException(status_code=409, detail="会话未运行，请先恢复会话")
    return record


@router.get("/{session_id}/files")
async def list_files(
    session_id: str,
    request: Request,
    token: str = Query(default=""),
    path: str = Query("/workspace"),
) -> dict[str, Any]:
    components = _components(request)
    record = await _running_record(components, _hub(request), session_id, token)
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
    components = _components(request)
    record = await _running_record(components, _hub(request), session_id, token)
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
    hub = _hub(websocket)
    components = _components(websocket)
    try:
        record = await _running_record(components, hub, session_id, token)
    except HTTPException as exc:
        await websocket.accept()
        code = CLOSE_UNAUTHORIZED if exc.status_code == 401 else CLOSE_CONFLICT
        await websocket.close(code=code, reason=str(exc.detail))
        return

    await websocket.accept()
    pty_id: str | None = None
    try:
        pty_id = await components.client.execd_create_pty(record.sandbox_id)
        endpoint = await components.client.endpoint(record.sandbox_id, _EXECD_PORT)
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
            await _bridge_terminal(websocket, exec_ws)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("终端代理失败：%s", session_id)
        if websocket.client_state == WebSocketState.CONNECTED:
            with contextlib.suppress(Exception):
                await websocket.close(code=1011)
    finally:
        if pty_id is not None and record.sandbox_id is not None:
            await components.client.execd_delete_pty(record.sandbox_id, pty_id)


async def _bridge_terminal(websocket: WebSocket, exec_ws: Any) -> None:
    async def browser_to_exec() -> None:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            text = message.get("text")
            if text is not None:
                await exec_ws.send(text)
                continue
            data = message.get("bytes")
            if data is not None:
                await exec_ws.send(data)

    async def exec_to_browser() -> None:
        async for message in exec_ws:
            if isinstance(message, bytes):
                if message[:1] == b"\x01":
                    await websocket.send_bytes(message[1:])
                elif message[:1] == b"\x03":
                    continue
                else:
                    await websocket.send_bytes(message)
            else:
                await websocket.send_text(message)

    tasks = [
        asyncio.create_task(browser_to_exec(), name="terminal-browser"),
        asyncio.create_task(exec_to_browser(), name="terminal-execd"),
    ]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
