# Phase 1: 合同管理补完 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 走通「签合同 → 按期还款 → Token 下发 → 逾期锁定 → 结清解锁」完整业务闭环

**Architecture:** 新增 `repayment_records` 表记录实际还款（关联 schedule + token），store 层新增还款标记/逾期检测/结清逻辑，API 层新增对应端点，UI 层增强合同详情展示还款进度条和操作按钮。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Chart.js, Jinja2

---

### Task 1: 数据模型变更 — repayment_records 表 + tokens 关联

**Files:**
- Modify: `app/models.py`
- Modify: `app/main.py` (ALTER TABLE migration)
- Test: `tests/test_contract_models.py`

- [ ] **Step 1: 写模型测试**

在 `tests/test_contract_models.py` 追加：

```python
from app.models import RepaymentRecord, Token

class TestRepaymentRecord:
    async def test_create_repayment_record(self, db_session):
        """创建还款记录，关联 schedule 和 token"""
        from app.models import _new_id, Customer, LoanProduct, Contract, RepaymentSchedule
        from app.security import init_fernet, encrypt_secret
        init_fernet()

        # 创建依赖数据
        c = Customer(id=_new_id("C"), name="T", phone="1", device_id="D1",
                     secret_key_encrypted=encrypt_secret("a"*32))
        lp = LoanProduct(id=_new_id("LP"), name="LP", capacity_kw=6, term_months=12,
                        interest_rate=10, down_payment_pct=20, total_amount=690)
        ct = Contract(id=_new_id("CT"), contract_no="KH-2026-00001", customer_id=c.id,
                     product_id=lp.id, down_payment=138, loan_amount=552,
                     monthly_payment=46, start_date=date(2026,1,1), end_date=date(2027,1,1))
        rs = RepaymentSchedule(id=_new_id("RS"), contract_id=ct.id, period_no=1,
                              due_date=date(2026,2,1), principal=34.11, interest=9.20,
                              total=43.31, balance=517.89)
        t = Token(id=_new_id("T"), customer_id=c.id, token="123456789", days=30, count=1)
        db_session.add_all([c, lp, ct, rs, t])
        await db_session.commit()

        rr = RepaymentRecord(
            id=_new_id("RR"),
            contract_id=ct.id,
            schedule_id=rs.id,
            token_id=t.id,
            amount=Decimal("43.31"),
            payment_method="Bakong",
        )
        db_session.add(rr)
        await db_session.commit()

        assert rr.id.startswith("RR")
        assert rr.amount == Decimal("43.31")
        assert rr.payment_method == "Bakong"
        assert rr.paid_at is not None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_contract_models.py::TestRepaymentRecord -v 2>&1 | tail -5
```
Expected: FAIL

- [ ] **Step 3: 修改 models.py — 新增 RepaymentRecord + tokens 外键**

在 `app/models.py` 的 Token 类中新增字段（在 `amount` 之后）：
```python
    contract_id = Column(String(8), ForeignKey("contracts.id"), nullable=True, index=True)
```

在 `RepaymentSchedule` 类之后新增 `RepaymentRecord`:
```python
class RepaymentRecord(Base):
    """实际还款记录"""
    __tablename__ = "repayment_records"

    id = Column(String(8), primary_key=True, default=lambda: _new_id("RR"))
    contract_id = Column(String(8), ForeignKey("contracts.id"), nullable=False, index=True)
    schedule_id = Column(String(8), ForeignKey("repayment_schedules.id"), nullable=False)
    token_id = Column(String(8), ForeignKey("tokens.id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(20), default="Bakong")
    paid_at = Column(DateTime(timezone=True), default=lambda: datetime.now())
```

- [ ] **Step 4: 修改 main.py — 添加 ALTER TABLE 迁移**

在 `app/main.py` 的 lifespan 中添加：
```python
        await conn.run_sync(lambda c: c.execute(text(
            "ALTER TABLE tokens ADD COLUMN IF NOT EXISTS contract_id VARCHAR(8)"
        )))
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_contract_models.py -v
```
Expected: all tests PASS

- [ ] **Step 6: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add app/models.py app/main.py tests/test_contract_models.py && git commit -m "feat: add RepaymentRecord model + tokens.contract_id FK"
```

---

### Task 2: Store 层 — 还款标记 + 逾期检测 + 结清

**Files:**
- Modify: `app/store.py`
- Test: `tests/test_contract_store.py`

- [ ] **Step 1: 写 store 层测试**

在 `tests/test_contract_store.py` 追加：

```python
from app.models import RepaymentRecord
from app.store import (
    mark_schedule_paid, check_overdue_schedules, settle_contract,
)

