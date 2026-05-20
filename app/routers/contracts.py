"""合同与贷款产品 API router"""
from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dateutil.relativedelta import relativedelta

from app.database import get_db
from app.store import (
    get_loan_products, get_loan_product, add_loan_product,
    update_loan_product, disable_loan_product,
    add_contract, get_contracts, get_contract, get_contract_with_schedules,
    approve_contract, update_contract_status, calc_amortization,
    mark_schedule_paid, check_overdue_schedules, settle_contract,
)
from app.routers.customers import _check_auth

router = APIRouter(prefix="/api")


# ---- 请求体模型 ----

class LoanProductCreate(BaseModel):
    name: str
    capacity_kw: float
    term_months: int
    interest_rate: float
    down_payment_pct: float
    total_amount: float


class LoanProductUpdate(BaseModel):
    name: str | None = None
    capacity_kw: float | None = None
    term_months: int | None = None
    interest_rate: float | None = None
    down_payment_pct: float | None = None
    total_amount: float | None = None


class ContractCreate(BaseModel):
    customer_id: str
    product_id: str


class StatusUpdate(BaseModel):
    status: str


class ContractPay(BaseModel):
    schedule_id: str
    amount: float


# ---- 贷款产品 API ----

@router.get("/loan-products")
async def api_get_loan_products(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_loan_products(db)


@router.get("/loan-products/{pid}")
async def api_get_loan_product(pid: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    p = await get_loan_product(db, pid)
    if not p:
        raise HTTPException(404, "产品不存在")
    return p


@router.post("/loan-products")
async def api_create_loan_product(body: LoanProductCreate, request: Request,
                                   db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    pid = await add_loan_product(
        db, body.name, Decimal(str(body.capacity_kw)), body.term_months,
        Decimal(str(body.interest_rate)), Decimal(str(body.down_payment_pct)),
        Decimal(str(body.total_amount)),
    )
    return await get_loan_product(db, pid)


@router.put("/loan-products/{pid}")
async def api_update_loan_product(pid: str, body: LoanProductUpdate,
                                   request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(400, "无更新字段")
    ok = await update_loan_product(db, pid, **kwargs)
    if not ok:
        raise HTTPException(404, "产品不存在")
    return await get_loan_product(db, pid)


@router.delete("/loan-products/{pid}")
async def api_disable_loan_product(pid: str, request: Request,
                                    db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await disable_loan_product(db, pid)
    if not ok:
        raise HTTPException(404, "产品不存在")
    return {"ok": True}


# ---- 合同 API ----

@router.get("/contracts")
async def api_get_contracts(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    return await get_contracts(db)


@router.get("/contracts/{cid}")
async def api_get_contract(cid: str, request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    c = await get_contract_with_schedules(db, cid)
    if not c:
        raise HTTPException(404, "合同不存在")
    return c


@router.post("/contracts")
async def api_create_contract(body: ContractCreate, request: Request,
                               db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    lp = await get_loan_product(db, body.product_id)
    if not lp:
        raise HTTPException(404, "贷款产品不存在")

    total = Decimal(str(lp["total_amount"]))
    dp_pct = Decimal(str(lp["down_payment_pct"]))
    down_payment = (total * dp_pct / Decimal("100")).quantize(Decimal("0.01"))
    loan_amount = total - down_payment

    start_date = date.today().replace(day=1)
    end_date = start_date + relativedelta(months=lp["term_months"])

    schedules = calc_amortization(
        loan_amount=loan_amount,
        annual_rate=Decimal(str(lp["interest_rate"])),
        term_months=lp["term_months"],
        start_date=start_date,
    )
    monthly_payment = schedules[0]["total"]

    cid = await add_contract(
        db, body.customer_id, body.product_id,
        down_payment, loan_amount, monthly_payment,
        start_date, end_date,
    )
    return await get_contract(db, cid)


@router.put("/contracts/{cid}/approve")
async def api_approve_contract(cid: str, request: Request,
                                db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    result = await approve_contract(db, cid)
    if not result:
        raise HTTPException(400, "审批失败（合同不存在或非 draft 状态）")
    return result


@router.put("/contracts/{cid}/status")
async def api_update_contract_status(cid: str, body: StatusUpdate,
                                      request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await update_contract_status(db, cid, body.status)
    if not ok:
        raise HTTPException(400, "状态变更失败（合同不存在或无效状态）")
    return await get_contract(db, cid)


@router.post("/contracts/{cid}/pay")
async def api_pay_schedule(cid: str, body: ContractPay, request: Request,
                           db: AsyncSession = Depends(get_db)):
    """还款一期：标记还款计划为已付 + 生成 ADD_TIME Token"""
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
    """结清合同：生成 DISABLE_PAYG Token + 永久解锁设备"""
    await _check_auth(request)
    result = await settle_contract(db, cid)
    if not result:
        raise HTTPException(400, "结清失败（合同不存在或状态不正确）")
    return result
