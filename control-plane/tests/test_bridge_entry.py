from __future__ import annotations

from pathlib import Path

import pytest

from app.bridge.entry import BridgeConfig, _prepare_codex_home


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


def test_prepare_codex_home_writes_provider_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_BASE_URL", "http://cp:8000/llm/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "session-token")
    monkeypatch.setenv("CODEX_MODEL", "internal-codex")
    monkeypatch.setenv("CODEX_REASONING_EFFORT", "minimal")
    monkeypatch.setenv("CODEX_CONTEXT_WINDOW", "100000")

    _prepare_codex_home()

    content = (tmp_path / "config.toml").read_text(encoding="utf-8")
    assert 'model = "internal-codex"' in content
    assert 'base_url = "http://cp:8000/llm/v1"' in content
    assert 'env_key = "OPENAI_API_KEY"' in content
    assert 'wire_api = "responses"' in content
    assert 'model_reasoning_effort = "minimal"' in content
    assert "model_context_window = 100000" in content
    assert "session-token" not in content


def test_prepare_codex_home_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_BASE_URL", "http://cp:8000/llm/v1")
    config = tmp_path / "config.toml"
    config.write_text("# operator managed\n", encoding="utf-8")

    _prepare_codex_home()

    assert config.read_text(encoding="utf-8") == "# operator managed\n"
