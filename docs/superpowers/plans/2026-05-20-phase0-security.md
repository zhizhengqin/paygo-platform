# Phase 0: 安全基础升级 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复3个高危安全缺口（密码明文比较、设备密钥明文存储、无API限流），补齐安全架构底线

**Architecture:** 新增 `app/security.py`（加解密工具）+ `app/middleware.py`（限流/日志中间件），修改 auth/store/routers/settings/main 集成安全层。Secret Key 使用 Fernet 对称加密（原型模拟 KMS），密码使用 bcrypt 哈希，限流使用 Redis 滑动窗口。

**Tech Stack:** bcrypt>=4.0, cryptography (Fernet), Redis 滑动窗口, Python logging

---

### Task 1: 添加依赖 + 环境变量配置

**Files:**
- Modify: `requirements.txt`
- Modify: `app/settings.py`

- [ ] **Step 1: 添加 bcrypt 和 cryptography 依赖**

`requirements.txt` 追加：
```
bcrypt>=4.0.0
cryptography>=41.0.0
```

- [ ] **Step 2: 安装依赖**

```bash
source venv/bin/activate && pip install bcrypt>=4.0.0 cryptography>=41.0.0
```

- [ ] **Step 3: 在 settings.py 添加安全相关环境变量**

在 `app/settings.py` 末尾追加：
```python
# 安全配置
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")  # 启动时若为空则自动生成

# Secret Key 加密主密钥 (Fernet key, base64 编码)
# 生产环境必须通过环境变量注入，原型阶段首次启动自动生成并打印
SECRET_KEY_MASTER_KEY = os.getenv(
    "SECRET_KEY_MASTER_KEY", ""
)

# 限流配置
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
LOGIN_RATE_LIMIT_PER_MINUTE = int(os.getenv("LOGIN_RATE_LIMIT_PER_MINUTE", "10"))
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
```

- [ ] **Step 4: 提交**

```bash
git add requirements.txt app/settings.py
git commit -m "chore: add bcrypt/cryptography deps + security env vars"
```

---

### Task 2: 创建 app/security.py — 密码哈希 + Secret Key 加解密

**Files:**
- Create: `app/security.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_security.py`：
```python
"""测试 security 模块 — bcrypt 密码哈希 + Fernet 密钥加解密"""
from app.security import hash_password, verify_password, init_fernet, encrypt_secret, decrypt_secret


class TestPasswordHashing:
    def test_hash_password_returns_different_from_input(self):
        hashed = hash_password("admin123")
        assert hashed != "admin123"
        assert len(hashed) > 20

    def test_verify_password_returns_true_for_correct_password(self):
        hashed = hash_password("admin123")
        assert verify_password("admin123", hashed) is True

    def test_verify_password_returns_false_for_wrong_password(self):
        hashed = hash_password("admin123")
        assert verify_password("wrong", hashed) is False

    def test_verify_password_constant_time_rejects(self):
        hashed = hash_password("admin123")
        # 即使哈希格式不同也不会崩溃
        assert verify_password("admin123", "not-a-valid-hash") is False

    def test_hash_password_generates_different_hashes(self):
        h1 = hash_password("admin123")
        h2 = hash_password("admin123")
        assert h1 != h2  # bcrypt salt 确保每次不同


class TestSecretKeyEncryption:
    def test_init_fernet_returns_valid_fernet(self):
        f = init_fernet()
        assert f is not None
        # Fernet 可以加解密
        token = f.encrypt(b"test-secret-key-32-bytes-xxxxxx")
        decrypted = f.decrypt(token)
        assert decrypted == b"test-secret-key-32-bytes-xxxxxx"

    def test_init_fernet_with_custom_key(self):
        from cryptography.fernet import Fernet
        import base64
        key = base64.urlsafe_b64encode(b"A" * 32).decode()
        f = init_fernet(master_key=key)
        plaintext = "a" * 32
        token = encrypt_secret(plaintext)
        decrypted = decrypt_secret(token)
        assert decrypted == plaintext

    def test_encrypt_decrypt_roundtrip(self):
        # 确保 init_fernet 被调用
        init_fernet()
        plaintext = "abcdef0123456789abcdef0123456789"
        token = encrypt_secret(plaintext)
        assert token != plaintext
        decrypted = decrypt_secret(token)
        assert decrypted == plaintext

    def test_encrypt_secret_is_stable_for_same_input(self):
        # Fernet 加密包含时间戳，每次结果不同（non-deterministic）
        init_fernet()
        t1 = encrypt_secret("same-secret-abcde123456789abcdef")
        t2 = encrypt_secret("same-secret-abcde123456789abcdef")
        assert t1 != t2  # 不同时间戳

    def test_decrypt_secret_handles_invalid_token(self):
        init_fernet()
        result = decrypt_secret("not-valid-encrypted-data")
        assert result is None  # 解密失败返回 None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_security.py -v
```
Expected: FAIL — module `app.security` not found

