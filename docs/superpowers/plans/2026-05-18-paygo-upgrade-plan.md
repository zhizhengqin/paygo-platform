# PAYGO 平台升级实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 PAYGO 平台原型从 8 位 Token / 3 状态升级到 15 位 Token / 4 状态，覆盖 5 个 MFI 演示场景。

**Architecture:** 同步升级服务端 `app/token_engine.py` 和终端 `controller/token_codec.py` 的编解码算法；在 `customers.py` 扩展 3 个 API 端点；新增 `config.py` 路由管理支付汇率；`db.py` 扩展客户字段和短信记录存储；控制器新增 permanent 状态、防重放和 [D] 调试快进命令。

**Tech Stack:** Python FastAPI, Jinja2, pytest, 内存 dict 存储

---

### Task 1: Token 引擎 15 位编码 (app/token_engine.py)

**Files:**
- Modify: `app/token_engine.py`
- Modify: `tests/test_token_engine.py`

- [ ] **Step 1: 更新测试 — 15 位输出 + type 编码**

在 `tests/test_token_engine.py` 末尾追加以下测试：

```python
class Test15DigitToken:
    """15位Token编码：{device_hash:5}{value:4}{type:2}{checksum:4}"""

    def test_generate_returns_15_digit_string(self):
        token = generate_token("Solar-001", 30)
        assert len(token) == 15
        assert token.isdigit()

    def test_known_device_30_days_15digit(self):
        token = generate_token("Solar-001", 30)
        # device_hash = sum(ord(c) for c in "Solar-001") % 100000
        char_sum = sum(ord(c) for c in "Solar-001")
        expected_hash = char_sum % 100000
        expected_value = 30
        expected_type = 1
        expected_checksum = (expected_hash + expected_value + expected_type) % 10000
        expected = f"{expected_hash:05d}{expected_value:04d}01{expected_checksum:04d}"
        assert token == expected

    def test_generate_disabled(self):
        token = generate_token("SN-KH-001", -1)  # -1 signals DISABLE_PAYG
        # type=99, value=0000
        char_sum = sum(ord(c) for c in "SN-KH-001")
        expected_hash = char_sum % 100000
        expected_checksum = (expected_hash + 0 + 99) % 10000
        expected = f"{expected_hash:05d}000099{expected_checksum:04d}"
        assert token == expected

    def test_days_boundary_1(self):
        token = generate_token("X", 1)
        assert token[5:9] == "0001"
        assert token[9:11] == "01"

    def test_days_boundary_3650(self):
        token = generate_token("X", 3650)
        assert token[5:9] == "3650"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_token_engine.py::Test15DigitToken -v
```
预期：所有 Test15DigitToken 测试 FAIL（因为 generate_token 仍返回 8 位）

- [ ] **Step 3: 重写 `generate_token` 实现 15 位编码**

替换 `app/token_engine.py` 全部内容：

```python
"""Token 生成模块。

生成 15 位结构化 Token: {device_hash:5}{value:4}{type:2}{checksum:4}
- type=01: 激活Token (PAY), value 编码天数
- type=99: 永久解锁Token (DISABLE_PAYG), value 填 0000

与 controller/token_codec.py 实现相同算法，修改时两处一起改。
"""


def generate_token(device_id: str, days: int) -> str:
    """生成 15 位数字 Token。

    days 为 -1 时生成 DISABLE_PAYG Token (type=99, value=0000)。
    否则生成激活 Token (type=01)，天数范围 1-3650。
    """
    char_sum = sum(ord(c) for c in device_id)
    device_hash = char_sum % 100000

    if days == -1:
        value = 0
        token_type = 99
    else:
        if not (1 <= days <= 3650):
            raise ValueError(f"days 必须在 1-3650 之间，收到 {days}")
        value = days
        token_type = 1

    checksum = (device_hash + value + token_type) % 10000
    return f"{device_hash:05d}{value:04d}{token_type:02d}{checksum:04d}"
```

- [ ] **Step 4: 运行全部 token_engine 测试**

```bash
pytest tests/test_token_engine.py -v
```
预期：新测试 PASS，旧测试可能 FAIL（因输出变为15位，旧断言改为8位）

- [ ] **Step 5: 更新旧测试适配 15 位**

修改 `tests/test_token_engine.py` 中的旧测试：

```python
def test_generate_returns_8_digit_string(self):
    token = generate_token("Solar-001", 30)
    assert len(token) == 15
    assert token.isdigit()

def test_generate_known_device_known_days(self):
    token = generate_token("Solar-001", 30)
    char_sum = sum(ord(c) for c in "Solar-001")
    expected_hash = char_sum % 100000
    expected = f"{expected_hash:05d}003001{((expected_hash + 30 + 1) % 10000):04d}"
    assert token == expected

def test_same_device_same_days_same_token(self):
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-001", 30)
    assert t1 == t2

def test_different_device_different_hash(self):
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-002", 30)
    assert t1[:5] != t2[:5]

def test_different_days_different_token(self):
    t1 = generate_token("Solar-001", 30)
    t2 = generate_token("Solar-001", 60)
    assert t1 != t2

def test_days_1(self):
    token = generate_token("X", 1)
    assert token[5:9] == "0001"

def test_days_365(self):
    token = generate_token("X", 365)
    assert token[5:9] == "0365"
```

- [ ] **Step 6: 确认全部测试通过**

```bash
pytest tests/test_token_engine.py -v
```
预期：ALL PASS

- [ ] **Step 7: Commit**

```bash
git add app/token_engine.py tests/test_token_engine.py
git commit -m "feat: token 引擎升级至 15 位编码，支持 type=01/99"
```

---

### Task 2: 控制器 Token 编解码 15 位 (controller/token_codec.py)

**Files:**
- Modify: `controller/token_codec.py`
- Modify: `tests/test_token_codec.py`

- [ ] **Step 1: 更新测试 — 15 位解码 + type 识别**

在 `tests/test_token_codec.py` 末尾追加：

