#!/usr/bin/env python3
"""OAuth Plugin — 独立数据库模型

oauth_providers 表在插件独立 Schema oauth_config 中，与主库完全解耦。
"""
import psycopg2
from contextlib import contextmanager
from plugins._base.db import PgConnection
from plugins._base.db import get_raw_connection

# §10.5 standard logging — safe: __init__.py defines _plugin_log at module level, no circular import
from plugins.oauth_config import _plugin_log


@contextmanager
def get_db():
    """获取插件独立数据库连接"""
    conn = get_raw_connection()
    conn.autocommit = False
    try:
        wrapped = PgConnection(conn)
        wrapped.execute("CREATE SCHEMA IF NOT EXISTS oauth_config")
        wrapped.execute("SET search_path TO oauth_config")
        yield wrapped
    finally:
        conn.close()


def init_oauth_tables():
    """创建 oauth_providers 表（幂等）"""
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
    _plugin_log('[OAuthPlugin] Schema oauth_config is ready')
