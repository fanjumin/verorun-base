# Coupon Management — 清理方案

## 一、现状：双重系统并行

```
主库 (easykai.db)
├── coupons 表          ← ⚠️ 仍在 database.py 中 CREATE TABLE
├── coupon_redemptions 表  ← ⚠️ 同上
│
主库路由 (sub_bp → subscription/__init__.py)
├── GET  /subscription/admin/coupons   ← ⚠️ 完整 CRUD（重复）
├── POST /subscription/admin/coupons   ← ⚠️ 同上
├── _apply_coupon()                    ← ⚠️ 订阅结算时直接操作 coupons 表
│
主库服务 (completion_service.py)
├── reward_claims 流程直接读写 coupons / coupon_redemptions  ← ⚠️ 表已不存在
│
用户端路由 (user_bp → user.py)
├── GET /user/coupons → 桥接到 plugins.coupons          ← ⚠️ 路由没移过去
│
插件 (plugins/coupons/)
├── couons.db (独立库)
├── /plugin/coupons/admin/list    ← ✅ 管理 API
├── /plugin/coupons/user/list     ← ✅ 用户 API
├── /plugin/coupons/validate      ← ✅ 验证 API
└── /plugin/coupons/apply         ← ✅ 应用 API
```

## 二、当前问题

### 问题 1: 403 FORBIDDEN（致命）

插件 `routes.py` 的 `_require_auth()` 使用硬编码回退密钥：

```python
secret = current_app.config.get('JWT_SECRET', 'verorun-jwt-secret-2025')
```

而 admin 服务的 `JWT_SECRET` 来自环境变量 `os.environ.get('JWT_SECRET')`，两者不匹配 → Token 解码失败 → 403。

**修复：改为复用 `auth-center/services/jwt_service.py` 的 `validate_token()`**

### 问题 2: 订阅模块完整重复

`subscription/__init__.py` 中有**完整的一套券管理**：
- `admin_coupon_list()` / `admin_coupon_create()` → 操作主库 `coupons` 表
- `_apply_coupon()` → 订阅结算时直接读 `coupons` + 写 `coupon_redemptions`

因为主库的 `coupons` 表还在，这能运行，但**两个系统互不知晓对方的数据**。

### 问题 3: completion_service.py 直接读主库 coupons 表

`services/completion_service.py` 在发放奖励时直接 `SELECT * FROM coupons`，但主库的 `coupons` 表已经空了（数据已迁移到插件独立库）。这个功能现在必定报错。

### 问题 4: coupons 表残留在主库 schema

`database.py` 中 `coupons` 和 `coupon_redemptions` 的 `CREATE TABLE` 还在。`sync_schema.py` 的排除列表里没有它们。

### 问题 5: reward_rules.html 调用旧接口

`admin/templates/partials/reward_rules.html:69` 调用 `/subscription/admin/coupons`，应改为 `/plugin/coupons/bridge/list`。

## 三、清理方案

### 3.1 修复 403（P0）

| 改动文件 | 改动内容 |
|----------|----------|
| `plugins/coupons/routes.py` | `_require_auth()` 中改掉硬编码 `JWT_SECRET`，复用 `auth-center/services/jwt_service.py` 或 `current_app.config['JWT_SECRET']`（env 的值） |

### 3.2 清理主库注册表（P1）

| 改动文件 | 改动内容 |
|----------|----------|
| `auth-center/models/database.py` | 删除 `coupons` 和 `coupon_redemptions` 的 `CREATE TABLE` |

### 3.3 改造订阅模块 → 走插件（P1）

| 改动文件 | 改动内容 |
|----------|----------|
| `auth-center/routes/subscription/__init__.py` | 删除 `admin_coupon_list()` / `admin_coupon_create()` |
| 同上 | `_apply_coupon()` 改造为调用插件 `engine.validate() + engine.apply_to_order()` |
| 同上 | `checkout` 流程中 `coupon_code` 改为走插件验证 |

### 3.4 改造 completion_service → 走插件（P1）

| 改动文件 | 改动内容 |
|----------|----------|
| `auth-center/services/completion_service.py` | `reward_type == 'coupon'` 的处理改为调用 `plugins.coupons.get_engine().distribute()` |

### 3.5 移走 user.py 桥接路由（P1）

| 改动文件 | 改动内容 |
|----------|----------|
| `auth-center/routes/user.py` | 删除 `get_user_coupons()`（`/user/coupons` 路由） |
| `admin/templates/partials/reward_rules.html` | 将 `/subscription/admin/coupons` → `/plugin/coupons/bridge/list` |

### 3.6 sync_schema.py 加排除（P1）

| 改动文件 | 改动内容 |
|----------|----------|
| `scripts/sync_schema.py` | 排除列表增加 `coupons`, `coupon_redemptions` |

### 3.7 删除主库残留表（P2，确认无误后）

- 在本地和服务器上验证功能正常后，手动 DROP TABLE `coupons` / `coupon_redemptions`

## 四、执行顺序

```
修复 403（P0）
    │
    ▼
改造 subscription:_apply_coupon() → 走插件    同步：sync_schema.py 加排除
    │                                              │
    ▼                                              ▼
改造 completion_service → 走插件            清理 database.py CREATE TABLE
    │
    ▼
删除 user.py 桥接 / 更新 reward_rules.html
    │
    ▼
验证：所有券功能正常
    │
    ▼
删除主库残留池表（DROP TABLE）
```

## 五、依赖

- `plugins/coupons/engine.py` 需要暴露与 `_apply_coupon()` 功能等价的方法（现已实现 `apply_to_order()` 和 `validate()`）
- 订阅结算是核心功能，改动需要先验证再上线
