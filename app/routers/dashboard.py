from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import get_dashboard_stats
from app.routers.customers import _check_auth

router = APIRouter(prefix="/api")


@router.get("/dashboard/stats")
async def dashboard_stats(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_dashboard_stats(db)
