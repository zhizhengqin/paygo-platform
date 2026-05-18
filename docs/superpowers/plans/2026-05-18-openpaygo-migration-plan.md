# OpenPAYGO 标准迁移实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 paygo-platform 自研 15 位 Token 方案替换为 OpenPAYGO 开源标准（9 位数字, SipHash 加密, count 防重放）

**Architecture:** 删除自研 `app/token_engine.py` 和 `controller/token_codec.py`，后端和控制器直接调用 `openpaygo` 库。Customer 模型新增 `secret_key` + `count`，控制器状态用 `secret_key` + `count` + `used_counts` 替换 `device_id_hash` + `used_tokens.json`。

**Tech Stack:** Python 3.12, FastAPI, openpaygo 0.6.3, SipHash, pytest

---

### Task 1: 删除旧代码 + 添加 openpaygo 依赖

**Files:**
- Delete: `app/token_engine.py`
- Delete: `controller/token_codec.py`
- Modify: `requirements.txt`

- [ ] **Step 1: 删除旧 token 模块**

Run:
```bash
rm /Users/qinzz/Desktop/paygo-platform/app/token_engine.py
rm /Users/qinzz/Desktop/paygo-platform/controller/token_codec.py
```

- [ ] **Step 2: 添加 openpaygo 到 requirements.txt**

Edit `requirements.txt`:

```diff
 fastapi>=0.100.0
 uvicorn[standard]>=0.23.0
 jinja2>=3.1.0
 python-multipart>=0.0.6
 pytest>=7.0.0
 httpx>=0.24.0
+openpaygo>=0.6.3
```

- [ ] **Step 3: 确认 openpaygo 已安装**

Run:
```bash
source /Users/qinzz/Desktop/paygo-platform/venv/bin/activate && python3 -c "from openpaygo import generate_token, decode_token, TokenType; print('openpaygo OK')"
```
Expected: `openpaygo OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add -A && git commit -m "$(cat <<'EOF'
chore: 删除自研 token 模块，添加 openpaygo 依赖
EOF
)"
```

---

### Task 2: 重写 app/db.py — Customer 模型加 secret_key + count

**Files:**
- Modify: `app/db.py`

- [ ] **Step 1: 更新 add_customer 签名和记录结构**

Edit `app/db.py`:

```python
import uuid
from datetime import datetime, timedelta

_customers: dict[str, dict] = {}
_tokens: list[dict] = []
_sms_records: list[dict] = []

_payment_rates: list[dict] = [
    {"amount": 5, "days": 30},
    {"amount": 10, "days": 60},
]


def get_customers() -> dict:
    return _customers


def get_customer(customer_id: str) -> dict | None:
    return _customers.get(customer_id)


def add_customer(name: str, phone: str, device_id: str, secret_key: str) -> str:
    cid = f"C{str(uuid.uuid4())[:4].upper()}"
    _customers[cid] = {
        "id": cid,
        "name": name,
        "phone": phone,
        "device_id": device_id,
        "secret_key": secret_key,
        "count": 0,
        "status": "locked",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "locked_at": None,
    }
    return cid


def get_customer_count(customer_id: str) -> int:
    return _customers[customer_id]["count"]


def set_customer_count(customer_id: str, new_count: int) -> None:
    _customers[customer_id]["count"] = new_count


def update_customer_status(customer_id: str, status: str) -> bool:
    if customer_id not in _customers:
        return False
    _customers[customer_id]["status"] = status
    if status == "locked":
        _customers[customer_id]["locked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return True


def delete_customer(customer_id: str) -> bool:
    if customer_id in _customers:
        del _customers[customer_id]
        return True
    return False


def reset_db():
    _customers.clear()
    _tokens.clear()
    _sms_records.clear()
    _payment_rates.clear()
    _payment_rates.extend([
        {"amount": 5, "days": 30},
        {"amount": 10, "days": 60},
    ])


def get_tokens() -> list:
    return _tokens


def add_token(customer_id: str, token: str, days: int, count: int) -> str:
    tid = f"T{str(uuid.uuid4())[:4].upper()}"
    now = datetime.now()
    _tokens.append({
        "id": tid,
        "customer_id": customer_id,
        "token": token,
        "days": days,
        "count": count,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    })
    return tid


def get_payment_rates() -> list[dict]:
    return _payment_rates


def get_days_for_amount(amount: float) -> int:
    for rate in _payment_rates:
        if rate["amount"] == amount:
            return rate["days"]
    return 0


def add_sms_record(customer_id: str, to_phone: str, message: str) -> str:
    sid = f"S{str(uuid.uuid4())[:4].upper()}"
    _sms_records.append({
        "id": sid,
        "customer_id": customer_id,
        "to": to_phone,
        "message": message,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    return sid


def get_sms_records(customer_id: str = None) -> list[dict]:
    if customer_id:
        return [r for r in _sms_records if r["customer_id"] == customer_id]
    return list(_sms_records)
```

