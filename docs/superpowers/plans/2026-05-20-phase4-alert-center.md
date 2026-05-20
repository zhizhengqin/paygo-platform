# Phase 4: 告警中心 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新建告警中心模块，实现告警规则引擎/实时告警列表/处理工作流/工单升级/统计面板，与合同逾期检测联动。

**Architecture:** 新增 models（Alert/AlertRule/AlertLog），store 层（告警 CRUD + 规则引擎 + 升级逻辑），新 router（alerts.py），UI 新增「告警中心」Tab。逾期告警与 Phase 1 的 check_overdue_schedules 联动触发。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Jinja2, Chart.js

---

### Task 1: 数据模型 — Alert + AlertRule + AlertLog

**Files:**
- Modify: `app/models.py`
- Modify: `app/main.py` (ALTER TABLE)

- [ ] **Step 1: 在 models.py 新增 3 个模型**

在 `app/models.py` 的 RepaymentRecord 类之后添加：

```python
class AlertRule(Base):
    """告警规则"""
    __tablename__ = "alert_rules"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("AR"))
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(String(4), nullable=False, default="P2")  # P0/P1/P2
    sla_hours = Column(Integer, default=24)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())


class Alert(Base):
    """告警记录"""
    __tablename__ = "alerts"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("AL"))
    rule_code = Column(String(20), ForeignKey("alert_rules.code"), nullable=False)
    contract_id = Column(String(8), ForeignKey("contracts.id"), nullable=True)
    customer_id = Column(String(8), ForeignKey("customers.id"), nullable=True, index=True)
    level = Column(String(4), nullable=False, default="P2")
    status = Column(String(20), default="pending")  # pending/claimed/processing/closed
    title = Column(String(200), nullable=False)
    detail = Column(Text, nullable=True)
    triggered_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
    claimed_by = Column(String(100), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(Text, nullable=True)


class AlertLog(Base):
    """告警操作审计日志"""
    __tablename__ = "alert_logs"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("LG"))
    alert_id = Column(String(8), ForeignKey("alerts.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # triggered/claimed/processing/resolved/escalated
    operator = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
```

注意需要导入 `Boolean`：在 `app/models.py` 顶部 import 加 `Boolean`：
```python
from sqlalchemy import (
    Column, String, Integer, Numeric, Text, Date, DateTime, ForeignKey, JSON, Index, Boolean,
)
```

- [ ] **Step 2: 在 main.py 添加 ALTER TABLE**

```python
        # Phase 4 — 告警表
        await conn.run_sync(lambda c: c.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_rules (
                id VARCHAR(8) PRIMARY KEY, code VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL, description TEXT, level VARCHAR(4) DEFAULT 'P2',
                sla_hours INTEGER DEFAULT 24, enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )""")))
        await conn.run_sync(lambda c: c.execute(text("""
            CREATE TABLE IF NOT EXISTS alerts (
                id VARCHAR(8) PRIMARY KEY, rule_code VARCHAR(20) REFERENCES alert_rules(code),
                contract_id VARCHAR(8), customer_id VARCHAR(8),
                level VARCHAR(4) DEFAULT 'P2', status VARCHAR(20) DEFAULT 'pending',
                title VARCHAR(200) NOT NULL, detail TEXT,
                triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                claimed_by VARCHAR(100), claimed_at TIMESTAMP WITH TIME ZONE,
                resolved_at TIMESTAMP WITH TIME ZONE, resolution_note TEXT
            )""")))
        await conn.run_sync(lambda c: c.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_logs (
                id VARCHAR(8) PRIMARY KEY, alert_id VARCHAR(8) REFERENCES alerts(id),
                action VARCHAR(50) NOT NULL, operator VARCHAR(100),
                note TEXT, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )""")))
```

- [ ] **Step 3: 运行模型测试确认**

```bash
pytest tests/test_models.py -v
```

- [ ] **Step 4: 提交**

```bash
git add app/models.py app/main.py && git commit -m "feat: Alert/AlertRule/AlertLog models + migrations"
```

---

### Task 2: Store 层 — 告警 CRUD + 规则引擎 + 种子数据

