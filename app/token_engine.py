import random


def generate_token(device_id: str, days: int) -> str:
    """生成 8 位随机数字 Token。
    后续切换 OpenPAYGO 时只需修改此函数内部实现。
    """
    return ''.join(random.choices('0123456789', k=8))
