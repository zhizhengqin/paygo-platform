"""Async 数据访问层 — 所有 CRUD 操作替换原 db.py 的内存 dict 实现。"""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer, Token, PaymentRate, SmsRecord, LoanProduct, Contract,
    RepaymentSchedule, RepaymentRecord, _new_id,
)
from app.security import encrypt_secret, decrypt_secret


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

    # 检查 secret_key 唯一绑定（同时检查明文和加密列）
    existing = await db.execute(
        select(Customer).where(Customer.secret_key == secret_key)
    )
    if existing.scalar():
        raise DuplicateSecretKeyError(secret_key)
    # 加密列逐条解密比对
    all_customers = await db.execute(
        select(Customer).where(Customer.secret_key_encrypted.isnot(None))
    )
    for c in all_customers.scalars().all():
        if decrypt_secret(c.secret_key_encrypted) == secret_key:
            raise DuplicateSecretKeyError(secret_key)

    cid = _new_id("C")
    encrypted = encrypt_secret(secret_key)
    c = Customer(
        id=cid, name=name, phone=phone, device_id=device_id,
        secret_key_encrypted=encrypted,
    )
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
                    days: int, count: int, amount: float = 0,
                    contract_id: str = None) -> str:
    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer_id, token=token, days=days,
        count=count, amount=amount, contract_id=contract_id,
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
        "secret_key": decrypt_secret(c.secret_key_encrypted) if c.secret_key_encrypted else (c.secret_key or ""),
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
        "status": t.status or "UNUSED",
        "contract_id": t.contract_id,
        "voided_by": t.voided_by,
        "void_reason": t.void_reason,
        "superseded_by": t.superseded_by,
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


# ============================================================
# 等额本息计算
# ============================================================

