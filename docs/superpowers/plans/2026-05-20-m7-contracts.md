# M7 合同与还款计划引擎 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为运营后台新增合同管理模块（贷款产品配置 + 合同全生命周期 + 等额本息还款计划），导航栏新增「合同管理」tab。

**Architecture:** TDD 增量构建：先模型 → 再数据层 → 再 API → 再前端。每一步都有独立测试覆盖。合同审批时自动生成还款计划表，等额本息公式计算月供。

**Tech Stack:** Python FastAPI + SQLAlchemy 2.0 async + Jinja2 + 原生 JS + 纯 CSS（零新依赖）

**Spec:** `docs/superpowers/specs/2026-05-20-m7-contracts-design.md`

---

### Task 1: 新增 ORM 模型（LoanProduct / Contract / RepaymentSchedule）

**Files:**
- Modify: `app/models.py` — 追加 3 个模型类
- Create: `tests/test_contract_models.py` — 模型测试

- [ ] **Step 1: 写模型测试**

```python
# tests/test_contract_models.py
import pytest
from decimal import Decimal
from datetime import date

from app.models import LoanProduct, Contract, RepaymentSchedule


class TestLoanProductModel:
    def test_create_loan_product(self):
        lp = LoanProduct(
            name="10kW-24月标准",
            capacity_kw=Decimal("10.00"),
            term_months=24,
            interest_rate=Decimal("12.00"),
            down_payment_pct=Decimal("20.00"),
            total_amount=Decimal("1150.00"),
        )
        assert lp.name == "10kW-24月标准"
        assert lp.capacity_kw == Decimal("10.00")
        assert lp.term_months == 24
        assert lp.status == "active"

    def test_loan_product_id_generation(self):
        lp = LoanProduct(name="Test")
        assert lp.id is None  # 由数据库生成
        assert lp.status == "active"


class TestContractModel:
    def test_create_contract(self):
        c = Contract(
            contract_no="KH-2026-00001",
            customer_id="Cxxxx",
            product_id="LPxxxx",
            down_payment=Decimal("230.00"),
            loan_amount=Decimal("920.00"),
            monthly_payment=Decimal("47.33"),
            start_date=date(2026, 6, 1),
            end_date=date(2028, 6, 1),
        )
        assert c.contract_no == "KH-2026-00001"
        assert c.status == "draft"
        assert c.remaining_days == 0

    def test_contract_default_status_draft(self):
        c = Contract(contract_no="KH-2026-00002")
        assert c.status == "draft"


class TestRepaymentScheduleModel:
    def test_create_schedule_item(self):
        rs = RepaymentSchedule(
            contract_id="CTxxxx",
            period_no=1,
            due_date=date(2026, 7, 1),
            principal=Decimal("35.83"),
            interest=Decimal("11.50"),
            total=Decimal("47.33"),
            balance=Decimal("884.17"),
        )
        assert rs.period_no == 1
        assert rs.status == "pending"
        assert rs.total == Decimal("47.33")

    def test_schedule_default_status_pending(self):
        rs = RepaymentSchedule(contract_id="CTxxxx", period_no=5)
        assert rs.status == "pending"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_contract_models.py -v
```
Expected: FAIL — `LoanProduct` not defined (ImportError from app.models)

- [ ] **Step 3: 在 app/models.py 末尾追加 3 个模型**

```python
# app/models.py — 在 DeviceState 类之后追加

class LoanProduct(Base):
    """贷款产品配置表"""
    __tablename__ = "loan_products"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("LP"))
    name = Column(String(100), nullable=False)
    capacity_kw = Column(Numeric(5, 2), nullable=False)
    term_months = Column(Integer, nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False)
    down_payment_pct = Column(Numeric(5, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())


class Contract(Base):
    """合同表"""
    __tablename__ = "contracts"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("CT"))
    contract_no = Column(String(30), nullable=False, unique=True)
    customer_id = Column(String(8), ForeignKey("customers.id"), nullable=False, index=True)
    product_id = Column(String(8), ForeignKey("loan_products.id"), nullable=False)
    down_payment = Column(Numeric(12, 2), nullable=False)
    loan_amount = Column(Numeric(12, 2), nullable=False)
    monthly_payment = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default="draft")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    remaining_days = Column(Integer, default=0)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())

    customer = relationship("Customer", back_populates="contracts")
    schedules = relationship("RepaymentSchedule", back_populates="contract",
                             lazy="selectin", cascade="all, delete-orphan")


class RepaymentSchedule(Base):
    """还款计划表"""
    __tablename__ = "repayment_schedules"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("RS"))
    contract_id = Column(String(8), ForeignKey("contracts.id"), nullable=False, index=True)
    period_no = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    principal = Column(Numeric(10, 2), nullable=False)
    interest = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default="pending")

    contract = relationship("Contract", back_populates="schedules")
```

