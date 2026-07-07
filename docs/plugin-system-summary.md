# 插件系统 — 会话总结

生成日期：2026-07-07

---

## 一、现状概览

### 5 个现有插件

| 插件 | 独立库 | 表 | 数据库状态 |
|------|--------|-----|-----------|
| **ali_api** | `plugins/ali_api/ali_api.db` | ali_api_items, ali_api_reviews, ali_api_logs, ali_api_user_stats, ali_api_tokens, ali_oauth_states, ali_api_config | ✅ 早已独立 |
| **coupons** | `plugins/coupons/coupons.db` | coupons, coupon_redemptions | ✅ 本次拆分完成 |
| **reviews** | `plugins/reviews/reviews.db` | product_reviews | ✅ 本次拆分完成 |
| **wishlist** | `plugins/wishlist/wishlist.db` | wishlist | ✅ 本次拆分完成 |
| **order_notify** | 无表 | 纯事件监听，只读主库 | ✅ 无需数据库 |

### 数据现状
- 以上所有插件表在主库 **还有残留定义**
- 本地和服务器上插件数据均为 **0 行**

---

## 二、已完成的工作

### 2.1 插件表拆分（本次会话完成）
- **coupons**：新建 `models.py`，改造 `engine.py`（构造器增加 `get_main_db`）、`routes.py`（增加 `get_main_db` 注入）、`__init__.py`
- **reviews**：新建 `models.py`，改造 `__init__.py`（跨库 JOIN 拆为 Python 拼接）
- **wishlist**：新建 `models.py`，改造 `__init__.py`（同上模式）

### 2.2 主库 Schema 同步脚本
- 新建 `scripts/sync_schema.py`
- 扫描 6 个代码文件 → 提取 **126 张主库表**（排除 11 个插件/外部表）
- 幂等：`CREATE TABLE IF NOT EXISTS`
- 可重复运行：`python scripts/sync_schema.py`

### 2.3 各插件数据库测试验证
- 3 个插件数据库均已通过创建测试
- 所有 .py 文件通过 `py_compile` 语法校验

### 2.4 数据库文件清理分析
- `data/easykai.db`（45MB）— 完整数据，177 张表
- `data/verorun.db`（1.4MB）— 当前开发库，129 表，缺 9 张最新表
- `data/x7k2m9a4.db`（48KB）— 空库，仅 4 表
- `verorun.db`（根目录）— 与 data/ 下重复
- `site.db`（根目录）— 0 用户的副本
- `auth-center/database.db`（0KB）— 空壳

---

## 三、下一步：插件管理系统设计

### 3.1 调研过的系统
| 系统 | 核心机制 |
|------|----------|
| **Jenkins** | Extension Points + ClassLoader 隔离 + Update Center |
| **WordPress** | Hook 系统（Actions + Filters）+ 主文件头声明元信息 |
| **VS Code** | activationEvents 懒加载 + 独立 Extension Host 进程 |
| **Drupal** | Plugin System + Hook System 双层 + Annotation 发现 + DI |
| **Flask** | Blueprint（路由分组）+ Extension 模式（`init_app`） |

### 3.2 已提出的方案框架

```
plugin_manager/               # 新增模块
├── __init__.py               # PluginManager 类（扫描/注册/生命周期）
├── models.py                 # plugin_registry 表
├── routes.py                 # 管理 API（list/install/uninstall/enable/disable/config）
└── templates/                # 后台管理 UI

plugins/<name>/               # 每个插件增加
└── plugin.json               # 元信息声明
```

### 3.3 设计缺失（待补充）
在评审方案时认为方案不够完整，**需要补充的元素**（但具体缺哪些未定论，下次会话需确认）：

- 🔲 **事件/钩子系统** — WordPress/Drupal 式的事件订阅机制？
- 🔲 **权限模型** — 插件能访问哪些资源？
- 🔲 **配置 UI** — 插件设置页面统一入口？
- 🔲 **依赖管理** — 插件间依赖声明？
- 🔲 **日志/监控** — 插件独立日志通道？
- 🔲 **版本/更新** — Schema 迁移 + 版本兼容？
- 🔲 **其他** — 你觉得还有的？

### 3.4 4 阶段实施计划

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| 一 | PluginManager 模块 + plugin_registry 表 + 插件扫描 + BasePlugin 扩展 | P0 |
| 二 | 管理 API + 后台管理页面 | P0 |
| 三 | 5 个插件标准化（加 plugin.json）+ install.py | P1 |
| 四 | 高级功能（配置/依赖/更新） | P2 |

---

## 四、已知问题

### 4.1 待修复
- `plugins/ali_api/routes/admin.py` L772：在插件库中创建了 `product_skus` 表（与主库重名）
- 所有插件 `__init__.py` 中的 `self.t()` 翻译方法 — 当前 routes 内联定义在 `register_routes()` 中，`self` 作用域有问题（部分路由用 `self.t()` 可能报错）

### 4.2 代码中的死代码
- `auth-center/models/database.py#L2240-L2450`：`_get_default_interests()` 函数 return 后的迁移代码
- 多处 `admin_loop.py`、`guardian_loop.py` 看起来是废弃的循环脚本

### 4.3 部署后需处理的
- 主库中残留的插件表（coupons、coupon_redemptions、product_reviews、wishlist）可以选择性删除
- 服务器部署时按：提交代码 → rsync 同步 → 重启服务的顺序

---

## 五、涉及的变更文件清单

### 本次会话变更（已修改/新建）
```
新建:
  plugins/coupons/models.py
  plugins/reviews/models.py
  plugins/wishlist/models.py
  scripts/sync_schema.py
  docs/plugin_db_split_plan.md
  docs/plugin-management-design.md

修改:
  plugins/coupons/__init__.py
  plugins/coupons/engine.py
  plugins/coupons/routes.py
  plugins/reviews/__init__.py
  plugins/wishlist/__init__.py
```

### 下次任务可能涉及
```
新建:
  plugin_manager/__init__.py
  plugin_manager/models.py
  plugin_manager/routes.py
  各插件/plugin.json

修改:
  plugins/base.py（扩展 BasePlugin）
  sync_schema.py（如需要加入 plugin_registry 表）
```
