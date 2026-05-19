"""升级集成测试：覆盖 5 个 MFI 演示场景 (OpenPAYGO + PostgreSQL 版本)。"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from openpaygo import decode_token, TokenType
from controller.state_manager import apply_token, fast_forward


TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


@pytest.fixture(autouse=True)
async def setup_redis():
    from app.redis import init_redis, close_redis
    r = await init_redis()
    await r.flushdb()
    yield
    await r.flushdb()
    await close_redis()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client):
    resp = await client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


async def _create_customer(client, sid, name="Sok Heng", phone="0888888001",
                          device_id="SN-KH-001", secret_key=TEST_KEY):
    resp = await client.post("/api/customers", json={
        "name": name, "phone": phone,
        "device_id": device_id, "secret_key": secret_key,
    }, cookies={"session": sid})
    return resp.json()["id"]


class TestScene1FirstPayment:
    async def test_scene1_full_flow(self, client):
        sid = await _login(client)
        cid = await _create_customer(client, sid)

        resp = await client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
            cookies={"session": sid},
        )
        assert resp.status_code == 200
        data = resp.json()
        token = data["token"]
        assert len(token) == 9
        assert data["days"] == 30
        assert "sms" in data

        value, token_type, new_count, used_counts = decode_token(
            token=token, secret_key=TEST_KEY, count=0,
        )
        assert token_type == TokenType.ADD_TIME
        assert int(value) == 30

        state = {
            "device_id": "test-1",
            "secret_key": TEST_KEY,
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": None,
            "status": "unbound",
        }
        apply_token(state, int(value), token_type, new_count, used_counts)
        assert state["status"] == "active"
        assert state["remaining_days"] == 30


class TestScene2Renewal:
    async def test_scene2_days_stack(self, client):
        sid = await _login(client)
        cid = await _create_customer(client, sid)

        resp1 = await client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": sid},
        )
        token1 = resp1.json()["token"]
        value1, type1, count1, used1 = decode_token(
            token=token1, secret_key=TEST_KEY, count=0,
        )
        state = {
            "device_id": "test-scene2",
            "secret_key": TEST_KEY,
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": None,
            "status": "unbound",
        }
        apply_token(state, int(value1), type1, count1, used1)
        assert state["remaining_days"] == 30

        resp2 = await client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 10}, cookies={"session": sid},
        )
        token2 = resp2.json()["token"]
        value2, type2, count2, used2 = decode_token(
            token=token2, secret_key=TEST_KEY, count=count1, used_counts=used1,
        )
        apply_token(state, int(value2), type2, count2, used2)
        assert state["remaining_days"] == 90

    async def test_scene2_tokens_are_different(self, client):
        sid = await _login(client)
        cid = await _create_customer(client, sid)
        r1 = await client.post(f"/api/customers/{cid}/simulate-payment",
                               json={"amount": 5}, cookies={"session": sid})
        r2 = await client.post(f"/api/customers/{cid}/simulate-payment",
                               json={"amount": 5}, cookies={"session": sid})
        assert r1.json()["token"] != r2.json()["token"]


class TestScene3InvalidToken:
    def test_wrong_length_rejected(self):
        value, token_type, new_count, used_counts = decode_token(
            token="12345", secret_key=TEST_KEY, count=0,
        )
        assert token_type == TokenType.INVALID

    def test_all_nines_rejected(self):
        value, token_type, new_count, used_counts = decode_token(
            token="999999999", secret_key=TEST_KEY, count=0,
        )
        assert token_type in (TokenType.INVALID, TokenType.ALREADY_USED) or \
            token_type == TokenType.INVALID


class TestScene4ExpiredLock:
    async def test_replay_blocked_by_openpaygo(self, client):
        sid = await _login(client)
        cid = await _create_customer(client, sid)
        resp = await client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": sid},
        )
        token = resp.json()["token"]

        value, token_type, count, used = decode_token(
            token=token, secret_key=TEST_KEY, count=0, used_counts=[],
        )
        assert token_type == TokenType.ADD_TIME

        value2, type2, count2, used2 = decode_token(
            token=token, secret_key=TEST_KEY, count=count, used_counts=used,
        )
        assert type2 == TokenType.ALREADY_USED

    def test_fast_forward_to_lock(self):
        state = {
            "device_id": "test-ff",
            "secret_key": TEST_KEY,
            "count": 2,
            "used_counts": [0, 1],
            "remaining_days": 5,
            "last_update": "2026-05-18",
            "status": "active",
        }
        fast_forward(state, 10)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"


class TestScene5PermanentUnlock:
    async def test_permanent_unlock_full_flow(self, client):
        sid = await _login(client)
        cid = await _create_customer(client, sid)

        resp = await client.post(
            f"/api/customers/{cid}/permanent-unlock",
            cookies={"session": sid},
        )
        assert resp.status_code == 200
        data = resp.json()
        token = data["token"]
        assert len(token) == 9
        assert data["days"] == -1
        assert "sms" in data

        value, token_type, count, used = decode_token(
            token=token, secret_key=TEST_KEY, count=0,
        )
        assert token_type == TokenType.DISABLE_PAYG

        state = {
            "device_id": "test-permanent",
            "secret_key": TEST_KEY,
            "count": 0,
            "used_counts": [],
            "remaining_days": 0,
            "last_update": None,
            "status": "unbound",
        }
        apply_token(state, 0, token_type, count, used)
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1

    def test_permanent_not_affected_by_fast_forward(self):
        state = {
            "device_id": "test-perm-ff",
            "secret_key": TEST_KEY,
            "count": 1,
            "used_counts": [0],
            "remaining_days": -1,
            "last_update": "2026-05-18",
            "status": "permanent",
        }
        fast_forward(state, 999)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"