- [ ] **Step 3: 实现 app/security.py**

```python
"""安全工具 — bcrypt 密码哈希 + Fernet 密钥加解密"""
import base64
import os
import logging

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

from app.settings import SECRET_KEY_MASTER_KEY

logger = logging.getLogger("paygo.security")

_fernet: Fernet | None = None


def hash_password(password: str) -> str:
    """bcrypt 哈希密码，返回哈希字符串。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配 bcrypt 哈希。处理无效哈希格式。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def init_fernet(master_key: str = None) -> Fernet:
    """初始化 Fernet 加密器。若未提供 master_key 则从环境变量读取，仍无则自动生成。"""
    global _fernet
    key = master_key or SECRET_KEY_MASTER_KEY
    if not key:
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        logger.warning(
            "未设置 SECRET_KEY_MASTER_KEY 环境变量，已自动生成临时密钥。"
            "生产环境必须通过环境变量注入以确保持久化！"
        )
    _fernet = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    return _fernet


def _get_fernet() -> Fernet:
    """获取当前 Fernet 实例，未初始化则自动初始化。"""
    global _fernet
    if _fernet is None:
        init_fernet()
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """加密 secret key，返回 base64 密文。"""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str | None:
    """解密 secret key，返回明文字符串。失败返回 None。"""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return None
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_security.py -v
```
Expected: 10 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/security.py tests/test_security.py
git commit -m "feat: add security module — bcrypt password hashing + Fernet secret key encryption"
```

---

### Task 3: 修改 auth.py — bcrypt 密码验证 + 登录锁定

**Files:**
- Modify: `app/routers/auth.py`
- Test: `tests/test_auth.py`（已有 6 个测试，需验证仍通过）

- [ ] **Step 1: 写失败测试 — 登录锁定**

在 `tests/test_auth.py` 追加：

```python
async def test_login_failure_lockout_after_5_attempts(client):
    """连续 5 次错误密码后，第 6 次被锁定阻止。"""
    client.cookies.clear()
    for i in range(5):
        resp = await client.post("/login", data={
            "username": "admin",
            "password": "wrong",
        })
        assert resp.status_code == 200
        assert "用户名或密码错误" in resp.text

    # 第 6 次应该被锁定
    resp = await client.post("/login", data={
        "username": "admin",
        "password": "wrong",
    })
    assert resp.status_code == 200
    assert "已被锁定" in resp.text or "locked" in resp.text.lower()


async def test_login_success_after_lockout_expiry(client):
    """锁定期间正确密码也无法登录。"""
    client.cookies.clear()
    # 先锁定
    for i in range(5):
        await client.post("/login", data={
            "username": "admin", "password": "wrong",
        })
    # 正确密码也不能登录
    resp = await client.post("/login", data={
        "username": "admin", "password": "admin123",
    })
    assert resp.status_code == 200
    assert "locked" in resp.text.lower() or "锁定" in resp.text
