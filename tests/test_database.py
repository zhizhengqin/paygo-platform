"""database.py 测试 — engine 创建、session 工厂。"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import create_engine_and_session
from app.settings import TEST_DATABASE_URL


class TestDatabase:
    async def test_engine_connects(self):
        engine, _ = create_engine_and_session(TEST_DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()

    async def test_session_factory_creates_session(self):
        engine, session_factory = create_engine_and_session(TEST_DATABASE_URL)
        async with session_factory() as session:
            assert isinstance(session, AsyncSession)
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await engine.dispose()

    async def test_session_commit_and_rollback(self):
        engine, session_factory = create_engine_and_session(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            from app.models import Base
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            from app.models import Customer
            c = Customer(id="C0001", name="Test", phone="1", device_id="D1",
                         secret_key="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
            session.add(c)
            await session.commit()

        async with engine.begin() as conn:
            from app.models import Base
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
