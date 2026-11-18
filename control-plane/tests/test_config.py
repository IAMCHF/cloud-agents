from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_docker_runtime_supports_pause() -> None:
    settings = Settings()

    assert settings.sandbox_runtime == "docker"
    assert settings.volume_backend == "host"
    assert settings.sandbox_supports_pause is True


def test_kubernetes_requires_pvc_volume() -> None:
    with pytest.raises(ValidationError, match="volume_backend=pvc"):
        Settings(sandbox_runtime="kubernetes", volume_backend="host")


def test_kubernetes_pvc_has_no_pause_capability() -> None:
    settings = Settings(sandbox_runtime="kubernetes", volume_backend="pvc")

    assert settings.sandbox_supports_pause is False
