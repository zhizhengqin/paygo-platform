"""ORM 模型单元测试 — 验证表结构、关系、约束。"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models import Base, Customer, Token, SmsRecord, PaymentRate, DeviceState
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


class TestCustomerModel:
    async def test_create_customer(self, session):
        c = Customer(
            id="C0001",
            name="Sok Heng",
            phone="0888888001",
            device_id="Solar-001",
            secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        )
        session.add(c)
        await session.commit()

        result = await session.get(Customer, "C0001")
        assert result.name == "Sok Heng"
        assert result.status == "locked"
        assert result.count == 0
        assert result.locked_at is None

    async def test_customer_unique_id(self, session):
        c1 = Customer(id="C0001", name="A", phone="1", device_id="D1", secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
        c2 = Customer(id="C0001", name="B", phone="2", device_id="D2", secret_key="b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7")
        session.add(c1)
        await session.commit()
        session.add(c2)
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()


class TestTokenModel:
    async def test_create_token(self, session):
        c = Customer(id="C0001", name="A", phone="1", device_id="D1", secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
        session.add(c)
        await session.commit()

        t = Token(
            id="T0001",
            customer_id="C0001",
            token="123456789",
            days=30,
            count=2,
        )
        session.add(t)
        await session.commit()

        result = await session.get(Token, "T0001")
        assert result.token == "123456789"
        assert result.customer_id == "C0001"
        assert result.days == 30

    async def test_token_customer_relationship(self, session):
        c = Customer(id="C0001", name="A", phone="1", device_id="D1", secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
        session.add(c)
        t1 = Token(id="T0001", customer_id="C0001", token="111111111", days=30, count=1)
        t2 = Token(id="T0002", customer_id="C0001", token="222222222", days=60, count=2)
        session.add_all([t1, t2])
        await session.commit()

        from sqlalchemy import select as sa_select
        from sqlalchemy.orm import selectinload
        result = (await session.execute(
            sa_select(Customer).where(Customer.id == "C0001").options(selectinload(Customer.tokens))
        )).scalar_one()
        assert len(result.tokens) == 2


class TestPaymentRateModel:
    async def test_create_rate(self, session):
        r = PaymentRate(amount=5, days=30)
        session.add(r)
        await session.commit()

        from sqlalchemy import select as sa_select
        result = (await session.execute(
            sa_select(PaymentRate).where(PaymentRate.amount == 5)
        )).scalar_one()
        assert result.days == 30

    async def test_rate_unique_amount(self, session):
        session.add(PaymentRate(amount=5, days=30))
        await session.commit()
        session.add(PaymentRate(amount=5, days=60))
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()


class TestDeviceStateModel:
    async def test_create_device_state(self, session):
        ds = DeviceState(
            device_id="Solar-001",
            secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            count=0,
            status="unbound",
        )
        session.add(ds)
        await session.commit()

        from sqlalchemy import select as sa_select
        result = (await session.execute(
            sa_select(DeviceState).where(DeviceState.device_id == "Solar-001")
        )).scalar_one()
        assert result.status == "unbound"
        assert result.used_counts == []

    async def test_device_state_used_counts_jsonb(self, session):
        ds = DeviceState(
            device_id="Solar-002",
            status="active",
            used_counts=[1, 2, 3],
        )
        session.add(ds)
        await session.commit()

        from sqlalchemy import select as sa_select
        result = (await session.execute(
            sa_select(DeviceState).where(DeviceState.device_id == "Solar-002")
        )).scalar_one()
        assert result.used_counts == [1, 2, 3]
