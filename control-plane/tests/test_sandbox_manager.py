from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.bridge.hub import SessionHub
from app.config import Settings
from app.ledger import Ledger
from app.sandbox import AdmissionRejectedError, OpenSandboxClient, SandboxManager
from app.sandbox.client import OpenSandboxError
from tests.fakes.opensandbox import FakeOpenSandbox


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        public_base_url="http://cp:8000",
        opensandbox_base_url="http://osb",
        sandbox_image="img:test",
        sandbox_cpu="2",
        sandbox_memory="2Gi",
        sandbox_timeout_seconds=900,
        sandbox_start_timeout_seconds=5,
        max_active_sessions=4,
        workspace_host_root=str(tmp_path / "volumes"),
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'unused.db'}",
        llm_upstream_base_url="",
    )


def _manager(
    tmp_path: Path,
    ledger: Ledger,
    osb: FakeOpenSandbox,
    hub: SessionHub,
    **overrides: Any,
) -> SandboxManager:
    client = OpenSandboxClient(base_url="http://osb", timeout=5, transport=osb.transport())
    return SandboxManager(
        settings=_settings(tmp_path).model_copy(update=overrides),
        hub=hub,
        ledger=ledger,
        client=client,
        detach_settle_seconds=0,
    )


async def test_create_session_injects_env_and_volume(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    hub = SessionHub()
    manager = _manager(tmp_path, ledger, osb, hub)

    handle = await manager.create_session("alice", "default")

    payload = osb.created[0]
    assert payload["image"] == {"uri": "img:test"}
    assert payload["entrypoint"] == ["python", "-m", "app.bridge"]
    assert payload["resourceLimits"] == {"cpu": "2", "memory": "2Gi"}
    assert payload["timeout"] == 900
    policy = payload["networkPolicy"]
    assert policy["defaultAction"] == "deny"
    assert {"action": "allow", "target": "cp"} in policy["egress"]

    env = payload["env"]
    assert env["SESSION_ID"] == handle.session_id
    assert env["SESSION_TOKEN"] == handle.session_token
    assert env["CONTROL_PLANE_URL"] == "ws://cp:8000"
    assert env["OPENAI_BASE_URL"] == "http://cp:8000/llm/v1"
    assert env["OPENAI_API_KEY"] == handle.session_token
    assert env["WORKSPACE_DIR"] == "/workspace"
    assert "CODEX_MODEL" not in env

    volume = payload["volumes"][0]
    assert volume["mountPath"] == "/workspace"
    assert volume["host"]["path"].endswith(handle.session_id)

    record = await ledger.get(handle.session_id)
    assert record is not None and record.status == "running"
    assert record.sandbox_id == "sb-1"
    assert record.tenant_id == "default"
    assert hub.get(handle.session_id) is not None


async def test_second_session_for_same_owner_is_rejected(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(tmp_path, ledger, osb, SessionHub())
    await manager.create_session("alice", "default")

    with pytest.raises(AdmissionRejectedError):
        await manager.create_session("alice", "default")


async def test_stop_session_deletes_sandbox_and_ends_record(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    hub = SessionHub()
    manager = _manager(tmp_path, ledger, osb, hub)
    handle = await manager.create_session("alice", "default")

    await manager.stop_session(handle.session_id)

    assert osb.deleted == ["sb-1"]
    assert hub.get(handle.session_id) is None
    record = await ledger.get(handle.session_id)
    assert record is not None
    assert record.status == "ended"
    assert record.end_reason == "stopped"


async def test_bridge_detach_marks_exited_when_sandbox_is_gone(
    ledger: Ledger, tmp_path: Path
) -> None:
    osb = FakeOpenSandbox()
    hub = SessionHub()
    manager = _manager(tmp_path, ledger, osb, hub)
    handle = await manager.create_session("alice", "default")

    osb.state = "Terminated"
    await manager.on_bridge_detached(handle.session_id)

    record = await ledger.get(handle.session_id)
    assert record is not None and record.status == "ended"
    assert record.end_reason == "sandbox_exited"
    assert hub.get(handle.session_id) is None


async def test_bridge_detach_keeps_running_session(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(tmp_path, ledger, osb, SessionHub())
    handle = await manager.create_session("alice", "default")

    await manager.on_bridge_detached(handle.session_id)

    record = await ledger.get(handle.session_id)
    assert record is not None and record.status == "running"


async def test_resume_restarts_paused_sandbox(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(tmp_path, ledger, osb, SessionHub())
    handle = await manager.create_session("alice", "default")

    osb.state = "Paused"
    info = await manager.resume_session(handle.session_id)

    assert osb.resumed == ["sb-1"]
    assert info.state == "Running"


async def test_pvc_volume_is_created_per_session_on_kubernetes(
    ledger: Ledger, tmp_path: Path
) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(
        tmp_path,
        ledger,
        osb,
        SessionHub(),
        sandbox_runtime="kubernetes",
        volume_backend="pvc",
        workspace_pvc_storage_class="standard",
        workspace_pvc_size="10Gi",
    )

    handle = await manager.create_session("alice", "default")

    volume = osb.created[0]["volumes"][0]
    assert volume["mountPath"] == "/workspace"
    assert "host" not in volume
    assert volume["pvc"] == {
        "claimName": f"ws-{handle.session_id}",
        "createIfNotExists": True,
        "deleteOnSandboxTermination": False,
        "storage": "10Gi",
        "storageClass": "standard",
    }


async def test_pvc_volume_omits_empty_storage_class(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(
        tmp_path,
        ledger,
        osb,
        SessionHub(),
        sandbox_runtime="kubernetes",
        volume_backend="pvc",
        workspace_pvc_storage_class="",
    )

    await manager.create_session("alice", "default")

    assert "storageClass" not in osb.created[0]["volumes"][0]["pvc"]


async def test_resume_paused_rejected_on_kubernetes(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(
        tmp_path,
        ledger,
        osb,
        SessionHub(),
        sandbox_runtime="kubernetes",
        volume_backend="pvc",
    )
    handle = await manager.create_session("alice", "default")

    osb.state = "Paused"
    with pytest.raises(OpenSandboxError, match="冷恢复"):
        await manager.resume_session(handle.session_id)
    assert osb.resumed == []


async def test_resume_rejects_terminated_sandbox(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(tmp_path, ledger, osb, SessionHub())
    handle = await manager.create_session("alice", "default")

    osb.state = "Terminated"
    with pytest.raises(OpenSandboxError, match="不可恢复"):
        await manager.resume_session(handle.session_id)


async def test_unknown_session_stop_raises(ledger: Ledger, tmp_path: Path) -> None:
    manager = _manager(tmp_path, ledger, FakeOpenSandbox(), SessionHub())

    with pytest.raises(LookupError):
        await manager.stop_session("missing")


async def test_create_session_injects_model_limits(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(
        tmp_path,
        ledger,
        osb,
        SessionHub(),
        codex_model="deepseek-flash",
        codex_reasoning_effort="minimal",
        codex_context_window=100000,
    )

    await manager.create_session("alice", "default")

    env = osb.created[0]["env"]
    assert env["CODEX_MODEL"] == "deepseek-flash"
    assert env["CODEX_REASONING_EFFORT"] == "minimal"
    assert env["CODEX_CONTEXT_WINDOW"] == "100000"


async def test_network_policy_parses_allow_list(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(
        tmp_path,
        ledger,
        osb,
        SessionHub(),
        sandbox_egress_allow="api.example.com,*.corp:443,10.0.0.0/8",
    )

    await manager.create_session("alice", "default")

    rules = osb.created[0]["networkPolicy"]["egress"]
    assert {"action": "allow", "target": "api.example.com"} in rules
    assert {"action": "allow", "target": "*.corp"} in rules
    assert {"action": "allow", "target": "10.0.0.0/8"} in rules


async def test_network_policy_parses_ip_and_ipv6_ports(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(
        tmp_path,
        ledger,
        osb,
        SessionHub(),
        sandbox_egress_allow="1.2.3.4:443,2001:db8::1,[2001:db8::2]:8443,192.168.0.0/16",
    )

    await manager.create_session("alice", "default")

    rules = osb.created[0]["networkPolicy"]["egress"]
    assert {"action": "allow", "target": "1.2.3.4", "ports": [443]} in rules
    # 裸 IPv6/CIDR 不被 rpartition(":") 误拆成 target:port
    assert {"action": "allow", "target": "2001:db8::1"} in rules
    assert {"action": "allow", "target": "192.168.0.0/16"} in rules
    assert {"action": "allow", "target": "2001:db8::2", "ports": [8443]} in rules
