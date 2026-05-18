from fastapi import APIRouter, Request, HTTPException

from app.db import get_payment_rates

router = APIRouter(prefix="/api/config")


def _check_auth(request: Request):
    if request.cookies.get("session") != "authenticated":
        raise HTTPException(status_code=401, detail="未认证")


@router.get("/payment-rates")
async def list_payment_rates(request: Request):
    _check_auth(request)
    return get_payment_rates()
