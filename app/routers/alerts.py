"""告警中心 API router"""
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import (
    get_alert_rules, get_alert_stats, get_alerts, get_alert_detail,
    create_alert, claim_alert, resolve_alert, escalate_alert,
)
from app.routers.customers import _check_auth

router = APIRouter(prefix="/api/alerts")


class AlertCreate(BaseModel):
    rule_code: str
    title: str
    detail: str = None
    level: str = "P2"
    contract_id: str = None
    customer_id: str = None


class ResolveRequest(BaseModel):
    note: str = ""


@router.get("/rules")
async def api_rules(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_alert_rules(db)


@router.get("/stats")
async def api_stats(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_alert_stats(db)


@router.get("")
async def api_list(request: Request, status: str = None, level: str = None,
                   db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_alerts(db, status=status, level=level)


@router.post("")
async def api_create(body: AlertCreate, request: Request,
                     db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    aid = await create_alert(db, body.rule_code, body.title,
                             contract_id=body.contract_id, customer_id=body.customer_id,
                             detail=body.detail, level=body.level)
    return {"id": aid}


@router.get("/{aid}")
async def api_detail(aid: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    d = await get_alert_detail(db, aid)
    if not d: raise HTTPException(404, "告警不存在")
    return d


@router.post("/{aid}/claim")
async def api_claim(aid: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    from app.redis import session_get
    sid = request.cookies.get("session")
    session_data = await session_get(sid) if sid else None
    operator = session_data.get("username", "unknown") if session_data else "unknown"
    ok = await claim_alert(db, aid, operator)
    if not ok: raise HTTPException(400, "认领失败（告警状态非pending）")
    return {"ok": True}


@router.post("/{aid}/resolve")
async def api_resolve(aid: str, body: ResolveRequest, request: Request,
                      db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await resolve_alert(db, aid, body.note)
    if not ok: raise HTTPException(400, "解决失败")
    return {"ok": True}


@router.post("/{aid}/escalate")
async def api_escalate(aid: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await escalate_alert(db, aid)
    if not ok: raise HTTPException(404, "告警不存在")
    return {"ok": True}
