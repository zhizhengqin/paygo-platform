# 控制器重新部署步骤

## 第 1 步（Mac 终端）：清除旧文件并重新推送

```bash
cd ~/Desktop/paygo-platform
~/Library/Android/sdk/platform-tools/adb shell rm -rf /sdcard/controller
~/Library/Android/sdk/platform-tools/adb push controller/ /sdcard/controller/
~/Library/Android/sdk/platform-tools/adb shell "grep 'def reset' /sdcard/controller/state_manager.py"
```

第三条应输出 `def reset() -> dict:`，确认推送成功。

## 第 2 步（模拟器 Termux）：清除旧工作目录并重新复制

```bash
rm -rf ~/controller && cp -r /sdcard/controller ~/controller && grep "def reset" ~/controller/state_manager.py
```

应输出 `def reset() -> dict:`。

## 第 3 步（模拟器 Termux）：运行

```bash
cd ~/controller && python controller.py
```

菜单应显示 `[N] 输入新Token  [R] 重置  [Q] 退出`。
