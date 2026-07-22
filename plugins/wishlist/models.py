"""
Wishlist Plugin — 独立数据库
=============================
插件自己的 wishlist.db，主库只读 products 表。
"""

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from plugins._base.db import get_raw_connection


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


PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))


@contextmanager
def get_db():
    """连接插件自己的数据库。"""
    conn = get_raw_connection()
    conn.autocommit = False
    conn.execute("CREATE SCHEMA IF NOT EXISTS wishlist")
    conn.execute("SET search_path TO wishlist")
    try:
        yield _PgConnection(conn)
    finally:
        conn.close()


def init_db():
    """创建插件自己的表。"""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS wishlist (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                product_id  BIGINT NOT NULL,
                created_at  TEXT DEFAULT (NOW()),
                UNIQUE(user_id, product_id)
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_wishlist_user ON wishlist(user_id)')
        conn.commit()


@contextmanager
def get_main_db():
    """只读连接主库（用于查询 products 表）。"""
    from models import get_db as main_get_db
    with main_get_db() as conn:
        yield conn
