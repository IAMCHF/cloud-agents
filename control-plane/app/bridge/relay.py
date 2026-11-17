"""stdio↔WSS 桥接核心。

传输无关：codex 侧的帧来源/写入函数、连接器都由调用方注入，测试可用内存替身。
职责：双向透传帧、断线缓冲与重连、未决服务端请求（审批）重放。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

Frame = str


class ConnectionClosedError(Exception):
    """桥接传输已关闭（可重连）。"""


class Connection(Protocol):
    async def send(self, frame: Frame) -> None: ...

    def frames(self) -> AsyncIterator[Frame]: ...

    async def close(self) -> None: ...


Connector = Callable[[], Awaitable[Connection]]
Sleeper = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class RelayStats:
    sent: int
    received: int
    reconnects: int
    buffered: int
    replayed: int


class _Outbox:
    """有界出站队列：满时阻塞生产者（对 codex 形成背压），连接断开时积压。"""

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity 必须 >= 1")
        self._items: deque[Frame] = deque()
        self._capacity = capacity
        self._condition = asyncio.Condition()
        self._peak = 0

    @property
    def peak(self) -> int:
        return self._peak

    async def put(self, frame: Frame) -> None:
        async with self._condition:
            while len(self._items) >= self._capacity:
                await self._condition.wait()
            self._items.append(frame)
            self._peak = max(self._peak, len(self._items))
            self._condition.notify_all()

    async def put_front(self, frame: Frame) -> None:
        async with self._condition:
            self._items.appendleft(frame)
            self._condition.notify_all()

    async def get(self) -> Frame:
        async with self._condition:
            while not self._items:
                await self._condition.wait()
            frame = self._items.popleft()
            self._condition.notify_all()
            return frame

    async def get_nowait(self) -> Frame | None:
        async with self._condition:
            if not self._items:
                return None
            frame = self._items.popleft()
            self._condition.notify_all()
            return frame


class Relay:
    """把 codex 的 stdio 帧与一条可重连的双向帧通道对接。"""

    def __init__(
        self,
        *,
        codex_frames: AsyncIterator[Frame],
        send_to_codex: Callable[[Frame], Awaitable[None]],
        connector: Connector,
        max_buffer: int = 1000,
        backoff_initial: float = 0.2,
        backoff_max: float = 10.0,
        jitter_ratio: float = 0.2,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._codex_frames = codex_frames
        self._send_to_codex = send_to_codex
        self._connector = connector
        self._outbox = _Outbox(max_buffer)
        self._pending: dict[str, Frame] = {}
        self._pending_sent: set[str] = set()
        self._connection: Connection | None = None
        self._send_lock = asyncio.Lock()
        self._backoff_initial = backoff_initial
        self._backoff_max = backoff_max
        self._jitter_ratio = jitter_ratio
        self._sleeper: Sleeper = sleeper if sleeper is not None else asyncio.sleep
        self._sent = 0
        self._received = 0
        self._reconnects = 0
        self._replayed = 0

    @property
    def stats(self) -> RelayStats:
        return RelayStats(
            sent=self._sent,
            received=self._received,
            reconnects=self._reconnects,
            buffered=self._outbox.peak,
            replayed=self._replayed,
        )

    async def run(self) -> None:
        """运行至 codex 输出结束（进程退出）。"""
        pump = asyncio.create_task(self._pump_codex(), name="relay-codex")
        connection = asyncio.create_task(self._connection_loop(), name="relay-connection")
        try:
            await pump
        finally:
            connection.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await connection
            await self._close_connection()

    async def _pump_codex(self) -> None:
        async for frame in self._codex_frames:
            if not frame.strip():
                continue
            self._track_server_request(frame)
            await self._outbox.put(frame)

    async def _connection_loop(self) -> None:
        delay = self._backoff_initial
        while True:
            try:
                connection = await self._connector()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # 连接失败按退避重试
                logger.info("桥接连接失败：%s（%.1fs 后重试）", exc, delay)
                await self._sleep(delay)
                delay = min(delay * 2, self._backoff_max)
                continue

            self._connection = connection
            self._reconnects += 1
            delay = self._backoff_initial
            try:
                await self._pump_connection(connection)
            except asyncio.CancelledError:
                raise
            except ConnectionClosedError as exc:
                logger.info("桥接连接关闭：%s", exc)
            except Exception:
                logger.exception("桥接连接异常")
            finally:
                self._connection = None
                with contextlib.suppress(Exception):
                    await connection.close()

            await self._sleep(delay)

    async def _pump_connection(self, connection: Connection) -> None:
        """一条连接上并发收发：任一方向结束或出错即结束本条连接。"""
        sender = asyncio.create_task(self._send_loop(connection), name="relay-send")
        receiver = asyncio.create_task(self._receive_loop(connection), name="relay-receive")
        try:
            await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in (sender, receiver):
                task.cancel()
            await asyncio.gather(sender, receiver, return_exceptions=True)
        for task in (sender, receiver):
            if task.cancelled():
                continue
            error = task.exception()
            if error is not None:
                raise error

    async def _send_loop(self, connection: Connection) -> None:
        # 重连补发未决审批，再持续消费积压/新帧。
        await self._replay_pending(connection)
        while True:
            frame = await self._outbox.get()
            await self._send(connection, frame)

    async def _receive_loop(self, connection: Connection) -> None:
        async for frame in connection.frames():
            self._settle(frame)
            self._received += 1
            await self._send_to_codex(frame)

    async def _replay_pending(self, connection: Connection) -> None:
        """重连补发仍未决的审批请求（原先已发出的）。"""
        for request_id, frame in list(self._pending.items()):
            if request_id in self._pending_sent:
                await self._send(connection, frame)
                self._replayed += 1

    async def _send(self, connection: Connection, frame: Frame) -> None:
        async with self._send_lock:
            await connection.send(frame)
        self._sent += 1
        request_id = _server_request_id(frame)
        if request_id is not None:
            self._pending_sent.add(request_id)

    def _track_server_request(self, frame: Frame) -> None:
        request_id = _server_request_id(frame)
        if request_id is not None:
            self._pending[request_id] = frame

    def _settle(self, frame: Frame) -> None:
        data = _load(frame)
        if not isinstance(data, dict) or "id" not in data or "method" in data:
            return
        request_id = str(data["id"])
        self._pending.pop(request_id, None)
        self._pending_sent.discard(request_id)

    async def _close_connection(self) -> None:
        connection = self._connection
        if connection is None:
            return
        self._connection = None
        with contextlib.suppress(Exception):
            await connection.close()

    async def _sleep(self, delay: float) -> None:
        jitter = delay * self._jitter_ratio
        await self._sleeper(delay + random.uniform(0.0, jitter))


def _load(frame: Frame) -> object:
    try:
        return json.loads(frame)
    except json.JSONDecodeError:
        return None


def _server_request_id(frame: Frame) -> str | None:
    """服务端发起的请求 = 同时带 id 与 method 的 JSON-RPC 消息。"""
    data = _load(frame)
    if isinstance(data, dict) and "id" in data and "method" in data:
        return str(data["id"])
    return None