- [ ] **Step 4: 在 Customer 模型追加 contracts relationship**

在 `app/models.py` 的 `Customer` 类中，`tokens` relationship 后追加：

```python
    contracts = relationship("Contract", back_populates="customer", lazy="selectin",
                             cascade="all, delete-orphan")
```

- [ ] **Step 5: 运行模型测试验证通过**

```bash
pytest tests/test_contract_models.py -v
```
Expected: 5 passed

- [ ] **Step 6: 确认现有测试不受影响**

```bash
pytest tests/test_models.py -v
```
Expected: 8 passed

- [ ] **Step 7: Commit**

```bash
git add app/models.py tests/test_contract_models.py
git commit -m "feat: 新增 LoanProduct / Contract / RepaymentSchedule ORM 模型"
```

---

### Task 2: Store 层 — CRUD + 等额本息计算 + 种子数据

**Files:**
- Modify: `app/store.py` — 追加合同相关函数
- Create: `tests/test_contract_store.py` — store 层测试

- [ ] **Step 1: 写 store 层测试**

```python
# tests/test_contract_store.py
import pytest
from decimal import Decimal
from datetime import date

from app.database import AsyncSessionLocal
from app.store import (
    add_loan_product, get_loan_products, get_loan_product,
    update_loan_product, disable_loan_product,
    add_contract, get_contracts, get_contract, get_contract_with_schedules,
    approve_contract, update_contract_status,
    calc_amortization, generate_contract_no, seed_loan_products,
)


class TestAmortization:
    def test_calc_monthly_payment(self):
        """等额本息月供计算"""
        schedules = calc_amortization(
            loan_amount=Decimal("920.00"),
            annual_rate=Decimal("12.00"),
            term_months=24,
            start_date=date(2026, 6, 1),
        )
        assert len(schedules) == 24
        first = schedules[0]
        assert first["period_no"] == 1
        assert first["due_date"] == date(2026, 7, 1)
        # 月供约 $47.33
        assert abs(float(first["total"]) - 47.33) < 0.10
        assert first["status"] == "pending"
        # 最后一期剩余本金应接近 0
        last = schedules[-1]
        assert abs(float(last["balance"])) < 1.00

    def test_calc_monthly_payment_12month(self):
        """12个月贷款"""
        schedules = calc_amortization(
            loan_amount=Decimal("600.00"),
            annual_rate=Decimal("10.00"),
            term_months=12,
            start_date=date(2026, 1, 1),
        )
        assert len(schedules) == 12
        # 月供约 $52.58
        assert abs(float(schedules[0]["total"]) - 52.58) < 0.10


class TestLoanProductCRUD:
    @pytest.mark.asyncio
    async def test_add_and_list(self):
        async with AsyncSessionLocal() as db:
            await add_loan_product(db, "6kW-12月基础", Decimal("6.00"), 12,
                                   Decimal("10.00"), Decimal("20.00"), Decimal("690.00"))
            products = await get_loan_products(db)
            assert len(products) >= 1
            assert products[0]["name"] == "6kW-12月基础"

    @pytest.mark.asyncio
    async def test_disable_product(self):
        async with AsyncSessionLocal() as db:
            pid = await add_loan_product(db, "Test-Product", Decimal("6.00"), 12,
                                         Decimal("10.00"), Decimal("20.00"), Decimal("690.00"))
            await disable_loan_product(db, pid)
            p = await get_loan_product(db, pid)
            assert p["status"] == "disabled"


class TestContractCRUD:
    @pytest.mark.asyncio
    async def test_create_and_get_contract(self):
        async with AsyncSessionLocal() as db:
            # 先创建贷款产品
            pid = await add_loan_product(db, "10kW-24月", Decimal("10.00"), 24,
                                         Decimal("12.00"), Decimal("20.00"), Decimal("1150.00"))
            cid = await add_contract(db, "C1234567", pid,
                                     Decimal("230.00"), Decimal("920.00"),
                                     Decimal("47.33"), date(2026, 6, 1), date(2028, 6, 1))
            assert cid.startswith("CT")

            c = await get_contract(db, cid)
            assert c["contract_no"].startswith("KH-")
            assert c["status"] == "draft"

    @pytest.mark.asyncio
    async def test_approve_contract_generates_schedule(self):
        async with AsyncSessionLocal() as db:
            pid = await add_loan_product(db, "10kW-24月", Decimal("10.00"), 24,
                                         Decimal("12.00"), Decimal("20.00"), Decimal("1150.00"))
            cid = await add_contract(db, "C1234567", pid,
                                     Decimal("230.00"), Decimal("920.00"),
                                     Decimal("47.33"), date(2026, 6, 1), date(2028, 6, 1))
            await approve_contract(db, cid)

            c = await get_contract_with_schedules(db, cid)
            assert c["status"] == "active"
            assert c["approved_at"] is not None
            assert len(c["schedules"]) == 24

    @pytest.mark.asyncio
    async def test_contract_status_transitions(self):
        async with AsyncSessionLocal() as db:
            pid = await add_loan_product(db, "10kW-24月", Decimal("10.00"), 24,
                                         Decimal("12.00"), Decimal("20.00"), Decimal("1150.00"))
            cid = await add_contract(db, "C1234567", pid,
                                     Decimal("230.00"), Decimal("920.00"),
                                     Decimal("47.33"), date(2026, 6, 1), date(2028, 6, 1))

            await update_contract_status(db, cid, "approved")
            c = await get_contract(db, cid)
            assert c["status"] == "approved"

            await update_contract_status(db, cid, "overdue")
            c = await get_contract(db, cid)
            assert c["status"] == "overdue"


class TestSeedProducts:
    @pytest.mark.asyncio
    async def test_seed_creates_five_products(self):
        async with AsyncSessionLocal() as db:
            await seed_loan_products(db)
            products = await get_loan_products(db)
            capacities = {str(p["capacity_kw"]) for p in products}
            assert "6.00" in capacities
            assert "10.00" in capacities
            assert "30.00" in capacities
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_contract_store.py -v
```
Expected: FAIL — `add_loan_product` not defined (ImportError)

