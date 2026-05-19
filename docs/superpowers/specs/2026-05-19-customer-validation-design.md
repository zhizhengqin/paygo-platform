# 客户数据校验 — device_id 唯一 + 密钥 1:1 绑定

**日期:** 2026-05-19
**状态:** 已确认

## 目标

在创建客户时增加校验逻辑，确保 device_id 唯一、secret_key 与 device 1:1 绑定，防止测试数据混乱。

## 校验规则

1. **device_id 唯一** — 一个设备编号只能属于一个客户
2. **secret_key 1:1 绑定** — 一个密钥只能绑定一个设备

## 实现方案

三层防护：DB 约束 → Store 层前置检查 → Router 层友好错误

### 模型层 (models.py)

`device_id` 和 `secret_key` 加 `unique=True` 约束。

### Store 层 (store.py)

- 新增 `DuplicateDeviceError(device_id)` 和 `DuplicateSecretKeyError(secret_key)` 自定义异常
- `add_customer` 插入前 SELECT 检查重复，重复则 raise 对应异常

### Router 层 (customers.py)

- 捕获 `DuplicateDeviceError` → 409 + "设备编号 'XXX' 已被其他客户使用"
- 捕获 `DuplicateSecretKeyError` → 409 + "该密钥已绑定到其他设备"

## 改动文件

| 文件 | 改动 |
|------|------|
| `app/models.py` | device_id + secret_key 加 unique=True |
| `app/store.py` | 新增异常类 + add_customer 重复检查 |
| `app/routers/customers.py` | 捕获异常返回 409 |
| `tests/test_store.py` | 新增 2 个测试 |
| `tests/test_customers_api.py` | 新增 2 个测试 |

## 测试策略

- test_store.py: 重复 device_id 被拒绝、重复 secret_key 被拒绝
- test_customers_api.py: POST 相同 device_id 返回 409、POST 相同 secret_key 返回 409
