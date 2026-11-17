from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from app.bridge.stdio import CodexProcess

FAKE = Path(__file__).resolve().parent / "fakes" / "fake_codex_app_server.py"


async def test_ndjson_roundtrip() -> None:
    process = await CodexProcess.spawn([sys.executable, str(FAKE)])
    frames = process.frames()
    try:
        await process.send(
            json.dumps(
                {
                    "id": 1,
                    "method": "initialize",
                    "params": {"clientInfo": {"name": "test", "version": "0.0.1"}},
                }
            )
        )
        frame = await asyncio.wait_for(anext(frames), timeout=20)
        message: Any = json.loads(frame)
        assert message["id"] == 1
        assert message["result"]["userAgent"] == "fake-codex/0.167.0"
    finally:
        await frames.aclose()
        await process.terminate()


async def test_process_exits_with_codex_status() -> None:
    process = await CodexProcess.spawn([sys.executable, "-c", "raise SystemExit(3)"])
    try:
        assert await asyncio.wait_for(process.wait(), timeout=20) == 3
    finally:
        await process.terminate()
