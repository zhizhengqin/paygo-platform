"""集成测试：验证 token_codec → state_manager → 状态流转 全链路。"""
import os
import tempfile
from datetime import date, timedelta

import controller.state_manager as sm
from controller.token_codec import generate, decode


def test_full_lifecycle(monkeypatch):
    """模拟完整生命周期：激活 → 叠加 → 过期锁定 → 重新激活"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))

        # 1. 初始状态 UNBOUND
        state = sm.load()
        assert state["status"] == "unbound"

        # 2. 输入 Token（模拟用户输入 Solar-001, 30天）
        token = generate("Solar-001", 30)
        result = decode(token)
        sm.apply_token(state, result["device_id_hash"], result["days"])
        sm.save(state)
        assert state["status"] == "active"
        assert state["remaining_days"] == 30

        # 3. 再次加载，状态持久化
        state2 = sm.load()
        assert state2["status"] == "active"
        assert state2["remaining_days"] == 30

        # 4. 叠加 Token（续费 15 天）
        token2 = generate("Solar-001", 15)
        result2 = decode(token2)
        sm.apply_token(state2, result2["device_id_hash"], result2["days"])
        assert state2["remaining_days"] == 45

        # 5. 模拟天数递减（直接修改 last_update 为 50 天前）
        past = (date.today() - timedelta(days=50)).isoformat()
        state2["last_update"] = past
        sm.tick(state2)
        assert state2["remaining_days"] == 0
        assert state2["status"] == "locked"

        # 6. LOCKED 状态输入新 Token 重新激活
        token3 = generate("Solar-001", 7)
        result3 = decode(token3)
        sm.apply_token(state2, result3["device_id_hash"], result3["days"])
        assert state2["status"] == "active"
        assert state2["remaining_days"] == 7


def test_invalid_token_rejected(monkeypatch):
    """无效 Token 被拒绝，状态不变"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))

        state = sm.load()
        assert state["status"] == "unbound"

        # 无效 Token 不解码
        assert decode("99999999") is None  # checksum 大概率不匹配
        assert decode("abc12345") is None
        assert decode("") is None

        # 状态未变化
        assert state["status"] == "unbound"
