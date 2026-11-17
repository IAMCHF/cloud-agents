"""Prometheus 指标：活跃会话数、准入拒绝、LLM 转发计数。"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    generate_latest,
)

__all__ = ["CONTENT_TYPE_LATEST", "Metrics"]


class Metrics:
    """每个应用实例一份注册表，避免测试/多实例之间串数据。"""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.active_sessions = Gauge(
            "cloud_agents_active_sessions",
            "当前活跃会话数（准入控制器口径）",
            registry=self.registry,
        )
        self.admission_rejections = Counter(
            "cloud_agents_admission_rejections_total",
            "准入拒绝次数",
            ["reason"],
            registry=self.registry,
        )
        self.llm_requests = Counter(
            "cloud_agents_llm_requests_total",
            "LLM 网关转发的请求数",
            registry=self.registry,
        )

    def observe_active_sessions(self, count: int) -> None:
        self.active_sessions.set(count)

    def render(self) -> bytes:
        return generate_latest(self.registry)
