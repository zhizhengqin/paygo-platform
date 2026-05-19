"""集成测试：验证 openpaygo → state_manager → 状态流转 全链路 (OpenPAYGO + async PostgreSQL 版本)。"""
import os
import uuid

import pytest

import controller.state_manager as sm
from openpaygo import generate_token, decode_token, TokenType
from app.settings import TEST_DATABASE_URL

TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


@pytest.fixture(autouse=True)
def reset_sm_engine(monkeypatch):
    """每个测试前：重置 state_manager 的引擎与数据库连接，指向测试数据库。"""
    monkeypatch.setattr(sm, "DATABASE_URL", TEST_DATABASE_URL, raising=False)
    sm._engine = None
    sm._session_factory = None


@pytest.mark.asyncio
async def test_full_lifecycle():
    dev_id = f"test_full_{uuid.uuid4().hex[:6]}"
    state = await sm.load(device_id=dev_id)
    state["secret_key"] = TEST_KEY
    assert state["status"] == "unbound"

    new_count, token = generate_token(
        secret_key=TEST_KEY, count=0, value=30,
        token_type=TokenType.ADD_TIME,
    )
    assert len(token) == 9
    value, token_type, count, used = decode_token(
        token=token, secret_key=TEST_KEY, count=0,
    )
    sm.apply_token(state, int(value), token_type, count, used)
    await sm.save(state)
    assert state["status"] == "active"
    assert state["remaining_days"] == 30

    state2 = await sm.load(device_id=dev_id)
    assert state2["status"] == "active"
    assert state2["remaining_days"] == 30

    new_count2, token2 = generate_token(
        secret_key=TEST_KEY, count=count, value=15,
        token_type=TokenType.ADD_TIME,
    )
    value2, type2, count2, used2 = decode_token(
        token=token2, secret_key=TEST_KEY, count=count, used_counts=used,
    )
    sm.apply_token(state2, int(value2), type2, count2, used2)
    assert state2["remaining_days"] == 45

    from datetime import date, timedelta
    past = (date.today() - timedelta(days=50)).isoformat()
    state2["last_update"] = past
    sm.tick(state2)
    assert state2["remaining_days"] == 0
    assert state2["status"] == "locked"

    new_count3, token3 = generate_token(
        secret_key=TEST_KEY, count=count2, value=7,
        token_type=TokenType.ADD_TIME,
    )
    value3, type3, count3, used3 = decode_token(
        token=token3, secret_key=TEST_KEY, count=count2, used_counts=used2,
    )
    sm.apply_token(state2, int(value3), type3, count3, used3)
    assert state2["status"] == "active"
    assert state2["remaining_days"] == 7

    new_count4, token4 = generate_token(
        secret_key=TEST_KEY, count=count3, value=7,
        token_type=TokenType.ADD_TIME,
    )
    assert token3 != token4, "同一输入应生成不同 token"


@pytest.mark.asyncio
async def test_invalid_token_rejected():
    dev_id = f"test_invalid_{uuid.uuid4().hex[:6]}"
    state = await sm.load(device_id=dev_id)
    state["secret_key"] = TEST_KEY
    assert state["status"] == "unbound"

    value, token_type, count, used = decode_token(
        token="123456789", secret_key=TEST_KEY, count=0,
    )
    assert token_type in (TokenType.INVALID, TokenType.ALREADY_USED)

    assert state["status"] == "unbound"


@pytest.mark.asyncio
async def test_disable_payg_full_flow():
    dev_id = f"test_disable_{uuid.uuid4().hex[:6]}"
    state = await sm.load(device_id=dev_id)
    state["secret_key"] = TEST_KEY

    new_count, token = generate_token(
        secret_key=TEST_KEY, count=0,
        token_type=TokenType.DISABLE_PAYG,
    )
    value, token_type, count, used = decode_token(
        token=token, secret_key=TEST_KEY, count=0,
    )
    assert token_type == TokenType.DISABLE_PAYG

    sm.apply_token(state, 0, token_type, count, used)
    assert state["status"] == "permanent"
    assert state["remaining_days"] == -1


@pytest.mark.asyncio
async def test_replay_rejected():
    new_count, token = generate_token(
        secret_key=TEST_KEY, count=0, value=30,
        token_type=TokenType.ADD_TIME,
    )

    value, token_type, count, used = decode_token(
        token=token, secret_key=TEST_KEY, count=0,
    )
    assert token_type == TokenType.ADD_TIME

    value2, type2, count2, used2 = decode_token(
        token=token, secret_key=TEST_KEY, count=count, used_counts=used,
    )
    assert type2 == TokenType.ALREADY_USED