- [ ] **Step 2: Commit**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add app/db.py && git commit -m "$(cat <<'EOF'
feat: Customer 模型添加 secret_key + count，token 记录加 count 字段
EOF
)"
```

---

### Task 3: 重写 controller/state_manager.py — secret_key + count + used_counts

**Files:**
- Modify: `controller/state_manager.py`

- [ ] **Step 1: 重写 state_manager.py**

Write `controller/state_manager.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add controller/state_manager.py && git commit -m "$(cat <<'EOF'
feat: 状态管理器迁移至 OpenPAYGO — secret_key/count/used_counts 替代 device_id_hash
EOF
)"
```

---

### Task 4: 重写 app/routers/customers.py — openpaygo Token 生成 + 无空格 SMS

**Files:**
- Modify: `app/routers/customers.py`

- [ ] **Step 1: 重写 customers.py**

Write `app/routers/customers.py`:

```python
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.db import (
    get_customers, get_customer, add_customer, delete_customer,
    get_tokens, add_token, update_customer_status, get_days_for_amount, add_sms_record,
    get_sms_records, set_customer_count,
)
from openpaygo import generate_token, TokenType

router = APIRouter(prefix="/api")


class CustomerCreate(BaseModel):
    name: str
    phone: str
    device_id: str
    secret_key: str


class TokenGenerate(BaseModel):
    days: int


SECRET_KEY_LENGTH = 32
SECRET_KEY_HEX_CHARS = set("0123456789abcdefABCDEF")


def _validate_secret_key(key: str) -> None:
    if len(key) != SECRET_KEY_LENGTH or not all(c in SECRET_KEY_HEX_CHARS for c in key):
        raise HTTPException(
            status_code=400,
            detail=f"secret_key 必须是 {SECRET_KEY_LENGTH} 位 hex 字符串",
        )


def _check_auth(request: Request):
    if request.cookies.get("session") != "authenticated":
        raise HTTPException(status_code=401, detail="未认证")


@router.get("/customers")
async def list_customers(request: Request):
    _check_auth(request)
    customers = get_customers()
    return list(customers.values())


@router.post("/customers")
async def create_customer(request: Request, body: CustomerCreate):
    _check_auth(request)
    _validate_secret_key(body.secret_key)
    cid = add_customer(
        name=body.name, phone=body.phone,
        device_id=body.device_id, secret_key=body.secret_key,
    )
    customer = get_customer(cid)
    return customer


@router.get("/customers/{customer_id}")
async def get_customer_detail(request: Request, customer_id: str):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer_route(request: Request, customer_id: str):
    _check_auth(request)
    ok = delete_customer(customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"ok": True}


@router.post("/customers/{customer_id}/token")
async def generate_token_for_customer(request: Request, customer_id: str, body: TokenGenerate):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        value=body.days,
        token_type=TokenType.ADD_TIME,
    )
    set_customer_count(customer_id, new_count)
    add_token(customer_id, token_str, body.days, new_count)

    return {
        "token": token_str,
        "customer_id": customer_id,
        "days": body.days,
    }


@router.get("/tokens")
async def list_tokens(request: Request):
    _check_auth(request)
    return get_tokens()


class SimulatePayment(BaseModel):
    amount: float


@router.post("/customers/{customer_id}/simulate-payment")
async def simulate_payment(request: Request, customer_id: str, body: SimulatePayment):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    days = get_days_for_amount(body.amount)
    if days == 0:
        raise HTTPException(status_code=400, detail=f"不支持的金额: ${body.amount}")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        value=days,
        token_type=TokenType.ADD_TIME,
    )
    set_customer_count(customer_id, new_count)
    add_token(customer_id, token_str, days, new_count)

    message = (
        f"[PAYGO Solar] 尊敬的用户，您已成功支付${body.amount:.2f}。"
        f"您的太阳能激活码为：{token_str}。"
        f"有效期{days}天。请尽快输入您的设备。"
    )
    add_sms_record(customer_id, customer["phone"], message)

    return {
        "token": token_str,
        "customer_id": customer_id,
        "days": days,
        "sms": {
            "to": customer["phone"],
            "message": message,
        },
    }


@router.post("/customers/{customer_id}/lock")
async def lock_device(request: Request, customer_id: str):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    update_customer_status(customer_id, "locked")
    return {"status": "ok"}


