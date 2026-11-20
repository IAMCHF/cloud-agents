"""控制面配置：全部来自环境变量，禁止硬编码环境地址与密钥。"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # 控制面对外基址：沙箱回连 WSS 与 LLM 网关都从这里派生。
    public_base_url: str = "http://127.0.0.1:8000"

    # 鉴权模式：token = P1 固定 token（开发/CI）；oidc = OIDC bearer token（P2）。
    auth_mode: Literal["token", "oidc"] = "token"
    p1_auth_token: str = ""
    p1_owner: str = "p1-user"

    # OIDC：issuer 用于发现与签名校验；client_id 供 Web SPA 走授权码 + PKCE。
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_audience: str = ""
    oidc_scope: str = "openid profile email"
    oidc_tenant_claim: str = "tenant"
    oidc_username_claim: str = "preferred_username"
    oidc_default_tenant: str = "default"
    oidc_jwks_cache_seconds: float = 300.0
    oidc_http_timeout_seconds: float = 5.0

    # 租户默认配额：租户首次出现时按此建档（0 = 不限制）。
    tenant_default_max_active_sessions: int = 2
    tenant_default_monthly_token_budget: int = 0

    # OpenSandbox 生命周期 API。
    opensandbox_base_url: str = "http://127.0.0.1:8080"
    opensandbox_api_key: str = ""
    sandbox_image: str = "cloud-agents/sandbox:0.1.0"
    sandbox_cpu: str = "2"
    sandbox_memory: str = "2Gi"
    sandbox_timeout_seconds: int = 3600
    sandbox_start_timeout_seconds: float = 90.0
    max_active_sessions: int = 24
    # execd 直连（终端/文件）可选的访问 token；OpenSandbox 未启用鉴权时留空。
    execd_access_token: str = ""
    # 应用预览：子域反代 `<session>--<port>.preview.<base>`；base 留空禁用。
    # 票据密钥留空时回落到 P1_AUTH_TOKEN（开发方便），生产应显式配置。
    preview_base_domain: str = ""
    preview_token_secret: str = ""
    preview_token_ttl_seconds: int = 3600

    # 沙箱出口策略：默认拒绝；白名单 target、target:port 或 [IPv6]:port（逗号分隔，
    # 裸 IP/CIDR 含 IPv6 不拆端口）。控制面/网关地址会自动加入白名单。
    sandbox_network_default_action: Literal["deny", "allow"] = "deny"
    sandbox_egress_allow: str = ""

    # 沙箱内 codex 的模型名与推理/上下文限制（空/0 用 codex 默认）。
    codex_model: str = ""
    codex_reasoning_effort: str = ""
    codex_context_window: int = 0
    # 容器即隔离边界：codex 自身不再套 bwrap（容器内无 user namespace 权限）。
    codex_sandbox_mode: str = "danger-full-access"
    codex_approval_policy: str = "on-request"

    # 用户卷：host 挂载（Docker）或平台命名卷（K8s PVC / Docker named volume）。
    sandbox_runtime: Literal["docker", "kubernetes"] = "docker"
    volume_backend: Literal["host", "pvc"] = "host"
    workspace_host_root: str = ""
    workspace_mount_path: str = "/workspace"
    # PVC 由 OpenSandbox 按 claimName 自动创建；留空 storageClass 用集群默认。
    workspace_pvc_storage_class: str = ""
    workspace_pvc_size: str = "5Gi"
    # codex 状态盘（CODEX_HOME）独立于工作区卷，销毁/恢复时随会话保留。
    state_pvc_size: str = "1Gi"

    # LLM 网关：真 key 只在这里，沙箱只拿会话 token。
    llm_upstream_base_url: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: float = 600.0

    # 台账/审计。
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/cloud_agents"
    audit_flush_interval_seconds: float = 0.2
    # 启动对账：只结束创建超过该时长的 creating 会话；running 保留供 WS 重连重建。
    creating_stale_timeout_seconds: float = 300.0
    # 空闲销毁：无客户端且无进行中 turn 超过该时长 → 销毁沙箱、保留卷、转 idle。
    idle_sweeper_enabled: bool = True
    idle_timeout_seconds: float = 900.0
    idle_sweep_interval_seconds: float = 60.0
    # 无人响应审批：超过该时长自动 decline，避免 turn 永久挂起拖住沙箱。
    approval_timeout_seconds: float = 300.0

    # 卷归档：仅归档已结束会话；默认 dry-run，不删除源卷。
    archive_enabled: bool = False
    archive_root: str = ""
    archive_retention_days: int = 30
    archive_dry_run: bool = True
    archive_timeout_seconds: float = 600.0
    archive_cpu: str = "1"
    archive_memory: str = "1Gi"

    # 浏览器跨域访问管理面/网关时按需放开（逗号分隔；默认不放开）。
    cors_allow_origins: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def websocket_base_url(self) -> str:
        if self.public_base_url.startswith("https://"):
            return "wss://" + self.public_base_url.removeprefix("https://")
        if self.public_base_url.startswith("http://"):
            return "ws://" + self.public_base_url.removeprefix("http://")
        raise ValueError("public_base_url 必须以 http:// 或 https:// 开头")

    @property
    def llm_public_base_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/llm/v1"

    @property
    def sandbox_supports_pause(self) -> bool:
        """K8s 默认没有 snapshot registry，pause 会 PauseFailed；P3 走冷恢复。"""
        return self.sandbox_runtime == "docker"

    @model_validator(mode="after")
    def _validate_runtime(self) -> Settings:
        if self.sandbox_runtime == "kubernetes" and self.volume_backend != "pvc":
            raise ValueError("sandbox_runtime=kubernetes 时必须 volume_backend=pvc")
        if self.auth_mode == "oidc" and not (self.oidc_issuer and self.oidc_client_id):
            raise ValueError("auth_mode=oidc 时必须配置 oidc_issuer 与 oidc_client_id")
        if self.archive_enabled and not self.archive_root:
            raise ValueError("archive_enabled=true 时必须配置 archive_root")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