- [ ] **Step 3: 在 app/store.py 末尾追加合同相关函数**

`app/store.py` 需要追加的内容（按函数分组）：

```python
# app/store.py — 在文件末尾追加

# ============================================================
# 等额本息计算
# ============================================================

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta


def calc_amortization(
    loan_amount: Decimal,
    annual_rate: Decimal,
    term_months: int,
    start_date: date,
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
    # 查询本年已有合同数
    from sqlalchemy import extract
    result = await db.execute(
        select(func.count()).select_from(Contract).where(
            extract("year", Contract.created_at) == year
        )
    )
    count = (result.scalar() or 0) + 1
    return f"KH-{year}-{count:05d}"
```

- [ ] **Step 4: 追加贷款产品 CRUD 函数**

```python
# app/store.py — 继续追加

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
```

- [ ] **Step 5: 追加合同 CRUD + 审批 + 状态变更函数**

```python
# app/store.py — 继续追加

# ============================================================
# 合同 CRUD
# ============================================================

async def add_contract(
    db: AsyncSession, customer_id: str, product_id: str,
    down_payment: Decimal, loan_amount: Decimal, monthly_payment: Decimal,
    start_date: date, end_date: date,
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
        select(Contract).where(Contract.id == cid)
    )
    c = result.scalar()
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

    # 获取贷款产品
    lp_result = await db.execute(select(LoanProduct).where(LoanProduct.id == c.product_id))
    lp = lp_result.scalar()
    if not lp:
        return None

    # 生成还款计划
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
```

- [ ] **Step 6: 追加种子数据函数**

```python
# app/store.py — 继续追加

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
```

- [ ] **Step 7: 在 app/store.py 顶部追加新导入**

```python
# app/store.py — 在现有 import 后追加
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from dateutil.relativedelta import relativedelta
from app.models import LoanProduct, Contract, RepaymentSchedule
```

- [ ] **Step 8: 运行 store 测试**

```bash
pytest tests/test_contract_store.py -v
```
Expected: 8 passed