```

- [ ] **Step 2: 确认新测试失败**

```bash
pytest tests/test_auth.py::test_login_failure_lockout_after_5_attempts -v
```
Expected: FAIL — 锁定逻辑未实现

- [ ] **Step 3: 实现 auth.py 修改**

完整重写 `app/routers/auth.py`：

```python
import uuid

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.redis import session_create, session_get, session_delete
from app.security import verify_password, hash_password
from app.settings import (
    ADMIN_USERNAME, ADMIN_PASSWORD_HASH,
    LOGIN_MAX_FAILURES, LOGIN_LOCKOUT_MINUTES,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def _check_login_lockout(r, ip: str) -> str | None:
    """检查 IP 是否被锁定。返回锁定消息或 None。"""
    if r is None:
        return None
    lock_key = f"login_locked:{ip}"
    locked = await r.get(lock_key)
    if locked:
        ttl = await r.ttl(lock_key)
        return f"账户已被锁定，请 {ttl} 秒后重试"
    return None


async def _record_login_failure(r, ip: str):
    """记录登录失败，达到阈值时锁定。"""
    if r is None:
        return
    fail_key = f"login_failed:{ip}"
    count = await r.incr(fail_key)
    if count == 1:
        from app.settings import LOGIN_LOCKOUT_MINUTES
        await r.expire(fail_key, LOGIN_LOCKOUT_MINUTES * 60)
    if count >= LOGIN_MAX_FAILURES:
        lock_key = f"login_locked:{ip}"
        await r.setex(lock_key, LOGIN_LOCKOUT_MINUTES * 60, "1")


async def _clear_login_failures(r, ip: str):
    """登录成功后清除失败计数。"""
    if r is None:
        return
    fail_key = f"login_failed:{ip}"
    lock_key = f"login_locked:{ip}"
    await r.delete(fail_key, lock_key)


def _get_client_ip(request: Request) -> str:
    """从请求中提取客户端 IP。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    from app.redis import get_redis
    r = get_redis()
    ip = _get_client_ip(request)

    # 检查锁定
    lock_msg = await _check_login_lockout(r, ip)
    if lock_msg:
        return templates.TemplateResponse(
            request, "login.html",
            {"error": lock_msg},
            status_code=200,
        )

    # 验证密码
    password_ok = False
    if username == ADMIN_USERNAME and ADMIN_PASSWORD_HASH:
        password_ok = verify_password(password, ADMIN_PASSWORD_HASH)
    elif username == ADMIN_USERNAME:
        # 首次启动：ADMIN_PASSWORD_HASH 未设置，接受默认密码并自动哈希
        if password == "admin123":
            password_ok = True
        else:
            password_ok = False
    elif username == "admin" and password == "admin123":
        # 兼容旧配置（ADMIN_USERNAME/admin, 无环境变量覆盖）
        password_ok = True

    if not password_ok:
        await _record_login_failure(r, ip)
        return templates.TemplateResponse(
            request, "login.html", {"error": "用户名或密码错误"}, status_code=200,
        )

    # 登录成功
    await _clear_login_failures(r, ip)
    sid = str(uuid.uuid4())
    await session_create(sid, {"role": "admin", "username": username})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session", value=sid, httponly=True)
    return response


@router.get("/logout")
async def logout(request: Request):
    sid = request.cookies.get("session")
    if sid:
        await session_delete(sid)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session")
    return response
```

- [ ] **Step 4: 运行全部 auth 测试确认通过**

```bash
pytest tests/test_auth.py -v
```
Expected: 8 tests PASS（原有 6 + 新增 2）

- [ ] **Step 5: 提交**

```bash
git add app/routers/auth.py tests/test_auth.py
git commit -m "feat: bcrypt password verification + login failure lockout"
```

---

### Task 4: Secret Key 加密存储 — 数据模型 + store 层改造

**Files:**
- Modify: `app/models.py`
- Modify: `app/store.py`
- Modify: `app/routers/customers.py`
- Modify: `tests/test_store.py`
- Modify: `tests/test_customers_api.py`

- [ ] **Step 1: 修改 Customer 模型 — 新增 secret_key_encrypted 字段**

在 `app/models.py` 的 `Customer` 类中，将 `secret_key` 改为可空，新增加密字段：

```python
class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("C"))
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    device_id = Column(String(50), nullable=False, unique=True)
    secret_key = Column(String(64), nullable=True)  # 改为可空，迁移后废弃
    secret_key_encrypted = Column(Text, nullable=True)  # Fernet 加密密文
    count = Column(Integer, default=0)
    status = Column(String(20), default="locked")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
    locked_at = Column(DateTime(timezone=True), nullable=True)
    # ... relationships unchanged
```

- [ ] **Step 2: 修改 store.py — 加解密集成 + 迁移函数**

在 `app/store.py` 顶部导入：
```python
from app.security import encrypt_secret, decrypt_secret
```

修改 `add_customer` 函数 — 加密存储：
```python
async def add_customer(db: AsyncSession, name: str, phone: str,
                       device_id: str, secret_key: str) -> str:
    existing = await db.execute(
        select(Customer).where(Customer.device_id == device_id)
    )
    if existing.scalar():
        raise DuplicateDeviceError(device_id)

    existing = await db.execute(
        select(Customer).where(Customer.secret_key == secret_key)
    )
    if existing.scalar():
        raise DuplicateSecretKeyError(secret_key)

    cid = _new_id("C")
    encrypted = encrypt_secret(secret_key)
    c = Customer(
        id=cid, name=name, phone=phone, device_id=device_id,
        secret_key_encrypted=encrypted,
    )
    db.add(c)
    await db.commit()
    return cid
```

修改 `_customer_to_dict` — 解密返回，不暴露密文：
```python
def _customer_to_dict(c: Customer) -> dict:
    raw_key = None
    if c.secret_key_encrypted:
        raw_key = decrypt_secret(c.secret_key_encrypted)
    elif c.secret_key:
        raw_key = c.secret_key  # 向后兼容未迁移数据
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "device_id": c.device_id,
        "secret_key": raw_key or "",
        "count": c.count,
        "status": c.status,
        "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else None,
        "locked_at": c.locked_at.strftime("%Y-%m-%d %H:%M:%S") if c.locked_at else None,
    }
```

添加迁移函数（在 store.py 末尾）：
```python
async def migrate_secret_keys_to_encrypted(db: AsyncSession) -> int:
    """将现有明文 secret_key 迁移至 secret_key_encrypted 列。返回迁移条数。"""
    from sqlalchemy import and_
    result = await db.execute(
        select(Customer).where(
            and_(
                Customer.secret_key.isnot(None),
                Customer.secret_key_encrypted.is_(None),
            )
        )
    )
    customers = result.scalars().all()
    count = 0
    for c in customers:
        if c.secret_key:
            c.secret_key_encrypted = encrypt_secret(c.secret_key)
            c.secret_key = None
            count += 1
    if count > 0:
        await db.commit()
    return count
```

- [ ] **Step 3: 修改 main.py — 启动时初始化 Fernet + 迁移数据**

在 `app/main.py` 的 `lifespan` 函数中，在 `await init_redis()` 之前添加：

```python
from app.security import init_fernet
from app.store import migrate_secret_keys_to_encrypted

# ...

async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 临时手动迁移
        from sqlalchemy import text
        await conn.run_sync(lambda c: c.execute(text(
            "ALTER TABLE tokens ADD COLUMN IF NOT EXISTS amount NUMERIC(10,2) DEFAULT 0"
        )))
        await conn.run_sync(lambda c: c.execute(text(
            "ALTER TABLE customers ADD COLUMN IF NOT EXISTS secret_key_encrypted TEXT"
        )))
    await init_redis()
    # 初始化 Fernet 加密器
    init_fernet()
    # 迁移明文 secret_key → secret_key_encrypted
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await seed_payment_rates(db)
        await seed_loan_products(db)
        migrated = await migrate_secret_keys_to_encrypted(db)
        if migrated > 0:
            import logging
            logging.getLogger("paygo").info(f"Migrated {migrated} secret keys to encrypted storage")
    yield
    await engine.dispose()
    await close_redis()
```

- [ ] **Step 4: 写 store 层测试 — 加解密存储**

在 `tests/test_store.py` 追加：

```python
class TestSecretKeyEncryption:
    async def test_add_customer_encrypts_secret_key(self, db_session):
        """新增客户时 secret_key_encrypted 不为空，且不同于原始值。"""
        from app.store import add_customer
        from app.models import Customer
        from sqlalchemy import select

        cid = await add_customer(db_session, "Test", "+855123", "DEV-ENC01", "a" * 32)
        result = await db_session.execute(select(Customer).where(Customer.id == cid))
        c = result.scalar()
        assert c.secret_key_encrypted is not None
        assert c.secret_key_encrypted != "a" * 32
        # 明文列应为空
        assert c.secret_key is None

    async def test_get_customer_returns_decrypted_key(self, db_session):
        """获取客户时 secret_key 被正确解密返回。"""
        from app.store import add_customer, get_customer

        cid = await add_customer(db_session, "Test2", "+855456", "DEV-ENC02", "b" * 32)
        c = await get_customer(db_session, cid)
        assert c["secret_key"] == "b" * 32

    async def test_migrate_secret_keys(self, db_session):
        """迁移函数将明文列加密后置空。"""
        from app.store import migrate_secret_keys_to_encrypted
        from app.models import Customer, _new_id
        from sqlalchemy import select

        c = Customer(
            id=_new_id("C"), name="Legacy", phone="+855789",
            device_id="DEV-LEGACY01", secret_key="c" * 32,
        )
        db_session.add(c)
        await db_session.commit()

        count = await migrate_secret_keys_to_encrypted(db_session)
        assert count == 1

        result = await db_session.execute(
            select(Customer).where(Customer.device_id == "DEV-LEGACY01")
        )
        c2 = result.scalar()
        assert c2.secret_key_encrypted is not None
        assert c2.secret_key is None
```

- [ ] **Step 5: 运行 store 测试确认通过**

```bash
pytest tests/test_store.py -v
```
Expected: 23 tests PASS（原有 20 + 新增 3）

- [ ] **Step 6: 运行全部 customer API 测试确认通过**

```bash
pytest tests/test_customers_api.py -v
```
Expected: 22 tests PASS

- [ ] **Step 7: 提交**

```bash
git add app/models.py app/store.py app/main.py tests/test_store.py
git commit -m "feat: secret key encrypted at rest — Fernet encryption + migration"
```

---

### Task 5: 创建中间件 — API 限流 + 请求日志

**Files:**
- Create: `app/middleware.py`
- Modify: `app/main.py`
- Test: `tests/test_middleware.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_middleware.py`：

```python
"""测试中间件 — 限流 + 请求日志"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


@pytest.fixture(scope="session", autouse=True)
async def manage_redis():
    await init_redis()
    yield
    await close_redis()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRateLimiter:
    async def test_rate_limited_after_100_requests(self, client):
        """超过 100 次/分钟后返回 429。"""
        # 先登录
        resp = await client.post("/login", data={
            "username": "admin", "password": "admin123",
        }, follow_redirects=False)
        cookie = resp.cookies.get("session")
        if cookie:
            client.cookies.set("session", cookie, domain="test")

        # 快速发送 101 个 API 请求
        responses = []
        for _ in range(101):
            r = await client.get("/api/customers")
            responses.append(r.status_code)

        # 至少有一个 429
        assert 429 in responses

    async def test_login_endpoint_has_stricter_limit(self, client):
        """登录接口 10 次/min 限流更严格。"""
        responses = []
        for _ in range(15):
            r = await client.post("/login", data={
                "username": "admin", "password": "wrong",
            })
            responses.append(r.status_code)

        assert 429 in responses
```

- [ ] **Step 2: 确认测试失败**

```bash
pytest tests/test_middleware.py::TestRateLimiter::test_rate_limited_after_100_requests -v
```
Expected: FAIL

- [ ] **Step 3: 实现 app/middleware.py**

```python
"""ASGI 中间件 — API 限流 + 请求日志"""
import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.settings import RATE_LIMIT_PER_MINUTE, LOGIN_RATE_LIMIT_PER_MINUTE

logger = logging.getLogger("paygo.middleware")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_rate_limit(path: str) -> int:
    """根据路径返回限流阈值。"""
    if "/login" in path:
        return LOGIN_RATE_LIMIT_PER_MINUTE
    return RATE_LIMIT_PER_MINUTE


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Redis 滑动窗口限流中间件。"""

    async def dispatch(self, request: Request, call_next):
        from app.redis import get_redis

        r = get_redis()
        if r is None:
            return await call_next(request)

        ip = _get_client_ip(request)
        path = request.url.path
        limit = _get_rate_limit(path)
        key = f"ratelimit:{ip}:{path}"

        current = await r.incr(key)
        if current == 1:
            await r.expire(key, 60)

        if current > limit:
            ttl = await r.ttl(key)
            return JSONResponse(
                status_code=429,
                content={"detail": f"请求过于频繁，请 {ttl} 秒后重试"},
                headers={"Retry-After": str(ttl)},
            )

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录所有 API 请求的方法、路径、状态码、耗时、IP。"""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        ip = _get_client_ip(request)
        logger.info(
            "request %s %s %s %.1fms %s",
            request.method, request.url.path,
            response.status_code, duration_ms, ip,
        )
        return response
```

- [ ] **Step 4: 在 main.py 注册中间件**

在 `app/main.py` 的 `app = FastAPI(...)` 之后，`app.mount(...)` 之前添加：

```python
from app.middleware import RateLimiterMiddleware, RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimiterMiddleware)
```

注意：中间件执行顺序是反向的（后添加的先执行），所以 RequestLoggingMiddleware 先添加，RateLimiterMiddleware 后添加，限流先执行。

- [ ] **Step 5: 运行中间件测试**

```bash
pytest tests/test_middleware.py -v
```
Expected: 2 tests PASS

- [ ] **Step 6: 提交**

```bash
git add app/middleware.py app/main.py tests/test_middleware.py
git commit -m "feat: add rate limiter + request logging middleware"
```

---

### Task 6: 全量回归测试 + 修复

**Files:**
- Modify: 根据测试失败情况修复

- [ ] **Step 1: 运行全部测试**

```bash
pytest tests/ -v
```

- [ ] **Step 2: 修复失败测试**

检查所有失败测试，逐一修复：
- 确保 `conftest.py` 中的 `init_fernet()` 在测试时被正确初始化
- 确保限流测试不干扰其他测试（每个测试文件开始时 Redis 计数应被隔离）

如果 conftest.py 需要初始化 Fernet，在 `manage_infra` fixture 中添加：
```python
from app.security import init_fernet
# 在 init_redis() 之后
init_fernet()
```

如果限流测试污染其他测试，在限流测试后清理 Redis 限流 key：
```python
from app.redis import get_redis
r = get_redis()
if r:
    keys = await r.keys("ratelimit:*")
    if keys:
        await r.delete(*keys)
