"""Async 数据访问层 — 所有 CRUD 操作替换原 db.py 的内存 dict 实现。"""
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Token, PaymentRate, SmsRecord, _new_id


class DuplicateDeviceError(Exception):
    def __init__(self, device_id: str):
        self.device_id = device_id
        super().__init__(f"device_id '{device_id}' already exists")


class DuplicateSecretKeyError(Exception):
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        super().__init__(f"secret_key already bound to another device")


# ---- Customers ----

async def get_customers(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Customer).order_by(Customer.created_at.desc()))
    return [_customer_to_dict(c) for c in result.scalars().all()]


async def get_customer(db: AsyncSession, customer_id: str) -> dict | None:
    c = await db.get(Customer, customer_id)
    return _customer_to_dict(c) if c else None


async def add_customer(db: AsyncSession, name: str, phone: str,
                       device_id: str, secret_key: str) -> str:
    # 检查 device_id 唯一性
    existing = await db.execute(
        select(Customer).where(Customer.device_id == device_id)
    )
    if existing.scalar():
        raise DuplicateDeviceError(device_id)

    # 检查 secret_key 唯一绑定
    existing = await db.execute(
        select(Customer).where(Customer.secret_key == secret_key)
    )
    if existing.scalar():
        raise DuplicateSecretKeyError(secret_key)

    cid = _new_id("C")
    c = Customer(id=cid, name=name, phone=phone, device_id=device_id, secret_key=secret_key)
    db.add(c)
    await db.commit()
    return cid


async def delete_customer(db: AsyncSession, customer_id: str) -> bool:
    c = await db.get(Customer, customer_id)
    if c is None:
        return False
    await db.delete(c)
    await db.commit()
    return True


async def update_customer_status(db: AsyncSession, customer_id: str, status: str) -> bool:
    c = await db.get(Customer, customer_id)
    if c is None:
        return False
    c.status = status
    if status == "locked":
        c.locked_at = datetime.now()
    await db.commit()
    return True


async def set_customer_count(db: AsyncSession, customer_id: str, new_count: int):
    c = await db.get(Customer, customer_id)
    if c:
        c.count = new_count
        await db.commit()


# ---- Tokens ----

async def get_tokens(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Token).order_by(Token.generated_at.desc()))
    return [_token_to_dict(t) for t in result.scalars().all()]


async def add_token(db: AsyncSession, customer_id: str, token: str,
                    days: int, count: int, amount: float = 0) -> str:
    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer_id, token=token, days=days,
        count=count, amount=amount,
        generated_at=datetime.now(), expires_at=datetime.now() + timedelta(days=7),
    )
    db.add(t)
    await db.commit()
    return tid


# ---- Payment Rates ----

async def get_payment_rates(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(PaymentRate).order_by(PaymentRate.amount))
    return [{"amount": float(r.amount), "days": r.days} for r in result.scalars().all()]


async def get_days_for_amount(db: AsyncSession, amount: float) -> int:
    result = await db.execute(
        select(PaymentRate.days).where(PaymentRate.amount == amount)
    )
    days = result.scalar()
    return days if days is not None else 0


async def seed_payment_rates(db: AsyncSession):
    """初始化支付汇率，已存在则跳过。"""
    existing = await db.execute(select(func.count()).select_from(PaymentRate))
    if existing.scalar() > 0:
        return
    db.add_all([
        PaymentRate(amount=5, days=30),
        PaymentRate(amount=10, days=60),
    ])
    await db.commit()


# ---- SMS Records ----

async def add_sms_record(db: AsyncSession, customer_id: str, to_phone: str,
                         message: str) -> str:
    sid = _new_id("S")
    r = SmsRecord(id=sid, customer_id=customer_id, to_phone=to_phone, message=message)
    db.add(r)
    await db.commit()
    return sid


async def get_sms_records(db: AsyncSession, customer_id: str = None) -> list[dict]:
    stmt = select(SmsRecord).order_by(SmsRecord.sent_at.desc())
    if customer_id:
        stmt = stmt.where(SmsRecord.customer_id == customer_id)
    result = await db.execute(stmt)
    return [_sms_to_dict(r) for r in result.scalars().all()]


# ---- Serialization helpers ----

def _customer_to_dict(c: Customer) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "device_id": c.device_id,
        "secret_key": c.secret_key,
        "count": c.count,
        "status": c.status,
        "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else None,
        "locked_at": c.locked_at.strftime("%Y-%m-%d %H:%M:%S") if c.locked_at else None,
    }


def _token_to_dict(t: Token) -> dict:
    return {
        "id": t.id,
        "customer_id": t.customer_id,
        "token": t.token,
        "days": t.days,
        "amount": float(t.amount) if t.amount else 0,
        "count": t.count,
        "generated_at": t.generated_at.strftime("%Y-%m-%d %H:%M:%S") if t.generated_at else None,
        "expires_at": t.expires_at.strftime("%Y-%m-%d %H:%M:%S") if t.expires_at else None,
    }


def _sms_to_dict(r: SmsRecord) -> dict:
    return {
        "id": r.id,
        "customer_id": r.customer_id,
        "to_phone": r.to_phone,
        "message": r.message,
        "sent_at": r.sent_at.strftime("%Y-%m-%d %H:%M:%S") if r.sent_at else None,
    }


async def get_dashboard_stats(db: AsyncSession) -> dict:
    from datetime import datetime

    total_result = await db.execute(select(func.count()).select_from(Customer))
    total_customers = total_result.scalar() or 0

    active_result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.status == "active")
    )
    active_devices = active_result.scalar() or 0

    locked_result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.status == "locked")
    )
    locked_devices = locked_result.scalar() or 0

    permanent_result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.status == "permanent")
    )
    permanent_devices = permanent_result.scalar() or 0

    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Token.amount), 0)).where(
            Token.generated_at >= month_start
        )
    )
    monthly_revenue = float(revenue_result.scalar() or 0)

    token_count_result = await db.execute(
        select(func.count()).select_from(Token).where(Token.generated_at >= month_start)
    )
    total_tokens = token_count_result.scalar() or 0

    recent_result = await db.execute(
        select(Token, Customer.name)
        .join(Customer, Token.customer_id == Customer.id, isouter=True)
        .order_by(Token.generated_at.desc())
        .limit(20)
    )
    recent_transactions = []
    for t, customer_name in recent_result.all():
        recent_transactions.append({
            "id": t.id,
            "customer_name": customer_name or "-",
            "amount": float(t.amount) if t.amount else 0,
            "days": t.days,
            "token": t.token,
            "generated_at": t.generated_at.strftime("%Y-%m-%d %H:%M:%S") if t.generated_at else None,
        })

    return {
        "total_customers": total_customers,
        "active_devices": active_devices,
        "locked_devices": locked_devices,
        "permanent_devices": permanent_devices,
        "monthly_revenue": monthly_revenue,
        "total_tokens": total_tokens,
        "recent_transactions": recent_transactions,
    }
