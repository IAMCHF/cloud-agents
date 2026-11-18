"""应用组件装配：真实依赖在 lifespan 内构建，测试可注入替身。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.bridge.hub import SessionHub
from app.config import Settings
from app.ledger import Database, Ledger
from app.llm_gateway import LlmGateway
from app.metrics import Metrics
from app.sandbox import OpenSandboxClient, SandboxManager

logger = logging.getLogger(__name__)


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
        self.hub.on_audit = None
        await self.gateway.aclose()
        await self.client.aclose()
        await self.ledger.stop()
        await self.database.dispose()


async def build_components(settings: Settings, hub: SessionHub) -> Components:
    database = Database(settings.database_url)
    ledger = Ledger(database, flush_interval=settings.audit_flush_interval_seconds)
    await ledger.start()
    # 多副本/重启对账：running 会话保留，等待沙箱桥接/客户端重连时按台账重建通道。
    stale_before = datetime.now(UTC) - timedelta(seconds=settings.creating_stale_timeout_seconds)
    stale = await ledger.end_stale_creating(older_than=stale_before, reason="stale_creating")
    if stale:
        logger.warning("启动对账：%s 个超时创建中的会话已标记结束", stale)
    client = OpenSandboxClient(
        base_url=settings.opensandbox_base_url,
        api_key=settings.opensandbox_api_key,
    )
    manager = SandboxManager(settings=settings, hub=hub, ledger=ledger, client=client)
    hub.on_bridge_detached = manager.on_bridge_detached
    # 多客户端连接事件与审批响应归因落审计（批量异步写）。
    hub.on_audit = ledger.submit_event
    metrics = Metrics()
    gateway = LlmGateway(
        upstream_base_url=settings.llm_upstream_base_url,
        api_key=settings.llm_api_key,
        ledger=ledger,
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
