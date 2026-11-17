"""codex app-server 子进程封装：NDJSON 行协议（每行一个 JSON-RPC 消息）。"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator, Sequence
from pathlib import Path

logger = logging.getLogger(__name__)

# 单条消息上限（大 diff/补丁会超过 64KB 默认值）。
_STREAM_LIMIT = 16 * 1024 * 1024


class CodexProcess:
    """以子进程运行 codex app-server，按行收发帧。"""

    def __init__(self, process: asyncio.subprocess.Process, argv: Sequence[str]) -> None:
        self._process = process
        self.argv = tuple(argv)
        self._write_lock = asyncio.Lock()
        self._stderr_task = asyncio.create_task(self._drain_stderr(), name="codex-stderr")

    @classmethod
    async def spawn(
        cls,
        argv: Sequence[str],
        *,
        env: dict[str, str] | None = None,
        cwd: str | Path | None = None,
    ) -> CodexProcess:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=None if cwd is None else str(cwd),
            limit=_STREAM_LIMIT,
        )
        return cls(process, argv)

    @property
    def pid(self) -> int:
        return self._process.pid

    async def _drain_stderr(self) -> None:
        stream = self._process.stderr
        assert stream is not None
        while True:
            line = await stream.readline()
            if not line:
                return
            logger.info("codex: %s", line.decode(errors="replace").rstrip())

    async def frames(self) -> AsyncGenerator[str, None]:
        """逐行产出 codex stdout 的 JSON-RPC 帧；进程退出时结束。"""
        stream = self._process.stdout
        assert stream is not None
        while True:
            line = await stream.readline()
            if not line:
                return
            frame = line.decode(errors="replace").strip()
            if frame:
                yield frame

    async def send(self, frame: str) -> None:
        stream = self._process.stdin
        if stream is None or stream.is_closing():
            raise BrokenPipeError("codex stdin 已关闭")
        async with self._write_lock:
            stream.write((frame + "\n").encode())
            await stream.drain()

    async def wait(self) -> int:
        return await self._process.wait()

    async def terminate(self, *, timeout: float = 5.0) -> None:
        if self._process.returncode is not None:
            return
        with contextlib.suppress(ProcessLookupError):
            self._process.terminate()
        try:
            await asyncio.wait_for(self._process.wait(), timeout=timeout)
        except TimeoutError:
            logger.warning("codex 未在 %.1fs 内退出，强制结束", timeout)
            with contextlib.suppress(ProcessLookupError):
                self._process.kill()
            await self._process.wait()
        self._stderr_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._stderr_task
