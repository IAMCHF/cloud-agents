from __future__ import annotations

import httpx
import pytest

from app.sandbox.client import (
    OpenSandboxClient,
    OpenSandboxError,
    SandboxSpec,
)


def _spec() -> SandboxSpec:
    return SandboxSpec(
        image="img:test",
        entrypoint=["python", "-m", "app.bridge"],
        env={"A": "1"},
        cpu="2",
        memory="2Gi",
        timeout_seconds=600,
        metadata={"k": "v"},
        volumes=[{"name": "workspace", "mountPath": "/workspace", "host": {"path": "/v/s1"}}],
    )


def test_spec_payload_shape() -> None:
    payload = _spec().to_payload()

    assert payload["image"] == {"uri": "img:test"}
    assert payload["entrypoint"] == ["python", "-m", "app.bridge"]
    assert payload["resourceLimits"] == {"cpu": "2", "memory": "2Gi"}
    assert payload["timeout"] == 600
    assert payload["volumes"][0]["host"]["path"] == "/v/s1"


async def test_wait_until_running_polls_states() -> None:
    states = iter(["Pending", "Pending", "Running"])
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        return httpx.Response(200, json={"id": "sb-1", "status": {"state": next(states)}})

    client = OpenSandboxClient(
        base_url="http://osb", timeout=5, transport=httpx.MockTransport(handler)
    )
    try:
        info = await client.wait_until_running("sb-1", timeout=5, interval=0)
        assert info.state == "Running"
        assert len(requests) == 3
    finally:
        await client.aclose()


async def test_wait_until_running_fails_on_terminal_state() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "sb-1", "status": {"state": "Failed"}})

    client = OpenSandboxClient(
        base_url="http://osb", timeout=5, transport=httpx.MockTransport(handler)
    )
    try:
        with pytest.raises(OpenSandboxError, match="终止态"):
            await client.wait_until_running("sb-1", timeout=5, interval=0)
    finally:
        await client.aclose()


async def test_delete_tolerates_not_found() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "gone"})

    client = OpenSandboxClient(
        base_url="http://osb", timeout=5, transport=httpx.MockTransport(handler)
    )
    try:
        await client.delete("sb-1")
    finally:
        await client.aclose()


async def test_error_response_raises_with_body() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = OpenSandboxClient(
        base_url="http://osb", timeout=5, transport=httpx.MockTransport(handler)
    )
    try:
        with pytest.raises(OpenSandboxError, match="500"):
            await client.get("sb-1")
    finally:
        await client.aclose()
