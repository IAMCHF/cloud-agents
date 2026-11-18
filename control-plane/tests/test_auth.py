from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from joserfc import jwt
from joserfc.jwk import RSAKey

from app.auth import OidcError, OidcProvider, Principal
from app.bootstrap import Components
from app.bridge.hub import SessionHub
from app.config import Settings
from app.main import create_app
from tests.fakes.components import build_test_components
from tests.fakes.opensandbox import FakeOpenSandbox

ISSUER = "https://idp.test"
CLIENT_ID = "cloud-agents"
KEY = RSAKey.generate_key(2048, auto_kid=True)
KID = KEY.kid


def _token(**overrides: Any) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "sub": "user-1",
        "preferred_username": "alice",
        "tenant": "acme",
        "email": "alice@example.test",
        "exp": now + 300,
        "iat": now,
        **overrides,
    }
    return jwt.encode({"alg": "RS256", "kid": KID}, claims, KEY)


def _jwks(*, include_key: bool = True) -> dict[str, Any]:
    keys = [KEY.as_dict(private=False)] if include_key else []
    return {"keys": keys}


def _transport(
    *, jwks: Callable[[], dict[str, Any]] = _jwks, calls: list[int] | None = None
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token",
                    "jwks_uri": f"{ISSUER}/jwks",
                },
            )
        if request.url.path == "/jwks":
            body = jwks()
            if calls is not None:
                calls[0] += 1
            return httpx.Response(200, json=body)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def _provider(**overrides: Any) -> OidcProvider:
    return OidcProvider(issuer=ISSUER, transport=_transport(), timeout=5, **overrides)


async def test_verify_returns_principal() -> None:
    principal = await _provider().verify(_token())

    assert principal == Principal(
        subject="user-1",
        username="alice",
        tenant_id="acme",
        email="alice@example.test",
    )


async def test_falls_back_to_default_tenant_and_subject() -> None:
    token = _token(tenant=None, preferred_username=None, email=None)

    principal = await _provider(default_tenant="default").verify(token)

    assert principal.tenant_id == "default"
    assert principal.username == "user-1"
    assert principal.email is None


async def test_rejects_wrong_issuer() -> None:
    with pytest.raises(OidcError, match="iss"):
        await _provider().verify(_token(iss="https://evil.test"))


async def test_rejects_expired_token() -> None:
    with pytest.raises(OidcError, match="token"):
        await _provider().verify(_token(exp=int(time.time()) - 3600))


async def test_rejects_missing_subject() -> None:
    with pytest.raises(OidcError, match="sub"):
        await _provider().verify(_token(sub=None))


async def test_rejects_wrong_audience() -> None:
    provider = OidcProvider(issuer=ISSUER, audience="cloud-agents", transport=_transport())

    with pytest.raises(OidcError, match="audience"):
        await provider.verify(_token(aud=["account"]))
    principal = await provider.verify(_token(aud=["account", "cloud-agents"]))
    assert principal.subject == "user-1"


async def test_refreshes_jwks_when_kid_unknown() -> None:
    calls = [0]
    payloads = [lambda: _jwks(include_key=False), _jwks]
    transport = _transport(jwks=lambda: payloads[min(calls[0], 1)](), calls=calls)
    provider = OidcProvider(issuer=ISSUER, transport=transport)

    principal = await provider.verify(_token())

    assert principal.subject == "user-1"
    assert calls[0] == 2


async def test_metadata_failure_is_reported() -> None:
    provider = OidcProvider(
        issuer=ISSUER,
        transport=httpx.MockTransport(lambda _: httpx.Response(500)),
    )

    with pytest.raises(OidcError, match="发现失败"):
        await provider.verify(_token())


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "public_base_url": "http://cp:8000",
        "opensandbox_base_url": "http://osb",
        "sandbox_image": "img:test",
        "sandbox_start_timeout_seconds": 5,
        "max_active_sessions": 4,
        "workspace_host_root": str(tmp_path / "volumes"),
        "database_url": f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}",
        "auth_mode": "oidc",
        "oidc_issuer": ISSUER,
        "oidc_client_id": CLIENT_ID,
    }
    values.update(overrides)
    return Settings(**values)


def _app(tmp_path: Path, **overrides: Any) -> tuple[TestClient, OidcProvider]:
    settings = _settings(tmp_path, **overrides)
    provider = _provider()

    async def factory(resolved: Settings, hub: SessionHub) -> Components:
        return await build_test_components(resolved, hub, osb=FakeOpenSandbox())

    return TestClient(
        create_app(settings=settings, components_factory=factory, oidc_provider=provider)
    ), provider


def test_auth_config_exposes_oidc_endpoints(tmp_path: Path) -> None:
    client, _ = _app(tmp_path)
    with client:
        body = client.get("/api/auth/config").json()

    assert body == {
        "mode": "oidc",
        "issuer": ISSUER,
        "client_id": CLIENT_ID,
        "scope": "openid profile email",
        "authorization_endpoint": f"{ISSUER}/authorize",
        "token_endpoint": f"{ISSUER}/token",
    }


def test_auth_config_token_mode(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'token.db'}",
        p1_auth_token="owner-token",
    )

    async def factory(resolved: Settings, hub: SessionHub) -> Components:
        return await build_test_components(resolved, hub, osb=FakeOpenSandbox())

    with TestClient(create_app(settings=settings, components_factory=factory)) as client:
        assert client.get("/api/auth/config").json() == {"mode": "token"}


def test_oidc_bearer_token_creates_session(tmp_path: Path) -> None:
    client, _ = _app(tmp_path)
    with client:
        created = client.post("/api/sessions", headers={"Authorization": f"Bearer {_token()}"})
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        fetched = client.get(
            f"/api/sessions/{session_id}", headers={"Authorization": f"Bearer {_token()}"}
        )
        assert fetched.status_code == 200

        rejected = client.post("/api/sessions", headers={"Authorization": "Bearer nope"})
        assert rejected.status_code == 401


def test_oidc_rejects_other_users_session(tmp_path: Path) -> None:
    client, _ = _app(tmp_path)
    with client:
        created = client.post("/api/sessions", headers={"Authorization": f"Bearer {_token()}"})
        session_id = created.json()["session_id"]

        other = _token(sub="user-2", tenant="acme", preferred_username="bob")
        denied = client.get(
            f"/api/sessions/{session_id}", headers={"Authorization": f"Bearer {other}"}
        )
        assert denied.status_code == 403
        assert (
            client.delete(
                f"/api/sessions/{session_id}", headers={"Authorization": f"Bearer {other}"}
            ).status_code
            == 403
        )