@router.post("/customers/{customer_id}/permanent-unlock")
async def permanent_unlock(request: Request, customer_id: str):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        token_type=TokenType.DISABLE_PAYG,
    )
    set_customer_count(customer_id, new_count)
    add_token(customer_id, token_str, -1, new_count)
    update_customer_status(customer_id, "permanent")

    message = (
        f"[PAYGO Solar] 恭喜！您的贷款已全部结清。"
        f"设备永久解锁码：{token_str}。"
        f"请在您的设备中输入此码以永久解锁。"
    )
    add_sms_record(customer_id, customer["phone"], message)

    return {
        "token": token_str,
        "customer_id": customer_id,
        "days": -1,
        "sms": {
            "to": customer["phone"],
            "message": message,
        },
    }


@router.get("/sms")
async def list_sms(request: Request, customer_id: str = None):
    _check_auth(request)
    return get_sms_records(customer_id)
```

- [ ] **Step 2: Commit**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add app/routers/customers.py && git commit -m "$(cat <<'EOF'
feat: 后端 API 迁移至 OpenPAYGO — 9位Token、无空格SMS、secret_key校验
EOF
)"
```

---

### Task 5: 重写 controller/controller.py — 9 位 Token UI + openpaygo 验证

**Files:**
- Modify: `controller/controller.py`

- [ ] **Step 1: 重写 controller.py**

Write `controller/controller.py`:

```python
#!/usr/bin/env python3
"""PAYGO 太阳能控制器 — 终端模拟脚本 (OpenPAYGO)。

运行在安卓 Termux 环境中，模拟 PAYGO 控制器的核心行为：
Token 解码验证（OpenPAYGO 9位）、设备状态管理、天数递减。
"""

import os

from openpaygo import decode_token, TokenType
from state_manager import (
    load, save, apply_token, tick, reset,
    fast_forward,
)


STATUS_LABELS = {
    "unbound": "未绑定",
    "active": "已激活",
    "locked": "已锁定",
    "permanent": "永久解锁",
}

RELAY_LABELS = {
    "unbound": "[断开]",
    "active": "[闭合] 供电中",
    "locked": "[断开] 天数用尽",
    "permanent": "[闭合] 供电中",
}

INNER = 28
LABEL_W = 8


def wlen(s: str) -> int:
    n = 0
    for c in s:
        n += 1 if ord(c) <= 127 else 2
    return n


def pad(s: str, width: int) -> str:
    return s + " " * (width - wlen(s))


def row(label: str, value: str) -> str:
    label_pad = label + " " * (LABEL_W - wlen(label))
    return "║" + pad(f" {label_pad}: {value}", INNER) + "║"


def clear_screen():
    os.system("clear")


def render(state):
    clear_screen()
    tick(state)

    key_display = state["secret_key"][:8] + "…" if state["secret_key"] else "--"
    status = state["status"]
    days = state["remaining_days"]

    print("╔══════════════════════════════╗")
    print("║" + pad("PAYGO 太阳能控制器", INNER) + "║")
    print("╠══════════════════════════════╣")
    print(row("设备密钥", key_display))
    print(row("状态", STATUS_LABELS[status]))
    if days == -1:
        print(row("剩余天数", "∞ 无限"))
    else:
        print(row("剩余天数", f"{days} 天"))
    print(row("继电器", RELAY_LABELS[status]))
    print(row("Count", str(state["count"])))
    print("╚══════════════════════════════╝")
    print()


def initial_setup(state):
    """首次运行时输入设备密钥。"""
    if state["secret_key"]:
        return
    clear_screen()
    print("╔══════════════════════════════╗")
    print("║" + pad("初始设置", INNER) + "║")
    print("╠══════════════════════════════╣")
    print("║ 请输入设备预设密钥 (32位hex) ║")
    print("╚══════════════════════════════╝")
    key = input("密钥: ").strip()
    if len(key) == 32 and all(c in "0123456789abcdefABCDEF" for c in key):
        state["secret_key"] = key
        save(state)
        print("密钥已保存，按回车键继续...")
    else:
        print("无效密钥格式，按回车键继续...")
    input()


def main():
    state = load()
    while True:
        initial_setup(state)
        render(state)
        save(state)
        print("[N] 输入新Token  [D] 模拟天数流逝  [R] 重置  [Q] 退出")
        cmd = input("> ").strip().upper()

        if cmd == "Q":
            break
        elif cmd == "R":
            confirm = input("确认重置？将清除绑定和天数 (y/N): ").strip().upper()
            if confirm == "Y":
                state = reset()
                print("已重置为未绑定状态，按回车键继续...")
                input()
            continue
        elif cmd == "D":
            try:
                days_input = input("快进天数: ").strip()
                days = int(days_input)
            except ValueError:
                print("无效天数，按回车键继续...")
                input()
                continue
            fast_forward(state, days)
            save(state)
            print(f"已快进 {days} 天，按回车键继续...")
            input()
            continue
        elif cmd == "N":
            if not state["secret_key"]:
                print("请先设置设备密钥，按回车键继续...")
                input()
                continue

            token = input("Token (9位): ").strip()
            if len(token) != 9 or not token.isdigit():
                print("✗ Token格式错误（需要9位数字），按回车键继续...")
                input()
                continue

            value, token_type, new_count, used_counts = decode_token(
                token=token,
                secret_key=state["secret_key"],
                count=state["count"],
                used_counts=state["used_counts"],
            )

            if token_type == TokenType.INVALID:
                print("✗ Token无效，按回车键继续...")
                input()
                continue
            elif token_type == TokenType.ALREADY_USED:
                print("✗ Token已使用过（防重放），按回车键继续...")
                input()
                continue

            apply_token(state, int(value) if value else 0,
                        token_type, new_count, used_counts)
            save(state)

            if token_type == TokenType.DISABLE_PAYG:
                print("✓✓✓ 贷款已结清！设备永久解锁！")
            else:
                print(f"✓ Token验证成功！增加{int(value)}天。")
            print(f"当前剩余{state['remaining_days']}天")
            print("按回车键继续...")
            input()

    print("控制器已退出。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add controller/controller.py && git commit -m "$(cat <<'EOF'
feat: 控制器迁移至 OpenPAYGO — 9位Token、密钥绑定、count防重放
EOF
)"
```

