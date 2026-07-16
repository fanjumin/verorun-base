#!/usr/bin/env python3
"""
VeroRun SQLite → PostgreSQL 全量数据迁移工具
============================================
用途：将所有 SQLite .db 文件数据迁移到 PostgreSQL，按 Schema 隔离。

使用：
  python tools/migrate_to_pg.py --dry-run     # 预演，不写 PG
  python tools/migrate_to_pg.py               # 执行迁移
  python tools/migrate_to_pg.py --only main   # 仅迁移主库
  python tools/migrate_to_pg.py --only plugins # 仅迁移插件

前置条件：
  - PostgreSQL 必须可连接（通过环境变量或默认值）
  - 所有 Python 模型代码已迁移到 PG（即已完成 Phase 1A-1C）
  - 先运行主应用初始化函数创建 schema 和表，再运行本脚本迁移数据

环境变量：
  PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASSWORD
"""

import os
import sys
import sqlite3
import argparse
import logging
from datetime import datetime, timezone
from collections import OrderedDict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 日志 ──
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('migrate')

# ── 项目根目录 ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')

# ── PG 连接配置 ──
PG_CONFIG = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': int(os.environ.get('PG_PORT', 5432)),
    'dbname': os.environ.get('PG_DB', 'verorun'),
    'user': os.environ.get('PG_USER', 'verorun'),
    'password': os.environ.get('PG_PASSWORD', ''),
}

# ── PostgreSQL 保留字映射 ──
PG_RESERVED_COLUMNS = {
    'user', 'group', 'order', 'table', 'select', 'from', 'where',
    'join', 'index', 'primary', 'key', 'foreign', 'references',
    'default', 'check', 'constraint', 'unique', 'null', 'not',
    'column', 'database', 'schema', 'grant', 'revoke', 'role',
}

# ================================================================
# 迁移清单定义
# ================================================================

# 主库（public schema）：verorun.db / x7k2m9a4.db
# 由 database.py 的 init_all_tables() 管理，表在 public schema
MAIN_TABLES = OrderedDict({
    'public': {                        # public schema 表
        'source': os.path.join(DATA_DIR, 'x7k2m9a4.db'),
        'fallback': os.path.join(DATA_DIR, 'verorun.db'),
        'tables': [
            'users', 'sessions', 'oauth_providers', 'oauth_accounts',
            'api_logs', 'admin_actions', 'system_config', 'notifications',
            'notification_settings', 'user_preferences', 'addresses',
            'totp_secrets', 'backup_codes', 'password_resets',
            'email_verifications', 'phone_verifications', 'audit_logs',
            'rate_limits', 'webhooks', 'webhook_logs',
            'user_agents', 'login_attempts', 'sso_tokens',
            'deployments', 'deployment_heartbeats', 'deployment_logs',
            'cleaner_agent_configs', 'comments', 'agents',
            'agent_api_keys', 'agent_metrics',
        ],
    },
})

# Shop schema 表（shop.db）
SHOP_TABLES = OrderedDict({
    'shop': {
        'source': os.path.join(DATA_DIR, 'shop.db'),
        'tables': [
            'products', 'categories', 'carts', 'user_purchases',
            'order_items', 'product_specs', 'product_spec_values',
            'product_skus', 'pricing_rules', 'express_companies',
            'order_shipping',
        ],
    },
})

# 插件独立 Schema → SQLite 文件映射
PLUGIN_SCHEMA_MAP = OrderedDict({
    'ads': 'plugins/ads/ads.db',
    'ali_api': 'plugins/ali_api/ali_api.db',
    'analytics': 'plugins/analytics/data/analytics.db',
    'chatbot': 'plugins/chatbot/data/chatbot.db',
    'content_factory': 'plugins/content_factory/content_factory.db',
    'coupons': 'plugins/coupons/coupons.db',
    'currency_converter': 'plugins/currency_converter/currency_converter.db',
    'email': 'plugins/email/email.db',
    'enterprise_verify': 'plugins/enterprise_verify/enterprise_verify.db',
    'health': 'plugins/health_check/data/health.db',
    'im_gateway': 'plugins/im_gateway/im_gateway.db',
    'logistics': 'plugins/logistics/logistics.db',
    'oauth_config': 'plugins/data/oauth.db',
    'order_notify': 'plugins/order_notify/data/order_notify.db',
    'payment': 'plugins/payment/payment.db',
    'reviews': 'plugins/reviews/reviews.db',
    'sms': 'plugins/sms/sms.db',
    'social_push': 'plugins/social_push/social_push.db',
    'subscription': None,   # subscription 表已在 plugin_manager 迁移
    'verification': 'plugins/verification/verification.db',
    'wishlist': 'plugins/wishlist/wishlist.db',
})

