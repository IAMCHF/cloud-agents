#!/usr/bin/env python3
"""脚本化 codex app-server 替身，供桥接/控制面集成测试使用（不连真实模型）。

行为：
- initialize / thread/start / thread/resume / turn/start 返回固定的合法 JSON-RPC 结果；
- turn/start 后依次发出 turn/started、item/started、agentMessage 增量，再发起一次命令审批请求；
- 收到审批响应后发出 item/completed 与 turn/completed；
- 未知方法返回 -32601。
"""

from __future__ import annotations

import json
import sys

THREAD_ID = "thr_fake_1"
TURN_ID = "turn_fake_1"
ITEM_ID = "item_fake_1"
APPROVAL_ID = "approval_fake_1"

THREAD = {
    "id": THREAD_ID,
    "cwd": "/workspace",
    "createdAt": 0,
    "cliVersion": "0.167.0",
    "status": "idle",
    "items": [],
}
TURN = {"id": TURN_ID, "items": [], "status": "inProgress"}
TURN_DONE = {"id": TURN_ID, "items": [], "status": "completed"}


def emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def respond(request_id: object, value: dict[str, object]) -> None:
    emit({"id": request_id, "result": value})


def notify(method: str, params: dict[str, object]) -> None:
    emit({"method": method, "params": params})


def main() -> int:
    approval_pending: str | None = None
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        message = json.loads(raw)
        method = message.get("method")
        request_id = message.get("id")

        if approval_pending is not None and method is None and str(request_id) == approval_pending:
            approval_pending = None
            notify(
                "item/completed",
                {
                    "threadId": THREAD_ID,
                    "turnId": TURN_ID,
                    "completedAtMs": 0,
                    "item": {
                        "id": ITEM_ID,
                        "type": "agentMessage",
                        "text": "命令已批准，任务完成。",
                    },
                },
            )
            notify("turn/completed", {"threadId": THREAD_ID, "turn": TURN_DONE})
            continue

        if method is None:
            continue  # 其它响应（例如中断确认），忽略

        if method == "initialize":
            respond(
                request_id,
                {
                    "userAgent": "fake-codex/0.167.0",
                    "codexHome": "/tmp/fake-codex-home",
                    "platformFamily": "unix",
                    "platformOs": "linux",
                },
            )
        elif method == "thread/list":
            respond(request_id, {"data": []})
        elif method in {"thread/start", "thread/resume"}:
            respond(request_id, {"thread": THREAD})
        elif method == "turn/start":
            respond(request_id, {"turn": TURN})
            notify("turn/started", {"threadId": THREAD_ID, "turn": TURN})
            notify(
                "item/started",
                {
                    "threadId": THREAD_ID,
                    "turnId": TURN_ID,
                    "startedAtMs": 0,
                    "item": {"id": ITEM_ID, "type": "agentMessage", "text": ""},
                },
            )
            notify(
                "item/agentMessage/delta",
                {
                    "threadId": THREAD_ID,
                    "turnId": TURN_ID,
                    "itemId": ITEM_ID,
                    "delta": "正在执行任务…",
                },
            )
            notify(
                "turn/diff/updated",
                {
                    "threadId": THREAD_ID,
                    "turnId": TURN_ID,
                    "diff": "--- a/demo.txt\n+++ b/demo.txt\n@@ -1 +1 @@\n-old\n+hello",
                },
            )
            notify(
                "turn/plan/updated",
                {
                    "threadId": THREAD_ID,
                    "turnId": TURN_ID,
                    "plan": [
                        {"status": "completed", "step": "定位问题"},
                        {"status": "inProgress", "step": "执行命令"},
                    ],
                },
            )
            approval_pending = APPROVAL_ID
            emit(
                {
                    "id": APPROVAL_ID,
                    "method": "item/commandExecution/requestApproval",
                    "params": {
                        "threadId": THREAD_ID,
                        "turnId": TURN_ID,
                        "itemId": ITEM_ID,
                        "startedAtMs": 0,
                        "command": "/bin/echo hello",
                        "cwd": "/workspace",
                        "reason": "需要执行命令以完成任务",
                    },
                }
            )
        elif method == "turn/interrupt":
            respond(request_id, {})
        else:
            emit(
                {"id": request_id, "error": {"code": -32601, "message": f"unknown method {method}"}}
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
