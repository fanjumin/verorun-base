# SQLite → PostgreSQL 迁移方案

> 版本：v0.1 | 日期：2026-07-15 | 状态：方案阶段

---

## 一、目标架构

```
迁移前                              迁移后
─────────────────────────          ─────────────────────────
x7k2m9a4.db  ──ATTACH── shop.db    easykai 数据库
                                        ├── public schema     (原 x7k2m9a4.db 表)
                                        ├── shop schema       (原 shop.db 表)
                                        ├── analytics schema  (原 analytics.db)
                                        ├── health schema     (原 health.db)
                                        ├── payment schema    (原 payment.db)
                                        └── order_notify schema
独立: analytics.db, health.db,
      payment.db, order_notify.db,
      captcha/verorun.db

连接方式: sqlite3.connect()        连接池: psycopg2.pool.ThreadedConnectionPool
       check_same_thread=False            minconn=5, maxconn=20
```

---

## 二、核心文件重写：database.py

### 2.1 新连接管理器

```python
# auth-center/models/database.py (新版)
import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

# PostgreSQL 连接配置
PG_CONFIG = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': int(os.environ.get('PG_PORT', 5432)),
    'dbname': os.environ.get('PG_DB', 'easykai'),
    'user': os.environ.get('PG_USER', 'easykai'),
    'password': os.environ.get('PG_PASSWORD', ''),
    'application_name': 'verorun',
}

# 连接池（全局单例）
_pool = ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    **PG_CONFIG
)

@contextmanager
def get_db():
    """获取数据库连接，自动归还连接池"""
    conn = _pool.getconn()
    conn.autocommit = False
    # 设置 search_path 以支持多 schema 查询
    with conn.cursor() as cur:
        cur.execute("SET search_path TO public, shop, analytics, health, payment, order_notify")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
```

### 2.2 修改对比

| 项目 | SQLite 写法 | PostgreSQL 写法 |
|------|-----------|---------------|
| 连接获取 | `sqlite3.connect(DB_PATH, check_same_thread=False)` | `_pool.getconn()` |
| 行工厂 | `conn.row_factory = sqlite3.Row` | psycopg2 默认返回 tuple，可用 `RealDictCursor` |
| PRAGMA | `PRAGMA journal_mode=WAL` | 删除（PG 自带 WAL） |
| PRAGMA | `PRAGMA foreign_keys=ON` | 删除（PG 默认开启） |
| PRAGMA | `PRAGMA busy_timeout=5000` | 删除（连接池管理） |
| ATTACH | `ATTACH DATABASE 'shop.db' AS shop` | `SET search_path TO public, shop` |
| 连接关闭 | `conn.close()` | `_pool.putconn(conn)` |

---

## 三、SQL 语法转换规则（全项目应用）

| # | SQLite 写法 | PostgreSQL 写法 | 说明 |
|---|-----------|---------------|------|
| 1 | `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` | 自增主键 |
| 2 | `datetime('now','localtime')` | `NOW()` | 时间默认值 |
| 3 | `datetime('now','localtime','+7 days')` | `NOW() + INTERVAL '7 days'` | 日期运算 |
| 4 | `strftime('%Y-%m', created_at)` | `TO_CHAR(created_at, 'YYYY-MM')` | 日期格式化 |
| 5 | `IFNULL(col, default)` | `COALESCE(col, default)` | 空值处理 |
| 6 | `REPLACE INTO table (...) VALUES (...)` | `INSERT INTO table (...) VALUES (...) ON CONFLICT (pk) DO UPDATE SET ...` | UPSERT |
| 7 | `"key" = ?` (位置占位符) | `"key" = %s` (psycopg2) | 占位符 |
| 8 | `SELECT last_insert_rowid()` | `SELECT LASTVAL()` 或 `RETURNING id` | 获取插入 ID |
| 9 | `PRAGMA journal_mode=WAL` | 删除 | PG 自带 WAL |
| 10 | `PRAGMA foreign_keys=ON` | 删除 | PG 默认开启 |
| 11 | `PRAGMA busy_timeout=5000` | 删除 | 连接池管理 |
| 12 | `ATTACH DATABASE 'shop.db' AS shop` | `SET search_path TO public, shop` | Schema 隔离 |
| 13 | `TEXT DEFAULT ''` | `TEXT DEFAULT ''` | 保持不变 |
| 14 | `INTEGER DEFAULT 0` (布尔) | `BOOLEAN DEFAULT FALSE` | 布尔值 |
| 15 | `json_extract(col, '$.key')` | `col->>'key'` 或 `col::jsonb->>'key'` | JSON 操作 |
| 16 | `RANDOM()` | `RANDOM()` | 相同，无需修改 |
| 17 | `LIMIT X OFFSET Y` | `LIMIT X OFFSET Y` | 相同 |
| 18 | `||` 字符串拼接 | `||` 或 `CONCAT()` | 相同 |

