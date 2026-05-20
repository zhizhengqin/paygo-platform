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


from app.store import (
    get_tokens_filtered, get_token_stats, get_token_detail,
    reissue_token, void_token,
)


class TestTokenManagement:
    async def _setup_tokens(self, session):
        """创建测试客户 + 3 个 Token"""
        from app.security import init_fernet
        init_fernet()
        cid = await add_customer(session, "TokTest", "+8551", "DEV-T1", "a" * 32)
        for i in range(3):
            await add_token(session, cid, f"12345678{i}", 30, i + 1, amount=5.0)
        return cid

    async def test_get_tokens_filtered_all(self, session):
        """筛选：全部 Token"""
        await self._setup_tokens(session)
        all_tokens = await get_tokens_filtered(session)
        assert len(all_tokens) == 3

    async def test_get_tokens_filtered_by_customer(self, session):
        """筛选：按客户"""
        cid = await self._setup_tokens(session)
        by_customer = await get_tokens_filtered(session, customer_id=cid)
        assert len(by_customer) == 3
        empty = await get_tokens_filtered(session, customer_id="NONEXIST")
        assert len(empty) == 0

    async def test_get_token_stats(self, session):
        """Token 统计"""
        from app.security import init_fernet
        init_fernet()
        await self._setup_tokens(session)
        stats = await get_token_stats(session)
        assert stats["total"] == 3
        assert stats["today"] >= 0
        assert stats["this_month"] >= 0

    async def test_get_token_detail(self, session):
        """Token 详情含客户名"""
        from app.security import init_fernet
        init_fernet()
        await self._setup_tokens(session)
        all_tokens = await get_tokens_filtered(session)
        tid = all_tokens[0]["id"]
        detail = await get_token_detail(session, tid)
        assert detail is not None
        assert detail["customer_name"] == "TokTest"
        assert detail["status"] == "UNUSED"

    async def test_reissue_token_success(self, session):
        """补发 Token：生成新 Token + 标记原 Token"""
        from app.security import init_fernet
        init_fernet()
        await self._setup_tokens(session)
        all_tokens = await get_tokens_filtered(session)
        original = all_tokens[0]

        result = await reissue_token(session, original["id"], reason="SMS 未送达")
        assert result is not None
        assert result["token"] != original["token"]
        assert result["superseded_id"] == original["id"]

        # 原 Token 状态变 SUPERSEDED
        orig_detail = await get_token_detail(session, original["id"])
        assert orig_detail["status"] == "SUPERSEDED"

    async def test_void_token_success(self, session):
        """作废 Token"""
        from app.security import init_fernet
        init_fernet()
        await self._setup_tokens(session)
        all_tokens = await get_tokens_filtered(session)
        tid = all_tokens[0]["id"]

        ok = await void_token(session, tid, "admin", "安全原因")
        assert ok is True

        detail = await get_token_detail(session, tid)
        assert detail["status"] == "SUPERSEDED"
        assert detail["voided_by"] == "admin"

    async def test_reissue_already_superseded_fails(self, session):
        """已作废 Token 不可补发"""
        from app.security import init_fernet
        init_fernet()
        await self._setup_tokens(session)
        all_tokens = await get_tokens_filtered(session)
        tid = all_tokens[0]["id"]
        await void_token(session, tid, "admin", "test")
        result = await reissue_token(session, tid, reason="test")
        assert result is None


from app.store import (
    get_customers_filtered, get_customer_360, add_mfi, get_mfis,
    update_customer_tags,
)


class TestCustomer360:
    async def _setup_360(self, session):
        from app.security import init_fernet
        init_fernet()
        mfi_id = await add_mfi(session, "LOLC Cambodia", "Phnom Penh")
        from app.store import add_customer
        cid = await add_customer(session, "Test360", "+855555", "DEV-360", "a"*32)
        from app.models import Customer
        c = await session.get(Customer, cid)
        c.address = "123 Street"
        c.id_number = "ID001"
        c.mfi_id = mfi_id
        await session.commit()
        return cid

    async def test_get_customers_filtered_by_name(self, session):
        cid = await self._setup_360(session)
        result = await get_customers_filtered(session, search="Test360")
        assert len(result) == 1
        empty = await get_customers_filtered(session, search="NoSuchName")
        assert len(empty) == 0

    async def test_get_customer_360(self, session):
        cid = await self._setup_360(session)
        view = await get_customer_360(session, cid)
        assert view is not None
        assert view["customer"]["name"] == "Test360"
        assert view["customer"]["address"] == "123 Street"
        assert "contracts" in view
        assert "tokens" in view
        assert view["mfi_name"] == "LOLC Cambodia"

    async def test_update_customer_tags(self, session):
        cid = await self._setup_360(session)
        await update_customer_tags(session, cid, ["VIP", "高风险"])
        c = await get_customer(session, cid)
        assert "VIP" in c["tags"]
        assert "高风险" in c["tags"]

    async def test_get_customers_filtered_by_tag(self, session):
        cid = await self._setup_360(session)
        await update_customer_tags(session, cid, ["VIP"])
        result = await get_customers_filtered(session, tags="VIP")
        assert len(result) >= 1
        empty = await get_customers_filtered(session, tags="NoSuchTag")
        assert len(empty) == 0


class TestMfiCRUD:
    async def test_add_and_list_mfi(self, session):
        mid = await add_mfi(session, "PRASAC", "Siem Reap")
        assert mid.startswith("MF")
        mfis = await get_mfis(session)
        assert len(mfis) == 1
        assert mfis[0]["name"] == "PRASAC"

    async def test_get_mfis_filter_by_status(self, session):
        await add_mfi(session, "ACLEDA", "Battambang")
        active = await get_mfis(session, status="active")
        assert len(active) == 1
        inactive = await get_mfis(session, status="disabled")
        assert len(inactive) == 0
