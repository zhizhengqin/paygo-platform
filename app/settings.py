"""应用配置 — 数据库连接、Redis 连接、缓存 TTL 等。"""
import os

# 加载 .env 文件中的环境变量（如 SECRET_KEY_MASTER_KEY）
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key, val)

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

# 安全配置
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

# Secret Key 加密主密钥 (Fernet key, base64 编码)
SECRET_KEY_MASTER_KEY = os.getenv(
    "SECRET_KEY_MASTER_KEY", ""
)

# JWT 配置
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "paygo-jwt-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE", "15"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE", "7"))

# 限流配置
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
LOGIN_RATE_LIMIT_PER_MINUTE = int(os.getenv("LOGIN_RATE_LIMIT_PER_MINUTE", "10"))
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
