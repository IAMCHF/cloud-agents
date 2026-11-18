"""端到端桥接集成测试：控制面 WSS + 沙箱侧桥接进程 + 脚本化 codex 替身。"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from websockets.asyncio.client import ClientConnection, connect

from app.bridge.hub import SessionHub
from app.config import Settings
from app.ledger import Database
from app.main import create_app

BASE = Path(__file__).resolve().parents[1]
FAKE = Path(__file__).resolve().parent / "fakes" / "fake_codex_app_server.py"
SESSION_ID = "it-session"
TOKEN = "it-token"


@contextlib.contextmanager
def _serve(app: FastAPI) -> Iterator[str]:
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("uvicorn 未能启动")
        time.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


async def _recv(websocket: ClientConnection, timeout: float = 20.0) -> Any:
    return json.loads(await asyncio.wait_for(websocket.recv(), timeout=timeout))


async def _until(predicate: Callable[[], bool], timeout: float = 20.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("等待条件超时")
        await asyncio.sleep(0.02)


async def test_full_bridge_path_with_client_reconnect(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'integration.db'}",
        public_base_url="http://127.0.0.1:1",
        p1_auth_token="",
    )
    database = Database(settings.database_url)
    await database.create_schema()
    await database.dispose()

    hub = SessionHub()
    hub.create(SESSION_ID, TOKEN, "alice")
    app = create_app(settings=settings, hub=hub)

    with _serve(app) as base:
        env = os.environ.copy()
        env.update(
            {
                "CONTROL_PLANE_URL": base,
                "SESSION_ID": SESSION_ID,
                "SESSION_TOKEN": TOKEN,
                "PYTHONPATH": str(BASE),
                "CODEX_BIN": sys.executable,
                "CODEX_APP_SERVER_ARGS": str(FAKE),
            }
        )
        bridge = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "app.bridge",
            cwd=str(BASE),
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        try:

            def bridge_ready() -> bool:
                channel = hub.get(SESSION_ID)
                return channel is not None and channel.bridge is not None

            await _until(bridge_ready)

            websocket = await connect(
                f"{base}/ws/session/{SESSION_ID}?token={TOKEN}", max_size=None
            )
            try:
                await websocket.send(
                    json.dumps(
                        {
                            "id": 1,
                            "method": "initialize",
                            "params": {"clientInfo": {"name": "integration", "version": "0.0.1"}},
                        }
                    )
                )
                initialized = await _recv(websocket)
                assert initialized["id"] == 1
                assert initialized["result"]["userAgent"].startswith("fake-codex/")

                await websocket.send(
                    json.dumps(
                        {
                            "id": 2,
                            "method": "turn/start",
                            "params": {
                                "threadId": "thr_fake_1",
                                "input": [{"type": "text", "text": "跑一下"}],
                            },
                        }
                    )
                )

                approval: Any = None
                seen: list[str] = []
                for _ in range(12):
                    message = await _recv(websocket)
                    seen.append(str(message.get("method") or f"response:{message.get('id')}"))
                    if message.get("method") == "item/commandExecution/requestApproval":
                        approval = message
                        break
                assert approval is not None, seen
                assert "turn/started" in seen, seen
                assert "item/agentMessage/delta" in seen, seen
            finally:
                await websocket.close()

            # 客户端重连：未决审批由控制面补发。
            await asyncio.sleep(0.2)
            reconnected = await connect(
                f"{base}/ws/session/{SESSION_ID}?token={TOKEN}", max_size=None
            )
            try:
                replayed = await _recv(reconnected)
                assert replayed["id"] == approval["id"], replayed
                await reconnected.send(
                    json.dumps({"id": approval["id"], "result": {"decision": "accept"}})
                )
                completed = False
                for _ in range(12):
                    message = await _recv(reconnected)
                    if message.get("method") == "turn/completed":
                        completed = True
                        break
                assert completed
            finally:
                await reconnected.close()
        finally:
            if bridge.returncode is None:
                bridge.terminate()
            try:
                _, stderr = await asyncio.wait_for(bridge.communicate(), timeout=20)
            except TimeoutError:
                bridge.kill()
                _, stderr = await bridge.communicate()
            if stderr:
                print(stderr.decode(errors="replace"), file=sys.stderr)
