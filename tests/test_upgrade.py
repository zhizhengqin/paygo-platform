"""
升级集成测试：覆盖 5 个 MFI 演示场景。
测试服务端 API 和控制器终端行为。
"""

from fastapi.testclient import TestClient

from app.main import app
from app.db import reset_db, add_customer, get_customer
from controller.token_codec import decode
from controller.state_manager import (
    apply_token,
    mark_token_used,
    is_token_used,
    fast_forward,
    DEFAULT_STATE,
)

client = TestClient(app)


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


# ========== 场景一：首次支付解锁 ==========

class TestScene1FirstPayment:
    def test_scene1_full_flow(self):
        """创建 SN-KH-001 status=locked → 模拟支付$5 → 15位Token → decode → apply → status=active, remaining_days=30"""
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001")
        c = get_customer(cid)
        assert c["status"] == "locked"

        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        token = data["token"]
        assert len(token) == 15
        assert data["days"] == 30
        assert "sms" in data
        assert data["sms"]["to"] == "0888888001"

        # 控制器 decode + apply
        result = decode(token)
        assert result is not None
        assert result["type"] == 1
        assert result["days"] == 30

        state = dict(DEFAULT_STATE)
        apply_token(state, result["device_id_hash"], result["days"], result["type"])
        assert state["status"] == "active"
        assert state["remaining_days"] == 30


# ========== 场景二：再次续费 ==========

class TestScene2Renewal:
    def test_scene2_days_stack(self):
        """第一次$5(30天) → 第二次$10(60天) → remaining_days=90"""
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001")
        cookie = _login()

        # 第一次支付 $5
        resp1 = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": cookie},
        )
        token1 = resp1.json()["token"]
        result1 = decode(token1)
        state = dict(DEFAULT_STATE)
        apply_token(state, result1["device_id_hash"], result1["days"], result1["type"])
        assert state["remaining_days"] == 30

        # 第二次支付 $10
        resp2 = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 10}, cookies={"session": cookie},
        )
        token2 = resp2.json()["token"]
        result2 = decode(token2)
        apply_token(state, result2["device_id_hash"], result2["days"], result2["type"])
        assert state["remaining_days"] == 90


# ========== 场景三：错误Token ==========

class TestScene3InvalidToken:
    def test_all_ones_rejected(self):
        result = decode("111111111111111")
        assert result is None

    def test_wrong_length_rejected(self):
        assert decode("12345") is None
        assert decode("1234567890123456") is None

    def test_non_numeric_rejected(self):
        assert decode("abcde1234567890") is None

    def test_bad_checksum_rejected(self):
        from controller.token_codec import generate
        token = generate("SN-KH-001", 30)
        bad = token[:14] + str((int(token[14]) + 1) % 10)
        assert decode(bad) is None


# ========== 场景四：逾期锁定 ==========

class TestScene4ExpiredLock:
    def test_old_token_replay_blocked(self):
        """用过一次再输入 → 防重放命中"""
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": cookie},
        )
        token = resp.json()["token"]

        result = decode(token)
        state = dict(DEFAULT_STATE)
        apply_token(state, result["device_id_hash"], result["days"], result["type"])
        mark_token_used(token)

        assert is_token_used(token)

    def test_fast_forward_to_lock(self):
        """快进耗尽天数 → locked"""
        state = {
            "device_id_hash": 12345,
            "remaining_days": 5,
            "last_update": "2026-05-18",
            "status": "active",
        }
        fast_forward(state, 10)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"


# ========== 场景五：贷款结清永久解锁 ==========

class TestScene5PermanentUnlock:
    def test_permanent_unlock_full_flow(self):
        """后台永久解锁 → type=99 Token → decode → apply → status=permanent"""
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001")
        cookie = _login()

        resp = client.post(
            f"/api/customers/{cid}/permanent-unlock",
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        token = data["token"]
        assert len(token) == 15
        assert token[9:11] == "99"
        assert data["days"] == -1
        assert "sms" in data

        result = decode(token)
        assert result is not None
        assert result["type"] == 99
        assert result["days"] == 0

        state = dict(DEFAULT_STATE)
        apply_token(state, result["device_id_hash"], result["days"], result["type"])
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1

        c = get_customer(cid)
        assert c["status"] == "permanent"

    def test_permanent_not_affected_by_fast_forward(self):
        """permanent 状态不受 fast_forward 影响"""
        state = {
            "device_id_hash": 12345,
            "remaining_days": -1,
            "last_update": "2026-05-18",
            "status": "permanent",
        }
        fast_forward(state, 999)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"
