# SQL 审计不兼容清单

> 生成日期：2026-07-15 | Phase 0 / 步骤 0C

---

## 审计摘要

| 类别 | 出现次数 | 涉及文件数 | 严重度 | 迁移操作 |
|------|----------|-----------|--------|----------|
| `datetime('now'` | 443 | 77 | **高** | 替换为 `NOW()` |
| `AUTOINCREMENT` | 173 | 36 | **高** | 替换为 `GENERATED ALWAYS AS IDENTITY` |
| `PRAGMA` | 100+ | 30 | **高** | 全部删除 |
| `strftime()` (SQL) | 20+ | 5 | **高** | 替换为 `TO_CHAR()` |
| `sqlite3.connect` | 53 | 42 | **高** | 替换为 `psycopg2.pool.getconn()` |
| `row_factory` | 45 | 39 | 高 | 删除/替换为 DictCursor |
| `last_insert_rowid` | 28 | 16 | 高 | 替换为 `RETURNING id` |
| `IFNULL()` | 22 | 1 | 中 | 替换为 `COALESCE()` |
| `check_same_thread` | 18 | 16 | 中 | 删除 |
| `REPLACE INTO` | 9 | 6 | 中 | 替换为 `INSERT ... ON CONFLICT` |
| `ATTACH DATABASE` | 1 | 1 | 中 | 替换为 `search_path` |
| `json_extract` | 0 | 0 | 无 | 无 |

---

## 一、`datetime('now'` — 443 处 / 77 个文件

### 核心文件（出现最多的 15 个文件）

| 文件 | 次数 | 说明 |
|------|------|------|
| `auth-center/models/database.py` | 102 | 建表 DEFAULT + UPDATE 语句 |
| `auth-center/routes/admin.py` | 37 | 仪表盘统计查询 |
| `auth-center/routes/subscription/__init__.py` | 26 | 订阅系统 |
| `agent_matrix/models.py` | 16 | Agent 矩阵模型 |
| `orchestrator/models.py` | 16 | 调度器模型 |
| `plugins/ali_api/models.py` | 14 | 阿里 API 插件 |
| `auth-center/models/cms.py` | 13 | CMS 模型 |
| `plugin_manager/subscription.py` | 12 | 插件订阅 |
| `site_builder/models.py` | 11 | 站点生成器 |
| `plugin_manager/license_server/__init__.py` | 10 | 许可证服务 |
| `plugins/health_check/models.py` | 10 | 健康检查 |
| `auth-center/routes/shop_admin.py` | 9 | 商城管理 |
| `plugins/chatbot/models.py` | 8 | 聊天机器人 |
| `auth-center/routes/user.py` | 7 | 用户路由 |
| `plugins/payment/models.py` | 6 | 支付插件 |

### 典型替换

```sql
-- 建表 DEFAULT
-- 旧: created_at TEXT DEFAULT (datetime('now'))
-- 新: created_at TIMESTAMP DEFAULT NOW()

-- 建表 DEFAULT（带 localtime）
-- 旧: created_at TEXT DEFAULT (datetime('now','localtime'))
-- 新: created_at TIMESTAMP DEFAULT NOW()

-- UPDATE 语句
-- 旧: UPDATE users SET updated_at=datetime('now') WHERE id=?
-- 新: UPDATE users SET updated_at=NOW() WHERE id=%s

-- 日期运算
-- 旧: WHERE paid_at>=datetime('now','-30 days')
-- 新: WHERE paid_at>=NOW() - INTERVAL '30 days'

-- 带参数
-- 旧: datetime('now', ?)
-- 新: NOW() + (%s * INTERVAL '1 second')
```

---

## 二、`strftime()` (SQL) — 需审计的 5 个文件

> 注意：大量 `strftime()` 调用是 Python 的 `datetime.strftime()`，不需要修改。以下列出实际的 SQL `strftime()` 调用：

| 文件 | 行号范围 | 数量 | 典型 SQL |
|------|----------|------|----------|
| `auth-center/routes/admin.py` | 278-492 | 15+ | `strftime('%Y-%m', paid_at)` 月度统计 |
| `agent_matrix/models.py` | 114 | 1 | `strftime('%Y%m%d', 'now')` 任务编号 |
| `plugins/analytics/tracker.py` | 250 | 1 | `strftime` 日期比较 |
| `tmp_test_logs.py` | 12 | 1 | `strftime('%s','now','-1 hour')` 测试文件 |

