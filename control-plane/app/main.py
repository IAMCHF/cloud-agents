"""FastAPI 应用装配：桥接端点 + 会话管理 + 最小 LLM 网关 + 指标。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.sessions import router as sessions_router
from app.bootstrap import Components, build_components
from app.bridge.hub import SessionHub
from app.bridge.server import router as bridge_router
from app.config import Settings, get_settings
from app.llm_gateway import build_router as build_llm_router
from app.metrics import CONTENT_TYPE_LATEST

ComponentsFactory = Callable[[Settings, SessionHub], Awaitable[Components]]


def create_app(
    *,
    settings: Settings | None = None,
    hub: SessionHub | None = None,
    components_factory: ComponentsFactory | None = None,
) -> FastAPI:
    resolved_settings = settings if settings is not None else get_settings()
    resolved_hub = hub if hub is not None else SessionHub()
    factory: ComponentsFactory = components_factory or build_components

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        components = await factory(resolved_settings, resolved_hub)
        app.state.components = components
        app.state.ledger = components.ledger
        app.state.manager = components.manager
        app.state.llm_gateway = components.gateway
        app.state.metrics = components.metrics
        try:
            yield
        finally:
            await components.aclose()

    app = FastAPI(title="cloud-agents control-plane", version=__version__, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.bridge_hub = resolved_hub

    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["authorization", "content-type"],
        )

    app.include_router(bridge_router)
    app.include_router(sessions_router)
    app.include_router(build_llm_router())

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics_endpoint(request: Request) -> Response:
        components = getattr(request.app.state, "components", None)
        if not isinstance(components, Components):
            return Response(status_code=503)
        components.metrics.observe_active_sessions(components.manager.admission.status.active)
        return Response(content=components.metrics.render(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
