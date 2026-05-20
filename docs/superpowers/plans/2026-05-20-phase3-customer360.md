# Phase 3: 客户 360 视图与 MFI 管理 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 客户详情从简单信息卡升级为 360 度聚合视图，包含合同/还款日历/Token时间线/标签，新增 MFI 机构管理，列表筛选增强。

**Architecture:** Customer 模型新增 7 个字段（地址/GPS/证件/MFI关联/标签），新增 mfis 表。Store 层增加客户筛选+360聚合查询+标签管理+MFI CRUD。API 层增强现有客户端点。UI 层在客户详情页增加合同卡片/还款日历/Token时间线/标签。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Jinja2, Chart.js, JSONB (tags)

---

### Task 1: 数据模型 — Customer 扩展 + MFI 表

**Files:**
- Modify: `app/models.py`
- Modify: `app/main.py` (ALTER TABLE migrations)
- Test: `tests/test_models.py`

- [ ] **Step 1: 修改 Customer 模型**

在 `app/models.py` 的 Customer 类中，`locked_at` 之后，`tokens` relationship 之前新增字段：

```python
    address = Column(Text, nullable=True)
    gps_latitude = Column(Numeric(10, 8), nullable=True)
    gps_longitude = Column(Numeric(11, 8), nullable=True)
    id_number = Column(String(50), nullable=True)
    mfi_id = Column(String(8), ForeignKey("mfis.id"), nullable=True, index=True)
    tags = Column(JSONB, nullable=True, default=list)
```

在 Customer 类之后，新增 MFI 模型：

```python
class Mfi(Base):
    """MFI 小额信贷机构"""
    __tablename__ = "mfis"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("MF"))
    name = Column(String(100), nullable=False)
    branch = Column(String(100), nullable=True)
    contact_info = Column(Text, nullable=True)
    api_endpoint = Column(String(255), nullable=True)
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
```

- [ ] **Step 2: 修改 main.py — 添加 ALTER TABLE 迁移**

```python
        # Phase 3 — Customer 扩展字段
        for col, col_type in [
            ("address", "TEXT"),
            ("gps_latitude", "NUMERIC(10,8)"),
            ("gps_longitude", "NUMERIC(11,8)"),
            ("id_number", "VARCHAR(50)"),
            ("mfi_id", "VARCHAR(8)"),
            ("tags", "JSONB DEFAULT '[]'::jsonb"),
        ]:
            await conn.run_sync(lambda c, col=col, col_type=col_type: c.execute(text(
                f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {col} {col_type}"
            )))
```

- [ ] **Step 3: 运行测试确认**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_models.py -v
```
Expected: all PASS

- [ ] **Step 4: 提交**

```bash
git add app/models.py app/main.py && git commit -m "feat: Customer model — add address/GPS/id/mfi/tags fields + Mfi model"
```

---

### Task 2: Store 层 — 客户筛选 + 360聚合 + MFI CRUD + 标签管理

**Files:**
- Modify: `app/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: 写 store 测试**

在 `tests/test_store.py` 追加：