---

### Task 6: 重写测试文件

**Files:**
- Delete: `tests/test_token_codec.py`, `tests/test_token_engine.py`
- Modify: `tests/test_customers_api.py`, `tests/test_integration.py`, `tests/test_state_manager.py`, `tests/test_controller_integration.py`, `tests/test_upgrade.py`

- [ ] **Step 1: 删除旧测试文件**

Run:
```bash
rm /Users/qinzz/Desktop/paygo-platform/tests/test_token_codec.py
rm /Users/qinzz/Desktop/paygo-platform/tests/test_token_engine.py
```

- [ ] **Step 2: 重写 tests/test_state_manager.py**

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
        saved = {"secret_key": "a" * 32, "count": 2, "used_counts": [0, 1],
                 "remaining_days": 27, "last_update": "2026-05-17", "status": "active"}
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
    def test_add_time_from_unbound(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        today = date.today().isoformat()
        sm.apply_token(state, days=30, token_type=1, new_count=2, used_counts=[0, 1])
        assert state["status"] == "active"
        assert state["remaining_days"] == 30
        assert state["count"] == 2
        assert state["used_counts"] == [0, 1]
        assert state["last_update"] == today

    def test_add_time_stacks_days(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 2, "used_counts": [0, 1],
                 "remaining_days": 10, "last_update": "2026-05-17", "status": "active"}
        sm.apply_token(state, days=30, token_type=1, new_count=4, used_counts=[0, 1, 2, 3])
        assert state["remaining_days"] == 40
        assert state["count"] == 4
        assert state["status"] == "active"

    def test_locked_to_active(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 0, "last_update": "2026-05-10", "status": "locked"}
        sm.apply_token(state, days=15, token_type=1, new_count=2, used_counts=[0, 1])
        assert state["status"] == "active"
        assert state["remaining_days"] == 15

    def test_disable_payg_permanent(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        sm.apply_token(state, days=0, token_type=3, new_count=1, used_counts=[0])
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1
        assert state["count"] == 1

    def test_disable_payg_from_active(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 2, "used_counts": [0, 1],
                 "remaining_days": 5, "last_update": "2026-05-18", "status": "active"}
        sm.apply_token(state, days=0, token_type=3, new_count=3, used_counts=[0, 1, 2])
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1


class TestTick:
    def test_reduces_days_by_date_difference(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=5)).isoformat()
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 30, "last_update": yesterday, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 25
        assert state["last_update"] == date.today().isoformat()
        assert state["status"] == "active"

    def test_goes_locked_when_days_run_out(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=35)).isoformat()
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 30, "last_update": yesterday, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"

    def test_no_change_same_day(self, temp_state_dir):
        today = date.today().isoformat()
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 10, "last_update": today, "status": "active"}
        sm.tick(state)
        assert state["remaining_days"] == 10
        assert state["status"] == "active"

    def test_does_not_change_unbound(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        sm.tick(state)
        assert state["status"] == "unbound"
        assert state["remaining_days"] == 0

    def test_does_not_change_locked(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 0, "last_update": "2026-05-10", "status": "locked"}
        sm.tick(state)
        assert state["status"] == "locked"

    def test_does_not_reduce_permanent(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=100)).isoformat()
        state = {"secret_key": "a" * 32, "count": 1, "used_counts": [0],
                 "remaining_days": -1, "last_update": yesterday, "status": "permanent"}
        sm.tick(state)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"

    def test_permanent_stays_permanent_forever(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 1, "used_counts": [0],
                 "remaining_days": -1, "last_update": "2020-01-01", "status": "permanent"}
        sm.tick(state)
        assert state["status"] == "permanent"


