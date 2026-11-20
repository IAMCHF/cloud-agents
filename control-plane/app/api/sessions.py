"""P1 会话管理 API（管理面；执行协议仍走 /ws/session 的原生 JSON-RPC）。"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.common import ledger_from_request as _ledger
from app.api.common import owned_session as _owned_session
from app.auth import Principal, require_principal
from app.config import Settings
from app.ledger import AdmissionRejectedError, SessionStateError
from app.metrics import Metrics
from app.sandbox import OpenSandboxError, SandboxManager, SessionHandle

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreateResponse(BaseModel):
    session_id: str
    session_token: str
    sandbox_id: str
    ws_url: str


class SessionSummary(BaseModel):
    session_id: str
    status: str
    created_at: datetime
    ended_at: datetime | None
    archived_at: datetime | None


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


def _reject_admission(request: Request, exc: AdmissionRejectedError) -> NoReturn:
    metrics = _metrics(request)
    if metrics is not None:
        metrics.admission_rejections.labels(reason=exc.reason).inc()
    raise HTTPException(status_code=429, detail=exc.reason) from exc


@router.get("", response_model=list[SessionSummary])
async def list_sessions(
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
    limit: int = 50,
) -> list[SessionSummary]:
    ledger = _ledger(request)
    records = await ledger.list_sessions_for_owner(principal.subject, limit=max(1, min(limit, 200)))
    return [
        SessionSummary(
            session_id=record.session_id,
            status=record.status,
            created_at=record.created_at,
            ended_at=record.ended_at,
            archived_at=record.archived_at,
        )
        for record in records
    ]


@router.post("", response_model=SessionCreateResponse)
async def create_session(
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> SessionCreateResponse:
    settings = _settings(request)
    manager = _manager(request)
    ledger = _ledger(request)
    # 登录即建档：租户按部署默认配额创建，用户刷新 last_seen_at；准入在 T3 改为查库。
    await ledger.ensure_principal(
        principal,
        tenant_max_active_sessions=settings.tenant_default_max_active_sessions,
        tenant_monthly_token_budget=settings.tenant_default_monthly_token_budget,
    )
    try:
        handle = await manager.create_session(principal.subject, principal.tenant_id)
    except AdmissionRejectedError as exc:
        _reject_admission(request, exc)
    except OpenSandboxError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _session_response(settings, handle)


def _session_response(settings: Settings, handle: SessionHandle) -> SessionCreateResponse:
    return SessionCreateResponse(
        session_id=handle.session_id,
        session_token=handle.session_token,
        sandbox_id=handle.sandbox_id,
        ws_url=(
            f"{settings.websocket_base_url}/ws/session/{handle.session_id}"
            f"?token={handle.session_token}"
        ),
    )


@router.post("/{session_id}/sleep", status_code=204)
async def sleep_session(
    session_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> None:
    ledger = _ledger(request)
    manager = _manager(request)
    record = await _owned_session(ledger, session_id, principal)
    if record.status == "ended":
        raise HTTPException(status_code=409, detail="会话已结束")
    try:
        await manager.sleep_session(session_id, force=True)
    except SessionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OpenSandboxError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{session_id}/resume", response_model=SessionCreateResponse)
async def resume_session(
    session_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> SessionCreateResponse:
    settings = _settings(request)
    manager = _manager(request)
    ledger = _ledger(request)
    await _owned_session(ledger, session_id, principal)
    await ledger.ensure_principal(
        principal,
        tenant_max_active_sessions=settings.tenant_default_max_active_sessions,
        tenant_monthly_token_budget=settings.tenant_default_monthly_token_budget,
    )
    try:
        handle = await manager.resume_session(session_id)
    except SessionStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AdmissionRejectedError as exc:
        _reject_admission(request, exc)
    except OpenSandboxError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _session_response(settings, handle)


@router.get("/{session_id}", response_model=SessionStatusResponse)
async def get_session(
    session_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> SessionStatusResponse:
    ledger = _ledger(request)
    manager = _manager(request)
    record = await _owned_session(ledger, session_id, principal)
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
    await _owned_session(ledger, session_id, principal)
    await manager.stop_session(session_id)