---

## 四、数据迁移工具

### 4.1 迁移脚本

```python
#!/usr/bin/env python3
"""scripts/sqlite_to_pg_migrate.py —— SQLite → PostgreSQL 数据迁移工具"""
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os

SOURCE_SQLITE = os.environ.get('SOURCE_DB', 'data/x7k2m9a4.db')
TARGET_PG_DSN = os.environ.get('PG_DSN', 'host=localhost dbname=easykai user=easykai')

# 表映射：SQLite 表名 → (PG schema, PG 表名)
TABLE_MAP = {
    # public schema（主库）
    'users': ('public', 'users'),
    'sessions': ('public', 'sessions'),
    'sites': ('public', 'sites'),
    'pages': ('public', 'pages'),
    'posts': ('public', 'posts'),
    'comments': ('public', 'comments'),
    'subscriptions': ('public', 'subscriptions'),
    'plans': ('public', 'plans'),
    'coupons': ('public', 'coupons'),
    'notifications': ('public', 'notifications'),
    'plugins': ('public', 'plugins'),
    'api_keys': ('public', 'api_keys'),
    'tickets': ('public', 'tickets'),
    'uploads': ('public', 'uploads'),
    'admin_logs': ('public', 'admin_logs'),
    'feature_orders': ('public', 'feature_orders'),
    'reward_rules': ('public', 'reward_rules'),
    'i18n_translations': ('public', 'i18n_translations'),
    'model_providers': ('public', 'model_providers'),
    'agent_configs': ('public', 'agent_configs'),
    'site_domains': ('public', 'site_domains'),
    'verification_codes': ('public', 'verification_codes'),
    'oauth_configs': ('public', 'oauth_configs'),
    # shop schema
    'products': ('shop', 'products'),
    'categories': ('shop', 'categories'),
    'carts': ('shop', 'carts'),
    'user_purchases': ('shop', 'user_purchases'),
    'order_items': ('shop', 'order_items'),
    'product_specs': ('shop', 'product_specs'),
    'product_spec_values': ('shop', 'product_spec_values'),
    'product_skus': ('shop', 'product_skus'),
    'pricing_rules': ('shop', 'pricing_rules'),
    'express_companies': ('shop', 'express_companies'),
    'order_shipping': ('shop', 'order_shipping'),
    'orders': ('shop', 'orders'),
    'sub_orders': ('shop', 'sub_orders'),
    'sub_events': ('shop', 'sub_events'),
    'sub_stats': ('shop', 'sub_stats'),
}


def get_sqlite_tables(conn: sqlite3.Connection) -> list[str]:
    """获取 SQLite 数据库中所有用户表"""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_%'"
    )
    return [row[0] for row in cur.fetchall()]


def get_table_columns(conn: sqlite3.Connection, table: str) -> list[dict]:
    """获取表结构"""
    cur = conn.execute(f"PRAGMA table_info('{table}')")
    return [
        {'cid': r[0], 'name': r[1], 'type': r[2], 'notnull': r[3], 'pk': r[5]}
        for r in cur.fetchall()
    ]


def sqlite_type_to_pg(sqlite_type: str) -> str:
    """SQLite 类型映射到 PostgreSQL"""
    type_upper = (sqlite_type or '').upper()
    mapping = {
        'INTEGER': 'BIGINT',
        'INT': 'BIGINT',
        'TEXT': 'TEXT',
        'REAL': 'DOUBLE PRECISION',
        'FLOAT': 'DOUBLE PRECISION',
        'DOUBLE': 'DOUBLE PRECISION',
        'BLOB': 'BYTEA',
        'BOOLEAN': 'BOOLEAN',
        'DATETIME': 'TIMESTAMP',
        'JSON': 'JSONB',
    }
    return mapping.get(type_upper, 'TEXT')


def generate_ddl(source_conn: sqlite3.Connection):
    """生成 PostgreSQL DDL 语句"""
    tables = get_sqlite_tables(source_conn)
    ddl_statements = []

    # 从 shop.db 读取 shop 表
    shop_conn = sqlite3.connect('data/shop.db')
    shop_tables = get_sqlite_tables(shop_conn)

    for table in tables:
        columns = get_table_columns(source_conn, table)
        schema, pg_table = TABLE_MAP.get(table, ('public', table))

        col_defs = []
        for col in columns:
            pg_type = sqlite_type_to_pg(col['type'])
            nullable = '' if col['notnull'] else ' NULL'
            if col['pk'] and col['type'].upper() in ('INTEGER', 'INT'):
                col_defs.append(f"    {col['name']} BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY")
            elif col['pk']:
                col_defs.append(f"    {col['name']} {pg_type} PRIMARY KEY{nullable}")
            else:
                col_defs.append(f"    {col['name']} {pg_type}{nullable}")

        ddl = (
            f"CREATE TABLE IF NOT EXISTS {schema}.{pg_table} (\n"
            + ",\n".join(col_defs)
            + "\n);"
        )
        ddl_statements.append(ddl)

    # 处理 shop 表（独立 shop.db）
    for table in shop_tables:
        if table in TABLE_MAP:
            continue
        columns = get_table_columns(shop_conn, table)
        col_defs = []
        for col in columns:
            pg_type = sqlite_type_to_pg(col['type'])
            nullable = '' if col['notnull'] else ' NULL'
            if col['pk'] and col['type'].upper() in ('INTEGER', 'INT'):
                col_defs.append(f"    {col['name']} BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY")
            elif col['pk']:
                col_defs.append(f"    {col['name']} {pg_type} PRIMARY KEY{nullable}")
            else:
                col_defs.append(f"    {col['name']} {pg_type}{nullable}")

        ddl = (
            f"CREATE TABLE IF NOT EXISTS shop.{table} (\n"
            + ",\n".join(col_defs)
            + "\n);"
        )
        ddl_statements.append(ddl)

    shop_conn.close()
    return ddl_statements


def migrate_data(source_conn: sqlite3.Connection, target_conn):
    """逐表迁移数据"""
    tables = get_sqlite_tables(source_conn)

    with target_conn.cursor() as cur:
        for table in tables:
            schema, pg_table = TABLE_MAP.get(table, ('public', table))
            print(f"迁移 {table} → {schema}.{pg_table} ...")

            rows = source_conn.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(f"  {table}: 0 行，跳过")
                continue

            columns = get_table_columns(source_conn, table)
            col_names = [c['name'] for c in columns]
            # 跳过自增 ID 列（用 DEFAULT）
            insert_cols = [c for c in col_names if c != 'id'] if 'id' in col_names else col_names

            if not insert_cols:
                continue

            placeholders = ','.join(['%s'] * len(insert_cols))
            col_list = ','.join(f'"{c}"' for c in insert_cols)
            sql = f'INSERT INTO {schema}.{pg_table} ({col_list}) VALUES {placeholders}'

            # 提取对应列数据
            col_indices = [col_names.index(c) for c in insert_cols]
            data = [tuple(row[i] for i in col_indices) for row in rows]

            execute_values(cur, sql, data, page_size=1000)
            print(f"  {table}: {len(rows)} 行完成")

        target_conn.commit()


def main():
    print("=== SQLite → PostgreSQL 迁移工具 ===")
    print(f"源: {SOURCE_SQLITE}")
    print(f"目标: {TARGET_PG_DSN}")

    source_conn = sqlite3.connect(SOURCE_SQLITE)
    source_conn.row_factory = sqlite3.Row

    target_conn = psycopg2.connect(TARGET_PG_DSN)

    # Step 1: 创建 Schema
    print("\n[1/4] 创建 Schema...")
    with target_conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS shop")
        cur.execute("CREATE SCHEMA IF NOT EXISTS analytics")
        cur.execute("CREATE SCHEMA IF NOT EXISTS health")
        cur.execute("CREATE SCHEMA IF NOT EXISTS payment")
        cur.execute("CREATE SCHEMA IF NOT EXISTS order_notify")
        target_conn.commit()

    # Step 2: 创建表
    print("\n[2/4] 创建表结构...")
    ddl_list = generate_ddl(source_conn)
    with target_conn.cursor() as cur:
        for ddl in ddl_list:
            try:
                cur.execute(ddl)
            except Exception as e:
                print(f"  DDL 错误: {e}")
                print(f"  SQL: {ddl[:200]}...")
        target_conn.commit()
    print(f"  共创建 {len(ddl_list)} 个表")

    # Step 3: 迁移数据
    print("\n[3/4] 迁移数据...")
    migrate_data(source_conn, target_conn)

    # Step 4: 重置序列
    print("\n[4/4] 重置序列值...")
    with target_conn.cursor() as cur:
        for table, (schema, pg_table) in TABLE_MAP.items():
            try:
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{schema}.{pg_table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {schema}.{pg_table}), 1))"
                )
            except Exception:
                pass
        target_conn.commit()

    source_conn.close()
    target_conn.close()
    print("\n✅ 迁移完成！")


if __name__ == '__main__':
    main()
```

