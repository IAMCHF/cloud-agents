"""会话卷归档管理面：计划、执行（默认 dry-run）与恢复。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.common import ledger_from_request as _ledger
from app.api.common import owned_session as _owned_session
from app.archive import ArchiveError, ArchiveService
from app.auth import Principal, require_principal

router = APIRouter(prefix="/api/archive", tags=["archive"])


class ArchivePlanModel(BaseModel):
    session_id: str
    workspace: str
    state: str
    target: str
    size_bytes: int | None


class ArchivePlanResponse(BaseModel):
    plans: list[ArchivePlanModel]
    retention_days: int
    dry_run: bool


class ArchiveRunRequest(BaseModel):
    session_ids: list[str] | None = None
    dry_run: bool | None = None


class ArchiveReportModel(BaseModel):
    archived: list[str]
    dry_run: bool
    targets: dict[str, str]
    errors: dict[str, str]


class RestoreResponse(BaseModel):
    session_id: str
    archive_path: str


def _service(request: Request) -> ArchiveService:
    service = getattr(request.app.state, "archive", None)
    if not isinstance(service, ArchiveService):
        raise HTTPException(status_code=503, detail="archive not configured")
    return service


@router.get("/plan", response_model=ArchivePlanResponse)
async def archive_plan(
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> ArchivePlanResponse:
    service = _service(request)
    settings = request.app.state.settings
    try:
        plans = await service.plan(principal.subject)
    except ArchiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ArchivePlanResponse(
        plans=[
            ArchivePlanModel(
                session_id=plan.session_id,
                workspace=plan.workspace,
                state=plan.state,
                target=plan.target,
                size_bytes=plan.size_bytes,
            )
            for plan in plans
        ],
        retention_days=settings.archive_retention_days,
        dry_run=settings.archive_dry_run,
    )


@router.post("/run", response_model=ArchiveReportModel)
async def archive_run(
    payload: ArchiveRunRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
) -> ArchiveReportModel:
    service = _service(request)
    try:
        plans = await service.plan(principal.subject)
        if payload.session_ids is not None:
            wanted = set(payload.session_ids)
            plans = [plan for plan in plans if plan.session_id in wanted]
        report = await service.archive(plans, dry_run=payload.dry_run)
    except ArchiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ArchiveReportModel(
        archived=report.archived,
        dry_run=report.dry_run,
        targets=report.targets,
        errors=report.errors,
    )


@router.post("/{session_id}/restore", response_model=RestoreResponse)
async def archive_restore(
    session_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_principal)],
    force: bool = False,
) -> RestoreResponse:
    ledger = _ledger(request)
    service = _service(request)
    record = await _owned_session(ledger, session_id, principal)
    if record.status in {"creating", "running", "sleeping"}:
        raise HTTPException(status_code=409, detail="会话仍活跃，不能恢复卷")
    try:
        path = await service.restore(record, force=force)
    except ArchiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RestoreResponse(session_id=session_id, archive_path=path)
