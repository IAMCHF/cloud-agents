"""认证配置端点：Web SPA 从后端取 OIDC 参数，避免把 issuer/client_id 写进构建产物。"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth.oidc import OidcError, OidcProvider
from app.config import Settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthConfigResponse(BaseModel):
    mode: Literal["token", "oidc"]
    issuer: str | None = None
    client_id: str | None = None
    scope: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None


@router.get("/config", response_model=AuthConfigResponse, response_model_exclude_none=True)
async def auth_config(request: Request) -> AuthConfigResponse:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise HTTPException(status_code=503, detail="settings not configured")
    if settings.auth_mode == "token":
        return AuthConfigResponse(mode="token")

    provider = getattr(request.app.state, "oidc", None)
    if not isinstance(provider, OidcProvider):
        raise HTTPException(status_code=503, detail="OIDC 未配置")
    try:
        metadata = await provider.metadata()
    except OidcError as exc:
        raise HTTPException(status_code=503, detail="OIDC 发现不可用") from exc
    return AuthConfigResponse(
        mode="oidc",
        issuer=metadata.issuer,
        client_id=settings.oidc_client_id,
        scope=settings.oidc_scope,
        authorization_endpoint=metadata.authorization_endpoint,
        token_endpoint=metadata.token_endpoint,
    )
