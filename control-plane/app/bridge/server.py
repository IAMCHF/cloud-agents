"""控制面 WSS 端点：沙箱桥接与 Web 客户端各一条。"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.auth import OidcError, OidcProvider
from app.bridge.hub import (
    CLOSE_FORBIDDEN,
    CLOSE_NO_BRIDGE,
    CLOSE_UNAUTHORIZED,
    HubError,
    SessionChannel,
    SessionHub,
)
from app.config import Settings

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


async def _authenticate_client(
    websocket: WebSocket, session_id: str, token: str, access_token: str
) -> tuple[SessionChannel, str] | None:
    """客户端连接：会话 token 定位通道；OIDC 模式再校验用户身份与会话属主。

    返回通道与该连接的审计主体（actor）：token 模式回落到会话属主。
    """
    channel = await _authenticate(websocket, session_id, token)
    if channel is None:
        return None
    settings = getattr(websocket.app.state, "settings", None)
    if not isinstance(settings, Settings) or settings.auth_mode != "oidc":
        return channel, channel.owner
    provider = getattr(websocket.app.state, "oidc", None)
    if not isinstance(provider, OidcProvider):
        await websocket.close(code=CLOSE_UNAUTHORIZED, reason="OIDC 未配置")
        return None
    try:
        principal = await provider.verify(access_token)
    except OidcError:
        await websocket.close(code=CLOSE_UNAUTHORIZED, reason="invalid access token")
        return None
    if principal.subject != channel.owner:
        await websocket.close(code=CLOSE_FORBIDDEN, reason="not session owner")
        return None
    return channel, principal.subject


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
    access_token: Annotated[str, Query()] = "",
) -> None:
    hub = _hub(websocket)
    authenticated = await _authenticate_client(websocket, session_id, token, access_token)
    if authenticated is None:
        return
    channel, actor = authenticated
    connection_id = await hub.attach_client(channel, websocket, actor=actor)
    try:
        while True:
            frame = await websocket.receive_text()
            await hub.from_client(channel, connection_id, frame)
    except WebSocketDisconnect:
        pass
    except HubError as exc:
        logger.info("会话 %s 转发失败：%s", session_id, exc)
        await websocket.close(code=CLOSE_NO_BRIDGE, reason="sandbox bridge not connected")
    finally:
        await hub.detach_client(channel, connection_id)