- [ ] **Step 9: 确保现有测试不受影响**

```bash
pytest tests/test_store.py -v
```
Expected: 20 passed

- [ ] **Step 10: Commit**

```bash
git add app/store.py tests/test_contract_store.py
git commit -m "feat: store 层 — 贷款产品 CRUD + 合同CRUD + 等额本息计算 + 种子数据"
```

---

### Task 3: 合同 API Router + 注册

**Files:**
- Create: `app/routers/contracts.py`
- Modify: `app/main.py`
- Create: `tests/test_contracts_api.py`

- [ ] **Step 1: 写 API 测试**

```python
# tests/test_contracts_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


def _login_headers():
    """Helper: 通过登录获取 session cookie"""
    # 该 helper 由 conftest 或 fixture 提供
    pass


@pytest.mark.asyncio
async def test_get_loan_products(async_session, test_client):
    """获取贷款产品列表"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"username": "admin", "password": "admin123"})
        resp = await client.get("/api/loan-products")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # 种子数据应有 5 个产品
        assert len(data) >= 5


@pytest.mark.asyncio
async def test_create_loan_product(async_session, test_client):
    """新增贷款产品"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"username": "admin", "password": "admin123"})
        resp = await client.post("/api/loan-products", json={
            "name": "Test-6kW",
            "capacity_kw": 6.0,
            "term_months": 12,
            "interest_rate": 10.0,
            "down_payment_pct": 20.0,
            "total_amount": 690.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"].startswith("LP")
        assert data["name"] == "Test-6kW"


@pytest.mark.asyncio
async def test_create_contract(async_session, test_client):
    """创建合同（draft 状态）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"username": "admin", "password": "admin123"})
        # 先获取贷款产品
        products = (await client.get("/api/loan-products")).json()
        lp = products[0]
        # 先获取客户
        customers = (await client.get("/api/customers")).json()
        customer = customers[0]

        resp = await client.post("/api/contracts", json={
            "customer_id": customer["id"],
            "product_id": lp["id"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_no"].startswith("KH-")
        assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_approve_contract(async_session, test_client):
    """审批合同 → 生成还款计划"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"username": "admin", "password": "admin123"})
        products = (await client.get("/api/loan-products")).json()
        customers = (await client.get("/api/customers")).json()
        c_resp = await client.post("/api/contracts", json={
            "customer_id": customers[0]["id"],
            "product_id": products[0]["id"],
        })
        contract_id = c_resp.json()["id"]

        resp = await client.put(f"/api/contracts/{contract_id}/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "active"
        assert len(data["schedules"]) > 0


@pytest.mark.asyncio
async def test_contract_status_change(async_session, test_client):
    """修改合同状态"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"username": "admin", "password": "admin123"})
        products = (await client.get("/api/loan-products")).json()
        customers = (await client.get("/api/customers")).json()
        c_resp = await client.post("/api/contracts", json={
            "customer_id": customers[0]["id"],
            "product_id": products[0]["id"],
        })
        cid = c_resp.json()["id"]

        resp = await client.put(f"/api/contracts/{cid}/status", json={"status": "overdue"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "overdue"


@pytest.mark.asyncio
async def test_get_contract_list(async_session, test_client):
    """获取合同列表"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"username": "admin", "password": "admin123"})
        resp = await client.get("/api/contracts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_contracts_api.py -v
```
Expected: FAIL — 404（路由未注册）或 ImportError

- [ ] **Step 3: 创建合同 API router**

