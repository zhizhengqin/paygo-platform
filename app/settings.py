"""应用配置 — 数据库连接、Redis 连接、缓存 TTL 等。"""
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform",
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://paygo_user:PaygoDB2026!@localhost:5432/paygo_platform_test",
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 连接池
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))

# 缓存 TTL（秒）
CACHE_TTL_API = int(os.getenv("CACHE_TTL_API", "60"))
SESSION_TTL = int(os.getenv("SESSION_TTL", "1800"))       # 30 min
ANTIREPLAY_TTL = int(os.getenv("ANTIREPLAY_TTL", "604800"))  # 7 days
