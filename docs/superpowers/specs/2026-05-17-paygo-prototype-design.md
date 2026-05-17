# 柬埔寨太阳能 PAYGO 平台原型 — 设计文档

**日期**: 2026-05-17  
**状态**: 已确认  
**目标**: 构建一个可在本地运行的原型，演示 PAYGO 太阳能设备按需付费的核心流程

---

## 1. 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | API + 模板渲染一体化，自动 Swagger 文档 |
| 前端 | Jinja2 模板 | 服务端渲染，无需构建工具 |
| 样式 | 纯 CSS | 绿色能源风（主色 #059669） |
| 数据库 | 内存 dict | 原型简化，重启清空 |
| Token 生成 | 随机数字串 | 预留 `token_engine.py` 接口，后续切换 OpenPAYGO |

## 2. 项目结构

```
paygo-platform/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI 入口，挂载路由和静态文件
│   ├── db.py              # 内存数据库，暴露 customers / tokens 两个 store
│   ├── token_engine.py    # Token 生成模块（接口预留）
│   └── routers/
│       ├── __init__.py
│       ├── auth.py        # 登录 / 登出
│       └── customers.py   # 客户 CRUD + Token 生成
├── static/
│   └── style.css          # 全局样式（绿色主题）
├── templates/
│   ├── base.html          # 布局框架（HTML 骨架、导航栏）
│   ├── login.html         # 登录页
│   └── dashboard.html     # 主界面：左列表 + 右详情面板
└── tests/
    └── __init__.py
```

## 3. 数据模型

### customers (dict)

```python
{
    "C001": {
        "id": "C001",
        "name": "Sok Heng",
        "phone": "0888888001",
        "device_id": "Solar-001",
        "remaining_days": 15,
        "status": "active",    # active | expired | disabled
        "created_at": "2026-05-15",
    }
}
```

### tokens (list)

```python
[
    {
        "id": "T001",
        "customer_id": "C001",
        "token": "48291736",
        "days": 30,
        "generated_at": "2026-05-17 14:30:00",
        "expires_at": "2026-05-24 14:30:00",  # 7 天有效期
    }
]
```

## 4. 路由设计

### 页面路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/login` | 登录页面 |
| POST | `/login` | 提交登录（验证账号密码） |
| GET | `/dashboard` | 主界面（需登录） |
| GET | `/logout` | 退出登录 |

### API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/customers` | 新增客户 |
| GET | `/api/customers/{id}` | 获取客户详情 |
| DELETE | `/api/customers/{id}` | 删除客户 |
| POST | `/api/customers/{id}/token` | 为该客户生成 Token |
| GET | `/api/tokens` | Token 历史列表 |

## 5. 页面流程

```
/login → 输入账号密码 → 验证通过 → /dashboard
                                       ├── 左侧：客户列表
                                       ├── 右侧：选中客户详情
                                       └── [生成Token] → 弹窗输入天数 → 显示Token码
```

## 6. Token 引擎设计

`token_engine.py` 暴露以下接口：

```python
def generate_token(device_id: str, days: int) -> str:
    """原型阶段生成 8 位随机数字串"""
    import random
    return ''.join(random.choices('0123456789', k=8))

# 后续切换 OpenPAYGO 时接口不变，内部改用:
# from openpaygo import OpenPAYGO
# op = OpenPAYGO(secret_key)
# return op.generate(device_id, days, counter)
```

## 7. 认证设计

- 单管理员账号，用户名密码写死在配置常量中
- 登录成功后设置 session cookie
- 页面路由检查 cookie，未登录重定向到 `/login`
- 无需多用户、无需密码加密

## 8. 短信网关预留

当前不接入真实网关。Token 生成后在页面直接显示。预留接口：

```python
def send_sms(phone: str, message: str):
    """原型阶段 print 到控制台，后续接入真实网关"""
    print(f"[SMS to {phone}]: {message}")
```

## 9. 视觉风格

- **主色**: Emerald 绿 `#059669`，白底
- **布局**: 左侧客户列表卡片 + 右侧详情面板（选中后显示）
- **Token 弹窗**: 居中大卡片，Token 码大字突出显示
- **风格**: 简洁干净，适合演示
- **参考**: Apple 设计理念——留白、清晰层次、无多余装饰

## 10. 不在范围内

- 多管理员 / 角色权限
- 在线支付集成
- 真实短信网关对接
- remaining_days 自动递减逻辑
- 密码加密
- 数据库持久化