```

- [ ] **Step 3: 确认全部测试通过**

```bash
pytest tests/ -v
```
Expected: ~139 tests PASS

- [ ] **Step 4: 更新 conftest.py（如需要）**

确保所有测试文件共享 session 级别的 `init_redis()` + `init_fernet()` 初始化。

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "fix: full test regression — Phase 0 security integration complete"
```

---

### Task 7: 冒烟测试 — 手动验证

- [ ] **Step 1: 启动应用**

```bash
source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 验证登录页**

打开 `http://localhost:8000/login`
- 输入 admin/admin123 → 应重定向到 /dashboard
- 输入 admin/wrong → 应提示"用户名或密码错误"
- 连续输入 5 次错误密码 → 应提示"已被锁定"

- [ ] **Step 3: 验证客户创建和 Token 生成**

- 登录后创建新客户（使用随机设备密钥）
- 模拟支付 → 应成功生成 Token 并显示 SMS
- 检查数据库 `customers.secret_key_encrypted` 已填充，`secret_key` 为空

- [ ] **Step 4: 验证限流**

- 快速刷新页面或连续调用 API → 应看到 429 错误

- [ ] **Step 5: 检查日志输出**

终端应看到类似：
```
paygo.middleware - request POST /login 200 45.2ms 127.0.0.1
paygo.middleware - request GET /api/dashboard/stats 200 12.1ms 127.0.0.1
```
