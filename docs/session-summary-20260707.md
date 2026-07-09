# 会话任务总结

生成本文档时间：2026-07-07

---

## 任务列表

### 1. 数据库文件清理分析
**状态**：分析完成，待执行清理

本地数据库文件冗余情况：
- `data/easykai.db`（45MB）— 完整数据库，177 张表 ✅ 保留
- `data/verorun.db`（1.4MB）— 当前开发库，129 张表，缺 9 张表，建议作为官方开发库更新
- `data/x7k2m9a4.db`（48KB）— 几乎空库（仅 4 表），**可清理**
- `verorun.db`（根目录）— 与 data/verorun.db 重复，**可清理**
- `site.db`（根目录）— 0 用户副本，**可清理**
- `auth-center/database.db`（0KB）— 空壳，**可清理**

### 2. 插件数据库独立拆分
**状态**：已完成

#### coupons 插件
- 新建 `plugins/coupons/models.py` — `coupons`、`coupon_redemptions` 表
- 改造 `engine.py` — 构造器增加 `get_main_db` 参数，读主库的查询全部切换
- 改造 `routes.py` — 增加 `get_main_db` 注入，`api_logs`/`users` 查询切到主库
- 改造 `__init__.py` — 改用本地 `get_db` + `get_main_db`

#### reviews 插件
- 新建 `plugins/reviews/models.py` — `product_reviews` 表
- 改造 `__init__.py` — 跨库 JOIN 拆为 Python 拼接，改用本地 `get_db` + `get_main_db`

#### wishlist 插件
- 新建 `plugins/wishlist/models.py` — `wishlist` 表
- 改造 `__init__.py` — 同上模式

数据库测试：3 个插件独立库均已通过创建验证。

### 3. 主库 Schema 同步脚本
**状态**：已完成

`scripts/sync_schema.py`：
- 扫描 6 个代码文件，提取 126 张主库表
- 排除 11 张插件/外部表
- 幂等：`CREATE TABLE IF NOT EXISTS`
- 可重复运行：`python scripts/sync_schema.py`

### 4. 插件管理系统方案设计
**状态**：调研完成，方案已出，但评审认为不够完整

#### 已调研的 5 个主流系统
Jenkins（Extension Points + ClassLoader 隔离） → Wordpress（Hook: Actions + Filters） → VS Code（activationEvents 懒加载 + 独立进程） → Drupal（Plugin System + Hook System 双层 + DI） → Flask（Blueprint + Extension 模式）

#### 已提出的方案框架
在 `plugin_manager/` 下新建管理模块，主库增加 `plugin_registry` 表，每个插件增加 `plugin.json` 元信息声明，提供 list/install/uninstall/enable/disable/config 管理 API。

#### 设计缺失（待下次确认）
哪些元素需要补充：
- 事件/钩子系统（WordPress/Drupal 式）？
- 权限模型（插件访问边界）？
- 配置 UI（插件设置页统一入口）？
- 依赖管理（插件间依赖声明）？
- 日志/监控（独立日志通道）？
- 版本/更新（Schema 迁移、版本兼容）？
- 其他？

#### 4 阶段实施计划（待定）
| 阶段 | 内容 | 优先级 |
|------|------|--------|
| 一 | PluginManager 模块 + plugin_registry 表 + 插件扫描 + BasePlugin 扩展 | P0 |
| 二 | 管理 API + 后台页面 | P0 |
| 三 | 5 个插件标准化（plugin.json）+ install.py | P1 |
| 四 | 高级功能（配置/依赖/更新） | P2 |

---

## 已知问题（待修复）

| 问题 | 位置 | 说明 |
|------|------|------|
| product_skus 重名表 | `plugins/ali_api/routes/admin.py` L772 | 在插件库里又建了 product_skus 表，主库已有同名表 |
| self.t() 作用域问题 | 各插件 `__init__.py` routes 内 | routes 定义在 register_routes() 方法内，self.t() 可能报错 |
| 数据库死代码 | `auth-center/models/database.py` L2240-2450 | _get_default_interests() return 后的代码永远不会执行 |
| admin_loop/guardian_loop | 根目录 | 废弃的循环脚本，未被引用 |

---

## 当前未提交更改概览

在执行任何新任务前，记得先提交当前更改。

```
新建:
  plugins/coupons/models.py
  plugins/reviews/models.py
  plugins/wishlist/models.py
  scripts/sync_schema.py
  docs/plugin_db_split_plan.md
  docs/plugin-management-design.md
  docs/session-summary-20260707.md

修改:
  plugins/coupons/__init__.py
  plugins/coupons/engine.py
  plugins/coupons/routes.py
  plugins/reviews/__init__.py
  plugins/wishlist/__init__.py
```

## 相关文档索引

- `docs/plugin_db_split_plan.md` — 插件数据库拆分方案
- `docs/plugin-management-design.md` — 插件管理系统设计方案
- `scripts/sync_schema.py` — 主库 Schema 同步脚本
