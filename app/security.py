"""安全工具 — bcrypt 密码哈希 + Fernet 密钥加解密"""
import base64
import os
import logging

import bcrypt
from cryptography.fernet import Fernet, InvalidToken

from app.settings import SECRET_KEY_MASTER_KEY

logger = logging.getLogger("paygo.security")

_fernet = None


def hash_password(password: str) -> str:
    """bcrypt 哈希密码，返回哈希字符串。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配 bcrypt 哈希。处理无效哈希格式。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _persist_fernet_key(key_b64: str):
    """将 Fernet 密钥持久化到 .env 文件，确保跨进程一致。"""
    import os as _os
    env_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), ".env")
    try:
        existing = ""
        if _os.path.exists(env_path):
            with open(env_path) as f:
                existing = f.read()
        line = f"SECRET_KEY_MASTER_KEY={key_b64}\n"
        if "SECRET_KEY_MASTER_KEY" in existing:
            existing_lines = existing.split("\n")
            new_lines = [line if "SECRET_KEY_MASTER_KEY" in l else l for l in existing_lines]
            with open(env_path, "w") as f:
                f.write("\n".join(new_lines))
        else:
            with open(env_path, "a") as f:
                f.write(line)
    except Exception:
        pass  # 非关键操作，失败不影响功能


def init_fernet(master_key: str = None):
    """初始化 Fernet 加密器。若未提供 master_key 则从环境变量读取，仍无则自动生成。"""
    global _fernet
    key = master_key or SECRET_KEY_MASTER_KEY
    if not key:
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        _persist_fernet_key(key)
        logger.warning(
            "未设置 SECRET_KEY_MASTER_KEY 环境变量，已自动生成密钥并持久化到 .env 文件。"
        )
    if isinstance(key, str):
        key = key.encode("utf-8")
    _fernet = Fernet(key)
    return _fernet


def _get_fernet():
    """获取当前 Fernet 实例，未初始化则自动初始化。"""
    global _fernet
    if _fernet is None:
        init_fernet()
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """加密 secret key，返回 base64 密文。"""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str):
    """解密 secret key，返回明文字符串。失败返回 None。"""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        return None


# ---- JWT Token 工具 ----

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.settings import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS


def create_access_token(data: dict) -> str:
    """生成 JWT access token，默认 15 分钟过期。"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """生成 JWT refresh token，默认 7 天过期。"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """解码 JWT token，失败返回 None。"""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