```python
class Test15DigitCodec:
    """15位Token编解码：{device_hash:5}{value:4}{type:2}{checksum:4}"""

    def test_generate_returns_15_digit(self):
        token = generate("Solar-001", 30)
        assert len(token) == 15
        assert token.isdigit()

    def test_generate_and_decode_roundtrip_type01(self):
        token = generate("Solar-001", 30)
        result = decode(token)
        assert result is not None
        assert result["days"] == 30
        assert result["type"] == 1

    def test_generate_disable_payg(self):
        token = generate("SN-KH-001", -1)
        result = decode(token)
        assert result is not None
        assert result["days"] == 0
        assert result["type"] == 99

    def test_decode_invalid_checksum(self):
        # 构造一个校验位错误的 token
        token = generate("X", 30)
        # 修改最后一位打乱校验
        bad_token = token[:14] + str((int(token[14]) + 1) % 10)
        assert decode(bad_token) is None

    def test_decode_wrong_length(self):
        assert decode("12345678901234") is None   # 14位
        assert decode("1234567890123456") is None  # 16位

    def test_decode_non_numeric(self):
        assert decode("a" * 15) is None

    def test_decode_invalid_type(self):
        # 构造 type=02 (非法) 的 token
        char_sum = sum(ord(c) for c in "X")
        dh = char_sum % 100000
        cs = (dh + 30 + 2) % 10000
        token = f"{dh:05d}003002{cs:04d}"
        assert decode(token) is None

    def test_roundtrip_multiple(self):
        for device_id in ["Solar-001", "SN-KH-002", "ABC-999"]:
            for days in [1, 30, 365, 3650]:
                token = generate(device_id, days)
                result = decode(token)
                assert result is not None, f"decode failed for {device_id}/{days}"
                assert result["days"] == days
                assert result["type"] == 1


class TestLegacy8Digit:
    """8位旧格式Token应该被拒绝"""

    def test_old_8_digit_rejected(self):
        assert decode("07030303") is None

    def test_old_8_digit_generate_no_longer_works(self):
        # generate 现在返回15位
        token = generate("Solar-001", 30)
        assert len(token) == 15
```

- [ ] **Step 2: 运行测试确认新测试失败**

```bash
pytest tests/test_token_codec.py::Test15DigitCodec tests/test_token_codec.py::TestLegacy8Digit -v
```
预期：15位测试 FAIL（还是旧实现）

- [ ] **Step 3: 重写 `controller/token_codec.py`**

```python
"""PAYGO Token 编解码模块。

Token 格式 (15位数字): {device_hash:5}{value:4}{type:2}{checksum:4}
- device_hash = sum(ord(c) for c in device_id) % 100000
- value = 天数 (1-3650)，type=99 时填 0000
- type = 01(激活) 或 99(永久解锁)
- checksum = (device_hash + value + type) % 10000

⚠ 算法与 app/token_engine.py 必须保持同步，修改时两处一起改。
"""

VALID_TYPES = {1, 99}


def generate(device_id: str, days: int) -> str:
    """生成 15 位数字 Token。

    days 为 -1 时生成 DISABLE_PAYG Token (type=99, value=0000)。
    否则生成激活 Token (type=01)，天数范围 1-3650。
    """
    char_sum = sum(ord(c) for c in device_id)
    device_hash = char_sum % 100000

    if days == -1:
        value = 0
        token_type = 99
    else:
        if not (1 <= days <= 3650):
            raise ValueError(f"days 必须在 1-3650 之间，收到 {days}")
        value = days
        token_type = 1

    checksum = (device_hash + value + token_type) % 10000
    return f"{device_hash:05d}{value:04d}{token_type:02d}{checksum:04d}"


def decode(token: str) -> dict | None:
    """解码 15 位 Token，返回 {'device_id_hash': int, 'days': int, 'type': int} 或 None。"""
    if len(token) != 15 or not token.isdigit():
        return None
    device_hash = int(token[:5])
    value = int(token[5:9])
    token_type = int(token[9:11])
    checksum = int(token[11:15])
    expected = (device_hash + value + token_type) % 10000
    if checksum != expected:
        return None
    if token_type not in VALID_TYPES:
        return None
    days = 0 if token_type == 99 else value
    return {"device_id_hash": device_hash, "days": days, "type": token_type}
```

- [ ] **Step 4: 更新旧测试适配 15 位**

修改 `tests/test_token_codec.py` 中 `TestGenerate` 和 `TestDecode` 和 `TestRoundtrip` 类：

```python
class TestGenerate:
    def test_returns_15_digit_string(self):
        token = generate("Solar-001", 30)
        assert len(token) == 15
        assert token.isdigit()

    def test_known_device_30_days(self):
        token = generate("Solar-001", 30)
        char_sum = sum(ord(c) for c in "Solar-001")
        dh = char_sum % 100000
        cs = (dh + 30 + 1) % 10000
        assert token == f"{dh:05d}003001{cs:04d}"

    def test_different_device_different_hash(self):
        token_a = generate("Solar-001", 30)
        token_b = generate("Solar-002", 30)
        assert token_a[:5] != token_b[:5]

    def test_days_boundary_1(self):
        token = generate("X", 1)
        assert len(token) == 15
        assert token[5:9] == "0001"
        assert token.isdigit()

    def test_days_boundary_3650(self):
        token = generate("X", 3650)
        assert token[5:9] == "3650"


class TestDecode:
    def test_valid_token_returns_full_dict(self):
        char_sum = sum(ord(c) for c in "Solar-001")
        dh = char_sum % 100000
        cs = (dh + 30 + 1) % 10000
        token = f"{dh:05d}003001{cs:04d}"
        result = decode(token)
        assert result is not None
        assert result["device_id_hash"] == dh
        assert result["days"] == 30
        assert result["type"] == 1

    def test_invalid_checksum_returns_none(self):
        char_sum = sum(ord(c) for c in "Solar-001")
        dh = char_sum % 100000
        cs = (dh + 30 + 1) % 10000
        bad_cs = (cs + 1) % 10000
        token = f"{dh:05d}003001{bad_cs:04d}"
        assert decode(token) is None

    def test_wrong_length(self):
        assert decode("12345678901234") is None
        assert decode("1234567890123456") is None

    def test_non_numeric(self):
        assert decode("abc123456789012") is None

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
        assert result["type"] == 1

    def test_multiple_devices(self):
        for device_id in ["Solar-001", "Solar-002", "ABC-999"]:
            for days in [1, 30, 365, 3650]:
                token = generate(device_id, days)
                result = decode(token)
                assert result is not None
                assert result["days"] == days
                assert result["type"] == 1
```

