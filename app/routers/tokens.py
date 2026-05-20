"""Token 管理 API router"""
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import (
    get_tokens_filtered, get_token_stats, get_token_detail,
    reissue_token, void_token,
)
from app.routers.customers import _check_auth

router = APIRouter(prefix="/api/tokens")


class VoidRequest(BaseModel):
    reason: str = ""


class ReissueRequest(BaseModel):
    reason: str = ""


@router.get("/stats")
async def api_token_stats(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_token_stats(db)


@router.get("")
async def api_get_tokens(
    request: Request,
    customer_id: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    await _check_auth(request)
    return await get_tokens_filtered(db, customer_id=customer_id, status=status,
                                     limit=limit, offset=offset)


@router.get("/{tid}")
async def api_token_detail(tid: str, request: Request,
                           db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    detail = await get_token_detail(db, tid)
    if not detail:
        raise HTTPException(404, "Token 不存在")
    return detail


@router.post("/{tid}/reissue")
async def api_reissue_token(tid: str, body: ReissueRequest, request: Request,
                            db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    result = await reissue_token(db, tid, body.reason)
    if not result:
        raise HTTPException(400, "补发失败（Token 不存在或已被作废）")
    return result


@router.post("/{tid}/void")
async def api_void_token(tid: str, body: VoidRequest, request: Request,
                         db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    from app.redis import session_get
    sid = request.cookies.get("session")
    session_data = await session_get(sid) if sid else None
    operator = session_data.get("username", "unknown") if session_data else "unknown"

    ok = await void_token(db, tid, operator, body.reason)
    if not ok:
        raise HTTPException(404, "Token 不存在")
    return {"ok": True}
