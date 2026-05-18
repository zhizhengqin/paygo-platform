#!/usr/bin/env python3
"""PAYGO 太阳能控制器 — 终端模拟脚本。

运行在安卓 Termux 环境中，模拟 PAYGO 控制器的核心行为：
Token 本地解码验证（15位）、设备状态管理、天数递减。
"""

import os

from token_codec import decode
from state_manager import (
    load, save, apply_token, tick, reset,
    fast_forward, is_token_used, mark_token_used,
)


STATUS_LABELS = {
    "unbound": "未绑定",
    "active": "已激活",
    "locked": "已锁定",
    "permanent": "永久解锁",
}

RELAY_LABELS = {
    "unbound": "[断开]",
    "active": "[闭合] 供电中",
    "locked": "[断开] 天数用尽",
    "permanent": "[闭合] 供电中",
}

INNER = 28
LABEL_W = 8


def wlen(s: str) -> int:
    """计算终端显示宽度：ASCII 占 1，其余占 2。"""
    n = 0
    for c in s:
        n += 1 if ord(c) <= 127 else 2
    return n


def pad(s: str, width: int) -> str:
    """右填充空格至指定显示宽度。"""
    return s + " " * (width - wlen(s))


def row(label: str, value: str) -> str:
    """生成对齐行：标签对齐 → 冒号 → 值 → 右边框。"""
    label_pad = label + " " * (LABEL_W - wlen(label))
    return "║" + pad(f" {label_pad}: {value}", INNER) + "║"


def clear_screen():
    os.system("clear")


def render(state):
    clear_screen()
    tick(state)

    device_display = f"#{state['device_id_hash']:05d}" if state["device_id_hash"] else "--"
    status = state["status"]
    days = state["remaining_days"]

    print("╔══════════════════════════════╗")
    print("║" + pad("PAYGO 太阳能控制器", INNER) + "║")
    print("╠══════════════════════════════╣")
    print(row("设备", device_display))
    print(row("状态", STATUS_LABELS[status]))
    if days == -1:
        print(row("剩余天数", "∞ 无限"))
    else:
        print(row("剩余天数", f"{days} 天"))
    print(row("继电器", RELAY_LABELS[status]))
    print("╚══════════════════════════════╝")
    print()


def main():
    state = load()
    while True:
        render(state)
        save(state)
        print("[N] 输入新Token  [D] 模拟天数流逝  [R] 重置  [Q] 退出")
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
        elif cmd == "D":
            try:
                days_input = input("快进天数: ").strip()
                days = int(days_input)
            except ValueError:
                print("无效天数，按回车键继续...")
                input()
                continue
            fast_forward(state, days)
            save(state)
            print(f"已快进 {days} 天，按回车键继续...")
            input()
            continue
        elif cmd == "N":
            token = input("Token: ").strip()
            # 15位校验
            if len(token) != 15 or not token.isdigit():
                print("✗ Token无效，按回车键继续...")
                input()
                continue

            result = decode(token)
            if result is None:
                print("✗ Token无效，按回车键继续...")
                input()
                continue

            # 防重放检查
            if is_token_used(token):
                print("Token已过期，按回车键继续...")
                input()
                continue

            # 应用 Token
            apply_token(state, result["device_id_hash"], result["days"], result["type"])
            mark_token_used(token)
            save(state)

            if result["type"] == 99:
                print("✓✓✓ 贷款已结清！设备永久解锁！")
            else:
                print(f"✓ Token验证成功！增加{result['days']}天。")
            print(f"当前剩余{state['remaining_days']}天")
            print("按回车键继续...")
            input()

    print("控制器已退出。")


if __name__ == "__main__":
    main()