class TestFastForward:
    def test_reduces_days(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 30, "last_update": "2026-05-18", "status": "active"}
        sm.fast_forward(state, 10)
        assert state["remaining_days"] == 20
        assert state["status"] == "active"

    def test_to_lock(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 0, "used_counts": [],
                 "remaining_days": 5, "last_update": "2026-05-18", "status": "active"}
        sm.fast_forward(state, 10)
        assert state["remaining_days"] == 0
        assert state["status"] == "locked"

    def test_permanent_does_nothing(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 1, "used_counts": [0],
                 "remaining_days": -1, "last_update": "2026-05-18", "status": "permanent"}
        sm.fast_forward(state, 999)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"


class TestReset:
    def test_reset_to_default(self, temp_state_dir):
        state = {"secret_key": "a" * 32, "count": 5, "used_counts": [0, 1, 2, 3, 4],
                 "remaining_days": 30, "last_update": "2026-05-18", "status": "active"}
        sm.save(state)
        new_state = sm.reset()
        assert new_state == sm.DEFAULT_STATE
        assert new_state["secret_key"] is None
        assert new_state["count"] == 0
```

- [ ] **Step 3: 运行状态管理器测试**

Run:
```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && python3 -m pytest tests/test_state_manager.py -v
```
Expected: all PASS

- [ ] **Step 4: 重写 tests/test_customers_api.py**

Write `tests/test_customers_api.py`:

```python
from fastapi.testclient import TestClient
from app.main import app
from app.db import reset_db

client = TestClient(app)

TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


class TestCreateCustomer:
    def test_create_customer_with_secret_key(self):
        from app.db import reset_db
        reset_db()
        cookie = _login()
        response = client.post("/api/customers", json={
            "name": "Sok Heng",
            "phone": "0888888001",
            "device_id": "Solar-001",
            "secret_key": TEST_KEY,
        }, cookies={"session": cookie})
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("C")
        assert data["name"] == "Sok Heng"
        assert data["secret_key"] == TEST_KEY
        assert data["count"] == 0

    def test_invalid_secret_key_rejected(self):
        cookie = _login()
        response = client.post("/api/customers", json={
            "name": "Bad Key",
            "phone": "000",
            "device_id": "D000",
            "secret_key": "too-short",
        }, cookies={"session": cookie})
        assert response.status_code == 400
        assert "secret_key" in response.json()["detail"]


