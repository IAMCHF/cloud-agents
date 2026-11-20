from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.bridge.hub import SessionHub
from app.config import Settings
from app.ledger import AdmissionRejectedError, Ledger, SessionStateError
from app.metrics import Metrics
from app.sandbox import OpenSandboxClient, SandboxManager
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
    *,
    metrics: Metrics | None = None,
    **overrides: Any,
) -> SandboxManager:
    client = OpenSandboxClient(base_url="http://osb", timeout=5, transport=osb.transport())
    return SandboxManager(
        settings=_settings(tmp_path).model_copy(update=overrides),
        hub=hub,
        ledger=ledger,
        client=client,
        detach_settle_seconds=0,
        metrics=metrics,
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
    state = payload["volumes"][1]
    assert state["mountPath"] == "/home/agent/.codex"
    assert state["host"]["path"].endswith(f"{handle.session_id}.state")

    record = await ledger.get(handle.session_id)
    assert record is not None and record.status == "running"
    assert record.sandbox_id == "sb-1"
    assert record.tenant_id == "default"
    assert hub.get(handle.session_id) is not None


async def test_create_and_resume_observe_latency_metric(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    metrics = Metrics()
    manager = _manager(tmp_path, ledger, osb, SessionHub(), metrics=metrics)
    handle = await manager.create_session("alice", "default")
    await manager.sleep_session(handle.session_id)
    await manager.resume_session(handle.session_id)

    rendered = metrics.render()
    assert b'cloud_agents_sandbox_create_seconds_count{mode="create"} 1.0' in rendered
    assert b'cloud_agents_sandbox_create_seconds_count{mode="resume"} 1.0' in rendered


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
    assert record is not None and record.status == "idle"
    assert record.end_reason == "sandbox_exited"
    assert hub.get(handle.session_id) is None


async def test_sleep_and_cold_resume_keep_volumes_and_rotate_token(
    ledger: Ledger, tmp_path: Path
) -> None:
    osb = FakeOpenSandbox()
    hub = SessionHub()
    manager = _manager(tmp_path, ledger, osb, hub)
    handle = await manager.create_session("alice", "default")
    old_token = handle.session_token

    assert await manager.sleep_session(handle.session_id) is True

    assert osb.deleted == ["sb-1"]
    record = await ledger.get(handle.session_id)
    assert record is not None and record.status == "idle"
    assert record.sandbox_id is None
    assert hub.get(handle.session_id) is None
    # 旧 token 仍能定位台账，但 idle 状态不再通过 WS/网关的活跃校验。
    old_record = await ledger.find_session_by_token(old_token)
    assert old_record is not None and old_record.status == "idle"

    resumed = await manager.resume_session(handle.session_id)

    assert resumed.session_token != old_token
    assert resumed.sandbox_id == "sb-1"
    assert len(osb.created) == 2
    spec = osb.created[1]
    assert spec["env"]["SESSION_TOKEN"] == resumed.session_token
    assert [volume["mountPath"] for volume in spec["volumes"]] == [
        "/workspace",
        "/home/agent/.codex",
    ]
    record = await ledger.get(handle.session_id)
    assert record is not None and record.status == "running"
    assert hub.get(handle.session_id) is not None
    # 恢复时轮换 token：旧 token 不再可查。
    assert await ledger.find_session_by_token(old_token) is None
    found = await ledger.find_session_by_token(resumed.session_token)
    assert found is not None and found.session_id == handle.session_id


async def test_sleep_is_idempotent_and_resume_requires_idle(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(tmp_path, ledger, osb, SessionHub())
    handle = await manager.create_session("alice", "default")

    with pytest.raises(SessionStateError):
        await manager.resume_session(handle.session_id)

    assert await manager.sleep_session(handle.session_id) is True
    assert await manager.sleep_session(handle.session_id) is False


async def test_resume_respects_same_owner_admission(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(tmp_path, ledger, osb, SessionHub())
    handle = await manager.create_session("alice", "default")
    await manager.sleep_session(handle.session_id)

    # idle 不计入活跃配额，允许同属主再建一个会话。
    other = await manager.create_session("alice", "default")
    with pytest.raises(AdmissionRejectedError):
        await manager.resume_session(handle.session_id)

    await manager.stop_session(other.session_id)
    resumed = await manager.resume_session(handle.session_id)
    assert resumed.session_id == handle.session_id


async def test_bridge_detach_keeps_running_session(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(tmp_path, ledger, osb, SessionHub())
    handle = await manager.create_session("alice", "default")

    await manager.on_bridge_detached(handle.session_id)

    record = await ledger.get(handle.session_id)
    assert record is not None and record.status == "running"


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

    workspace, state = osb.created[0]["volumes"]
    assert workspace["mountPath"] == "/workspace"
    assert "host" not in workspace
    assert workspace["pvc"] == {
        "claimName": f"ws-{handle.session_id}",
        "createIfNotExists": True,
        "deleteOnSandboxTermination": False,
        "storage": "10Gi",
        "storageClass": "standard",
    }
    assert state["mountPath"] == "/home/agent/.codex"
    assert state["pvc"] == {
        "claimName": f"state-{handle.session_id}",
        "createIfNotExists": True,
        "deleteOnSandboxTermination": False,
        "storage": "1Gi",
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

    for volume in osb.created[0]["volumes"]:
        assert "storageClass" not in volume["pvc"]


async def test_reconcile_running_marks_missing_sandbox_idle(ledger: Ledger, tmp_path: Path) -> None:
    osb = FakeOpenSandbox()
    manager = _manager(tmp_path, ledger, osb, SessionHub())
    handle = await manager.create_session("alice", "default")

    osb.state = "Terminated"
    assert await manager.reconcile_running() == 1

    record = await ledger.get(handle.session_id)
    assert record is not None and record.status == "idle"
    assert record.end_reason == "sandbox_missing"


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
