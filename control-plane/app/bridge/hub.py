"""控制面会话通道：桥接连接与 Web 客户端之间的薄转发、多客户端扇出与响应仲裁。"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from starlette.websockets import WebSocket

logger = logging.getLogger(__name__)

# WebSocket 关闭码：与会话鉴权相关的自定义区间（4000–4999 归应用）。
CLOSE_UNAUTHORIZED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_CONFLICT = 4409
CLOSE_NO_BRIDGE = 1013
# 客户端出站队列积压超限：判定为慢客户端并断开，避免拖慢其它客户端与桥接。
CLOSE_SLOW_CLIENT = 4408

# 每个客户端连接的出站帧上限；流式 delta 很小，积压到上限说明连接已不可用。
CLIENT_QUEUE_SIZE = 256

# 审计钩子（session_id, kind, payload）；由装配层注入，缺失时静默跳过。
AuditHook = Callable[[str, str, dict[str, Any]], None]


class HubError(Exception):
    """转发条件不满足（例如桥接未连接）。"""


def _frame_queue() -> asyncio.Queue[str | None]:
    return asyncio.Queue(maxsize=CLIENT_QUEUE_SIZE)


@dataclass
class ClientLink:
    """一条 Web 客户端连接：独立出站队列 + 写协程，慢客户端不阻塞扇出。"""

    connection_id: str
    websocket: WebSocket
    actor: str
    queue: asyncio.Queue[str | None] = field(default_factory=_frame_queue)
    writer: asyncio.Task[None] | None = None

    def enqueue(self, frame: str) -> bool:
        try:
            self.queue.put_nowait(frame)
        except asyncio.QueueFull:
            return False
        return True

    def alive(self) -> bool:
        return self.writer is not None and not self.writer.done()

    async def run(self) -> None:
        try:
            while True:
                frame = await self.queue.get()
                if frame is None:
                    return
                await self.websocket.send_text(frame)
        except Exception:
            logger.info("客户端 %s 发送失败", self.connection_id)

    async def stop(self) -> None:
        writer = self.writer
        self.writer = None
        if writer is None:
            return
        writer.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await writer


@dataclass
class SessionChannel:
    """一条云端会话：一个桥接端 + 多个 Web 客户端端。"""

    session_id: str
    token: str
    owner: str
    bridge: WebSocket | None = None
    clients: dict[str, ClientLink] = field(default_factory=dict)
    pending: dict[str, str] = field(default_factory=dict)


class SessionHub:
    def __init__(self) -> None:
        self._channels: dict[str, SessionChannel] = {}
        # 桥接断开回调：由生命周期管理器注入，用于判定沙箱是否已退出。
        self.on_bridge_detached: Callable[[str], Awaitable[None]] | None = None
        # 审计回调：由装配层注入台账，多客户端连接事件与响应归因落库。
        self.on_audit: AuditHook | None = None

    def create(self, session_id: str, token: str, owner: str) -> SessionChannel:
        channel = SessionChannel(session_id=session_id, token=token, owner=owner)
        self._channels[session_id] = channel
        return channel

    def ensure(self, session_id: str, token: str, owner: str) -> SessionChannel:
        """按台账重建通道：已存在则复用（函数内无 await，检查-创建在事件循环内原子）。"""
        channel = self._channels.get(session_id)
        if channel is None:
            channel = self.create(session_id, token, owner)
            logger.info("会话 %s 通道已按台账重建", session_id)
        return channel

    def remove(self, session_id: str) -> None:
        self._channels.pop(session_id, None)

    def get(self, session_id: str) -> SessionChannel | None:
        return self._channels.get(session_id)

    def authorize(self, session_id: str, token: str) -> SessionChannel | None:
        channel = self._channels.get(session_id)
        if channel is None or not token:
            return None
        if not hmac.compare_digest(channel.token, token):
            return None
        return channel

    async def wait_bridge(self, channel: SessionChannel, timeout: float) -> bool:
        """等待桥接接入（客户端可能先于桥接重连到达）；超时返回 False。"""
        deadline = asyncio.get_running_loop().time() + timeout
        while channel.bridge is None:
            if asyncio.get_running_loop().time() >= deadline:
                return False
            await asyncio.sleep(0.02)
        return True

    def drop_if_idle(self, session_id: str) -> None:
        """移除无桥接且无客户端的空通道（错误副本上按台账重建出来的壳）。"""
        channel = self._channels.get(session_id)
        if channel is not None and channel.bridge is None and not channel.clients:
            self._channels.pop(session_id, None)

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

    async def attach_client(
        self, channel: SessionChannel, websocket: WebSocket, *, actor: str
    ) -> str:
        """登记新客户端并补发未决服务端请求（审批）；多端同时在线，响应由 from_client 仲裁。"""
        connection_id = uuid.uuid4().hex
        link = ClientLink(connection_id=connection_id, websocket=websocket, actor=actor)
        link.writer = asyncio.create_task(link.run(), name=f"client-send-{connection_id[:8]}")
        channel.clients[connection_id] = link
        logger.info(
            "会话 %s 客户端 %s 已连接（在线 %s）",
            channel.session_id,
            connection_id,
            len(channel.clients),
        )
        self._audit(
            channel.session_id,
            "client.connected",
            {"connection_id": connection_id, "actor": actor, "clients": len(channel.clients)},
        )
        for request_id, frame in list(channel.pending.items()):
            if request_id not in channel.pending:
                continue  # 补发期间已被其它客户端响应
            await self._deliver(channel, link, frame)
        return connection_id

    async def detach_client(self, channel: SessionChannel, connection_id: str) -> None:
        link = channel.clients.pop(connection_id, None)
        if link is None:
            return
        self._audit(
            channel.session_id,
            "client.disconnected",
            {
                "connection_id": link.connection_id,
                "actor": link.actor,
                "clients": len(channel.clients),
            },
        )
        await link.stop()

    async def from_bridge(self, channel: SessionChannel, frame: str) -> None:
        request_id = _server_request_id(frame)
        if request_id is not None:
            channel.pending[request_id] = frame
        for link in list(channel.clients.values()):
            if link.connection_id not in channel.clients:
                continue
            if not link.alive():
                await self._drop_client(channel, link, reason="写协程已退出")
                continue
            await self._deliver(channel, link, frame)

    async def from_client(self, channel: SessionChannel, connection_id: str, frame: str) -> None:
        """客户端帧：响应类按「首个生效」仲裁，重复响应丢弃；其它帧透传桥接。"""
        link = channel.clients.get(connection_id)
        if link is None:
            return  # 慢客户端已被断开，剩余帧直接忽略
        request_id = _client_response_id(frame)
        if request_id is not None:
            pending_frame = channel.pending.pop(request_id, None)
            if pending_frame is None:
                self._audit(
                    channel.session_id,
                    "client.response_duplicate",
                    {
                        "connection_id": connection_id,
                        "actor": link.actor,
                        "request_id": request_id,
                    },
                )
                return
            payload: dict[str, Any] = {
                "connection_id": connection_id,
                "actor": link.actor,
                "request_id": request_id,
            }
            method = _method(pending_frame)
            if method is not None:
                payload["method"] = method
            decision = _decision(frame)
            if decision is not None:
                payload["decision"] = decision
            self._audit(channel.session_id, "client.response", payload)
        bridge = channel.bridge
        if bridge is None:
            raise HubError("会话桥接未连接")
        try:
            await bridge.send_text(frame)
        except Exception as exc:
            channel.bridge = None
            raise HubError("会话桥接发送失败") from exc

    async def _deliver(self, channel: SessionChannel, link: ClientLink, frame: str) -> None:
        if link.enqueue(frame):
            return
        await self._drop_client(channel, link, reason="出站队列已满")

    async def _drop_client(self, channel: SessionChannel, link: ClientLink, *, reason: str) -> None:
        if channel.clients.pop(link.connection_id, None) is None:
            return
        logger.info("会话 %s 客户端 %s 断开：%s", channel.session_id, link.connection_id, reason)
        self._audit(
            channel.session_id,
            "client.dropped",
            {"connection_id": link.connection_id, "actor": link.actor, "reason": reason},
        )
        await link.stop()
        with contextlib.suppress(Exception):
            await link.websocket.close(code=CLOSE_SLOW_CLIENT, reason="client too slow")

    def _audit(self, session_id: str, kind: str, payload: dict[str, Any]) -> None:
        hook = self.on_audit
        if hook is None:
            return
        try:
            hook(session_id, kind, payload)
        except Exception:
            logger.exception("审计事件写入失败：%s/%s", session_id, kind)


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


def _method(frame: str) -> str | None:
    data = _load(frame)
    if isinstance(data, dict):
        method = data.get("method")
        if isinstance(method, str):
            return method
    return None


def _decision(frame: str) -> str | None:
    data = _load(frame)
    if not isinstance(data, dict):
        return None
    result = data.get("result")
    if isinstance(result, dict):
        decision = result.get("decision")
        if isinstance(decision, str):
            return decision
    return None
