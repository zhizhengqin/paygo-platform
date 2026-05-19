"""PostgreSQL 连接池 + session 工厂 + FastAPI Depends 注入。"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.settings import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW


def create_engine_and_session(database_url: str = None):
    """创建 async engine 和 session 工厂。可传入 database_url 覆盖（测试用）。"""
    url = database_url or DATABASE_URL
    engine = create_async_engine(
        url,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


# 全局 engine + session 工厂
engine, AsyncSessionLocal = create_engine_and_session()


async def get_db() -> AsyncSession:
    """FastAPI Depends: 每个请求注入一个独立 AsyncSession，结束后自动关闭。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
