"""控制面会话通道：桥接连接与 Web 客户端之间的薄转发与审批重放。"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)

# WebSocket 关闭码：与会话鉴权相关的自定义区间（4000–4999 归应用）。
CLOSE_UNAUTHORIZED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_CONFLICT = 4409
CLOSE_NO_BRIDGE = 1013


class HubError(Exception):
    """转发条件不满足（例如桥接未连接）。"""


@dataclass
class SessionChannel:
    """一条云端会话的两个连接端；P1 单客户端在线。"""

    session_id: str
    token: str
    owner: str
    bridge: WebSocket | None = None
    client: WebSocket | None = None
    pending: dict[str, str] = field(default_factory=dict)
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionHub:
    def __init__(self) -> None:
        self._channels: dict[str, SessionChannel] = {}
        self._tokens: dict[str, str] = {}  # token -> session_id（LLM 网关鉴权用）
        # 桥接断开回调：由生命周期管理器注入，用于判定沙箱是否已退出。
        self.on_bridge_detached: Callable[[str], Awaitable[None]] | None = None

    def create(self, session_id: str, token: str, owner: str) -> SessionChannel:
        channel = SessionChannel(session_id=session_id, token=token, owner=owner)
        self._channels[session_id] = channel
        self._tokens[token] = session_id
        return channel

    def remove(self, session_id: str) -> None:
        channel = self._channels.pop(session_id, None)
        if channel is not None:
            self._tokens.pop(channel.token, None)

    def get(self, session_id: str) -> SessionChannel | None:
        return self._channels.get(session_id)

    def authorize(self, session_id: str, token: str) -> SessionChannel | None:
        channel = self._channels.get(session_id)
        if channel is None or not token:
            return None
        if not hmac.compare_digest(channel.token, token):
            return None
        return channel

    def authorize_token(self, token: str) -> SessionChannel | None:
        """按 token 反查会话（LLM 网关：沙箱只有会话 token，没有会话 ID）。"""
        if not token:
            return None
        session_id = self._tokens.get(token)
        if session_id is None:
            return None
        return self._channels.get(session_id)

    async def attach_bridge(self, channel: SessionChannel, websocket: WebSocket) -> bool:
        if channel.bridge is not None and channel.bridge is not websocket:
            await websocket.close(code=CLOSE_CONFLICT, reason="bridge already connected")
            return False
        channel.bridge = websocket
        logger.info("会话 %s 桥接已连接", channel.session_id)
        return True

    async def detach_bridge(self, channel: SessionChannel, websocket: WebSocket) -> None:
        if channel.bridge is websocket:
            channel.bridge = None
            logger.info("会话 %s 桥接已断开", channel.session_id)
            callback = self.on_bridge_detached
            if callback is not None:
                try:
                    await callback(channel.session_id)
                except Exception:
                    logger.exception("桥接断开回调失败：%s", channel.session_id)

    async def attach_client(self, channel: SessionChannel, websocket: WebSocket) -> bool:
        if channel.client is not None and channel.client is not websocket:
            await websocket.close(code=CLOSE_CONFLICT, reason="client already connected")
            return False
        channel.client = websocket
        # 客户端重连：补发未决审批请求（同沙箱重连 stdio 不断，事件不回放）。
        for frame in list(channel.pending.values()):
            await self._send(channel, websocket, frame)
        return True

    async def detach_client(self, channel: SessionChannel, websocket: WebSocket) -> None:
        if channel.client is websocket:
            channel.client = None

    async def from_bridge(self, channel: SessionChannel, frame: str) -> None:
        request_id = _server_request_id(frame)
        if request_id is not None:
            channel.pending[request_id] = frame
        client = channel.client
        if client is None:
            return  # 无客户端在线：事件丢弃，重开走 thread/resume 回放
        try:
            await self._send(channel, client, frame)
        except Exception:
            logger.info("会话 %s 客户端发送失败，标记离线", channel.session_id)
            channel.client = None

    async def from_client(self, channel: SessionChannel, frame: str) -> None:
        request_id = _client_response_id(frame)
        if request_id is not None:
            channel.pending.pop(request_id, None)
        bridge = channel.bridge
        if bridge is None:
            raise HubError("会话桥接未连接")
        try:
            await self._send(channel, bridge, frame)
        except Exception as exc:
            channel.bridge = None
            raise HubError("会话桥接发送失败") from exc

    async def _send(self, channel: SessionChannel, websocket: WebSocket, frame: str) -> None:
        async with channel.send_lock:
            await websocket.send_text(frame)


def _load(frame: str) -> object:
    try:
        return json.loads(frame)
    except json.JSONDecodeError:
        return None


def _server_request_id(frame: str) -> str | None:
    data = _load(frame)
    if isinstance(data, dict) and "id" in data and "method" in data:
        return str(data["id"])
    return None


def _client_response_id(frame: str) -> str | None:
    data = _load(frame)
    if isinstance(data, dict) and "id" in data and "method" not in data:
        return str(data["id"])
    return None
