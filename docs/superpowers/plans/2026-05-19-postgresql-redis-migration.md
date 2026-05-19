# PostgreSQL + Redis 迁移实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 paygo-platform 从内存 dict 存储迁移至 PostgreSQL 15 + Redis 缓存，建立完整 SQLAlchemy 2.0 async ORM 模型

**Architecture:** 分层渐进式 — models.py (ORM 定义) → database.py (连接池) → redis.py (缓存) → store.py (async 数据访问) → 路由层 async handler。每层独立测试，上层依赖下层。

**Tech Stack:** SQLAlchemy 2.0 async, asyncpg, redis-py (async), FastAPI, pytest-asyncio

**数据库连接信息:**
- PostgreSQL: `postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform`
- 测试数据库: `postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform_test`
- Redis: `redis://localhost:6379/0`

---

### Task 1: 安装依赖 + 创建测试数据库

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 更新 requirements.txt**

```bash
cat > requirements.txt << 'DEPS'
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
jinja2>=3.1.0
python-multipart>=0.0.6
pytest>=7.0.0
pytest-asyncio>=0.24.0
httpx>=0.24.0
openpaygo>=0.6.3
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
redis>=5.0.0
DEPS
```

- [ ] **Step 2: 安装依赖**

Run: `source venv/bin/activate && pip install sqlalchemy[asyncio] asyncpg redis pytest-asyncio`
Expected: 所有包安装成功

- [ ] **Step 3: 创建测试数据库**

Run: `psql -U paygo_user -d postgres -c "CREATE DATABASE paygo_platform_test OWNER paygo_user;"`
Expected: CREATE DATABASE

- [ ] **Step 4: 验证连接**

Run:
```bash
source venv/bin/activate && python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
async def test():
    engine = create_async_engine('postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform')
    async with engine.connect() as conn:
        result = await conn.exec_driver_sql('SELECT 1')
        print('PostgreSQL OK:', result.scalar())
    await engine.dispose()
asyncio.run(test())
"
```
Expected: PostgreSQL OK: 1

- [ ] **Step 5: 验证 Redis 连接**

Run:
```bash
source venv/bin/activate && python -c "
import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
print('Redis OK:', r.ping())
"
```
Expected: Redis OK: True

- [ ] **Step 6: Commit**

```bash
git add requirements.txt
git commit -m "chore: 添加 SQLAlchemy async + asyncpg + redis + pytest-asyncio 依赖"
```

---

### Task 2: 创建 app/settings.py

**Files:**
- Create: `app/settings.py`

- [ ] **Step 1: 编写 settings.py**

```python
"""应用配置 — 数据库连接、Redis 连接、缓存 TTL 等。"""
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform",
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform_test",
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 连接池
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))

# 缓存 TTL（秒）
CACHE_TTL_API = int(os.getenv("CACHE_TTL_API", "60"))
SESSION_TTL = int(os.getenv("SESSION_TTL", "1800"))       # 30 min
ANTIREPLAY_TTL = int(os.getenv("ANTIREPLAY_TTL", "604800"))  # 7 days
```

- [ ] **Step 2: 验证模块可导入**

Run: `source venv/bin/activate && python -c "from app.settings import DATABASE_URL; print(DATABASE_URL)"`
Expected: 输出连接串

- [ ] **Step 3: Commit**

```bash
git add app/settings.py
git commit -m "feat: 添加 settings.py — DB/Redis 连接配置"
```

---

### Task 3: 创建 app/models.py — ORM 模型

**Files:**
- Create: `app/models.py`

- [ ] **Step 1: 编写测试 test_models.py**

Create file `tests/test_models.py`:

```python
"""ORM 模型单元测试 — 验证表结构、关系、约束。"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect

from app.models import Base, Customer, Token, SmsRecord, PaymentRate, DeviceState
from app.settings import TEST_DATABASE_URL


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


class TestCustomerModel:
    async def test_create_customer(self, session):
        c = Customer(
            id="C0001",
            name="Sok Heng",
            phone="0888888001",
            device_id="Solar-001",
            secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        )
        session.add(c)
        await session.commit()

        result = await session.get(Customer, "C0001")
        assert result.name == "Sok Heng"
        assert result.status == "locked"
        assert result.count == 0
        assert result.locked_at is None

    async def test_customer_unique_id(self, session):
        c1 = Customer(id="C0001", name="A", phone="1", device_id="D1", secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
        c2 = Customer(id="C0001", name="B", phone="2", device_id="D2", secret_key="b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7")
        session.add(c1)
        await session.commit()
        session.add(c2)
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()


class TestTokenModel:
    async def test_create_token(self, session):
        c = Customer(id="C0001", name="A", phone="1", device_id="D1", secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
        session.add(c)
        await session.commit()

        t = Token(
            id="T0001",
            customer_id="C0001",
            token="123456789",
            days=30,
            count=2,
        )
        session.add(t)
        await session.commit()

        result = await session.get(Token, "T0001")
        assert result.token == "123456789"
        assert result.customer_id == "C0001"
        assert result.days == 30

    async def test_token_customer_relationship(self, session):
        c = Customer(id="C0001", name="A", phone="1", device_id="D1", secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
        session.add(c)
        t1 = Token(id="T0001", customer_id="C0001", token="111111111", days=30, count=1)
        t2 = Token(id="T0002", customer_id="C0001", token="222222222", days=60, count=2)
        session.add_all([t1, t2])
        await session.commit()

        result = await session.get(Customer, "C0001")
        assert len(result.tokens) == 2


class TestPaymentRateModel:
    async def test_create_rate(self, session):
        r = PaymentRate(amount=5, days=30)
        session.add(r)
        await session.commit()

        result = (await session.execute(
            __import__("sqlalchemy").select(PaymentRate).where(PaymentRate.amount == 5)
        )).scalar_one()
        assert result.days == 30

    async def test_rate_unique_amount(self, session):
        session.add(PaymentRate(amount=5, days=30))
        await session.commit()
        session.add(PaymentRate(amount=5, days=60))
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()


class TestDeviceStateModel:
    async def test_create_device_state(self, session):
        ds = DeviceState(
            device_id="Solar-001",
            secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            count=0,
            status="unbound",
        )
        session.add(ds)
        await session.commit()

        result = (await session.execute(
            __import__("sqlalchemy").select(DeviceState).where(DeviceState.device_id == "Solar-001")
        )).scalar_one()
        assert result.status == "unbound"
        assert result.used_counts == []

    async def test_device_state_used_counts_jsonb(self, session):
        ds = DeviceState(
            device_id="Solar-002",
            status="active",
            used_counts=[1, 2, 3],
        )
        session.add(ds)
        await session.commit()

        result = (await session.execute(
            __import__("sqlalchemy").select(DeviceState).where(DeviceState.device_id == "Solar-002")
        )).scalar_one()
        assert result.used_counts == [1, 2, 3]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`

