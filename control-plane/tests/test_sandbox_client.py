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
    assert "networkPolicy" not in payload


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


def _execd_client(execd: httpx.MockTransport) -> OpenSandboxClient:
    """OpenSandbox 主 API 返回直连 endpoint；execd 请求走注入的 MockTransport。"""

    def osb_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/sandboxes/sb-1/endpoints/44772":
            return httpx.Response(200, json={"endpoint": "execd.local:44772"})
        return httpx.Response(404, json={"error": "not found"})

    return OpenSandboxClient(
        base_url="http://osb",
        execd_token="secret",
        timeout=5,
        transport=httpx.MockTransport(osb_handler),
        execd_transport=execd,
    )


async def test_execd_methods_use_direct_endpoint_and_token() -> None:
    seen: list[httpx.Request] = []

    def execd_handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path == "/directories/list":
            return httpx.Response(200, json=[{"path": "/workspace/a", "type": "file"}])
        if path == "/files/download":
            return httpx.Response(200, content=b"hello")
        if path == "/pty" and request.method == "POST":
            return httpx.Response(200, json={"session_id": "pty-1"})
        if path == "/pty/pty-1" and request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(404)

    client = _execd_client(httpx.MockTransport(execd_handler))
    try:
        entries = await client.execd_list_directory("sb-1", "/workspace")
        assert entries == [{"path": "/workspace/a", "type": "file"}]
        assert await client.execd_read_file("sb-1", "/workspace/a") == b"hello"
        pty_id = await client.execd_create_pty("sb-1")
        assert pty_id == "pty-1"
        await client.execd_delete_pty("sb-1", pty_id)
    finally:
        await client.aclose()

    assert all(request.headers["X-EXECD-ACCESS-TOKEN"] == "secret" for request in seen)
    assert seen[0].url.params["path"] == "/workspace"


async def test_execd_errors_surface_and_delete_is_best_effort() -> None:
    def execd_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/directories/list":
            return httpx.Response(200, json={"not": "a list"})
        if path == "/files/download":
            return httpx.Response(200, content=b"x" * (512 * 1024 + 1))
        if path == "/pty":
            return httpx.Response(500, text="boom")
        return httpx.Response(500, text="boom")

    client = _execd_client(httpx.MockTransport(execd_handler))
    try:
        with pytest.raises(OpenSandboxError, match="列目录响应不是数组"):
            await client.execd_list_directory("sb-1", "/workspace")
        with pytest.raises(OpenSandboxError, match="预览上限"):
            await client.execd_read_file("sb-1", "/workspace/big")
        with pytest.raises(OpenSandboxError, match="创建终端失败"):
            await client.execd_create_pty("sb-1")
        await client.execd_delete_pty("sb-1", "pty-missing")
    finally:
        await client.aclose()
