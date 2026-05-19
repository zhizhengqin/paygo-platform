from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import get_payment_rates
from app.redis import cache_get, cache_set, session_get

router = APIRouter(prefix="/api/config")


async def _check_auth(request: Request):
    sid = request.cookies.get("session")
    if not sid:
        raise HTTPException(status_code=401, detail="未认证")
    data = await session_get(sid)
    if data is None:
        raise HTTPException(status_code=401, detail="未认证")


@router.get("/payment-rates")
async def list_payment_rates(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get("config:payment-rates")
    if cached:
        return cached
    result = await get_payment_rates(db)
    await cache_set("config:payment-rates", result)
    return result
