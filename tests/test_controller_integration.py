"""集成测试：验证 openpaygo → state_manager → 状态流转 全链路 (OpenPAYGO 版本)。"""
import os
import tempfile
from datetime import date, timedelta

import controller.state_manager as sm
from openpaygo import generate_token, decode_token, TokenType

TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def test_full_lifecycle(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))

        state = sm.load()
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
        sm.save(state)
        assert state["status"] == "active"
        assert state["remaining_days"] == 30

        state2 = sm.load()
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
        assert token3 != token4, "Same inputs should produce different tokens"


def test_invalid_token_rejected(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))

        state = sm.load()
        state["secret_key"] = TEST_KEY
        assert state["status"] == "unbound"

        value, token_type, count, used = decode_token(
            token="123456789", secret_key=TEST_KEY, count=0,
        )
        assert token_type in (TokenType.INVALID, TokenType.ALREADY_USED)

        assert state["status"] == "unbound"


def test_disable_payg_full_flow(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))

        state = sm.load()
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


def test_replay_rejected(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))

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
