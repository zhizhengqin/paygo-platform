"""状态机 + JSON 持久化模块。

管理控制器状态（unbound/active/locked/permanent），处理天数递减和状态转换。
"""

import hashlib
import json
import os
from datetime import date

STATE_DIR = os.path.join(os.path.expanduser("~"), ".paygo")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
USED_TOKENS_FILE = os.path.join(STATE_DIR, "used_tokens.json")

DEFAULT_STATE = {
    "device_id_hash": None,
    "remaining_days": 0,
    "last_update": None,
    "status": "unbound",
}


def load() -> dict:
    """从 ~/.paygo/state.json 加载状态，不存在则返回默认值。"""
    if not os.path.exists(STATE_FILE):
        return dict(DEFAULT_STATE)
    with open(STATE_FILE) as f:
        return json.load(f)


def save(state: dict) -> None:
    """持久化状态到 ~/.paygo/state.json。"""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _load_used_tokens() -> dict:
    """加载已用 Token 记录。"""
    if not os.path.exists(USED_TOKENS_FILE):
        return {"hashes": []}
    with open(USED_TOKENS_FILE) as f:
        return json.load(f)


def _save_used_tokens(data: dict) -> None:
    """保存已用 Token 记录。"""
    os.makedirs(os.path.dirname(USED_TOKENS_FILE), exist_ok=True)
    with open(USED_TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_token_used(token: str) -> bool:
    """检查 Token 是否已被使用过。"""
    h = hashlib.sha256(token.encode()).hexdigest()[:16]
    data = _load_used_tokens()
    return h in data["hashes"]


def mark_token_used(token: str) -> None:
    """标记 Token 为已使用。"""
    h = hashlib.sha256(token.encode()).hexdigest()[:16]
    data = _load_used_tokens()
    if h not in data["hashes"]:
        data["hashes"].append(h)
        _save_used_tokens(data)


def apply_token(state: dict, device_id_hash: int, days: int, token_type: int = 1) -> None:
    """解码后的 Token 应用到状态。

    token_type=1:  激活Token，累加天数
    token_type=99: DISABLE_PAYG，永久解锁
    """
    if token_type == 99:
        apply_permanent_unlock(state, device_id_hash)
    else:
        state["device_id_hash"] = device_id_hash
        state["remaining_days"] = state["remaining_days"] + days
        state["last_update"] = date.today().isoformat()
        state["status"] = "active"


def apply_permanent_unlock(state: dict, device_id_hash: int) -> None:
    """永久解锁：设置 permanent 状态，天数无限。"""
    state["device_id_hash"] = device_id_hash
    state["remaining_days"] = -1
    state["last_update"] = date.today().isoformat()
    state["status"] = "permanent"


def reset() -> dict:
    """重置为默认状态并持久化。"""
    state = dict(DEFAULT_STATE)
    save(state)
    return state


def tick(state: dict) -> None:
    """日期推进：根据实际日期差递减天数，归零则锁定。
    permanent 状态不递减。
    """
    if state["status"] in ("unbound", "locked", "permanent"):
        return
    today = date.today()
    last = (
        date.fromisoformat(state["last_update"])
        if state["last_update"]
        else today
    )
    days_passed = (today - last).days
    if days_passed <= 0:
        return
    state["remaining_days"] = max(0, state["remaining_days"] - days_passed)
    state["last_update"] = today.isoformat()
    if state["remaining_days"] <= 0:
        state["remaining_days"] = 0
        state["status"] = "locked"


def fast_forward(state: dict, days: int) -> None:
    """调试用：直接递减 remaining_days，归零则锁定。"""
    if state["status"] == "permanent":
        return
    state["remaining_days"] = max(0, state["remaining_days"] - days)
    if state["remaining_days"] <= 0:
        state["remaining_days"] = 0
        state["status"] = "locked"
    state["last_update"] = date.today().isoformat()
