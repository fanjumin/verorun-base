"""
Coupons Plugin — 独立数据库
============================
插件自己的 coupons.db，主库只读 users/order_items/api_logs/admin_actions 表。
"""

import os
import sqlite3
from contextlib import contextmanager

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, 'coupons.db')


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
        conn.execute('''CREATE TABLE IF NOT EXISTS coupons (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            code            TEXT UNIQUE NOT NULL,
            name            TEXT DEFAULT '',
            coupon_type     TEXT DEFAULT 'fixed',
            value           REAL NOT NULL DEFAULT 0,
            min_amount      REAL DEFAULT 0,
            min_quantity    INTEGER DEFAULT 0,
            usage_limit     INTEGER DEFAULT 0,
            used_count      INTEGER DEFAULT 0,
            per_user_limit  INTEGER DEFAULT 1,
            expire_at       TEXT,
            is_active       INTEGER DEFAULT 1,
            description     TEXT DEFAULT '',
            coupon_category TEXT DEFAULT 'general',
            applicable_products TEXT DEFAULT '',
            applicable_plans    TEXT DEFAULT '',
            scene           TEXT DEFAULT '',
            first_month_only   INTEGER DEFAULT 0,
            stackable       INTEGER DEFAULT 0,
            active_from     TEXT,
            active_to       TEXT,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS coupon_redemptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_id       INTEGER NOT NULL REFERENCES coupons(id),
            user_id         INTEGER NOT NULL,
            order_no        TEXT NOT NULL,
            discount_fen    INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()


@contextmanager
def get_main_db():
    """只读连接主库（用于查询 users/order_items/api_logs/admin_actions 表）。"""
    from models import get_db as main_get_db
    with main_get_db() as conn:
        yield conn
