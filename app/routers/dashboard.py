from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import get_dashboard_stats, get_enhanced_dashboard_stats
from app.routers.customers import _check_auth
from app.redis import cache_get, cache_set

router = APIRouter(prefix="/api")


@router.get("/dashboard/stats")
async def dashboard_stats(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_dashboard_stats(db)


@router.get("/dashboard/enhanced-stats")
async def enhanced_dashboard_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    mfi_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    await _check_auth(request)
    cache_key = f"dashboard:enhanced:{days}:{mfi_id or 'all'}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    result = await get_enhanced_dashboard_stats(db, days=days, mfi_id=mfi_id)
    await cache_set(cache_key, result, ttl=300)
    return result
