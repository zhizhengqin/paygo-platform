"""系统设置 API router"""
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PaymentRate, SmsTemplate, User, _new_id
from app.routers.customers import _check_auth
from app.security import hash_password

router = APIRouter(prefix="/api/settings")


# ---- 健康检查 ----
@router.get("/health")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    from app.redis import get_redis
    r = get_redis()
    redis_status = "ok"
    if r:
        try:
            await r.ping()
        except Exception:
            redis_status = "error"
    else:
        redis_status = "error"
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {"database": db_status, "redis": redis_status, "status": overall}


# ---- 支付汇率 ----
@router.get("/payment-rates")
async def get_rates(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    result = await db.execute(select(PaymentRate).order_by(PaymentRate.amount))
    return [{"id": r.id, "amount": float(r.amount), "days": r.days} for r in result.scalars().all()]


class RateUpdate(BaseModel):
    amount: float
    days: int


@router.post("/payment-rates")
async def add_rate(body: RateUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    from decimal import Decimal
    # 检查重复金额
    existing = await db.execute(select(PaymentRate).where(PaymentRate.amount == Decimal(str(body.amount))))
    if existing.scalar():
        raise HTTPException(400, f"金额 ${body.amount:.2f} 的汇率已存在")
    r = PaymentRate(amount=Decimal(str(body.amount)), days=body.days)
    db.add(r)
    await db.commit()
    return {"ok": True}


@router.delete("/payment-rates/{rid}")
async def delete_rate(rid: int, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    r = await db.get(PaymentRate, rid)
    if not r:
        raise HTTPException(404, "汇率不存在")
    await db.delete(r)
    await db.commit()
    return {"ok": True}


# ---- SMS 模板 ----
@router.get("/sms-templates")
async def get_templates(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    result = await db.execute(select(SmsTemplate).order_by(SmsTemplate.code))
    return [{"id": t.id, "code": t.code, "language": t.language, "content": t.content} for t in result.scalars().all()]


class TemplateUpdate(BaseModel):
    code: str
    language: str
    content: str


@router.post("/sms-templates")
async def save_template(body: TemplateUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    t = SmsTemplate(
        id=_new_id("ST"), code=body.code,
        language=body.language, content=body.content,
    )
    db.add(t)
    await db.commit()
    return {"ok": True}


# ---- 用户管理 ----
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "readonly"


@router.get("/users")
async def list_users(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    result = await db.execute(select(User).order_by(User.username))
    return [{"id": u.id, "username": u.username, "role": u.role, "status": u.status} for u in result.scalars().all()]


@router.post("/users")
async def create_user(body: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    h = hash_password(body.password)
    u = User(id=_new_id("U"), username=body.username, password_hash=h, role=body.role)
    db.add(u)
    await db.commit()
    return {"id": u.id, "username": u.username}


@router.delete("/users/{uid}")
async def delete_user(uid: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    u = await db.get(User, uid)
    if not u:
        raise HTTPException(404, "用户不存在")
    await db.delete(u)
    await db.commit()
    return {"ok": True}
