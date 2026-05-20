"""store.py 测试 — 所有 async 数据访问函数，操作测试数据库。"""
import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.models import Base, Customer, Token, PaymentRate, SmsRecord
from app.settings import TEST_DATABASE_URL
from app.store import (
    get_customers, get_customer, add_customer, delete_customer,
    update_customer_status, set_customer_count,
    get_tokens, add_token,
    get_payment_rates, get_days_for_amount,
    add_sms_record, get_sms_records,
    seed_payment_rates,
)


def _key() -> str:
    """生成唯一密钥，避免测试间冲突。"""
    return secrets.token_hex(16)


TEST_KEY = _key()  # 向后兼容


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


class TestCustomers:
    async def test_get_customers_empty(self, session):
        result = await get_customers(session)
        assert result == []

    async def test_add_and_get_customer(self, session):
        cid = await add_customer(session, "Sok Heng", "0888888001", "Solar-001", TEST_KEY)
        assert cid.startswith("C")
        customer = await get_customer(session, cid)
        assert customer["name"] == "Sok Heng"
        assert customer["phone"] == "0888888001"
        assert customer["device_id"] == "Solar-001"
        assert customer["secret_key"] == TEST_KEY
        assert customer["count"] == 0
        assert customer["status"] == "locked"

    async def test_get_customer_not_found(self, session):
        result = await get_customer(session, "C9999999")
        assert result is None

    async def test_get_customers_list(self, session):
        await add_customer(session, "A", "1", "D1", _key())
        await add_customer(session, "B", "2", "D2", _key())
        result = await get_customers(session)
        assert len(result) == 2

    async def test_delete_customer(self, session):
        cid = await add_customer(session, "Test", "000", "D000", TEST_KEY)
        ok = await delete_customer(session, cid)
        assert ok is True
        assert await get_customer(session, cid) is None

    async def test_delete_customer_not_found(self, session):
        assert await delete_customer(session, "C9999999") is False

    async def test_update_customer_status(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        ok = await update_customer_status(session, cid, "active")
        assert ok is True
        c = await get_customer(session, cid)
        assert c["status"] == "active"

    async def test_update_status_nonexistent(self, session):
        assert await update_customer_status(session, "NOEXIST", "active") is False

    async def test_lock_sets_locked_at(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        await update_customer_status(session, cid, "active")
        await update_customer_status(session, cid, "locked")
        c = await get_customer(session, cid)
        assert c["locked_at"] is not None

    async def test_set_customer_count(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        await set_customer_count(session, cid, 5)
        c = await get_customer(session, cid)
        assert c["count"] == 5

    async def test_duplicate_device_id_rejected(self, session):
        await add_customer(session, "A", "1", "D1", TEST_KEY)
        from app.store import DuplicateDeviceError
        with pytest.raises(DuplicateDeviceError) as exc:
            await add_customer(session, "B", "2", "D1",
                               "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7")
        assert "D1" in str(exc.value)

    async def test_duplicate_secret_key_rejected(self, session):
        await add_customer(session, "A", "1", "D1", TEST_KEY)
        from app.store import DuplicateSecretKeyError
        with pytest.raises(DuplicateSecretKeyError):
            await add_customer(session, "B", "2", "D2", TEST_KEY)


class TestTokens:
    async def test_get_tokens_empty(self, session):
        result = await get_tokens(session)
        assert result == []

    async def test_add_and_get_token(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        tid = await add_token(session, cid, "123456789", 30, 2)
        assert tid.startswith("T")
        tokens = await get_tokens(session)
        assert len(tokens) == 1
        assert tokens[0]["customer_id"] == cid
        assert tokens[0]["days"] == 30
        assert tokens[0]["count"] == 2

    async def test_get_tokens_returns_list_of_dicts(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        await add_token(session, cid, "111111111", 30, 1)
        await add_token(session, cid, "222222222", 60, 2)
        tokens = await get_tokens(session)
        assert len(tokens) == 2
        assert isinstance(tokens[0], dict)
        assert "id" in tokens[0]
        assert "customer_id" in tokens[0]


class TestPaymentRates:
    async def test_seed_payment_rates(self, session):
        await seed_payment_rates(session)
        rates = await get_payment_rates(session)
        assert len(rates) == 2
        assert {"amount": 5.0, "days": 30} in rates
        assert {"amount": 10.0, "days": 60} in rates

    async def test_get_days_for_amount(self, session):
        await seed_payment_rates(session)
        assert await get_days_for_amount(session, 5) == 30
        assert await get_days_for_amount(session, 10) == 60
        assert await get_days_for_amount(session, 999) == 0

    async def test_seed_idempotent(self, session):
        await seed_payment_rates(session)
        await seed_payment_rates(session)
        rates = await get_payment_rates(session)
        assert len(rates) == 2


class TestSmsRecords:
    async def test_add_and_get_sms(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        sid = await add_sms_record(session, cid, "0888888001", "Test message")
        assert sid.startswith("S")
        records = await get_sms_records(session, cid)
        assert len(records) == 1
        assert records[0]["to_phone"] == "0888888001"
        assert records[0]["message"] == "Test message"

    async def test_get_all_sms(self, session):
        cid1 = await add_customer(session, "A", "1", "D1", _key())
        cid2 = await add_customer(session, "B", "2", "D2", _key())
        await add_sms_record(session, cid1, "0888888001", "msg1")
        await add_sms_record(session, cid2, "0888888002", "msg2")
        records = await get_sms_records(session)
        assert len(records) == 2


class TestSecretKeyEncryption:
    async def test_add_customer_encrypts_secret_key(self, session):
        """新增客户时 secret_key_encrypted 不为空，且不同于原始值。"""
        from app.store import add_customer
        from app.models import Customer
        from sqlalchemy import select
        from app.security import init_fernet
        init_fernet()

        cid = await add_customer(session, "Test", "+855123", "DEV-ENC01", "a" * 32)
        result = await session.execute(select(Customer).where(Customer.id == cid))
        c = result.scalar()
        assert c.secret_key_encrypted is not None
        assert c.secret_key_encrypted != "a" * 32
        assert c.secret_key is None

    async def test_get_customer_returns_decrypted_key(self, session):
        """获取客户时 secret_key 被正确解密返回。"""
        from app.store import add_customer, get_customer
        from app.security import init_fernet
        init_fernet()

        cid = await add_customer(session, "Test2", "+855456", "DEV-ENC02", "b" * 32)
        c = await get_customer(session, cid)
        assert c["secret_key"] == "b" * 32

    async def test_migrate_secret_keys(self, session):
        """迁移函数将明文列加密后置空。"""
        from app.store import migrate_secret_keys_to_encrypted
        from app.models import Customer, _new_id
        from sqlalchemy import select
        from app.security import init_fernet
        init_fernet()

        c = Customer(
            id=_new_id("C"), name="Legacy", phone="+855789",
            device_id="DEV-LEGACY01", secret_key="c" * 32,
        )
        session.add(c)
        await session.commit()

        count = await migrate_secret_keys_to_encrypted(session)
        assert count == 1

        result = await session.execute(
            select(Customer).where(Customer.device_id == "DEV-LEGACY01")
        )
        c2 = result.scalar()
        assert c2.secret_key_encrypted is not None
        assert c2.secret_key is None
