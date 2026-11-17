"""FastAPI 应用装配。P1 只有桥接端点与健康检查，P2 再挂认证/台账/网关。"""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.bridge.hub import SessionHub
from app.bridge.server import router as bridge_router


def create_app(*, hub: SessionHub | None = None) -> FastAPI:
    app = FastAPI(title="cloud-agents control-plane", version=__version__)
    app.state.bridge_hub = hub if hub is not None else SessionHub()
    app.include_router(bridge_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
