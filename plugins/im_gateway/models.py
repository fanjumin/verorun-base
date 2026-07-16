#!/usr/bin/env python3
"""IM Gateway Plugin — 数据库模型

独立数据库 im_gateway.db，存放频道配置表 channel_configs。
从主库迁移而来（feishu/wecom/qq/dingtalk），主库结构保持一致。
"""
import psycopg2
import psycopg2.extras
import os


class _PgConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface."""
    def __init__(self, conn):
        self._conn = conn
    def execute(self, sql, params=None):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if params is not None:
            cur.execute(sql.replace('?', '%s'), params)
        else:
            cur.execute(sql)
        return cur
    def commit(self):
        self._conn.commit()
    def close(self):
        self._conn.close()


DB_PATH = os.path.join(os.path.dirname(__file__), 'im_gateway.db')

_im_conn = None

# 默认频道种子（channel, is_enabled）
_SEED_CHANNELS = [
    ('feishu', 1),
    ('wecom', 1),
    ('qq', 0),
    ('dingtalk', 0),
]


def get_im_db():
    """获取 IM Gateway 插件独立数据库连接"""
    global _im_conn
    if _im_conn is None:
        _im_conn = psycopg2.connect(
            host=os.environ.get('PG_HOST','localhost'),
            port=int(os.environ.get('PG_PORT',5432)),
            dbname=os.environ.get('PG_DB','verorun'),
            user=os.environ.get('PG_USER','verorun'),
            password=os.environ.get('PG_PASSWORD',''),
            cursor_factory=RealDictCursor
        )
        _im_conn.execute("CREATE SCHEMA IF NOT EXISTS im_gateway")
        _im_conn.execute("SET search_path TO im_gateway")
    return _PgConnection(_im_conn)


def init_im_db():
    """初始化频道配置表 + 种子数据（幂等）。

    表结构与主库 channel_configs 保持完全一致，便于数据迁移。
    """
    conn = get_im_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS channel_configs (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            channel         TEXT NOT NULL UNIQUE,
            config_json     TEXT NOT NULL DEFAULT '{}',
            is_enabled      BIGINT DEFAULT 0,
            created_at      TEXT DEFAULT NOW(),
            updated_at      TEXT DEFAULT NOW()
        )
    """)
    for channel, is_enabled in _SEED_CHANNELS:
        exists = conn.execute(
            "SELECT id FROM channel_configs WHERE channel=%s", (channel,)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO channel_configs (channel, config_json, is_enabled) VALUES (%s, '{}', %s)",
                (channel, is_enabled)
            )
    conn.commit()


def migrate_from_main_db():
    """从主库 channel_configs 迁移已有配置到插件库（幂等）。

    仅当插件库对应频道 config_json 为空 '{}' 时才覆盖，避免回退用户新改的配置。
    主库无 channel_configs 表或无数据时静默跳过。
    返回迁移的记录数。
    """
    try:
        from models import get_db as get_main_db
    except Exception:
        return 0

    migrated = 0
    try:
        with get_main_db() as main:
            has_table = main.execute(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE tablename='channel_configs'"
            ).fetchone()
            if not has_table:
                return 0
            rows = main.execute(
                "SELECT channel, config_json, is_enabled FROM channel_configs"
            ).fetchall()
    except Exception:
        return 0

    conn = get_im_db()
    for r in rows:
        channel = r['channel']
        config_json = r['config_json'] or '{}'
        is_enabled = r['is_enabled']
        local = conn.execute(
            "SELECT config_json FROM channel_configs WHERE channel=%s", (channel,)
        ).fetchone()
        if local is None:
            conn.execute(
                "INSERT INTO channel_configs (channel, config_json, is_enabled) VALUES (%s, %s, %s)",
                (channel, config_json, is_enabled)
            )
            migrated += 1
        elif (local['config_json'] or '{}') == '{}' and config_json != '{}':
            conn.execute(
                "UPDATE channel_configs SET config_json=%s, is_enabled=%s, updated_at=NOW() WHERE channel=%s",
                (config_json, is_enabled, channel)
            )
            migrated += 1
    conn.commit()
    return migrated
