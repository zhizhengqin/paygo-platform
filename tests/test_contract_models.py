"""贷款合同 ORM 模型单元测试 — 验证 LoanProduct / Contract / RepaymentSchedule 表结构。"""
import pytest
from decimal import Decimal
from datetime import date

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select as sa_select

from app.models import Base, Customer, LoanProduct, Contract, RepaymentSchedule
from app.settings import TEST_DATABASE_URL


@pytest.fixture(scope="function")
def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    return eng


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine, create_tables):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


class TestLoanProductModel:
    async def test_create_loan_product(self, session):
        lp = LoanProduct(
            id="LP0001",
            name="10kW-24月标准",
            capacity_kw=Decimal("10.00"),
            term_months=24,
            interest_rate=Decimal("12.00"),
            down_payment_pct=Decimal("20.00"),
            total_amount=Decimal("1150.00"),
        )
        session.add(lp)
        await session.commit()

        result = await session.get(LoanProduct, "LP0001")
        assert result.name == "10kW-24月标准"
        assert result.capacity_kw == Decimal("10.00")
        assert result.term_months == 24
        assert result.status == "active"

    async def test_loan_product_default_status(self, session):
        lp = LoanProduct(
            id="LP0002",
            name="Test Default",
            capacity_kw=Decimal("5.00"),
            term_months=12,
            interest_rate=Decimal("10.00"),
            down_payment_pct=Decimal("15.00"),
            total_amount=Decimal("500.00"),
        )
        session.add(lp)
        await session.commit()

        result = await session.get(LoanProduct, "LP0002")
        assert result.status == "active"


class TestContractModel:
    async def test_create_contract(self, session):
        # 先创建关联的客户和产品
        c = Customer(
            id="C0001",
            name="Sok Heng",
            phone="0888888001",
            device_id="Solar-CT-001",
            secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        )
        lp = LoanProduct(
            id="LP0001",
            name="10kW-24月标准",
            capacity_kw=Decimal("10.00"),
            term_months=24,
            interest_rate=Decimal("12.00"),
            down_payment_pct=Decimal("20.00"),
            total_amount=Decimal("1150.00"),
        )
        session.add_all([c, lp])
        await session.commit()

        contract = Contract(
            id="CT0001",
            contract_no="KH-2026-00001",
            customer_id="C0001",
            product_id="LP0001",
            down_payment=Decimal("230.00"),
            loan_amount=Decimal("920.00"),
            monthly_payment=Decimal("47.33"),
            start_date=date(2026, 6, 1),
            end_date=date(2028, 6, 1),
        )
        session.add(contract)
        await session.commit()

        result = await session.get(Contract, "CT0001")
        assert result.contract_no == "KH-2026-00001"
        assert result.status == "draft"
        assert result.remaining_days == 0
        assert result.down_payment == Decimal("230.00")

    async def test_contract_default_status_draft(self, session):
        c = Customer(
            id="C0002",
            name="Test",
            phone="0888888002",
            device_id="Solar-CT-002",
            secret_key="b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7",
        )
        lp = LoanProduct(
            id="LP0002",
            name="5kW-12月标准",
            capacity_kw=Decimal("5.00"),
            term_months=12,
            interest_rate=Decimal("10.00"),
            down_payment_pct=Decimal("15.00"),
            total_amount=Decimal("500.00"),
        )
        session.add_all([c, lp])
        await session.commit()

        contract = Contract(
            id="CT0002",
            contract_no="KH-2026-00002",
            customer_id="C0002",
            product_id="LP0002",
            down_payment=Decimal("75.00"),
            loan_amount=Decimal("425.00"),
            monthly_payment=Decimal("40.50"),
        )
        session.add(contract)
        await session.commit()

        result = await session.get(Contract, "CT0002")
        assert result.status == "draft"


class TestRepaymentScheduleModel:
    async def test_create_schedule_item(self, session):
        # 先创建关联的合同链：Customer -> LoanProduct -> Contract
        c = Customer(
            id="C0001",
            name="Test",
            phone="0888888003",
            device_id="Solar-RS-001",
            secret_key="c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8",
        )
        lp = LoanProduct(
            id="LP0001",
            name="10kW-24月标准",
            capacity_kw=Decimal("10.00"),
            term_months=24,
            interest_rate=Decimal("12.00"),
            down_payment_pct=Decimal("20.00"),
            total_amount=Decimal("1150.00"),
        )
        contract = Contract(
            id="CT0001",
            contract_no="KH-2026-RS01",
            customer_id="C0001",
            product_id="LP0001",
            down_payment=Decimal("230.00"),
            loan_amount=Decimal("920.00"),
            monthly_payment=Decimal("47.33"),
        )
        session.add_all([c, lp, contract])
        await session.commit()

        rs = RepaymentSchedule(
            id="RS0001",
            contract_id="CT0001",
            period_no=1,
            due_date=date(2026, 7, 1),
            principal=Decimal("35.83"),
            interest=Decimal("11.50"),
            total=Decimal("47.33"),
            balance=Decimal("884.17"),
        )
        session.add(rs)
        await session.commit()

        result = await session.get(RepaymentSchedule, "RS0001")
        assert result.period_no == 1
        assert result.status == "pending"
        assert result.total == Decimal("47.33")

    async def test_schedule_default_status_pending(self, session):
        c = Customer(
            id="C0002",
            name="Test2",
            phone="0888888004",
            device_id="Solar-RS-002",
            secret_key="d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9",
        )
        lp = LoanProduct(
            id="LP0002",
            name="5kW-12月标准",
            capacity_kw=Decimal("5.00"),
            term_months=12,
            interest_rate=Decimal("10.00"),
            down_payment_pct=Decimal("15.00"),
            total_amount=Decimal("500.00"),
        )
        contract = Contract(
            id="CT0002",
            contract_no="KH-2026-RS02",
            customer_id="C0002",
            product_id="LP0002",
            down_payment=Decimal("75.00"),
            loan_amount=Decimal("425.00"),
            monthly_payment=Decimal("40.50"),
        )
        session.add_all([c, lp, contract])
        await session.commit()

        rs = RepaymentSchedule(
            id="RS0002",
            contract_id="CT0002",
            period_no=5,
            due_date=date(2026, 11, 1),
            principal=Decimal("0"),
            interest=Decimal("0"),
            total=Decimal("0"),
            balance=Decimal("0"),
        )
        session.add(rs)
        await session.commit()

        result = await session.get(RepaymentSchedule, "RS0002")
        assert result.status == "pending"
