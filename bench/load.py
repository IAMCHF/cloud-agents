"""L6 简化基准（ bench/，入库可复跑）：admission / density / resume 三模式。

口径与限制见 bench/README.md。零产品代码改动；结果 JSON 落 .local/bench/（不入库）。

用法（仓库根，先起 OpenSandbox server 与控制面，见 docs/tests/本地测试指南.md）：
  set -a; . ./.env; set +a
  uv run --directory control-plane python ../bench/load.py admission
  uv run --directory control-plane python ../bench/load.py density --sessions 8 --duration 180 --duty 0.3
  uv run --directory control-plane python ../bench/load.py resume --turns 10
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import statistics
import subprocess
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urlsplit

# 开发机代理 bypass 含 [::1]，httpx 0.28.1 会崩；基准一律直连（同 tests/conftest.py）。
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

import httpx  # noqa: E402
import websockets  # noqa: E402

CP = os.environ.get("BENCH_CP_URL", "http://127.0.0.1:8000")
WS_BASE = re.sub(r"^http", "ws", CP)
OSB = os.environ.get("OPENSANDBOX_BASE_URL", "http://127.0.0.1:8080")
OSB_KEY = os.environ.get("OPENSANDBOX_API_KEY", "test-key")
AUTH = os.environ["P1_AUTH_TOKEN"]
VOL_ROOT = os.environ["WORKSPACE_HOST_ROOT"].rstrip("/")
IMAGE = os.environ.get("SANDBOX_IMAGE", "cloud-agents/sandbox:0.1.0")
PUBLIC = os.environ.get("PUBLIC_BASE_URL", "http://host.docker.internal:8000")
GATEWAY_HOST = urlsplit(PUBLIC).hostname or "host.docker.internal"
RESULT_DIR = Path(__file__).resolve().parent.parent / ".local" / "bench"
LIMIT = 16 * 1024 * 1024
OSB_HEADERS = {"OPEN-SANDBOX-API-KEY": OSB_KEY}
CP_HEADERS = {"Authorization": f"Bearer {AUTH}"}


def docker_exec(container: str, cmd: str) -> str:
    r = subprocess.run(
        ["docker", "exec", container, "sh", "-c", cmd],
        capture_output=True, text=True, timeout=60,
    )
    return (r.stdout + r.stderr).strip()


def docker_stats() -> dict[str, dict[str, float]]:
    """每容器 CPU%（100%=1 核）与内存 MiB；只取沙箱容器（不含 egress sidecar）。"""
    r = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
        capture_output=True, text=True, timeout=60,
    )
    out: dict[str, dict[str, float]] = {}
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = d.get("Name", "")
        if not name.startswith("sandbox-") or name.startswith("sandbox-egress-"):
            continue
        cpu = float(d.get("CPUPerc", "0%").rstrip("%") or 0)
        mem_raw = d.get("MemUsage", "0MiB / 0MiB").split(" / ")[0]
        m = re.match(r"([\d.]+)(KiB|MiB|GiB)", mem_raw)
        mem = float(m.group(1)) * {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024}[m.group(2)] if m else 0.0
        out[name] = {"cpu_pct": cpu, "mem_mib": mem}
    return out


async def fetch_metrics(http: httpx.AsyncClient) -> dict[str, float]:
    text = (await http.get(f"{CP}/metrics")).text
    out: dict[str, float] = {}
    for line in text.splitlines():
        m = re.match(r"^(cloud_agents_\w+)(?:\{.*\})?\s+([0-9.eE+-]+)$", line)
        if m:
            out[m.group(1)] = out.get(m.group(1), 0.0) + float(m.group(2))
    return out


def pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p))]


class RpcPeer:
    """JSON-RPC 对端：send/recv 注入，WS 与 stdio 共用一套归约。"""

    def __init__(
        self,
        send: Callable[[str], Awaitable[None]],
        recv: Callable[[], Awaitable[str | None]],
    ) -> None:
        self._send = send
        self._recv = recv
        self.pending: dict[int, asyncio.Future] = {}
        self.next_id = 0
        self.deltas: list[str] = []
        self.final: list[str] = []
        self.done = asyncio.Event()
        self.task = asyncio.create_task(self._read())

    async def _read(self) -> None:
        while True:
            try:
                raw = await self._recv()
            except Exception:
                raw = None
            if raw is None:
                break
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if "id" in msg and ("result" in msg or "error" in msg):
                fut = self.pending.pop(msg["id"], None)
                if fut and not fut.done():
                    if "error" in msg:
                        fut.set_exception(RuntimeError(json.dumps(msg["error"], ensure_ascii=False)))
                    else:
                        fut.set_result(msg["result"])
                continue
            m, p = msg.get("method"), msg.get("params") or {}
            if m == "item/agentMessage/delta":
                self.deltas.append(p.get("delta", ""))
            elif m == "item/completed" and (p.get("item") or {}).get("type") == "agentMessage":
                self.final.append(p["item"].get("text", ""))
            elif m == "turn/completed":
                self.done.set()
        for fut in self.pending.values():
            if not fut.done():
                fut.set_exception(RuntimeError("连接已关闭"))
        self.pending.clear()

    async def request(self, method: str, params: dict, timeout: float = 120) -> dict:
        self.next_id += 1
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self.pending[self.next_id] = fut
        await self._send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def turn(self, thread_id: str, text: str, timeout: float = 120) -> tuple[str, float]:
        self.done.clear()
        i0, d0 = len(self.final), len(self.deltas)
        t0 = time.monotonic()
        await self.request("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": text}]})
        await asyncio.wait_for(self.done.wait(), timeout=timeout)
        dt = time.monotonic() - t0
        return ("".join(self.final[i0:]) or "".join(self.deltas[d0:])), dt

    async def close(self) -> None:
        self.task.cancel()


async def ws_peer(session_id: str, token: str, timeout: float = 90) -> tuple[RpcPeer, object]:
    """客户端 WS；桥接冷启动晚于客户端时 hub 回 1013，重试至就绪。"""
    deadline = time.monotonic() + timeout
    while True:
        ws = await websockets.connect(
            f"{WS_BASE}/ws/session/{session_id}?token={token}", max_size=LIMIT
        )

        async def recv() -> str | None:
            try:
                return await ws.recv()
            except websockets.exceptions.ConnectionClosed:
                return None

        peer = RpcPeer(ws.send, recv)
        try:
            await peer.request("initialize", {"clientInfo": {"name": "bench", "version": "0"}}, timeout=15)
        except Exception:
            await peer.close()
            await ws.close()
            if time.monotonic() > deadline:
                raise
            await asyncio.sleep(2)
            continue
        return peer, ws


async def stdio_peer(container: str) -> tuple[RpcPeer, asyncio.subprocess.Process]:
    """docker exec -i 驱动全新 codex app-server（NDJSON over stdio）。"""
    proc = await asyncio.create_subprocess_exec(
        "docker", "exec", "-i", container, "codex", "app-server",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, limit=LIMIT,
    )

    async def send(frame: str) -> None:
        assert proc.stdin is not None
        proc.stdin.write((frame + "\n").encode())
        await proc.stdin.drain()

    async def recv() -> str | None:
        assert proc.stdout is not None
        line = await proc.stdout.readline()
        return line.decode(errors="replace").strip() if line else None

    peer = RpcPeer(send, recv)
    await peer.request("initialize", {"clientInfo": {"name": "bench", "version": "0"}})
    return peer, proc


def codex_config_toml() -> str:
    """复刻桥接 entry._prepare_codex_home 的 provider 配置（exec 驱动不经过桥接）。"""
    lines = []
    for env_key, toml_key in (
        ("CODEX_MODEL", "model"),
        ("CODEX_REASONING_EFFORT", "model_reasoning_effort"),
        ("CODEX_SANDBOX_MODE", "sandbox_mode"),
        ("CODEX_APPROVAL_POLICY", "approval_policy"),
    ):
        v = os.environ.get(env_key, "").strip()
        if v:
            lines.append(f'{toml_key} = "{v}"')
    cw = os.environ.get("CODEX_CONTEXT_WINDOW", "").strip()
    if cw.isdigit():
        lines.append(f"model_context_window = {cw}")
    lines += [
        'model_provider = "cloud"', "", "[model_providers.cloud]", 'name = "cloud"',
        f'base_url = "{PUBLIC}/llm/v1"', 'env_key = "OPENAI_API_KEY"', 'wire_api = "responses"',
    ]
    return "\n".join(lines) + "\n"


def write_codex_config(container: str) -> None:
    b64 = base64.b64encode(codex_config_toml().encode()).decode()
    docker_exec(container, f"mkdir -p /home/agent/.codex && echo {b64} | base64 -d > /home/agent/.codex/config.toml")


def worker_payload(token: str, *, volumes: list | None = None) -> dict:
    env = {
        "CODEX_HOME": "/home/agent/.codex",
        "OPENAI_BASE_URL": f"{PUBLIC}/llm/v1",
        "OPENAI_API_KEY": token,
        "CODEX_SANDBOX_MODE": os.environ.get("CODEX_SANDBOX_MODE", "danger-full-access"),
        "CODEX_APPROVAL_POLICY": os.environ.get("CODEX_APPROVAL_POLICY", "on-request"),
    }
    for k in ("CODEX_MODEL", "CODEX_REASONING_EFFORT", "CODEX_CONTEXT_WINDOW"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    payload: dict = {
        "image": {"uri": IMAGE},
        "entrypoint": ["sleep", "infinity"],
        "env": env,
        "metadata": {"kind": "bench"},
        "timeout": 1800,
        "resourceLimits": {"cpu": "2", "memory": "2Gi"},
        "networkPolicy": {"defaultAction": "deny", "egress": [{"action": "allow", "target": GATEWAY_HOST}]},
    }
    if volumes:
        payload["volumes"] = volumes
    return payload


async def osb_create(http: httpx.AsyncClient, payload: dict) -> str:
    r = await http.post(f"{OSB}/v1/sandboxes", headers=OSB_HEADERS, json=payload)
    r.raise_for_status()
    sid = r.json()["id"]
    for _ in range(60):
        info = (await http.get(f"{OSB}/v1/sandboxes/{sid}", headers=OSB_HEADERS)).json()
        if (info.get("status") or {}).get("state") == "Running":
            return sid
        await asyncio.sleep(1)
    raise RuntimeError(f"沙箱 {sid} 未 Running: {info}")


async def osb_state(http: httpx.AsyncClient, sid: str) -> str:
    info = (await http.get(f"{OSB}/v1/sandboxes/{sid}", headers=OSB_HEADERS)).json()
    return (info.get("status") or {}).get("state", "?")


async def osb_wait_state(http: httpx.AsyncClient, sid: str, want: str, timeout: float = 90) -> float:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if await osb_state(http, sid) == want:
            return time.monotonic() - t0
        await asyncio.sleep(1)
    raise RuntimeError(f"沙箱 {sid} 等待 {want} 超时")


async def cp_create(http: httpx.AsyncClient) -> tuple[dict, float]:
    t0 = time.monotonic()
    r = await http.post(f"{CP}/api/sessions", headers=CP_HEADERS, json={})
    r.raise_for_status()
    return r.json(), time.monotonic() - t0


def save_result(mode: str, data: dict) -> Path:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULT_DIR / f"{mode}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    data["_meta"] = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "image": IMAGE,
        "model": os.environ.get("CODEX_MODEL", ""),
        "docker_host": docker_exec_host_info(),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[result] {path}")
    return path


def docker_exec_host_info() -> dict:
    r = subprocess.run(
        ["docker", "info", "--format", "{{.NCPU}} {{.MemTotal}}"],
        capture_output=True, text=True, timeout=30,
    )
    parts = r.stdout.split()
    return {"ncpu": int(parts[0]), "mem_total_bytes": int(parts[1])} if len(parts) == 2 else {}


async def mode_admission(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient(timeout=180) as http:
        m0 = await fetch_metrics(http)
        a, first_dt = await cp_create(http)
        print(f"[admission] A created in {first_dt:.1f}s: {a['session_id']}")
        gauge_active = (await fetch_metrics(http)).get("cloud_agents_active_sessions", -1)
        r = await http.post(f"{CP}/api/sessions", headers=CP_HEADERS, json={})
        seq_429 = r.status_code == 429
        print(f"[admission] second create: {r.status_code} detail={r.json().get('detail')}")
        burst = await asyncio.gather(*[
            http.post(f"{CP}/api/sessions", headers=CP_HEADERS, json={}) for _ in range(args.burst)
        ])
        burst_429 = sum(1 for x in burst if x.status_code == 429)
        print(f"[admission] burst {args.burst} concurrent: {burst_429}/{args.burst} rejected 429")
        await http.delete(f"{CP}/api/sessions/{a['session_id']}", headers=CP_HEADERS)
        churn: list[float] = []
        last: dict | None = None
        for i in range(args.churn):
            last, dt = await cp_create(http)
            churn.append(dt)
            await http.delete(f"{CP}/api/sessions/{last['session_id']}", headers=CP_HEADERS)
            print(f"[admission] churn {i + 1}: create {dt:.1f}s + delete OK")
        m1 = await fetch_metrics(http)
        gauge_after = m1.get("cloud_agents_active_sessions", -1)
        rej_delta = m1.get("cloud_agents_admission_rejections_total", 0) - m0.get("cloud_agents_admission_rejections_total", 0)
        expected = 1 + args.burst
        ok = seq_429 and burst_429 == args.burst and rej_delta == expected and gauge_active == 1 and gauge_after == 0
        print(f"[admission] rejections delta={rej_delta:.0f} expected={expected}; gauge active={gauge_active:.0f} after={gauge_after:.0f}")
        save_result("admission", {
            "pass": ok, "create_latency_first": first_dt, "churn_create_latencies": churn,
            "sequential_429": seq_429, "burst_429": burst_429, "burst": args.burst,
            "rejections_delta": rej_delta, "rejections_expected": expected,
            "gauge_active": gauge_active, "gauge_after": gauge_after,
        })
        print(f"[RESULT] admission {'PASS' if ok else 'FAIL'}")


async def mode_density(args: argparse.Namespace) -> None:
    n = args.sessions
    workers: list[dict] = []
    anchor: dict | None = None
    anchor_ws = None
    anchor_peer: RpcPeer | None = None
    procs: list[asyncio.subprocess.Process] = []
    async with httpx.AsyncClient(timeout=180) as http:
        try:
            anchor, _ = await cp_create(http)
            anchor_peer, anchor_ws = await ws_peer(anchor["session_id"], anchor["session_token"])
            th = await anchor_peer.request("thread/start", {})
            workers.append({"name": f"sandbox-{anchor['sandbox_id']}", "peer": anchor_peer,
                            "thread": th["thread"]["id"], "kind": "cp-bridge"})
            print(f"[density] anchor (CP bridge path): {anchor['session_id']}")
            payloads = [worker_payload(anchor["session_token"]) for _ in range(n - 1)]
            sids = await asyncio.gather(*[osb_create(http, p) for p in payloads])
            for sid in sids:
                c = f"sandbox-{sid}"
                write_codex_config(c)
                peer, proc = await stdio_peer(c)
                procs.append(proc)
                th = await peer.request("thread/start", {})
                workers.append({"name": c, "peer": peer, "thread": th["thread"]["id"], "kind": "osb-exec"})
            print(f"[density] {len(workers)} workers ready ({n - 1} OSB-direct + 1 CP anchor)")
            m0 = await fetch_metrics(http)
            samples: list[dict] = []
            stop = asyncio.Event()

            async def sampler() -> None:
                while not stop.is_set():
                    samples.append({"t": time.monotonic(), "containers": docker_stats(),
                                    "metrics": await fetch_metrics(http)})
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=args.sample_interval)
                    except TimeoutError:
                        pass

            async def worker_loop(w: dict) -> None:
                lat: list[float] = []
                busy = 0.0
                fails = 0
                deadline = time.monotonic() + args.duration
                while time.monotonic() < deadline:
                    try:
                        _, dt = await w["peer"].turn(w["thread"], "Reply with exactly: ok")
                        lat.append(dt)
                        busy += dt
                        await asyncio.sleep(max(0.5, dt * (1 - args.duty) / args.duty))
                    except Exception as e:
                        fails += 1
                        print(f"[density] {w['name']} turn failed: {e}")
                        await asyncio.sleep(5)
                w["latencies"] = lat
                w["busy_seconds"] = busy
                w["failures"] = fails

            sam = asyncio.create_task(sampler())
            t_start = time.monotonic()
            await asyncio.gather(*[worker_loop(w) for w in workers])
            elapsed = time.monotonic() - t_start
            stop.set()
            await sam
            m1 = await fetch_metrics(http)
            all_lat = [x for w in workers for x in w["latencies"]]
            total_turns = len(all_lat)
            fails = sum(w["failures"] for w in workers)
            per_container: dict[str, dict] = {}
            for name in {k for s in samples for k in s["containers"]}:
                cpus = [s["containers"][name]["cpu_pct"] for s in samples if name in s["containers"]]
                mems = [s["containers"][name]["mem_mib"] for s in samples if name in s["containers"]]
                per_container[name] = {
                    "cpu_avg_pct": round(statistics.mean(cpus), 1), "cpu_max_pct": round(max(cpus), 1),
                    "mem_avg_mib": round(statistics.mean(mems), 1), "mem_max_mib": round(max(mems), 1),
                }
            llm_delta = m1.get("cloud_agents_llm_requests_total", 0) - m0.get("cloud_agents_llm_requests_total", 0)
            busy_frac = statistics.mean(w["busy_seconds"] / elapsed for w in workers)
            ok = fails == 0 and total_turns > 0 and llm_delta >= total_turns and len(samples) >= 3
            print(f"[density] {total_turns} turns in {elapsed:.0f}s, failures={fails}, "
                  f"latency p50={pct(all_lat, 0.5):.2f}s p95={pct(all_lat, 0.95):.2f}s max={max(all_lat or [0]):.2f}s")
            print(f"[density] measured busy fraction={busy_frac:.2f} (target duty={args.duty}); gateway llm delta={llm_delta:.0f}")
            for name, s in per_container.items():
                print(f"[density] {name[:24]}… cpu avg={s['cpu_avg_pct']}% max={s['cpu_max_pct']}% "
                      f"mem avg={s['mem_avg_mib']}MiB max={s['mem_max_mib']}MiB")
            save_result("density", {
                "pass": ok, "sessions": n, "duration_target": args.duration, "duration_actual": elapsed,
                "duty_target": args.duty, "busy_fraction": busy_frac, "total_turns": total_turns,
                "failures": fails, "latency_p50": pct(all_lat, 0.5), "latency_p95": pct(all_lat, 0.95),
                "latency_max": max(all_lat or [0]), "llm_requests_delta": llm_delta,
                "per_container": per_container, "samples": len(samples),
                "workers": [{k: w[k] for k in ("name", "kind", "failures", "busy_seconds")} |
                            {"turns": len(w["latencies"]), "p50": pct(w["latencies"], 0.5)} for w in workers],
            })
            print(f"[RESULT] density {'PASS' if ok else 'FAIL'}")
        finally:
            if anchor_peer:
                await anchor_peer.close()
            if anchor_ws:
                await anchor_ws.close()
            for w in workers:
                if w["kind"] == "osb-exec":
                    await w["peer"].close()
            for p in procs:
                p.terminate()
            for w in workers:
                if w["kind"] == "osb-exec":
                    sid = w["name"].removeprefix("sandbox-")
                    await http.delete(f"{OSB}/v1/sandboxes/{sid}", headers=OSB_HEADERS)
            if anchor:
                await http.delete(f"{CP}/api/sessions/{anchor['session_id']}", headers=CP_HEADERS)
            print("[density] cleanup done")


async def mode_resume(args: argparse.Namespace) -> None:
    k = args.turns
    async with httpx.AsyncClient(timeout=180) as http:
        a, _ = await cp_create(http)
        peer, ws = await ws_peer(a["session_id"], a["session_token"])
        th = await peer.request("thread/start", {})
        tid = th["thread"]["id"]
        turn_lats: list[float] = []
        for i in range(k):
            text, dt = await peer.turn(tid, f"Reply with exactly: ok-{i}")
            turn_lats.append(dt)
            if f"ok-{i}" not in text:
                print(f"[resume] WARN turn {i} text={text!r}")
        print(f"[resume] history built: {k} turns, p50={pct(turn_lats, 0.5):.2f}s")
        sandbox_a = f"sandbox-{a['sandbox_id']}"
        docker_exec(sandbox_a, "echo bench-resume-marker > /workspace/marker.txt")

        # ① 断线重连 + thread/resume（同沙箱，stdio 不断）
        await peer.close()
        await ws.close()
        t0 = time.monotonic()
        peer, ws = await ws_peer(a["session_id"], a["session_token"])
        await peer.request("thread/resume", {"threadId": tid})
        reconnect_dt = time.monotonic() - t0
        print(f"[resume] ① reconnect+resume: {reconnect_dt:.2f}s")

        # ② OSB pause → resume → thread/resume
        t0 = time.monotonic()
        r = await http.post(f"{OSB}/v1/sandboxes/{a['sandbox_id']}/pause", headers=OSB_HEADERS)
        r.raise_for_status()
        pause_dt = await osb_wait_state(http, a["sandbox_id"], "Paused")
        r = await http.post(f"{OSB}/v1/sandboxes/{a['sandbox_id']}/resume", headers=OSB_HEADERS)
        r.raise_for_status()
        run_dt = await osb_wait_state(http, a["sandbox_id"], "Running")
        await peer.close()
        await ws.close()
        peer, ws = await ws_peer(a["session_id"], a["session_token"])
        await peer.request("thread/resume", {"threadId": tid})
        pause_resume_dt = time.monotonic() - t0
        print(f"[resume] ② pause({pause_dt:.1f}s)+resume({run_dt:.1f}s)+thread/resume: {pause_resume_dt:.2f}s")
        await peer.close()
        await ws.close()

        # ③ 冷恢复：状态落卷 → 销毁 A → 新沙箱挂卷 → 全新 codex 磁盘回放
        docker_exec(sandbox_a, "cp -a /home/agent/.codex /workspace/.codex")
        await http.delete(f"{CP}/api/sessions/{a['session_id']}", headers=CP_HEADERS)
        b, _ = await cp_create(http)  # 网关 token 锚点（同 L4 实验）
        a_vol = f"{VOL_ROOT}/{a['session_id']}"
        t0 = time.monotonic()
        rid = await osb_create(http, worker_payload(b["session_token"], volumes=[
            {"name": "workspace", "mountPath": "/workspace", "host": {"path": a_vol}},
            {"name": "codex-home", "mountPath": "/home/agent/.codex", "host": {"path": f"{a_vol}/.codex"}},
        ]))
        create_dt = time.monotonic() - t0
        rc = f"sandbox-{rid}"
        marker = docker_exec(rc, "cat /workspace/marker.txt")
        cx, proc = await stdio_peer(rc)
        t0 = time.monotonic()
        res = await cx.request("thread/resume", {"threadId": tid})
        cold_dt = time.monotonic() - t0
        blob = json.dumps(res, ensure_ascii=False)
        history_ok = f"ok-{k - 1}" in blob
        text, cont_dt = await cx.turn(tid, "Reply with exactly: resumed-ok")
        print(f"[resume] ③ cold: sandbox {create_dt:.1f}s + disk resume {cold_dt:.2f}s "
              f"(history {k} turns verified={history_ok}, resp {len(blob)}B); continuation {cont_dt:.1f}s text={text!r}")
        await cx.close()
        proc.terminate()
        await http.delete(f"{OSB}/v1/sandboxes/{rid}", headers=OSB_HEADERS)
        await http.delete(f"{CP}/api/sessions/{b['session_id']}", headers=CP_HEADERS)
        ok = history_ok and "resumed-ok" in text and marker == "bench-resume-marker"
        save_result("resume", {
            "pass": ok, "history_turns": k, "turn_latency_p50": pct(turn_lats, 0.5),
            "reconnect_resume_seconds": reconnect_dt,
            "pause_resume_seconds": pause_resume_dt, "pause_seconds": pause_dt, "resume_seconds": run_dt,
            "cold_sandbox_create_seconds": create_dt, "cold_disk_resume_seconds": cold_dt,
            "cold_history_verified": history_ok, "cold_response_bytes": len(blob),
            "continuation_seconds": cont_dt, "continuation_text": text,
        })
        print(f"[RESULT] resume {'PASS' if ok else 'FAIL'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("admission", help="同用户单活跃准入 + churn + 拒绝计数")
    p.add_argument("--churn", type=int, default=3)
    p.add_argument("--burst", type=int, default=5)
    p = sub.add_parser("density", help="N 并发占空比真实 turn + 资源/网关采样")
    p.add_argument("--sessions", type=int, default=8)
    p.add_argument("--duration", type=int, default=180)
    p.add_argument("--duty", type=float, default=0.3)
    p.add_argument("--sample-interval", type=float, default=5)
    p = sub.add_parser("resume", help="重连/pause/冷恢复三种 resume 时延（K 轮历史）")
    p.add_argument("--turns", type=int, default=10)
    args = parser.parse_args()
    asyncio.run({"admission": mode_admission, "density": mode_density, "resume": mode_resume}[args.mode](args))


if __name__ == "__main__":
    main()