class TestRepaymentFlow:
    """还款闭环测试"""

    async def test_mark_schedule_paid_generates_token_and_record(self, session):
        """标记一期还款为已付：创建还款记录 + 生成 Token + 更新计划状态"""
        from app.security import init_fernet
        init_fernet()

        pid = await add_loan_product(
            session, "6kW-12月", Decimal("6.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("690.00"),
        )
        cid = await add_customer(session, "Test", "+855111", "DEV-T1", "a" * 32)
        ct_id = await add_contract(
            session, cid, pid, Decimal("138.00"), Decimal("552.00"),
            Decimal("46.00"), date(2026, 1, 1), date(2027, 1, 1),
        )
        result = await approve_contract(session, ct_id)
        schedule_id = result["schedules"][0]["id"]

        rr = await mark_schedule_paid(session, schedule_id, amount=Decimal("43.31"))
        assert rr is not None
        assert rr["schedule_id"] == schedule_id
        assert rr["amount"] == 43.31
        assert rr["token"] is not None  # Token 自动生成
        assert len(rr["token"]) == 9  # OpenPAYGO 9-digit token

        # 验证计划状态变化
        from app.store import get_contract_with_schedules
        ct = await get_contract_with_schedules(session, ct_id)
        assert ct["schedules"][0]["status"] == "paid"

    async def test_mark_schedule_paid_already_paid_returns_none(self, session):
        """已还款的期数不可重复还款"""
        from app.security import init_fernet
        init_fernet()

        pid = await add_loan_product(
            session, "6kW-12月", Decimal("6.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("690.00"),
        )
        cid = await add_customer(session, "Test2", "+855222", "DEV-T2", "a" * 32)
        ct_id = await add_contract(
            session, cid, pid, Decimal("138.00"), Decimal("552.00"),
            Decimal("46.00"), date(2026, 1, 1), date(2027, 1, 1),
        )
        result = await approve_contract(session, ct_id)
        schedule_id = result["schedules"][0]["id"]

        rr1 = await mark_schedule_paid(session, schedule_id, amount=Decimal("43.31"))
        assert rr1 is not None
        rr2 = await mark_schedule_paid(session, schedule_id, amount=Decimal("43.31"))
        assert rr2 is None

    async def test_check_overdue_finds_unpaid_past_due(self, session):
        """逾期检测：到期未付的计划被标记为 overdue，合同和设备状态联动"""
        from app.security import init_fernet
        init_fernet()

        pid = await add_loan_product(
            session, "6kW-12月", Decimal("6.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("690.00"),
        )
        cid = await add_customer(session, "Test3", "+855333", "DEV-T3", "a" * 32)
        ct_id = await add_contract(
            session, cid, pid, Decimal("138.00"), Decimal("552.00"),
            Decimal("46.00"), date(2025, 1, 1), date(2026, 1, 1),
            # 历史合同，所有期数都过期了
        )
        await approve_contract(session, ct_id)

        count = await check_overdue_schedules(session)
        assert count > 0

        # 验证合同状态
        from app.store import get_contract
        ct = await get_contract(session, ct_id)
        assert ct["status"] == "overdue"

    async def test_settle_contract_generates_disable_token(self, session):
        """结清合同：生成 DISABLE_PAYG Token，设备永久解锁"""
        from app.security import init_fernet
        init_fernet()

        pid = await add_loan_product(
            session, "6kW-12月", Decimal("6.00"), 12,
            Decimal("10.00"), Decimal("20.00"), Decimal("690.00"),
        )
        cid = await add_customer(session, "Test4", "+855444", "DEV-T4", "a" * 32)
        ct_id = await add_contract(
            session, cid, pid, Decimal("138.00"), Decimal("552.00"),
            Decimal("46.00"), date(2026, 1, 1), date(2027, 1, 1),
        )
        await approve_contract(session, ct_id)

        result = await settle_contract(session, ct_id)
        assert result is not None
        assert result["status"] == "closed"
        assert result["token"] is not None
        assert "永久" in result["sms"]["message"] or "DISABLE" in str(result)

        # 验证客户状态
        from app.store import get_customer
        c = await get_customer(session, cid)
        assert c["status"] == "permanent"
```

- [ ] **Step 2: 确认测试失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_contract_store.py::TestRepaymentFlow -v 2>&1 | tail -5
```
Expected: FAIL — functions not defined

- [ ] **Step 3: 实现 store.py 新增函数**

在 `app/store.py` 末尾追加：

```python
# ============================================================
# 还款记录 CRUD + 还款标记 + 逾期检测 + 结清
# ============================================================

async def mark_schedule_paid(
    db: AsyncSession, schedule_id: str, amount: Decimal,
) -> dict | None:
    """标记一期还款为已付：检查状态 → 生成 Token → 创建还款记录 → 更新计划状态"""
    rs_result = await db.execute(
        select(RepaymentSchedule).where(RepaymentSchedule.id == schedule_id)
    )
    rs = rs_result.scalar()
    if not rs or rs.status == "paid":
        return None

    # 获取合同和客户信息
    ct = await db.get(Contract, rs.contract_id)
    if not ct:
        return None
    customer = await db.get(Customer, ct.customer_id)
    if not customer:
        return None

    raw_key = None
    if customer.secret_key_encrypted:
        raw_key = decrypt_secret(customer.secret_key_encrypted)
    elif customer.secret_key:
        raw_key = customer.secret_key
    if not raw_key:
        return None

    # 生成 ADD_TIME Token
    from openpaygo import generate_token, TokenType
    new_count, token_str = generate_token(
        secret_key=raw_key,
        count=customer.count,
        value=30,  # 每期还款增加30天
        token_type=TokenType.ADD_TIME,
    )

    # 更新客户 counter
    customer.count = new_count
    customer.status = "active"

    # 创建 Token 记录
    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer.id, token=token_str, days=30,
        count=new_count, amount=amount, contract_id=ct.id,
    )
    db.add(t)

    # 创建还款记录
    rrid = _new_id("RR")
    rr = RepaymentRecord(
        id=rrid, contract_id=ct.id, schedule_id=rs.id, token_id=tid,
        amount=amount, payment_method="Bakong",
    )
    db.add(rr)

    # 更新还款计划状态
    rs.status = "paid"

    await db.commit()

    return {
        "id": rrid,
        "contract_id": ct.id,
        "schedule_id": rs.id,
        "token_id": tid,
        "token": token_str,
        "amount": float(amount),
        "paid_at": rr.paid_at.strftime("%Y-%m-%d %H:%M:%S") if rr.paid_at else None,
    }


async def check_overdue_schedules(db: AsyncSession) -> int:
    """检查逾期未付的还款计划，标记为 overdue 并更新合同状态。返回逾期条数。"""
    from datetime import date
    today = date.today()

    result = await db.execute(
        select(RepaymentSchedule).where(
            RepaymentSchedule.status == "pending",
            RepaymentSchedule.due_date < today,
        )
    )
    overdue_schedules = result.scalars().all()

    affected_contracts = set()
    for rs in overdue_schedules:
        rs.status = "overdue"
        affected_contracts.add(rs.contract_id)

    # 更新对应合同状态
    for ct_id in affected_contracts:
        ct = await db.get(Contract, ct_id)
        if ct and ct.status == "active":
            ct.status = "overdue"
            # 联动锁定设备
            customer = await db.get(Customer, ct.customer_id)
            if customer:
                customer.status = "locked"
                customer.locked_at = datetime.now()

    if overdue_schedules:
        await db.commit()

    return len(overdue_schedules)


async def settle_contract(db: AsyncSession, cid: str) -> dict | None:
    """结清合同：标记所有未付计划为已付 → 生成 DISABLE_PAYG Token → 永久解锁"""
    ct = await db.get(Contract, cid)
    if not ct or ct.status not in ("active", "overdue"):
        return None

    customer = await db.get(Customer, ct.customer_id)
    if not customer:
        return None

    raw_key = None
    if customer.secret_key_encrypted:
        raw_key = decrypt_secret(customer.secret_key_encrypted)
    elif customer.secret_key:
        raw_key = customer.secret_key
    if not raw_key:
        return None

    # 生成 DISABLE_PAYG Token
    from openpaygo import generate_token, TokenType
    new_count, token_str = generate_token(
        secret_key=raw_key,
        count=customer.count,
        token_type=TokenType.DISABLE_PAYG,
    )

    # 更新客户状态
    customer.count = new_count
    customer.status = "permanent"

    # 创建 Token 记录
    tid = _new_id("T")
    t = Token(
        id=tid, customer_id=customer.id, token=token_str, days=-1,
        count=new_count, amount=0, contract_id=ct.id,
    )
    db.add(t)

    # 标记所有未付计划为已付
    schedules_result = await db.execute(
        select(RepaymentSchedule).where(
            RepaymentSchedule.contract_id == cid,
            RepaymentSchedule.status != "paid",
        )
    )
    for rs in schedules_result.scalars():
        rs.status = "paid"

    # 创建还款记录
    rrid = _new_id("RR")
    rr = RepaymentRecord(
        id=rrid, contract_id=ct.id, token_id=tid,
        amount=ct.loan_amount, payment_method="SETTLEMENT",
    )
    db.add(rr)

    # 更新合同状态
    ct.status = "closed"
    ct.remaining_days = 0

    # 构造 SMS 消息
    from app.store import _new_id
    message = (
        f"[PAYGO Solar] 恭喜！您的贷款已全部结清。"
        f"设备永久解锁码：{token_str}。请在您的设备中输入此码以永久解锁。"
    )
    await db.commit()

    return {
        "contract_id": cid,
        "status": "closed",
        "token": token_str,
        "sms": {"to": "SIMULATED", "message": message},
    }
```

- [ ] **Step 4: 添加 sms_record 到结清流程**

结清时记录 SMS：
```python
    # 在 settle_contract 中 await db.commit() 之前添加：
    sms_id = _new_id("S")
    sms = SmsRecord(id=sms_id, customer_id=customer.id, to_phone=customer.phone, message=message)
    db.add(sms)
```

注意需要在函数内导入 SmsRecord。

- [ ] **Step 5: 运行 store 测试确认通过**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_contract_store.py -v
```
Expected: 21 tests PASS (17 existing + 4 new)

- [ ] **Step 6: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add app/store.py tests/test_contract_store.py && git commit -m "feat: store — repayment marking + overdue check + contract settlement"
```

---

### Task 3: API 端点 — 还款 / 逾期检测 / 结清

**Files:**
- Modify: `app/routers/contracts.py`
- Test: `tests/test_contracts_api.py`

- [ ] **Step 1: 写 API 测试**

在 `tests/test_contracts_api.py` 追加：

```python
@pytest.mark.asyncio
async def test_pay_schedule(auth_client):
    """还款一期 → 生成 Token"""
    import secrets
    # 创建客户
    resp = await auth_client.post("/api/customers", json={
        "name": "Pay Test", "phone": "010000100",
        "device_id": f"DEV-{secrets.token_hex(3)}",
        "secret_key": secrets.token_hex(16),
    })
    cid = resp.json()["id"]

    # 创建合同
    products = (await auth_client.get("/api/loan-products")).json()
    c_resp = await auth_client.post("/api/contracts", json={
        "customer_id": cid, "product_id": products[0]["id"],
    })
    ct_id = c_resp.json()["id"]

    # 审批
    approved = (await auth_client.put(f"/api/contracts/{ct_id}/approve")).json()
    schedule_id = approved["schedules"][0]["id"]

    # 还款
    resp = await auth_client.post(
        f"/api/contracts/{ct_id}/pay",
        json={"schedule_id": schedule_id, "amount": approved["schedules"][0]["total"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] is not None
    assert len(data["token"]) == 9


@pytest.mark.asyncio
async def test_check_overdue(auth_client):
    """检查逾期 — 返回逾期条数"""
    resp = await auth_client.post("/api/contracts/check-overdue")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data


@pytest.mark.asyncio
async def test_settle_contract(auth_client):
    """结清合同 → 永久解锁"""
    import secrets
    resp = await auth_client.post("/api/customers", json={
        "name": "Settle Test", "phone": "010000200",
        "device_id": f"DEV-{secrets.token_hex(3)}",
        "secret_key": secrets.token_hex(16),
    })
    cid = resp.json()["id"]

    products = (await auth_client.get("/api/loan-products")).json()
    c_resp = await auth_client.post("/api/contracts", json={
        "customer_id": cid, "product_id": products[0]["id"],
    })
    ct_id = c_resp.json()["id"]

    # 审批通过
    await auth_client.put(f"/api/contracts/{ct_id}/approve")

    # 结清
    resp = await auth_client.post(f"/api/contracts/{ct_id}/settle")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "closed"
    assert data["token"] is not None
```

- [ ] **Step 2: 确认新测试失败**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_contracts_api.py::test_pay_schedule -v 2>&1 | tail -5
```
Expected: FAIL (404 or function not found)

- [ ] **Step 3: 在 contracts.py 添加 API 端点**

在 `app/routers/contracts.py` 末尾追加（在 import 中加入新依赖）：

新增 import：
```python
from decimal import Decimal
from app.store import mark_schedule_paid, check_overdue_schedules, settle_contract
```

新增请求体模型：
```python
class ContractPay(BaseModel):
    schedule_id: str
    amount: float
```

新增端点：
```python
@router.post("/contracts/{cid}/pay")
async def api_pay_schedule(cid: str, body: ContractPay, request: Request,
                           db: AsyncSession = Depends(get_db)):
    """还款一期：标记还款计划为已付 + 生成 Token"""
    await _check_auth(request)
    result = await mark_schedule_paid(db, body.schedule_id, Decimal(str(body.amount)))
    if not result:
        raise HTTPException(400, "还款失败（计划不存在或已付）")
    return result


@router.post("/contracts/check-overdue")
async def api_check_overdue(request: Request, db: AsyncSession = Depends(get_db)):
    """手动触发逾期检测"""
    await _check_auth(request)
    count = await check_overdue_schedules(db)
    return {"count": count}


@router.post("/contracts/{cid}/settle")
async def api_settle_contract(cid: str, request: Request,
                              db: AsyncSession = Depends(get_db)):
    """结清合同 → DISABLE_PAYG + 永久解锁"""
    await _check_auth(request)
    result = await settle_contract(db, cid)
    if not result:
        raise HTTPException(400, "结清失败（合同不存在或状态不正确）")
    return result
```

- [ ] **Step 4: 运行 API 测试**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/test_contracts_api.py -v
```
Expected: 9 tests PASS (6 existing + 3 new)

- [ ] **Step 5: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add app/routers/contracts.py tests/test_contracts_api.py && git commit -m "feat: API — contract pay/overdue-check/settle endpoints"
```

---

### Task 4: UI 增强 — 还款进度条 + 操作按钮

**Files:**
- Modify: `templates/dashboard.html`

- [ ] **Step 1: 增强合同详情 — 还款进度条 + 还款按钮**

在 `selectContract` 函数中，合同操作的 `btn-group` 部分（约 line 600），替换为：

在现有操作按钮区域添加还款进度可视化和还款操作。找到合同状态操作区，在当前 `approveContract` 按钮之后添加：

```javascript
// 在 selectContract 函数中，schedules 渲染之前添加进度计算
const paidCount = c.schedules ? c.schedules.filter(s => s.status === 'paid').length : 0;
const totalCount = c.schedules ? c.schedules.length : 0;
const progressPct = totalCount > 0 ? Math.round(paidCount / totalCount * 100) : 0;
```

在还款计划表之前添加进度条和快捷还款区：

```html
<div class="detail-section">
  <h4>还款进度 ${totalCount > 0 ? '(' + paidCount + '/' + totalCount + ' 期)' : ''}</h4>
  <div style="background:#e2e8f0;border-radius:8px;height:24px;overflow:hidden;margin:8px 0;">
    <div style="width:${progressPct}%;height:100%;background:linear-gradient(90deg,#059669,#10b981);border-radius:8px;transition:width 0.4s;">
    </div>
  </div>
  <span style="font-size:12px;color:#64748b;">${progressPct}% 已完成</span>
</div>
```

在操作区添加：
```html
${c.status === 'active' ? `
  <div class="detail-section">
    <h4>模拟还款</h4>
    <p style="color:#94a3b8;font-size:12px;margin-bottom:10px;">选择待还期数进行模拟还款</p>
    <div class="btn-group" style="flex-wrap:wrap;">
      ${c.schedules ? c.schedules.filter(s => s.status === 'pending').slice(0,3).map(s => 
        '<button class="btn btn-primary btn-sm" onclick="paySchedule(\'' + c.id + '\',\'' + s.id + '\',' + s.total + ')">第' + s.period_no + '期 $' + s.total.toFixed(2) + '</button>'
      ).join('') : ''}
    </div>
  </div>
` : ''}
```

- [ ] **Step 2: 添加 JS 函数 — paySchedule**

在 dashboard.html 的 JS 区域添加：

```javascript
async function paySchedule(contractId, scheduleId, amount) {
  const resp = await fetch('/api/contracts/' + encodeURIComponent(contractId) + '/pay', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({schedule_id: scheduleId, amount: amount})
  });
  if (!resp.ok) {
    const err = await resp.json();
    showToast('还款失败: ' + (err.detail || ''));
    return;
  }
  const data = await resp.json();
  // 展示 Token 结果弹窗
  document.getElementById('tokenResultTitle').textContent = '还款成功 - 激活码已生成';
  document.getElementById('tokenCode').textContent = data.token;
  document.getElementById('smsTo').textContent = 'SIMULATED';
  document.getElementById('smsBody').textContent = 
    '[PAYGO Solar] 您已成功还款 $' + amount.toFixed(2) + '。激活码：' + data.token + '。有效期30天。';
  document.getElementById('tokenResultModal').classList.add('show');
  // 刷新合同详情
  setTimeout(() => selectContract(contractId), 500);
}

async function settleContract(contractId) {
  if (!confirm('确定要结清此合同？将生成永久解锁码。')) return;
  const resp = await fetch('/api/contracts/' + encodeURIComponent(contractId) + '/settle', {
    method: 'POST'
  });
  if (!resp.ok) {
    const err = await resp.json();
    showToast('结清失败: ' + (err.detail || ''));
    return;
  }
  const data = await resp.json();
  document.getElementById('tokenResultTitle').textContent = '合同已结清 - 永久解锁码';
  document.getElementById('tokenCode').textContent = data.token;
  document.getElementById('smsTo').textContent = 'SIMULATED';
  document.getElementById('smsBody').textContent = data.sms.message;
  document.getElementById('tokenResultModal').classList.add('show');
  setTimeout(() => selectContract(contractId), 500);
}

async function checkOverdue() {
  const resp = await fetch('/api/contracts/check-overdue', { method: 'POST' });
  const data = await resp.json();
  showToast('检测到 ' + data.count + ' 条逾期计划');
  if (selectedContractId) selectContract(selectedContractId);
}
```

- [ ] **Step 3: 在合同操作区添加结清和逾期检测按钮**

在现有操作按钮区域，`${c.status === 'active' || c.status === 'overdue' ?` 条件中，添加结清按钮：

```html
${(c.status === 'active' || c.status === 'overdue') ? 
  '<button class="btn btn-success btn-sm" onclick="settleContract(\'' + c.id + '\')">提前结清</button>' +
  '<button class="btn btn-danger btn-sm" onclick="closeContract(\'' + c.id + '\')">结清/回收</button>'
: ''}
```

在操作区底部添加：
```html
<button class="btn btn-outline btn-sm" onclick="checkOverdue()">🔄 检测逾期</button>
```

- [ ] **Step 4: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add templates/dashboard.html && git commit -m "feat: UI — contract repayment progress bar + pay/settle buttons"
```

---

### Task 5: 全量回归测试 + 修复

**Files:**
- Modify: 根据测试失败情况修复

- [ ] **Step 1: 运行全部测试**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/ -v 2>&1 | tail -30
```

- [ ] **Step 2: 修复失败测试**

逐项检查并修复。可能需要：
- 确保 `test_contract_store.py` 中的 `TestRepaymentFlow` 正确初始化 Fernet
- 确保 API 测试中客户创建时 secret_key 足够长
- 检查 `mark_schedule_paid` 中的 `generate_token` 调用参数正确

- [ ] **Step 3: 确认全部通过**

```bash
cd /Users/qinzz/Desktop/paygo-platform && source venv/bin/activate && pytest tests/ -q
```
Expected: ~172 tests PASS (157 existing + 15 new)

- [ ] **Step 4: 提交**

```bash
cd /Users/qinzz/Desktop/paygo-platform && git add -A && git commit -m "fix: full regression — Phase 1 contract repayment loop complete"
```

---

### Task 6: 冒烟测试 — 手动验证闭环

- [ ] **Step 1: 启动应用**

```bash
source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 验证完整闭环**

1. 登录 admin/admin123
2. 创建客户（随机密钥）
3. 切换到"合同管理" → 创建新合同（选一个贷款产品）
4. 审批通过 → 应看到还款计划表
5. 点击第1期"还款"按钮 → 应生成 Token 并弹窗
6. 观察还款进度条变化 → 应显示 1/N
7. 点击"提前结清" → 应生成永久解锁码
8. 点击"检测逾期" → 应返回逾期计数

- [ ] **Step 3: 验证数据一致性**

检查数据库确认：
- `repayment_records` 有对应记录
- `repayment_schedules` 状态变为 paid
- `tokens.contract_id` 关联正确
- 客户 status 在结清后变为 permanent
