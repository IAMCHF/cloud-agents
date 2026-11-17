from __future__ import annotations

import pytest

from app.sandbox.admission import AdmissionController, AdmissionRejectedError


async def test_rejects_when_global_limit_reached() -> None:
    controller = AdmissionController(max_active=1)
    await controller.acquire("s1", "alice")

    with pytest.raises(AdmissionRejectedError, match="全局活跃"):
        await controller.acquire("s2", "bob")


async def test_rejects_second_session_for_same_owner() -> None:
    controller = AdmissionController(max_active=4)
    await controller.acquire("s1", "alice")

    with pytest.raises(AdmissionRejectedError, match="同用户"):
        await controller.acquire("s2", "alice")


async def test_release_frees_capacity() -> None:
    controller = AdmissionController(max_active=1)
    await controller.acquire("s1", "alice")
    await controller.release("s1")

    await controller.acquire("s2", "bob")
    assert controller.status.active == 1
    assert controller.active_session_of("bob") == "s2"