- [ ] **Step 3: 编写 models.py**

```python
"""SQLAlchemy ORM 模型 — 5 张表：customers, tokens, sms_records, payment_rates, device_states。"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import (
    Column, String, Integer, Numeric, Text, Date, DateTime, ForeignKey, JSON, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _new_id(prefix: str) -> str:
    return f"{prefix}{str(uuid.uuid4())[:4].upper()}"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("C"))
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    device_id = Column(String(50), nullable=False)
    secret_key = Column(String(64), nullable=False)
    count = Column(Integer, default=0)
    status = Column(String(20), default="locked")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
    locked_at = Column(DateTime(timezone=True), nullable=True)

    tokens = relationship("Token", back_populates="customer", lazy="selectin")
    sms_records = relationship("SmsRecord", back_populates="customer", lazy="selectin")


class Token(Base):
    __tablename__ = "tokens"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("T"))
    customer_id = Column(String(8), ForeignKey("customers.id"), nullable=False, index=True)
    token = Column(String(9), nullable=False)
    days = Column(Integer, nullable=False)
    count = Column(Integer, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
    expires_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now() + timedelta(days=7))

    customer = relationship("Customer", back_populates="tokens")

    __table_args__ = (
        Index("ix_tokens_expires_at", "expires_at"),
    )


class SmsRecord(Base):
    __tablename__ = "sms_records"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("S"))
    customer_id = Column(String(8), ForeignKey("customers.id"), nullable=False)
    to_phone = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now())

    customer = relationship("Customer", back_populates="sms_records")


class PaymentRate(Base):
    __tablename__ = "payment_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Numeric(10, 2), nullable=False, unique=True)
    days = Column(Integer, nullable=False)


class DeviceState(Base):
    __tablename__ = "device_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), nullable=False, unique=True, index=True)
    secret_key = Column(String(64), nullable=True)
    count = Column(Integer, default=0)
    used_counts = Column(JSON, default=list)
    remaining_days = Column(Integer, default=0)
    last_update = Column(Date, nullable=True)
    status = Column(String(20), default="unbound")
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_models.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_models.py
git commit -m "feat: 添加 SQLAlchemy ORM 模型 — customers, tokens, sms_records, payment_rates, device_states"
```

---

### Task 4: 创建 app/database.py — 连接池 + session 注入

**Files:**
- Create: `app/database.py`

- [ ] **Step 1: 编写测试 test_database.py**

Create file `tests/test_database.py`:

```python
"""database.py 测试 — engine 创建、session 工厂、get_db 依赖注入。"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import create_engine_and_session, get_db
from app.settings import TEST_DATABASE_URL


class TestDatabase:
    async def test_engine_connects(self):
        engine, _ = create_engine_and_session(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()

    async def test_session_factory_creates_session(self):
        engine, session_factory = create_engine_and_session(TEST_DATABASE_URL)
        async with session_factory() as session:
            assert isinstance(session, AsyncSession)
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()

    async def test_session_commit_and_rollback(self):
        engine, session_factory = create_engine_and_session(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            from app.models import Base
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            from app.models import Customer
            c = Customer(id="C0001", name="Test", phone="1", device_id="D1",
                         secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
            session.add(c)
            await session.commit()

        async with engine.begin() as conn:
            from app.models import Base
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_database.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 编写 database.py**

```python
"""PostgreSQL 连接池 + session 工厂 + FastAPI Depends 注入。"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.settings import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW


def create_engine_and_session(database_url: str = None):
    """创建 async engine 和 session 工厂。可传入 database_url 覆盖（测试用）。"""
    url = database_url or DATABASE_URL
    engine = create_async_engine(
        url,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


# 全局 engine + session 工厂
engine, AsyncSessionLocal = create_engine_and_session()


async def get_db() -> AsyncSession:
    """FastAPI Depends: 每个请求注入一个独立 AsyncSession，结束后自动关闭。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_database.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/database.py tests/test_database.py
git commit -m "feat: 添加 database.py — async engine + session 工厂 + get_db 注入"
```

---

### Task 5: 创建 app/redis.py — Redis 客户端 + 缓存工具

**Files:**
- Create: `app/redis.py`

- [ ] **Step 1: 编写测试 test_redis_client.py**

Create file `tests/test_redis_client.py`:

```python
"""redis.py 测试 — 连接、session 读写、API 缓存、防重放。"""
import pytest
from app.redis import (
    get_redis, init_redis, close_redis,
    session_create, session_get,
    cache_get, cache_set, cache_delete,
    antireplay_check_and_mark,
)


@pytest.fixture(autouse=True)
async def clean_redis():
    r = await init_redis()
    await r.flushdb()
    yield
    await r.flushdb()
    await close_redis()


class TestRedisConnection:
    async def test_redis_ping(self):
        r = get_redis()
        assert r is not None
        pong = await r.ping()
        assert pong is True


class TestSessionStore:
    async def test_session_create_and_get(self):
        await session_create("sess-1", {"role": "admin"})
        data = await session_get("sess-1")
        assert data == {"role": "admin"}

    async def test_session_not_found(self):
        data = await session_get("nonexistent")
        assert data is None

    async def test_session_expire(self):
        await session_create("sess-2", {"role": "admin"})
        r = get_redis()
        await r.expire("session:sess-2", 0)  # 立即过期
        data = await session_get("sess-2")
        assert data is None


class TestApiCache:
    async def test_cache_set_and_get(self):
        await cache_set("test:key", {"name": "value"})
        result = await cache_get("test:key")
        assert result == {"name": "value"}

    async def test_cache_miss(self):
        result = await cache_get("nonexistent:key")
        assert result is None

    async def test_cache_delete(self):
        await cache_set("test:del", "x")
        await cache_delete("test:del")
        assert await cache_get("test:del") is None


