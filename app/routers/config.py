from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import get_payment_rates
from app.redis import cache_get, cache_set, session_get

router = APIRouter(prefix="/api/config")


async def _check_auth(request: Request):
    # JWT Bearer token（云部署 / API 客户端）
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        from app.security import decode_token
        token = auth_header[7:]
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            return payload

    # JWT cookie（浏览器端云部署）
    jwt_cookie = request.cookies.get("access_token")
    if jwt_cookie:
        from app.security import decode_token
        payload = decode_token(jwt_cookie)
        if payload and payload.get("type") == "access":
            return payload

    # Session cookie（兼容旧版）
    sid = request.cookies.get("session")
    if not sid:
        raise HTTPException(status_code=401, detail="未认证")
    data = await session_get(sid)
    if data is None:
        raise HTTPException(status_code=401, detail="未认证")
    return data


@router.get("/payment-rates")
async def list_payment_rates(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get("config:payment-rates")
    if cached:
        return cached
    result = await get_payment_rates(db)
    await cache_set("config:payment-rates", result)
    return result
