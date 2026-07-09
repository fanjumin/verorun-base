# Coupon Management — 合并清理方案

## 目标

将主库和订阅模块中残留的优惠券系统**全部合并到插件**，统一数据 + 统一逻辑 + 统一接口。

---

## 一、改动清单（14 处）

### 1.1 插件新增字段

**文件**：`plugins/coupons/models.py`

coupons 表新增 `applicable_plans` 字段（订阅独有，限制适用套餐）：

```sql
ALTER TABLE coupons ADD COLUMN applicable_plans TEXT DEFAULT '';
```

同步更新 `init_db()` 中 `CREATE TABLE`。

---

### 1.2 插件 engine 新增 `plan` 参数

**文件**：`plugins/coupons/engine.py`

- `__init__()` — 无变化
- `validate()` — 参数增加 `plan: str = None`
  - 如果 `applicable_plans` 有值且 `plan` 传入，校验套餐归属
- `apply_to_order()` — 无变化，沿袭使用
- `_calc_discount()` — 无变化

---

### 1.3 插件 routes.py — 修复 403

**文件**：`plugins/coupons/routes.py`

`_require_auth()` 中改掉硬编码回退密钥：

```python
# 改为走 auth-center 的 jwt_service
from services.jwt_service import validate_token
```

或者直接用环境变量值。关键是 admin 服务的 `JWT_SECRET` 来自 env，插件要用同一个。

---

### 1.4 插件 routes.py — i18n 标准化

**文件**：`plugins/coupons/routes.py`

当前 `_t()` 是在 `init_routes()` 时注入的，但内联在 `register_routes()` 中时 `self.t()` 作用域可能出问题。需改为：

- 删除 `_t = None` + `init_routes()` 的 t_func 参数
- routes.py 中直接用 `_()` 从 `flask_babel import gettext`（与系统其他路由一致）
- 如果插件不想依赖 flask_babel，在 `coupon_bp.before_request` 统一设置

---

### 1.5 删除订阅模块重复 CRUD

**文件**：`auth-center/routes/subscription/__init__.py`

- 删除 `admin_coupon_list()` (L997-1003)
- 删除 `admin_coupon_create()` (L1005-1038)
- 保留 `_apply_coupon()` 暂时不改（1.6 处理）

---

### 1.6 改造订阅模块 `_apply_coupon()` → 走插件

**文件**：`auth-center/routes/subscription/__init__.py`

`_apply_coupon(code, user_id, plan_key, amount_fen)` 替换为：

```python
def _apply_coupon(code, user_id, plan_key, amount_fen):
    """走插件引擎验证优惠券"""
    from plugins.coupons import get_engine
    engine = get_engine()
    if not engine:
        return 0
    result = engine.validate(code, amount_fen / 100.0,
                              user_id=user_id, plan=plan_key)
    if not result['valid']:
        return 0
    # 插件 engine 用元，订阅用分
    return int(result['discount'] * 100)
```

注意：`validate()` 返回的 `discount` 单位是**元**，订阅模块用**分**，所以 `* 100`。

注意：订阅的结算流程原来在 `_apply_coupon()` 内直接 `UPDATE coupons SET used_count+1` 和 `INSERT coupon_redemptions`，改造后这部分由 `apply_to_order()` 完成。所以 checkout 流程还需要调用 `apply_to_order()` 写使用记录。

---

### 1.7 编辑 subscription 的 checkout 流程

**文件**：`auth-center/routes/subscription/__init__.py`（L336-337 附近）

```python
# 原来：
discount_fen = _apply_coupon(coupon_code, uid, plan_key, amount_fen)

# 改为：
from plugins.coupons import get_engine
engine = get_engine()
result = engine.validate(coupon_code, amount_fen / 100.0, user_id=uid, plan=plan_key)
discount_fen = int(result['discount'] * 100) if result.get('valid') else 0
# 同时记录使用
if result.get('valid') and result.get('coupon'):
    engine.apply_to_order(coupon_code, uid, order_no, amount_fen / 100.0)
```

---

### 1.8 改造 completion_service → 走插件

**文件**：`auth-center/services/completion_service.py`

原来直接 `SELECT * FROM coupons` + `INSERT INTO coupon_redemptions`，改为：

```python
if rule['reward_type'] == 'coupon' and rule['reward_id']:
    from plugins.coupons import get_engine
    engine = get_engine()
    if engine:
        count = engine.distribute(rule['reward_id'], [user_id])
        coupon_id = ...  # 从 distribute 返回
```

注意：`engine.distribute()` 返回的是 count（int），不返回 coupon_id。需要确认 `reward_claims.coupon_id` 字段是否仍需要，如果不需要可直接去掉。

---

### 1.9 删除 user.py 桥接路由

**文件**：`auth-center/routes/user.py`