```python
# app/routers/contracts.py
from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import (
    get_loan_products, get_loan_product, add_loan_product,
    update_loan_product, disable_loan_product,
    add_contract, get_contracts, get_contract, get_contract_with_schedules,
    approve_contract, update_contract_status, calc_amortization,
)
from app.routers.customers import _check_auth
from app.models import LoanProduct

router = APIRouter(prefix="/api")


# ---- 请求体模型 ----

class LoanProductCreate(BaseModel):
    name: str
    capacity_kw: float
    term_months: int
    interest_rate: float
    down_payment_pct: float
    total_amount: float


class LoanProductUpdate(BaseModel):
    name: str | None = None
    capacity_kw: float | None = None
    term_months: int | None = None
    interest_rate: float | None = None
    down_payment_pct: float | None = None
    total_amount: float | None = None


class ContractCreate(BaseModel):
    customer_id: str
    product_id: str


class StatusUpdate(BaseModel):
    status: str


# ---- 贷款产品 API ----

@router.get("/loan-products")
async def api_get_loan_products(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_loan_products(db)


@router.get("/loan-products/{pid}")
async def api_get_loan_product(pid: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    p = await get_loan_product(db, pid)
    if not p:
        raise HTTPException(404, "产品不存在")
    return p


@router.post("/loan-products")
async def api_create_loan_product(body: LoanProductCreate, request: Request,
                                   db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    pid = await add_loan_product(
        db, body.name, Decimal(str(body.capacity_kw)), body.term_months,
        Decimal(str(body.interest_rate)), Decimal(str(body.down_payment_pct)),
        Decimal(str(body.total_amount)),
    )
    return await get_loan_product(db, pid)


@router.put("/loan-products/{pid}")
async def api_update_loan_product(pid: str, body: LoanProductUpdate,
                                   request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(400, "无更新字段")
    ok = await update_loan_product(db, pid, **kwargs)
    if not ok:
        raise HTTPException(404, "产品不存在")
    return await get_loan_product(db, pid)


@router.delete("/loan-products/{pid}")
async def api_disable_loan_product(pid: str, request: Request,
                                    db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await disable_loan_product(db, pid)
    if not ok:
        raise HTTPException(404, "产品不存在")
    return {"ok": True}


# ---- 合同 API ----

@router.get("/contracts")
async def api_get_contracts(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_contracts(db)


@router.get("/contracts/{cid}")
async def api_get_contract(cid: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    c = await get_contract_with_schedules(db, cid)
    if not c:
        raise HTTPException(404, "合同不存在")
    return c


@router.post("/contracts")
async def api_create_contract(body: ContractCreate, request: Request,
                               db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    # 获取贷款产品计算财务数据
    lp = await get_loan_product(db, body.product_id)
    if not lp:
        raise HTTPException(404, "贷款产品不存在")

    total = Decimal(str(lp["total_amount"]))
    dp_pct = Decimal(str(lp["down_payment_pct"]))
    down_payment = (total * dp_pct / Decimal("100")).quantize(Decimal("0.01"))
    loan_amount = total - down_payment

    # 计算月供
    schedules = calc_amortization(
        loan_amount=loan_amount,
        annual_rate=Decimal(str(lp["interest_rate"])),
        term_months=lp["term_months"],
        start_date=date.today().replace(day=1),
    )
    monthly_payment = schedules[0]["total"]
    start_date = date.today()
    end_date = date(start_date.year + lp["term_months"] // 12,
                    start_date.month + lp["term_months"] % 12, 1)
    from dateutil.relativedelta import relativedelta
    end_date = start_date + relativedelta(months=lp["term_months"])

    cid = await add_contract(
        db, body.customer_id, body.product_id,
        down_payment, loan_amount, monthly_payment,
        start_date, end_date,
    )
    return await get_contract(db, cid)


@router.put("/contracts/{cid}/approve")
async def api_approve_contract(cid: str, request: Request,
                                db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    result = await approve_contract(db, cid)
    if not result:
        raise HTTPException(400, "审批失败（合同不存在或非 draft 状态）")
    return result


@router.put("/contracts/{cid}/status")
async def api_update_contract_status(cid: str, body: StatusUpdate,
                                      request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await update_contract_status(db, cid, body.status)
    if not ok:
        raise HTTPException(400, "状态变更失败")
    return await get_contract(db, cid)
```

- [ ] **Step 4: 在 main.py 注册 router**

```python
# app/main.py — 在现有 include_router 行后追加
from app.routers.contracts import router as contracts_router
app.include_router(contracts_router)
```

- [ ] **Step 5: 在 lifespan 中添加种子数据调用**

```python
# app/main.py — lifespan 函数中，seed_payment_rates 之后追加
async with AsyncSessionLocal() as db:
    await seed_loan_products(db)
```

同时在 import 区补充：
```python
from app.store import seed_payment_rates, seed_loan_products
```

- [ ] **Step 6: 运行 API 测试**

```bash
pytest tests/test_contracts_api.py -v
```
Expected: 6 passed

- [ ] **Step 7: 确保现有测试不受影响**

```bash
pytest tests/ -v
```
Expected: all existing tests pass (estimate: ~130 total)

