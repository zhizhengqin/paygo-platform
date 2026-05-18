# 控制器重新部署步骤

代码更新后，按以下步骤部署到模拟器。

## 第 1 步（Mac 终端）：推送新文件

```bash
cd ~/Desktop/paygo-platform && ~/Library/Android/sdk/platform-tools/adb shell rm -rf /sdcard/controller && ~/Library/Android/sdk/platform-tools/adb push controller/ /sdcard/controller/ && ~/Library/Android/sdk/platform-tools/adb shell "grep 'def reset' /sdcard/controller/state_manager.py"
```

应输出 `def reset() -> dict:`，确认推送成功。

## 第 2 步（模拟器 Termux）：替换工作目录

```bash
rm -rf ~/controller && cp -r /sdcard/controller ~/controller && rm -rf ~/controller/__pycache__ && grep "def reset" ~/controller/state_manager.py
```

应输出 `def reset() -> dict:`。

> 同时清除 `__pycache__` 避免 Python 加载缓存的旧字节码。

## 第 3 步（模拟器 Termux）：运行

```bash
cd ~/controller && python controller.py
```

菜单应显示 `[N] 输入新Token  [R] 重置  [Q] 退出`。
