# PAYGO 控制器模拟脚本 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 开发在 Termux 中运行的 PAYGO 太阳能控制器模拟脚本（token_codec + state_manager + controller），并更新平台侧 token_engine 为新编码算法。

**Architecture:** 三个模块：`token_codec.py`（纯函数 Token 编解码）、`state_manager.py`（状态机 + JSON 持久化）、`controller.py`（终端 UI 交互循环）。平台侧 `token_engine.py` 同步实现相同编码算法。TDD 驱动：先写测试，再写实现。

**Tech Stack:** Python 3.10+ 标准库（json, os, datetime, select, sys）

---

### Task 1: 创建 controller 包结构和 Token Codec 测试

**Files:**
- Create: `controller/__init__.py`
- Create: `tests/test_token_codec.py`

- [ ] **Step 1: 创建 controller 包目录和空 __init__.py**

```bash
mkdir -p controller
```

Write `controller/__init__.py`:
```python
# PAYGO 控制器模块
```

- [ ] **Step 2: 编写 token_codec 测试文件**

Write `tests/test_token_codec.py`:
```python
import pytest
from controller.token_codec import generate, decode


class TestGenerate:
    def test_returns_8_digit_string(self):
        token = generate("Solar-001", 30)
        assert len(token) == 8
        assert token.isdigit()

    def test_known_device_30_days(self):
        token = generate("Solar-001", 30)
        assert token == "07030303"

    def test_different_device_different_hash(self):
        token_a = generate("Solar-001", 30)
        token_b = generate("Solar-002", 30)
        assert token_a[:4] != token_b[:4]

    def test_days_boundary_1(self):
        token = generate("X", 1)
        assert len(token) == 8
        assert token[4:7] == "001"
        assert token.isdigit()

    def test_days_boundary_365(self):
        token = generate("X", 365)
        assert token[4:7] == "365"


class TestDecode:
    def test_valid_token_returns_device_hash_and_days(self):
        result = decode("07030303")
        assert result is not None
        assert result["device_id_hash"] == 703
        assert result["days"] == 30

    def test_invalid_checksum_returns_none(self):
        assert decode("07030304") is None

    def test_wrong_length(self):
        assert decode("1234567") is None
        assert decode("123456789") is None

    def test_non_numeric(self):
        assert decode("abc12345") is None

    def test_empty_string(self):
        assert decode("") is None


class TestRoundtrip:
    def test_generate_then_decode(self):
        device_id = "Solar-001"
        days = 30
        token = generate(device_id, days)
        result = decode(token)
        assert result is not None
        assert result["days"] == days

    def test_multiple_devices(self):
        for device_id in ["Solar-001", "Solar-002", "ABC-999"]:
            for days in [1, 30, 365]:
                token = generate(device_id, days)
                result = decode(token)
                assert result is not None
                assert result["days"] == days
```

- [ ] **Step 3: 运行测试确认失败（模块不存在）**

Run: `cd /Users/qinzz/Desktop/paygo-platform && PYTHONPATH=. python -m pytest tests/test_token_codec.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'controller.token_codec'`

- [ ] **Step 4: 提交**

```bash
git add controller/__init__.py tests/test_token_codec.py
git commit -m "test: 添加 token_codec 测试用例"
```

---

### Task 2: 实现 Token Codec

**Files:**
- Create: `controller/token_codec.py`

- [ ] **Step 1: 实现 generate 和 decode 函数**

Write `controller/token_codec.py`:
```python
"""PAYGO Token 编解码模块。

Token 格式 (8位数字): {device_hash:4位}{days:3位}{checksum:1位}
- device_hash = sum(ord(c) for c in device_id) % 10000
- days = 天数 (1-365)
- checksum = (device_hash + days) % 10
"""


def generate(device_id: str, days: int) -> str:
    """生成 8 位数字 Token，编码 device_id 哈希 + 天数 + 校验位。"""
    char_sum = sum(ord(c) for c in device_id)
    device_hash = char_sum % 10000
    checksum = (device_hash + days) % 10
    return f"{device_hash:04d}{days:03d}{checksum}"


def decode(token: str) -> dict | None:
    """解码 8 位 Token，返回 {'device_id_hash': int, 'days': int} 或 None。"""
    if len(token) != 8 or not token.isdigit():
        return None
    device_hash = int(token[:4])
    days = int(token[4:7])
    checksum = int(token[7])
    expected = (device_hash + days) % 10
    if checksum != expected:
        return None
    return {"device_id_hash": device_hash, "days": days}
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd /Users/qinzz/Desktop/paygo-platform && PYTHONPATH=. python -m pytest tests/test_token_codec.py -v`
Expected: PASS (10 tests)

- [ ] **Step 3: 提交**

```bash
git add controller/token_codec.py
git commit -m "feat: 实现 token_codec (结构化 Token 编解码)"
```

---

### Task 3: State Manager 测试 + 实现

**Files:**
- Create: `tests/test_state_manager.py`
- Create: `controller/state_manager.py`

- [ ] **Step 1: 编写 state_manager 测试文件**

