"""管理面公共依赖：台账、属主校验与会话 token 鉴权。"""

from __future__ import annotations

from fastapi import HTTPException, Request
from starlette.requests import HTTPConnection

from app.auth import Principal
from app.bootstrap import Components
from app.bridge.hub import SessionHub
from app.ledger import Ledger, SessionRecord


def components_from(connection: HTTPConnection) -> Components:
    components = getattr(connection.app.state, "components", None)
    if not isinstance(components, Components):
        raise HTTPException(status_code=503, detail="components not configured")
    return components


def hub_from(connection: HTTPConnection) -> SessionHub:
    hub = getattr(connection.app.state, "bridge_hub", None)
    if not isinstance(hub, SessionHub):
        raise HTTPException(status_code=503, detail="bridge hub not configured")
    return hub


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


async def running_record_by_token(
    components: Components, hub: SessionHub, session_id: str, token: str
) -> SessionRecord:
    """按台账校验会话 token：多副本下终端/文件/预览请求可落在任意实例。"""
    if not token:
        raise HTTPException(status_code=401, detail="session token invalid")
    record = await components.ledger.find_session_by_token(token)
    if record is None or record.session_id != session_id or record.status == "ended":
        raise HTTPException(status_code=401, detail="session token invalid")
    if record.status in {"creating", "running"}:
        hub.ensure(session_id, token, record.owner)
    if record.status != "running" or record.sandbox_id is None:
        raise HTTPException(status_code=409, detail="会话未运行，请先恢复会话")
    return record
