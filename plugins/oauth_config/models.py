#!/usr/bin/env python3
"""OAuth Plugin — 独立数据库模型

oauth_providers 表迁移至插件独立数据库 oauth.db，与主库完全解耦。
"""
import os
import sys
import sqlite3
from contextlib import contextmanager

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PLUGIN_DIR, 'data')
_DB_PATH = os.path.join(_DATA_DIR, 'oauth.db')
os.makedirs(_DATA_DIR, exist_ok=True)


@contextmanager
def get_db():
    """获取插件独立数据库连接"""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()


def init_oauth_tables():
    """创建 oauth_providers 表（幂等）"""
    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS oauth_providers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            site_domain   TEXT NOT NULL,
            provider      TEXT NOT NULL DEFAULT 'douyin',
            client_key    TEXT NOT NULL DEFAULT '',
            client_secret TEXT NOT NULL DEFAULT '',
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT,
            updated_at    TEXT,
            UNIQUE(site_domain, provider)
        )
    """)
    conn.commit()
    conn.close()
    print(f'[OAuthPlugin] ✅ 独立数据库 oauth.db 已就绪（{_DB_PATH}）')