- [ ] **Step 5: 运行全部 token_codec 测试**

```bash
pytest tests/test_token_codec.py -v
```
预期：ALL PASS

- [ ] **Step 6: Commit**

```bash
git add controller/token_codec.py tests/test_token_codec.py
git commit -m "feat: 控制器 token 编解码升级至 15 位，支持 type 识别"
```

---

### Task 3: 数据库模型扩展 (app/db.py)

**Files:**
- Modify: `app/db.py`
- Create/Modify: `tests/test_db.py`

- [ ] **Step 1: 读取现有 db.py 测试文件确认结构**

```bash
pytest tests/test_db.py -v
```

- [ ] **Step 2: 更新 db.py 新增存储和函数**

替换 `app/db.py` 全部内容：

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


def add_customer(name: str, phone: str, device_id: str) -> str:
    cid = f"C{str(uuid.uuid4())[:4].upper()}"
    _customers[cid] = {
        "id": cid,
        "name": name,
        "phone": phone,
        "device_id": device_id,
        "remaining_days": 0,
        "status": "locked",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "locked_at": None,
    }
    return cid


def update_customer_status(customer_id: str, status: str) -> bool:
    """更新客户状态: active / locked / permanent"""
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
    """Clear all in-memory data. Useful for tests."""
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


def add_token(customer_id: str, token: str, days: int) -> str:
    tid = f"T{str(uuid.uuid4())[:4].upper()}"
    now = datetime.now()
    _tokens.append({
        "id": tid,
        "customer_id": customer_id,
        "token": token,
        "days": days,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    })
    return tid


def get_payment_rates() -> list[dict]:
    return _payment_rates


def get_days_for_amount(amount: float) -> int:
    """根据金额查询对应天数，未匹配返回 0"""
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

- [ ] **Step 3: 更新 tests/test_db.py**

如果 `tests/test_db.py` 存在旧测试，需要更新以匹配新接口。确保以下测试通过：

```python
from app.db import (
    get_customers, get_customer, add_customer, update_customer_status,
    delete_customer, reset_db, get_tokens, add_token,
    get_payment_rates, get_days_for_amount,
    add_sms_record, get_sms_records,
)


class TestPaymentRates:
    def test_default_rates_exist(self):
        rates = get_payment_rates()
        assert len(rates) == 2
        assert rates[0] == {"amount": 5, "days": 30}
        assert rates[1] == {"amount": 10, "days": 60}

    def test_get_days_for_amount(self):
        assert get_days_for_amount(5) == 30
        assert get_days_for_amount(10) == 60
        assert get_days_for_amount(999) == 0

    def test_reset_restores_defaults(self):
        _payment_rates = get_payment_rates()
        _payment_rates.clear()
        reset_db()
        assert len(get_payment_rates()) == 2


class TestSmsRecords:
    def test_add_and_get_sms(self):
        reset_db()
        sid = add_sms_record("C001", "0888888001", "Test message")
        assert sid.startswith("S")
        records = get_sms_records("C001")
        assert len(records) == 1
        assert records[0]["to"] == "0888888001"
        assert records[0]["message"] == "Test message"

    def test_get_all_sms(self):
        reset_db()
        add_sms_record("C001", "0888888001", "msg1")
        add_sms_record("C002", "0888888002", "msg2")
        all_records = get_sms_records()
        assert len(all_records) == 2


class TestCustomerStatus:
    def test_new_customer_defaults_locked(self):
        reset_db()
        cid = add_customer("Test", "0880000001", "SN-KH-001")
        c = get_customer(cid)
        assert c["status"] == "locked"

    def test_update_status(self):
        reset_db()
        cid = add_customer("Test", "0880000001", "SN-KH-001")
        assert update_customer_status(cid, "active")
        assert get_customer(cid)["status"] == "active"
        assert update_customer_status(cid, "permanent")
        assert get_customer(cid)["status"] == "permanent"

    def test_lock_sets_locked_at(self):
        reset_db()
        cid = add_customer("Test", "0880000001", "SN-KH-001")
        update_customer_status(cid, "locked")
        c = get_customer(cid)
        assert c["locked_at"] is not None

    def test_update_nonexistent_customer(self):
        assert not update_customer_status("NOEXIST", "active")
```

- [ ] **Step 4: 运行 db 测试**

```bash
pytest tests/test_db.py -v
```
预期：ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/db.py tests/test_db.py
git commit -m "feat: db 扩展 — 客户状态管理、支付汇率、短信记录存储"
```

---

### Task 4: 支付汇率配置 API (app/routers/config.py)

**Files:**
- Create: `app/routers/config.py`
- Create: `tests/test_config_api.py`

- [ ] **Step 1: 先写测试 `tests/test_config_api.py`**

```python
from fastapi.testclient import TestClient
from app.main import app
from app.db import reset_db

client = TestClient(app)


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


def test_get_payment_rates_requires_auth():
    resp = client.get("/api/config/payment-rates")
    assert resp.status_code == 401


def test_get_payment_rates_returns_defaults():
    reset_db()
    cookie = _login()
    resp = client.get("/api/config/payment-rates", cookies={"session": cookie})
    assert resp.status_code == 200
    rates = resp.json()
    assert len(rates) == 2
    assert {"amount": 5, "days": 30} in rates
    assert {"amount": 10, "days": 60} in rates
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_config_api.py -v
```
预期：FAIL（路由不存在）

- [ ] **Step 3: 创建 `app/routers/config.py`**

```python
from fastapi import APIRouter, Request, HTTPException

from app.db import get_payment_rates

router = APIRouter(prefix="/api/config")


def _check_auth(request: Request):
    if request.cookies.get("session") != "authenticated":
        raise HTTPException(status_code=401, detail="未认证")


@router.get("/payment-rates")
async def list_payment_rates(request: Request):
    _check_auth(request)
    return get_payment_rates()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_config_api.py -v
