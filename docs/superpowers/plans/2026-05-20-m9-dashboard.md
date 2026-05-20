# M9 运营仪表盘首页 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为运营后台新增一个独立仪表盘首页，展示 KPI 概览卡片、设备状态分布图表、最近交易流水，让平台在演示时呈现运营级系统的数据可视化能力。

**Architecture:** 新增 `/api/dashboard/stats` 接口聚合查询统计数据；dashboard.html 改为双模式（首页仪表盘 / 客户详情），默认显示仪表盘；引入 Chart.js CDN 渲染饼图；Token 模型新增 `amount` 字段记录支付金额。

**Tech Stack:** Python FastAPI + SQLAlchemy 2.0 async + Jinja2 模板 + Chart.js 4.x CDN + 纯 CSS

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `app/models.py` | 修改 | Token 模型新增 `amount` 列 |
| `app/store.py` | 修改 | 新增 `get_dashboard_stats()` 聚合查询 |
| `app/routers/dashboard.py` | 新建 | `/api/dashboard/stats` 接口 |
| `app/main.py` | 修改 | 注册 dashboard router |
| `templates/base.html` | 修改 | 引入 Chart.js CDN |
| `templates/dashboard.html` | 修改 | 双模式：首页仪表盘 + 客户详情 |
| `static/style.css` | 修改 | 仪表盘卡片、图表容器样式 |
| `tests/test_dashboard_api.py` | 新建 | 仪表盘 API 测试 |

---

### Task 1: Token 模型新增 `amount` 字段

**Files:**
- Modify: `app/models.py:40-57`

- [ ] **Step 1: 修改 Token 模型，新增 amount 列**

```python
# app/models.py — Token 类，在 days 列后新增 amount 列
class Token(Base):
    __tablename__ = "tokens"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("T"))
    customer_id = Column(String(8), ForeignKey("customers.id"), nullable=False)
    token = Column(String(9), nullable=False)
    days = Column(Integer, default=0)
    amount = Column(Numeric(10, 2), default=0)     # 新增：支付金额（USD）
    count = Column(Integer, default=0)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="tokens")
```

- [ ] **Step 2: 运行测试验证 Token 模型**

```bash
pytest tests/test_models.py -v
```
Expected: PASS（因为没有破坏现有字段）

- [ ] **Step 3: 更新 `app/store.py` 的 `add_token` 和 `_token_to_dict`，支持 amount**

```python
# app/store.py

async def add_token(db: AsyncSession, customer_id: str, token: str,
                    days: int, count: int, amount: float = 0) -> str:
    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer_id, token=token, days=days,
        count=count, amount=amount,
        generated_at=datetime.now(), expires_at=datetime.now() + timedelta(days=7),
    )
    db.add(t)
    await db.commit()
    return tid


def _token_to_dict(t: Token) -> dict:
    return {
        "id": t.id,
        "customer_id": t.customer_id,
        "token": t.token,
        "days": t.days,
        "amount": float(t.amount) if t.amount else 0,   # 新增
        "count": t.count,
        "generated_at": t.generated_at.strftime("%Y-%m-%d %H:%M:%S") if t.generated_at else None,
        "expires_at": t.expires_at.strftime("%Y-%m-%d %H:%M:%S") if t.expires_at else None,
    }
```

- [ ] **Step 4: 运行 store 测试**

```bash
pytest tests/test_store.py -v
```
Expected: 20 passed

- [ ] **Step 5: 更新 `simulate-payment` 接口，传入 amount**

在 `app/routers/customers.py` 的 `simulate_payment` 函数中，`add_token` 调用传入 `amount=body.amount`。

```python
# app/routers/customers.py — simulate_payment 函数内
new_count, token_str = generate_token(
    secret_key=customer["secret_key"],
    count=customer["count"],
    value=days,
    token_type=TokenType.ADD_TIME,
)
await set_customer_count(db, customer_id, new_count)
await add_token(db, customer_id, token_str, days, new_count, amount=body.amount)  # 新增 amount
await update_customer_status(db, customer_id, "active")
```

永久解锁接口也传 `amount=0`（不需要改，因为默认值已经是 0）。

- [ ] **Step 6: 运行客户 API 测试**

```bash
pytest tests/test_customers_api.py -v
```
Expected: 22 passed

- [ ] **Step 7: Commit**

```bash
git add app/models.py app/store.py app/routers/customers.py
git commit -m "feat: Token 模型新增 amount 字段，simulate-payment 记录支付金额"
```

---

### Task 2: 创建仪表盘 stats API

**Files:**
- Create: `app/store.py` (新增函数)
- Create: `app/routers/dashboard.py`
- Modify: `app/main.py`

