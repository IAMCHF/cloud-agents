from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable

from app.bridge.relay import Connection, Relay

APPROVAL = json.dumps(
    {
        "id": "approval-1",
        "method": "item/commandExecution/requestApproval",
        "params": {"threadId": "t", "turnId": "u", "itemId": "i", "startedAtMs": 0},
    }
)
NOTIFICATION = json.dumps({"method": "turn/started", "params": {"threadId": "t"}})
CLIENT_RESPONSE = json.dumps({"id": "approval-1", "result": {"decision": "accept"}})


class FakeConnection:
    def __init__(self) -> None:
        self.incoming: asyncio.Queue[str | None] = asyncio.Queue()
        self.sent: list[str] = []
        self.closed = False

    async def send(self, frame: str) -> None:
        self.sent.append(frame)

    async def frames(self) -> AsyncIterator[str]:
        while True:
            item = await self.incoming.get()
            if item is None:
                return
            yield item

    async def close(self) -> None:
        self.closed = True


class CodexSource:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def frames(self) -> AsyncIterator[str]:
        while True:
            item = await self.queue.get()
            if item is None:
                return
            yield item


async def _until(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("等待条件超时")
        await asyncio.sleep(0.01)


async def _no_sleep(_: float) -> None:
    return None


async def test_forwards_frames_both_directions() -> None:
    source = CodexSource()
    connection = FakeConnection()
    to_codex: list[str] = []

    async def send_to_codex(frame: str) -> None:
        to_codex.append(frame)

    async def connector() -> Connection:
        return connection

    relay = Relay(
        codex_frames=source.frames(),
        send_to_codex=send_to_codex,
        connector=connector,
        sleeper=_no_sleep,
    )
    task = asyncio.create_task(relay.run())
    await source.queue.put(NOTIFICATION)
    await _until(lambda: bool(connection.sent))
    assert json.loads(connection.sent[0])["method"] == "turn/started"

    await connection.incoming.put(CLIENT_RESPONSE)
    await _until(lambda: bool(to_codex))
    assert to_codex[0] == CLIENT_RESPONSE

    await source.queue.put(None)
    await asyncio.wait_for(task, timeout=5)
    assert connection.closed


async def test_replays_pending_approval_after_reconnect() -> None:
    source = CodexSource()
    first = FakeConnection()
    second = FakeConnection()
    attempts = 0
    to_codex: list[str] = []

    async def send_to_codex(frame: str) -> None:
        to_codex.append(frame)

    async def connector() -> Connection:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return first
        if attempts == 2:
            raise OSError("control plane 暂不可达")
        return second

    relay = Relay(
        codex_frames=source.frames(),
        send_to_codex=send_to_codex,
        connector=connector,
        sleeper=_no_sleep,
    )
    task = asyncio.create_task(relay.run())
    await source.queue.put(APPROVAL)
    await _until(lambda: bool(first.sent))

    # 连接断开 → 重连一次失败 → 第二次重连成功，未决审批需补发
    await first.incoming.put(None)
    await _until(lambda: bool(second.sent), timeout=10)
    assert second.sent == [APPROVAL]
    assert relay.stats.reconnects == 2
    assert relay.stats.replayed == 1

    await second.incoming.put(CLIENT_RESPONSE)
    await _until(lambda: bool(to_codex))

    await source.queue.put(None)
    await asyncio.wait_for(task, timeout=5)


async def test_backpressures_when_buffer_full() -> None:
    source = CodexSource()
    connection = FakeConnection()
    gate = asyncio.Event()
    attempts = 0

    async def send_to_codex(_: str) -> None:
        return None

    async def connector() -> Connection:
        nonlocal attempts
        attempts += 1
        if not gate.is_set():
            raise OSError("offline")
        return connection

    async def wait_gate(_: float) -> None:
        await gate.wait()

    relay = Relay(
        codex_frames=source.frames(),
        send_to_codex=send_to_codex,
        connector=connector,
        max_buffer=2,
        sleeper=wait_gate,
    )
    task = asyncio.create_task(relay.run())
    await source.queue.put(NOTIFICATION)
    await source.queue.put(NOTIFICATION)
    await source.queue.put(NOTIFICATION)  # 第三条被有界队列挡住
    await asyncio.sleep(0.1)
    assert relay.stats.buffered == 2
    assert not connection.sent

    gate.set()
    await _until(lambda: len(connection.sent) == 3, timeout=10)
    assert connection.sent == [NOTIFICATION, NOTIFICATION, NOTIFICATION]

    await source.queue.put(None)
    await asyncio.wait_for(task, timeout=5)


async def test_connection_attempts_are_awaited_by_relay() -> None:
    """连接器抛错不应结束 relay：codex 帧继续入队，等连接恢复后发出。"""
    source = CodexSource()
    connection = FakeConnection()
    attempts = 0

    async def send_to_codex(_: str) -> None:
        return None

    async def connector() -> Connection:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OSError("offline")
        return connection

    relay = Relay(
        codex_frames=source.frames(),
        send_to_codex=send_to_codex,
        connector=connector,
        sleeper=_no_sleep,
    )
    task = asyncio.create_task(relay.run())
    await source.queue.put(NOTIFICATION)
    await _until(lambda: bool(connection.sent), timeout=10)
    assert attempts == 3

    await source.queue.put(None)
    await asyncio.wait_for(task, timeout=5)


async def test_reuses_initialize_result_for_late_clients() -> None:
    source = CodexSource()
    connection = FakeConnection()
    to_codex: list[str] = []

    async def send_to_codex(frame: str) -> None:
        to_codex.append(frame)

    async def connector() -> Connection:
        return connection

    relay = Relay(
        codex_frames=source.frames(),
        send_to_codex=send_to_codex,
        connector=connector,
        sleeper=_no_sleep,
    )
    task = asyncio.create_task(relay.run())
    try:
        await _until(lambda: len(connection.sent) == 0)
        connection.incoming.put_nowait(json.dumps({"id": 1, "method": "initialize", "params": {}}))
        await _until(lambda: len(to_codex) == 1)

        source.queue.put_nowait(json.dumps({"id": 1, "result": {"userAgent": "codex/0.167.0"}}))
        await _until(lambda: any("codex/0.167.0" in frame for frame in connection.sent))

        connection.incoming.put_nowait(json.dumps({"id": 2, "method": "initialize", "params": {}}))
        await _until(lambda: any('"id": 2' in frame for frame in connection.sent))

        assert len(to_codex) == 1, "重复 initialize 不应再次转发给 codex"
        cached = [json.loads(frame) for frame in connection.sent if '"id": 2' in frame]
        assert cached[0]["result"] == {"userAgent": "codex/0.167.0"}
    finally:
        connection.incoming.put_nowait(None)
        source.queue.put_nowait(None)
        await asyncio.wait_for(task, timeout=5)
