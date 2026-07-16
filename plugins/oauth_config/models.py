#!/usr/bin/env python3
"""OAuth Plugin — 独立数据库模型

oauth_providers 表迁移至插件独立数据库 oauth.db，与主库完全解耦。
"""
import os
import sys
import psycopg2
import psycopg2.extras
from contextlib import contextmanager


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


_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PLUGIN_DIR, 'data')
_DB_PATH = os.path.join(_DATA_DIR, 'oauth.db')
os.makedirs(_DATA_DIR, exist_ok=True)


@contextmanager
def get_db():
    """获取插件独立数据库连接"""
    conn = psycopg2.connect(
        host=os.environ.get('PG_HOST','localhost'),
        port=int(os.environ.get('PG_PORT',5432)),
        dbname=os.environ.get('PG_DB','verorun'),
        user=os.environ.get('PG_USER','verorun'),
        password=os.environ.get('PG_PASSWORD',''),
        cursor_factory=RealDictCursor
    )
    conn.execute("CREATE SCHEMA IF NOT EXISTS oauth_config")
    conn.execute("SET search_path TO oauth_config")
    try:
        yield conn
    finally:
        conn.close()


def init_oauth_tables():
    """创建 oauth_providers 表（幂等）"""
    os.makedirs(_DATA_DIR, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oauth_providers (
                id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                site_domain   TEXT NOT NULL,
                provider      TEXT NOT NULL DEFAULT 'douyin',
                client_key    TEXT NOT NULL DEFAULT '',
                client_secret TEXT NOT NULL DEFAULT '',
                is_active     BIGINT NOT NULL DEFAULT 1,
                created_at    TEXT,
                updated_at    TEXT,
                UNIQUE(site_domain, provider)
            )
        """)
        conn.commit()
    print(f'[OAuthPlugin] ✅ Schema oauth_config 已就绪')
