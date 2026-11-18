"""FastAPI 鉴权依赖：token / OIDC 双模式统一成 Principal。"""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

from app.auth.oidc import OidcError, OidcProvider
from app.auth.principal import Principal
from app.config import Settings


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise HTTPException(status_code=503, detail="settings not configured")
    return settings


def _provider(request: Request) -> OidcProvider:
    provider = getattr(request.app.state, "oidc", None)
    if not isinstance(provider, OidcProvider):
        raise HTTPException(status_code=503, detail="OIDC 未配置")
    return provider


def bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


async def require_principal(request: Request) -> Principal:
    """管理面鉴权：token 模式比对 P1_AUTH_TOKEN，OIDC 模式校验 bearer token。"""
    settings = _settings(request)
    if settings.auth_mode == "token":
        if not settings.p1_auth_token:
            raise HTTPException(status_code=503, detail="P1_AUTH_TOKEN 未配置")
        if not hmac.compare_digest(bearer_token(request), settings.p1_auth_token):
            raise HTTPException(status_code=401, detail="invalid token")
        return Principal(
            subject=settings.p1_owner,
            username=settings.p1_owner,
            tenant_id=settings.oidc_default_tenant,
        )

    try:
        return await _provider(request).verify(bearer_token(request))
    except OidcError as exc:
        raise HTTPException(
            status_code=401,
            detail="invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