### 4.2 类型映射表

| SQLite 类型 | PostgreSQL 类型 |
|------------|----------------|
| INTEGER / INT | BIGINT |
| TEXT | TEXT |
| REAL / FLOAT / DOUBLE | DOUBLE PRECISION |
| BLOB | BYTEA |
| BOOLEAN | BOOLEAN |
| DATETIME | TIMESTAMP |
| JSON | JSONB |

---

## 五、文件改造清单

### 5.1 核心层（必须先改）

| 文件 | 行数（约） | 改造内容 | 风险 |
|------|-----------|----------|------|
| `auth-center/models/database.py` | 2300+ | 全部重写连接、建表、迁移、备份函数 | **极高** |
| `auth-center/models/cms.py` | ~800 | 50 处 SQL，替换占位符和特殊函数 | 高 |
| `auth-center/models/user.py` | ~500 | 用户 CRUD 查询改造 | 高 |
| `auth-center/models/site.py` | ~600 | 站点 CRUD 查询改造 | 高 |

### 5.2 服务层

| 文件 | 改造内容 |
|------|----------|
| `auth_server.py` | 入口处初始化连接池 |
| `platform/app.py` | 数据库连接引用 |
| `admin/app.py` | 数据库连接引用 |
| `health_service/app.py` | 数据库连接引用 |

