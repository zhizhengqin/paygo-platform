"""报表中心 API router — 运营汇总 / ESG 碳减排 / CSV 导出"""
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Customer, Token, Contract, Alert
from app.routers.customers import _check_auth

router = APIRouter(prefix="/api/reports")


@router.get("/summary")
async def report_summary(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    db: AsyncSession = Depends(get_db),
):
    """运营汇总报表：新增客户/Token 收入/合同/告警/设备状态"""
    await _check_auth(request)

    today = date.today()
    start = date.fromisoformat(start_date) if start_date else today.replace(day=1)
    end = date.fromisoformat(end_date) if end_date else today

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    # 新增客户
    new_customers_r = await db.execute(
        select(func.count()).select_from(Customer).where(
            Customer.created_at >= start_dt, Customer.created_at <= end_dt
        )
    )

    # Token 数量 + 收入
    tokens_r = await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Token.amount), 0),
        ).where(Token.generated_at >= start_dt, Token.generated_at <= end_dt)
    )
    token_count, total_revenue = tokens_r.first()

    # 新增合同
    new_contracts_r = await db.execute(
        select(func.count()).select_from(Contract).where(
            Contract.created_at >= start_dt, Contract.created_at <= end_dt
        )
    )

    # 告警数
    alerts_r = await db.execute(
        select(func.count()).select_from(Alert).where(
            Alert.triggered_at >= start_dt, Alert.triggered_at <= end_dt
        )
    )

    # 当前设备状态
    active_r = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.status == "active")
    )
    locked_r = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.status == "locked")
    )
    total_r = await db.execute(select(func.count()).select_from(Customer))

    total_customers = total_r.scalar() or 0
    overdue_rate = (
        round((locked_r.scalar() or 0) / total_customers * 100, 1)
        if total_customers > 0
        else 0
    )

    return {
        "period": {"start": str(start), "end": str(end)},
        "new_customers": new_customers_r.scalar() or 0,
        "token_count": token_count or 0,
        "total_revenue": float(total_revenue or 0),
        "new_contracts": new_contracts_r.scalar() or 0,
        "alert_count": alerts_r.scalar() or 0,
        "active_devices": active_r.scalar() or 0,
        "locked_devices": locked_r.scalar() or 0,
        "total_customers": total_customers,
        "overdue_rate": overdue_rate,
    }


@router.get("/esg")
async def report_esg(request: Request, db: AsyncSession = Depends(get_db)):
    """ESG 碳减排报表：基于 Token 天数估算发电量 -> CO2 减排"""
    await _check_auth(request)

    total_tokens_r = await db.execute(select(func.count()).select_from(Token))
    total_tokens = total_tokens_r.scalar() or 0

    total_days_r = await db.execute(
        select(func.coalesce(func.sum(Token.days), 0)).where(Token.days > 0)
    )
    total_days = total_days_r.scalar() or 0

    # 估算：每天平均发电 20kWh（6kW 系统 x 3.5 峰时），CO2 系数 0.0007 tCO2/kWh
    estimated_kwh = float(total_days) * 20
    co2_reduction = round(estimated_kwh * 0.0007, 2)

    return {
        "total_tokens": total_tokens,
        "total_days": total_days,
        "estimated_kwh": estimated_kwh,
        "co2_reduction_tons": co2_reduction,
    }


@router.get("/export")
async def report_export(request: Request, db: AsyncSession = Depends(get_db)):
    """导出运营数据为 CSV"""
    await _check_auth(request)

    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Type", "Count", "Amount", "Period"])

    # 客户总数
    cust_r = await db.execute(select(func.count()).select_from(Customer))
    writer.writerow(["Customers", cust_r.scalar() or 0, "-", "Total"])

    # Token 总数 + 金额
    tok_r = await db.execute(
        select(func.count(), func.coalesce(func.sum(Token.amount), 0)).select_from(Token)
    )
    tc, ta = tok_r.first()
    writer.writerow(["Tokens", tc or 0, f"${float(ta or 0):.2f}", "Total"])

    # 合同总数
    con_r = await db.execute(select(func.count()).select_from(Contract))
    writer.writerow(["Contracts", con_r.scalar() or 0, "-", "Total"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report.csv"},
    )