### 替换规则

```sql
-- 旧: strftime('%Y-%m', paid_at) = strftime('%Y-%m','now')
-- 新: TO_CHAR(paid_at, 'YYYY-MM') = TO_CHAR(NOW(), 'YYYY-MM')

-- 旧: strftime('%Y-%m', paid_at) = strftime('%Y-%m','now','-1 month')
-- 新: TO_CHAR(paid_at, 'YYYY-MM') = TO_CHAR(NOW() - INTERVAL '1 month', 'YYYY-MM')

-- 旧: strftime('%Y%m%d', 'now')
-- 新: TO_CHAR(NOW(), 'YYYYMMDD')

-- 旧: strftime('%s','now','-1 hour')
-- 新: EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour')
```

---

## 三、`AUTOINCREMENT` — 173 处 / 36 个文件

### 核心文件

| 文件 | 次数 |
|------|------|
| `auth-center/models/database.py` | 76 |
| `agent_matrix/models.py` | 6 |
| `orchestrator/models.py` | 10 |
| `plugins/analytics/models.py` | 10 |
| `plugins/health_check/models.py` | 8 |
| `plugins/ali_api/models.py` | 7 |
| `plugins/payment/models.py` | 4 |
| `plugins/chatbot/models.py` | 2 |

### 替换规则

```sql
-- 旧: id INTEGER PRIMARY KEY AUTOINCREMENT
-- 新: id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY
```

---

## 四、`PRAGMA` — 100+ 行 / 30 个文件

### 分类 A：连接初始化（需全部删除）

| 文件 | 典型代码 |
|------|----------|
| `auth-center/models/database.py` (L28-30, L48-49) | `PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000` |
| `agent_matrix/models.py` (L93-95) | 同上 |
| `orchestrator/models.py` (L35-37) | 同上 |
| `plugin_manager/models.py` (L40-41) | 同上 |
| `plugins/analytics/models.py` (L299-302) | 含 `PRAGMA synchronous=NORMAL; PRAGMA cache_size=-8000` |
| 其他 25 个插件 models.py | `PRAGMA journal_mode=WAL` |

### 分类 B：`PRAGMA table_info()` 查询列信息（需替换）

| 文件 | 出现次数 | 替换方案 |
|------|----------|----------|
| `auth-center/models/database.py` | 15+ 处 | `information_schema.columns` |
| `agent_matrix/models.py` | 4 处 | 同上 |
| `plugins/ali_api/models.py` | 2 处 | 同上 |
| `auth-center/models/cms.py` | 1 处 | 同上 |

```sql
-- 旧: PRAGMA table_info(users)
-- 新: SELECT column_name FROM information_schema.columns WHERE table_name='users' AND table_schema='public'
```

---

## 五、`sqlite3.connect` — 53 处 / 42 个文件

| 文件 | 说明 |
|------|------|
| `auth-center/models/database.py` (3 处) | 主连接 + shop.db 连接 + shop 建表连接 |
| `plugins/payment/models.py` (3 处) | 支付数据库连接 |
| `plugins/subscription/models.py` (3 处) | 订阅数据库连接 |
| `plugins/oauth_config/models.py` (2 处) | OAuth 配置 |
| `plugins/order_notify/models.py` (2 处) | 订单通知 |
| `auth-center/services/brand_service.py` (2 处) | 品牌服务 |
| `scripts/sync_schema.py` (3 处) | 同步脚本 |
| `_tmp_check_both.py` (1 处) | 临时测试文件（可忽略） |
| 其余 33 个文件 | 各 1 处 |

### 替换规则

```python
# 旧:
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row

# 新:
from auth_center.models.database import _pool
conn = _pool.getconn()
```

---

## 六、`row_factory` — 45 处 / 39 个文件

全部为 `conn.row_factory = sqlite3.Row`，迁移后删除或替换为 `RealDictCursor`。

---

## 七、`check_same_thread` — 18 处 / 16 个文件

全部为 `sqlite3.connect(..., check_same_thread=False)`，迁移后删除（连接池管理）。

---

## 八、`last_insert_rowid` — 28 处 / 16 个文件

