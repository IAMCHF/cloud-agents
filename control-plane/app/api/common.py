"""管理面公共依赖：台账与属主校验。"""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.auth import Principal
from app.ledger import Ledger, SessionRecord


def ledger_from_request(request: Request) -> Ledger:
    ledger = getattr(request.app.state, "ledger", None)
    if not isinstance(ledger, Ledger):
        raise HTTPException(status_code=503, detail="ledger not configured")
    return ledger


async def owned_session(ledger: Ledger, session_id: str, principal: Principal) -> SessionRecord:
    record = await ledger.get(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="session not found")
    if record.owner != principal.subject:
        raise HTTPException(status_code=403, detail="session belongs to another user")
    return record