- [ ] **Step 1: 写测试 — 仪表盘 stats API**

```python
# tests/test_dashboard_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models import Customer, Token


@pytest.mark.asyncio
async def test_dashboard_stats_empty(async_session, test_client):
    """空数据库返回零值统计"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 登录
        resp = await client.post("/login", data={"username": "admin", "password": "admin123"})
        assert resp.status_code == 303
        resp = await client.get("/api/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_customers"] == 0
        assert data["active_devices"] == 0
        assert data["monthly_revenue"] == 0
        assert data["locked_devices"] == 0
        assert data["permanent_devices"] == 0
        assert data["total_tokens"] == 0
        assert data["recent_transactions"] == []


@pytest.mark.asyncio
async def test_dashboard_stats_with_data(async_session, test_client):
    """有客户和 Token 时返回正确统计"""
    from app.store import add_customer as store_add, add_token as store_add_token
    from app.database import AsyncSessionLocal

    # 先通过 API 创建客户
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/login", data={"username": "admin", "password": "admin123"})
        # 创建 2 个客户
        await client.post("/api/customers", json={
            "name": "Alice", "phone": "011", "device_id": "DEV01",
            "secret_key": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        })
        await client.post("/api/customers", json={
            "name": "Bob", "phone": "022", "device_id": "DEV02",
            "secret_key": "b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        })
        # 模拟支付
        customers = (await client.get("/api/customers")).json()
        alice = next(c for c in customers if c["name"] == "Alice")
        await client.post(f"/api/customers/{alice['id']}/simulate-payment", json={"amount": 5})

        resp = await client.get("/api/dashboard/stats")
        data = resp.json()
        assert data["total_customers"] == 2
        assert data["active_devices"] == 1
        assert data["monthly_revenue"] == 5.0
        assert data["total_tokens"] == 1
        assert len(data["recent_transactions"]) == 1
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_dashboard_api.py -v
```
Expected: FAIL — 404 Not Found（路由未注册）

- [ ] **Step 3: 写 store 聚合查询函数**

```python
# app/store.py — 在文件末尾新增

async def get_dashboard_stats(db: AsyncSession) -> dict:
    from datetime import datetime

    # 客户状态分布
    total_result = await db.execute(select(func.count()).select_from(Customer))
    total_customers = total_result.scalar() or 0

    active_result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.status == "active")
    )
    active_devices = active_result.scalar() or 0

    locked_result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.status == "locked")
    )
    locked_devices = locked_result.scalar() or 0

    permanent_result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.status == "permanent")
    )
    permanent_devices = permanent_result.scalar() or 0

    # 本月收入（Token 表中本月记录的 amount 总和）
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Token.amount), 0)).where(
            Token.generated_at >= month_start
        )
    )
    monthly_revenue = float(revenue_result.scalar() or 0)

    # 本月 Token 总数
    token_count_result = await db.execute(
        select(func.count()).select_from(Token).where(Token.generated_at >= month_start)
    )
    total_tokens = token_count_result.scalar() or 0

    # 最近交易（20 条）
    recent_result = await db.execute(
        select(Token).order_by(Token.generated_at.desc()).limit(20)
    )
    recent_transactions = []
    for t in recent_result.scalars().all():
        customer_result = await db.execute(select(Customer.name).where(Customer.id == t.customer_id))
        customer_name = customer_result.scalar() or "—"
        recent_transactions.append({
            "id": t.id,
            "customer_name": customer_name,
            "amount": float(t.amount) if t.amount else 0,
            "days": t.days,
            "token": t.token,
            "generated_at": t.generated_at.strftime("%Y-%m-%d %H:%M:%S") if t.generated_at else None,
        })

    return {
        "total_customers": total_customers,
        "active_devices": active_devices,
        "locked_devices": locked_devices,
        "permanent_devices": permanent_devices,
        "monthly_revenue": monthly_revenue,
        "total_tokens": total_tokens,
        "recent_transactions": recent_transactions,
    }
```

- [ ] **Step 4: 创建 dashboard router**

```python
# app/routers/dashboard.py
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import get_dashboard_stats
from app.routers.customers import _check_auth

router = APIRouter(prefix="/api")


@router.get("/dashboard/stats")
async def dashboard_stats(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_dashboard_stats(db)
```

- [ ] **Step 5: 注册 dashboard router 到 app**

