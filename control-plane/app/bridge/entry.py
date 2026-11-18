"""沙箱侧桥接进程入口：拉起 codex app-server，把 stdio 帧透传到控制面 WSS。

    python -m app.bridge

环境变量：
    CONTROL_PLANE_URL       控制面基址（必填），如 ws://control-plane:8000
    SESSION_ID              会话 ID（必填）
    SESSION_TOKEN           会话级 token（必填，查询参数传递，勿写日志）
    CODEX_BIN               codex 可执行文件（默认 codex）
    CODEX_APP_SERVER_ARGS   app-server 启动参数（默认 "app-server"）
    WORKSPACE_DIR           codex 工作目录（默认当前目录）
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from app.bridge.relay import Connection, ConnectionClosedError, Relay
from app.bridge.stdio import CodexProcess

logger = logging.getLogger("bridge")


@dataclass(frozen=True)
class BridgeConfig:
    control_plane_url: str
    session_id: str
    session_token: str
    codex_bin: str
    codex_args: tuple[str, ...]
    workspace_dir: str | None

    @classmethod
    def from_env(cls) -> BridgeConfig:
        def required(name: str) -> str:
            value = os.environ.get(name, "").strip()
            if not value:
                raise SystemExit(f"缺少环境变量 {name}")
            return value

        return cls(
            control_plane_url=required("CONTROL_PLANE_URL").rstrip("/"),
            session_id=required("SESSION_ID"),
            session_token=required("SESSION_TOKEN"),
            codex_bin=os.environ.get("CODEX_BIN", "codex"),
            codex_args=tuple(os.environ.get("CODEX_APP_SERVER_ARGS", "app-server").split()),
            workspace_dir=os.environ.get("WORKSPACE_DIR") or None,
        )

    def bridge_url(self) -> str:
        token = quote(self.session_token)
        return f"{self.control_plane_url}/ws/bridge/{self.session_id}?token={token}"


def _prepare_codex_home() -> None:
    """把模型 provider 指向控制面 LLM 网关；token 只经 env_key 引用，不落配置文件。"""
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    if not base_url:
        return
    codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
    config_path = codex_home / "config.toml"
    if config_path.exists():
        return
    codex_home.mkdir(parents=True, exist_ok=True)
    lines = []
    model = os.environ.get("CODEX_MODEL", "").strip()
    if model:
        lines.append(f'model = "{model}"')
    effort = os.environ.get("CODEX_REASONING_EFFORT", "").strip()
    if effort:
        lines.append(f'model_reasoning_effort = "{effort}"')
    context_window = os.environ.get("CODEX_CONTEXT_WINDOW", "").strip()
    if context_window.isdigit():
        lines.append(f"model_context_window = {context_window}")
    lines.extend(
        [
            'model_provider = "cloud"',
            "",
            "[model_providers.cloud]",
            'name = "cloud"',
            f'base_url = "{base_url}"',
            'env_key = "OPENAI_API_KEY"',
            # codex 0.167 起只支持 Responses API（chat wire_api 已移除）。
            'wire_api = "responses"',
        ]
    )
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("已写入 codex provider 配置 %s", config_path)


class _WebSocketConnection:
    def __init__(self, websocket: ClientConnection) -> None:
        self._websocket = websocket

    async def send(self, frame: str) -> None:
        try:
            await self._websocket.send(frame)
        except ConnectionClosed as exc:
            raise ConnectionClosedError(str(exc)) from exc

    async def frames(self) -> AsyncIterator[str]:
        try:
            async for message in self._websocket:
                if isinstance(message, bytes):
                    yield message.decode(errors="replace")
                else:
                    yield message
        except ConnectionClosed as exc:
            raise ConnectionClosedError(str(exc)) from exc

    async def close(self) -> None:
        with contextlib.suppress(ConnectionClosed):
            await self._websocket.close()


async def _run(config: BridgeConfig) -> int:
    _prepare_codex_home()
    process = await CodexProcess.spawn(
        [config.codex_bin, *config.codex_args],
        cwd=config.workspace_dir,
    )
    logger.info("codex 已启动 pid=%s", process.pid)

    async def connector() -> Connection:
        websocket = await connect(
            config.bridge_url(),
            max_size=None,
            open_timeout=10,
            ping_interval=20,
            ping_timeout=20,
        )
        logger.info("已连接控制面 %s", config.control_plane_url)
        return _WebSocketConnection(websocket)

    relay = Relay(
        codex_frames=process.frames(),
        send_to_codex=process.send,
        connector=connector,
    )
    try:
        await relay.run()
    finally:
        stats = relay.stats
        logger.info(
            "桥接结束 sent=%s received=%s reconnects=%s peak_buffer=%s replayed=%s",
            stats.sent,
            stats.received,
            stats.reconnects,
            stats.buffered,
            stats.replayed,
        )
        await process.terminate()
    return await process.wait()


async def _main() -> int:
    config = BridgeConfig.from_env()
    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    if task is not None:
        with contextlib.suppress(NotImplementedError):
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, task.cancel)
    try:
        return await _run(config)
    except asyncio.CancelledError:
        logger.info("桥接进程收到终止信号")
        return 0


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("BRIDGE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    sys.exit(asyncio.run(_main()))
