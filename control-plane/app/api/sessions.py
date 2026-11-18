"""P1 会话管理 API（管理面；执行协议仍走 /ws/session 的原生 JSON-RPC）。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import Principal, require_principal
from app.config import Settings
from app.ledger import Ledger
from app.metrics import Metrics
from app.sandbox import AdmissionRejectedError, OpenSandboxError, SandboxManager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreateResponse(BaseModel):
    session_id: str
    session_token: str
    sandbox_id: str
    ws_url: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    sandbox_id: str | None
    sandbox_state: str | None


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise HTTPException(status_code=503, detail="settings not configured")
    return settings


def _manager(request: Request) -> SandboxManager:
    manager = getattr(request.app.state, "manager", None)
    if not isinstance(manager, SandboxManager):
        raise HTTPException(status_code=503, detail="sandbox manager not configured")
    return manager


def _metrics(request: Request) -> Metrics | None:
    metrics = getattr(request.app.state, "metrics", None)
    return metrics if isinstance(metrics, Metrics) else None


def _ledger(request: Request) -> Ledger:
    ledger = getattr(request.app.state, "ledger", None)
    if not isinstance(ledger, Ledger):
        raise HTTPException(status_code=503, detail="ledger not configured")
    return ledger


@router.post("", response_model=SessionCreateResponse)
async def create_session(
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> SessionCreateResponse:
    settings = _settings(request)
    manager = _manager(request)
    try:
        handle = await manager.create_session(principal.subject)
    except AdmissionRejectedError as exc:
        metrics = _metrics(request)
        if metrics is not None:
            metrics.admission_rejections.labels(reason=exc.reason).inc()
        raise HTTPException(status_code=429, detail=exc.reason) from exc
    except OpenSandboxError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return SessionCreateResponse(
        session_id=handle.session_id,
        session_token=handle.session_token,
        sandbox_id=handle.sandbox_id,
        ws_url=(
            f"{settings.websocket_base_url}/ws/session/{handle.session_id}"
            f"?token={handle.session_token}"
        ),
    )


@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session(
    session_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> SessionStatusResponse:
    ledger = _ledger(request)
    manager = _manager(request)
    record = await ledger.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="session not found")
    if record.owner != principal.subject:
        raise HTTPException(status_code=403, detail="session belongs to another user")
    sandbox_state: str | None = None
    try:
        sandbox_state = (await manager.sandbox_status(session_id)).state
    except (LookupError, OpenSandboxError):
        sandbox_state = None
    return SessionStatusResponse(
        session_id=record.session_id,
        status=record.status,
        sandbox_id=record.sandbox_id,
        sandbox_state=sandbox_state,
    )


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> None:
    ledger = _ledger(request)
    manager = _manager(request)
    record = await ledger.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="session not found")
    if record.owner != principal.subject:
        raise HTTPException(status_code=403, detail="session belongs to another user")
    await manager.stop_session(session_id)