```python
from app.store import (
    get_customers_filtered, get_customer_360, add_mfi, get_mfis,
    update_customer_tags, add_customer_field,
)

class TestCustomer360:
    async def _setup(self, session):
        from app.security import init_fernet
        init_fernet()
        # 创建 MFI
        mfi_id = await add_mfi(session, "LOLC Cambodia", "Phnom Penh")
        # 创建客户
        cid = await add_customer(session, "Test360", "+855555", "DEV-360", "a"*32)
        # 扩展字段
        await add_customer_field(session, cid, address="123 Street", id_number="ID001", mfi_id=mfi_id)
        return cid

    async def test_get_customers_filtered_by_name(self, session):
        await self._setup(session)
        result = await get_customers_filtered(session, search="Test360")
        assert len(result) == 1
        empty = await get_customers_filtered(session, search="NoSuchName")
        assert len(empty) == 0

    async def test_get_customers_filtered_by_status(self, session):
        await self._setup(session)
        result = await get_customers_filtered(session, status="locked")
        assert len(result) >= 1

    async def test_get_customer_360(self, session):
        cid = await self._setup(session)
        view = await get_customer_360(session, cid)
        assert view is not None
        assert view["customer"]["name"] == "Test360"
        assert view["customer"]["address"] == "123 Street"
        assert "contracts" in view
        assert "tokens" in view
        assert view["mfi_name"] == "LOLC Cambodia"

    async def test_update_customer_tags(self, session):
        cid = await self._setup(session)
        await update_customer_tags(session, cid, ["VIP", "高风险"])
        c = await get_customer(session, cid)
        assert "VIP" in c["tags"]
        assert "高风险" in c["tags"]


class TestMfiCRUD:
    async def test_add_and_list_mfi(self, session):
        mid = await add_mfi(session, "PRASAC", "Siem Reap")
        assert mid.startswith("MF")
        mfis = await get_mfis(session)
        assert len(mfis) == 1
        assert mfis[0]["name"] == "PRASAC"

    async def test_get_mfis_filter_by_status(self, session):
        await add_mfi(session, "ACLEDA", "Battambang")
        active = await get_mfis(session, status="active")
        assert len(active) == 1
        inactive = await get_mfis(session, status="disabled")
        assert len(inactive) == 0
```

- [ ] **Step 2: 确认测试失败**

```bash
pytest tests/test_store.py::TestCustomer360 -v 2>&1 | tail -5
```
Expected: FAIL

- [ ] **Step 3: 实现 store.py 新增函数**

在 `app/store.py` 末尾追加：

```python
# ============================================================
# 客户 360 + MFI CRUD + 标签
# ============================================================

async def get_customers_filtered(
    db: AsyncSession,
    search: str = None,
    status: str = None,
    mfi_id: str = None,
    tags: str = None,
) -> list[dict]:
    """客户列表 — 支持姓名/电话搜索 + 状态/MFI/标签筛选"""
    q = select(Customer).order_by(Customer.created_at.desc())
    if search:
        q = q.where(
            (Customer.name.ilike(f"%{search}%")) |
            (Customer.phone.ilike(f"%{search}%"))
        )
    if status:
        q = q.where(Customer.status == status)
    if mfi_id:
        q = q.where(Customer.mfi_id == mfi_id)
    result = await db.execute(q)
    customers = result.scalars().all()

    # 标签筛选在 Python 层面做（JSONB contains 查询）
    filtered = []
    for c in customers:
        d = _customer_to_dict(c)
        if tags and c.tags:
            if tags not in c.tags:
                continue
        filtered.append(d)
    return filtered


async def get_customer_360(db: AsyncSession, customer_id: str) -> dict | None:
    """客户 360 聚合视图：基本信息 + 合同列表 + Token 历史 + MFI 信息"""
    c = await db.get(Customer, customer_id)
    if not c:
        return None

    # 合同列表
    contracts_result = await db.execute(
        select(Contract).where(Contract.customer_id == customer_id)
    )
    contracts = [_contract_to_dict(ct) for ct in contracts_result.scalars().all()]

    # Token 历史（最近 20 条）
    tokens_result = await db.execute(
        select(Token).where(Token.customer_id == customer_id)
        .order_by(Token.generated_at.desc()).limit(20)
    )
    tokens = [_token_to_dict(t) for t in tokens_result.scalars().all()]

    # MFI 信息
    mfi_name = None
    if c.mfi_id:
        mfi_result = await db.execute(select(Mfi.name).where(Mfi.id == c.mfi_id))
        mfi_name = mfi_result.scalar()

    return {
        "customer": _customer_to_dict(c),
        "contracts": contracts,
        "tokens": tokens,
        "mfi_name": mfi_name,
    }


async def add_customer_field(
    db: AsyncSession, customer_id: str,
    address: str = None, id_number: str = None,
    gps_latitude: float = None, gps_longitude: float = None,
    mfi_id: str = None,
) -> bool:
    """更新客户扩展字段"""
    c = await db.get(Customer, customer_id)
    if not c:
        return False
    if address is not None: c.address = address
    if id_number is not None: c.id_number = id_number
    if gps_latitude is not None: c.gps_latitude = gps_latitude
    if gps_longitude is not None: c.gps_longitude = gps_longitude
    if mfi_id is not None: c.mfi_id = mfi_id
    await db.commit()
    return True


async def update_customer_tags(db: AsyncSession, customer_id: str, tag_list: list[str]) -> bool:
    """更新客户标签列表"""
    c = await db.get(Customer, customer_id)
    if not c:
        return False
    c.tags = tag_list
    await db.commit()
    return True


async def add_mfi(db: AsyncSession, name: str, branch: str = "") -> str:
    """新增 MFI 机构"""
    mid = _new_id("MF")
    m = Mfi(id=mid, name=name, branch=branch)
    db.add(m)
    await db.commit()
    return mid


async def get_mfis(db: AsyncSession, status: str = None) -> list[dict]:
    """MFI 机构列表"""
    q = select(Mfi).order_by(Mfi.name)
    if status:
        q = q.where(Mfi.status == status)
    result = await db.execute(q)
    return [{"id": m.id, "name": m.name, "branch": m.branch,
             "contact_info": m.contact_info, "api_endpoint": m.api_endpoint,
             "status": m.status} for m in result.scalars().all()]
```