**Files:**
- Modify: `app/store.py`
- Create: `tests/test_alert_store.py`

- [ ] **Step 1: 创建测试文件**

创建 `tests/test_alert_store.py`：

```python
"""告警 store 层测试"""
import secrets
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import Base
from app.settings import TEST_DATABASE_URL


def _key(): return secrets.token_hex(16)

@pytest.fixture(scope="function")
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
    await engine.dispose()

@pytest.fixture
async def session(engine, create_tables):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s


class TestAlertCRUD:
    async def _setup(self, session):
        from app.security import init_fernet; init_fernet()
        from app.store import seed_alert_rules, add_customer, add_loan_product, add_contract, approve_contract
        await seed_alert_rules(session)
        pid = await add_loan_product(session, "6kW", Decimal("6"), 12, Decimal("10"), Decimal("20"), Decimal("690"))
        cid = await add_customer(session, "AlertTest", "+8551", "DEV-AL1", "a"*32)
        ct_id = await add_contract(session, cid, pid, Decimal("138"), Decimal("552"), Decimal("46"), date(2025,1,1), date(2026,1,1))
        await approve_contract(session, ct_id)
        return cid, ct_id

    async def test_seed_alert_rules(self, session):
        """种子数据创建 3 条告警规则"""
        from app.store import seed_alert_rules, get_alert_rules
        await seed_alert_rules(session)
        rules = await get_alert_rules(session)
        assert len(rules) == 3

    async def test_create_alert(self, session):
        from app.store import seed_alert_rules, create_alert, get_alerts
        await seed_alert_rules(session)
        cid, ct_id = await self._setup(session)
        aid = await create_alert(session, rule_code="ALM-001", title="逾期未还款",
                                  contract_id=ct_id, customer_id=cid, detail="已逾期3天")
        assert aid.startswith("AL")
        alerts = await get_alerts(session)
        assert len(alerts) == 1
        assert alerts[0]["status"] == "pending"

    async def test_claim_and_resolve_alert(self, session):
        from app.store import seed_alert_rules, create_alert, claim_alert, resolve_alert, get_alert_detail
        await seed_alert_rules(session)
        cid, ct_id = await self._setup(session)
        aid = await create_alert(session, "ALM-001", "test", ct_id, cid)
        assert await claim_alert(session, aid, "admin")
        a = await get_alert_detail(session, aid)
        assert a["status"] == "claimed"
        assert a["claimed_by"] == "admin"
        assert await resolve_alert(session, aid, "已联系客户还款")
        a = await get_alert_detail(session, aid)
        assert a["status"] == "closed"

    async def test_escalate_alert(self, session):
        from app.store import seed_alert_rules, create_alert, escalate_alert, get_alert_detail
        await seed_alert_rules(session)
        cid, ct_id = await self._setup(session)
        aid = await create_alert(session, "ALM-002", "P1 test", ct_id, cid, level="P1")
        ok = await escalate_alert(session, aid)
        assert ok
        a = await get_alert_detail(session, aid)
        assert a["level"] == "P0"

    async def test_alert_stats(self, session):
        from app.store import seed_alert_rules, create_alert, get_alert_stats
        await seed_alert_rules(session)
        cid, ct_id = await self._setup(session)
        await create_alert(session, "ALM-001", "test", ct_id, cid)
        stats = await get_alert_stats(session)
        assert stats["total"] >= 1
        assert "today" in stats
```

- [ ] **Step 2: 确认测试失败**

```bash
pytest tests/test_alert_store.py -v 2>&1 | tail -5
```

- [ ] **Step 3: 实现 store.py 告警函数**

在 `app/store.py` 末尾追加（导入 Alert/AlertRule/AlertLog）：

