# 插件独立数据库拆分方案

## 目标
将 coupons、reviews、wishlist 三个插件的表从主库拆出，各自拥有独立 SQLite 数据库。ali_api 已独立，order_notify 无表。

## 现状问题

| 插件 | 表 | 当前数据库 | 依赖的主库表（只读） |
|------|-----|-----------|-------------------|
| coupons | `coupons`, `coupon_redemptions` | 主库 `easykai.db` | `users`, `order_items` |
| reviews | `product_reviews` | 主库 `easykai.db` | `users`, `products`, `order_items` |
| wishlist | `wishlist` | 主库 `easykai.db` | `products` |

## 变更文件清单

### coupons 插件（4 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `plugins/coupons/models.py` | **新建** | 独立 DB 连接：`get_db()` → `coupons.db`，`get_main_db()` → 主库 |
| `plugins/coupons/__init__.py` | **修改** | `on_install()` 改用本地 `get_db()` 建表 |
| `plugins/coupons/engine.py` | **修改** | 改用本地 `get_db()`，读主库时显式用 `get_main_db()` |
| `plugins/coupons/routes.py` | **修改** | 改用本地 `get_db()` |

### reviews 插件（1 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `plugins/reviews/models.py` | **新建** | 独立 DB 连接 |
| `plugins/reviews/__init__.py` | **修改** | `on_install()` 改用本地 `get_db()`，查询主库时用 `get_main_db()` |

### wishlist 插件（1 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `plugins/wishlist/models.py` | **新建** | 独立 DB 连接 |
| `plugins/wishlist/__init__.py` | **修改** | `on_install()` 改用本地 `get_db()`，查询 `products` 时用 `get_main_db()` |

### 主库同步脚本（1 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/sync_schema.py` | **新建** | 可重复运行，按代码定义补全主库缺少的表 |

## 具体改动点

### 1. 各插件 models.py 模板

每个插件的 `models.py` 包含：
- `PLUGIN_DB_PATH` — 指向 `plugins/{name}/{name}.db`
- `get_db()` — 连接插件自己的数据库，`init_db()` 中 CREATE TABLE
- `get_main_db()` — 从 `auth-center/models/database.py` 导入，只读查询主库

```python
# plugins/coupons/models.py 示例结构
import os, sqlite3
from contextlib import contextmanager

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, 'coupons.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS coupons (...略...)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS coupon_redemptions (...略...)''')

@contextmanager
def get_main_db():
    from models import get_db as main_get_db
    with main_get_db() as conn:
        yield conn
```

### 2. plugins/coupons/__init__.py 改动

- `on_install()`: 调用 `from .models import get_db, init_db` → `init_db()`
- `on_enable()`: `from .models import get_db` → 传给 `CouponEngine(get_db)`

### 3. plugins/coupons/engine.py 改动

所有当前读主库的查询（`users`, `order_items`），从 `self._get_db()` 改为 `get_main_db()` 上下文。

涉及的方法：
- `get_available_coupons()` — 检查 `order_items`（新人券）
- `validate()` — 检查 `order_items`（新人券）
- `stats()` — 查询 `order_items`
- `distribute()` — 查询 `users`

### 4. plugins/reviews/__init__.py 改动

- `on_install()`: `from .models import get_db, init_db` → `init_db()`
- JOIN 查询 `users`、`products`、`order_items` 时：改用 `get_main_db()`
- `product_reviews` 表自己的 CRUD：用 `get_db()`

### 5. plugins/wishlist/__init__.py 改动

- `on_install()`: `from .models import get_db, init_db` → `init_db()`
- JOIN 查询 `products` 时：改用 `get_main_db()`
- `wishlist` 表 CRUD：用 `get_db()`

### 6. scripts/sync_schema.py 设计

```python
# 可重复运行的 schema 同步脚本
# python scripts/sync_schema.py [--db data/verorun.db]
# 功能：
#   1. 扫描代码中所有 CREATE TABLE 语句
#   2. 排除 plugins/ 目录下的表
#   3. 排除 cognition-service 的 PostgreSQL 表
#   4. 对主库执行 CREATE TABLE IF NOT EXISTS
#   5. 输出报告：新增了哪些表
```

## 执行顺序

1. **同步主库** — 先跑 `sync_schema.py` 确保主库完整
2. **coupons 插件** — 创建独立 models.py + 改造 engine/routes
3. **reviews 插件** — 创建独立 models.py + 改造 __init__.py
4. **wishlist 插件** — 创建独立 models.py + 改造 __init__.py
5. **验证** — 确保各插件启动时自动建表成功

## 风险点

| 风险 | 缓解措施 |
|------|---------|
| coupons/routes.py 中 `admin_actions` 和 `api_logs` 表在主库 | routes 中的管理日志操作使用 `get_main_db()` |
| reviews 插件 JOIN `users` + `products` 跨库 | 使用 `get_main_db()` 读主库，`get_db()` 写本库 |
| 已有数据迁移问题 | 当前 3 个表在本地主库均为 0 行（空表），无需迁移 |
| 插件加载顺序 | init_db() 在 on_install 中执行，生命周期不变 |