```
预期：ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/routers/config.py tests/test_config_api.py
git commit -m "feat: 新增支付汇率配置 API"
```

---

### Task 5: 客户 API 扩展 (app/routers/customers.py)

**Files:**
- Modify: `app/routers/customers.py`
- Modify: `tests/test_customers_api.py`

- [ ] **Step 1: 写测试 — simulate-payment, lock, permanent-unlock**

在 `tests/test_customers_api.py` 末尾追加：

```python
class TestSimulatePayment:
    def test_simulate_payment_requires_auth(self):
        resp = client.post("/api/customers/C001/simulate-payment", json={"amount": 5})
        assert resp.status_code == 401

    def test_simulate_payment_returns_token_and_sms(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) == 15
        assert data["days"] == 30
        assert "sms" in data
        assert data["sms"]["to"] == "0888888001"
        assert "PAYGO" in data["sms"]["message"]

    def test_simulate_payment_10_dollars_gives_60_days(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 10},
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["days"] == 60

    def test_simulate_payment_nonexistent_customer(self):
        cookie = _login()
        resp = client.post(
            "/api/customers/NOEXIST/simulate-payment",
            json={"amount": 5},
            cookies={"session": cookie},
        )
        assert resp.status_code == 404

    def test_simulate_payment_unknown_amount(self):
        from app.db import reset_db, add_customer
        reset_db()
        cid = add_customer("Test", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/simulate-payment",
            json={"amount": 999},
            cookies={"session": cookie},
        )
        assert resp.status_code == 400


class TestLockDevice:
    def test_lock_device(self):
        from app.db import reset_db, add_customer, get_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/lock",
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        customer = get_customer(cid)
        assert customer["status"] == "locked"

    def test_lock_requires_auth(self):
        resp = client.post("/api/customers/C001/lock")
        assert resp.status_code == 401


class TestPermanentUnlock:
    def test_permanent_unlock_returns_disable_payg_token(self):
        from app.db import reset_db, add_customer, get_customer
        reset_db()
        cid = add_customer("Test User", "0888888001", "SN-KH-001")
        cookie = _login()
        resp = client.post(
            f"/api/customers/{cid}/permanent-unlock",
            cookies={"session": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["token"]) == 15
        # 校验 type=99
        assert data["token"][9:11] == "99"
        assert data["days"] == -1
        assert "sms" in data
        assert "贷款已结清" in data["sms"]["message"]

        customer = get_customer(cid)
        assert customer["status"] == "permanent"

    def test_permanent_unlock_requires_auth(self):
        resp = client.post("/api/customers/C001/permanent-unlock")
        assert resp.status_code == 401
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_customers_api.py::TestSimulatePayment tests/test_customers_api.py::TestLockDevice tests/test_customers_api.py::TestPermanentUnlock -v
```
预期：FAIL（端点不存在）

- [ ] **Step 3: 扩展 `app/routers/customers.py` 新增 3 个端点**

在文件末尾追加：

```python
class SimulatePayment(BaseModel):
    amount: float


class SimulatePaymentResponse(BaseModel):
    token: str
    customer_id: str
    days: int
    sms: dict


@router.post("/customers/{customer_id}/simulate-payment")
async def simulate_payment(request: Request, customer_id: str, body: SimulatePayment):
    """模拟支付：根据金额查汇率 → 生成15位Token → 模拟短信发送"""
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    days = get_days_for_amount(body.amount)
    if days == 0:
        raise HTTPException(status_code=400, detail=f"不支持的金额: ${body.amount}")

    token_str = generate_token(customer["device_id"], days)
    add_token(customer_id, token_str, days)

    # 生成模拟短信
    token_formatted = f"{token_str[:5]} {token_str[5:9]} {token_str[9:11]} {token_str[11:15]}"
    message = (
        f"[PAYGO Solar] 尊敬的用户，您已成功支付${body.amount:.2f}。"
        f"您的太阳能激活码为：{token_formatted}。"
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
    """锁定设备"""
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    update_customer_status(customer_id, "locked")
    return {"status": "ok"}


@router.post("/customers/{customer_id}/permanent-unlock")
async def permanent_unlock(request: Request, customer_id: str):
    """永久解锁：生成 DISABLE_PAYG Token (type=99)"""
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    token_str = generate_token(customer["device_id"], -1)  # -1 → DISABLE_PAYG
    add_token(customer_id, token_str, -1)
    update_customer_status(customer_id, "permanent")

    token_formatted = f"{token_str[:5]} {token_str[5:9]} {token_str[9:11]} {token_str[11:15]}"
    message = (
        f"[PAYGO Solar] 恭喜！您的贷款已全部结清。"
        f"设备永久解锁码：{token_formatted}。"
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
```

同时更新文件顶部的 import：

```python
from app.db import (
    get_customers, get_customer, add_customer, delete_customer,
    get_tokens, add_token, update_customer_status, get_days_for_amount, add_sms_record,
)
from app.token_engine import generate_token
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_customers_api.py -v
```
预期：ALL PASS

- [ ] **Step 5: Commit**

```bash
git add app/routers/customers.py tests/test_customers_api.py
git commit -m "feat: 新增模拟支付、锁定设备、永久解锁 API"
```

---

### Task 6: 注册 config 路由 (app/main.py)

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: 注册 config 路由**

在 `app/main.py` 中添加：

```python
from app.routers.config import router as config_router

# 在 app.include_router(customers_router) 之后添加：
app.include_router(config_router)
```

- [ ] **Step 2: 验证路由已注册**

```bash
pytest tests/test_config_api.py -v
```
预期：ALL PASS

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: 注册 config 路由"
```

---

### Task 7: 前端 Dashboard 升级 (templates/dashboard.html)

**Files:**
- Modify: `templates/dashboard.html`
- Modify: `static/style.css`（如需要新增样式）

- [ ] **Step 1: 启动开发服务器预览当前 UI**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 2
echo "http://localhost:8000/dashboard"
```
打开浏览器确认当前 UI 状态，然后 kill 服务器。

- [ ] **Step 2: 重构 dashboard.html**

完整替换 `templates/dashboard.html`：