def calc_amortization(
    loan_amount: Decimal,
    annual_rate: Decimal,
    term_months: int,
    start_date,
) -> list[dict]:
    """等额本息还款计划。返回每期明细 list[dict]"""
    monthly_rate = annual_rate / Decimal("100") / Decimal("12")
    rate_plus_one = Decimal("1") + monthly_rate

    # 月供 = P × r × (1+r)^n / ((1+r)^n - 1)
    factor = rate_plus_one ** term_months
    monthly = (loan_amount * monthly_rate * factor) / (factor - Decimal("1"))
    monthly = monthly.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    schedules = []
    balance = loan_amount
    for i in range(1, term_months + 1):
        interest = (balance * monthly_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        principal = (monthly - interest).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # 最后一期：确保余额归零
        if i == term_months:
            principal = balance
            monthly = principal + interest
        balance = (balance - principal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        schedules.append({
            "period_no": i,
            "due_date": start_date + relativedelta(months=i),
            "principal": principal,
            "interest": interest,
            "total": monthly if i < term_months else (principal + interest),
            "balance": balance,
            "status": "pending",
        })
    return schedules


# ============================================================
# 合同编号生成
# ============================================================

async def generate_contract_no(db: AsyncSession) -> str:
    """生成合同编号：KH-YYYY-NNNNN"""
    now = datetime.now()
    year = now.year
    from sqlalchemy import extract
    result = await db.execute(
        select(func.count()).select_from(Contract).where(
            extract("year", Contract.created_at) == year
        )
    )
    count = (result.scalar() or 0) + 1
    return f"KH-{year}-{count:05d}"


# ============================================================
# 贷款产品 CRUD
# ============================================================

async def add_loan_product(
    db: AsyncSession, name: str, capacity_kw: Decimal, term_months: int,
    interest_rate: Decimal, down_payment_pct: Decimal, total_amount: Decimal,
) -> str:
    pid = _new_id("LP")
    lp = LoanProduct(
        id=pid, name=name, capacity_kw=capacity_kw, term_months=term_months,
        interest_rate=interest_rate, down_payment_pct=down_payment_pct,
        total_amount=total_amount,
    )
    db.add(lp)
    await db.commit()
    return pid


async def get_loan_products(db: AsyncSession, status: str = None) -> list[dict]:
    q = select(LoanProduct).order_by(LoanProduct.capacity_kw)
    if status:
        q = q.where(LoanProduct.status == status)
    result = await db.execute(q)
    return [_loan_product_to_dict(lp) for lp in result.scalars().all()]


async def get_loan_product(db: AsyncSession, pid: str) -> dict | None:
    result = await db.execute(select(LoanProduct).where(LoanProduct.id == pid))
    lp = result.scalar()
    return _loan_product_to_dict(lp) if lp else None


async def update_loan_product(db: AsyncSession, pid: str, **kwargs) -> bool:
    result = await db.execute(select(LoanProduct).where(LoanProduct.id == pid))
    lp = result.scalar()
    if not lp:
        return False
    for k, v in kwargs.items():
        if hasattr(lp, k):
            setattr(lp, k, v)
    await db.commit()
    return True


async def disable_loan_product(db: AsyncSession, pid: str) -> bool:
    return await update_loan_product(db, pid, status="disabled")


def _loan_product_to_dict(lp: LoanProduct) -> dict:
    return {
        "id": lp.id,
        "name": lp.name,
        "capacity_kw": float(lp.capacity_kw) if lp.capacity_kw else 0,
        "term_months": lp.term_months,
        "interest_rate": float(lp.interest_rate) if lp.interest_rate else 0,
        "down_payment_pct": float(lp.down_payment_pct) if lp.down_payment_pct else 0,
        "total_amount": float(lp.total_amount) if lp.total_amount else 0,
        "status": lp.status,
        "created_at": lp.created_at.strftime("%Y-%m-%d %H:%M:%S") if lp.created_at else None,
    }


# ============================================================
# 合同 CRUD
# ============================================================

async def add_contract(
    db: AsyncSession, customer_id: str, product_id: str,
    down_payment: Decimal, loan_amount: Decimal, monthly_payment: Decimal,
    start_date, end_date,
) -> str:
    cid = _new_id("CT")
    contract_no = await generate_contract_no(db)
    c = Contract(
        id=cid, contract_no=contract_no, customer_id=customer_id,
        product_id=product_id, down_payment=down_payment, loan_amount=loan_amount,
        monthly_payment=monthly_payment, start_date=start_date, end_date=end_date,
    )
    db.add(c)
    await db.commit()
    return cid


async def get_contracts(db: AsyncSession, status: str = None,
                        customer_id: str = None) -> list[dict]:
    q = select(Contract).order_by(Contract.created_at.desc())
    if status:
        q = q.where(Contract.status == status)
    if customer_id:
        q = q.where(Contract.customer_id == customer_id)
    result = await db.execute(q)
    contracts = result.scalars().all()
    return [_contract_to_dict(c) for c in contracts]


async def get_contract(db: AsyncSession, cid: str) -> dict | None:
    result = await db.execute(select(Contract).where(Contract.id == cid))
    c = result.scalar()
    return _contract_to_dict(c) if c else None


async def get_contract_with_schedules(db: AsyncSession, cid: str) -> dict | None:
    result = await db.execute(
        select(Contract).where(Contract.id == cid).options(
            selectinload(Contract.schedules)
        )
    )
    c = result.unique().scalar_one_or_none()
    if not c:
        return None
    d = _contract_to_dict(c)
    d["schedules"] = []
    if c.schedules:
        d["schedules"] = sorted(
            [_schedule_to_dict(s) for s in c.schedules],
            key=lambda x: x["period_no"],
        )
    return d


async def approve_contract(db: AsyncSession, cid: str) -> dict | None:
    """审批通过合同：生成还款计划 + 状态变更"""
    result = await db.execute(select(Contract).where(Contract.id == cid))
    c = result.scalar()
    if not c or c.status != "draft":
        return None

    lp_result = await db.execute(select(LoanProduct).where(LoanProduct.id == c.product_id))
    lp = lp_result.scalar()
    if not lp:
        return None

    schedules_data = calc_amortization(
        loan_amount=c.loan_amount,
        annual_rate=lp.interest_rate,
        term_months=lp.term_months,
        start_date=c.start_date,
    )

    for s in schedules_data:
        rs = RepaymentSchedule(
            id=_new_id("RS"),
            contract_id=c.id,
            period_no=s["period_no"],
            due_date=s["due_date"],
            principal=s["principal"],
            interest=s["interest"],
            total=s["total"],
            balance=s["balance"],
            status="pending",
        )
        db.add(rs)

    c.status = "active"
    c.approved_at = datetime.now()
    c.remaining_days = lp.term_months * 30
    await db.commit()
    await db.refresh(c, ["schedules"])

    return await get_contract_with_schedules(db, cid)


async def update_contract_status(db: AsyncSession, cid: str, status: str) -> bool:
    valid_statuses = ["draft", "approved", "active", "overdue", "closed", "recovered"]
    if status not in valid_statuses:
        return False
    result = await db.execute(select(Contract).where(Contract.id == cid))
    c = result.scalar()
    if not c:
        return False
    c.status = status
    await db.commit()
    return True


def _contract_to_dict(c: Contract) -> dict:
    return {
        "id": c.id,
        "contract_no": c.contract_no,
        "customer_id": c.customer_id,
        "customer_name": c.customer.name if c.customer else None,
        "product_id": c.product_id,
        "down_payment": float(c.down_payment) if c.down_payment else 0,
        "loan_amount": float(c.loan_amount) if c.loan_amount else 0,
        "monthly_payment": float(c.monthly_payment) if c.monthly_payment else 0,
        "status": c.status,
        "start_date": c.start_date.strftime("%Y-%m-%d") if c.start_date else None,
        "end_date": c.end_date.strftime("%Y-%m-%d") if c.end_date else None,
        "remaining_days": c.remaining_days,
        "approved_at": c.approved_at.strftime("%Y-%m-%d %H:%M:%S") if c.approved_at else None,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else None,
    }


def _schedule_to_dict(s: RepaymentSchedule) -> dict:
    return {
        "id": s.id,
        "period_no": s.period_no,
        "due_date": s.due_date.strftime("%Y-%m-%d") if s.due_date else None,
        "principal": float(s.principal) if s.principal else 0,
        "interest": float(s.interest) if s.interest else 0,
        "total": float(s.total) if s.total else 0,
        "balance": float(s.balance) if s.balance else 0,
        "status": s.status,
    }


# ============================================================
# 贷款产品种子数据
# ============================================================

async def seed_loan_products(db: AsyncSession):
    """初始化 5 档贷款产品（幂等：已存在则跳过）"""
    existing = await db.execute(select(func.count()).select_from(LoanProduct))
    if existing.scalar() > 0:
        return

    products = [
        ("6kW-12月基础", Decimal("6.00"), 12, Decimal("10.00"), Decimal("20.00"), Decimal("690.00")),
        ("10kW-24月标准", Decimal("10.00"), 24, Decimal("12.00"), Decimal("20.00"), Decimal("1150.00")),
        ("15kW-24月标准", Decimal("15.00"), 24, Decimal("12.00"), Decimal("20.00"), Decimal("1725.00")),
        ("20kW-36月进阶", Decimal("20.00"), 36, Decimal("14.00"), Decimal("20.00"), Decimal("2300.00")),
        ("30kW-36月旗舰", Decimal("30.00"), 36, Decimal("14.00"), Decimal("20.00"), Decimal("3450.00")),
    ]
    for name, cap, term, rate, dp_pct, total in products:
        pid = _new_id("LP")
        db.add(LoanProduct(
            id=pid, name=name, capacity_kw=cap, term_months=term,
            interest_rate=rate, down_payment_pct=dp_pct, total_amount=total,
        ))
    await db.commit()


async def migrate_secret_keys_to_encrypted(db: AsyncSession) -> int:
    """将现有明文 secret_key 迁移至 secret_key_encrypted 列。返回迁移条数。"""
    from sqlalchemy import and_
    result = await db.execute(
        select(Customer).where(
            and_(
                Customer.secret_key.isnot(None),
                Customer.secret_key_encrypted.is_(None),
            )
        )
    )
    customers = result.scalars().all()
    count = 0
    for c in customers:
        if c.secret_key:
            c.secret_key_encrypted = encrypt_secret(c.secret_key)
            c.secret_key = None
            count += 1
    if count > 0:
        await db.commit()
    return count


# ============================================================
# 还款记录 + 还款标记 + 逾期检测 + 结清
# ============================================================

async def mark_schedule_paid(
    db: AsyncSession, schedule_id: str, amount: Decimal,
) -> dict | None:
    """标记一期还款为已付：检查状态 → 生成 Token → 创建还款记录 → 更新状态"""
    rs_result = await db.execute(
        select(RepaymentSchedule).where(RepaymentSchedule.id == schedule_id)
    )
    rs = rs_result.scalar()
    if not rs or rs.status == "paid":
        return None

    ct = await db.get(Contract, rs.contract_id)
    if not ct:
        return None
    customer = await db.get(Customer, ct.customer_id)
    if not customer:
        return None

    raw_key = decrypt_secret(customer.secret_key_encrypted) if customer.secret_key_encrypted else customer.secret_key
    if not raw_key:
        return None

    from openpaygo import generate_token, TokenType
    new_count, token_str = generate_token(
        secret_key=raw_key,
        count=customer.count,
        value=30,
        token_type=TokenType.ADD_TIME,
    )

    customer.count = new_count
    customer.status = "active"

    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer.id, token=token_str, days=30,
        count=new_count, amount=amount, contract_id=ct.id,
    )
    db.add(t)
    await db.flush()  # 先刷入 Token 以便 RepaymentRecord FK 引用

    rrid = _new_id("RR")
    rr = RepaymentRecord(
        id=rrid, contract_id=ct.id, schedule_id=rs.id, token_id=tid,
        amount=amount, payment_method="Bakong",
    )
    db.add(rr)

    rs.status = "paid"
    await db.commit()

    return {
        "id": rrid,
        "contract_id": ct.id,
        "schedule_id": rs.id,
        "token_id": tid,
        "token": token_str,
        "amount": float(amount),
        "paid_at": rr.paid_at.strftime("%Y-%m-%d %H:%M:%S") if rr.paid_at else None,
    }


async def check_overdue_schedules(db: AsyncSession) -> int:
    """检查逾期未付的还款计划 → 标记 overdue → 合同联动 → 设备锁定"""
    from datetime import date
    today = date.today()

    result = await db.execute(
        select(RepaymentSchedule).where(
            RepaymentSchedule.status == "pending",
            RepaymentSchedule.due_date < today,
        )
    )
    overdue_schedules = result.scalars().all()

    affected_contracts = set()
    for rs in overdue_schedules:
        rs.status = "overdue"
        affected_contracts.add(rs.contract_id)

    for ct_id in affected_contracts:
        ct = await db.get(Contract, ct_id)
        if ct and ct.status == "active":
            ct.status = "overdue"
            customer = await db.get(Customer, ct.customer_id)
            if customer:
                customer.status = "locked"
                customer.locked_at = datetime.now()

    if overdue_schedules:
        await db.commit()

    return len(overdue_schedules)


async def settle_contract(db: AsyncSession, cid: str) -> dict | None:
    """结清合同：生成 DISABLE_PAYG Token → 标记所有计划已付 → 永久解锁"""
    ct = await db.get(Contract, cid)
    if not ct or ct.status not in ("active", "overdue"):
        return None

    customer = await db.get(Customer, ct.customer_id)
    if not customer:
        return None

    raw_key = decrypt_secret(customer.secret_key_encrypted) if customer.secret_key_encrypted else customer.secret_key
    if not raw_key:
        return None

    from openpaygo import generate_token, TokenType
    new_count, token_str = generate_token(
        secret_key=raw_key,
        count=customer.count,
        token_type=TokenType.DISABLE_PAYG,
    )

    customer.count = new_count
    customer.status = "permanent"

    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer.id, token=token_str, days=-1,
        count=new_count, amount=0, contract_id=ct.id,
    )
    db.add(t)
    await db.flush()  # 先刷入 Token 以便 RepaymentRecord FK 引用

    # Mark all unpaid schedules as paid
    schedules_result = await db.execute(
        select(RepaymentSchedule).where(
            RepaymentSchedule.contract_id == cid,
            RepaymentSchedule.status != "paid",
        )
    )
    unpaid_schedules = schedules_result.scalars().all()
    first_schedule_id = unpaid_schedules[0].id if unpaid_schedules else None
    for rs in unpaid_schedules:
        rs.status = "paid"

    # Create repayment record
    rrid = _new_id("RR")
    rr = RepaymentRecord(
        id=rrid, contract_id=ct.id, schedule_id=first_schedule_id,
        token_id=tid, amount=ct.loan_amount, payment_method="SETTLEMENT",
    )
    db.add(rr)

    ct.status = "closed"
    ct.remaining_days = 0

    message = (
        f"[PAYGO Solar] 恭喜！您的贷款已全部结清。"
        f"设备永久解锁码：{token_str}。请在您的设备中输入此码以永久解锁。"
    )

    # Record SMS
    sms_id = _new_id("S")
    sms = SmsRecord(id=sms_id, customer_id=customer.id, to_phone=customer.phone, message=message)
    db.add(sms)

    await db.commit()

    return {
        "contract_id": cid,
        "status": "closed",
        "token": token_str,
        "sms": {"to": customer.phone, "message": message},
    }