class TestAntireplay:
    async def test_first_use_allowed(self):
        allowed = await antireplay_check_and_mark("device-1", 1)
        assert allowed is True

    async def test_replay_blocked(self):
        await antireplay_check_and_mark("device-2", 1)
        allowed = await antireplay_check_and_mark("device-2", 1)
        assert allowed is False

    async def test_different_count_allowed(self):
        await antireplay_check_and_mark("device-3", 1)
        allowed = await antireplay_check_and_mark("device-3", 2)
        assert allowed is True
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_redis_client.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 编写 redis.py**

```python
"""Redis 客户端 — session 管理 + API 响应缓存 + Token 防重放。"""
import json
import uuid
from typing import Optional

import redis.asyncio as aioredis

from app.settings import REDIS_URL, CACHE_TTL_API, SESSION_TTL, ANTIREPLAY_TTL

_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    global _client
    _client = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _client


async def close_redis():
    global _client
    if _client:
        await _client.close()
        _client = None


def get_redis() -> Optional[aioredis.Redis]:
    return _client


# ---- Session ----

async def session_create(data: dict) -> str:
    """创建 Redis session，返回 session_id。"""
    sid = str(uuid.uuid4())
    r = get_redis()
    if r:
        await r.setex(f"session:{sid}", SESSION_TTL, json.dumps(data))
    return sid


async def session_get(sid: str) -> Optional[dict]:
    """读取 session，命中则自动续期 TTL。"""
    r = get_redis()
    if r is None:
        return None
    key = f"session:{sid}"
    data = await r.get(key)
    if data is None:
        return None
    await r.expire(key, SESSION_TTL)
    return json.loads(data)


async def session_delete(sid: str):
    r = get_redis()
    if r:
        await r.delete(f"session:{sid}")


# ---- API Cache ----

async def cache_get(key: str) -> Optional[dict]:
    r = get_redis()
    if r is None:
        return None
    data = await r.get(f"cache:{key}")
    return json.loads(data) if data else None


async def cache_set(key: str, value, ttl: int = CACHE_TTL_API):
    r = get_redis()
    if r:
        await r.setex(f"cache:{key}", ttl, json.dumps(value, default=str))


async def cache_delete(pattern: str):
    """删除匹配模式的所有缓存 key。"""
    r = get_redis()
    if r:
        keys = await r.keys(f"cache:{pattern}")
        if keys:
            await r.delete(*keys)


# ---- Antireplay ----

async def antireplay_check_and_mark(device_id: str, count: int) -> bool:
    """检查 (device_id, count) 是否已使用。首次使用返回 True 并标记，重放返回 False。"""
    r = get_redis()
    if r is None:
        return True  # Redis 不可用时降级放行
    key = f"antireplay:{device_id}:{count}"
    was_set = await r.setnx(key, "1")
    if was_set:
        await r.expire(key, ANTIREPLAY_TTL)
    return was_set
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_redis_client.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add app/redis.py tests/test_redis_client.py
git commit -m "feat: 添加 redis.py — session 管理 + API 缓存 + Token 防重放"
```

---

### Task 6: 创建 app/store.py — async 数据访问层

**Files:**
- Create: `app/store.py`
- Create: `tests/test_store.py`

- [ ] **Step 1: 编写 store 测试**

Create file `tests/test_store.py`:

```python
"""store.py 测试 — 所有 async 数据访问函数，操作测试数据库。"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.models import Base, Customer, Token, PaymentRate, SmsRecord
from app.settings import TEST_DATABASE_URL
from app.store import (
    get_customers, get_customer, add_customer, delete_customer,
    update_customer_status, set_customer_count,
    get_tokens, add_token,
    get_payment_rates, get_days_for_amount,
    add_sms_record, get_sms_records,
    seed_payment_rates,
)

TEST_KEY = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


@pytest.fixture(scope="module")
def engine():
    return create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest.fixture(autouse=True)
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


class TestCustomers:
    async def test_get_customers_empty(self, session):
        result = await get_customers(session)
        assert result == []

    async def test_add_and_get_customer(self, session):
        cid = await add_customer(session, "Sok Heng", "0888888001", "Solar-001", TEST_KEY)
        assert cid.startswith("C")
        customer = await get_customer(session, cid)
        assert customer.name == "Sok Heng"
        assert customer.phone == "0888888001"
        assert customer.device_id == "Solar-001"
        assert customer.secret_key == TEST_KEY
        assert customer.count == 0
        assert customer.status == "locked"

    async def test_get_customer_not_found(self, session):
        result = await get_customer(session, "C9999999")
        assert result is None

    async def test_get_customers_list(self, session):
        await add_customer(session, "A", "1", "D1", TEST_KEY)
        await add_customer(session, "B", "2", "D2", TEST_KEY)
        result = await get_customers(session)
        assert len(result) == 2

    async def test_delete_customer(self, session):
        cid = await add_customer(session, "Test", "000", "D000", TEST_KEY)
        ok = await delete_customer(session, cid)
        assert ok is True
        assert await get_customer(session, cid) is None

    async def test_delete_customer_not_found(self, session):
        assert await delete_customer(session, "C9999999") is False

    async def test_update_customer_status(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        ok = await update_customer_status(session, cid, "active")
        assert ok is True
        c = await get_customer(session, cid)
        assert c.status == "active"

    async def test_update_status_nonexistent(self, session):
        assert await update_customer_status(session, "NOEXIST", "active") is False

    async def test_lock_sets_locked_at(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        await update_customer_status(session, cid, "active")
        await update_customer_status(session, cid, "locked")
        c = await get_customer(session, cid)
        assert c.locked_at is not None

    async def test_set_customer_count(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        await set_customer_count(session, cid, 5)
        c = await get_customer(session, cid)
        assert c.count == 5


class TestTokens:
    async def test_get_tokens_empty(self, session):
        result = await get_tokens(session)
        assert result == []

    async def test_add_and_get_token(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        tid = await add_token(session, cid, "123456789", 30, 2)
        assert tid.startswith("T")
        tokens = await get_tokens(session)
        assert len(tokens) == 1
        assert tokens[0].customer_id == cid
        assert tokens[0].days == 30
        assert tokens[0].count == 2

    async def test_get_tokens_returns_list_of_dicts(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        await add_token(session, cid, "111111111", 30, 1)
        await add_token(session, cid, "222222222", 60, 2)
        tokens = await get_tokens(session)
        assert len(tokens) == 2
        assert isinstance(tokens[0], dict)
        assert "id" in tokens[0]
        assert "customer_id" in tokens[0]


class TestPaymentRates:
    async def test_seed_payment_rates(self, session):
        await seed_payment_rates(session)
        rates = await get_payment_rates(session)
        assert len(rates) == 2
        assert {"amount": 5.0, "days": 30} in rates
        assert {"amount": 10.0, "days": 60} in rates

    async def test_get_days_for_amount(self, session):
        await seed_payment_rates(session)
        assert await get_days_for_amount(session, 5) == 30
        assert await get_days_for_amount(session, 10) == 60
        assert await get_days_for_amount(session, 999) == 0

    async def test_seed_idempotent(self, session):
        await seed_payment_rates(session)
        await seed_payment_rates(session)
        rates = await get_payment_rates(session)
        assert len(rates) == 2


class TestSmsRecords:
    async def test_add_and_get_sms(self, session):
        cid = await add_customer(session, "Test", "1", "D1", TEST_KEY)
        sid = await add_sms_record(session, cid, "0888888001", "Test message")
        assert sid.startswith("S")
        records = await get_sms_records(session, cid)
        assert len(records) == 1
        assert records[0]["to_phone"] == "0888888001"
        assert records[0]["message"] == "Test message"

    async def test_get_all_sms(self, session):
        cid1 = await add_customer(session, "A", "1", "D1", TEST_KEY)
        cid2 = await add_customer(session, "B", "2", "D2", TEST_KEY)
        await add_sms_record(session, cid1, "0888888001", "msg1")
        await add_sms_record(session, cid2, "0888888002", "msg2")
        records = await get_sms_records(session)
        assert len(records) == 2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_store.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: 编写 store.py**

```python
"""Async 数据访问层 — 所有 CRUD 操作替换原 db.py 的内存 dict 实现。"""
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, Token, PaymentRate, SmsRecord, _new_id