### 5.3 插件层（5 个独立库）

| 插件 | 原数据库文件 | 改造策略 |
|------|------------|----------|
| `plugins/analytics/` | `analytics.db` | Schema: `analytics`，改数据库连接 |
| `plugins/health_check/` | `health.db` | Schema: `health`，改数据库连接 |
| `plugins/payment/` | `payment.db` | Schema: `payment`，改数据库连接 |
| `plugins/order_notify/` | `order_notify.db` | Schema: `order_notify`，改数据库连接 |
| `captcha-service/` | `verorun.db` | 迁入 public schema 或以独立库运行 |

### 5.4 全局搜索清单

执行迁移前需要全文搜索以下关键字，逐文件审查和替换：

| 搜索关键字 | 迁移操作 |
|-----------|----------|
| `sqlite3.connect` | 替换为连接池 |
| `row_factory` | 删除或替换 |
| `check_same_thread` | 删除 |
| `PRAGMA` | 全部删除 |
| `ATTACH DATABASE` | 替换为 search_path |
| `AUTOINCREMENT` | 替换为 IDENTITY |
| `datetime('now'` | 替换为 NOW() |
| `strftime(` | 替换为 TO_CHAR() |
| `IFNULL(` | 替换为 COALESCE() |
| `REPLACE INTO` | 替换为 INSERT ... ON CONFLICT |
| `last_insert_rowid` | 替换为 RETURNING id |
| `json_extract(` | 替换为 `->>` 操作符 |
| `.execute(` | 逐行审查占位符 |

---

## 六、安装部署步骤

