"""认证主体：一次请求对应的用户与租户。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    subject: str
    username: str
    tenant_id: str
    email: str | None = None
