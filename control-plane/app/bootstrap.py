"""应用组件装配：真实依赖在 lifespan 内构建，测试可注入替身。"""

from __future__ import annotations

from dataclasses import dataclass

from app.bridge.hub import SessionHub
from app.config import Settings
from app.ledger import Database, Ledger
from app.llm_gateway import LlmGateway
from app.metrics import Metrics
from app.sandbox import OpenSandboxClient, SandboxManager


@dataclass
class Components:
    settings: Settings
    hub: SessionHub
    database: Database
    ledger: Ledger
    client: OpenSandboxClient
    manager: SandboxManager
    gateway: LlmGateway
    metrics: Metrics

    async def aclose(self) -> None:
        self.hub.on_bridge_detached = None
        await self.gateway.aclose()
        await self.client.aclose()
        await self.ledger.stop()
        await self.database.dispose()


async def build_components(settings: Settings, hub: SessionHub) -> Components:
    database = Database(settings.database_url)
    ledger = Ledger(database, flush_interval=settings.audit_flush_interval_seconds)
    await ledger.start()
    client = OpenSandboxClient(
        base_url=settings.opensandbox_base_url,
        api_key=settings.opensandbox_api_key,
    )
    manager = SandboxManager(settings=settings, hub=hub, ledger=ledger, client=client)
    hub.on_bridge_detached = manager.on_bridge_detached
    metrics = Metrics()
    gateway = LlmGateway(
        upstream_base_url=settings.llm_upstream_base_url,
        api_key=settings.llm_api_key,
        hub=hub,
        timeout=settings.llm_timeout_seconds,
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
