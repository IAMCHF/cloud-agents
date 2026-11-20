"""通用 WebSocket 双向转发：浏览器 ↔ 控制面 ↔ 沙箱内服务。

终端与预览共用；二进制帧可按需过滤（如 execd PTY 的 0x01/0x03 帧头）。
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


async def relay_websockets(
    websocket: WebSocket,
    upstream: Any,
    *,
    to_browser_bytes: Callable[[bytes], bytes | None] | None = None,
) -> None:
    """双向转发直到任一侧断开；`to_browser_bytes` 返回 None 表示丢弃该帧。"""

    async def browser_to_upstream() -> None:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            text = message.get("text")
            if text is not None:
                await upstream.send(text)
                continue
            data = message.get("bytes")
            if data is not None:
                await upstream.send(data)

    async def upstream_to_browser() -> None:
        async for message in upstream:
            if isinstance(message, bytes):
                data = message if to_browser_bytes is None else to_browser_bytes(message)
                if data is not None:
                    await websocket.send_bytes(data)
            else:
                await websocket.send_text(message)

    tasks = [
        asyncio.create_task(browser_to_upstream(), name="ws-browser"),
        asyncio.create_task(upstream_to_browser(), name="ws-upstream"),
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
        if websocket.client_state == WebSocketState.CONNECTED:
            with contextlib.suppress(Exception):
                await websocket.close()
        logger.debug("WebSocket 转发结束")