- [ ] **Step 8: Commit**

```bash
git add app/routers/contracts.py app/main.py tests/test_contracts_api.py
git commit -m "feat: 合同 API — /api/loan-products + /api/contracts CRUD + 审批"
```

---

### Task 4: 前端 UI — tab + JS + CSS

**Files:**
- Modify: `templates/base.html` — nav-tabs 加「合同管理」
- Modify: `templates/dashboard.html` — switchTab('contracts') + 合同管理 JS
- Modify: `static/style.css` — 合同详情 + 还款计划表样式

- [ ] **Step 1: base.html 加 tab**

在 `templates/base.html` 的 `.nav-tabs` 中，「客户管理」之后追加：

```html
    <a class="nav-tab" data-tab="contracts" onclick="switchTab('contracts')">合同管理</a>
```

- [ ] **Step 2: dashboard.html — 在 switchTab() 中添加 contracts 分支**

在 `switchTab()` 函数中，`} else if (tab === 'customers') { ... }` 之后追加：

```javascript
  } else if (tab === 'contracts') {
    layout.classList.remove('sidebar-hidden');
    selectedCustomerId = null;
    loadContracts();
  }
```

- [ ] **Step 3: dashboard.html — 追加合同管理 JS 函数**

在 `</script>` 之前（或按功能分区插入），追加：

```javascript
// ---- 合同管理 ----
let selectedContractId = null;

async function loadContracts() {
  const resp = await fetch('/api/contracts');
  const contracts = await resp.json();
  const container = document.getElementById('customerItems');
  // 合同列表复用 customer-list 容器，但改标题
  document.querySelector('.sidebar-header h3').textContent = '合同列表';
  document.querySelector('.sidebar-header h3').onclick = null;
  document.getElementById('customerCount').textContent = contracts.length;

  const STATUS_DOT_C = { draft:'📝', approved:'🔵', active:'🟢', overdue:'🟡', closed:'✅', recovered:'🔴' };

  container.innerHTML = contracts.map(c => `
    <div class="customer-item ${c.id === selectedContractId ? 'active' : ''}"
         onclick="selectContract('${c.id}')">
      <div class="name">${STATUS_DOT_C[c.status] || '⚪'} ${c.contract_no}</div>
      <div class="meta">${c.customer_name || '—'} · ${c.status}</div>
    </div>
  `).join('');

  // 显示贷款产品配置入口
  const keygenSection = document.querySelector('.keygen-section');
  if (keygenSection) {
    keygenSection.innerHTML = `
      <div class="keygen-title">贷款产品</div>
      <button class="keygen-btn" onclick="showLoanProductModal()">⚙ 贷款产品配置</button>
      <button class="keygen-btn" style="margin-top:6px;" onclick="showNewContractModal()">+ 新合同</button>
    `;
  }

  if (!selectedContractId) {
    document.getElementById('detailPanel').innerHTML = `
      <div class="empty-state">
        <div class="icon">📋</div>
        <p>选择左侧合同查看详情</p>
      </div>
    `;
  }
}

async function selectContract(cid) {
  selectedContractId = cid;
  await loadContracts();
  const resp = await fetch(`/api/contracts/${cid}`);
  const c = await resp.json();

  const STATUS_LABEL = {
    draft: '草稿', approved: '已审批', active: '执行中',
    overdue: '逾期', closed: '已结清', recovered: '已回收',
  };

  document.getElementById('detailPanel').innerHTML = `
    <div class="detail-card">
      <div class="detail-header">
        <div class="detail-avatar">${c.contract_no[3] || 'C'}</div>
        <div>
          <h2>${c.contract_no}</h2>
          <span class="status-badge">${STATUS_LABEL[c.status] || c.status}</span>
        </div>
      </div>
      <div class="detail-body">
        <div class="detail-row"><span class="label">客户</span><span class="value">${escapeHtml(c.customer_name || '—')}</span></div>
        <div class="detail-row"><span class="label">贷款金额</span><span class="value">$${c.loan_amount.toFixed(2)}</span></div>
        <div class="detail-row"><span class="label">月供</span><span class="value">$${c.monthly_payment.toFixed(2)}</span></div>
        <div class="detail-row"><span class="label">首付</span><span class="value">$${c.down_payment.toFixed(2)}</span></div>
        <div class="detail-row"><span class="label">合同期限</span><span class="value">${c.start_date} ~ ${c.end_date}</span></div>
        <div class="detail-row"><span class="label">剩余天数</span><span class="value">${c.remaining_days} 天</span></div>
      </div>
      <div class="detail-section">
        <h4>操作</h4>
        <div class="btn-group">
          ${c.status === 'draft' ? `<button class="btn btn-primary btn-sm" onclick="approveContract('${c.id}')">审批通过</button>` : ''}
          ${c.status === 'active' ? `<button class="btn btn-warning btn-sm" onclick="markOverdue('${c.id}')">标记逾期</button>` : ''}
          ${c.status === 'overdue' ? `<button class="btn btn-primary btn-sm" onclick="markActive('${c.id}')">恢复活跃</button>` : ''}
          ${(c.status === 'active' || c.status === 'overdue') ? `<button class="btn btn-danger btn-sm" onclick="closeContract('${c.id}')">结清/回收</button>` : ''}
        </div>
      </div>
      ${c.schedules && c.schedules.length > 0 ? `
      <div class="detail-section">
        <h4>还款计划表</h4>
        <div style="overflow-x:auto;">
          <table class="tx-table">
            <thead><tr><th>期数</th><th>应还日</th><th>月供</th><th>本金</th><th>利息</th><th>剩余本金</th><th>状态</th></tr></thead>
            <tbody>
              ${c.schedules.map(s => `
                <tr>
                  <td>${s.period_no}</td>
                  <td>${s.due_date}</td>
                  <td>$${s.total.toFixed(2)}</td>
                  <td>$${s.principal.toFixed(2)}</td>
                  <td>$${s.interest.toFixed(2)}</td>
                  <td>$${s.balance.toFixed(2)}</td>
                  <td>${s.status === 'paid' ? '✅' : s.status === 'overdue' ? '🔴' : '⏳'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
      ` : ''}
    </div>
  `;
}

async function approveContract(cid) {
  await fetch(`/api/contracts/${cid}/approve`, { method: 'PUT' });
  selectContract(cid);
  showToast('合同已审批通过，还款计划已生成');
}

async function markOverdue(cid) {
  await fetch(`/api/contracts/${cid}/status`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({status: 'overdue'})
  });
  selectContract(cid);
  showToast('合同已标记为逾期');
}

