# Phase 2: Token 管理独立模块 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Token 从客户详情附带功能升级为独立管理模块，支持列表筛选、批量生成、手动补发、Token 作废的完整生命周期。

**Architecture:** 新增 `app/routers/tokens.py`（独立 Token 管理 API），增强 store.py Token CRUD（筛选/批量/补发/作废），Token 模型新增状态和审计字段，dashboard.html 新增「Token 管理」tab。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Jinja2, Chart.js

---

### Task 1: Token 模型增强 + 数据迁移

**Files:**
- Modify: `app/models.py`
- Modify: `app/main.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 修改 Token 模型**

在 `app/models.py` 的 Token 类中新增字段（在 `contract_id` 之后，`count` 之前）：

```python
    status = Column(String(20), default="UNUSED")  # UNUSED / USED / SUPERSEDED
    superseded_by = Column(String(8), nullable=True)  # 替换 Token ID
    voided_at = Column(DateTime(timezone=True), nullable=True)
    voided_by = Column(String(100), nullable=True)
    void_reason = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
```

- [ ] **Step 2: 修改 main.py — ALTER TABLE 迁移**

在 `app/main.py` 的 lifespan 中添加：

```python
        # Token 管理字段
        for col, col_type in [
            ("status", "VARCHAR(20) DEFAULT 'UNUSED'"),
            ("superseded_by", "VARCHAR(8)"),
            ("voided_at", "TIMESTAMP WITH TIME ZONE"),
            ("voided_by", "VARCHAR(100)"),
            ("void_reason", "TEXT"),
            ("ip_address", "VARCHAR(45)"),
            ("user_agent", "TEXT"),
        ]:
            await conn.run_sync(lambda c: c.execute(text(
                f"ALTER TABLE tokens ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )))
```

- [ ] **Step 3: 运行模型测试确认**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_models.py -v
```
Expected: all tests PASS

- [ ] **Step 4: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add app/models.py app/main.py && git commit -m "feat: Token model — add status/superseded/void/audit fields"
```

---

### Task 2: Store 层 — Token 增强 CRUD

**Files:**
- Modify: `app/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: 写 store 测试**

在 `tests/test_store.py` 追加：

```python
from app.store import (
    get_tokens_filtered, get_token_stats, batch_generate_tokens,
    reissue_token, void_token, get_token_detail,
)

class TestTokenManagement:
    async def _setup(self, session):
        from app.security import init_fernet, encrypt_secret
        init_fernet()
        cid = await add_customer(session, "TokTest", "+8551", "DEV-T1", "a" * 32)
        # 创建多个 Token
        for i in range(3):
            await add_token(session, cid, f"12345678{i}", 30, i + 1, amount=5.0)
        return cid

    async def test_get_tokens_filtered(self, session):
        """按客户/时间/状态筛选 Token 列表"""
        from app.security import init_fernet
        init_fernet()
        cid = await self._setup(session)

        # 全部
        all_tokens = await get_tokens_filtered(session)
        assert len(all_tokens) == 3

        # 按客户筛选
        by_customer = await get_tokens_filtered(session, customer_id=cid)
        assert len(by_customer) == 3

        # 不存在的客户
        empty = await get_tokens_filtered(session, customer_id="NONEXIST")
        assert len(empty) == 0

    async def test_get_token_stats(self, session):
        """Token 统计：今日/本月生成数、使用率"""
        from app.security import init_fernet
        init_fernet()
        await self._setup(session)
        stats = await get_token_stats(session)
        assert stats["total"] == 3
        assert stats["today"] >= 0
        assert stats["this_month"] >= 0

    async def test_get_token_detail(self, session):
        """Token 详情包含客户名和合同信息"""
        from app.security import init_fernet
        init_fernet()
        cid = await self._setup(session)
        all_tokens = await get_tokens_filtered(session)
        tid = all_tokens[0]["id"]

        detail = await get_token_detail(session, tid)
        assert detail is not None
        assert detail["customer_name"] is not None
        assert detail["status"] == "UNUSED"

    async def test_reissue_token(self, session):
        """补发 Token：验证未使用 → 新 Token → 标记原 Token"""
        from app.security import init_fernet
        init_fernet()
        cid = await self._setup(session)
        all_tokens = await get_tokens_filtered(session)
        original = all_tokens[0]

        result = await reissue_token(session, original["id"], reason="客户未收到 SMS")
        assert result is not None
        assert result["token"] != original["token"]
        assert result["superseded_id"] == original["id"]

        # 原 Token 状态变为 SUPERSEDED
        orig_detail = await get_token_detail(session, original["id"])
        assert orig_detail["status"] == "SUPERSEDED"

    async def test_reissue_token_already_used_fails(self, session):
        """已使用的 Token 不可补发"""
        from app.security import init_fernet
        init_fernet()
        cid = await self._setup(session)
        all_tokens = await get_tokens_filtered(session)
        # 先作废第一个 token
        await void_token(session, all_tokens[0]["id"], "admin", "test")
        # 尝试补发
        result = await reissue_token(session, all_tokens[0]["id"], reason="test")
        assert result is None

    async def test_void_token(self, session):
        """作废 Token：状态变 SUPERSEDED，记录操作人"""
        from app.security import init_fernet
        init_fernet()
        await self._setup(session)
        all_tokens = await get_tokens_filtered(session)
        tid = all_tokens[0]["id"]

        ok = await void_token(session, tid, "admin", "安全原因")
        assert ok is True

        detail = await get_token_detail(session, tid)
        assert detail["status"] == "SUPERSEDED"
        assert detail["voided_by"] == "admin"
```

- [ ] **Step 2: 确认测试失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_store.py::TestTokenManagement -v 2>&1 | tail -5
```
Expected: FAIL

- [ ] **Step 3: 实现 store.py 新增函数**

在 `app/store.py` 末尾追加：

```python
# ============================================================
# Token 管理增强 — 筛选/统计/批量/补发/作废/详情
# ============================================================

async def get_tokens_filtered(
    db: AsyncSession,
    customer_id: str = None,
    token_type: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Token 列表 — 支持多维度筛选 + 分页"""
    q = select(Token).order_by(Token.generated_at.desc())
    if customer_id:
        q = q.where(Token.customer_id == customer_id)
    if status:
        q = q.where(Token.status == status)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return [_token_to_dict(t) for t in result.scalars().all()]


async def get_token_stats(db: AsyncSession) -> dict:
    """Token 统计卡片"""
    from datetime import datetime
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_result = await db.execute(select(func.count()).select_from(Token))
    total = total_result.scalar() or 0

    today_result = await db.execute(
        select(func.count()).select_from(Token).where(Token.generated_at >= today_start)
    )
    today = today_result.scalar() or 0

    month_result = await db.execute(
        select(func.count()).select_from(Token).where(Token.generated_at >= month_start)
    )
    this_month = month_result.scalar() or 0

    superseded_result = await db.execute(
        select(func.count()).select_from(Token).where(Token.status == "SUPERSEDED")
    )
    superseded = superseded_result.scalar() or 0

    return {
        "total": total,
        "today": today,
        "this_month": this_month,
        "superseded": superseded,
    }


async def get_token_detail(db: AsyncSession, tid: str) -> dict | None:
    """Token 详情 — 含客户名和关联信息"""
    result = await db.execute(
        select(Token, Customer.name)
        .join(Customer, Token.customer_id == Customer.id, isouter=True)
        .where(Token.id == tid)
    )
    row = result.first()
    if not row:
        return None
    t, customer_name = row
    d = _token_to_dict(t)
    d["customer_name"] = customer_name or "-"
    d["status"] = t.status or "UNUSED"
    d["voided_by"] = t.voided_by
    d["void_reason"] = t.void_reason
    d["voided_at"] = t.voided_at.strftime("%Y-%m-%d %H:%M:%S") if t.voided_at else None
    d["superseded_by"] = t.superseded_by
    return d


async def batch_generate_tokens(
    db: AsyncSession,
    customer_ids: list[str],
    days: int,
    token_type: str = "ADD_TIME",
) -> list[dict]:
    """批量生成 Token — 为指定客户列表每人生成一个 Token"""
    from openpaygo import generate_token, TokenType as OT
    type_map = {"ADD_TIME": OT.ADD_TIME, "SET_TIME": OT.SET_TIME,
                "DISABLE_PAYG": OT.DISABLE_PAYG}
    ot_type = type_map.get(token_type, OT.ADD_TIME)

    results = []
    for cid in customer_ids:
        customer = await db.get(Customer, cid)
        if not customer:
            continue
        raw_key = decrypt_secret(customer.secret_key_encrypted) if customer.secret_key_encrypted else customer.secret_key
        if not raw_key:
            continue

        new_count, token_str = generate_token(
            secret_key=raw_key, count=customer.count,
            value=days if ot_type == OT.ADD_TIME else None,
            token_type=ot_type,
        )
        customer.count = new_count
        customer.status = "active"

        tid = _new_id("T")
        t = Token(id=tid, customer_id=cid, token=token_str, days=days,
                  count=new_count, amount=0)
        db.add(t)
        results.append({"customer_id": cid, "token_id": tid, "token": token_str,
                        "days": days, "status": "success"})

    if results:
        await db.commit()
    return results


async def reissue_token(db: AsyncSession, original_tid: str, reason: str = "") -> dict | None:
    """补发 Token：验证原 Token 未使用 → 生成新 Token(Counter+1) → 标记原 Token"""
    orig = await db.get(Token, original_tid)
    if not orig or orig.status == "SUPERSEDED":
        return None

    customer = await db.get(Customer, orig.customer_id)
    if not customer:
        return None

    raw_key = decrypt_secret(customer.secret_key_encrypted) if customer.secret_key_encrypted else customer.secret_key
    if not raw_key:
        return None

    from openpaygo import generate_token, TokenType as OT
    new_count, token_str = generate_token(
        secret_key=raw_key, count=customer.count + 1,
        value=orig.days, token_type=OT.ADD_TIME,
    )
    customer.count = new_count

    # 新 Token
    new_tid = _new_id("T")
    new_t = Token(id=new_tid, customer_id=customer.id, token=token_str,
                  days=orig.days, count=new_count, amount=float(orig.amount or 0),
                  contract_id=orig.contract_id)
    db.add(new_t)

    # 标记原 Token
    orig.status = "SUPERSEDED"
    orig.superseded_by = new_tid
    orig.void_reason = reason
    orig.voided_at = datetime.now()

    await db.commit()
    return {"token_id": new_tid, "token": token_str, "days": orig.days,
            "superseded_id": original_tid}


async def void_token(db: AsyncSession, tid: str, operator: str, reason: str = "") -> bool:
    """作废 Token：标记 SUPERSEDED + 记录操作人"""
    t = await db.get(Token, tid)
    if not t:
        return False
    t.status = "SUPERSEDED"
    t.voided_by = operator
    t.void_reason = reason
    t.voided_at = datetime.now()
    await db.commit()
    return True
```

修改 `add_token` 函数，增加 `contract_id` 和 `status` 参数支持：
```python
async def add_token(db: AsyncSession, customer_id: str, token: str,
                    days: int, count: int, amount: float = 0,
                    contract_id: str = None) -> str:
    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer_id, token=token, days=days,
        count=count, amount=amount, contract_id=contract_id,
        generated_at=datetime.now(), expires_at=datetime.now() + timedelta(days=7),
    )
    db.add(t)
    await db.commit()
    return tid
```

修改 `_token_to_dict`，增加新字段：
```python
def _token_to_dict(t: Token) -> dict:
    return {
        "id": t.id,
        "customer_id": t.customer_id,
        "token": t.token,
        "days": t.days,
        "amount": float(t.amount) if t.amount else 0,
        "count": t.count,
        "status": t.status or "UNUSED",
        "contract_id": t.contract_id,
        "voided_by": t.voided_by,
        "void_reason": t.void_reason,
        "superseded_by": t.superseded_by,
        "generated_at": t.generated_at.strftime("%Y-%m-%d %H:%M:%S") if t.generated_at else None,
        "expires_at": t.expires_at.strftime("%Y-%m-%d %H:%M:%S") if t.expires_at else None,
    }
```

- [ ] **Step 4: 运行 store 测试确认**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_store.py -v
```
Expected: all tests PASS (~29 tests)

- [ ] **Step 5: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add app/store.py tests/test_store.py && git commit -m "feat: store — token CRUD with filters/stats/batch/reissue/void"
```

---

### Task 3: 创建 Token 管理 API router

**Files:**
- Create: `app/routers/tokens.py`
- Modify: `app/main.py`
- Test: `tests/test_tokens_api.py`

- [ ] **Step 1: 写 API 测试**

创建 `tests/test_tokens_api.py`：

```python
"""Token 管理 API 测试"""
import secrets
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.redis import init_redis, close_redis


@pytest.fixture(scope="session", autouse=True)
async def manage_infra():
    await init_redis()
    yield
    await close_redis()
    from app.database import engine
    await engine.dispose()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client(client):
    resp = await client.post(
        "/login", data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    cookie = resp.cookies.get("session")
    assert cookie is not None
    client.cookies.set("session", cookie, domain="test")
    return client


@pytest.mark.asyncio
async def test_get_token_stats(auth_client):
    """Token 统计接口"""
    resp = await auth_client.get("/api/tokens/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "today" in data
    assert "this_month" in data


@pytest.mark.asyncio
async def test_get_token_list_filtered(auth_client):
    """Token 列表筛选"""
    resp = await auth_client.get("/api/tokens")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_token_detail(auth_client):
    """Token 详情 — 先用已有 token"""
    tokens = (await auth_client.get("/api/tokens")).json()
    if tokens:
        tid = tokens[0]["id"]
        resp = await auth_client.get(f"/api/tokens/{tid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "customer_name" in data


@pytest.mark.asyncio
async def test_void_token(auth_client):
    """作废 Token"""
    # 先创建一个客户 + 模拟支付生成 token
    resp = await auth_client.post("/api/customers", json={
        "name": "VoidTest", "phone": "010000300",
        "device_id": f"DEV-{secrets.token_hex(3)}",
        "secret_key": secrets.token_hex(16),
    })
    cid = resp.json()["id"]
    await auth_client.post(f"/api/customers/{cid}/simulate-payment", json={"amount": 5.0})
    tokens = (await auth_client.get("/api/tokens")).json()
    tid = tokens[0]["id"]

    resp = await auth_client.post(f"/api/tokens/{tid}/void", json={
        "reason": "测试作废"
    })
    assert resp.status_code == 200
    detail = (await auth_client.get(f"/api/tokens/{tid}")).json()
    assert detail["status"] == "SUPERSEDED"


@pytest.mark.asyncio
async def test_reissue_token(auth_client):
    """补发 Token"""
    resp = await auth_client.post("/api/customers", json={
        "name": "ReissueTest", "phone": "010000400",
        "device_id": f"DEV-{secrets.token_hex(3)}",
        "secret_key": secrets.token_hex(16),
    })
    cid = resp.json()["id"]
    await auth_client.post(f"/api/customers/{cid}/simulate-payment", json={"amount": 5.0})
    tokens = (await auth_client.get("/api/tokens")).json()
    tid = tokens[0]["id"]

    resp = await auth_client.post(f"/api/tokens/{tid}/reissue", json={
        "reason": "SMS 未送达"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] is not None
    assert data["token"] != tokens[0]["token"]
```

- [ ] **Step 2: 确认测试失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_tokens_api.py -v 2>&1 | tail -5
```
Expected: FAIL (404)

- [ ] **Step 3: 创建 app/routers/tokens.py**

```python
"""Token 管理 API router"""
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import (
    get_tokens_filtered, get_token_stats, get_token_detail,
    batch_generate_tokens, reissue_token, void_token,
)
from app.routers.customers import _check_auth

router = APIRouter(prefix="/api/tokens")


class BatchGenerate(BaseModel):
    customer_ids: list[str]
    days: int = 30
    token_type: str = "ADD_TIME"


class VoidRequest(BaseModel):
    reason: str = ""


class ReissueRequest(BaseModel):
    reason: str = ""


@router.get("/stats")
async def api_token_stats(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_token_stats(db)


@router.get("")
async def api_get_tokens(
    request: Request,
    customer_id: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    await _check_auth(request)
    return await get_tokens_filtered(db, customer_id=customer_id, status=status,
                                     limit=limit, offset=offset)


@router.get("/{tid}")
async def api_token_detail(tid: str, request: Request,
                           db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    detail = await get_token_detail(db, tid)
    if not detail:
        raise HTTPException(404, "Token 不存在")
    return detail


@router.post("/batch-generate")
async def api_batch_generate(body: BatchGenerate, request: Request,
                             db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    results = await batch_generate_tokens(
        db, body.customer_ids, body.days, body.token_type,
    )
    return {"generated": len(results), "results": results}


@router.post("/{tid}/reissue")
async def api_reissue_token(tid: str, body: ReissueRequest, request: Request,
                            db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    result = await reissue_token(db, tid, body.reason)
    if not result:
        raise HTTPException(400, "补发失败（Token 不存在或已被使用/作废）")
    return result


@router.post("/{tid}/void")
async def api_void_token(tid: str, body: VoidRequest, request: Request,
                         db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    # 获取操作人（从 session 中）
    from app.redis import session_get
    sid = request.cookies.get("session")
    session_data = await session_get(sid) if sid else None
    operator = session_data.get("username", "unknown") if session_data else "unknown"

    ok = await void_token(db, tid, operator, body.reason)
    if not ok:
        raise HTTPException(404, "Token 不存在")
    return {"ok": True}
```

- [ ] **Step 4: 注册 router 到 main.py**

在 `app/main.py` 中添加：
```python
from app.routers.tokens import router as tokens_router
app.include_router(tokens_router)
```

- [ ] **Step 5: 运行 API 测试**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_tokens_api.py -v
```
Expected: 6 tests PASS

- [ ] **Step 6: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add app/routers/tokens.py app/main.py tests/test_tokens_api.py && git commit -m "feat: API — Token management router with stats/filter/detail/reissue/void/batch"
```

---

### Task 4: UI — 新增「Token 管理」导航 Tab

**Files:**
- Modify: `templates/base.html`
- Modify: `templates/dashboard.html`

- [ ] **Step 1: base.html 添加新 Tab**

在 `templates/base.html` 的 nav-tabs 中添加：

```html
    <a class="nav-tab" data-tab="tokens" onclick="switchTab('tokens')">Token 管理</a>
```

- [ ] **Step 2: dashboard.html 添加 switchTab 处理**

在 `switchTab` 函数的 else-if 链中（在 `contracts` 之后）添加：

```javascript
  } else if (tab === 'tokens') {
    layout.classList.remove('sidebar-hidden');
    selectedCustomerId = null;
    selectedContractId = null;
    loadTokens();
  }
```

- [ ] **Step 3: 添加 Token 列表和详情 JS 函数**

在 dashboard.html 的 JS 区域末尾添加：

```javascript
// ---- Token 管理 ----
let selectedTokenId = null;

async function loadTokens() {
  const resp = await fetch('/api/tokens/stats');
  const stats = await resp.json();

  const tokensResp = await fetch('/api/tokens?limit=100');
  const tokens = await tokensResp.json();

  const container = document.getElementById('customerItems');
  document.querySelector('.sidebar-header h3').textContent = 'Token 列表';
  document.querySelector('.sidebar-header h3').onclick = null;
  document.getElementById('customerCount').textContent = tokens.length;

  const keygenSection = document.querySelector('.keygen-section');
  if (keygenSection) {
    keygenSection.innerHTML = `
      <div class="keygen-title">Token 统计</div>
      <div style="padding:8px 12px;font-size:12px;color:#475569;">
        <div>总数: ${stats.total} · 今日: ${stats.today} · 本月: ${stats.this_month}</div>
        <div style="margin-top:4px;">已作废: ${stats.superseded}</div>
      </div>
    `;
  }

  const STATUS_DOT_T = { 'UNUSED':'⚪', 'USED':'🟢', 'SUPERSEDED':'🔴' };

  container.innerHTML = tokens.map(function(t) {
    return '<div class="customer-item ' + (t.id === selectedTokenId ? 'active' : '') + '" onclick="selectToken(\'' + t.id + '\')">' +
      '<div class="name">' + (STATUS_DOT_T[t.status] || '⚪') + ' ' + t.token + '</div>' +
      '<div class="meta">' + escapeHtml(t.customer_id || '—') + ' · ' + t.days + '天 · ' + (t.status || 'UNUSED') + '</div>' +
      '</div>';
  }).join('');

  if (!selectedTokenId) {
    document.getElementById('detailPanel').innerHTML = '<div class="empty-state"><div class="icon">🔑</div><p>选择左侧 Token 查看详情</p></div>';
  }
}

async function selectToken(tid) {
  selectedTokenId = tid;
  document.querySelectorAll('.nav-tab').forEach(function(el) {
    el.classList.toggle('active', el.dataset.tab === 'tokens');
  });
  document.querySelector('.main-layout').classList.remove('sidebar-hidden');
  await loadTokens();

  const resp = await fetch('/api/tokens/' + encodeURIComponent(tid));
  const t = await resp.json();

  const STATUS_LABEL_T = { 'UNUSED':'未使用', 'USED':'已使用', 'SUPERSEDED':'已作废' };

  document.getElementById('detailPanel').innerHTML = `
    <div class="detail-card">
      <div class="detail-header">
        <div class="detail-avatar">T</div>
        <div>
          <h2>${t.token}</h2>
          <span class="status-badge">${STATUS_LABEL_T[t.status] || t.status}</span>
        </div>
      </div>
      <div class="detail-body">
        <div class="detail-row"><span class="label">Token 值</span><span class="value-mono">${t.token}</span></div>
        <div class="detail-row"><span class="label">类型</span><span class="value">${t.days === -1 ? 'DISABLE_PAYG (永久解锁)' : 'ADD_TIME (' + t.days + '天)'}</span></div>
        <div class="detail-row"><span class="label">客户</span><span class="value">${escapeHtml(t.customer_name || '—')} (${t.customer_id})</span></div>
        <div class="detail-row"><span class="label">金额</span><span class="value">$${t.amount.toFixed(2)}</span></div>
        <div class="detail-row"><span class="label">Counter</span><span class="value">${t.count}</span></div>
        <div class="detail-row"><span class="label">生成时间</span><span class="value">${t.generated_at || '—'}</span></div>
        <div class="detail-row"><span class="label">过期时间</span><span class="value">${t.expires_at || '—'}</span></div>
        ${t.contract_id ? '<div class="detail-row"><span class="label">关联合同</span><span class="value">' + t.contract_id + '</span></div>' : ''}
        ${t.status === 'SUPERSEDED' ? '<div class="detail-row"><span class="label">作废原因</span><span class="value">' + escapeHtml(t.void_reason || '—') + '</span></div>' : ''}
        ${t.superseded_by ? '<div class="detail-row"><span class="label">替换 Token</span><span class="value">' + t.superseded_by + '</span></div>' : ''}
      </div>
      <div class="detail-section">
        <h4>操作</h4>
        <div class="btn-group">
          ${t.status !== 'SUPERSEDED' ? '<button class="btn btn-warning btn-sm" onclick="doVoidToken(\'' + t.id + '\')">作废 Token</button>' : ''}
          ${t.status === 'UNUSED' ? '<button class="btn btn-primary btn-sm" onclick="doReissueToken(\'' + t.id + '\')">补发 Token</button>' : ''}
        </div>
      </div>
    </div>
  `;
}

async function doVoidToken(tid) {
  const reason = prompt('请输入作废原因：');
  if (!reason) return;
  const resp = await fetch('/api/tokens/' + encodeURIComponent(tid) + '/void', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({reason: reason})
  });
  if (!resp.ok) { showToast('作废失败'); return; }
  showToast('Token 已作废');
  selectToken(tid);
}

async function doReissueToken(tid) {
  if (!confirm('确定要补发此 Token 吗？原 Token 将被标记为已作废。')) return;
  const resp = await fetch('/api/tokens/' + encodeURIComponent(tid) + '/reissue', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({reason: '手动补发'})
  });
  if (!resp.ok) { const err = await resp.json(); showToast('补发失败: ' + (err.detail || '')); return; }
  const data = await resp.json();
  showToast('新 Token 已生成: ' + data.token);
  selectedTokenId = null;
  loadTokens();
}
```

- [ ] **Step 3: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add templates/base.html templates/dashboard.html && git commit -m "feat: UI — Token management tab with list/detail/void/reissue"
```

---

### Task 5: 全量回归测试 + 修复

**Files:**
- Modify: 根据失败情况修复

- [ ] **Step 1: 运行全部测试**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/ -v 2>&1 | tail -30
```

- [ ] **Step 2: 修复失败测试**

逐项检查并修复。可能的问题：
- Token API router 的 prefix `/api/tokens` 和 customers.py 的 `/api/tokens` 冲突
  - 解决方案：从 customers.py 移除旧的 `/api/tokens` 端点（或改为兼容转发）
- 新的 store 函数签名和旧调用不一致

- [ ] **Step 3: 确认全部通过**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/ -q
```
Expected: ~172 tests PASS (165 + 7 new)

- [ ] **Step 4: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add -A && git commit -m "fix: full regression — Phase 2 Token management complete"
```

---

### Task 6: 冒烟测试

- [ ] **Step 1: 启动应用**

```bash
source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 验证 Token 管理 Tab**

1. 登录 → 点击「Token 管理」tab
2. 左侧显示 Token 列表（含状态图标）
3. 点击一个 Token → 右侧显示详情（Token值/类型/客户/金额/状态）
4. 点击「作废」→ 输入原因 → Token 状态变为已作废
5. 对未使用的 Token 点击「补发」→ 生成新 Token

- [ ] **Step 3: 验证 API 端点**

```bash
# Token 统计
curl -b cookies.txt http://localhost:8000/api/tokens/stats
# Token 列表
curl -b cookies.txt http://localhost:8000/api/tokens?limit=10
```
