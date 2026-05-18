#!/usr/bin/env python3
"""PAYGO 太阳能控制器 — 终端模拟脚本 (OpenPAYGO)。

运行在安卓 Termux 环境中，模拟 PAYGO 控制器的核心行为：
Token 解码验证（OpenPAYGO 9位）、设备状态管理、天数递减。
"""

import os

from openpaygo import decode_token, TokenType
from state_manager import (
    load, save, apply_token, tick, reset,
    fast_forward,
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
    n = 0
    for c in s:
        n += 1 if ord(c) <= 127 else 2
    return n


def pad(s: str, width: int) -> str:
    return s + " " * (width - wlen(s))


def row(label: str, value: str) -> str:
    label_pad = label + " " * (LABEL_W - wlen(label))
    return "║" + pad(f" {label_pad}: {value}", INNER) + "║"


def clear_screen():
    os.system("clear")


def render(state):
    clear_screen()
    tick(state)

    key_display = state["secret_key"][:8] + "…" if state["secret_key"] else "--"
    status = state["status"]
    days = state["remaining_days"]

    print("╔══════════════════════════════╗")
    print("║" + pad("PAYGO 太阳能控制器", INNER) + "║")
    print("╠══════════════════════════════╣")
    print(row("设备密钥", key_display))
    print(row("状态", STATUS_LABELS[status]))
    if days == -1:
        print(row("剩余天数", "∞ 无限"))
    else:
        print(row("剩余天数", f"{days} 天"))
    print(row("继电器", RELAY_LABELS[status]))
    print(row("Count", str(state["count"])))
    print("╚══════════════════════════════╝")
    print()


def initial_setup(state):
    """首次运行时输入设备密钥。"""
    if state["secret_key"]:
        return
    clear_screen()
    print("╔══════════════════════════════╗")
    print("║" + pad("初始设置", INNER) + "║")
    print("╠══════════════════════════════╣")
    print("║ 请输入设备预设密钥 (32位hex) ║")
    print("╚══════════════════════════════╝")
    key = input("密钥: ").strip()
    if len(key) == 32 and all(c in "0123456789abcdefABCDEF" for c in key):
        state["secret_key"] = key
        save(state)
        print("密钥已保存，按回车键继续...")
    else:
        print("无效密钥格式，按回车键继续...")
    input()


def main():
    state = load()
    while True:
        initial_setup(state)
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
            if not state["secret_key"]:
                print("请先设置设备密钥，按回车键继续...")
                input()
                continue

            token = input("Token (9位): ").strip()
            if len(token) != 9 or not token.isdigit():
                print("✗ Token格式错误（需要9位数字），按回车键继续...")
                input()
                continue

            value, token_type, new_count, used_counts = decode_token(
                token=token,
                secret_key=state["secret_key"],
                count=state["count"],
                used_counts=state["used_counts"],
            )

            if token_type == TokenType.INVALID:
                print("✗ Token无效，按回车键继续...")
                input()
                continue
            elif token_type == TokenType.ALREADY_USED:
                print("✗ Token已使用过（防重放），按回车键继续...")
                input()
                continue

            apply_token(state, int(value) if value else 0,
                        token_type, new_count, used_counts)
            save(state)

            if token_type == TokenType.DISABLE_PAYG:
                print("✓✓✓ 贷款已结清！设备永久解锁！")
            else:
                print(f"✓ Token验证成功！增加{int(value)}天。")
            print(f"当前剩余{state['remaining_days']}天")
            print("按回车键继续...")
            input()

    print("控制器已退出。")


if __name__ == "__main__":
    main()