```html
{% extends "base.html" %}
{% block content %}
<div class="main-layout">
  <!-- 左侧客户列表 -->
  <aside class="customer-list" id="customerList">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
      <h3 style="margin:0;">📋 客户列表</h3>
      <button class="btn btn-primary" style="padding:6px 14px;font-size:12px;"
              onclick="showAddCustomerModal()">+ 新增</button>
    </div>
    <div id="customerItems"></div>
  </aside>

  <!-- 右侧详情面板 -->
  <main class="detail-panel" id="detailPanel">
    <div class="empty">
      <p style="font-size:48px;margin-bottom:12px;">👈</p>
      <p>选择左侧客户查看详情</p>
    </div>
  </main>
</div>

<!-- 新增客户弹窗 -->
<div class="modal-overlay" id="addCustomerModal">
  <div class="modal-card">
    <h3>新增客户</h3>
    <div class="form-group">
      <label>姓名</label>
      <input type="text" id="newName" placeholder="客户姓名">
    </div>
    <div class="form-group">
      <label>电话</label>
      <input type="text" id="newPhone" placeholder="联系电话">
    </div>
    <div class="form-group">
      <label>设备编号</label>
      <input type="text" id="newDevice" placeholder="如 SN-KH-001">
    </div>
    <div class="modal-actions">
      <button class="btn" style="background:#f1f5f9;color:#475569;"
              onclick="closeModal('addCustomerModal')">取消</button>
      <button class="btn btn-primary" onclick="createCustomer()">确认添加</button>
    </div>
  </div>
</div>

<!-- 模拟支付弹窗 -->
<div class="modal-overlay" id="simulatePaymentModal">
  <div class="modal-card">
    <h3>💰 模拟支付</h3>
    <p style="color:#64748b;font-size:13px;margin-bottom:16px;" id="simulateCustomerName"></p>
    <div class="form-group">
      <label>支付金额</label>
      <select id="paymentAmount" style="width:100%;padding:10px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;">
        <option value="5">$5.00 — 30天</option>
        <option value="10">$10.00 — 60天</option>
      </select>
    </div>
    <div class="modal-actions">
      <button class="btn" style="background:#f1f5f9;color:#475569;"
              onclick="closeModal('simulatePaymentModal')">取消</button>
      <button class="btn btn-primary" onclick="simulatePayment()">确认支付</button>
    </div>
  </div>
</div>

<!-- Token + SMS 结果弹窗 -->
<div class="modal-overlay" id="tokenResultModal">
  <div class="modal-card" style="max-width:420px;">
    <h3 id="tokenResultTitle">🔑 激活码已生成</h3>
    <div class="token-display" id="tokenCode"></div>
    <!-- 短信预览 -->
    <div class="sms-preview" style="margin-top:16px;padding:12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;">
      <div style="font-size:11px;color:#64748b;margin-bottom:4px;">📱 模拟短信发送</div>
      <div style="font-size:12px;color:#475569;margin-bottom:4px;">收件人: <strong id="smsTo"></strong></div>
      <div style="font-size:12px;color:#1e293b;padding:8px;background:#fff;border-radius:6px;line-height:1.5;" id="smsBody"></div>
    </div>
    <div class="modal-actions" style="margin-top:16px;">
      <button class="btn btn-primary" onclick="closeModal('tokenResultModal');selectCustomer(selectedCustomerId);">完成</button>
    </div>
  </div>
</div>

<!-- 确认弹窗（锁定/永久解锁复用） -->
<div class="modal-overlay" id="confirmModal">
  <div class="modal-card">
    <h3 id="confirmTitle">确认操作</h3>
    <p style="color:#64748b;font-size:14px;margin-bottom:20px;" id="confirmMessage"></p>
    <div class="modal-actions">
      <button class="btn" style="background:#f1f5f9;color:#475569;"
              onclick="closeModal('confirmModal')">取消</button>
      <button class="btn btn-danger" id="confirmBtn" onclick="">确认</button>
    </div>
  </div>
</div>

<!-- 删除确认弹窗 -->
<div class="modal-overlay" id="deleteConfirmModal">
  <div class="modal-card">
    <h3>确认删除</h3>
    <p style="color:#64748b;font-size:14px;margin-bottom:20px;">
      确定要删除客户 <strong id="deleteCustomerName"></strong> 吗？此操作不可撤销。
    </p>
    <div class="modal-actions">
      <button class="btn" style="background:#f1f5f9;color:#475569;"
              onclick="closeModal('deleteConfirmModal')">取消</button>
      <button class="btn btn-danger" onclick="confirmDelete()">确认删除</button>
    </div>
  </div>
</div>

<script>
let selectedCustomerId = null;
let deleteTargetId = null;

const STATUS_MAP = {
  active: '🟢 活跃',
  locked: '🔴 已锁定',
  permanent: '⭐ 永久解锁',
};

async function loadCustomers() {
  const resp = await fetch('/api/customers');
  const customers = await resp.json();
  const container = document.getElementById('customerItems');
  if (customers.length === 0) {
    container.innerHTML = '<p style="color:#94a3b8;font-size:13px;text-align:center;padding:20px;">暂无客户</p>';
    return;
  }
  container.innerHTML = customers.map(c => `
    <div class="customer-item ${c.id === selectedCustomerId ? 'active' : ''}"
         onclick="selectCustomer('${c.id}')">
      <div class="name">👤 ${c.name}</div>
      <div class="meta">📱 ${c.phone} · 🔌 ${c.device_id}</div>
    </div>
  `).join('');
}

async function selectCustomer(id) {
  selectedCustomerId = id;
  await loadCustomers();
  const resp = await fetch(`/api/customers/${id}`);
  const c = await resp.json();

  // 加载该客户的短信记录
  const smsResp = await fetch('/api/sms?customer_id=' + encodeURIComponent(id));
  const smsRecords = await smsResp.json();

  const statusLabel = STATUS_MAP[c.status] || c.status;

  document.getElementById('detailPanel').innerHTML = `
    <div class="detail-card">
      <h2>👤 ${c.name}</h2>
      <div class="detail-row"><span class="label">电话</span><span class="value">${c.phone}</span></div>
      <div class="detail-row"><span class="label">设备</span><span class="value">${c.device_id}</span></div>
      <div class="detail-row"><span class="label">剩余天数</span><span class="value">${c.remaining_days} 天</span></div>
      <div class="detail-row"><span class="label">状态</span><span class="value">${statusLabel}</span></div>
      <div class="detail-row"><span class="label">创建日期</span><span class="value">${c.created_at}</span></div>

      <!-- 模拟支付区域 -->
      <div class="payment-section" style="margin-top:20px;padding:16px;background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;">
        <h4 style="margin:0 0 4px 0;">💰 模拟支付</h4>
        <p style="color:#64748b;font-size:12px;margin:0 0 12px 0;">模拟客户通过 Bakong 完成还款</p>
        <button class="btn btn-primary" onclick="showSimulatePaymentModal('${c.id}', '${c.name.replace(/'/g, "\\'")}')">💳 模拟支付</button>
      </div>

      <!-- 操作按钮组 -->
      <div class="actions" style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn btn-danger" onclick="showLockConfirm('${c.id}', '${c.name.replace(/'/g, "\\'")}')">🔒 锁定设备</button>
        <button class="btn" style="background:#f59e0b;color:#fff;" onclick="showPermanentUnlockConfirm('${c.id}', '${c.name.replace(/'/g, "\\'")}')">⭐ 永久解锁</button>
        <button class="btn btn-danger" onclick="showDeleteModal('${c.id}', '${c.name.replace(/'/g, "\\'")}')">删除客户</button>
      </div>

      <!-- 短信记录 -->
      <div style="margin-top:20px;">
        <h4 style="margin:0 0 8px 0;">📱 短信记录</h4>
        ${smsRecords.length === 0
          ? '<p style="color:#94a3b8;font-size:12px;">暂无记录</p>'
          : smsRecords.map(r => `
            <div style="padding:8px;margin-bottom:6px;background:#fff;border:1px solid #e2e8f0;border-radius:6px;">
              <div style="font-size:11px;color:#64748b;">收件人: ${r.to} · ${r.sent_at}</div>
              <div style="font-size:12px;color:#334155;margin-top:4px;">${r.message}</div>
            </div>
          `).join('')
        }
      </div>
    </div>
  `;
}

// ---- 新增客户 ----
function showAddCustomerModal() {
  document.getElementById('newName').value = '';
  document.getElementById('newPhone').value = '';
  document.getElementById('newDevice').value = '';
  document.getElementById('addCustomerModal').classList.add('show');
}

async function createCustomer() {
  const name = document.getElementById('newName').value.trim();
  const phone = document.getElementById('newPhone').value.trim();
  const device_id = document.getElementById('newDevice').value.trim();
  if (!name || !phone || !device_id) { alert('请填写所有字段'); return; }
  await fetch('/api/customers', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, phone, device_id})
  });
  closeModal('addCustomerModal');
  await loadCustomers();
}

// ---- 模拟支付 ----
let simulateCustomerId = null;
function showSimulatePaymentModal(cid, name) {
  simulateCustomerId = cid;
  document.getElementById('simulateCustomerName').textContent = '为客户 ' + name + ' 模拟一笔支付';
  document.getElementById('simulatePaymentModal').classList.add('show');
}

async function simulatePayment() {
  const amount = parseFloat(document.getElementById('paymentAmount').value);
  const resp = await fetch(`/api/customers/${simulateCustomerId}/simulate-payment`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({amount})
  });
  const data = await resp.json();
  closeModal('simulatePaymentModal');

  // 展示结果 + 短信
  const token = data.token;
  document.getElementById('tokenResultTitle').textContent = data.days === -1 ? '⭐ 永久解锁码已生成' : '🔑 激活码已生成';
  document.getElementById('tokenCode').textContent = token.slice(0,5) + ' ' + token.slice(5,9) + ' ' + token.slice(9,11) + ' ' + token.slice(11,15);
  document.getElementById('smsTo').textContent = data.sms.to;
  document.getElementById('smsBody').textContent = data.sms.message;
  document.getElementById('tokenResultModal').classList.add('show');
}

// ---- 锁定设备 ----
function showLockConfirm(cid, name) {
  document.getElementById('confirmTitle').textContent = '🔒 锁定设备';
  document.getElementById('confirmMessage').textContent = '确定要锁定客户 ' + name + ' 的设备吗？锁定后设备将停止供电。';
  document.getElementById('confirmBtn').onclick = async function() {
    await fetch(`/api/customers/${cid}/lock`, {method: 'POST'});
    closeModal('confirmModal');
    selectCustomer(cid);
  };
  document.getElementById('confirmModal').classList.add('show');
}

// ---- 永久解锁 ----
function showPermanentUnlockConfirm(cid, name) {
  document.getElementById('confirmTitle').textContent = '⭐ 永久解锁';
  document.getElementById('confirmMessage').textContent = '确定要为 ' + name + ' 生成永久解锁 Token 吗？此操作不可撤销。';
  document.getElementById('confirmBtn').onclick = async function() {
    const resp = await fetch(`/api/customers/${cid}/permanent-unlock`, {method: 'POST'});
    const data = await resp.json();
    closeModal('confirmModal');

    const token = data.token;
    document.getElementById('tokenResultTitle').textContent = '⭐ 永久解锁码已生成';
    document.getElementById('tokenCode').textContent = token.slice(0,5) + ' ' + token.slice(5,9) + ' ' + token.slice(9,11) + ' ' + token.slice(11,15);
    document.getElementById('smsTo').textContent = data.sms.to;
    document.getElementById('smsBody').textContent = data.sms.message;
    document.getElementById('tokenResultModal').classList.add('show');
  };
  document.getElementById('confirmModal').classList.add('show');
}

// ---- 删除客户 ----
function showDeleteModal(cid, name) {
  deleteTargetId = cid;
  document.getElementById('deleteCustomerName').textContent = name;
  document.getElementById('deleteConfirmModal').classList.add('show');
}

async function confirmDelete() {
  await fetch(`/api/customers/${deleteTargetId}`, {method: 'DELETE'});
  closeModal('deleteConfirmModal');
  selectedCustomerId = null;
  document.getElementById('detailPanel').innerHTML = `
    <div class="empty"><p style="font-size:48px;">👈</p><p>选择左侧客户查看详情</p></div>
  `;
  await loadCustomers();
}

// ---- 通用 ----
function closeModal(id) {
  document.getElementById(id).classList.remove('show');
}

loadCustomers();
</script>
{% endblock %}
```

