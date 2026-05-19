from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import (
    get_customers, get_customer as store_get_customer,
    add_customer as store_add_customer, delete_customer as store_delete_customer,
    set_customer_count, update_customer_status,
    get_tokens, add_token,
    add_sms_record, get_sms_records, get_days_for_amount,
    DuplicateDeviceError, DuplicateSecretKeyError,
)
from app.redis import cache_get, cache_set, cache_delete, session_get
from openpaygo import generate_token, TokenType

router = APIRouter(prefix="/api")


# ---- Helper ----

SECRET_KEY_LENGTH = 32
SECRET_KEY_HEX_CHARS = set("0123456789abcdefABCDEF")


def _validate_secret_key(key: str) -> None:
    if len(key) != SECRET_KEY_LENGTH or not all(c in SECRET_KEY_HEX_CHARS for c in key):
        raise HTTPException(
            status_code=400,
            detail=f"secret_key 必须是 {SECRET_KEY_LENGTH} 位 hex 字符串",
        )


async def _check_auth(request: Request):
    sid = request.cookies.get("session")
    if not sid:
        raise HTTPException(status_code=401, detail="未认证")
    data = await session_get(sid)
    if data is None:
        raise HTTPException(status_code=401, detail="未认证")


# ---- Utils ----

@router.get("/utils/generate-secret-key")
async def generate_secret_key():
    import secrets
    return {"secret_key": secrets.token_hex(16)}


@router.get("/utils/generate-secret-keys")
async def generate_secret_keys(count: int = 5):
    import secrets
    if count < 1 or count > 20:
        raise HTTPException(status_code=400, detail="数量范围 1-20")
    return {"secret_keys": [secrets.token_hex(16) for _ in range(count)]}


# ---- Customers ----

class CustomerCreate(BaseModel):
    name: str
    phone: str
    device_id: str
    secret_key: str


class TokenGenerate(BaseModel):
    days: int


class SimulatePayment(BaseModel):
    amount: float


@router.get("/customers")
async def list_customers(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get("customers:list")
    if cached:
        return cached
    result = await get_customers(db)
    await cache_set("customers:list", result)
    return result


@router.post("/customers")
async def create_customer(request: Request, body: CustomerCreate,
                          db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    _validate_secret_key(body.secret_key)
    try:
        cid = await store_add_customer(
            db, name=body.name, phone=body.phone,
            device_id=body.device_id, secret_key=body.secret_key,
        )
    except DuplicateDeviceError:
        raise HTTPException(
            status_code=409,
            detail=f"设备编号 '{body.device_id}' 已被其他客户使用",
        )
    except DuplicateSecretKeyError:
        raise HTTPException(
            status_code=409,
            detail="该密钥已绑定到其他设备",
        )
    await cache_delete("customers:*")
    customer = await store_get_customer(db, cid)
    return customer


@router.get("/customers/{customer_id}")
async def get_customer_detail(request: Request, customer_id: str,
                              db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cache_key = f"customers:{customer_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    await cache_set(cache_key, customer)
    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer_route(request: Request, customer_id: str,
                                db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    ok = await store_delete_customer(db, customer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="客户不存在")
    await cache_delete("customers:*")
    return {"ok": True}


@router.post("/customers/{customer_id}/token")
async def generate_token_for_customer(request: Request, customer_id: str,
                                      body: TokenGenerate,
                                      db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        value=body.days,
        token_type=TokenType.ADD_TIME,
    )
    await set_customer_count(db, customer_id, new_count)
    await add_token(db, customer_id, token_str, body.days, new_count)
    await update_customer_status(db, customer_id, "active")
    await cache_delete("customers:*")
    await cache_delete("tokens:*")

    return {"token": token_str, "customer_id": customer_id, "days": body.days}


@router.get("/tokens")
async def list_tokens(request: Request, db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get("tokens:list")
    if cached:
        return cached
    result = await get_tokens(db)
    await cache_set("tokens:list", result)
    return result


@router.post("/customers/{customer_id}/simulate-payment")
async def simulate_payment(request: Request, customer_id: str,
                           body: SimulatePayment,
                           db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    days = await get_days_for_amount(db, body.amount)
    if days == 0:
        raise HTTPException(status_code=400, detail=f"不支持的金额: ${body.amount}")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        value=days,
        token_type=TokenType.ADD_TIME,
    )
    await set_customer_count(db, customer_id, new_count)
    await add_token(db, customer_id, token_str, days, new_count, amount=body.amount)
    await update_customer_status(db, customer_id, "active")

    message = (
        f"[PAYGO Solar] 尊敬的用户，您已成功支付${body.amount:.2f}。"
        f"您的太阳能激活码为：{token_str}。有效期{days}天。请尽快输入您的设备。"
    )
    await add_sms_record(db, customer_id, customer["phone"], message)
    await cache_delete("customers:*")
    await cache_delete("tokens:*")
    await cache_delete("sms:*")

    return {
        "token": token_str, "customer_id": customer_id, "days": days,
        "sms": {"to": customer["phone"], "message": message},
    }


@router.post("/customers/{customer_id}/lock")
async def lock_device(request: Request, customer_id: str,
                      db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")
    await update_customer_status(db, customer_id, "locked")
    await cache_delete("customers:*")
    return {"status": "ok"}


@router.post("/customers/{customer_id}/permanent-unlock")
async def permanent_unlock(request: Request, customer_id: str,
                           db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    customer = await store_get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="客户不存在")

    new_count, token_str = generate_token(
        secret_key=customer["secret_key"],
        count=customer["count"],
        token_type=TokenType.DISABLE_PAYG,
    )
    await set_customer_count(db, customer_id, new_count)
    await add_token(db, customer_id, token_str, -1, new_count)
    await update_customer_status(db, customer_id, "permanent")

    message = (
        f"[PAYGO Solar] 恭喜！您的贷款已全部结清。"
        f"设备永久解锁码：{token_str}。请在您的设备中输入此码以永久解锁。"
    )
    await add_sms_record(db, customer_id, customer["phone"], message)
    await cache_delete("customers:*")
    await cache_delete("tokens:*")
    await cache_delete("sms:*")

    return {
        "token": token_str, "customer_id": customer_id, "days": -1,
        "sms": {"to": customer["phone"], "message": message},
    }


@router.get("/sms")
async def list_sms(request: Request, customer_id: str = None,
                   db: AsyncSession = Depends(get_db)):
    await _check_auth(request)
    cached = await cache_get(f"sms:{customer_id or 'all'}")
    if cached:
        return cached
    result = await get_sms_records(db, customer_id)
    await cache_set(f"sms:{customer_id or 'all'}", result)
    return result
