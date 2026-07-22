"""
Reviews Plugin — 独立数据库
============================
插件自己的 reviews.db，主库只读 users/products/order_items 表。
"""

import os
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


PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, 'reviews.db')


@contextmanager
def get_db():
    """连接插件自己的数据库。"""
    from plugins._base.db import get_raw_connection
    conn = get_raw_connection()
    conn.execute("CREATE SCHEMA IF NOT EXISTS reviews")
    conn.execute("SET search_path TO reviews")
    try:
        yield _PgConnection(conn)
    finally:
        conn.close()


def init_db():
    """创建插件自己的表。"""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS product_reviews (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id         BIGINT NOT NULL,
                product_id      BIGINT NOT NULL,
                order_id        TEXT DEFAULT '',
                rating          BIGINT NOT NULL DEFAULT 5 CHECK(rating >= 1 AND rating <= 5),
                content         TEXT DEFAULT '',
                images          TEXT DEFAULT '[]',
                spec_info       TEXT DEFAULT '',
                is_anonymous    BIGINT DEFAULT 0,
                is_verified     BIGINT DEFAULT 0,
                reply_content   TEXT DEFAULT '',
                reply_at        TEXT,
                is_active       BIGINT DEFAULT 1,
                created_at      TEXT DEFAULT NOW(),
                updated_at      TEXT DEFAULT NOW(),
                UNIQUE(user_id, product_id, order_id)
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reviews_product ON product_reviews(product_id, is_active)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_reviews_user ON product_reviews(user_id)')
        conn.commit()


@contextmanager
def get_main_db():
    """只读连接主库（用于查询 users/products/order_items 表）。"""
    from models import get_db as main_get_db
    with main_get_db() as conn:
        yield conn