- 删除 `get_user_coupons()` — L1800-1816

前端用户端的 `/user/coupons` 由插件自己的 `/plugin/coupons/user/list` 替代（`coupons_plugin.html` 已经用了 `/plugin/coupons/...`）。

---

### 1.10 修复 reward_rules.html

**文件**：`admin/templates/partials/reward_rules.html`

- L69：`fetch("/subscription/admin/coupons")` → `fetch("/plugin/coupons/bridge/list")`

---

### 1.11 清理 database.py（主库 schema）

**文件**：`auth-center/models/database.py`

- 删除 `coupons` 表的 `CREATE TABLE IF NOT EXISTS`（database.py L869 附近）
- 删除 `coupon_redemptions` 表的相关定义（L1689 附近）

---

### 1.12 更新 sync_schema.py 排除列表

**文件**：`scripts/sync_schema.py`

- 排除列表增加 `coupons`, `coupon_redemptions`

---

### 1.13 删除主库残留表（确认后执行）

**操作**：手动执行 SQL（本地 + 服务器）

```sql
DROP TABLE IF EXISTS coupons;
DROP TABLE IF EXISTS coupon_redemptions;
```

**时机**：前面所有改动完成并验证功能无误后。

---

### 1.14 创建 plugin.json（如果缺少）

**文件**：`plugins/coupons/plugin.json`

目前 `plugins/coupons/` 下是否有 `plugin.json`？如果没有，plugin_manager 扫描不到它。

```json
{
  "name": "Coupon Engine",
  "version": "0.1.0",
  "description": "智能优惠券引擎 - 场景券/AI推荐/订阅联动",
  "author": "VeroRun",
  "min_app_version": "1.0.0",
  "dependencies": {},
  "settings_schema": {},
  "config": {}
}
```

---

## 二、涉及文件汇总

| # | 文件 | 操作 | 规模 |
|---|------|------|------|
| 1 | `plugins/coupons/models.py` | 加字段 | 小 |
| 2 | `plugins/coupons/engine.py` | 加 plan 参数 | 小 |
| 3 | `plugins/coupons/routes.py` | 修复 JWT + i18n | 中 |
| 4 | `plugins/coupons/plugin.json` | 新建 | 小 |
| 5 | `auth-center/routes/subscription/__init__.py` | 删除 CRUD + 改造 apply | 中 |
| 6 | `auth-center/services/completion_service.py` | 改走插件 | 中 |
| 7 | `auth-center/routes/user.py` | 删除桥接 | 小 |
| 8 | `auth-center/models/database.py` | 删 CREATE TABLE | 小 |
| 9 | `admin/templates/partials/reward_rules.html` | 换 URL | 小 |
| 10 | `scripts/sync_schema.py` | 加排除 | 小 |

---

## 三、执行顺序

```
第一阶段：插件增强
  1. models.py — 加 applicable_plans 字段
  2. engine.py — validate() 加 plan 参数校验
  3. routes.py — 修复 JWT 校验（403 根因）
  4. routes.py — i18n 统一处理
  5. plugin.json — 新建
  → 验证：管理页 /plugin/coupons/admin/list 不再 403

第二阶段：系统侧清理
  6. subscription/__init__.py — 删除重复 CRUD
  7. subscription/__init__.py — checkout 流程改走插件
  8. completion_service.py — 改走插件
  9. user.py — 删除桥接
  10. reward_rules.html — 换 URL

第三阶段：数据库清理
  11. sync_schema.py — 加排除
  12. database.py — 删 CREATE TABLE
  13. 验证功能正常后 → DROP 主库旧表

第四阶段：部署
  14. git 提交
  15. rsync 到服务器
  16. 重启服务
  17. 验证
```

---

## 四、风险点

| 风险 | 缓解 |
|------|------|
| 订阅结算功能出问题 | 先在本地完整测试 checkout 流程，再上线 |
| JWT_SECRET 不匹配导致 403 反复 | 统一走 `services.jwt_service.validate_token()` |
| completion_service 奖励发放中断 | `engine.distribute()` 已存在，返回 count 足够 |
| 翻译 /i18n 在 routes.py 内不生效 | 改用 `flask_babel.gettext` 或统一 before_request 注入 |
| 主库 `coupons` 表 DROP 后 rollback 不便 | 先备份，确认所有引用已清除后再删 |

---

## 五、当前插件状态验证

部署前需确认 `plugins/coupons/` 下文件完备：

```
plugins/coupons/
├── __init__.py          ✅
├── plugin.json          ❌ 需新建
├── models.py            ✅
├── engine.py            ✅
├── routes.py            ✅（需修）
├── ai_recommender.py    ✅
├── scene.py             ✅
└── coupons.db           ✅（空，待初始数据）
```
