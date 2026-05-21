"""演示数据初始化 — 8 客户 × 7 合同 × 3 MFI × 3 告警 × 完整状态覆盖"""
import asyncio
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import delete, text

from app.database import engine, AsyncSessionLocal
from app.models import Customer, Token, SmsRecord, PaymentRate, Contract, LoanProduct, RepaymentSchedule, Mfi, Alert, AlertRule
from app.store import (
    add_customer, set_customer_count, update_customer_status,
    add_loan_product, add_contract, approve_contract,
    update_contract_status, add_token, mark_schedule_paid,
    seed_payment_rates, seed_loan_products, seed_alert_rules,
    add_mfi, update_customer_tags, migrate_secret_keys_to_encrypted,
)


async def main():
    async with engine.begin() as conn:
        # 清空数据（按 FK 依赖顺序）
        for tbl in ["alert_logs", "alerts", "repayment_schedules", "repayment_records",
                     "contracts", "tokens", "sms_records", "payment_rates",
                     "loan_products", "customers", "device_states",
                     "alert_rules", "mfis", "users", "sms_templates"]:
            await conn.execute(text(f"DELETE FROM {tbl}"))

    async with AsyncSessionLocal() as db:
        # ── MFI ──
        mfi_lolc = await add_mfi(db, "LOLC Cambodia", "Phnom Penh")
        mfi_prasac = await add_mfi(db, "PRASAC", "Siem Reap")
        mfi_acleda = await add_mfi(db, "ACLEDA Bank", "Phnom Penh")

        # ── 贷款产品 ──
        await seed_loan_products(db)
        prods_result = await db.execute(text("SELECT id, capacity_kw FROM loan_products ORDER BY capacity_kw"))
        prod_map = {float(r[1]): r[0] for r in prods_result.fetchall()}

        # ── 支付汇率 ──
        await seed_payment_rates(db)
        # 额外汇率档位
        db.add_all([
            PaymentRate(amount=20, days=120),
            PaymentRate(amount=50, days=365),
        ])
        await db.commit()

        # ── 告警规则 ──
        await seed_alert_rules(db)

        # ── 辅助函数 ──
        async def make_customer(name, phone, device, key_hex, status, gps, addr, mfi_id, tags):
            cid = await add_customer(db, name, phone, device, key_hex)
            c = await db.get(Customer, cid)
            c.gps_latitude, c.gps_longitude = gps
            c.address = addr
            c.mfi_id = mfi_id
            if tags:
                await update_customer_tags(db, cid, tags)
            if status != "locked":
                await update_customer_status(db, cid, status)
            else:
                c.status = "locked"
                c.locked_at = datetime.now()
            await db.commit()
            return cid

        async def make_contract(cid, prod_kw, down, loan, monthly, start, end, status):
            pid = prod_map[prod_kw]
            ct_id = await add_contract(db, cid, pid, down, loan, monthly, start, end)
            if status != "draft":
                await approve_contract(db, ct_id)
                if status in ("overdue", "closed", "recovered"):
                    await update_contract_status(db, ct_id, status)
            return ct_id

        async def pay_schedule(ct_id, cid, schedule_id, amount):
            await mark_schedule_paid(db, schedule_id, amount)

        # ═══════════════════════════════════════════════
        # 客户 1: Sok Heng — 🟢 活跃 · VIP · 10kW-24月 (6/24)
        # ═══════════════════════════════════════════════
        c1 = await make_customer("Sok Heng", "0888888001", "DEV-KH-001",
            "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
            "active", (11.5564, 104.9282), "123 Norodom Blvd, Phnom Penh",
            mfi_lolc, ["VIP"])
        ct1 = await make_contract(c1, 10.0, Decimal("230"), Decimal("920"), Decimal("47.33"),
            date(2025, 12, 1), date(2027, 12, 1), "active")
        result = (await db.execute(text(
            "SELECT id, total FROM repayment_schedules WHERE contract_id=:ct ORDER BY period_no"
        ), {"ct": ct1})).fetchall()
        for i in range(6):
            await pay_schedule(ct1, c1, result[i][0], result[i][1])
        await set_customer_count(db, c1, 6)
        print("✓ 客户1: Sok Heng · 10kW-24月 · 活跃 · 已还6/24期 · VIP")

        # ═══════════════════════════════════════════════
        # 客户 2: Chenda — 🟢 活跃 · 6kW-12月 (3/12)
        # ═══════════════════════════════════════════════
        c2 = await make_customer("Chenda", "011222333", "DEV-KH-002",
            "b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d7",
            "active", (13.3618, 103.8556), "45 Wat Bo Rd, Siem Reap",
            mfi_prasac, [])
        ct2 = await make_contract(c2, 6.0, Decimal("138"), Decimal("552"), Decimal("52.58"),
            date(2026, 2, 1), date(2027, 2, 1), "active")
        result2 = (await db.execute(text(
            "SELECT id, total FROM repayment_schedules WHERE contract_id=:ct ORDER BY period_no"
        ), {"ct": ct2})).fetchall()
        for i in range(3):
            await pay_schedule(ct2, c2, result2[i][0], result2[i][1])
        await set_customer_count(db, c2, 3)
        print("✓ 客户2: Chenda · 6kW-12月 · 活跃 · 已还3/12期")

        # ═══════════════════════════════════════════════
        # 客户 3: Bopha — 🔴 逾期锁定 · 15kW-24月 (1/24, 其余逾期)
        # ═══════════════════════════════════════════════
        c3 = await make_customer("Bopha", "044555666", "DEV-KH-003",
            "c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d8",
            "locked", (10.6104, 103.5239), "78 Ekareach St, Sihanoukville",
            mfi_lolc, ["高风险"])
        ct3 = await make_contract(c3, 15.0, Decimal("345"), Decimal("1380"), Decimal("57.50"),
            date(2025, 10, 1), date(2027, 10, 1), "overdue")
        result3 = (await db.execute(text(
            "SELECT id, total FROM repayment_schedules WHERE contract_id=:ct ORDER BY period_no"
        ), {"ct": ct3})).fetchall()
        await pay_schedule(ct3, c3, result3[0][0], result3[0][1])
        await set_customer_count(db, c3, 1)
        await update_customer_status(db, c3, "locked")
        print("✓ 客户3: Bopha · 15kW-24月 · 逾期锁定 · 仅还1期")

        # ═══════════════════════════════════════════════
        # 客户 4: Vannak — ⭐ 永久解锁 · 20kW-36月 (已结清)
        # ═══════════════════════════════════════════════
        c4 = await make_customer("Vannak", "077888999", "DEV-KH-004",
            "d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6",
            "permanent", (13.0957, 103.2022), "12 National Rd 5, Battambang",
            mfi_acleda, [])
        ct4 = await make_contract(c4, 20.0, Decimal("460"), Decimal("1840"), Decimal("60.00"),
            date(2024, 6, 1), date(2027, 6, 1), "closed")
        result4 = (await db.execute(text(
            "SELECT id, total FROM repayment_schedules WHERE contract_id=:ct ORDER BY period_no"
        ), {"ct": ct4})).fetchall()
        for row in result4:
            await pay_schedule(ct4, c4, row[0], row[1])
        await set_customer_count(db, c4, 36)
        await update_customer_status(db, c4, "permanent")
        # 永久解锁 Token
        await add_token(db, c4, "999999999", -1, 36, amount=0, contract_id=ct4)
        # 补发场景：作废的 Token
        tid = await add_token(db, c4, "888888888", 30, 10, amount=Decimal("60.00"), contract_id=ct4)
        t = await db.get(Token, tid)
        t.status = "SUPERSEDED"
        t.voided_by = "admin"
        t.void_reason = "客户反馈未收到SMS，已补发新Token"
        t.voided_at = datetime.now()
        await db.commit()
        print("✓ 客户4: Vannak · 20kW-36月 · 永久解锁 · 已结清")

        # ═══════════════════════════════════════════════
        # 客户 5: Dara — 🟢 活跃 · 30kW-36月 (12/36) · 大客户
        # ═══════════════════════════════════════════════
        c5 = await make_customer("Dara", "066555444", "DEV-KH-005",
            "f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c1",
            "active", (10.6067, 104.1833), "5 River Rd, Kampot",
            mfi_prasac, ["VIP", "大客户"])
        ct5 = await make_contract(c5, 30.0, Decimal("690"), Decimal("2760"), Decimal("90.00"),
            date(2025, 6, 1), date(2028, 6, 1), "active")
        result5 = (await db.execute(text(
            "SELECT id, total FROM repayment_schedules WHERE contract_id=:ct ORDER BY period_no"
        ), {"ct": ct5})).fetchall()
        for i in range(12):
            await pay_schedule(ct5, c5, result5[i][0], result5[i][1])
        await set_customer_count(db, c5, 12)
        print("✓ 客户5: Dara · 30kW-36月 · 活跃 · 已还12/36期 · VIP大客户")

        # ═══════════════════════════════════════════════
        # 客户 6: Sopheap — ⚪ 待签约 · 无合同 · 新客户
        # ═══════════════════════════════════════════════
        c6 = await make_customer("Sopheap", "099111222", "DEV-KH-006",
            "a1a2a3a4a5a6a7a8a9a0b1b2b3b4b5b6",
            "locked", (12.5657, 104.9910), "88 Riverside, Kampong Cham",
            None, ["新客户"])
        print("✓ 客户6: Sopheap · 无合同 · 待签约 · 新客户")

        # ═══════════════════════════════════════════════
        # 客户 7: Kunthea — ⚪ 草稿合同 · 6kW-12月
        # ═══════════════════════════════════════════════
        c7 = await make_customer("Kunthea", "012333444", "DEV-KH-007",
            "c1c2c3c4c5c6c7c8c9c0d1d2d3d4d5d6",
            "locked", (11.5588, 104.9174), "67 Monivong Blvd, Phnom Penh",
            mfi_lolc, ["新客户"])
        ct7 = await make_contract(c7, 6.0, Decimal("138"), Decimal("552"), Decimal("52.58"),
            date(2026, 5, 15), date(2027, 5, 15), "draft")
        print("✓ 客户7: Kunthea · 6kW-12月 · 草稿合同 · 待审批")

        # ═══════════════════════════════════════════════
        # 客户 8: Rithy — 🔴 已回收 · 20kW-36月
        # ═══════════════════════════════════════════════
        c8 = await make_customer("Rithy", "098777666", "DEV-KH-008",
            "e1e2e3e4e5e6e7e8e9e0f1f2f3f4f5f6",
            "locked", (12.4833, 106.0167), "3 Main St, Kratie",
            mfi_acleda, ["投诉频繁"])
        ct8 = await make_contract(c8, 20.0, Decimal("460"), Decimal("1840"), Decimal("60.00"),
            date(2024, 1, 1), date(2027, 1, 1), "recovered")
        result8 = (await db.execute(text(
            "SELECT id, total FROM repayment_schedules WHERE contract_id=:ct ORDER BY period_no"
        ), {"ct": ct8})).fetchall()
        for i in range(4):
            await pay_schedule(ct8, c8, result8[i][0], result8[i][1])
        await set_customer_count(db, c8, 4)
        await update_customer_status(db, c8, "locked")
        print("✓ 客户8: Rithy · 20kW-36月 · 已回收 · 投诉频繁")

        # ═══════════════════════════════════════════════
        # 告警数据
        # ═══════════════════════════════════════════════
        # P0 — 逾期未还款（Bopha）
        alert1 = Alert(id="AL000001", rule_code="ALM-001", title="逾期未还款",
                       detail="客户 Bopha（DEV-KH-003）合同 KH-2026-00003 已逾期超过7天，累计3期未付，设备已自动锁定。",
                       level="P0", status="pending", customer_id=c3, contract_id=ct3,
                       triggered_at=datetime(2026, 5, 18, 8, 0, 0))
        # P1 — 设备通信失联（Vannak，已被认领）
        alert2 = Alert(id="AL000002", rule_code="ALM-002", title="设备通信失联",
                       detail="客户 Vannak（DEV-KH-004）超过96小时无心跳信号，最后通信时间 2026-05-16 14:30。",
                       level="P1", status="claimed", customer_id=c4, contract_id=ct4,
                       claimed_by="admin", claimed_at=datetime(2026, 5, 19, 10, 0, 0),
                       triggered_at=datetime(2026, 5, 19, 8, 0, 0))
        # P2 — Token验证异常（Dara，已关闭）
        alert3 = Alert(id="AL000003", rule_code="ALM-003", title="Token验证异常",
                       detail="客户 Dara（DEV-KH-005）连续3次输入错误Token，已联系客户确认。客户表示误操作，已指导正确输入。",
                       level="P2", status="closed", customer_id=c5, contract_id=ct5,
                       resolved_at=datetime(2026, 5, 17, 16, 0, 0),
                       resolution_note="已联系客户确认，系误操作，已正常使用",
                       triggered_at=datetime(2026, 5, 17, 9, 0, 0))
        db.add_all([alert1, alert2, alert3])
        await db.commit()

        # 告警日志
        from app.models import AlertLog, _new_id
        db.add_all([
            AlertLog(id=_new_id("LG"), alert_id="AL000001", action="triggered",
                     note="规则 ALM-001 触发：逾期超过7天", created_at=datetime(2026, 5, 18, 8, 0, 0)),
            AlertLog(id=_new_id("LG"), alert_id="AL000002", action="triggered",
                     note="规则 ALM-002 触发：信号丢失超过72小时", created_at=datetime(2026, 5, 19, 8, 0, 0)),
            AlertLog(id=_new_id("LG"), alert_id="AL000002", action="claimed", operator="admin",
                     created_at=datetime(2026, 5, 19, 10, 0, 0)),
            AlertLog(id=_new_id("LG"), alert_id="AL000003", action="triggered",
                     note="规则 ALM-003 触发：连续3次Token验证失败", created_at=datetime(2026, 5, 17, 9, 0, 0)),
            AlertLog(id=_new_id("LG"), alert_id="AL000003", action="resolved",
                     note="已联系客户确认，系误操作，已正常使用", created_at=datetime(2026, 5, 17, 16, 0, 0)),
        ])
        await db.commit()
        print("✓ 告警数据: 3条（P0待处理 / P1已认领 / P2已关闭）")

        # ═══════════════════════════════════════════════
        # 完成
        # ═══════════════════════════════════════════════
        total_cust = (await db.execute(text("SELECT count(*) FROM customers"))).scalar()
        total_contracts = (await db.execute(text("SELECT count(*) FROM contracts"))).scalar()
        total_tokens = (await db.execute(text("SELECT count(*) FROM tokens"))).scalar()
        total_alerts = (await db.execute(text("SELECT count(*) FROM alerts"))).scalar()

    print(f"\n🎬 演示数据加载完毕!")
    print(f"   客户: {total_cust} · 合同: {total_contracts} · Token: {total_tokens} · 告警: {total_alerts}")
    print(f"   MFI: 3家 · 贷款产品: 5档 · 支付汇率: 4档")


if __name__ == "__main__":
    asyncio.run(main())
