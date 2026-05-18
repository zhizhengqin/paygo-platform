"""状态机 + JSON 持久化模块 — OpenPAYGO 版本。

管理控制器状态（unbound/active/locked/permanent），处理天数递减和状态转换。
使用 openpaygo 的 count 机制替代旧的 is_token_used/mark_token_used。
"""

import json
import os
from datetime import date

STATE_DIR = os.path.join(os.path.expanduser("~"), ".paygo")
STATE_FILE = os.path.join(STATE_DIR, "state.json")

DEFAULT_STATE = {
    "secret_key": None,
    "count": 0,
    "used_counts": [],
    "remaining_days": 0,
    "last_update": None,
    "status": "unbound",
}


def load() -> dict:
    if not os.path.exists(STATE_FILE):
        return dict(DEFAULT_STATE)
    with open(STATE_FILE) as f:
        return json.load(f)


def save(state: dict) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def apply_token(state: dict, days: int, token_type: int, new_count: int,
                used_counts: list | None) -> None:
    """解码后的 Token 应用到状态。

    token_type:
      TokenType.ADD_TIME=1 — 累加天数到 remaining_days
      TokenType.DISABLE_PAYG=3 — 永久解锁
    """
    if token_type == 3:  # DISABLE_PAYG
        state["remaining_days"] = -1
        state["last_update"] = date.today().isoformat()
        state["status"] = "permanent"
    else:  # ADD_TIME
        state["remaining_days"] = state["remaining_days"] + days
        state["last_update"] = date.today().isoformat()
        state["status"] = "active"

    state["count"] = new_count
    if used_counts is not None:
        state["used_counts"] = used_counts


def reset() -> dict:
    state = dict(DEFAULT_STATE)
    save(state)
    return state


def tick(state: dict) -> None:
    """日期推进：根据实际日期差递减天数，归零则锁定。permanent 状态不递减。"""
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