async function markActive(cid) {
  await fetch(`/api/contracts/${cid}/status`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({status: 'active'})
  });
  selectContract(cid);
}

async function closeContract(cid) {
  const status = confirm('选「确定」结清合同，选「取消」标记为设备回收') ? 'closed' : 'recovered';
  await fetch(`/api/contracts/${cid}/status`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({status})
  });
  selectContract(cid);
  showToast(status === 'closed' ? '合同已结清' : '合同已标记为设备回收');
}

async function showNewContractModal() {
  // 获取客户列表 + 贷款产品列表
  const [customersResp, productsResp] = await Promise.all([
    fetch('/api/customers'), fetch('/api/loan-products')
  ]);
  const customers = await customersResp.json();
  const products = await productsResp.json();
  const activeProducts = products.filter(p => p.status === 'active');

  const customerOpts = customers.map(c => `<option value="${c.id}">${c.name} (${c.device_id})</option>`).join('');
  const productOpts = activeProducts.map(p => `<option value="${p.id}">${p.name} — $${p.total_amount.toFixed(0)} ${p.term_months}月 ${p.interest_rate}%</option>`).join('');

  document.getElementById('detailPanel').innerHTML = `
    <div class="detail-card" style="max-width:500px;">
      <h3 style="padding:20px 24px 0;">新合同</h3>
      <div class="detail-body">
        <div class="form-group">
          <label>客户</label>
          <select id="newContractCustomer" style="width:100%;height:38px;border:1px solid var(--border);border-radius:6px;padding:0 12px;font-family:inherit;">${customerOpts}</select>
        </div>
        <div class="form-group">
          <label>贷款产品</label>
          <select id="newContractProduct" style="width:100%;height:38px;border:1px solid var(--border);border-radius:6px;padding:0 12px;font-family:inherit;">${productOpts}</select>
        </div>
        <div class="modal-actions">
          <button class="btn btn-outline" onclick="selectContract(null);loadContracts();">取消</button>
          <button class="btn btn-primary" onclick="createContract()">确认创建</button>
        </div>
      </div>
    </div>
  `;
}

