"""store.py 合同/贷款产品测试 — 等额本息计算 + LoanProduct CRUD + Contract CRUD + 种子数据。"""
import secrets
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Base, Customer, LoanProduct, _new_id
from app.settings import TEST_DATABASE_URL
from app.store import (
    calc_amortization,
    generate_contract_no,
    add_loan_product, get_loan_products, get_loan_product,
    update_loan_product, disable_loan_product,
    add_contract, get_contracts, get_contract,
    get_contract_with_schedules, approve_contract,
    update_contract_status,
    seed_loan_products,
    add_customer,
)


def _key() -> str:
    return secrets.token_hex(16)


@pytest.fixture(scope="function")
def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    return eng


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine, create_tables):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


class TestCalcAmortization:
    """等额本息计算单元测试"""

    def test_24month_920_at_12pct(self):
        """24月 $920 @ 12% 年利率：24 期，首期月供 ~$43.31，末期余额 ≈ 0"""
        schedules = calc_amortization(
            loan_amount=Decimal("920.00"),
            annual_rate=Decimal("12.00"),
            term_months=24,
            start_date=date(2026, 1, 15),
        )
        assert len(schedules) == 24

        # 月供公式：P=920, r=0.12/12=0.01, n=24
        # monthly = 920 * 0.01 * 1.01^24 / (1.01^24 - 1)
        # 1.01^24 ≈ 1.26973465
        # = 920 * 0.01 * 1.26973465 / (1.26973465 - 1)
        # = 9.2 * 1.26973465 / 0.26973465
        # ≈ 43.31
        first = schedules[0]
        assert first["period_no"] == 1
        assert first["total"] == Decimal("43.31")
        assert first["interest"] == Decimal("9.20")  # 920 * 0.01 = 9.20
        assert first["principal"] == Decimal("34.11")  # 43.31 - 9.20 = 34.11
        assert first["balance"] == Decimal("885.89")  # 920 - 34.11
        assert first["status"] == "pending"

        last = schedules[-1]
        assert last["period_no"] == 24
        assert last["balance"] == Decimal("0.00")

    def test_12month_600_at_10pct(self):
        """12月 $600 @ 10% 年利率：12 期，月供 ~$52.75"""
        schedules = calc_amortization(
            loan_amount=Decimal("600.00"),
            annual_rate=Decimal("10.00"),
            term_months=12,
            start_date=date(2026, 2, 1),
        )
        assert len(schedules) == 12

        # 月供公式：P=600, r=0.10/12≈0.0083333, n=12
        # monthly ≈ 52.75
        first = schedules[0]
        assert first["period_no"] == 1
        assert first["total"] == Decimal("52.75")
        assert first["interest"] == Decimal("5.00")  # 600 * 0.10/12 = 5.00
        assert first["principal"] == Decimal("47.75")

        last = schedules[-1]
        assert last["period_no"] == 12
        assert last["balance"] == Decimal("0.00")

    def test_dates_increment_by_month(self):
        """验证每期日期递推正确"""
        schedules = calc_amortization(
            loan_amount=Decimal("300.00"),
            annual_rate=Decimal("12.00"),
            term_months=3,
            start_date=date(2026, 1, 31),
        )
        assert schedules[0]["due_date"] == date(2026, 2, 28)
        assert schedules[1]["due_date"] == date(2026, 3, 31)
        assert schedules[2]["due_date"] == date(2026, 4, 30)


