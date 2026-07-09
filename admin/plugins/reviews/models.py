"""
Reviews Plugin — 独立数据库
============================
插件自己的 reviews.db，主库只读 users/products/order_items 表。
"""

import os
import sqlite3
from contextlib import contextmanager

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, 'reviews.db')


@contextmanager
def get_db():
    """连接插件自己的数据库。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """创建插件自己的表。"""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS product_reviews (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                product_id      INTEGER NOT NULL,
                order_id        TEXT DEFAULT '',
                rating          INTEGER NOT NULL DEFAULT 5 CHECK(rating >= 1 AND rating <= 5),
                content         TEXT DEFAULT '',
                images          TEXT DEFAULT '[]',
                spec_info       TEXT DEFAULT '',
                is_anonymous    INTEGER DEFAULT 0,
                is_verified     INTEGER DEFAULT 0,
                reply_content   TEXT DEFAULT '',
                reply_at        TEXT,
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now','localtime')),
                updated_at      TEXT DEFAULT (datetime('now','localtime')),
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
