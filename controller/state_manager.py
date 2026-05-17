"""状态机 + JSON 持久化模块。

管理控制器状态（unbound/active/locked），处理天数递减和状态转换。
"""

import json
import os
from datetime import date

STATE_DIR = os.path.join(os.path.expanduser("~"), ".paygo")
STATE_FILE = os.path.join(STATE_DIR, "state.json")

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


def apply_token(state: dict, device_id_hash: int, days: int) -> None:
    """解码后的 Token 应用到状态：绑定设备、叠加天数、激活。"""
    state["device_id_hash"] = device_id_hash
    state["remaining_days"] = state["remaining_days"] + days
    state["last_update"] = date.today().isoformat()
    state["status"] = "active"


def tick(state: dict) -> None:
    """日期推进：根据实际日期差递减天数，归零则锁定。"""
    if state["status"] != "active":
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
