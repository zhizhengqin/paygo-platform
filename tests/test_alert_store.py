"""告警 store 层测试"""
import secrets
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Base
from app.settings import TEST_DATABASE_URL

def _key(): return secrets.token_hex(16)

@pytest.fixture(scope="function")
def engine():
    return create_async_engine(TEST_DATABASE_URL, echo=False)

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
    async with async_session() as s: yield s


class TestAlertCRUD:
    async def _setup(self, session):
        from app.security import init_fernet; init_fernet()
        from app.store import seed_alert_rules, add_customer, add_loan_product, add_contract, approve_contract
        await seed_alert_rules(session)
        pid = await add_loan_product(session, "6kW", Decimal("6"), 12, Decimal("10"), Decimal("20"), Decimal("690"))
        cid = await add_customer(session, "AlertT", "+8551", "DEV-AL1", "a"*32)
        ct_id = await add_contract(session, cid, pid, Decimal("138"), Decimal("552"), Decimal("46"), date(2025,1,1), date(2026,1,1))
        await approve_contract(session, ct_id)
        return cid, ct_id

    async def test_seed_rules(self, session):
        from app.store import seed_alert_rules, get_alert_rules
        await seed_alert_rules(session)
        rules = await get_alert_rules(session)
        assert len(rules) == 3

    async def test_create_alert(self, session):
        from app.store import seed_alert_rules, create_alert, get_alerts
        await seed_alert_rules(session)
        cid, ct_id = await self._setup(session)
        aid = await create_alert(session, "ALM-001", "逾期未还款", contract_id=ct_id, customer_id=cid, detail="已逾期3天")
        assert aid.startswith("AL")
        alerts = await get_alerts(session)
        assert len(alerts) == 1
        assert alerts[0]["status"] == "pending"

    async def test_claim_resolve_flow(self, session):
        from app.store import seed_alert_rules, create_alert, claim_alert, resolve_alert, get_alert_detail
        await seed_alert_rules(session)
        cid, ct_id = await self._setup(session)
        aid = await create_alert(session, "ALM-001", "test", ct_id, cid)
        assert await claim_alert(session, aid, "admin")
        a = await get_alert_detail(session, aid)
        assert a["status"] == "claimed" and a["claimed_by"] == "admin"
        assert await resolve_alert(session, aid, "已联系客户")
        a = await get_alert_detail(session, aid)
        assert a["status"] == "closed"

    async def test_escalate(self, session):
        from app.store import seed_alert_rules, create_alert, escalate_alert, get_alert_detail
        await seed_alert_rules(session)
        cid, ct_id = await self._setup(session)
        aid = await create_alert(session, "ALM-002", "P2 test", ct_id, cid, level="P2")
        assert await escalate_alert(session, aid)
        a = await get_alert_detail(session, aid)
        assert a["level"] == "P1"

    async def test_alert_stats(self, session):
        from app.store import seed_alert_rules, create_alert, get_alert_stats
        await seed_alert_rules(session)
        cid, ct_id = await self._setup(session)
        await create_alert(session, "ALM-001", "test", ct_id, cid)
        stats = await get_alert_stats(session)
        assert stats["total"] >= 1 and "today" in stats
