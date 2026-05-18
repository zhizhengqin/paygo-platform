"""Token 生成模块。

生成 15 位结构化 Token: {device_hash:5}{value:4}{type:2}{checksum:4}
- type=01: 激活Token (PAY), value 编码天数
- type=99: 永久解锁Token (DISABLE_PAYG), value 填 0000

与 controller/token_codec.py 实现相同算法，修改时两处一起改。
"""


def generate_token(device_id: str, days: int) -> str:
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