# ============================================================
# Token 管理增强 — 筛选/统计/详情/补发/作废
# ============================================================

async def get_tokens_filtered(
    db: AsyncSession,
    customer_id: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Token 列表 — 支持按客户/状态筛选 + 分页"""
    q = select(Token).order_by(Token.generated_at.desc())
    if customer_id:
        q = q.where(Token.customer_id == customer_id)
    if status:
        q = q.where(Token.status == status)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return [_token_to_dict(t) for t in result.scalars().all()]


async def get_token_stats(db: AsyncSession) -> dict:
    """Token 统计卡片"""
    from datetime import datetime
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_result = await db.execute(select(func.count()).select_from(Token))
    total = total_result.scalar() or 0

    today_result = await db.execute(
        select(func.count()).select_from(Token).where(Token.generated_at >= today_start)
    )
    today = today_result.scalar() or 0

    month_result = await db.execute(
        select(func.count()).select_from(Token).where(Token.generated_at >= month_start)
    )
    this_month = month_result.scalar() or 0

    superseded_result = await db.execute(
        select(func.count()).select_from(Token).where(Token.status == "SUPERSEDED")
    )
    superseded = superseded_result.scalar() or 0

    return {
        "total": total,
        "today": today,
        "this_month": this_month,
        "superseded": superseded,
    }


async def get_token_detail(db: AsyncSession, tid: str) -> dict | None:
    """Token 详情 — 含客户名和关联信息"""
    result = await db.execute(
        select(Token, Customer.name)
        .join(Customer, Token.customer_id == Customer.id, isouter=True)
        .where(Token.id == tid)
    )
    row = result.first()
    if not row:
        return None
    t, customer_name = row
    d = _token_to_dict(t)
    d["customer_name"] = customer_name or "-"
    d["status"] = t.status or "UNUSED"
    d["voided_by"] = t.voided_by
    d["void_reason"] = t.void_reason
    d["voided_at"] = t.voided_at.strftime("%Y-%m-%d %H:%M:%S") if t.voided_at else None
    d["superseded_by"] = t.superseded_by
    return d


async def reissue_token(db: AsyncSession, original_tid: str, reason: str = "") -> dict | None:
    """补发 Token：验证原 Token 状态 → 生成新 Token(Counter+1) → 标记原 Token"""
    orig = await db.get(Token, original_tid)
    if not orig or orig.status == "SUPERSEDED":
        return None

    customer = await db.get(Customer, orig.customer_id)
    if not customer:
        return None

    raw_key = decrypt_secret(customer.secret_key_encrypted) if customer.secret_key_encrypted else customer.secret_key
    if not raw_key:
        return None

    from openpaygo import generate_token, TokenType as OT
    new_count, token_str = generate_token(
        secret_key=raw_key, count=customer.count + 1,
        value=orig.days if orig.days != -1 else None,
        token_type=OT.DISABLE_PAYG if orig.days == -1 else OT.ADD_TIME,
    )
    customer.count = new_count

    new_tid = _new_id("T")
    new_t = Token(
        id=new_tid, customer_id=customer.id, token=token_str,
        days=orig.days, count=new_count, amount=float(orig.amount or 0),
        contract_id=orig.contract_id, status="UNUSED",
    )
    db.add(new_t)
    await db.flush()

    orig.status = "SUPERSEDED"
    orig.superseded_by = new_tid
    orig.void_reason = reason or "补发"
    orig.voided_at = datetime.now()

    await db.commit()
    return {"token_id": new_tid, "token": token_str, "days": orig.days,
            "superseded_id": original_tid}


async def void_token(db: AsyncSession, tid: str, operator: str, reason: str = "") -> bool:
    """作废 Token：标记 SUPERSEDED + 记录操作人"""
    t = await db.get(Token, tid)
    if not t:
        return False
    t.status = "SUPERSEDED"
    t.voided_by = operator
    t.void_reason = reason
    t.voided_at = datetime.now()
    await db.commit()
    return True