修改 `_customer_to_dict`，添加新字段：

```python
def _customer_to_dict(c: Customer) -> dict:
    raw_key = None
    if c.secret_key_encrypted:
        raw_key = decrypt_secret(c.secret_key_encrypted)
    elif c.secret_key:
        raw_key = c.secret_key
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "device_id": c.device_id,
        "secret_key": raw_key or "",
        "count": c.count,
        "status": c.status,
        "address": c.address,
        "gps_latitude": float(c.gps_latitude) if c.gps_latitude else None,
        "gps_longitude": float(c.gps_longitude) if c.gps_longitude else None,
        "id_number": c.id_number,
        "mfi_id": c.mfi_id,
        "tags": c.tags or [],
        "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else None,
        "locked_at": c.locked_at.strftime("%Y-%m-%d %H:%M:%S") if c.locked_at else None,
    }
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_store.py -v
```
Expected: ~36 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/store.py tests/test_store.py && git commit -m "feat: store — customer filters + 360 view + MFI CRUD + tags"
```

---

### Task 3: API — 客户360端点 + 筛选增强 + MFI 端点

**Files:**
- Modify: `app/routers/customers.py`
- Test: `tests/test_customers_api.py`

- [ ] **Step 1: 增强 customers API**

在 `app/routers/customers.py` 中：

修改 `list_customers` 端点，增加筛选参数：
```python
@router.get("/customers")
async def list_customers(request: Request,
                         search: str = None,
                         status: str = None,
                         mfi_id: str = None,
                         tags: str = None,
                         db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    result = await get_customers_filtered(db, search=search, status=status,
                                          mfi_id=mfi_id, tags=tags)
    return result
```

新增客户 360 端点：
```python
@router.get("/customers/{customer_id}/360")
async def get_customer_360_view(request: Request, customer_id: str,
                                 db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    view = await get_customer_360(db, customer_id)
    if not view:
        raise HTTPException(status_code=404, detail="客户不存在")
    return view
```

新增标签更新端点：
```python
class TagsUpdate(BaseModel):
    tags: list[str]

@router.put("/customers/{customer_id}/tags")
async def api_update_tags(request: Request, customer_id: str, body: TagsUpdate,
                           db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await update_customer_tags(db, customer_id, body.tags)
    if not ok:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"ok": True}
```

新增 MFI 端点：
```python
@router.get("/mfis")
async def list_mfis(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_mfis(db)

class MfiCreate(BaseModel):
    name: str
    branch: str = ""

@router.post("/mfis")
async def create_mfi(request: Request, body: MfiCreate,
                     db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    mid = await add_mfi(db, body.name, body.branch)
    return {"id": mid, "name": body.name, "branch": body.branch}
```

修改 import 增加：
```python
from app.store import (
    ...
    get_customers_filtered, get_customer_360,
    update_customer_tags, add_mfi, get_mfis,
)
```

- [ ] **Step 2: 追加 API 测试**

在 `tests/test_customers_api.py` 末尾追加 4 个测试：

```python
@pytest.mark.asyncio
async def test_get_customers_filtered_by_name(auth_client):
    resp = await auth_client.get("/api/customers?search=Test")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_get_customer_360(auth_client):
    customers = (await auth_client.get("/api/customers")).json()
    if customers:
        cid = customers[0]["id"]
        resp = await auth_client.get(f"/api/customers/{cid}/360")
        assert resp.status_code == 200
        data = resp.json()
        assert "customer" in data
        assert "contracts" in data
        assert "tokens" in data

@pytest.mark.asyncio
async def test_mfi_crud(auth_client):
    resp = await auth_client.post("/api/mfis", json={"name":"LOLC","branch":"PP"})
    assert resp.status_code == 200
    mfis = (await auth_client.get("/api/mfis")).json()
    assert len(mfis) >= 1

@pytest.mark.asyncio
async def test_update_tags(auth_client):
    customers = (await auth_client.get("/api/customers")).json()
    if customers:
        cid = customers[0]["id"]
        resp = await auth_client.put(f"/api/customers/{cid}/tags",
            json={"tags":["VIP"]})
        assert resp.status_code == 200
```

- [ ] **Step 3: 运行 API 测试**

```bash
pytest tests/test_customers_api.py -v
```
Expected: ~26 tests PASS

- [ ] **Step 4: 提交**

```bash
git add app/routers/customers.py tests/test_customers_api.py && git commit -m "feat: API — customer 360 view + filters + MFI CRUD + tags"
```

---

### Task 4: UI — 客户详情增强（360视图）

**Files:**
- Modify: `templates/dashboard.html`

- [ ] **Step 1: 替换 selectCustomer 函数**

重写 `selectCustomer` 函数，调用 `/api/customers/{id}/360` 替代 `/api/customers/{id}`，展示合同卡片+Token时间线+标签管理。

关键变更（在现有 selectCustomer 函数基础上）：

1. 数据源改为 `GET /api/customers/{id}/360`
2. 在详情区域增加：
   - 客户扩展信息（地址/GPS/身份证/MFI）
   - 合同聚合卡片（每个合同小卡片，点击跳转合同详情）
   - Token 时间线（最近 5 条）
   - 标签管理（显示+新增+删除按钮）

```javascript
async function selectCustomer(id) {
  selectedCustomerId = id;
  document.querySelectorAll('.nav-tab').forEach(function(el) {
    el.classList.toggle('active', el.dataset.tab === 'customers');
  });
  document.querySelector('.main-layout').classList.remove('sidebar-hidden');
  await loadCustomers();

  // 使用 360 聚合接口
  const resp = await fetch('/api/customers/' + encodeURIComponent(id) + '/360');
  const view = await resp.json();
  const c = view.customer;

  const initials = c.name.charAt(0);
  const statusLabel = STATUS_MAP[c.status] || c.status;
  const statusClass = STATUS_CLASS[c.status] || '';
  const statusDot = STATUS_DOT[c.status] || '';

  const contractsHtml = view.contracts && view.contracts.length > 0
    ? view.contracts.map(function(ct) {
        return '<div class="customer-item" onclick="switchTab(\'contracts\');selectContract(\'' + ct.id + '\')" style="cursor:pointer;margin:4px 0;">' +
          '<span>' + ct.contract_no + '</span>' +
          '<span style="float:right;color:#64748b;font-size:12px;">' + ct.status + '</span></div>';
      }).join('')
    : '<p style="color:#94a3b8;font-size:12px;">暂无合同</p>';

  const tokensHtml = view.tokens && view.tokens.length > 0
    ? '<div style="border-left:2px solid #e2e8f0;padding-left:12px;">' +
      view.tokens.slice(0,10).map(function(t) {
        return '<div style="margin:6px 0;font-size:12px;">' +
          '<span style="color:#059669;">' + t.token + '</span>' +
          ' · <span>' + (t.days === -1 ? '永久' : t.days+'天') + '</span>' +
          ' · <span style="color:#94a3b8;">' + (t.generated_at || '') + '</span>' +
          ' · <span>' + (t.status || 'UNUSED') + '</span></div>';
      }).join('') + '</div>'
    : '<p style="color:#94a3b8;font-size:12px;">暂无 Token</p>';

  const tagsHtml = c.tags && c.tags.length > 0
    ? c.tags.map(function(t) { return '<span class="tag-chip">' + escapeHtml(t) + ' <a href="#" onclick="removeTag(\'' + c.id + '\',\'' + t + '\');return false;">×</a></span>'; }).join('')
    : '<span style="color:#94a3b8;font-size:12px;">暂无标签</span>';

  document.getElementById('detailPanel').innerHTML = `
    <div class="detail-card">
      <div class="detail-header">
        <div class="detail-avatar">${initials}</div>
        <div>
          <h2>${escapeHtml(c.name)}</h2>
          <span class="status-badge ${statusClass}">${statusDot} ${statusLabel}</span>
        </div>
      </div>

      <div class="detail-body">
        <div class="detail-row"><span class="label">电话</span><span class="value">${c.phone}</span></div>
        <div class="detail-row"><span class="label">设备编号</span><span class="value">${c.device_id}</span></div>
        <div class="detail-row"><span class="label">设备密钥</span><span class="value-mono">${(c.secret_key||'').substring(0,12)}…</span></div>
        <div class="detail-row"><span class="label">Token 计数</span><span class="value">${c.count}</span></div>
        ${c.address ? '<div class="detail-row"><span class="label">地址</span><span class="value">' + escapeHtml(c.address) + '</span></div>' : ''}
        ${c.id_number ? '<div class="detail-row"><span class="label">身份证</span><span class="value">' + escapeHtml(c.id_number) + '</span></div>' : ''}
        ${c.gps_latitude ? '<div class="detail-row"><span class="label">GPS</span><span class="value">' + c.gps_latitude + ', ' + c.gps_longitude + '</span></div>' : ''}
        ${view.mfi_name ? '<div class="detail-row"><span class="label">MFI</span><span class="value">' + escapeHtml(view.mfi_name) + '</span></div>' : ''}
        <div class="detail-row"><span class="label">创建日期</span><span class="value">${c.created_at}</span></div>
      </div>

      <div class="detail-section">
        <h4>标签</h4>
        <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
          ${tagsHtml}
          <button class="btn btn-outline btn-sm" onclick="addTag('${c.id}')">+ 添加标签</button>
        </div>
      </div>

      <div class="detail-section">
        <h4>模拟支付</h4>
        <p style="color:#94a3b8;font-size:12px;margin-bottom:10px;">模拟客户通过 Bakong 完成还款</p>
        <button class="btn btn-primary" onclick="showSimulatePaymentModal('${c.id}', '${escapeHtml(c.name).replace(/'/g, "\\'")}')">模拟支付</button>
      </div>

      <div class="detail-section">
        <h4>合同列表</h4>
        ${contractsHtml}
      </div>

      <div class="detail-section">
        <h4>Token 历史</h4>
        ${tokensHtml}
      </div>

      <div class="detail-body">
        <div class="action-group">
          <button class="btn btn-danger" onclick="showLockConfirm('${c.id}', '${escapeHtml(c.name).replace(/'/g, "\\'")}')">锁定设备</button>
          <button class="btn btn-warning" onclick="showPermanentUnlockConfirm('${c.id}', '${escapeHtml(c.name).replace(/'/g, "\\'")}')">永久解锁</button>
          <button class="btn btn-outline" style="color:#dc2626;" onclick="showDeleteModal('${c.id}', '${escapeHtml(c.name).replace(/'/g, "\\'")}')">删除客户</button>
        </div>
      </div>
    </div>
  `;
}
```

- [ ] **Step 2: 添加标签管理 JS 函数**

在 dashboard.html 末尾追加：

```javascript
async function addTag(cid) {
  const tag = prompt('输入标签名（如：VIP、高风险、投诉频繁、新客户）：');
  if (!tag) return;
  const resp = await fetch('/api/customers/' + encodeURIComponent(cid) + '/360');
  const view = await resp.json();
  const currentTags = view.customer.tags || [];
  if (currentTags.includes(tag)) { showToast('标签已存在'); return; }
  const newTags = currentTags.concat([tag]);
  await fetch('/api/customers/' + encodeURIComponent(cid) + '/tags', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({tags: newTags})
  });
  selectCustomer(cid);
}

async function removeTag(cid, tag) {
  const resp = await fetch('/api/customers/' + encodeURIComponent(cid) + '/360');
  const view = await resp.json();
  const newTags = (view.customer.tags || []).filter(function(t) { return t !== tag; });
  await fetch('/api/customers/' + encodeURIComponent(cid) + '/tags', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({tags: newTags})
  });
  selectCustomer(cid);
}
```

在 `switchTab('customers')` 中添加搜索筛选器。找到 switchTab 中 `customers` 分支，增强 keygenSection：

```javascript
    const keygenSection = document.querySelector('.keygen-section');
    if (keygenSection) {
      keygenSection.innerHTML = `
        <div class="keygen-title">客户筛选</div>
        <div style="padding:8px 12px;">
          <input type="text" id="customerSearch" placeholder="搜索姓名/电话..." 
            style="width:100%;padding:6px 10px;border:1px solid #e2e8f0;border-radius:4px;font-size:12px;margin-bottom:6px;"
            onkeyup="searchCustomers()">
        </div>
        <div style="padding:0 12px 8px;">
          <button class="keygen-btn" onclick="generateKeys()">生成 5 个设备密钥</button>
        </div>
        <div class="keygen-list" id="keygenList"></div>
      `;
    }
```

添加搜索函数：
```javascript
let customerSearchTimeout = null;
async function searchCustomers() {
  clearTimeout(customerSearchTimeout);
  customerSearchTimeout = setTimeout(async function() {
    const q = document.getElementById('customerSearch').value.trim();
    const url = q ? '/api/customers?search=' + encodeURIComponent(q) : '/api/customers';
    const resp = await fetch(url);
    const customers = await resp.json();
    renderCustomerList(customers);
  }, 300);
}

function renderCustomerList(customers) {
  const container = document.getElementById('customerItems');
  document.getElementById('customerCount').textContent = customers.length;
  if (customers.length === 0) {
    container.innerHTML = '<p style="color:#94a3b8;font-size:13px;text-align:center;padding:20px;">无匹配客户</p>';
    return;
  }
  container.innerHTML = customers.map(function(c) {
    const tagStr = c.tags && c.tags.length > 0 ? ' · ' + c.tags.join(',') : '';
    return '<div class="customer-item ' + (c.id === selectedCustomerId ? 'active' : '') + '" onclick="selectCustomer(\'' + c.id + '\')">' +
      '<div class="name">' + (STATUS_DOT[c.status] || '⚪') + ' ' + escapeHtml(c.name) + tagStr + '</div>' +
      '<div class="meta">' + c.phone + ' · ' + c.device_id + '</div></div>';
  }).join('');
}
```

修改 `loadCustomers` 函数，改用 `renderCustomerList`：
```javascript
async function loadCustomers() {
  const resp = await fetch('/api/customers');
  const customers = await resp.json();
  renderCustomerList(customers);
  document.getElementById('customerCount').textContent = customers.length;
}
```

- [ ] **Step 3: 提交**

```bash
git add templates/dashboard.html && git commit -m "feat: UI — customer 360 view with contracts/tokens/timeline/tags/search"
```

---

### Task 5: 全量回归测试 + 修复

- [ ] **Step 1: 运行全部测试**

```bash
pytest tests/ -v 2>&1 | tail -30
```

- [ ] **Step 2: 修复 + 确认**

```bash
pytest tests/ -q 2>&1 | tail -5
```
Expected: ~188 tests PASS

- [ ] **Step 3: 提交**

```bash
git add -A && git commit -m "fix: full regression — Phase 3 customer 360 complete"
```

---

### Task 6: 冒烟测试

- [ ] 启动应用，验证：客户列表搜索、客户详情 360 视图（合同卡片/Token时间线/标签）、MFI 管理 API
