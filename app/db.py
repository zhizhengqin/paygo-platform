import uuid
from datetime import datetime, timedelta

_customers: dict[str, dict] = {}
_tokens: list[dict] = []


def get_customers() -> dict:
    return _customers


def get_customer(customer_id: str) -> dict | None:
    return _customers.get(customer_id)


def add_customer(name: str, phone: str, device_id: str) -> str:
    cid = f"C{str(uuid.uuid4())[:4].upper()}"
    _customers[cid] = {
        "id": cid,
        "name": name,
        "phone": phone,
        "device_id": device_id,
        "remaining_days": 0,
        "status": "active",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    return cid


def delete_customer(customer_id: str) -> bool:
    if customer_id in _customers:
        del _customers[customer_id]
        return True
    return False


def reset_db():
    """Clear all in-memory data. Useful for tests."""
    _customers.clear()
    _tokens.clear()


def get_tokens() -> list:
    return _tokens


def add_token(customer_id: str, token: str, days: int) -> str:
    tid = f"T{str(uuid.uuid4())[:4].upper()}"
    now = datetime.now()
    _tokens.append({
        "id": tid,
        "customer_id": customer_id,
        "token": token,
        "days": days,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    })
    return tid
