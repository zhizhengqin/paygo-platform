"""state_manager.py 测试 — PostgreSQL 持久化 + 状态机逻辑。"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models import Base, DeviceState
from app.settings import TEST_DATABASE_URL
import controller.state_manager as sm

TEST_DEVICE = "test-device"


@pytest.fixture(autouse=True)
async def setup_test_db(monkeypatch):
    """每个测试使用独立的测试数据库连接，测试前后清理。"""
    monkeypatch.setattr(sm, "DATABASE_URL", TEST_DATABASE_URL)
    # 重置 engine 全局状态，使用测试库
    sm._engine = None
    sm._session_factory = None

    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    # 清理 state_manager 内部的 engine
    if sm._engine is not None:
        await sm._engine.dispose()
        sm._engine = None
        sm._session_factory = None


class TestLoad:
    async def test_no_row_returns_default(self, setup_test_db):
        state = await sm.load(TEST_DEVICE)
        assert state["device_id"] == TEST_DEVICE
        assert state["secret_key"] is None
        assert state["count"] == 0
        assert state["used_counts"] == []
        assert state["remaining_days"] == 0
        assert state["last_update"] is None
        assert state["status"] == "unbound"

    async def test_existing_row_returns_saved_state(self, setup_test_db):
        saved = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 2,
            "used_counts": [0, 1],
            "remaining_days": 27,
            "last_update": "2026-05-17",
            "status": "active",
        }
        await sm.save(saved)
        loaded = await sm.load(TEST_DEVICE)
        assert loaded == saved


class TestSave:
    async def test_persist_and_reload(self, setup_test_db):
        saved = {
            "device_id": TEST_DEVICE,
            "secret_key": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": None,
            "status": "active",
        }
        await sm.save(saved)
        loaded = await sm.load(TEST_DEVICE)
        assert loaded["status"] == "active"
        assert loaded["secret_key"] == saved["secret_key"]


class TestApplyToken:
    async def test_add_time_from_unbound(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": None,
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": None,
            "status": "unbound",
        }
        today = date.today().isoformat()
        sm.apply_token(state, days=30, token_type=1, new_count=2, used_counts=[0, 1])
        assert state["status"] == "active"
        assert state["remaining_days"] == 30
        assert state["count"] == 2
        assert state["used_counts"] == [0, 1]
        assert state["last_update"] == today

    async def test_add_time_stacks_days(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 2,
            "used_counts": [0, 1],
            "remaining_days": 10,
            "last_update": "2026-05-17",
            "status": "active",
        }
        sm.apply_token(state, days=30, token_type=1, new_count=4, used_counts=[0, 1, 2, 3])
        assert state["remaining_days"] == 40
        assert state["count"] == 4
        assert state["status"] == "active"

    async def test_locked_to_active(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": "2026-05-10",
            "status": "locked",
        }
        sm.apply_token(state, days=15, token_type=1, new_count=2, used_counts=[0, 1])
        assert state["status"] == "active"
        assert state["remaining_days"] == 15

    async def test_disable_payg_permanent(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": None,
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": None,
            "status": "unbound",
        }
        sm.apply_token(state, days=0, token_type=3, new_count=1, used_counts=[0])
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1
        assert state["count"] == 1

    async def test_disable_payg_from_active(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 2,
            "used_counts": [0, 1],
            "remaining_days": 5,
            "last_update": "2026-05-18",
            "status": "active",
        }
        sm.apply_token(state, days=0, token_type=3, new_count=3, used_counts=[0, 1, 2])
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1


class TestTick:
    async def test_reduces_days_by_date_difference(self, setup_test_db):
        yesterday = (date.today() - timedelta(days=5)).isoformat()
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 0,
            "used_counts": [],
            "remaining_days": 30,
            "last_update": yesterday,
            "status": "active",
        }
        sm.tick(state)
        assert state["remaining_days"] == 25
        assert state["last_update"] == date.today().isoformat()
        assert state["status"] == "active"

    async def test_goes_locked_when_days_run_out(self, setup_test_db):
        yesterday = (date.today() - timedelta(days=35)).isoformat()
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 0,
            "used_counts": [],
            "remaining_days": 30,
            "last_update": yesterday,
            "status": "active",
        }
        sm.tick(state)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"

    async def test_no_change_same_day(self, setup_test_db):
        today = date.today().isoformat()
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 0,
            "used_counts": [],
            "remaining_days": 10,
            "last_update": today,
            "status": "active",
        }
        sm.tick(state)
        assert state["remaining_days"] == 10
        assert state["status"] == "active"

    async def test_does_not_change_unbound(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": None,
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": None,
            "status": "unbound",
        }
        sm.tick(state)
        assert state["status"] == "unbound"
        assert state["remaining_days"] == 0

    async def test_does_not_change_locked(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": "2026-05-10",
            "status": "locked",
        }
        sm.tick(state)
        assert state["status"] == "locked"

    async def test_does_not_reduce_permanent(self, setup_test_db):
        yesterday = (date.today() - timedelta(days=100)).isoformat()
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 1,
            "used_counts": [0],
            "remaining_days": -1,
            "last_update": yesterday,
            "status": "permanent",
        }
        sm.tick(state)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"

    async def test_permanent_stays_permanent_forever(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 1,
            "used_counts": [0],
            "remaining_days": -1,
            "last_update": "2020-01-01",
            "status": "permanent",
        }
        sm.tick(state)
        assert state["status"] == "permanent"


class TestFastForward:
    async def test_reduces_days(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 0,
            "used_counts": [],
            "remaining_days": 30,
            "last_update": "2026-05-18",
            "status": "active",
        }
        sm.fast_forward(state, 10)
        assert state["remaining_days"] == 20
        assert state["status"] == "active"

    async def test_to_lock(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 0,
            "used_counts": [],
            "remaining_days": 5,
            "last_update": "2026-05-18",
            "status": "active",
        }
        sm.fast_forward(state, 10)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"

    async def test_permanent_does_nothing(self, setup_test_db):
        state = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 1,
            "used_counts": [0],
            "remaining_days": -1,
            "last_update": "2026-05-18",
            "status": "permanent",
        }
        sm.fast_forward(state, 999)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"


class TestReset:
    async def test_reset_to_default(self, setup_test_db):
        saved = {
            "device_id": TEST_DEVICE,
            "secret_key": "a" * 32,
            "count": 5,
            "used_counts": [0, 1, 2, 3, 4],
            "remaining_days": 30,
            "last_update": "2026-05-18",
            "status": "active",
        }
        await sm.save(saved)
        new_state = await sm.reset(TEST_DEVICE)
        assert new_state["secret_key"] is None
        assert new_state["count"] == 0
        assert new_state["used_counts"] == []
        assert new_state["remaining_days"] == 0
        assert new_state["last_update"] is None
        assert new_state["status"] == "unbound"