```python
from app.models import Alert, AlertRule, AlertLog

# ============================================================
# 告警中心 — CRUD + 规则引擎 + 统计
# ============================================================

async def seed_alert_rules(db: AsyncSession):
    """种子告警规则（幂等）"""
    existing = await db.execute(select(func.count()).select_from(AlertRule))
    if existing.scalar() > 0: return
    db.add_all([
        AlertRule(id=_new_id("AR"), code="ALM-001", name="逾期未还款", level="P0", sla_hours=24,
                  description="合同还款到期超过3天未付"),
        AlertRule(id=_new_id("AR"), code="ALM-002", name="设备通信失联", level="P1", sla_hours=48,
                  description="设备超过72小时无心跳"),
        AlertRule(id=_new_id("AR"), code="ALM-003", name="Token验证异常", level="P2", sla_hours=72,
                  description="同一设备连续3次Token验证失败"),
    ])
    await db.commit()


async def get_alert_rules(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(AlertRule).order_by(AlertRule.code))
    return [{"id": r.id, "code": r.code, "name": r.name, "level": r.level,
             "sla_hours": r.sla_hours, "enabled": r.enabled} for r in result.scalars().all()]


async def create_alert(db: AsyncSession, rule_code: str, title: str,
                       contract_id: str = None, customer_id: str = None,
                       detail: str = None, level: str = "P0") -> str:
    aid = _new_id("AL")
    a = Alert(id=aid, rule_code=rule_code, title=title, detail=detail,
              contract_id=contract_id, customer_id=customer_id, level=level,
              status="pending", triggered_at=datetime.now())
    db.add(a)
    log = AlertLog(id=_new_id("LG"), alert_id=aid, action="triggered",
                   note=f"规则 {rule_code} 触发告警")
    db.add(log)
    await db.commit()
    return aid


async def get_alerts(db: AsyncSession, status: str = None, level: str = None) -> list[dict]:
    q = select(Alert).order_by(
        Alert.level.desc() if hasattr(Alert.level, 'desc') else Alert.triggered_at.desc()
    )
    if status: q = q.where(Alert.status == status)
    if level: q = q.where(Alert.level == level)
    result = await db.execute(q.order_by(Alert.triggered_at.desc()).limit(100))
    alerts = result.scalars().all()
    # P0 > P1 > P2 排序
    level_order = {"P0": 0, "P1": 1, "P2": 2}
    alerts_sorted = sorted(alerts, key=lambda a: (level_order.get(a.level, 9), a.triggered_at), reverse=False)
    # Actually: P0 first, then by time desc
    def sort_key(a):
        return (level_order.get(a.level, 9), -(a.triggered_at.timestamp() if a.triggered_at else 0))
    alerts_sorted = sorted(alerts, key=sort_key)
    return [_alert_to_dict(a) for a in alerts_sorted]


async def get_alert_detail(db: AsyncSession, aid: str) -> dict | None:
    a = await db.get(Alert, aid)
    if not a: return None
    d = _alert_to_dict(a)
    # 附加日志
    logs_result = await db.execute(
        select(AlertLog).where(AlertLog.alert_id == aid).order_by(AlertLog.created_at)
    )
    d["logs"] = [{"action": l.action, "operator": l.operator, "note": l.note,
                  "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else None}
                 for l in logs_result.scalars().all()]
    return d


async def claim_alert(db: AsyncSession, aid: str, operator: str) -> bool:
    a = await db.get(Alert, aid)
    if not a or a.status != "pending": return False
    a.status = "claimed"; a.claimed_by = operator; a.claimed_at = datetime.now()
    log = AlertLog(id=_new_id("LG"), alert_id=aid, action="claimed", operator=operator)
    db.add(log)
    await db.commit()
    return True


async def resolve_alert(db: AsyncSession, aid: str, note: str = "") -> bool:
    a = await db.get(Alert, aid)
    if not a or a.status not in ("claimed", "processing"): return False
    a.status = "closed"; a.resolved_at = datetime.now(); a.resolution_note = note
    log = AlertLog(id=_new_id("LG"), alert_id=aid, action="resolved", note=note)
    db.add(log)
    await db.commit()
    return True


async def escalate_alert(db: AsyncSession, aid: str) -> bool:
    a = await db.get(Alert, aid)
    if not a: return False
    new_level = "P1" if a.level == "P2" else "P0"
    a.level = new_level
    log = AlertLog(id=_new_id("LG"), alert_id=aid, action="escalated",
                   note=f"升级至 {new_level}")
    db.add(log)
    await db.commit()
    return True


async def get_alert_stats(db: AsyncSession) -> dict:
    from datetime import date
    today = date.today()
    total_r = await db.execute(select(func.count()).select_from(Alert))
    today_r = await db.execute(select(func.count()).select_from(Alert).where(
        func.date(Alert.triggered_at) == today))
    pending_r = await db.execute(select(func.count()).select_from(Alert).where(
        Alert.status == "pending"))
    closed_r = await db.execute(select(func.count()).select_from(Alert).where(
        Alert.status == "closed"))
    return {"total": total_r.scalar() or 0, "today": today_r.scalar() or 0,
            "pending": pending_r.scalar() or 0, "closed": closed_r.scalar() or 0}


def _alert_to_dict(a: Alert) -> dict:
    return {"id": a.id, "rule_code": a.rule_code, "title": a.title, "detail": a.detail,
            "level": a.level, "status": a.status,
            "contract_id": a.contract_id, "customer_id": a.customer_id,
            "claimed_by": a.claimed_by, "claimed_at": a.claimed_at.strftime("%Y-%m-%d %H:%M:%S") if a.claimed_at else None,
            "resolved_at": a.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if a.resolved_at else None,
            "resolution_note": a.resolution_note,
            "triggered_at": a.triggered_at.strftime("%Y-%m-%d %H:%M:%S") if a.triggered_at else None}
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_alert_store.py -v
```
Expected: 6 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/store.py tests/test_alert_store.py && git commit -m "feat: store — alert CRUD + rules engine + stats"
```

---

### Task 3: API — 告警中心 router

**Files:**
- Create: `app/routers/alerts.py`
- Modify: `app/main.py`
- Create: `tests/test_alerts_api.py`

- [ ] **Step 1: 创建 tests/test_alerts_api.py** 6 个测试（stats/list/detail/claim/resolve/escalate）

- [ ] **Step 2: 创建 app/routers/alerts.py** 6 个端点

```python
router = APIRouter(prefix="/api/alerts")