# ---- Customers ----

async def get_customers(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Customer).order_by(Customer.created_at.desc()))
    return [_customer_to_dict(c) for c in result.scalars().all()]


async def get_customer(db: AsyncSession, customer_id: str) -> dict | None:
    c = await db.get(Customer, customer_id)
    return _customer_to_dict(c) if c else None


async def add_customer(db: AsyncSession, name: str, phone: str,
                       device_id: str, secret_key: str) -> str:
    cid = _new_id("C")
    c = Customer(id=cid, name=name, phone=phone, device_id=device_id, secret_key=secret_key)
    db.add(c)
    await db.commit()
    return cid


async def delete_customer(db: AsyncSession, customer_id: str) -> bool:
    c = await db.get(Customer, customer_id)
    if c is None:
        return False
    await db.delete(c)
    await db.commit()
    return True


async def update_customer_status(db: AsyncSession, customer_id: str, status: str) -> bool:
    c = await db.get(Customer, customer_id)
    if c is None:
        return False
    c.status = status
    if status == "locked":
        c.locked_at = datetime.now()
    await db.commit()
    return True


async def set_customer_count(db: AsyncSession, customer_id: str, new_count: int):
    c = await db.get(Customer, customer_id)
    if c:
        c.count = new_count
        await db.commit()


# ---- Tokens ----

async def get_tokens(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Token).order_by(Token.generated_at.desc()))
    return [_token_to_dict(t) for t in result.scalars().all()]


async def add_token(db: AsyncSession, customer_id: str, token: str,
                    days: int, count: int) -> str:
    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer_id, token=token, days=days, count=count,
        generated_at=datetime.now(), expires_at=datetime.now() + timedelta(days=7),
    )
    db.add(t)
    await db.commit()
    return tid


# ---- Payment Rates ----

async def get_payment_rates(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(PaymentRate).order_by(PaymentRate.amount))
    return [{"amount": float(r.amount), "days": r.days} for r in result.scalars().all()]


async def get_days_for_amount(db: AsyncSession, amount: float) -> int:
    result = await db.execute(
        select(PaymentRate.days).where(PaymentRate.amount == amount)
    )
    days = result.scalar()
    return days if days is not None else 0


async def seed_payment_rates(db: AsyncSession):
    """初始化支付汇率，已存在则跳过。"""
    existing = await db.execute(select(func.count()).select_from(PaymentRate))
    if existing.scalar() > 0:
        return
    db.add_all([
        PaymentRate(amount=5, days=30),
        PaymentRate(amount=10, days=60),
    ])
    await db.commit()


# ---- SMS Records ----

async def add_sms_record(db: AsyncSession, customer_id: str, to_phone: str,
                         message: str) -> str:
    sid = _new_id("S")
    r = SmsRecord(id=sid, customer_id=customer_id, to_phone=to_phone, message=message)
    db.add(r)
    await db.commit()
    return sid


async def get_sms_records(db: AsyncSession, customer_id: str = None) -> list[dict]:
    stmt = select(SmsRecord).order_by(SmsRecord.sent_at.desc())
    if customer_id:
        stmt = stmt.where(SmsRecord.customer_id == customer_id)
    result = await db.execute(stmt)
    return [_sms_to_dict(r) for r in result.scalars().all()]


# ---- Serialization helpers ----

def _customer_to_dict(c: Customer) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "device_id": c.device_id,
        "secret_key": c.secret_key,
        "count": c.count,
        "status": c.status,
        "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else None,
        "locked_at": c.locked_at.strftime("%Y-%m-%d %H:%M:%S") if c.locked_at else None,
    }


def _token_to_dict(t: Token) -> dict:
    return {
        "id": t.id,
        "customer_id": t.customer_id,
        "token": t.token,
        "days": t.days,
        "count": t.count,
        "generated_at": t.generated_at.strftime("%Y-%m-%d %H:%M:%S") if t.generated_at else None,
        "expires_at": t.expires_at.strftime("%Y-%m-%d %H:%M:%S") if t.expires_at else None,
    }