async function createContract() {
  const customer_id = document.getElementById('newContractCustomer').value;
  const product_id = document.getElementById('newContractProduct').value;
  const resp = await fetch('/api/contracts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({customer_id, product_id})
  });
  if (!resp.ok) { const err = await resp.json(); alert('创建失败: ' + (err.detail || '')); return; }
  const c = await resp.json();
  showToast('合同 ' + c.contract_no + ' 已创建');
  selectContract(c.id);
}

// ---- 贷款产品配置弹窗 ----
async function showLoanProductModal() {
  const resp = await fetch('/api/loan-products');
  const products = await resp.json();

  document.getElementById('detailPanel').innerHTML = `
    <div class="detail-card" style="max-width:700px;">
      <h3 style="padding:20px 24px 0;">贷款产品配置</h3>
      <div class="detail-body">
        <table class="tx-table">
          <thead><tr><th>名称</th><th>kW</th><th>月数</th><th>利率</th><th>首付%</th><th>总价</th><th>状态</th></tr></thead>
          <tbody>
            ${products.map(p => `
              <tr>
                <td>${p.name}</td><td>${p.capacity_kw}</td><td>${p.term_months}</td>
                <td>${p.interest_rate}%</td><td>${p.down_payment_pct}%</td>
                <td>$${p.total_amount.toFixed(0)}</td>
                <td>${p.status === 'active' ? '🟢' : '⚫'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}
```

- [ ] **Step 4: 修复客户管理 tab 还原侧边栏**

确保从「合同管理」切换回「客户管理」时，侧边栏按钮恢复正常。在 `switchTab('customers')` 分支中追加侧边栏还原逻辑：

```javascript
  } else if (tab === 'customers') {
    layout.classList.remove('sidebar-hidden');
    selectedCustomerId = null;
    // 还原侧边栏为客户列表模式
    document.querySelector('.sidebar-header h3').textContent = '客户列表';
    document.querySelector('.sidebar-header h3').onclick = function() { showDashboard(); };
    const keygenSection = document.querySelector('.keygen-section');
    if (keygenSection) {
      keygenSection.innerHTML = `
        <div class="keygen-title">密钥生成器</div>
        <button class="keygen-btn" onclick="generateKeys()">生成 5 个设备密钥</button>
        <div class="keygen-list" id="keygenList"></div>
      `;
    }
    loadCustomers();
    document.getElementById('detailPanel').innerHTML = `
      <div class="empty-state">
        <div class="icon">☀</div>
        <p>选择左侧客户查看详情</p>
      </div>
    `;
  }
```

- [ ] **Step 5: 追加 CSS 样式**

在 `static/style.css` 末尾追加：

```css
/* ── 合同管理 ── */
.contract-status-draft { color: #64748b; }
.contract-status-active { color: #059669; }
.contract-status-overdue { color: #d97706; }
.contract-status-closed { color: #16a34a; }
.contract-status-recovered { color: #dc2626; }

.schedule-paid { color: #059669; }
.schedule-overdue { color: #dc2626; font-weight: 600; }
.schedule-pending { color: #94a3b8; }
```

- [ ] **Step 6: Commit**

```bash
git add templates/base.html templates/dashboard.html static/style.css
git commit -m "feat: 合同管理 UI — tab + 合同列表/详情 + 还款计划表 + 贷款产品配置"
```

---

### Task 5: 验证 — 全量测试 + Playwright

- [ ] **Step 1: 运行全部测试**

```bash
pytest tests/ -v
```
Expected: all tests pass (estimate: ~135+ passed)

- [ ] **Step 2: 确认服务正常**

```bash
curl -s http://localhost:8000/api/loan-products -b cookies.txt | python3 -m json.tool | head -10
```
Expected: 返回贷款产品列表 JSON

- [ ] **Step 3: Playwright 验证**

导航到 `http://localhost:8000/dashboard`，验证：
- 「合同管理」tab 可见
- 点击切换侧边栏显示合同列表
- 「贷款产品配置」查看 5 档产品
- 「新合同」创建合同（选客户+选产品）
- 「审批通过」生成还款计划表
- 还款计划表格正确（24行等额本息）

- [ ] **Step 4: Commit（如有修改）**

```bash
git add -A && git commit -m "chore: M7 合同管理验证通过"
```