class TestGetCustomers:
    def test_list(self):
        cookie = _login()
        response = client.get("/api/customers", cookies={"session": cookie})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_detail(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Mary Keo", "0966666002", "Solar-002", TEST_KEY)
        cookie = _login()
        response = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
        assert response.status_code == 200
        assert response.json()["name"] == "Mary Keo"

    def test_not_found(self):
        cookie = _login()
        response = client.get("/api/customers/C999", cookies={"session": cookie})
        assert response.status_code == 404

    def test_delete(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Delete Me", "000", "D000", TEST_KEY)
        cookie = _login()
        response = client.delete(f"/api/customers/{cid}", cookies={"session": cookie})
        assert response.status_code == 200
        assert response.json()["ok"] is True


class TestGenerateToken:
    def test_returns_9_digit_token(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Token Test", "0999999999", "Solar-099", TEST_KEY)
        cookie = _login()
        response = client.post(f"/api/customers/{cid}/token", json={
            "days": 30,
        }, cookies={"session": cookie})
        assert response.status_code == 200
        data = response.json()
        assert len(data["token"]) == 9
        assert data["token"].isdigit()
        assert data["customer_id"] == cid
        assert data["days"] == 30

    def test_two_generations_different_tokens(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Token Test", "0999999999", "Solar-099", TEST_KEY)
        cookie = _login()
        r1 = client.post(f"/api/customers/{cid}/token", json={
            "days": 30,
        }, cookies={"session": cookie})
        r2 = client.post(f"/api/customers/{cid}/token", json={
            "days": 30,
        }, cookies={"session": cookie})
        t1 = r1.json()["token"]
        t2 = r2.json()["token"]
        assert t1 != t2, f"Same device+days should produce DIFFERENT tokens: {t1}"


class TestListTokens:
    def test_list_tokens(self):
        cookie = _login()
        response = client.get("/api/tokens", cookies={"session": cookie})
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestAuth:
    def test_api_requires_auth(self):
        client.cookies.clear()
        response = client.get("/api/customers")
        assert response.status_code == 401


class TestSimulatePayment:
    def test_requires_auth(self):
        resp = client.post("/api/customers/C001/simulate-payment", json={"amount": 5})
        assert resp.status_code == 401

    def test_returns_9_digit_token_and_sms_no_spaces(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        token = data["token"]
        assert len(token) == 9
        assert token.isdigit()
        assert data["days"] == 30
        assert "sms" in data
        assert data["sms"]["to"] == "0888888001"
        assert "PAYGO" in data["sms"]["message"]
        # SMS中Token无空格，是整个9位数字
        assert token in data["sms"]["message"]

    def test_10_dollars_gives_60_days(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 10},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["days"] == 60

    def test_nonexistent_customer(self):
        cookie = _login()
        resp = client.post(
            "/api/customers/NOEXIST/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 404

    def test_unknown_amount(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 999},
            cookies={"session": cookie},
        )
        assert resp.status_code == 400

    def test_two_payments_different_tokens(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        r1 = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": cookie},
        )
        r2 = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": cookie},
        )
        assert r1.json()["token"] != r2.json()["token"]


class TestLockDevice:
    def test_lock_device(self):
        from app.db import reset_db, add_customer, get_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(f"/api/customers/{cid}/lock", cookies={"session": cookie})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        customer = get_customer(cid)
        assert customer["status"] == "locked"

    def test_lock_requires_auth(self):
        client.cookies.clear()
        resp = client.post("/api/customers/C001/lock")
        assert resp.status_code == 401


class TestPermanentUnlock:
    def test_returns_9_digit_permanent_token(self):
        from app.db import reset_db, add_customer, get_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/permanent-unlock",
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) == 9
        assert data["token"].isdigit()
        assert data["days"] == -1
        assert "sms" in data
        assert "全部结清" in data["sms"]["message"]

        customer = get_customer(cid)
        assert customer["status"] == "permanent"

    def test_requires_auth(self):
        client.cookies.clear()
        resp = client.post("/api/customers/C001/permanent-unlock")
        assert resp.status_code == 401
```

- [ ] **Step 5: 运行 API 测试**

Run:
```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && python3 -m pytest tests/test_customers_api.py -v
```
Expected: all PASS

- [ ] **Step 6: 重写 tests/test_upgrade.py**

Write `tests/test_upgrade.py`:

```python
"""升级集成测试：覆盖 5 个 MFI 演示场景 (OpenPAYGO 版本)。"""
from fastapi.testclient import TestClient

from app.main import app
from app.db import reset_db, add_customer, get_customer
from openpaygo import decode_token, TokenType
from controller.state_manager import (
    apply_token, fast_forward, DEFAULT_STATE,
)

client = TestClient(app)

TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


# ========== 场景一：首次支付解锁 ==========

class TestScene1FirstPayment:
    def test_scene1_full_flow(self):
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001", TEST_KEY)
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
        assert len(token) == 9
        assert data["days"] == 30
        assert "sms" in data

        # 控制器 decode + apply
        value, token_type, new_count, used_counts = decode_token(
            token=token,
            secret_key=TEST_KEY,
            count=0,
        )
        assert token_type == TokenType.ADD_TIME
        assert int(value) == 30

        state = dict(DEFAULT_STATE)
        state["secret_key"] = TEST_KEY
        apply_token(state, int(value), token_type, new_count, used_counts)
        assert state["status"] == "active"
        assert state["remaining_days"] == 30


# ========== 场景二：再次续费 ==========

class TestScene2Renewal:
    def test_scene2_days_stack(self):
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()

        # 第一次支付 $5 → 30天
        resp1 = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": cookie},
        )
        token1 = resp1.json()["token"]
        value1, type1, count1, used1 = decode_token(
            token=token1, secret_key=TEST_KEY, count=0,
        )
        state = dict(DEFAULT_STATE)
        state["secret_key"] = TEST_KEY
        apply_token(state, int(value1), type1, count1, used1)
        assert state["remaining_days"] == 30

        # 第二次支付 $10 → 60天，累计90天
        resp2 = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 10}, cookies={"session": cookie},
        )
        token2 = resp2.json()["token"]
        value2, type2, count2, used2 = decode_token(
            token=token2, secret_key=TEST_KEY, count=count1, used_counts=used1,
        )
        apply_token(state, int(value2), type2, count2, used2)
        assert state["remaining_days"] == 90

    def test_scene2_tokens_are_different(self):
        """同设备同金额两次充值，Token 必须不同"""
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        r1 = client.post(f"/api/customers/{cid}/simulate-payment",
                         json={"amount": 5}, cookies={"session": cookie})
        r2 = client.post(f"/api/customers/{cid}/simulate-payment",
                         json={"amount": 5}, cookies={"session": cookie})
        assert r1.json()["token"] != r2.json()["token"]