def _sms_to_dict(r: SmsRecord) -> dict:
    return {
        "id": r.id,
        "customer_id": r.customer_id,
        "to_phone": r.to_phone,
        "message": r.message,
        "sent_at": r.sent_at.strftime("%Y-%m-%d %H:%M:%S") if r.sent_at else None,
    }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_store.py -v`
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
git add app/store.py tests/test_store.py
git commit -m "feat: 添加 store.py — async 数据访问层，替代内存 dict"
```

---

### Task 7: 更新 app/main.py — 生命周期管理

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: 重写 main.py**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.models import Base
from app.database import engine, get_db
from app.redis import init_redis, close_redis
from app.store import seed_payment_rates
from app.routers.auth import router as auth_router
from app.routers.customers import router as customers_router
from app.routers.config import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：创建表 + 初始化 Redis + 种子数据
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_redis()
    # 种子支付汇率
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await seed_payment_rates(db)
    yield
    # 关闭：释放连接池 + 关闭 Redis
    await engine.dispose()
    await close_redis()


app = FastAPI(title="Cambodia Solar PAYGO Platform", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(config_router)


@app.get("/dashboard")
async def dashboard(request: Request):
    if request.cookies.get("session") != "authenticated":
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html")
```

- [ ] **Step 2: 验证应用启动**

Run: `source venv/bin/activate && timeout 5 uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 || true`
Expected: 输出包含 "Application startup complete" 且无错误

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: main.py 添加 lifespan 管理 — 启动建表/种子数据/Redis，关闭释放连接池"
```

---

### Task 8: 更新 app/routers/auth.py — Redis Session

**Files:**
- Modify: `app/routers/auth.py`

- [ ] **Step 1: 更新 auth.py**

Replace entire file with:

```python
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis import session_create, session_delete

router = APIRouter()
templates = Jinja2Templates(directory="templates")

HARDCODED_USERNAME = "admin"
HARDCODED_PASSWORD = "admin123"


async def check_auth(request: Request):
    """检查 Redis session，返回 True 表示已认证。"""
    from app.redis import session_get
    sid = request.cookies.get("session")
    if not sid:
        return False
    data = await session_get(sid)
    return data is not None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == HARDCODED_USERNAME and password == HARDCODED_PASSWORD:
        sid = await session_create({"role": "admin", "username": username})
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="session", value=sid, httponly=True)
        return response
    return templates.TemplateResponse(
        request, "login.html", {"error": "用户名或密码错误"}, status_code=200,
    )


@router.get("/logout")
async def logout(request: Request):
    sid = request.cookies.get("session")
    if sid:
        await session_delete(sid)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session")
    return response
```

- [ ] **Step 2: Commit**

```bash
git add app/routers/auth.py
git commit -m "feat: auth.py 改用 Redis session — 30min TTL，httponly cookie"
```

---

### Task 9: 更新 app/routers/customers.py — async handler

**Files:**
- Modify: `app/routers/customers.py`

- [ ] **Step 1: 更新 customers.py**

Replace entire file with:

```python
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import (
    get_customers, get_customer as store_get_customer,
    add_customer as store_add_customer, delete_customer as store_delete_customer,
    set_customer_count, update_customer_status,
    get_tokens, add_token,
    add_sms_record, get_sms_records, get_days_for_amount,
)
from app.redis import cache_get, cache_set, cache_delete
from openpaygo import generate_token, TokenType

router = APIRouter(prefix="/api")


# ---- Helper ----

SECRET_KEY_LENGTH = 32
SECRET_KEY_HEX_CHARS = set("0123456789abcdefABCDEF")


def _validate_secret_key(key: str) -> None:
    if len(key) != SECRET_KEY_LENGTH or not all(c in SECRET_KEY_HEX_CHARS for c in key):
        raise HTTPException(
            status_code=400,
            detail=f"secret_key 必须是 {SECRET_KEY_LENGTH} 位 hex 字符串",
        )


async def _check_auth(request: Request):
    from app.redis import session_get
    sid = request.cookies.get("session")
    if not sid:
        raise HTTPException(status_code=401, detail="未认证")
    data = await session_get(sid)
    if data is None:
        raise HTTPException(status_code=401, detail="未认证")


# ---- Utils ----

@router.get("/utils/generate-secret-key")
async def generate_secret_key():
    import secrets
    return {"secret_key": secrets.token_hex(16)}


@router.get("/utils/generate-secret-keys")
async def generate_secret_keys(count: int = 5):
    import secrets
    if count < 1 or count > 20:
        raise HTTPException(status_code=400, detail="数量范围 1-20")
    return {"secret_keys": [secrets.token_hex(16) for _ in range(count)]}


# ---- Customers ----

class CustomerCreate(BaseModel):
    name: str
    phone: str
    device_id: str
    secret_key: str


class TokenGenerate(BaseModel):
    days: int


class SimulatePayment(BaseModel):
    amount: float


@router.get("/customers")
async def list_customers(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get("customers:list")
    if cached:
        return cached
    result = await get_customers(db)
    await cache_set("customers:list", result)
    return result


@router.post("/customers")
async def create_customer(request: Request, body: CustomerCreate,
                          db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    _validate_secret_key(body.secret_key)
    cid = await store_add_customer(
        db, name=body.name, phone=body.phone,
        device_id=body.device_id, secret_key=body.secret_key,
    )
    await cache_delete("customers:*")
    customer = await store_get_customer(db, cid)
    return customer


@router.get("/customers/{customer_id}")
async def get_customer_detail(request: Request, customer_id: str,
                              db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cache_key = f"customers:{customer_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    await cache_set(cache_key, customer)
    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer_route(request: Request, customer_id: str,
                                db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await store_delete_customer(db, customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="客户不存在")
    await cache_delete("customers:*")
    return {"ok": True}


@router.post("/customers/{customer_id}/token")
async def generate_token_for_customer(request: Request, customer_id: str,
                                      body: TokenGenerate,
                                      db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        value=body.days,
        token_type=TokenType.ADD_TIME,
    )
    await set_customer_count(db, customer_id, new_count)
    await add_token(db, customer_id, token_str, body.days, new_count)
    await update_customer_status(db, customer_id, "active")
    await cache_delete("customers:*")
    await cache_delete("tokens:*")

    return {"token": token_str, "customer_id": customer_id, "days": body.days}


@router.get("/tokens")
async def list_tokens(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get("tokens:list")
    if cached:
        return cached
    result = await get_tokens(db)
    await cache_set("tokens:list", result)
    return result


@router.post("/customers/{customer_id}/simulate-payment")
async def simulate_payment(request: Request, customer_id: str,
                           body: SimulatePayment,
                           db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    days = await get_days_for_amount(db, body.amount)
    if days == 0:
        raise HTTPException(status_code=400, detail=f"不支持的金额: ${body.amount}")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        value=days,
        token_type=TokenType.ADD_TIME,
    )
    await set_customer_count(db, customer_id, new_count)
    await add_token(db, customer_id, token_str, days, new_count)
    await update_customer_status(db, customer_id, "active")

    message = (
        f"[PAYGO Solar] 尊敬的用户，您已成功支付${body.amount:.2f}。"
        f"您的太阳能激活码为：{token_str}。有效期{days}天。请尽快输入您的设备。"
    )
    await add_sms_record(db, customer_id, customer["phone"], message)
    await cache_delete("customers:*")
    await cache_delete("tokens:*")
    await cache_delete("sms:*")

    return {
        "token": token_str, "customer_id": customer_id, "days": days,
        "sms": {"to": customer["phone"], "message": message},
    }


@router.post("/customers/{customer_id}/lock")
async def lock_device(request: Request, customer_id: str,
                      db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    await update_customer_status(db, customer_id, "locked")
    await cache_delete("customers:*")
    return {"status": "ok"}


@router.post("/customers/{customer_id}/permanent-unlock")
async def permanent_unlock(request: Request, customer_id: str,
                           db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        token_type=TokenType.DISABLE_PAYG,
    )
    await set_customer_count(db, customer_id, new_count)
    await add_token(db, customer_id, token_str, -1, new_count)
    await update_customer_status(db, customer_id, "permanent")

    message = (
        f"[PAYGO Solar] 恭喜！您的贷款已全部结清。"
        f"设备永久解锁码：{token_str}。请在您的设备中输入此码以永久解锁。"
    )
    await add_sms_record(db, customer_id, customer["phone"], message)
    await cache_delete("customers:*")
    await cache_delete("tokens:*")
    await cache_delete("sms:*")

    return {
        "token": token_str, "customer_id": customer_id, "days": -1,
        "sms": {"to": customer["phone"], "message": message},
    }


@router.get("/sms")
async def list_sms(request: Request, customer_id: str = None,
                   db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get(f"sms:{customer_id or 'all'}")
    if cached:
        return cached
    result = await get_sms_records(db, customer_id)
    await cache_set(f"sms:{customer_id or 'all'}", result)
    return result
```

- [ ] **Step 2: Commit**

```bash
git add app/routers/customers.py
git commit -m "feat: customers.py 改为 async handler + DB session 注入 + Redis 缓存"
```

---

### Task 10: 更新 app/routers/config.py — async handler

**Files:**
- Modify: `app/routers/config.py`

- [ ] **Step 1: 更新 config.py**

Replace entire file with:

```python
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import get_payment_rates
from app.redis import cache_get, cache_set, session_get

router = APIRouter(prefix="/api/config")


async def _check_auth(request: Request):
    sid = request.cookies.get("session")
    if not sid:
        raise HTTPException(status_code=401, detail="未认证")
    data = await session_get(sid)
    if data is None:
        raise HTTPException(status_code=401, detail="未认证")


@router.get("/payment-rates")
async def list_payment_rates(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get("config:payment-rates")
    if cached:
        return cached
    result = await get_payment_rates(db)
    await cache_set("config:payment-rates", result)
    return result
```

- [ ] **Step 2: Commit**

```bash
git add app/routers/config.py
git commit -m "feat: config.py 改为 async handler + Redis 缓存"
```

---

### Task 11: 更新 controller/state_manager.py — PostgreSQL 持久化

**Files:**
- Modify: `controller/state_manager.py`

- [ ] **Step 1: 更新 state_manager.py**

Replace entire file with:

```python
"""状态机 + PostgreSQL 持久化模块 — OpenPAYGO 版本。"""
import asyncio
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.models import Base, DeviceState
from app.settings import DATABASE_URL

_engine = None
_session_factory = None


def _get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine, _session_factory


async def _ensure_tables():
    engine, _ = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def load(device_id: str = "default") -> dict:
    await _ensure_tables()
    _, session_factory = _get_engine()
    async with session_factory() as db:
        result = await db.execute(
            select(DeviceState).where(DeviceState.device_id == device_id)
        )
        ds = result.scalar()
        if ds is None:
            return {
                "device_id": device_id,
                "secret_key": None,
                "count": 0,
                "used_counts": [],
                "remaining_days": 0,
                "last_update": None,
                "status": "unbound",
            }
        return _to_dict(ds)


async def save(state: dict) -> None:
    await _ensure_tables()
    _, session_factory = _get_engine()
    device_id = state.get("device_id", "default")
    async with session_factory() as db:
        result = await db.execute(
            select(DeviceState).where(DeviceState.device_id == device_id)
        )
        ds = result.scalar()
        if ds is None:
            ds = DeviceState(device_id=device_id)
            db.add(ds)
        ds.secret_key = state.get("secret_key")
        ds.count = state.get("count", 0)
        ds.used_counts = state.get("used_counts", [])
        ds.remaining_days = state.get("remaining_days", 0)
        ds.last_update = (
            date.fromisoformat(state["last_update"])
            if state.get("last_update") else None
        )
        ds.status = state.get("status", "unbound")
        await db.commit()


def apply_token(state: dict, days: int, token_type: int, new_count: int,
                used_counts: list | None) -> None:
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


async def reset(device_id: str = "default") -> dict:
    state = {
        "device_id": device_id,
        "secret_key": None,
        "count": 0,
        "used_counts": [],
        "remaining_days": 0,
        "last_update": None,
        "status": "unbound",
    }
    await save(state)
    return state


def tick(state: dict) -> None:
    if state["status"] in ("unbound", "locked", "permanent"):
        return
    today = date.today()
    last = (
        date.fromisoformat(state["last_update"])
        if state["last_update"] else today
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
    if state["status"] == "permanent":
        return
    state["remaining_days"] = max(0, state["remaining_days"] - days)
    if state["remaining_days"] <= 0:
        state["remaining_days"] = 0
        state["status"] = "locked"
    state["last_update"] = date.today().isoformat()


def _to_dict(ds: DeviceState) -> dict:
    return {
        "device_id": ds.device_id,
        "secret_key": ds.secret_key,
        "count": ds.count,
        "used_counts": list(ds.used_counts) if ds.used_counts else [],
        "remaining_days": ds.remaining_days,
        "last_update": ds.last_update.isoformat() if ds.last_update else None,
        "status": ds.status,
    }
```

- [ ] **Step 2: Commit**

```bash
git add controller/state_manager.py
git commit -m "feat: state_manager.py 改用 PostgreSQL device_states 表持久化"
```

---

### Task 12: 更新 controller/controller.py — 适配 async state_manager

**Files:**
- Modify: `controller/controller.py`

- [ ] **Step 1: 更新 controller.py**

Replace entire file with:

```python
#!/usr/bin/env python3
"""PAYGO 太阳能控制器 — 终端模拟脚本 (OpenPAYGO + PostgreSQL)。"""
import asyncio
import os

from openpaygo import decode_token, TokenType
from state_manager import (
    load, save, apply_token, tick, reset, fast_forward,
)

STATUS_LABELS = {
    "unbound": "未绑定",
    "active": "已激活",
    "locked": "已锁定",
    "permanent": "永久解锁",
}

RELAY_ON = "● 供电中"
RELAY_OFF = "○ 断开"


def clear_screen():
    os.system("clear")


def render(state):
    clear_screen()
    tick(state)

    key = state["secret_key"]
    key_display = key[:8] + "…" if key else "（未设置）"
    status = state["status"]
    days = state["remaining_days"]

    if days == -1:
        days_text = "∞"
    else:
        days_text = f"{days} 天"

    relay = RELAY_ON if status in ("active", "permanent") else RELAY_OFF

    print("── 太阳能控制器 ────────────────────────────")
    print(f"  密钥      {key_display}")
    if status == "permanent":
        print(f"  状态      {STATUS_LABELS[status]} · {days_text}")
    elif days == 0 and status == "unbound":
        print(f"  状态      {STATUS_LABELS[status]} · {days_text}")
    else:
        print(f"  状态      {STATUS_LABELS[status]} · 剩余 {days_text}")
    print(f"  继电器    {relay}")
    print(f"  Count     {state['count']}")
    print("─────────────────────────────────────────────")
    print("  [N] 输入Token  [D] 快进天数  [R] 重置  [Q] 退出")


def initial_setup(state):
    if state["secret_key"]:
        return
    clear_screen()
    print("── 初始设置 ──────────────────────────────")
    print("  请输入设备预设密钥（32位 hex）")
    key = input("  > ").strip()
    if len(key) == 32 and all(c in "0123456789abcdefABCDEF" for c in key):
        state["secret_key"] = key
        asyncio.run(save(state))
        print("  密钥已保存")
    else:
        print("  无效密钥格式")
    input("  按回车键继续…")


async def main_async():
    state = await load()
    while True:
        initial_setup(state)
        render(state)
        await save(state)
        cmd = input("> ").strip().upper()

        if cmd == "Q":
            break
        elif cmd == "R":
            confirm = input("  确认重置？将清除密钥和天数 (y/N): ").strip().upper()
            if confirm == "Y":
                state = await reset()
        elif cmd == "D":
            try:
                days = int(input("  快进天数: ").strip())
            except ValueError:
                print("  无效天数")
                input("  按回车键继续…")
                continue
            fast_forward(state, days)
            await save(state)
            print(f"  ✓ 已快进 {days} 天 · 剩余 {state['remaining_days']} 天")
            input("  按回车键继续…")
        elif cmd == "N":
            if not state["secret_key"]:
                print("  请先设置设备密钥")
                input("  按回车键继续…")
                continue

            token = input("  Token (9位): ").strip()
            if len(token) != 9 or not token.isdigit():
                print("  ✗ Token 格式错误（需要9位数字）")
                input("  按回车键继续…")
                continue

            value, token_type, new_count, used_counts = decode_token(
                token=token,
                secret_key=state["secret_key"],
                count=state["count"],
                used_counts=state["used_counts"],
            )

            if token_type == TokenType.INVALID:
                print("  ✗ Token 无效")
                input("  按回车键继续…")
            elif token_type == TokenType.ALREADY_USED:
                print("  ✗ Token 已使用过（防重放）")
                input("  按回车键继续…")
            else:
                days = int(value) if value else 0
                apply_token(state, days, token_type, new_count, used_counts)
                await save(state)

                if token_type == TokenType.DISABLE_PAYG:
                    print("  ✓✓ 贷款已结清 · 设备永久解锁")
                else:
                    print(f"  ✓ 验证成功 · +{days} 天 · 剩余 {state['remaining_days']} 天")
                input("  按回车键继续…")

    print("控制器已退出。")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add controller/controller.py
git commit -m "feat: controller.py 适配 async state_manager — PostgreSQL 持久化"
```

---

### Task 13: 更新测试基础设施 — conftest.py

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: 更新 conftest.py**

Replace entire file with:

```python
import pytest

# ---------------------------------------------------------------------------
# Monkey-patch openpaygo to fix None-handling bug
# ---------------------------------------------------------------------------
from openpaygo.token_decode import OpenPAYGOTokenDecoder as _Decoder

_orig_count_is_valid = _Decoder._count_is_valid.__func__
_orig_update_used_counts = _Decoder.update_used_counts.__func__


@classmethod
def _patched_count_is_valid(cls, count, last_count, value, type, used_counts):
    if used_counts is None:
        used_counts = []
    return _orig_count_is_valid(cls, count, last_count, value, type, used_counts)


@classmethod
def _patched_update_used_counts(cls, past_used_counts, value, new_count, type):
    if not past_used_counts:
        past_used_counts = []
    return _orig_update_used_counts(cls, past_used_counts, value, new_count, type)


_Decoder._count_is_valid = _patched_count_is_valid
_Decoder.update_used_counts = _patched_update_used_counts


# ---------------------------------------------------------------------------
# 测试数据库 fixtures
# ---------------------------------------------------------------------------
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models import Base
from app.settings import TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine():
    return create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_database(engine):
    """在整个测试 session 中创建一次表，结束后清理。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(engine):
    """每个测试独立的 DB session，测试结束后 rollback 保证隔离。"""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "test: 更新 conftest.py — 测试数据库 session fixture"
```

---

### Task 14: 更新旧测试文件适配 async

**Files:**
- Modify: `tests/test_db.py` (重定向到 test_store.py)
- Modify: `tests/test_customers_api.py`
- Modify: `tests/test_config_api.py`
- Modify: `tests/test_auth.py`
- Modify: `tests/test_state_manager.py`
- Modify: `tests/test_integration.py`
- Modify: `tests/test_controller_integration.py`
- Modify: `tests/test_upgrade.py`

- [ ] **Step 1: 删除旧 test_db.py**

Run: `rm tests/test_db.py`
（功能已由 tests/test_store.py 完整覆盖）

- [ ] **Step 2: 更新 tests/test_auth.py**

Replace entire file with:

```python
"""认证测试 — Redis session 版本的登录/登出。"""
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    from app.main import app
    from app.redis import init_redis, close_redis
    await init_redis()
    r = __import__("app.redis", fromlist=["get_redis"]).get_redis()
    await r.flushdb()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await r.flushdb()
    await close_redis()


class TestAuth:
    async def test_login_page_returns_html(self, client):
        resp = await client.get("/login")
        assert resp.status_code == 200
        assert "login" in resp.text.lower()

    async def test_login_success_redirects(self, client):
        resp = await client.post("/login", data={"username": "admin", "password": "admin123"})
        assert resp.status_code == 303
        assert "session" in resp.cookies

    async def test_login_failure_shows_error(self, client):
        resp = await client.post("/login", data={"username": "admin", "password": "wrong"})
        assert resp.status_code == 200
        assert "用户名或密码错误" in resp.text

    async def test_logout_clears_cookie(self, client):
        resp = await client.get("/logout")
        assert resp.status_code == 303
        # cookie 应该被删除（值为空或已过期）

    async def test_dashboard_redirects_when_not_authenticated(self, client):
        resp = await client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 303

    async def test_dashboard_accessible_after_login(self, client):
        login_resp = await client.post("/login", data={"username": "admin", "password": "admin123"})
        session_cookie = login_resp.cookies.get("session")
        resp = await client.get("/dashboard", cookies={"session": session_cookie})
        assert resp.status_code == 200
```

- [ ] **Step 3: 运行测试验证通过**

Run: `pytest tests/test_auth.py -v`
Expected: 6 passed

- [ ] **Step 4: 更新 tests/test_config_api.py**

Replace entire file with:

```python
"""支付汇率 API 测试 — async handler + 真实测试数据库。"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.models import Base
from app.settings import TEST_DATABASE_URL
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
async def client():
    from app.main import app
    from app.redis import init_redis, close_redis
    from app.store import seed_payment_rates
    from app.database import AsyncSessionLocal

    # 初始化 Redis
    await init_redis()
    r = __import__("app.redis", fromlist=["get_redis"]).get_redis()
    await r.flushdb()

    # 种子数据
    async with AsyncSessionLocal() as db:
        await seed_payment_rates(db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await r.flushdb()
    await close_redis()


async def _login(client):
    resp = await client.post("/login", data={"username": "admin", "password": "admin123"})
    return resp.cookies.get("session")


class TestConfigApi:
    async def test_get_payment_rates_requires_auth(self, client):
        resp = await client.get("/api/config/payment-rates")
        assert resp.status_code == 401

    async def test_get_payment_rates(self, client):
        sid = await _login(client)
        resp = await client.get("/api/config/payment-rates", cookies={"session": sid})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert {"amount": 5.0, "days": 30} in data
        assert {"amount": 10.0, "days": 60} in data
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/test_config_api.py -v`
Expected: 2 passed

- [ ] **Step 6: 更新 tests/test_state_manager.py**

Modify test_state_manager.py to use async. Key changes:
- `load()` → `await load()`
- `save(state)` → `await save(state)`
- `reset()` → `await reset()`

Since the state_manager functions are now async, all tests need `@pytest.mark.asyncio` and `await`.

Run to check what needs updating:
`pytest tests/test_state_manager.py -v`

- [ ] **Step 7: 更新 tests/test_customers_api.py**

需要改写为 async + 真实测试 DB。关键点：
- 使用 `AsyncClient` + `ASGITransport`
- 每个测试前通过 `_login()` 获取 session cookie
- API 端点不变，响应格式不变

- [ ] **Step 8: 更新 tests/test_integration.py, test_controller_integration.py, test_upgrade.py**

同样改为 async + 真实 DB。

- [ ] **Step 9: 运行全部测试**

Run: `pytest tests/ -v`
Expected: 全部通过（约 70+ tests）

- [ ] **Step 10: Commit**

```bash
git add tests/
git commit -m "test: 迁移所有测试到 async + 真实测试数据库"
```

---

### Task 15: 删除 app/db.py + 最终验证

**Files:**
- Delete: `app/db.py`

- [ ] **Step 1: 删除旧 db.py**

Run: `rm app/db.py`

- [ ] **Step 2: 确认无引用残留**

Run: `grep -r "from app.db import\|from app import db\|import app.db" app/ tests/ controller/ 2>/dev/null || echo "No references found"`
Expected: No references found

- [ ] **Step 3: 运行全部测试**

Run: `pytest tests/ -v`
Expected: 全部通过

- [ ] **Step 4: 验证应用启动**

Run: `source venv/bin/activate && timeout 5 uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 || true`
Expected: 启动成功，无错误

- [ ] **Step 5: Commit**

```bash
git rm app/db.py
git commit -m "feat: 删除 app/db.py — 完全迁移至 PostgreSQL + Redis"
```

---

### 实施顺序（依赖关系）

```
Task 1 (安装依赖)
  ↓
Task 2 (settings.py)
  ↓
Task 3 (models.py) ───── Task 5 (redis.py)
  ↓                        ↓
Task 4 (database.py) ──────┤
  ↓                        ↓
Task 6 (store.py) ─────────┤
  ↓                        ↓
Task 7 (main.py) ←────────┘
  ↓
Task 8 (auth.py)
  ↓
Task 9 (customers.py)
  ↓
Task 10 (config.py)
  ↓
Task 11 (state_manager.py)
  ↓
Task 12 (controller.py)
  ↓
Task 13 (conftest.py)
  ↓
Task 14 (更新旧测试)
  ↓
Task 15 (删除 db.py)
```