- [ ] **Step 3: 添加 SMS 查询 API**

在 `app/routers/customers.py` 中添加 SMS 查询端点：

```python
@router.get("/sms")
async def list_sms(request: Request, customer_id: str = None):
    """列出短信记录，可按客户筛选"""
    _check_auth(request)
    return get_sms_records(customer_id)
```

同时确保文件顶部已 import `get_sms_records`。

- [ ] **Step 4: 启动服务器验证 UI**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
预期：dashboard 正常加载，详情面板显示模拟支付区、操作按钮组、短信记录。

- [ ] **Step 5: 运行全部现有测试确认无回归**

```bash
pytest tests/ -v
```
预期：ALL PASS（除 upgrade 测试待 Task 10 编写）

- [ ] **Step 6: Commit**

```bash
git add templates/dashboard.html app/routers/customers.py
git commit -m "feat: 前端升级 — 模拟支付、SMS预览、锁定/永久解锁按钮"
```

---

### Task 8: 控制器状态管理器升级 (controller/state_manager.py)

**Files:**
- Modify: `controller/state_manager.py`
- Modify: `tests/test_state_manager.py`

- [ ] **Step 1: 写测试**

在 `tests/test_state_manager.py` 末尾追加：

```python
class TestPermanentUnlock:
    def test_apply_permanent_unlock(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        sm.apply_permanent_unlock(state, device_id_hash=12345)
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1
        assert state["device_id_hash"] == 12345

    def test_tick_does_not_reduce_permanent(self, temp_state_dir):
        yesterday = (date.today() - timedelta(days=100)).isoformat()
        state = {
            "device_id_hash": 12345,
            "remaining_days": -1,
            "last_update": yesterday,
            "status": "permanent",
        }
        sm.tick(state)
        assert state["remaining_days"] == -1
        assert state["status"] == "permanent"

    def test_permanent_stays_permanent_forever(self, temp_state_dir):
        state = {
            "device_id_hash": 12345,
            "remaining_days": -1,
            "last_update": "2020-01-01",
            "status": "permanent",
        }
        sm.tick(state)
        assert state["status"] == "permanent"


class TestAntiReplay:
    def __init_used_tokens(self, temp_state_dir, monkeypatch):
        """初始化 used_tokens 存储"""
        import json
        used_dir = os.path.join(temp_state_dir, ".paygo")
        used_file = os.path.join(used_dir, "used_tokens.json")
        monkeypatch.setattr(sm, "USED_TOKENS_FILE", used_file)

    def test_first_use_not_expired(self, temp_state_dir, monkeypatch):
        import json
        used_dir = os.path.join(temp_state_dir, ".paygo")
        used_file = os.path.join(used_dir, "used_tokens.json")
        monkeypatch.setattr(sm, "USED_TOKENS_FILE", used_file)
        assert not sm.is_token_used("0123400300101265")

    def test_replay_is_detected(self, temp_state_dir, monkeypatch):
        import json
        used_dir = os.path.join(temp_state_dir, ".paygo")
        used_file = os.path.join(used_dir, "used_tokens.json")
        monkeypatch.setattr(sm, "USED_TOKENS_FILE", used_file)
        token = "0123400300101265"
        sm.mark_token_used(token)
        assert sm.is_token_used(token)

    def test_mark_token_persists(self, temp_state_dir, monkeypatch):
        import json
        used_dir = os.path.join(temp_state_dir, ".paygo")
        used_file = os.path.join(used_dir, "used_tokens.json")
        monkeypatch.setattr(sm, "USED_TOKENS_FILE", used_file)
        token = "9876500600105432"
        sm.mark_token_used(token)
        # Reload — should still be used
        assert sm.is_token_used(token)


class TestApplyTokenWithType:
    def test_type01_activates(self, temp_state_dir):
        state = dict(sm.DEFAULT_STATE)
        sm.apply_token(state, device_id_hash=12345, days=30, token_type=1)
        assert state["status"] == "active"
        assert state["remaining_days"] == 30

    def test_type99_permanent_unlock(self, temp_state_dir):
        state = {"device_id_hash": 12345, "remaining_days": 5,
                 "last_update": "2026-05-18", "status": "active"}
        sm.apply_token(state, device_id_hash=12345, days=0, token_type=99)
        assert state["status"] == "permanent"
        assert state["remaining_days"] == -1

    def test_type01_on_locked_reactivates(self, temp_state_dir):
        state = {"device_id_hash": 12345, "remaining_days": 0,
                 "last_update": "2026-05-10", "status": "locked"}
        sm.apply_token(state, device_id_hash=12345, days=10, token_type=1)
        assert state["status"] == "active"
        assert state["remaining_days"] == 10
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_state_manager.py::TestPermanentUnlock tests/test_state_manager.py::TestAntiReplay tests/test_state_manager.py::TestApplyTokenWithType -v
```
预期：FAIL（函数未定义）

