"""控制面配置：全部来自环境变量，禁止硬编码环境地址与密钥。"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # 控制面对外基址：沙箱回连 WSS 与 LLM 网关都从这里派生。
    public_base_url: str = "http://127.0.0.1:8000"

    # P1 单租户鉴权：管理面用固定 token，会话属主取配置值；P2 换 OIDC。
    p1_auth_token: str = ""
    p1_owner: str = "p1-user"

    # OpenSandbox 生命周期 API。
    opensandbox_base_url: str = "http://127.0.0.1:8080"
    opensandbox_api_key: str = ""
    sandbox_image: str = "cloud-agents/sandbox:0.1.0"
    sandbox_cpu: str = "2"
    sandbox_memory: str = "2Gi"
    sandbox_timeout_seconds: int = 3600
    sandbox_start_timeout_seconds: float = 90.0
    max_active_sessions: int = 24

    # 用户卷：host 挂载（Docker）或平台命名卷（K8s）。
    volume_backend: Literal["host", "pvc"] = "host"
    workspace_host_root: str = ""
    workspace_mount_path: str = "/workspace"

    # LLM 网关：真 key 只在这里，沙箱只拿会话 token。
    llm_upstream_base_url: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: float = 600.0

    # 台账/审计。
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/cloud_agents"
    audit_flush_interval_seconds: float = 0.2

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
