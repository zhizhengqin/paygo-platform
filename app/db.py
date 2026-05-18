import uuid
from datetime import datetime, timedelta

_customers: dict[str, dict] = {}
_tokens: list[dict] = []
_sms_records: list[dict] = []

_payment_rates: list[dict] = [
    {"amount": 5, "days": 30},
    {"amount": 10, "days": 60},
]


def get_customers() -> dict:
    return _customers


def get_customer(customer_id: str) -> dict | None:
    return _customers.get(customer_id)


def add_customer(name: str, phone: str, device_id: str, secret_key: str) -> str:
    cid = f"C{str(uuid.uuid4())[:4].upper()}"
    _customers[cid] = {
        "id": cid,
        "name": name,
        "phone": phone,
        "device_id": device_id,
        "secret_key": secret_key,
        "count": 0,
        "status": "locked",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "locked_at": None,
    }
    return cid


def get_customer_count(customer_id: str) -> int:
    return _customers[customer_id]["count"]


def set_customer_count(customer_id: str, new_count: int) -> None:
    _customers[customer_id]["count"] = new_count


def update_customer_status(customer_id: str, status: str) -> bool:
    if customer_id not in _customers:
        return False
    _customers[customer_id]["status"] = status
    if status == "locked":
        _customers[customer_id]["locked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return True


def delete_customer(customer_id: str) -> bool:
    if customer_id in _customers:
        del _customers[customer_id]
        return True
    return False


def reset_db():
    _customers.clear()
    _tokens.clear()
    _sms_records.clear()
    _payment_rates.clear()
    _payment_rates.extend([
        {"amount": 5, "days": 30},
        {"amount": 10, "days": 60},
    ])


def get_tokens() -> list:
    return _tokens


def add_token(customer_id: str, token: str, days: int, count: int) -> str:
    tid = f"T{str(uuid.uuid4())[:4].upper()}"
    now = datetime.now()
    _tokens.append({
        "id": tid,
        "customer_id": customer_id,
        "token": token,
        "days": days,
        "count": count,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
    })
    return tid


def get_payment_rates() -> list[dict]:
    return _payment_rates


def get_days_for_amount(amount: float) -> int:
    for rate in _payment_rates:
        if rate["amount"] == amount:
            return rate["days"]
    return 0


def add_sms_record(customer_id: str, to_phone: str, message: str) -> str:
    sid = f"S{str(uuid.uuid4())[:4].upper()}"
    _sms_records.append({
        "id": sid,
        "customer_id": customer_id,
        "to": to_phone,
        "message": message,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    return sid


def get_sms_records(customer_id: str = None) -> list[dict]:
    if customer_id:
        return [r for r in _sms_records if r["customer_id"] == customer_id]
    return list(_sms_records)
