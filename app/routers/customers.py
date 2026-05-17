from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from app.db import get_customers, get_customer, add_customer, delete_customer, get_tokens, add_token
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
