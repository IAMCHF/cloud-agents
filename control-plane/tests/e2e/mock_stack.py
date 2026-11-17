"""E2E mock 链路：控制面 + 桥接进程 + fake codex（无沙箱、无真实 LLM）。

给 Playwright 的 webServer 使用；收到 SIGTERM 后结束桥接并退出。
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys
import tempfile
from pathlib import Path

import uvicorn

BASE = Path(__file__).resolve().parents[2]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from app.bridge.hub import SessionHub  # noqa: E402 - 需要先注入仓库根到 sys.path
from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

SESSION_ID = "e2e-session"
TOKEN = "e2e-token"
PORT = int(os.environ.get("E2E_CONTROL_PLANE_PORT", "8800"))
FAKE = Path(__file__).resolve().parents[1] / "fakes" / "fake_codex_app_server.py"


async def _main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="cloud-agents-e2e-"))
    settings = Settings(
        public_base_url=f"http://127.0.0.1:{PORT}",
        p1_auth_token="e2e-owner",
        opensandbox_base_url="http://127.0.0.1:1",
        database_url=f"sqlite+aiosqlite:///{workdir / 'ledger.db'}",
        workspace_host_root=str(workdir / "volumes"),
    )
    hub = SessionHub()
    hub.create(SESSION_ID, TOKEN, "e2e-user")
    app = create_app(settings=settings, hub=hub)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    serve_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)

    env = os.environ.copy()
    env.update(
        {
            "CONTROL_PLANE_URL": f"ws://127.0.0.1:{PORT}",
            "SESSION_ID": SESSION_ID,
            "SESSION_TOKEN": TOKEN,
            "PYTHONPATH": str(BASE),
            "CODEX_BIN": sys.executable,
            "CODEX_APP_SERVER_ARGS": str(FAKE),
            "CODEX_HOME": str(workdir / "codex-home"),
        }
    )
    bridge = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.bridge",
        cwd=str(BASE),
        env=env,
        stdout=asyncio.subprocess.DEVNULL,
    )

    print(f"E2E stack ready: control-plane={PORT} session={SESSION_ID}", flush=True)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    try:
        await stop.wait()
    finally:
        if bridge.returncode is None:
            bridge.terminate()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(bridge.wait(), timeout=10)
        server.should_exit = True
        await serve_task
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