@router.get("/stats")          # 统计
@router.get("")                # 列表（?status=&level=）
@router.get("/{aid}")          # 详情（含日志）
@router.post("/{aid}/claim")   # 认领
@router.post("/{aid}/resolve") # 解决 {note: str}
@router.post("/{aid}/escalate")# 升级
```

- [ ] **Step 3: 注册 router 到 main.py**

- [ ] **Step 4: 运行测试 → 提交**

```bash
pytest tests/test_alerts_api.py -v
git add app/routers/alerts.py app/main.py tests/test_alerts_api.py && git commit -m "feat: API — alert center router with stats/list/detail/claim/resolve/escalate"
```

---

### Task 4: UI — 新增「告警中心」Tab + 联动逾期检测

**Files:**
- Modify: `templates/base.html`
- Modify: `templates/dashboard.html`

- [ ] **Step 1: base.html 添加 tab**

```html
<a class="nav-tab" data-tab="alerts" onclick="switchTab('alerts')">告警中心</a>
```

- [ ] **Step 2: dashboard.html 添加告警 UI**

在 `switchTab` 添加 `alerts` 分支，新建 JS 函数：
- `loadAlerts()` — 加载告警列表 + 统计卡片
- `selectAlert(aid)` — 告警详情（含日志时间线 + 操作按钮）
- `claimAlert(aid)` / `resolveAlert(aid)` / `escalateAlert(aid)`

告警列表按 P0(红) > P1(黄) > P2(蓝) 颜色区分，统计卡片显示总数/今日/待处理/已关闭。

- [ ] **Step 4: 提交**

```bash
git add templates/base.html templates/dashboard.html && git commit -m "feat: UI — alert center tab with list/detail/claim/resolve/escalate"
```

---

### Task 5: 全量回归 + 修复

```bash
pytest tests/ -q
```
Expected: ~202 tests PASS

---

### Task 6: 冒烟测试
启动应用，验证告警中心 Tab：生成告警 → 认领 → 解决 → 升级