class TestLoanProductCRUD:
    """贷款产品 CRUD"""

    async def test_add_and_list(self, session):
        pid = await add_loan_product(
            session,
            name="6kW-12月基础",
            capacity_kw=Decimal("6.00"),
            term_months=12,
            interest_rate=Decimal("10.00"),
            down_payment_pct=Decimal("20.00"),
            total_amount=Decimal("690.00"),
        )
        assert pid.startswith("LP")

        products = await get_loan_products(session)
        assert len(products) == 1
        assert products[0]["name"] == "6kW-12月基础"
        assert products[0]["capacity_kw"] == 6.0
        assert products[0]["status"] == "active"

    async def test_get_single(self, session):
        pid = await add_loan_product(
            session, "10kW-24月标准", Decimal("10.00"), 24,
            Decimal("12.00"), Decimal("20.00"), Decimal("1150.00"),
        )
        lp = await get_loan_product(session, pid)
        assert lp is not None
        assert lp["name"] == "10kW-24月标准"
        assert lp["term_months"] == 24

        lp = await get_loan_product(session, "NONEXIST")
        assert lp is None

    async def test_filter_by_status(self, session):
        pid1 = await add_loan_product(
            session, "A", Decimal("5.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("500.00"),
        )
        pid2 = await add_loan_product(
            session, "B", Decimal("8.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("800.00"),
        )
        await disable_loan_product(session, pid2)

        active = await get_loan_products(session, status="active")
        assert len(active) == 1
        assert active[0]["id"] == pid1

        disabled = await get_loan_products(session, status="disabled")
        assert len(disabled) == 1
        assert disabled[0]["id"] == pid2

    async def test_disable(self, session):
        pid = await add_loan_product(
            session, "test", Decimal("5.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("500.00"),
        )
        assert await disable_loan_product(session, pid)
        lp = await get_loan_product(session, pid)
        assert lp["status"] == "disabled"

        # disable non-existent
        assert await disable_loan_product(session, "NONEXIST") is False

    async def test_update(self, session):
        pid = await add_loan_product(
            session, "original", Decimal("5.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("500.00"),
        )
        assert await update_loan_product(session, pid, name="updated")
        lp = await get_loan_product(session, pid)
        assert lp["name"] == "updated"

        # update non-existent
        assert await update_loan_product(session, "NONEXIST", name="x") is False


class TestContractCRUD:
    """合同 CRUD"""

    async def _setup_product_and_customer(self, session):
        """辅助：创建贷款产品和客户，返回 (product_id, customer_id)"""
        pid = await add_loan_product(
            session, "6kW-12月基础", Decimal("6.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("690.00"),
        )
        cid = await add_customer(session, "Sok Heng", "0888888001", "Solar-001", _key())
        return pid, cid

    async def test_add_and_get_contract(self, session):
        pid, cid = await self._setup_product_and_customer(session)

        ct_id = await add_contract(
            session,
            customer_id=cid,
            product_id=pid,
            down_payment=Decimal("138.00"),
            loan_amount=Decimal("552.00"),
            monthly_payment=Decimal("46.00"),
            start_date=date(2026, 1, 15),
            end_date=date(2027, 1, 15),
        )
        assert ct_id.startswith("CT")

        c = await get_contract(session, ct_id)
        assert c is not None
        assert c["contract_no"].startswith("KH-")
        assert c["status"] == "draft"
        assert c["loan_amount"] == 552.0
        assert c["customer_name"] == "Sok Heng"

        c_none = await get_contract(session, "NONEXIST")
        assert c_none is None

    async def test_list_contracts(self, session):
        pid, cid = await self._setup_product_and_customer(session)

        await add_contract(
            session, cid, pid,
            Decimal("138.00"), Decimal("552.00"), Decimal("46.00"),
            date(2026, 1, 15), date(2027, 1, 15),
        )

        contracts = await get_contracts(session)
        assert len(contracts) == 1

        # filter by status
        draft = await get_contracts(session, status="draft")
        assert len(draft) == 1
        active = await get_contracts(session, status="active")
        assert len(active) == 0

        # filter by customer
        by_customer = await get_contracts(session, customer_id=cid)
        assert len(by_customer) == 1
        other = await get_contracts(session, customer_id="NONEXIST")
        assert len(other) == 0

    async def test_approve_generates_schedule(self, session):
        pid, cid = await self._setup_product_and_customer(session)

        ct_id = await add_contract(
            session, cid, pid,
            Decimal("138.00"), Decimal("552.00"), Decimal("46.00"),
            date(2026, 1, 15), date(2027, 1, 15),
        )

        result = await approve_contract(session, ct_id)
        assert result is not None
        assert result["status"] == "active"
        assert result["approved_at"] is not None
        assert result["remaining_days"] == 360  # 12 months * 30
        assert len(result["schedules"]) == 12
        assert result["schedules"][0]["period_no"] == 1
        assert result["schedules"][-1]["period_no"] == 12

        # re-approve returns None (not draft)
        result2 = await approve_contract(session, ct_id)
        assert result2 is None

    async def test_approve_nonexistent(self, session):
        result = await approve_contract(session, "NONEXIST")
        assert result is None

    async def test_update_contract_status(self, session):
        pid, cid = await self._setup_product_and_customer(session)

        ct_id = await add_contract(
            session, cid, pid,
            Decimal("138.00"), Decimal("552.00"), Decimal("46.00"),
            date(2026, 1, 15), date(2027, 1, 15),
        )

        # valid transition
        assert await update_contract_status(session, ct_id, "overdue")
        c = await get_contract(session, ct_id)
        assert c["status"] == "overdue"

        # invalid status
        assert await update_contract_status(session, ct_id, "invalid_status") is False

        # non-existent contract
        assert await update_contract_status(session, "NONEXIST", "active") is False

    async def test_get_contract_with_schedules_empty(self, session):
        pid, cid = await self._setup_product_and_customer(session)

        ct_id = await add_contract(
            session, cid, pid,
            Decimal("138.00"), Decimal("552.00"), Decimal("46.00"),
            date(2026, 1, 15), date(2027, 1, 15),
        )

        c = await get_contract_with_schedules(session, ct_id)
        assert c is not None
        assert c["schedules"] == []

        c_none = await get_contract_with_schedules(session, "NONEXIST")
        assert c_none is None


class TestSeedLoanProducts:
    """种子数据"""

    async def test_seed_creates_5_products(self, session):
        await seed_loan_products(session)
        products = await get_loan_products(session)
        assert len(products) == 5
        capacities = [p["capacity_kw"] for p in products]
        assert capacities == [6.0, 10.0, 15.0, 20.0, 30.0]

    async def test_seed_is_idempotent(self, session):
        await seed_loan_products(session)
        await seed_loan_products(session)
        products = await get_loan_products(session)
        assert len(products) == 5


class TestGenerateContractNo:
    """合同编号生成"""

    async def test_format(self, session):
        no = await generate_contract_no(session)
        assert no.startswith("KH-")
        parts = no.split("-")
        assert len(parts) == 3
        assert len(parts[2]) == 5
        assert int(parts[1]) == 2026
