"""状态机 + PostgreSQL 持久化模块 — OpenPAYGO 版本。"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.models import Base, DeviceState
from app.settings import DATABASE_URL

_engine = None
_session_factory = None


def _get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine, _session_factory


async def _ensure_tables():
    engine, _ = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def load(device_id: str = "default") -> dict:
    await _ensure_tables()
    _, session_factory = _get_engine()
    async with session_factory() as db:
        result = await db.execute(
            select(DeviceState).where(DeviceState.device_id == device_id)
        )
        ds = result.scalar()
        if ds is None:
            return {
                "device_id": device_id,
                "secret_key": None,
                "count": 0,
                "used_counts": [],
                "remaining_days": 0,
                "last_update": None,
                "status": "unbound",
            }
        return _to_dict(ds)


async def save(state: dict) -> None:
    await _ensure_tables()
    _, session_factory = _get_engine()
    device_id = state.get("device_id", "default")
    async with session_factory() as db:
        result = await db.execute(
            select(DeviceState).where(DeviceState.device_id == device_id)
        )
        ds = result.scalar()
        if ds is None:
            ds = DeviceState(device_id=device_id)
            db.add(ds)
        ds.secret_key = state.get("secret_key")
        ds.count = state.get("count", 0)
        ds.used_counts = state.get("used_counts", [])
        ds.remaining_days = state.get("remaining_days", 0)
        ds.last_update = (
            date.fromisoformat(state["last_update"])
            if state.get("last_update") else None
        )
        ds.status = state.get("status", "unbound")
        await db.commit()


def apply_token(state: dict, days: int, token_type: int, new_count: int,
                used_counts: list | None) -> None:
    if token_type == 3:  # DISABLE_PAYG
        state["remaining_days"] = -1
        state["last_update"] = date.today().isoformat()
        state["status"] = "permanent"
    else:  # ADD_TIME
        state["remaining_days"] = state["remaining_days"] + days
        state["last_update"] = date.today().isoformat()
        state["status"] = "active"

    state["count"] = new_count
    if used_counts is not None:
        state["used_counts"] = used_counts


async def reset(device_id: str = "default") -> dict:
    state = {
        "device_id": device_id,
        "secret_key": None,
        "count": 0,
        "used_counts": [],
        "remaining_days": 0,
        "last_update": None,
        "status": "unbound",
    }
    await save(state)
    return state


def tick(state: dict) -> None:
    if state["status"] in ("unbound", "locked", "permanent"):
        return
    today = date.today()
    last = (
        date.fromisoformat(state["last_update"])
        if state["last_update"] else today
    )
    days_passed = (today - last).days
    if days_passed <= 0:
        return
    state["remaining_days"] = max(0, state["remaining_days"] - days_passed)
    state["last_update"] = today.isoformat()
    if state["remaining_days"] <= 0:
        state["remaining_days"] = 0
        state["status"] = "locked"


def fast_forward(state: dict, days: int) -> None:
    if state["status"] == "permanent":
        return
    state["remaining_days"] = max(0, state["remaining_days"] - days)
    if state["remaining_days"] <= 0:
        state["remaining_days"] = 0
        state["status"] = "locked"
    state["last_update"] = date.today().isoformat()


def _to_dict(ds: DeviceState) -> dict:
    return {
        "device_id": ds.device_id,
        "secret_key": ds.secret_key,
        "count": ds.count,
        "used_counts": list(ds.used_counts) if ds.used_counts else [],
        "remaining_days": ds.remaining_days,
        "last_update": ds.last_update.isoformat() if ds.last_update else None,
        "status": ds.status,
    }
