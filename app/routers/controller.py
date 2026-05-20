"""设备控制器模拟 API"""
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.store import get_customer, set_customer_count, update_customer_status
from openpaygo import decode_token, TokenType as OT

router = APIRouter(prefix="/api/controller")


class TokenValidate(BaseModel):
    customer_id: str
    token: str
    count: int


@router.post("/validate-token")
async def validate_token(body: TokenValidate, db: AsyncSession = Depends(get_db)):
    """控制器 Token 验证 — 在服务端解码 OpenPAYGO Token"""
    customer = await get_customer(db, body.customer_id)
    if not customer or not customer.get("secret_key"):
        return {"valid": False, "reason": "设备密钥无效"}

    try:
        value, token_type, new_count, used_counts = decode_token(
            token=body.token,
            secret_key=customer["secret_key"],
            count=body.count,
            used_counts=[],
        )
    except Exception:
        return {"valid": False, "reason": "Token 解码失败"}

    if token_type == OT.INVALID:
        return {"valid": False, "reason": "Token 无效"}
    if token_type == OT.ALREADY_USED:
        return {"valid": False, "reason": "Token 已使用（防重放）"}

    days = int(value) if value else 0

    await set_customer_count(db, body.customer_id, new_count)
    if token_type == OT.DISABLE_PAYG:
        await update_customer_status(db, body.customer_id, "permanent")
    else:
        await update_customer_status(db, body.customer_id, "active")

    return {
        "valid": True,
        "days": days,
        "token_type": token_type.name if hasattr(token_type, 'name') else str(token_type),
        "new_count": new_count,
    }
