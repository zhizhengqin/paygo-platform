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


@router.post("/validate-token")
async def validate_token(body: TokenValidate, db: AsyncSession = Depends(get_db)):
    """控制器 Token 验证 — 从 DB 读取 count，防重放"""
    customer = await get_customer(db, body.customer_id)
    if not customer or not customer.get("secret_key"):
        return {"valid": False, "reason": "设备密钥无效"}

    # 从数据库读取真实 count（不信任前端传入）
    current_count = customer.get("count", 0)

    try:
        value, token_type, new_count, used_counts = decode_token(
            token=body.token,
            secret_key=customer["secret_key"],
            count=current_count,
            used_counts=[],
        )
    except Exception:
        return {"valid": False, "reason": "Token 解码失败"}

    if token_type == OT.INVALID:
        return {"valid": False, "reason": "Token 无效"}
    if token_type == OT.ALREADY_USED:
        return {"valid": False, "reason": "Token 已使用（防重放）"}

    # 额外防重放：检查此 token 是否已被使用过（Redis）
    from app.redis import get_redis, antireplay_check_and_mark
    r = get_redis()
    if r:
        replay_key = f"token_used:{body.customer_id}:{body.token}"
        if await r.get(replay_key):
            return {"valid": False, "reason": "Token 已使用（防重放）"}
        await r.setex(replay_key, 604800, "1")  # 7 days TTL

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