Write `tests/test_state_manager.py`:
```python
import json
import os
import tempfile
from datetime import date, timedelta

import pytest

import controller.state_manager as sm


@pytest.fixture
def temp_state_dir(monkeypatch):
    """使用临时目录替代 ~/.paygo"""
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))
        yield state_dir


class TestLoad:
    def test_no_file_returns_default(self, temp_state_dir):
        state = sm.load()
        assert state == sm.DEFAULT_STATE

    def test_existing_file_returns_saved_state(self, temp_state_dir):
        saved = {"device_id_hash": 703, "remaining_days": 27,
                 "last_update": "2026-05-17", "status": "active"}
        sm.save(saved)
        loaded = sm.load()
        assert loaded == saved


class TestSave:
    def test_create_directory_if_missing(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        state["status"] = "active"
        sm.save(state)
        assert os.path.exists(sm.STATE_FILE)
        with open(sm.STATE_FILE) as f:
            assert json.load(f)["status"] == "active"


class TestApplyToken:
    def test_unbound_to_active(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        today = date.today().isoformat()
        sm.apply_token(state, device_id_hash=703, days=30)
        assert state["status"] == "active"
        assert state["remaining_days"] == 30
        assert state["device_id_hash"] == 703
        assert state["last_update"] == today

    def test_active_stack_days_same_device(self, temp_state_dir):
        state = {"device_id_hash": 703, "remaining_days": 10,
                 "last_update": "2026-05-17", "status": "active"}
        sm.apply_token(state, device_id_hash=703, days=30)
        assert state["remaining_days"] == 40
        assert state["status"] == "active"

    def test_locked_to_active(self, temp_state_dir):
        state = {"device_id_hash": 703, "remaining_days": 0,
                 "last_update": "2026-05-10", "status": "locked"}
        sm.apply_token(state, device_id_hash=703, days=15)
        assert state["status"] == "active"
        assert state["remaining_days"] == 15


class TestTick:
    def test_reduces_days_by_date_difference(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=5)).isoformat()
        state = {"device_id_hash": 703, "remaining_days": 30,
                 "last_update": yesterday, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 25
        assert state["last_update"] == date.today().isoformat()
        assert state["status"] == "active"

    def test_goes_locked_when_days_run_out(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=35)).isoformat()
        state = {"device_id_hash": 703, "remaining_days": 30,
                 "last_update": yesterday, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"

    def test_no_change_same_day(self, temp_state_dir):
        today = date.today().isoformat()
        state = {"device_id_hash": 703, "remaining_days": 10,
                 "last_update": today, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 10
        assert state["status"] == "active"

    def test_does_not_change_unbound(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        sm.tick(state)
        assert state["status"] == "unbound"
        assert state["remaining_days"] == 0

    def test_does_not_change_locked(self, temp_state_dir):
        state = {"device_id_hash": 703, "remaining_days": 0,
                 "last_update": "2026-05-10", "status": "locked"}
        sm.tick(state)
        assert state["status"] == "locked"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/qinzz/Desktop/paygo-platform && PYTHONPATH=. python -m pytest tests/test_state_manager.py -v`
Expected: FAIL — `ModuleNotFoundError` 或 `ImportError`

- [ ] **Step 3: 实现 state_manager 模块**

Write `controller/state_manager.py`:
```python
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
    """日期推进：根据 actual 日期差递减天数，归零则锁定。"""
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/qinzz/Desktop/paygo-platform && PYTHONPATH=. python -m pytest tests/test_state_manager.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: 提交**

```bash
git add tests/test_state_manager.py controller/state_manager.py
git commit -m "feat: 实现 state_manager (状态机 + JSON 持久化)"
```

---

### Task 4: 更新平台 token_engine.py

**Files:**
- Modify: `app/token_engine.py`
- Modify: `tests/test_token_engine.py`

- [ ] **Step 1: 更新 test_token_engine.py 测试**

Read the existing test file first, then update.

Write updated `tests/test_token_engine.py`:
```python
"""测试 Token 引擎（结构化编码版本）。"""
from app.token_engine import generate_token


def test_generate_returns_8_digit_string():
    token = generate_token("Solar-001", 30)
    assert len(token) == 8
    assert token.isdigit()


def test_generate_known_device_known_days():
    token = generate_token("Solar-001", 30)
    assert token == "07030303"


def test_same_device_same_days_same_token():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-001", 30)
    assert t1 == t2


def test_different_device_different_hash():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-002", 30)
    assert t1[:4] != t2[:4]


def test_different_days_different_token():
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-001", 60)
    assert t1 != t2


def test_days_1():
    token = generate_token("X", 1)
    assert token[4:7] == "001"


def test_days_365():
    token = generate_token("X", 365)
    assert token[4:7] == "365"
```

- [ ] **Step 2: 运行测试确认失败（旧实现生成随机数）**

Run: `cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/test_token_engine.py -v`
Expected: FAIL — `test_generate_known_device_known_days` 断言失败（随机 Token 不等于 "07030303"）

- [ ] **Step 3: 更新 app/token_engine.py 实现**

Write updated `app/token_engine.py`:
```python
"""Token 生成模块。

生成 8 位结构化 Token: {device_hash:4}{days:3}{checksum:1}
与 controller/token_codec.py 实现相同算法。
"""