```python
# app/main.py — 在现有 include_router 后新增
from app.routers.dashboard import router as dashboard_router
app.include_router(dashboard_router)  # 加在 config_router 行后
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/test_dashboard_api.py -v
```
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add app/store.py app/routers/dashboard.py app/main.py tests/test_dashboard_api.py
git commit -m "feat: 新增 /api/dashboard/stats 接口 + 聚合查询（客户/收入/交易）"
```

---

### Task 3: 仪表盘首页 UI — KPI 卡片 + 图表 + 交易列表

**Files:**
- Modify: `templates/dashboard.html`
- Modify: `templates/base.html`

- [ ] **Step 1: base.html 引入 Chart.js CDN**

```html
<!-- templates/base.html — </head> 前新增 -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

- [ ] **Step 2: 重构 dashboard.html — 双模式布局**

整个 dashboard.html 重写，核心改动：

1. 左侧 `sidebar` 保持不变（客户列表 + 密钥生成器）
2. 右侧 `detailPanel` 改为双模式：
   - **首页模式**（默认 / 未选择客户 / 点击 sidebar 标题时）：显示仪表盘
   - **详情模式**（选择客户时）：显示客户详情（原有功能）
3. 仪表盘首页结构：

```
┌─────────────────────────────────────────────────────┐
│  KPI 概览卡片 (4 个横向)                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │总客户   │ │活跃设备  │ │本月收入  │ │逾期设备    │  │
│  │  12     │ │   8     │ │$245.00  │ │   2      │  │
│  └─────────┘ └─────────┘ └─────────┘ └──────────┘  │
├─────────────────────────┬───────────────────────────┤
│  设备状态分布 (饼图)      │  最近交易 (表格)           │
│  Chart.js 饼图          │  ┌──────────────────────┐ │
│                         │  │时间    客户    金额    │ │
│                         │  │ ...    ...    ...    │ │
│                         │  └──────────────────────┘ │
└─────────────────────────┴───────────────────────────┘
```

```html
{% extends "base.html" %}
{% block content %}
<div class="main-layout">
  <!-- 左侧面板 — 保持不变 -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <h3 onclick="showDashboard()" style="cursor:pointer;">客户列表</h3>
      <span class="badge" id="customerCount">0</span>
      <button class="btn btn-primary btn-sm" onclick="showAddCustomerModal()">+ 新增</button>
    </div>
    <div class="customer-list" id="customerItems"></div>
    <div class="keygen-section">
      <div class="keygen-title">密钥生成器</div>
      <button class="keygen-btn" onclick="generateKeys()">生成 5 个设备密钥</button>
      <div class="keygen-list" id="keygenList"></div>
    </div>
  </aside>

  <!-- 右侧面板 — 双模式 -->
  <main class="detail-panel" id="detailPanel">
    <!-- 仪表盘首页（默认） -->
    <div id="dashboardHome"></div>
  </main>
</div>

<!-- 弹窗保持原有不变 ... -->

<script>
let selectedCustomerId = null;
let deleteTargetId = null;

// ---- 仪表盘首页 ----
async function showDashboard() {
  selectedCustomerId = null;
  await loadCustomers();
  const resp = await fetch('/api/dashboard/stats');
  const stats = await resp.json();

  document.getElementById('detailPanel').innerHTML = `
    <div id="dashboardHome">
      <div class="dash-header">
        <h2>运营仪表盘</h2>
        <span class="dash-date" id="dashDate"></span>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card kpi-blue">
          <div class="kpi-value">${stats.total_customers}</div>
          <div class="kpi-label">总客户数</div>
        </div>
        <div class="kpi-card kpi-green">
          <div class="kpi-value">${stats.active_devices}</div>
          <div class="kpi-label">活跃设备</div>
        </div>
        <div class="kpi-card kpi-gold">
          <div class="kpi-value">$${stats.monthly_revenue.toFixed(2)}</div>
          <div class="kpi-label">本月收入 (USD)</div>
        </div>
        <div class="kpi-card kpi-red">
          <div class="kpi-value">${stats.locked_devices}</div>
          <div class="kpi-label">逾期锁定</div>
        </div>
      </div>

      <div class="dash-grid">
        <div class="dash-chart-box">
          <h4>设备状态分布</h4>
          <div class="chart-wrap"><canvas id="statusChart"></canvas></div>
        </div>
        <div class="dash-table-box">
          <h4>最近交易</h4>
          <table class="tx-table" id="txTable">
            <thead><tr><th>时间</th><th>客户</th><th>金额</th><th>天数</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  document.getElementById('dashDate').textContent =
    new Date().toLocaleDateString('zh-CN', {year:'numeric',month:'long',day:'numeric'});

  // 渲染饼图
  renderStatusChart(stats);
  // 渲染交易表
  renderTxTable(stats.recent_transactions);
}

