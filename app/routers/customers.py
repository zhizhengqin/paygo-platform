from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.db import (
    get_customers, get_customer, add_customer, delete_customer,
    get_tokens, add_token, update_customer_status, get_days_for_amount, add_sms_record,
    get_sms_records,
)
from app.token_engine import generate_token

router = APIRouter(prefix="/api")


class CustomerCreate(BaseModel):
    name: str
    phone: str
    device_id: str


class TokenGenerate(BaseModel):
    days: int


def _check_auth(request: Request):
    """检查 session cookie 是否已认证，未认证则抛出 401"""
    if request.cookies.get("session") != "authenticated":
        raise HTTPException(status_code=401, detail="未认证")


@router.get("/customers")
async def list_customers(request: Request):
    """列出所有客户"""
    _check_auth(request)
    customers = get_customers()
    return list(customers.values())


@router.post("/customers")
async def create_customer(request: Request, body: CustomerCreate):
    """创建新客户"""
    _check_auth(request)
    cid = add_customer(name=body.name, phone=body.phone, device_id=body.device_id)
    customer = get_customer(cid)
    return customer


@router.get("/customers/{customer_id}")
async def get_customer_detail(request: Request, customer_id: str):
    """获取单个客户详情"""
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer_route(request: Request, customer_id: str):
    """删除客户"""
    _check_auth(request)
    ok = delete_customer(customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"ok": True}


@router.post("/customers/{customer_id}/token")
async def generate_token_for_customer(request: Request, customer_id: str, body: TokenGenerate):
    """为客户生成 Token"""
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    token_str = generate_token(customer["device_id"], body.days)
    add_token(customer_id, token_str, body.days)
    return {
        "token": token_str,
        "customer_id": customer_id,
        "days": body.days,
    }


@router.get("/tokens")
async def list_tokens(request: Request):
    """列出所有 Token 记录"""
    _check_auth(request)
    return get_tokens()


class SimulatePayment(BaseModel):
    amount: float


@router.post("/customers/{customer_id}/simulate-payment")
async def simulate_payment(request: Request, customer_id: str, body: SimulatePayment):
    """模拟支付：根据金额查汇率 → 生成15位Token → 模拟短信发送"""
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    days = get_days_for_amount(body.amount)
    if days == 0:
        raise HTTPException(status_code=400, detail=f"不支持的金额: ${body.amount}")

    token_str = generate_token(customer["device_id"], days)
    add_token(customer_id, token_str, days)

    # 生成模拟短信
    token_formatted = f"{token_str[:5]} {token_str[5:9]} {token_str[9:11]} {token_str[11:15]}"
    message = (
        f"[PAYGO Solar] 尊敬的用户，您已成功支付${body.amount:.2f}。"
        f"您的太阳能激活码为：{token_formatted}。"
        f"有效期{days}天。请尽快输入您的设备。"
    )
    add_sms_record(customer_id, customer["phone"], message)

    return {
        "token": token_str,
        "customer_id": customer_id,
        "days": days,
        "sms": {
            "to": customer["phone"],
            "message": message,
        },
    }


@router.post("/customers/{customer_id}/lock")
async def lock_device(request: Request, customer_id: str):
    """锁定设备"""
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    update_customer_status(customer_id, "locked")
    return {"status": "ok"}


@router.post("/customers/{customer_id}/permanent-unlock")
async def permanent_unlock(request: Request, customer_id: str):
    """永久解锁：生成 DISABLE_PAYG Token (type=99)"""
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    token_str = generate_token(customer["device_id"], -1)  # -1 → DISABLE_PAYG
    add_token(customer_id, token_str, -1)
    update_customer_status(customer_id, "permanent")

    token_formatted = f"{token_str[:5]} {token_str[5:9]} {token_str[9:11]} {token_str[11:15]}"
    message = (
        f"[PAYGO Solar] 恭喜！您的贷款已全部结清。"
        f"设备永久解锁码：{token_formatted}。"
        f"请在您的设备中输入此码以永久解锁。"
    )
    add_sms_record(customer_id, customer["phone"], message)

    return {
        "token": token_str,
        "customer_id": customer_id,
        "days": -1,
        "sms": {
            "to": customer["phone"],
            "message": message,
        },
    }


@router.get("/sms")
async def list_sms(request: Request, customer_id: str = None):
    """列出短信记录，可按客户筛选"""
    _check_auth(request)
    return get_sms_records(customer_id)