def generate_token(device_id: str, days: int) -> str:
    """生成 8 位数字 Token，编码 device_id 哈希 + 天数 + 校验位。"""
    char_sum = sum(ord(c) for c in device_id)
    device_hash = char_sum % 10000
    checksum = (device_hash + days) % 10
    return f"{device_hash:04d}{days:03d}{checksum}"
```

- [ ] **Step 4: 运行 token_engine 测试确认通过**

Run: `cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/test_token_engine.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: 运行全部测试确保无回归**

Run: `cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/ -v`
Expected: PASS (all existing + new tests, ~33 tests)

- [ ] **Step 6: 提交**

```bash
git add app/token_engine.py tests/test_token_engine.py
git commit -m "feat: token_engine 切换为结构化编码算法"
```

---

### Task 5: 实现 Controller 主入口脚本

**Files:**
- Create: `controller/controller.py`

- [ ] **Step 1: 实现 controller.py**

Write `controller/controller.py`:
```python
#!/usr/bin/env python3
"""PAYGO 太阳能控制器 — 终端模拟脚本。

运行在安卓 Termux 环境中，模拟 PAYGO 控制器的核心行为：
Token 本地解码验证、设备状态管理、天数递减。
"""

import os
import select
import sys

from controller.token_codec import decode
from controller.state_manager import load, save, apply_token, tick


STATUS_LABELS = {
    "unbound": "○ 未绑定",
    "active": "● 已激活",
    "locked": "◇ 已锁定",
}

RELAY_LABELS = {
    "unbound": "[断开]",
    "active": "[闭合] 供电中",
    "locked": "[断开] 天数用尽",
}


def clear_screen():
    os.system("clear")


def render(state):
    clear_screen()
    tick(state)

    device_display = f"#{state['device_id_hash']:04d}" if state["device_id_hash"] else "--"
    status = state["status"]
    days = state["remaining_days"]

    print("╔══════════════════════════════╗")
    print("║    PAYGO 太阳能控制器       ║")
    print("╠══════════════════════════════╣")
    print(f"║ 设备:   {device_display:<22}║")
    print(f"║ 状态:   {STATUS_LABELS[status]:<22}║")
    print(f"║ 剩余天数: {days} 天{'':<19}║")
    print(f"║ 继电器: {RELAY_LABELS[status]:<22}║")
    print("╚══════════════════════════════╝")
    print()
    print("[N] 输入新Token  [Q] 退出")


def main():
    state = load()
    while True:
        render(state)
        save(state)

        # 等待按键或 1 秒后刷新
        r, _, _ = select.select([sys.stdin], [], [], 1.0)
        if not r:
            continue

        key = sys.stdin.readline().strip().upper()
        if key == "Q":
            break
        elif key == "N":
            token = input("Token: ").strip()
            result = decode(token)
            if result is None:
                print("无效 Token，按回车键继续...")
                input()
                continue
            apply_token(state, result["device_id_hash"], result["days"])
            save(state)
            print(f"激活成功！+{result['days']} 天，按回车键继续...")
            input()

    print("控制器已退出。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 提交**

```bash
git add controller/controller.py
git commit -m "feat: 实现 controller 主入口脚本"
```

---

### Task 6: 端到端集成测试

**Files:**
- Create: `tests/test_controller_integration.py`

- [ ] **Step 1: 编写集成测试**

Write `tests/test_controller_integration.py`:
```python
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
```

- [ ] **Step 2: 运行集成测试**

Run: `cd /Users/qinzz/Desktop/paygo-platform && PYTHONPATH=. python -m pytest tests/test_controller_integration.py -v`
Expected: PASS (2 tests)

- [ ] **Step 3: 运行全部测试确认**

Run: `cd /Users/qinzz/Desktop/paygo-platform && python -m pytest tests/ -v`
Expected: PASS (all tests, ~35 tests)

- [ ] **Step 4: 提交**

```bash
git add tests/test_controller_integration.py
git commit -m "test: 添加控制器集成测试"
```

---

### Task 7: 在 PC 上手动验证 controller.py

- [ ] **Step 1: 首次运行（UNBOUND 状态）**

Run: `cd /Users/qinzz/Desktop/paygo-platform && PYTHONPATH=. python controller/controller.py`

Expected 显示：设备 `--`，状态 `○ 未绑定`，继电器 `[断开]`。

按 `Q` 退出。

- [ ] **Step 2: 生成 Token 并激活**

先用 Python 生成一个测试 Token：
```bash
cd /Users/qinzz/Desktop/paygo-platform && PYTHONPATH=. python -c "from controller.token_codec import generate; print(generate('Solar-001', 30))"
```

返回 Token 如 `07030303`。

再次启动 controller.py，按 `N`，输入 Token，验证显示：
- 设备 `#0703`
- 状态 `● 已激活`
- 剩余天数 `30 天`
- 继电器 `[闭合] 供电中`

按 `Q` 退出，重新启动后状态应保持。

- [ ] **Step 3: 清理测试状态**

```bash
rm -rf ~/.paygo
```
