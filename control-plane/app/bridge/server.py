"""控制面 WSS 端点：沙箱桥接与 Web 客户端各一条。"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.bridge.hub import (
    CLOSE_NO_BRIDGE,
    CLOSE_UNAUTHORIZED,
    HubError,
    SessionChannel,
    SessionHub,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _hub(websocket: WebSocket) -> SessionHub:
    hub = getattr(websocket.app.state, "bridge_hub", None)
    if not isinstance(hub, SessionHub):
        raise RuntimeError("应用未配置 bridge_hub")
    return hub


async def _authenticate(websocket: WebSocket, session_id: str, token: str) -> SessionChannel | None:
    """先 accept 再 close：未 accept 时 Starlette 回 HTTP 403，客户端拿不到业务关闭码。"""
    await websocket.accept()
    channel = _hub(websocket).authorize(session_id, token)
    if channel is None:
        await websocket.close(code=CLOSE_UNAUTHORIZED, reason="invalid session token")
    return channel


@router.websocket("/ws/bridge/{session_id}")
async def bridge_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Annotated[str, Query()] = "",
) -> None:
    hub = _hub(websocket)
    channel = await _authenticate(websocket, session_id, token)
    if channel is None:
        return
    if not await hub.attach_bridge(channel, websocket):
        return
    try:
        while True:
            frame = await websocket.receive_text()
            await hub.from_bridge(channel, frame)
    except WebSocketDisconnect:
        pass
    finally:
        await hub.detach_bridge(channel, websocket)


@router.websocket("/ws/session/{session_id}")
async def client_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Annotated[str, Query()] = "",
) -> None:
    hub = _hub(websocket)
    channel = await _authenticate(websocket, session_id, token)
    if channel is None:
        return
    if not await hub.attach_client(channel, websocket):
        return
    try:
        while True:
            frame = await websocket.receive_text()
            await hub.from_client(channel, frame)
    except WebSocketDisconnect:
        pass
    except HubError as exc:
        logger.info("会话 %s 转发失败：%s", session_id, exc)
        await websocket.close(code=CLOSE_NO_BRIDGE, reason="sandbox bridge not connected")
    finally:
        await hub.detach_client(channel, websocket)
