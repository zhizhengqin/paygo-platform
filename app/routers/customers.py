from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.db import (
    get_customers, get_customer, add_customer, delete_customer,
    get_tokens, add_token, update_customer_status, get_days_for_amount, add_sms_record,
    get_sms_records, set_customer_count,
)
from openpaygo import generate_token, TokenType

router = APIRouter(prefix="/api")


class CustomerCreate(BaseModel):
    name: str
    phone: str
    device_id: str
    secret_key: str


class TokenGenerate(BaseModel):
    days: int


SECRET_KEY_LENGTH = 32
SECRET_KEY_HEX_CHARS = set("0123456789abcdefABCDEF")


def _validate_secret_key(key: str) -> None:
    if len(key) != SECRET_KEY_LENGTH or not all(c in SECRET_KEY_HEX_CHARS for c in key):
        raise HTTPException(
            status_code=400,
            detail=f"secret_key 必须是 {SECRET_KEY_LENGTH} 位 hex 字符串",
        )


def _check_auth(request: Request):
    if request.cookies.get("session") != "authenticated":
        raise HTTPException(status_code=401, detail="未认证")


@router.get("/customers")
async def list_customers(request: Request):
    _check_auth(request)
    customers = get_customers()
    return list(customers.values())


@router.post("/customers")
async def create_customer(request: Request, body: CustomerCreate):
    _check_auth(request)
    _validate_secret_key(body.secret_key)
    cid = add_customer(
        name=body.name, phone=body.phone,
        device_id=body.device_id, secret_key=body.secret_key,
    )
    customer = get_customer(cid)
    return customer


@router.get("/customers/{customer_id}")
async def get_customer_detail(request: Request, customer_id: str):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer_route(request: Request, customer_id: str):
    _check_auth(request)
    ok = delete_customer(customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"ok": True}


@router.post("/customers/{customer_id}/token")
async def generate_token_for_customer(request: Request, customer_id: str, body: TokenGenerate):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        value=body.days,
        token_type=TokenType.ADD_TIME,
    )
    set_customer_count(customer_id, new_count)
    add_token(customer_id, token_str, body.days, new_count)

    return {
        "token": token_str,
        "customer_id": customer_id,
        "days": body.days,
    }


@router.get("/tokens")
async def list_tokens(request: Request):
    _check_auth(request)
    return get_tokens()


class SimulatePayment(BaseModel):
    amount: float


@router.post("/customers/{customer_id}/simulate-payment")
async def simulate_payment(request: Request, customer_id: str, body: SimulatePayment):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    days = get_days_for_amount(body.amount)
    if days == 0:
        raise HTTPException(status_code=400, detail=f"不支持的金额: ${body.amount}")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        value=days,
        token_type=TokenType.ADD_TIME,
    )
    set_customer_count(customer_id, new_count)
    add_token(customer_id, token_str, days, new_count)

    message = (
        f"[PAYGO Solar] 尊敬的用户，您已成功支付${body.amount:.2f}。"
        f"您的太阳能激活码为：{token_str}。"
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
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    update_customer_status(customer_id, "locked")
    return {"status": "ok"}


@router.post("/customers/{customer_id}/permanent-unlock")
async def permanent_unlock(request: Request, customer_id: str):
    _check_auth(request)
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        token_type=TokenType.DISABLE_PAYG,
    )
    set_customer_count(customer_id, new_count)
    add_token(customer_id, token_str, -1, new_count)
    update_customer_status(customer_id, "permanent")

    message = (
        f"[PAYGO Solar] 恭喜！您的贷款已全部结清。"
        f"设备永久解锁码：{token_str}。"
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
    _check_auth(request)
    return get_sms_records(customer_id)
