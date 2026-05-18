#!/usr/bin/env python3
"""PAYGO 太阳能控制器 — 终端模拟脚本 (OpenPAYGO)。"""

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

RELAY_ON = "● 供电中"
RELAY_OFF = "○ 断开"


def clear_screen():
    os.system("clear")


def render(state):
    clear_screen()
    tick(state)

    key = state["secret_key"]
    key_display = key[:8] + "…" if key else "（未设置）"
    status = state["status"]
    days = state["remaining_days"]

    if days == -1:
        days_text = "∞"
    else:
        days_text = f"{days} 天"

    relay = RELAY_ON if status in ("active", "permanent") else RELAY_OFF

    print("── 太阳能控制器 ────────────────────────────")
    print(f"  密钥      {key_display}")
    if status == "permanent":
        print(f"  状态      {STATUS_LABELS[status]} · {days_text}")
    elif days == 0 and status == "unbound":
        print(f"  状态      {STATUS_LABELS[status]} · {days_text}")
    else:
        print(f"  状态      {STATUS_LABELS[status]} · 剩余 {days_text}")
    print(f"  继电器    {relay}")
    print(f"  Count     {state['count']}")
    print("─────────────────────────────────────────────")
    print("  [N] 输入Token  [D] 快进天数  [R] 重置  [Q] 退出")


def initial_setup(state):
    if state["secret_key"]:
        return
    clear_screen()
    print("── 初始设置 ──────────────────────────────")
    print("  请输入设备预设密钥（32位 hex）")
    key = input("  > ").strip()
    if len(key) == 32 and all(c in "0123456789abcdefABCDEF" for c in key):
        state["secret_key"] = key
        save(state)
        print("  密钥已保存")
    else:
        print("  无效密钥格式")
    input("  按回车键继续…")


def main():
    state = load()
    while True:
        initial_setup(state)
        render(state)
        save(state)
        cmd = input("> ").strip().upper()

        if cmd == "Q":
            break
        elif cmd == "R":
            confirm = input("  确认重置？将清除密钥和天数 (y/N): ").strip().upper()
            if confirm == "Y":
                state = reset()
        elif cmd == "D":
            try:
                days = int(input("  快进天数: ").strip())
            except ValueError:
                print("  无效天数")
                input("  按回车键继续…")
                continue
            fast_forward(state, days)
            save(state)
            print(f"  ✓ 已快进 {days} 天 · 剩余 {state['remaining_days']} 天")
            input("  按回车键继续…")
        elif cmd == "N":
            if not state["secret_key"]:
                print("  请先设置设备密钥")
                input("  按回车键继续…")
                continue

            token = input("  Token (9位): ").strip()
            if len(token) != 9 or not token.isdigit():
                print("  ✗ Token 格式错误（需要9位数字）")
                input("  按回车键继续…")
                continue

            value, token_type, new_count, used_counts = decode_token(
                token=token,
                secret_key=state["secret_key"],
                count=state["count"],
                used_counts=state["used_counts"],
            )

            if token_type == TokenType.INVALID:
                print("  ✗ Token 无效")
                input("  按回车键继续…")
            elif token_type == TokenType.ALREADY_USED:
                print("  ✗ Token 已使用过（防重放）")
                input("  按回车键继续…")
            else:
                days = int(value) if value else 0
                apply_token(state, days, token_type, new_count, used_counts)
                save(state)

                if token_type == TokenType.DISABLE_PAYG:
                    print("  ✓✓ 贷款已结清 · 设备永久解锁")
                else:
                    print(f"  ✓ 验证成功 · +{days} 天 · 剩余 {state['remaining_days']} 天")
                input("  按回车键继续…")

    print("控制器已退出。")


if __name__ == "__main__":
    main()