- [ ] **Step 3: 更新 `controller/state_manager.py`**

```python
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
    os.makedirs(STATE_DIR, exist_ok=True)
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
```

- [ ] **Step 4: 更新旧 `apply_token` 测试调用签名**

旧测试 `TestApplyToken` 中调用 `sm.apply_token(state, device_id_hash=703, days=30)` 的地方需要加上 `token_type=1` 或保留默认参数（已兼容）。

运行全部 state_manager 测试：

```bash
pytest tests/test_state_manager.py -v
```
预期：ALL PASS

- [ ] **Step 5: Commit**

```bash
git add controller/state_manager.py tests/test_state_manager.py
git commit -m "feat: state_manager — permanent 状态、防重放、fast_forward 调试命令"
```

---

### Task 9: 控制器 UI 升级 (controller/controller.py)

**Files:**
- Modify: `controller/controller.py`

- [ ] **Step 1: 重写 `controller/controller.py`**

```python
#!/usr/bin/env python3
"""PAYGO 太阳能控制器 — 终端模拟脚本。

运行在安卓 Termux 环境中，模拟 PAYGO 控制器的核心行为：
Token 本地解码验证（15位）、设备状态管理、天数递减。
"""

import os

from token_codec import decode
from state_manager import (
    load, save, apply_token, tick, reset,
    fast_forward, is_token_used, mark_token_used,
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
    """计算终端显示宽度：ASCII 占 1，其余占 2。"""
    n = 0
    for c in s:
        n += 1 if ord(c) <= 127 else 2
    return n


def pad(s: str, width: int) -> str:
    """右填充空格至指定显示宽度。"""
    return s + " " * (width - wlen(s))


def row(label: str, value: str) -> str:
    """生成对齐行：标签对齐 → 冒号 → 值 → 右边框。"""
    label_pad = label + " " * (LABEL_W - wlen(label))
    return "║" + pad(f" {label_pad}: {value}", INNER) + "║"


def clear_screen():
    os.system("clear")


def render(state):
    clear_screen()
    tick(state)

    device_display = f"#{state['device_id_hash']:05d}" if state["device_id_hash"] else "--"
    status = state["status"]
    days = state["remaining_days"]

    print("╔══════════════════════════════╗")
    print("║" + pad("PAYGO 太阳能控制器", INNER) + "║")
    print("╠══════════════════════════════╣")
    print(row("设备", device_display))
    print(row("状态", STATUS_LABELS[status]))
    if days == -1:
        print(row("剩余天数", "∞ 无限"))
    else:
        print(row("剩余天数", f"{days} 天"))
    print(row("继电器", RELAY_LABELS[status]))
    print("╚══════════════════════════════╝")
    print()


def main():
    state = load()
    while True:
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
            token = input("Token: ").strip()
            # 15位校验
            if len(token) != 15 or not token.isdigit():
                print("✗ Token无效，按回车键继续...")
                input()
                continue

            result = decode(token)
            if result is None:
                print("✗ Token无效，按回车键继续...")
                input()
                continue

            # 防重放检查
            if is_token_used(token):
                print("Token已过期，按回车键继续...")
                input()
                continue

            # 应用 Token
            apply_token(state, result["device_id_hash"], result["days"], result["type"])
            mark_token_used(token)
            save(state)

            if result["type"] == 99:
                print("✓✓✓ 贷款已结清！设备永久解锁！")
            else:
                print(f"✓ Token验证成功！增加{result['days']}天。")
            print(f"当前剩余{state['remaining_days']}天")
            print("按回车键继续...")
            input()

    print("控制器已退出。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行控制器集成测试确认无回归**

```bash
pytest tests/test_controller_integration.py -v
```
预期：ALL PASS（如果旧测试使用 8 位 Token，需更新）

- [ ] **Step 3: Commit**

```bash
git add controller/controller.py
git commit -m "feat: 控制器 UI 升级 — 15位Token、[D]快进、新提示文案、permanent状态"
```

---

### Task 10: 集成测试 — 五个场景 (tests/test_upgrade.py)

**Files:**
- Create: `tests/test_upgrade.py`

- [ ] **Step 1: 编写五场景集成测试**

```python
"""
升级集成测试：覆盖 5 个 MFI 演示场景。
测试服务端 API 和控制器终端行为。
"""

