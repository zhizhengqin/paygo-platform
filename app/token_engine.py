"""Token 生成模块。

生成 8 位结构化 Token: {device_hash:4}{days:3}{checksum:1}
与 controller/token_codec.py 实现相同算法。
"""


def generate_token(device_id: str, days: int) -> str:
    """生成 8 位数字 Token，编码 device_id 哈希 + 天数 + 校验位。"""
    char_sum = sum(ord(c) for c in device_id)
    device_hash = char_sum % 10000
    checksum = (device_hash + days) % 10
    return f"{device_hash:04d}{days:03d}{checksum}"
