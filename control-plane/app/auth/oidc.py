"""OIDC 接入：issuer 发现、JWKS 缓存与 bearer token 校验。

只校验签名与标准声明，不做授权决策；租户取自定义声明（默认 ``tenant``），
缺失时落到配置的默认租户。JOSE 用 joserfc（Authlib 1.9 起 authlib.jose 已弃用）。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry

from app.auth.principal import Principal

_ALGORITHMS = ["RS256", "ES256"]
_CLOCK_LEEWAY_SECONDS = 60


class OidcError(RuntimeError):
    """OIDC 发现或 token 校验失败。"""


@dataclass(frozen=True)
class OidcMetadata:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str


class OidcProvider:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str = "",
        tenant_claim: str = "tenant",
        username_claim: str = "preferred_username",
        default_tenant: str = "default",
        jwks_cache_seconds: float = 300.0,
        timeout: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not issuer:
            raise ValueError("OIDC issuer 不能为空")
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._tenant_claim = tenant_claim
        self._username_claim = username_claim
        self._default_tenant = default_tenant
        self._jwks_cache_seconds = jwks_cache_seconds
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport)
        self._metadata: OidcMetadata | None = None
        self._keys: KeySet | None = None
        self._keys_expire_at = 0.0
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def metadata(self) -> OidcMetadata:
        cached = self._metadata
        if cached is not None:
            return cached
        url = f"{self._issuer}/.well-known/openid-configuration"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()
            metadata = OidcMetadata(
                issuer=str(data["issuer"]).rstrip("/"),
                authorization_endpoint=str(data["authorization_endpoint"]),
                token_endpoint=str(data["token_endpoint"]),
                jwks_uri=str(data["jwks_uri"]),
            )
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise OidcError(f"OIDC 发现失败：{exc}") from exc
        if metadata.issuer != self._issuer:
            raise OidcError(f"OIDC issuer 不匹配：{metadata.issuer}")
        self._metadata = metadata
        return metadata

    async def verify(self, token: str) -> Principal:
        if not token:
            raise OidcError("缺少 bearer token")
        metadata = await self.metadata()
        try:
            claims = await self._decode(token, metadata)
        except OidcError:
            raise
        except JoseError as exc:
            raise OidcError(f"token 校验失败：{exc}") from exc

        if self._audience and not _has_audience(claims.get("aud"), self._audience):
            raise OidcError("token audience 不匹配")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise OidcError("token 缺少 sub")
        return Principal(
            subject=subject,
            username=_as_text(claims.get(self._username_claim)) or subject,
            tenant_id=_as_text(claims.get(self._tenant_claim)) or self._default_tenant,
            email=_as_text(claims.get("email")),
        )

    async def _decode(self, token: str, metadata: OidcMetadata) -> dict[str, Any]:
        """kid 轮换时刷新一次 JWKS 再重试。"""
        try:
            decoded = jwt.decode(token, await self._key_set(metadata), algorithms=_ALGORITHMS)
        except JoseError:
            refreshed = await self._key_set(metadata, force=True)
            decoded = jwt.decode(token, refreshed, algorithms=_ALGORITHMS)
        claims = dict(decoded.claims)
        JWTClaimsRegistry(
            leeway=_CLOCK_LEEWAY_SECONDS,
            iss={"essential": True, "value": self._issuer},
            exp={"essential": True},
        ).validate(claims)
        return claims

    async def _key_set(self, metadata: OidcMetadata, *, force: bool = False) -> KeySet:
        async with self._lock:
            now = time.monotonic()
            if not force and self._keys is not None and now < self._keys_expire_at:
                return self._keys
            try:
                response = await self._client.get(metadata.jwks_uri)
                response.raise_for_status()
                self._keys = KeySet.import_key_set(response.json())
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                raise OidcError(f"JWKS 获取失败：{exc}") from exc
            self._keys_expire_at = now + self._jwks_cache_seconds
            return self._keys


def _as_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _has_audience(value: object, expected: str) -> bool:
    if isinstance(value, str):
        return value == expected
    if isinstance(value, list):
        return expected in value
    return False
