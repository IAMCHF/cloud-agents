"""组件装配替身：真实 Ledger（SQLite）+ 假 OpenSandbox/LLM 传输层。"""

from __future__ import annotations

import httpx

from app.bootstrap import Components
from app.bridge.hub import SessionHub
from app.config import Settings
from app.ledger import Database, Ledger
from app.llm_gateway import LlmGateway
from app.metrics import Metrics
from app.sandbox import OpenSandboxClient, SandboxManager
from tests.fakes.opensandbox import FakeOpenSandbox


async def build_test_components(
    settings: Settings,
    hub: SessionHub,
    *,
    osb: FakeOpenSandbox | None = None,
    llm_transport: httpx.AsyncBaseTransport | None = None,
) -> Components:
    database = Database(settings.database_url)
    await database.create_schema()
    ledger = Ledger(database, flush_interval=0.01)
    await ledger.start()
    sandbox = osb if osb is not None else FakeOpenSandbox()
    client = OpenSandboxClient(
        base_url=settings.opensandbox_base_url,
        transport=sandbox.transport(),
    )
    manager = SandboxManager(
        settings=settings,
        hub=hub,
        ledger=ledger,
        client=client,
        detach_settle_seconds=0,
    )
    metrics = Metrics()
    gateway = LlmGateway(
        upstream_base_url=settings.llm_upstream_base_url,
        api_key=settings.llm_api_key,
        hub=hub,
        transport=llm_transport,
        metrics=metrics,
    )
    return Components(
        settings=settings,
        hub=hub,
        database=database,
        ledger=ledger,
        client=client,
        manager=manager,
        gateway=gateway,
        metrics=metrics,
    )
