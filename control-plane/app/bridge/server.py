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
from app.ledger import Ledger

logger = logging.getLogger(__name__)

router = APIRouter()

# 可重建通道的会话状态：创建中与运行中（ended 的 token 不再可用）。
_ACTIVE_STATUSES = ("creating", "running")


def _hub(websocket: WebSocket) -> SessionHub:
    hub = getattr(websocket.app.state, "bridge_hub", None)
    if not isinstance(hub, SessionHub):
        raise RuntimeError("应用未配置 bridge_hub")
    return hub


async def _authorize(websocket: WebSocket, session_id: str, token: str) -> SessionChannel | None:
    """本进程有通道直接认证；没有则按台账重建（多副本/重启后 WS 落在任意实例）。"""
    hub = _hub(websocket)
    channel = hub.authorize(session_id, token)
    if channel is not None:
        return channel
    ledger = getattr(websocket.app.state, "ledger", None)
    if not isinstance(ledger, Ledger):
        return None
    record = await ledger.find_session_by_token(token)
    if record is None or record.session_id != session_id or record.status not in _ACTIVE_STATUSES:
        return None
    return hub.ensure(session_id, token, record.owner)


async def _authenticate(websocket: WebSocket, session_id: str, token: str) -> SessionChannel | None:
    """先 accept 再 close：未 accept 时 Starlette 回 HTTP 403，客户端拿不到业务关闭码。"""
    await websocket.accept()
    channel = await _authorize(websocket, session_id, token)
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
