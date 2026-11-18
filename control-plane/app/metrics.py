"""Prometheus 指标：活跃会话数、准入拒绝、LLM 转发计数与 token 计量。"""

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
        self.llm_tokens = Counter(
            "cloud_agents_llm_tokens_total",
            "LLM 网关计量的 token 数",
            ["tenant", "direction"],
            registry=self.registry,
        )
        self.llm_budget_rejections = Counter(
            "cloud_agents_llm_budget_rejections_total",
            "租户月度 token 预算拒绝次数",
            ["tenant"],
            registry=self.registry,
        )

    def observe_active_sessions(self, count: int) -> None:
        self.active_sessions.set(count)

    def observe_llm_usage(self, tenant_id: str, input_tokens: int, output_tokens: int) -> None:
        if input_tokens:
            self.llm_tokens.labels(tenant=tenant_id, direction="input").inc(input_tokens)
        if output_tokens:
            self.llm_tokens.labels(tenant=tenant_id, direction="output").inc(output_tokens)

    def observe_budget_rejection(self, tenant_id: str) -> None:
        self.llm_budget_rejections.labels(tenant=tenant_id).inc()

    def render(self) -> bytes:
        return generate_latest(self.registry)
