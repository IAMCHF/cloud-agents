from __future__ import annotations

import pytest

from app.bridge.entry import BridgeConfig


def test_config_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTROL_PLANE_URL", "ws://control-plane:8000/")
    monkeypatch.setenv("SESSION_ID", "session-1")
    monkeypatch.setenv("SESSION_TOKEN", "token with space")
    monkeypatch.setenv("CODEX_BIN", "/usr/local/bin/codex")
    monkeypatch.setenv("CODEX_APP_SERVER_ARGS", "app-server --listen stdio")
    monkeypatch.setenv("WORKSPACE_DIR", "/workspace")

    config = BridgeConfig.from_env()

    assert config.control_plane_url == "ws://control-plane:8000"
    assert config.session_id == "session-1"
    assert config.codex_bin == "/usr/local/bin/codex"
    assert config.codex_args == ("app-server", "--listen", "stdio")
    assert config.workspace_dir == "/workspace"
    # token 需 URL 编码，不能原样拼进查询串
    assert (
        config.bridge_url()
        == "ws://control-plane:8000/ws/bridge/session-1?token=token%20with%20space"
    )


def test_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTROL_PLANE_URL", "ws://cp:8000")
    monkeypatch.setenv("SESSION_ID", "s")
    monkeypatch.setenv("SESSION_TOKEN", "t")
    monkeypatch.delenv("CODEX_BIN", raising=False)
    monkeypatch.delenv("CODEX_APP_SERVER_ARGS", raising=False)
    monkeypatch.delenv("WORKSPACE_DIR", raising=False)

    config = BridgeConfig.from_env()

    assert config.codex_bin == "codex"
    assert config.codex_args == ("app-server",)
    assert config.workspace_dir is None


def test_config_requires_control_plane_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONTROL_PLANE_URL", raising=False)
    monkeypatch.setenv("SESSION_ID", "s")
    monkeypatch.setenv("SESSION_TOKEN", "t")

    with pytest.raises(SystemExit):
        BridgeConfig.from_env()
