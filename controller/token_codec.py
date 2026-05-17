"""PAYGO Token 编解码模块。

Token 格式 (8位数字): {device_hash:4位}{days:3位}{checksum:1位}
- device_hash = sum(ord(c) for c in device_id) % 10000
- days = 天数 (1-365)
- checksum = (device_hash + days) % 10
"""


def generate(device_id: str, days: int) -> str:
    """生成 8 位数字 Token，编码 device_id 哈希 + 天数 + 校验位。"""
    char_sum = sum(ord(c) for c in device_id)
    device_hash = char_sum % 10000
    checksum = (device_hash + days) % 10
    return f"{device_hash:04d}{days:03d}{checksum}"


def decode(token: str) -> dict | None:
    """解码 8 位 Token，返回 {'device_id_hash': int, 'days': int} 或 None。"""
    if len(token) != 8 or not token.isdigit():
        return None
    device_hash = int(token[:4])
    days = int(token[4:7])
    checksum = int(token[7])
    expected = (device_hash + days) % 10
    if checksum != expected:
        return None
    return {"device_id_hash": device_hash, "days": days}
