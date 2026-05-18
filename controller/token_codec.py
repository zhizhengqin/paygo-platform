"""PAYGO Token 编解码模块。

Token 格式 (15位数字): {device_hash:5}{value:4}{type:2}{checksum:4}
- device_hash = sum(ord(c) for c in device_id) % 100000
- value = 天数 (1-3650)，type=99 时填 0000
- type = 01(激活) 或 99(永久解锁)
- checksum = (device_hash + value + type) % 10000

⚠ 算法与 app/token_engine.py 必须保持同步，修改时两处一起改。
"""

VALID_TYPES = {1, 99}


def generate(device_id: str, days: int) -> str:
    """生成 15 位数字 Token。

    days 为 -1 时生成 DISABLE_PAYG Token (type=99, value=0000)。
    否则生成激活 Token (type=01)，天数范围 1-3650。
    """
    char_sum = sum(ord(c) for c in device_id)
    device_hash = char_sum % 100000

    if days == -1:
        value = 0
        token_type = 99
    else:
        if not (1 <= days <= 3650):
            raise ValueError(f"days 必须在 1-3650 之间，收到 {days}")
        value = days
        token_type = 1

    checksum = (device_hash + value + token_type) % 10000
    return f"{device_hash:05d}{value:04d}{token_type:02d}{checksum:04d}"


def decode(token: str) -> dict | None:
    """解码 15 位 Token，返回 {'device_id_hash': int, 'days': int, 'type': int} 或 None。"""
    if len(token) != 15 or not token.isdigit():
        return None
    device_hash = int(token[:5])
    value = int(token[5:9])
    token_type = int(token[9:11])
    checksum = int(token[11:15])
    expected = (device_hash + value + token_type) % 10000
    if checksum != expected:
        return None
    if token_type not in VALID_TYPES:
        return None
    days = 0 if token_type == 99 else value
    return {"device_id_hash": device_hash, "days": days, "type": token_type}
