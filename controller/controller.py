#!/usr/bin/env python3
"""PAYGO 太阳能控制器 — 终端模拟脚本。

运行在安卓 Termux 环境中，模拟 PAYGO 控制器的核心行为：
Token 本地解码验证、设备状态管理、天数递减。
"""

import os
import unicodedata

from token_codec import decode
from state_manager import load, save, apply_token, tick, reset


STATUS_LABELS = {
    "unbound": "未绑定",
    "active": "已激活",
    "locked": "已锁定",
}

RELAY_LABELS = {
    "unbound": "[断开]",
    "active": "[闭合] 供电中",
    "locked": "[断开] 天数用尽",
}

INNER = 28  # 内容区显示宽度


def wlen(s: str) -> int:
    """计算终端显示宽度（CJK 字符占 2，其余占 1）。"""
    n = 0
    for c in s:
        n += 2 if unicodedata.east_asian_width(c) in ("F", "W") else 1
    return n


def pad(s: str, width: int) -> str:
    """右填充空格至指定显示宽度。"""
    return s + " " * (width - wlen(s))


def clear_screen():
    os.system("clear")


def render(state):
    clear_screen()
    tick(state)

    device_display = f"#{state['device_id_hash']:04d}" if state["device_id_hash"] else "--"
    status = state["status"]
    days = state["remaining_days"]

    print("╔══════════════════════════════╗")
    print("║" + pad("PAYGO 太阳能控制器", INNER) + "║")
    print("╠══════════════════════════════╣")
    print("║" + pad(f" 设备:   {device_display}", INNER) + "║")
    print("║" + pad(f" 状态:   {STATUS_LABELS[status]}", INNER) + "║")
    print("║" + pad(f" 剩余天数: {days} 天", INNER) + "║")
    print("║" + pad(f" 继电器: {RELAY_LABELS[status]}", INNER) + "║")
    print("╚══════════════════════════════╝")
    print()


def main():
    state = load()
    while True:
        render(state)
        save(state)
        print("[N] 输入新Token  [R] 重置  [Q] 退出")
        cmd = input("> ").strip().upper()

        if cmd == "Q":
            break
        elif cmd == "R":
            confirm = input("确认重置？将清除绑定和天数 (y/N): ").strip().upper()
            if confirm == "Y":
                state = reset()
                print("已重置为未绑定状态，按回车键继续...")
                input()
            continue
        elif cmd == "N":
            token = input("Token: ").strip()
            result = decode(token)
            if result is None:
                print("无效 Token，按回车键继续...")
                input()
                continue
            apply_token(state, result["device_id_hash"], result["days"])
            save(state)
            print(f"激活成功！+{result['days']} 天，按回车键继续...")
            input()

    print("控制器已退出。")


if __name__ == "__main__":
    main()