# ========== 场景三：错误Token ==========

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


# ========== 场景四：逾期锁定 + 防重放 ==========

class TestScene4ExpiredLock:
    def test_replay_blocked_by_openpaygo(self):
        """同一个 Token 第二次 decode 返回 ALREADY_USED"""
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5}, cookies={"session": cookie},
        )
        token = resp.json()["token"]

        # 第一次使用
        value, token_type, count, used = decode_token(
            token=token, secret_key=TEST_KEY, count=0,
        )
        assert token_type == TokenType.ADD_TIME

        # 第二次使用（重放）
        value2, type2, count2, used2 = decode_token(
            token=token, secret_key=TEST_KEY, count=count, used_counts=used,
        )
        assert type2 == TokenType.ALREADY_USED

    def test_fast_forward_to_lock(self):
        state = {
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


# ========== 场景五：贷款结清永久解锁 ==========

class TestScene5PermanentUnlock:
    def test_permanent_unlock_full_flow(self):
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001", TEST_KEY)
        cookie = _login()

        resp = client.post(
            f"/api/customers/{cid}/permanent-unlock",
            cookies={"session": cookie},
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

        state = dict(DEFAULT_STATE)
        state["secret_key"] = TEST_KEY
        apply_token(state, 0, token_type, count, used)
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1

        c = get_customer(cid)
        assert c["status"] == "permanent"

    def test_permanent_not_affected_by_fast_forward(self):
        state = {
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
```

- [ ] **Step 7: 运行升级测试**

Run:
```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && python3 -m pytest tests/test_upgrade.py -v
```
Expected: all PASS

- [ ] **Step 8: 重写 tests/test_controller_integration.py**

Write `tests/test_controller_integration.py`:

```python
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

        # 1. 初始状态 UNBOUND，设置密钥
        state = sm.load()
        state["secret_key"] = TEST_KEY
        assert state["status"] == "unbound"

        # 2. 生成 + 输入 Token（30天）
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

        # 3. 状态持久化
        state2 = sm.load()
        assert state2["status"] == "active"
        assert state2["remaining_days"] == 30

        # 4. 续费 15 天（count 已更新，不会重复）
        new_count2, token2 = generate_token(
            secret_key=TEST_KEY, count=count, value=15,
            token_type=TokenType.ADD_TIME,
        )
        value2, type2, count2, used2 = decode_token(
            token=token2, secret_key=TEST_KEY, count=count, used_counts=used,
        )
        sm.apply_token(state2, int(value2), type2, count2, used2)
        assert state2["remaining_days"] == 45

        # 5. 模拟天数递减 50 天 → locked
        past = (date.today() - timedelta(days=50)).isoformat()
        state2["last_update"] = past
        sm.tick(state2)
        assert state2["remaining_days"] == 0
        assert state2["status"] == "locked"

        # 6. LOCKED 状态输入新 Token 重新激活
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

        # 7. Token 不重复 — 同样的(device,duration)生成不同token
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

        # 无效 Token 被拒绝
        value, token_type, count, used = decode_token(
            token="123456789", secret_key=TEST_KEY, count=0,
        )
        assert token_type in (TokenType.INVALID, TokenType.ALREADY_USED)

        # 状态未变化
        assert state["status"] == "unbound"


def test_disable_payg_full_flow(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, ".paygo")
        monkeypatch.setattr(sm, "STATE_DIR", state_dir)
        monkeypatch.setattr(sm, "STATE_FILE", os.path.join(state_dir, "state.json"))

        state = sm.load()
        state["secret_key"] = TEST_KEY

        # 生成永久解锁 Token
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

        # 第一次 decode
        value, token_type, count, used = decode_token(
            token=token, secret_key=TEST_KEY, count=0,
        )
        assert token_type == TokenType.ADD_TIME

        # 第二次 decode（重放）
        value2, type2, count2, used2 = decode_token(
            token=token, secret_key=TEST_KEY, count=count, used_counts=used,
        )
        assert type2 == TokenType.ALREADY_USED
```

- [ ] **Step 9: 运行控制器集成测试**

Run:
```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && python3 -m pytest tests/test_controller_integration.py -v
```
Expected: all PASS

- [ ] **Step 10: 重写 tests/test_integration.py**

Write `tests/test_integration.py`:

```python
from fastapi.testclient import TestClient
from app.main import app
from app.db import reset_db

client = TestClient(app)

TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


def test_full_user_flow():
    from app.db import reset_db
    reset_db()
    cookie = _login()

    # 1. 创建客户
    resp = client.post("/api/customers", json={
        "name": "Sok Heng",
        "phone": "0888888001",
        "device_id": "Solar-001",
        "secret_key": TEST_KEY,
    }, cookies={"session": cookie})
    assert resp.status_code == 200
    cid = resp.json()["id"]

    # 2. 查看客户列表
    resp = client.get("/api/customers", cookies={"session": cookie})
    customers = resp.json()
    assert any(c["id"] == cid for c in customers)

    # 3. 查看客户详情
    resp = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.json()["name"] == "Sok Heng"

    # 4. 生成 Token (9位)
    resp = client.post(f"/api/customers/{cid}/token", json={
        "days": 30,
    }, cookies={"session": cookie})
    assert resp.status_code == 200
    token_data = resp.json()
    assert len(token_data["token"]) == 9
    assert token_data["days"] == 30

    # 5. 查看 Token 历史
    resp = client.get("/api/tokens", cookies={"session": cookie})
    tokens = resp.json()
    assert len(tokens) == 1
    assert tokens[0]["customer_id"] == cid

    # 6. 删除客户
    resp = client.delete(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.json()["ok"] is True

    # 7. 确认已删除
    resp = client.get(f"/api/customers/{cid}", cookies={"session": cookie})
    assert resp.status_code == 404


def test_login_flow():
    resp = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert "用户名或密码错误" in resp.text

    resp = client.post("/login", data={
        "username": "admin",
        "password": "admin123",
    }, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"

    cookie = resp.cookies.get("session")
    resp = client.get("/logout", cookies={"session": cookie}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"


def test_ui_pages_render():
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "PAYGO Solar" in resp.text
    assert "/static/style.css" in resp.text

    login_resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    cookie = login_resp.cookies.get("session")
    resp = client.get("/dashboard", cookies={"session": cookie})
    assert resp.status_code == 200
    assert "客户列表" in resp.text
    assert "模拟支付" in resp.text
    assert "锁定设备" in resp.text
    assert "永久解锁" in resp.text
```

- [ ] **Step 11: 运行端到端测试**

Run:
```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && python3 -m pytest tests/test_integration.py -v
```
Expected: all PASS

- [ ] **Step 12: Commit all tests**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add tests/ && git commit -m "$(cat <<'EOF'
test: 全部测试迁移至 OpenPAYGO — 9位Token、count防重放、secret_key
EOF
)"
```

---

### Task 7: 全量测试 + 清理

- [ ] **Step 1: 删除旧的 used_tokens.json（如存在）**

Run:
```bash
rm -f ~/.paygo/used_tokens.json ~/.paygo/state.json
```

- [ ] **Step 2: 运行全量测试**

Run:
```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && python3 -m pytest tests/ -v
```
Expected: all PASS, no failures, no errors

- [ ] **Step 3: 修复任何失败或导入错误**

检查每个失败测试，确保：
- `from openpaygo import ...` 正确导入
- `TokenType.ADD_TIME = 1`, `TokenType.DISABLE_PAYG = 3`
- `apply_token` 使用新签名
- Token 长度断言从 15 改为 9

- [ ] **Step 4: 最终 Commit**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add -A && git commit -m "$(cat <<'EOF'
feat: OpenPAYGO 标准迁移完成 — 全量测试通过
EOF
)"
```

---

### Task 8: 手动验证控制器（可选）

- [ ] **Step 1: 启动后台服务**

Run (background):
```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 创建客户并生成 Token**

```bash
# 创建客户
curl -s -b /tmp/paygo-cookies.txt -X POST http://localhost:8000/api/customers \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Test\",\"phone\":\"099\",\"device_id\":\"D001\",\"secret_key\":\"a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6\"}"

# 模拟支付，记录输出的 Token
curl -s -b /tmp/paygo-cookies.txt -X POST http://localhost:8000/api/customers/<CID>/simulate-payment \
  -H "Content-Type: application/json" -d '{"amount": 5}'
```

- [ ] **Step 3: 控制器输入 Token 验证**

Run:
```bash
cd /Users/qinzz/Desktop/paygo-platform/controller && source ../venv/bin/activate && python3 -c "
from openpaygo import decode_token, TokenType
from state_manager import load, save, apply_token

state = load()
state['secret_key'] = 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'
token = input('Token: ').strip()
value, token_type, new_count, used_counts = decode_token(
    token=token, secret_key=state['secret_key'], count=state['count'],
    used_counts=state.get('used_counts'),
)
print(f'type={token_type}, value={value}, count={new_count}')
if token_type == TokenType.ADD_TIME:
    apply_token(state, int(value), token_type, new_count, used_counts)
    save(state)
    print(f'激活成功，剩余{state[\"remaining_days\"]}天')
elif token_type == TokenType.ALREADY_USED:
    print('Token已使用过')
elif token_type == TokenType.INVALID:
    print('Token无效')
"
```