import hashlib

from fastapi.testclient import TestClient

from app.main import app
from app.db import reset_db, add_customer, get_customer
from controller.token_codec import decode
from controller.state_manager import (
    load as ctrl_load,
    save as ctrl_save,
    apply_token,
    mark_token_used,
    is_token_used,
    DEFAULT_STATE,
    STATE_FILE,
    USED_TOKENS_FILE,
)

client = TestClient(app)


def _login():
    resp = client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


# ========== 场景一：首次支付解锁 ==========

class TestScene1FirstPayment:
    def test_scene1_full_flow(self, tmp_path, monkeypatch):
        """创建locked客户 → 模拟支付$5 → 15位Token → 控制器decode → apply激活"""
        # 后台：创建客户 SN-KH-001
        reset_db()
        cid = add_customer("Sok Heng", "0888888001", "SN-KH-001")
        c = get_customer(cid)
        assert c["status"] == "locked"

        # 后台：模拟支付 $5
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

        # 控制器：decode
        result = decode(token)
        assert result is not None
        assert result["type"] == 1
        assert result["days"] == 30

        # 控制器：apply
        state = dict(DEFAULT_STATE)
        apply_token(state, result["device_id_hash"], result["days"], result["type"])
        assert state["status"] == "active"
        assert state["remaining_days"] == 30


# ========== 场景二：再次续费 ==========

class TestScene2Renewal:
    def test_scene2_days_stack(self, tmp_path, monkeypatch):
        """模拟支付$10 → apply → remaining_days=90（30+60）"""
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
        # 翻转最后一位
        bad = token[:14] + str((int(token[14]) + 1) % 10)
        assert decode(bad) is None


# ========== 场景四：逾期锁定 ==========

class TestScene4ExpiredLock:
    def test_old_token_replay_blocked(self, tmp_path, monkeypatch):
        """防重放：用过一次再输入 → 已过期"""
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

        # 再次输入同一 Token
        assert is_token_used(token)

    def test_fast_forward_to_lock(self, tmp_path, monkeypatch):
        """快进耗尽天数 → locked"""
        from controller.state_manager import fast_forward

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
    def test_permanent_unlock_full_flow(self, tmp_path, monkeypatch):
        """后台永久解锁 → type=99 Token → 控制器永久解锁"""
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
        assert token[9:11] == "99"

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
```

- [ ] **Step 2: 运行五场景测试**

```bash
pytest tests/test_upgrade.py -v
```
预期：ALL PASS

- [ ] **Step 3: 运行全部测试确认无回归**

```bash
pytest tests/ -v
```
预期：ALL PASS

- [ ] **Step 4: 最终 Commit**

```bash
git add tests/test_upgrade.py
git commit -m "test: 添加五场景 MFI 演示集成测试"
```

---

## 最终验证

```bash
# 启动服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 运行全部测试
pytest tests/ -v
```

预期：所有测试通过，5 个演示场景全部覆盖。
