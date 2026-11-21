"""P3 T7 控制面 150 路仿真：假 OpenSandbox + 假 codex 桥接，驱动真实控制面。

不启真实沙箱/模型：每个会话由一个假桥接 WS 扮演沙箱内 codex，客户端走原生 JSON-RPC。
验证：180 路建会话、桥接/客户端 WS、turn 流式、审批首响应、指标活跃 gauge。

用法（仓库根）：
  uv run --directory control-plane python ../bench/sim_control_plane.py --sessions 150
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

import httpx  # noqa: E402
import uvicorn  # noqa: E402
import websockets  # noqa: E402
from fastapi import FastAPI, Response  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "control-plane"))

from app.auth import OidcError, OidcProvider, Principal  # noqa: E402
from app.config import Settings  # noqa: E402
from app.ledger import Database  # noqa: E402
from app.main import create_app  # noqa: E402

ACCESS_PREFIX = "sim-user"
OSB_PORT = 18091
CP_PORT = 18092
OSB_URL = f"http://127.0.0.1:{OSB_PORT}"
CP_URL = f"http://127.0.0.1:{CP_PORT}"
WS_URL = f"ws://127.0.0.1:{CP_PORT}"
RESULT_DIR = Path(__file__).resolve().parent.parent / ".local" / "bench"


class FakeOidcProvider(OidcProvider):
    """OIDC 替身：bearer token 直接作为 subject，便于 150 个不同属主各建一个会话。"""

    def __init__(self) -> None:
        super().__init__(issuer="https://sim.invalid")

    async def verify(self, token: str) -> Principal:
        if not token:
            raise OidcError("missing token")
        return Principal(subject=token, username=token, tenant_id="sim")


class FakeOpenSandbox:
    """最小生命周期 API：创建即 Running，删除 204。"""

    def __init__(self) -> None:
        self.counter = 0

    def app(self) -> FastAPI:
        app = FastAPI()

        @app.post("/v1/sandboxes")
        async def create() -> dict[str, Any]:
            self.counter += 1
            return {"id": f"sim-{self.counter}", "status": {"state": "Pending"}}

        @app.get("/v1/sandboxes/{sandbox_id}")
        async def get(sandbox_id: str) -> dict[str, Any]:
            return {"id": sandbox_id, "status": {"state": "Running"}}

        @app.delete("/v1/sandboxes/{sandbox_id}")
        async def delete(sandbox_id: str) -> Response:
            return Response(status_code=204)

        return app


class FakeBridge:
    """沙箱侧 codex 替身：应答 initialize/thread/turn，发起一次审批并等待客户端决定。"""

    def __init__(self, index: int) -> None:
        self.index = index
        self.ws: Any = None
        self.decision = asyncio.Event()
        self.approvals: list[str] = []
        self.task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        assert self.ws is not None
        async for raw in self.ws:
            message = json.loads(raw)
            if "id" in message and ("result" in message or "error" in message):
                self.approvals.append(str(message["id"]))
                self.decision.set()
                continue
            method = message.get("method")
            request_id = message.get("id")
            if method == "initialize":
                await self._reply(request_id, {"serverInfo": {"name": "sim-codex", "version": "0"}})
            elif method in {"thread/start", "thread/resume"}:
                await self._reply(request_id, {"thread": {"id": f"thr-{self.index}"}})
            elif method == "turn/start":
                assert self.task is None
                self.task = asyncio.create_task(self._turn(request_id))

    async def _turn(self, request_id: Any) -> None:
        await self._reply(request_id, {"turn": {"id": f"turn-{self.index}"}})
        await self._notify("turn/started", {"turnId": f"turn-{self.index}"})
        await self._send(
            {
                "id": f"appr-{self.index}",
                "method": "item/commandExecution/requestApproval",
                "params": {"command": "pnpm test", "cwd": "/workspace"},
            }
        )
        await asyncio.wait_for(self.decision.wait(), timeout=10)
        for chunk in ("仿真", "完成"):
            await self._notify("item/agentMessage/delta", {"itemId": "item-1", "delta": chunk})
        await self._notify(
            "item/completed",
            {"item": {"id": "item-1", "type": "agentMessage", "text": "仿真完成"}},
        )
        await self._notify("turn/completed", {"turnId": f"turn-{self.index}"})

    async def _reply(self, request_id: Any, result: dict[str, Any]) -> None:
        await self._send({"id": request_id, "result": result})

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
        await self._send({"method": method, "params": params})

    async def _send(self, payload: dict[str, Any]) -> None:
        await self.ws.send(json.dumps(payload))


class ClientPeer:
    """原生 JSON-RPC 客户端；服务端请求（审批）自动 accept。"""

    def __init__(self, ws: Any) -> None:
        self.ws = ws
        self.next_id = 0
        self.pending: dict[str, asyncio.Future[Any]] = {}
        self.notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.approvals = 0
        self.task = asyncio.create_task(self._read())

    async def _read(self) -> None:
        async for raw in self.ws:
            message = json.loads(raw)
            if "id" in message and "method" in message:
                self.approvals += 1
                await self.ws.send(
                    json.dumps({"id": message["id"], "result": {"decision": "accept"}})
                )
                continue
            if "id" in message and ("result" in message or "error" in message):
                future = self.pending.pop(str(message["id"]), None)
                if future is not None and not future.done():
                    if "error" in message:
                        future.set_exception(RuntimeError(str(message["error"])))
                    else:
                        future.set_result(message["result"])
                continue
            await self.notifications.put(message)

    async def request(self, method: str, params: dict[str, Any], timeout: float = 30) -> Any:
        self.next_id += 1
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self.pending[str(self.next_id)] = future
        await self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        return await asyncio.wait_for(future, timeout=timeout)

    async def wait_method(self, method: str, timeout: float = 30) -> dict[str, Any]:
        while True:
            message = await asyncio.wait_for(self.notifications.get(), timeout=timeout)
            if message.get("method") == method:
                return message

    async def close(self) -> None:
        self.task.cancel()
        await self.ws.close()


async def run_session(index: int, session: dict[str, str]) -> dict[str, Any]:
    session_id = session["session_id"]
    token = session["session_token"]
    access_token = f"{ACCESS_PREFIX}-{index}"
    bridge_ws = await websockets.connect(
        f"{WS_URL}/ws/bridge/{session_id}?token={token}", max_size=16 * 1024 * 1024
    )
    bridge = FakeBridge(index)
    bridge.ws = bridge_ws
    bridge_task = asyncio.create_task(bridge.run())
    client_ws = await websockets.connect(
        f"{WS_URL}/ws/session/{session_id}?token={token}&access_token={access_token}",
        max_size=16 * 1024 * 1024,
    )
    peer = ClientPeer(client_ws)
    try:
        await peer.request("initialize", {"clientInfo": {"name": "sim", "version": "0"}})
        thread = await peer.request("thread/start", {})
        turn_started = time.monotonic()
        await peer.request(
            "turn/start",
            {"threadId": thread["thread"]["id"], "input": [{"type": "text", "text": "hi"}]},
        )
        await peer.wait_method("turn/completed")
        turn_seconds = time.monotonic() - turn_started
        return {
            "ok": True,
            "turn_seconds": turn_seconds,
            "approvals": peer.approvals,
            "bridge_decisions": len(bridge.approvals),
        }
    finally:
        await peer.close()
        if bridge.task is not None:
            bridge.task.cancel()
        bridge_task.cancel()
        await bridge_ws.close()


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * p))]


async def serve(app: Any, port: int) -> tuple[uvicorn.Server, asyncio.Task[None]]:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.02)
    return server, task


async def main(sessions: int) -> int:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    osb = FakeOpenSandbox()
    osb_server, osb_task = await serve(osb.app(), OSB_PORT)
    settings = Settings(
        public_base_url=CP_URL,
        auth_mode="oidc",
        oidc_issuer="https://sim.invalid",
        oidc_client_id="sim-client",
        oidc_default_tenant="sim",
        p1_owner="sim-user",
        opensandbox_base_url=OSB_URL,
        sandbox_image="sim:0",
        sandbox_start_timeout_seconds=10,
        max_active_sessions=1000,
        tenant_default_max_active_sessions=1000,
        tenant_default_monthly_token_budget=0,
        volume_backend="host",
        workspace_host_root=str(RESULT_DIR / "volumes"),
        database_url=f"sqlite+aiosqlite:///{RESULT_DIR / f'sim-{stamp}.db'}",
        archive_enabled=False,
        idle_sweeper_enabled=False,
        preview_base_domain="",
    )
    database = Database(settings.database_url)
    await database.create_schema()
    await database.dispose()
    cp = create_app(settings=settings, oidc_provider=FakeOidcProvider())
    cp_server, cp_task = await serve(cp, CP_PORT)
    failures: list[str] = []
    created: list[dict[str, str]] = []
    create_latencies: list[float] = []
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            for index in range(sessions):
                headers = {"Authorization": f"Bearer {ACCESS_PREFIX}-{index}"}
                started = time.monotonic()
                response = await http.post(f"{CP_URL}/api/sessions", headers=headers, json={})
                if response.status_code != 200:
                    failures.append(f"create {index}: HTTP {response.status_code} {response.text[:200]}")
                    break
                created.append(response.json())
                create_latencies.append(time.monotonic() - started)
            print(f"[sim] created {len(created)}/{sessions} sessions")

            wall_started = time.monotonic()
            gathered = await asyncio.gather(
                *[run_session(i, session) for i, session in enumerate(created)],
                return_exceptions=True,
            )
            wall_seconds = time.monotonic() - wall_started
            for index, item in enumerate(gathered):
                if isinstance(item, BaseException):
                    failures.append(f"session {index}: {item!r}")
                else:
                    results.append(item)

            metrics_text = (await http.get(f"{CP_URL}/metrics")).text
            gauge = next(
                (
                    float(line.split()[-1])
                    for line in metrics_text.splitlines()
                    if line.startswith("cloud_agents_active_sessions ")
                ),
                0.0,
            )
            print(f"[sim] active gauge={gauge:.0f} metrics_bytes={len(metrics_text)}")

            for session in created:
                await http.delete(f"{CP_URL}/api/sessions/{session['session_id']}", headers=headers)

        turns = [item["turn_seconds"] for item in results]
        approvals = sum(item["approvals"] for item in results)
        bridge_decisions = sum(item["bridge_decisions"] for item in results)
        ok = (
            len(created) == sessions
            and len(results) == sessions
            and not failures
            and approvals == sessions
            and bridge_decisions == sessions
            and gauge == sessions
        )
        report = {
            "pass": ok,
            "sessions": sessions,
            "created": len(created),
            "turns_ok": len(results),
            "failures": failures,
            "create_p50_seconds": pct(create_latencies, 0.5),
            "turn_p50_seconds": pct(turns, 0.5),
            "turn_p95_seconds": pct(turns, 0.95),
            "turn_max_seconds": max(turns or [0]),
            "wall_seconds": wall_seconds,
            "approvals_client": approvals,
            "approvals_bridge": bridge_decisions,
            "active_gauge": gauge,
        }
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        path = RESULT_DIR / f"control-plane-{sessions}-{time.strftime('%Y%m%d-%H%M%S')}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[result] {path}")
        print(
            f"[sim] turns={len(results)} p50={report['turn_p50_seconds']:.3f}s "
            f"p95={report['turn_p95_seconds']:.3f}s wall={wall_seconds:.1f}s"
        )
        print(f"[RESULT] sim {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        cp_server.should_exit = True
        osb_server.should_exit = True
        await asyncio.gather(cp_task, osb_task, return_exceptions=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=150)
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.sessions)))