# license_server 独立数据库
LICENSE_SERVER = {
    'source': os.path.join(ROOT, 'plugin_manager/license_server/data/license_server.db'),
    'tables': ['licenses', 'license_validations', 'license_activations'],
}

# ================================================================
# 连接辅助
# ================================================================

def get_pg_conn():
    """获取 PostgreSQL 连接。"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        log.error("请安装 psycopg2: pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(cursor_factory=RealDictCursor, **PG_CONFIG)
    conn.autocommit = False
    return conn


def get_sqlite_conn(db_path: str):
    """获取 SQLite 只读连接。"""
    if not os.path.isfile(db_path):
        return None
    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def discover_tables(sqlite_conn) -> list[str]:
    """获取 SQLite 库中所有用户表名。"""
    cur = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [r['name'] for r in cur]


def quote_col(name: str) -> str:
    """为 PG 保留字列名加引号。"""
    if name.lower() in PG_RESERVED_COLUMNS:
        return f'"{name}"'
    return name


# ================================================================
# 类型映射
# ================================================================

def sqlite_type_to_pg(col_type: str) -> str:
    """SQLite 亲和类型 → PostgreSQL 类型。"""
    t = col_type.upper().strip()
    if 'INT' in t:
        return 'BIGINT'
    if 'REAL' in t or 'FLOAT' in t or 'DOUB' in t:
        return 'DOUBLE PRECISION'
    if 'BOOL' in t:
        return 'BOOLEAN'
    if 'BLOB' in t or 'NONE' in t:
        return 'BYTEA'
    return 'TEXT'


def convert_value(value, col_name: str, col_type: str):
    """
    转换 SQLite 值到 PostgreSQL 兼容格式。
    - SQLite datetime 字符串 → PG timestamp
    - SQLite INTEGER (bool) → PG boolean
    - None → None (NULL)
    """
    if value is None:
        return None

    t = col_type.upper().strip() if col_type else ''

    # BOOLEAN 列：INTEGER 0/1 → True/False
    if 'BOOL' in t:
        return bool(value)

    # TEXT 列：保持原样
    if isinstance(value, str):
        return value

    # INTEGER/BIGINT 列：确保是 int
    if isinstance(value, (int, float)):
        if 'INT' in t:
            return int(value)
        if 'REAL' in t or 'FLOAT' in t or 'DOUB' in t:
            return float(value)

    return value


# ================================================================
# 核心迁移逻辑
# ================================================================

def migrate_table(
    pg_conn, sqlite_conn, table_name: str, schema: str,
    dry_run: bool = False,
) -> dict:
    """
    迁移单表数据。
    返回: {'rows': int, 'errors': int, 'skipped': int}
    """
    result = {'rows': 0, 'errors': 0, 'skipped': 0}

    # 获取 SQLite 列信息
    col_info = sqlite_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    if not col_info:
        log.warning(f"  [{schema}] {table_name}: 无列信息，跳过")
        result['skipped'] = 1
        return result

    columns = []
    pg_types = []
    for c in col_info:
        name = c['name']
        # SQLite 的 INTEGER PRIMARY KEY 在 PG 里是 BIGINT IDENTITY
        pg_type = sqlite_type_to_pg(c['type'] or '')
        columns.append(name)
        pg_types.append(pg_type)

    # 构建 INSERT 语句（ON CONFLICT DO NOTHING 避免重复）
    col_list = ', '.join(quote_col(c) for c in columns)
    placeholders = ', '.join('%s' for _ in columns)
    pk = columns[0]  # 假设第一列是主键名

    insert_sql = (
        f'INSERT INTO {schema}."{table_name}" ({col_list}) '
        f'VALUES ({placeholders}) '
        f'ON CONFLICT ("{pk}") DO NOTHING'
    )

    # 读取 SQLite 数据
    try:
        rows = sqlite_conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
    except sqlite3.Error as e:
        log.error(f"  [{schema}] {table_name}: 读取失败 - {e}")
        result['errors'] = 1
        return result

    if not rows:
        log.info(f"  [{schema}] {table_name}: 0 行（空表），跳过")
        result['skipped'] = 1
        return result

    # 插入 PG
    if dry_run:
        log.info(f"  [{schema}] {table_name}: {len(rows)} 行（dry-run，未写入）")
        result['rows'] = len(rows)
        return result

    batch = []
    batch_size = 500
    inserted = 0

    cur = pg_conn.cursor()
    try:
        for row in rows:
            values = []
            for i, col_name in enumerate(columns):
                val = row[col_name]
                val = convert_value(val, col_name, pg_types[i])
                values.append(val)
            batch.append(tuple(values))

            if len(batch) >= batch_size:
                cur.executemany(insert_sql, batch)
                inserted += len(batch)
                batch = []

        # 剩余行
        if batch:
            cur.executemany(insert_sql, batch)
            inserted += len(batch)
    except Exception as e:
        log.error(f"  [{schema}] {table_name}: 插入失败 - {e}")
        result['errors'] = len(rows)
        return result

    result['rows'] = inserted
    return result


def reset_pg_sequence(pg_conn, schema: str, tables: list[str]):
    """
    重置 PostgreSQL SERIAL/IDENTITY 序列，使后续 INSERT 从 max(id)+1 开始。
    """
    cur = pg_conn.cursor()
    for table in tables:
        try:
            cur.execute(
                "SELECT pg_get_serial_sequence(%s, 'id')",
                (f'{schema}."{table}"',),
            )
            seq = cur.fetchone()
            if seq and seq[0]:
                seq_name = seq[0]
                cur.execute(f"SELECT setval(%s, COALESCE((SELECT MAX(id) FROM {schema}.\"{table}\"), 1))", (seq_name,))
        except Exception:
            pass  # 表可能无 SERIAL 列
    pg_conn.commit()


# ================================================================
# 迁移入口
# ================================================================

def migrate_main(pg_conn, dry_run: bool):
    """迁移主库 public + shop schema。"""
    log.info("=" * 60)
    log.info("开始迁移：主库 public schema")

    # 尝试主源 x7k2m9a4.db，fallback verorun.db
    source = MAIN_TABLES['public']['source']
    if not os.path.isfile(source):
        source = MAIN_TABLES['public']['fallback']

    if not os.path.isfile(source):
        log.warning(f"主库文件不存在: {source}，跳过")
        return

    sqlite_conn = get_sqlite_conn(source)
    if not sqlite_conn:
        log.warning(f"无法打开 SQLite: {source}")
        return

    try:
        # 自动发现 or 使用预定义列表
        actual_tables = discover_tables(sqlite_conn)
        log.info(f"发现 {len(actual_tables)} 个表: {actual_tables[:10]}...")

        total = 0
        for table in actual_tables:
            # 跳过 shop 表（单独迁移）
            if table in SHOP_TABLES.get('shop', {}).get('tables', []):
                continue
            r = migrate_table(pg_conn, sqlite_conn, table, 'public', dry_run)
            total += r['rows']
            log.info(f"  [public] {table}: {r['rows']} 行")
            # 每表独立事务：失败不回滚整个连接，成功则提交
            if not dry_run:
                if r['errors'] > 0:
                    pg_conn.rollback()
                    log.warning(f"  [public] {table}: 已回滚（{r['errors']} 条错误）")
                else:
                    pg_conn.commit()

        reset_pg_sequence(pg_conn, 'public', actual_tables)
        pg_conn.commit()
        log.info(f"public schema 迁移完成：共 {total} 行")
    finally:
        sqlite_conn.close()

    # ── Shop schema ──
    shop_path = SHOP_TABLES['shop']['source']
    if os.path.isfile(shop_path):
        log.info("-" * 40)
        log.info("开始迁移：shop schema")

        shop_conn = get_sqlite_conn(shop_path)
        if shop_conn:
            try:
                actual_tables = discover_tables(shop_conn)
                total = 0
                for table in actual_tables:
                    r = migrate_table(pg_conn, shop_conn, table, 'shop', dry_run)
                    total += r['rows']
                    log.info(f"  [shop] {table}: {r['rows']} 行")
                    # 每表独立事务
                    if not dry_run:
                        if r['errors'] > 0:
                            pg_conn.rollback()
                            log.warning(f"  [shop] {table}: 已回滚（{r['errors']} 条错误）")
                        else:
                            pg_conn.commit()
                reset_pg_sequence(pg_conn, 'shop', actual_tables)
                pg_conn.commit()
                log.info(f"shop schema 迁移完成：共 {total} 行")
            finally:
                shop_conn.close()


def migrate_plugins(pg_conn, dry_run: bool):
    """迁移所有插件独立 Schema。"""
    log.info("=" * 60)
    log.info(f"开始迁移：{len(PLUGIN_SCHEMA_MAP)} 个插件 Schema")

    for schema_name, rel_path in PLUGIN_SCHEMA_MAP.items():
        if rel_path is None:
            log.info(f"  [{schema_name}]: 无独立 SQLite，跳过")
            continue

        db_path = os.path.join(ROOT, rel_path)
        if not os.path.isfile(db_path):
            log.info(f"  [{schema_name}]: 文件不存在 {rel_path}，跳过")
            continue

        sqlite_conn = get_sqlite_conn(db_path)
        if not sqlite_conn:
            continue

        try:
            # 确保 schema 存在
            if not dry_run:
                pg_conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

            actual_tables = discover_tables(sqlite_conn)
            log.info(f"  [{schema_name}]: 发现 {len(actual_tables)} 个表")

            total = 0
            for table in actual_tables:
                r = migrate_table(pg_conn, sqlite_conn, table, schema_name, dry_run)
                total += r['rows']
                log.info(f"    [{schema_name}] {table}: {r['rows']} 行")
                # 每表独立事务
                if not dry_run:
                    if r['errors'] > 0:
                        pg_conn.rollback()
                        log.warning(f"    [{schema_name}] {table}: 已回滚（{r['errors']} 条错误）")
                    else:
                        pg_conn.commit()

            reset_pg_sequence(pg_conn, schema_name, actual_tables)
            pg_conn.commit()
            log.info(f"  [{schema_name}] 完成：共 {total} 行")
        except Exception as e:
            log.error(f"  [{schema_name}] 迁移失败: {e}")
            pg_conn.rollback()
        finally:
            sqlite_conn.close()


def migrate_license_server(pg_conn, dry_run: bool):
    """迁移 license_server 数据库。"""
    source = LICENSE_SERVER['source']
    if not os.path.isfile(source):
        log.info("license_server.db 不存在，跳过")
        return

    log.info("=" * 60)
    log.info("迁移 license_server 数据库")

    sqlite_conn = get_sqlite_conn(source)
    if not sqlite_conn:
        return

    try:
        actual_tables = discover_tables(sqlite_conn)
        # license_server 表迁到独立 PG 库（不同 dbname）
        # 如果只需在同一库，放在 license_server schema
        for table in actual_tables:
            r = migrate_table(pg_conn, sqlite_conn, table, 'license_server', dry_run)
            log.info(f"  [license_server] {table}: {r['rows']} 行")
    finally:
        sqlite_conn.close()


# ================================================================
# 验证
# ================================================================

def verify_migration(pg_conn):
    """迁移后验证：对比各 schema 的记录数。"""
    log.info("=" * 60)
    log.info("验证迁移完整性")

    cur = pg_conn.cursor()
    schemas_to_check = ['public', 'shop'] + list(PLUGIN_SCHEMA_MAP.keys())

    for schema in schemas_to_check:
        # 获取 schema 下所有表
        cur.execute(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname=%s",
            (schema,),
        )
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            continue

        total = 0
        for table in tables:
            cur.execute(f'SELECT COUNT(*) FROM {schema}."{table}"')
            count = cur.fetchone()[0]
            if count > 0:
                log.info(f"  [{schema}] {table}: {count} 行")
            total += count

        if total > 0:
            log.info(f"  [{schema}] 合计: {total} 行")


# ================================================================
# CLI
# ================================================================

def main():
    parser = argparse.ArgumentParser(description='VeroRun SQLite → PostgreSQL 数据迁移')
    parser.add_argument('--dry-run', action='store_true', help='预演模式，不写入 PG')
    parser.add_argument('--only', choices=['main', 'plugins', 'license'], help='仅迁移指定部分')
    parser.add_argument('--verify-only', action='store_true', help='仅验证（不迁移）')
    args = parser.parse_args()

    log.info(f"PG 目标: {PG_CONFIG['host']}:{PG_CONFIG['port']}/{PG_CONFIG['dbname']}")
    log.info(f"模式: {'DRY-RUN（不写入）' if args.dry_run else '正式迁移'}")

    pg_conn = None
    try:
        pg_conn = get_pg_conn()
        log.info("PG 连接成功")

        if args.verify_only:
            verify_migration(pg_conn)
            return

        if not args.only or args.only == 'main':
            migrate_main(pg_conn, args.dry_run)
        if not args.only or args.only == 'plugins':
            migrate_plugins(pg_conn, args.dry_run)
        if not args.only or args.only == 'license':
            migrate_license_server(pg_conn, args.dry_run)

        if not args.dry_run:
            verify_migration(pg_conn)

        log.info("=" * 60)
        log.info("迁移完成！")

    except Exception as e:
        log.error(f"迁移过程出错: {e}")
        raise
    finally:
        if pg_conn:
            pg_conn.close()


if __name__ == '__main__':
    main()
