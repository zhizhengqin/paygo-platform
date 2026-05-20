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


def init_fernet(master_key: str = None):
    """初始化 Fernet 加密器。若未提供 master_key 则从环境变量读取，仍无则自动生成。"""
    global _fernet
    key = master_key or SECRET_KEY_MASTER_KEY
    if not key:
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        logger.warning(
            "未设置 SECRET_KEY_MASTER_KEY 环境变量，已自动生成临时密钥。"
            "生产环境必须通过环境变量注入以确保持久化！"
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
