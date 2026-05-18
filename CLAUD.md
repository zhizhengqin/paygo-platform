# 柬埔寨太阳能PAYGO平台原型

## 项目概述
本项目是柬埔寨太阳能发电系统PAYGO（Pay-As-You-Go）平台的原型系统。通过与MFI（小额信贷机构）合作，客户可以分期付款购买太阳能系统，每次还款后系统生成激活Token延长设备使用期限。

## 业务背景
- 柬埔寨商业电价高达0.135-0.185美元/千瓦时
- 太阳能发电成本仅约0.03美元/千瓦时，成本优势超过75%
- 目标系统规模：6kW-30kW分布式太阳能系统
- 目标客户：别墅、商铺、中小型工厂、大型农场
- 合作MFI：LOLC Cambodia、PRASAC、ACLEDA等
- 支付方式：通过Bakong系统（柬埔寨国家银行数字支付平台）

## 当前原型范围

当前为**第一阶段原型**，仅包含运营后台核心功能。以下功能暂不在范围内：
- 多管理员 / 角色权限
- 在线支付集成（Bakong）
- 真实短信网关对接
- remaining_days 自动递减逻辑
- 设备端 Starting Code / DISABLE_PAYG 逻辑
- 密码加密
- 数据库持久化

后续迭代规划：
- 接入 Bakong 支付回调
- 接入 SMS 网关发送 Token
- 迁移至 PostgreSQL

## 技术栈
- 后端框架：Python FastAPI
- 前端：Jinja2 模板 + 纯 CSS（绿色主题 #059669）
- 数据库：内存 dict（原型阶段）
- Token 生成：OpenPAYGO 标准 v0.6.3（SipHash-2-4 哈希链，9 位纯数字，ADD_TIME / DISABLE_PAYG）

## Superpowers 框架配置
- 强制使用TDD：所有功能必须先写测试再写实现
- 计划先行：每个开发阶段前必须编写实施计划
- 子代理开发：复杂任务使用子代理执行
- 双重审查：规格合规审查 + 代码质量审查
- 验证前完成：所有功能必须通过测试验证
- 频繁提交：每个小步骤完成后提交代码

## 项目目录结构
```
paygo-platform/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI主应用入口
│   ├── db.py                # 内存数据库（customers + tokens + SMS + 汇率）
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # 登录/登出
│       ├── customers.py     # 客户CRUD + 模拟支付 + 锁定/永久解锁 API（OpenPAYGO）
│       └── config.py        # 支付汇率配置 API
├── controller/
│   ├── controller.py        # 终端 UI（9位Token输入/密钥绑定/count显示）
│   └── state_manager.py     # 状态机 + 持久化（secret_key/count/used_counts）
├── static/
│   └── style.css            # 全局样式（绿色主题 #059669）
├── templates/
│   ├── base.html            # 布局框架
│   ├── login.html           # 登录页
│   └── dashboard.html       # 主界面（左列表+右详情）
├── tests/
│   ├── conftest.py          # 全局 fixture + openpaygo 兼容补丁
│   ├── test_db.py           # 数据库 (16 tests)
│   ├── test_auth.py         # 认证 (6 tests)
│   ├── test_customers_api.py# 客户API (20 tests)
│   ├── test_state_manager.py# 状态机 (19 tests)
│   ├── test_config_api.py   # 支付汇率 (2 tests)
│   ├── test_controller_integration.py  # 控制器集成 (4 tests)
│   ├── test_integration.py  # 端到端集成 (3 tests)
│   └── test_upgrade.py      # 五场景 MFI 演示 (9 tests)
├── docs/
│   └── superpowers/
│       ├── specs/           # 设计文档
│       └── plans/           # 实施计划
├── requirements.txt
├── README.md
├── CLAUDE.md                # 本文件
└── AGENTS.md                # 代理角色定义
```

## 开发规范
- 强制TDD：每个功能必须先有失败的测试，再写实现代码
- 代码注释使用中文
- 所有API接口使用 `/api/` 前缀
- 认证方式：单一管理员账号 + session cookie
- 每次变更后运行全部测试验证
- 每个功能完成后编写简短的中文提交信息

## 启动命令
```bash
# 开发环境启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_db.py -v

# 访问API文档
http://localhost:8000/docs

# 访问运营后台
http://localhost:8000/dashboard
```
