"""演示数据初始化脚本 — 清空旧数据，按业务流程创建3个演示客户+合同+支付记录"""
import asyncio
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import delete, text

from app.database import engine, AsyncSessionLocal
from app.models import Customer, Token, SmsRecord, PaymentRate, DeviceState, Contract, LoanProduct, RepaymentSchedule
from app.store import (
    add_customer, set_customer_count, update_customer_status,
    add_token, add_loan_product, add_contract,
    approve_contract, update_contract_status, seed_loan_products,
)


async def clear_all_data():
    """清空所有业务表"""
    async with AsyncSessionLocal() as db:
        tables = [RepaymentSchedule, Token, SmsRecord, Contract, LoanProduct, Customer, DeviceState]
        for table in tables:
            await db.execute(delete(table))
        await db.commit()
        print("✓ 已清空所有数据")


async def create_demo_data():
    """创建演示数据：3个客户 + 5个贷款产品 + 3个合同 + 支付记录"""

    async with AsyncSessionLocal() as db:
        # ---- 贷款产品种子 ----
        await seed_loan_products(db)
        products = await db.execute(
            text("SELECT id, name, capacity_kw, term_months FROM loan_products ORDER BY capacity_kw")
        )
        prods = {}
        for row in products:
            prods[str(row[2])] = {"id": row[0], "name": row[1], "term": row[3]}
        print(f"✓ 贷款产品就绪: {len(prods)} 档")

        # ---- 客户 1: Sok Heng — 已签约10kW系统，正常还款中 ----
        c1_id = await add_customer(
            db, "Sok Heng", "0888888001", "DEV-KH-001",
            "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        )
        await set_customer_count(db, c1_id, 3)
        await update_customer_status(db, c1_id, "active")

        # 创建合同（10kW-24月）
        p10 = prods["10.00"]
        ctr1 = await add_contract(
            db, c1_id, p10["id"],
            Decimal("230.00"), Decimal("920.00"), Decimal("47.33"),
            date(2026, 3, 1), date(2028, 3, 1),
        )
        await approve_contract(db, ctr1)  # 审批通过 → active

        # 模拟 2 次还款
        await add_token(db, c1_id, "123456789", 30, 3, amount=Decimal("47.33"))
        await add_token(db, c1_id, "123456790", 30, 4, amount=Decimal("47.33"))
        print(f"✓ 客户1: Sok Heng · 0888888001 · DEV-KH-001 · 10kW-24月 · 已还2期")

        # ---- 客户 2: Alice — 6kW系统，首次还款刚完成 ----
        c2_id = await add_customer(
            db, "Alice", "011222333", "DEV-KH-002",
            "b1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d7"
        )
        await set_customer_count(db, c2_id, 2)
        await update_customer_status(db, c2_id, "active")

        p6 = prods["6.00"]
        ctr2 = await add_contract(
            db, c2_id, p6["id"],
            Decimal("138.00"), Decimal("552.00"), Decimal("52.58"),
            date(2026, 4, 1), date(2027, 4, 1),
        )
        await approve_contract(db, ctr2)

        await add_token(db, c2_id, "234567891", 30, 2, amount=Decimal("52.58"))
        print(f"✓ 客户2: Alice · 011222333 · DEV-KH-002 · 6kW-12月 · 已还1期")

        # ---- 客户 3: Bob — 15kW系统，逾期中 ----
        c3_id = await add_customer(
            db, "Bob", "044555666", "DEV-KH-003",
            "c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d8"
        )
        await set_customer_count(db, c3_id, 1)
        await update_customer_status(db, c3_id, "locked")

        p15 = prods["15.00"]
        ctr3 = await add_contract(
            db, c3_id, p15["id"],
            Decimal("345.00"), Decimal("1380.00"), Decimal("57.50"),
            date(2025, 12, 1), date(2027, 12, 1),
        )
        await approve_contract(db, ctr3)
        await update_contract_status(db, ctr3, "overdue")

        await add_token(db, c3_id, "345678912", 30, 1, amount=Decimal("57.50"))
        print(f"✓ 客户3: Bob · 044555666 · DEV-KH-003 · 15kW-24月 · 逾期(仅还1期)")

        # ---- 客户 4 (无合同): Sarun — 刚安装设备，待签约 ----
        c4_id = await add_customer(
            db, "Sarun", "077123456", "DEV-KH-004",
            "d1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d9"
        )
        await update_customer_status(db, c4_id, "locked")
        print(f"✓ 客户4: Sarun · 077123456 · DEV-KH-004 · 待签约(无合同)")

        await db.commit()
        print(f"\n🎬 演示数据准备完毕! 4个客户 · 5个产品 · 3个合同 · 4笔支付")


async def main():
    await clear_all_data()
    await create_demo_data()


if __name__ == "__main__":
    asyncio.run(main())