function renderStatusChart(stats) {
  const ctx = document.getElementById('statusChart').getContext('2d');
  const labels = ['活跃', '已锁定', '永久解锁'];
  const colors = ['#059669', '#dc2626', '#f59e0b'];
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: [stats.active_devices, stats.locked_devices, stats.permanent_devices],
        backgroundColor: colors,
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyleWidth: 10 } } }
    }
  });
}

function renderTxTable(transactions) {
  const tbody = document.querySelector('#txTable tbody');
  if (transactions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:24px;">暂无交易记录</td></tr>';
    return;
  }
  tbody.innerHTML = transactions.map(t => `
    <tr>
      <td>${t.generated_at}</td>
      <td>${t.customer_name}</td>
      <td>$${t.amount.toFixed(2)}</td>
      <td>${t.days}天</td>
    </tr>
  `).join('');
}

// ---- 客户列表（原有逻辑保留，修改 selectCustomer 调用） ----
async function loadCustomers() { /* 原有实现不变 */ }

async function selectCustomer(id) {
  selectedCustomerId = id;
  await loadCustomers();
  // ... 原有客户详情渲染不变
}

// 其余所有函数保持不变：showAddCustomerModal, createCustomer, simulatePayment,
// showLockConfirm, showPermanentUnlockConfirm, showDeleteModal, confirmDelete,
// generateKeys, fillRandomKey, copyKey, closeModal, showToast
</script>
{% endblock %}
```

- [ ] **Step 3: 启动服务验证 UI**

```bash
source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
访问 `http://localhost:8000/dashboard`，验证：
- 默认显示仪表盘首页，KPI 卡片显示正确数据
- 饼图渲染正常（有数据时）
- 交易列表显示最近 Token 记录
- 点击左侧客户仍然跳转到客户详情

- [ ] **Step 4: Commit**

```bash
git add templates/dashboard.html templates/base.html
git commit -m "feat: 运营仪表盘首页 — KPI 卡片 + 设备状态饼图 + 最近交易列表"
```

---

### Task 4: 仪表盘 CSS 样式

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: 追加仪表盘专用 CSS**

```css
/* static/style.css — 末尾追加 */

/* 仪表盘首页 */
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}
.dash-header h2 { font-size: 20px; color: #0f172a; }
.dash-date { font-size: 13px; color: #94a3b8; }

/* KPI 卡片网格 */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 20px 24px;
}
.kpi-card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border-top: 3px solid;
}
.kpi-blue  { border-top-color: #3b82f6; }
.kpi-green { border-top-color: #059669; }
.kpi-gold  { border-top-color: #f59e0b; }
.kpi-red   { border-top-color: #dc2626; }
.kpi-value { font-size: 28px; font-weight: 700; color: #0f172a; }
.kpi-label { font-size: 13px; color: #64748b; margin-top: 4px; }

/* 图表 + 表格双栏 */
.dash-grid {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 16px;
  padding: 0 24px 24px;
}
.dash-chart-box, .dash-table-box {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.dash-chart-box h4, .dash-table-box h4 {
  font-size: 15px; color: #0f172a; margin-bottom: 16px;
}
.chart-wrap { height: 280px; position: relative; }

/* 交易表格 */
.tx-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.tx-table th {
  text-align: left; padding: 10px 12px; color: #64748b;
  font-weight: 600; border-bottom: 1px solid #e2e8f0;
}
.tx-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.tx-table tbody tr:hover { background: #f8fafc; }
```

- [ ] **Step 2: 启动服务验证样式**

访问 `http://localhost:8000/dashboard`，验证：
- KPI 卡片四列均匀分布，顶部彩色边框正确
- 饼图和表格并列排列
- 表格 hover 效果

- [ ] **Step 3: Commit**

```bash
git add static/style.css
git commit -m "style: 仪表盘首页 CSS — KPI 卡片 / 图表容器 / 交易表格样式"
```

---

## 验证清单

部署后逐项确认：

- [ ] 访问 `/dashboard`，未选择客户时默认显示仪表盘首页
- [ ] KPI 卡片显示正确的总客户数 / 活跃设备 / 本月收入 / 逾期锁定数
- [ ] 设备状态饼图用 Chart.js doughnut 渲染，颜色区分活跃/锁定/永久
- [ ] 最近交易列表显示 20 条最新 Token 记录
- [ ] 点击左侧客户名称仍然跳转到客户详情页
- [ ] 从客户详情页点击 sidebar 标题"客户列表"返回仪表盘首页
- [ ] 新增客户 + 模拟支付后，仪表盘数据实时更新
- [ ] 全部 109 个现有测试仍然通过
- [ ] 新增 2 个 dashboard API 测试通过

---

## 依赖关系

```
Task 1 (amount 字段) ──→ Task 2 (stats API) ──→ Task 3 (UI) ──→ Task 4 (CSS)
```