| 文件 | 次数 | 迁移方案 |
|------|------|----------|
| `orchestrator/models.py` | 3 | `RETURNING id` |
| `agent_matrix/models.py` | 1 | `RETURNING id` |
| `auth-center/routes/user.py` | 2 | `RETURNING id` |
| `auth-center/routes/shop_admin.py` | 4 | `RETURNING id` |
| `auth-center/routes/comments.py` | 1 | `RETURNING id` |
| `auth-center/routes/agents.py` | 2 | `RETURNING id` |
| `auth-center/routes/admin.py` | 1 | `RETURNING id` |
| `platform/routes/api_v1.py` | 1 | `RETURNING id` |
| `site_builder/models.py` | 1 | `RETURNING id` |
| `plugins/health_check/routes.py` | 2 | `RETURNING id` |
| `plugins/content_factory/` | 4 | `RETURNING id` |
| `plugins/analytics/` | 2 | `RETURNING id` |
| `plugins/coupons/engine.py` | 1 | `RETURNING id` |
| `plugins/sms/routes.py` | 1 | `RETURNING id` |

### 替换规则

```python
# 旧:
conn.execute("INSERT INTO users (...) VALUES (...)")
new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

# 新 (方案 A: RETURNING):
row = conn.execute("INSERT INTO users (...) VALUES (...) RETURNING id").fetchone()
new_id = row[0]

# 新 (方案 B: cursor.lastrowid):
cur = conn.cursor()
cur.execute("INSERT INTO users (...) VALUES (...)")
new_id = cur.lastrowid
```

---

## 九、`REPLACE INTO` / `INSERT OR REPLACE` — 9 处 / 6 个文件

| 文件 | 行号 | 原 SQL |
|------|------|--------|
| `i18n/__init__.py` | 291 | `INSERT OR REPLACE INTO i18n_strings` |
| `auth-center/services/license_service.py` | 56 | `INSERT OR REPLACE INTO system_config` |
| `auth-center/services/jwt_service.py` | 87 | `INSERT OR REPLACE INTO system_config` |
| `auth-center/services/wechat_push_service.py` | 59 | `INSERT OR REPLACE INTO system_config` |
| `auth-center/routes/subscription/__init__.py` | 547 | `INSERT OR REPLACE INTO subscriptions` |
| `orchestrator/scheduler.py` | 458 | `INSERT OR REPLACE INTO scheduler_state` |
| `plugins/health_check/routes.py` | 211 | `INSERT OR REPLACE INTO health_trend` |
| `plugins/health_check/routes.py` | 1122 | `INSERT OR REPLACE INTO system_config` |
| `plugins/health_check/checkers.py` | 972 | `INSERT OR REPLACE INTO system_config` |

### 替换规则

```sql
-- 旧: INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)
-- 新: INSERT INTO system_config (key, value) VALUES (%s, %s)
--     ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
```

---

## 十、`IFNULL()` — 22 处 / 1 个文件

全部集中在 `auth-center/routes/admin.py`（552-3769 行），用于用户显示名回退。

```sql
-- 旧: IFNULL(u.display_name, u.username)
-- 新: COALESCE(u.display_name, u.username)
```

---

## 十一、`ATTACH DATABASE` — 1 处

| 文件 | 行号 |
|------|------|
| `auth-center/models/database.py` | 34 |

```python
# 旧:
conn.execute(f"ATTACH DATABASE '{SHOP_DB_PATH}' AS shop")

# 新:
conn.execute("SET search_path TO public, shop, analytics, health, payment, order_notify")
```

---

## 十二、`json_extract()` — 0 处

项目未使用 SQLite `json_extract()`，无需处理。

---

## 改造优先级

| 优先级 | 类别 | 理由 |
|--------|------|------|
| P0 | `database.py` 全面重写 | 所有依赖汇聚点 |
| P0 | `AUTOINCREMENT` → `IDENTITY` | 所有建表语句必须改 |
| P0 | `PRAGMA` 删除 | 启动即报错 |
| P1 | `datetime('now'` → `NOW()` | 数量最大（443 处），分布最广 |
| P1 | `sqlite3.connect` → 连接池 | 42 个文件各自直连 |
| P1 | `last_insert_rowid` → `RETURNING` | 28 处需逐个改 |
| P2 | `REPLACE INTO` → `INSERT ON CONFLICT` | 仅 9 处，但逻辑敏感 |
| P2 | `IFNULL` → `COALESCE` | 仅 1 个文件 |
| P2 | `strftime()` (SQL) → `TO_CHAR()` | 少量 SQL 使用 |
| P2 | `ATTACH DATABASE` → `search_path` | 仅 1 处 |