```bash
# 1. 安装 PostgreSQL 16
sudo apt update
sudo apt install -y postgresql-16 postgresql-contrib

# 2. 启动并设置开机自启
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 3. 创建数据库和用户
sudo -u postgres psql <<EOF
CREATE USER easykai WITH PASSWORD 'your_secure_password';
CREATE DATABASE easykai OWNER easykai;
GRANT ALL PRIVILEGES ON DATABASE easykai TO easykai;
-- 允许本地连接
ALTER USER easykai CREATEDB;
EOF

# 4. 配置 pg_hba.conf 允许密码认证
# /etc/postgresql/16/main/pg_hba.conf 添加:
# local   all   easykai   md5
# host    all   easykai   127.0.0.1/32   md5

# 5. 安装 Python 依赖
cd /home/easykai/easykai-workspace/easykai.cn
pip install psycopg2-binary==2.9.9

# 6. 更新 .env 环境变量（新增以下配置）
cat >> .env <<EOF
DB_ENGINE=postgresql
PG_HOST=localhost
PG_PORT=5432
PG_DB=easykai
PG_USER=easykai
PG_PASSWORD=your_secure_password
EOF

# 7. 执行数据迁移
python scripts/sqlite_to_pg_migrate.py

# 8. 重启所有服务
sudo systemctl restart verorun-auth
sudo systemctl restart verorun-platform
sudo systemctl restart verorun-admin
sudo systemctl restart verorun-health

# 9. 验证
curl -s http://localhost:8081/health | python -m json.tool
curl -s http://localhost:8084/admin/api/health | python -m json.tool
```

---

## 七、回滚方案

```bash
# 1. 切换回 SQLite 模式
# 修改 .env，注释 PG_* 配置，恢复 DB_PATH
sed -i 's/^DB_ENGINE=postgresql/#DB_ENGINE=postgresql/' .env
sed -i 's/^PG_HOST=/#PG_HOST=/' .env

# 2. 恢复原始数据库代码
git checkout auth-center/models/database.py
git checkout auth-center/models/cms.py
git checkout auth-center/models/user.py
git checkout auth-center/models/site.py

# 3. 重启所有服务
sudo systemctl restart verorun-*

# 4. 确认 SQLite 数据完整
python -c "
from auth_center.models.database import get_db
with get_db() as db:
    row = db.execute('SELECT COUNT(*) FROM users').fetchone()
    print(f'Users: {row[0]}')
"
```

---

## 八、工作量估算

| 阶段 | 工作内容 | 预估人天 |
|------|----------|----------|
| 1. SQL 审计 | 全项目扫描所有 `.execute()` 调用，分类 SQLite 特有语法 | 3-5 |
| 2. Schema 迁移 | 编写迁移脚本，转换 DDL，处理 AUTOINCREMENT → SERIAL | 2-3 |
| 3. database.py 重写 | 2300 行重写，替换所有 PRAGMA、ATTACH、连接管理 | 5-7 |
| 4. 全项目 SQL 改造 | 逐个文件替换占位符、时间函数、特殊语法 | 8-12 |
| 5. 插件数据库迁移 | 5+ 个插件独立库改造 | 3-5 |
| 6. 连接池/ORM 引入 | 引入 psycopg2 连接池或 SQLAlchemy | 2-3 |
| 7. 数据迁移脚本 | SQLite → PostgreSQL 数据导出导入 | 1-2 |
| 8. 测试 & 修复 | 全功能回归测试 | 5-7 |
| **合计** | | **29-44 人天** |

---

## 九、风险清单

| 风险等级 | 描述 | 缓解措施 |
|----------|------|----------|
| **高** | SQL 语法遗漏导致运行时崩溃（272+ 处查询） | 全文搜索 + 逐文件审查清单 |
| **高** | 跨库 JOIN 逻辑重构后数据不一致 | 迁移后执行数据校验脚本 |
| **中** | 插件系统独立数据库需逐个修改，可能破坏热加载机制 | 先在一个插件上验证方案 |
| **中** | 现有备份脚本全部基于 SQLite `.dump` | 预先编写 pg_dump 备份脚本 |
| **低** | 连接池配置不当导致连接泄漏 | 设置连接超时 + 监控池状态 |
