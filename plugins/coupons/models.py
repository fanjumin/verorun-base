"""
Coupons Plugin — PostgreSQL schema: coupons
============================================
插件自己的 coupons schema，主库只读 users/order_items/api_logs/admin_actions 表。
"""

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, 'coupons.db')  # 保留用于迁移


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


@contextmanager
def get_db():
    """连接插件自己的数据库（PG schema: coupons）。"""
    raw = psycopg2.connect(
        host=os.environ.get('PG_HOST', 'localhost'),
        port=int(os.environ.get('PG_PORT', 5432)),
        dbname=os.environ.get('PG_DB', 'verorun'),
        user=os.environ.get('PG_USER', 'verorun'),
        password=os.environ.get('PG_PASSWORD', ''),
    )
    raw.autocommit = False
    raw.cursor().execute("CREATE SCHEMA IF NOT EXISTS coupons")
    raw.commit()
    raw.cursor().execute("SET search_path TO coupons")
    raw.commit()
    conn = _PgConnection(raw)
    try:
        yield conn
    finally:
        raw.close()


def init_db():
    """创建插件自己的表。"""
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS coupons (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            code            TEXT UNIQUE NOT NULL,
            name            TEXT DEFAULT '',
            coupon_type     TEXT DEFAULT 'fixed',
            value           DOUBLE PRECISION NOT NULL DEFAULT 0,
            min_amount      DOUBLE PRECISION DEFAULT 0,
            min_quantity    BIGINT DEFAULT 0,
            usage_limit     BIGINT DEFAULT 0,
            used_count      BIGINT DEFAULT 0,
            per_user_limit  BIGINT DEFAULT 1,
            expire_at       TIMESTAMPTZ,
            is_active       BIGINT DEFAULT 1,
            description     TEXT DEFAULT '',
            coupon_category TEXT DEFAULT 'general',
            applicable_products TEXT DEFAULT '',
            applicable_plans    TEXT DEFAULT '',
            scene           TEXT DEFAULT '',
            first_month_only   BIGINT DEFAULT 0,
            stackable       BIGINT DEFAULT 0,
            active_from     TIMESTAMPTZ,
            active_to       TIMESTAMPTZ,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS coupon_redemptions (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            coupon_id       BIGINT NOT NULL REFERENCES coupons(id),
            user_id         BIGINT NOT NULL,
            order_no        TEXT NOT NULL,
            discount_fen    BIGINT NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )''')
        conn.commit()


@contextmanager
def get_main_db():
    """只读连接主库（用于查询 users/order_items/api_logs/admin_actions 表）。"""
    from models import get_db as main_get_db
    with main_get_db() as conn:
        yield conn
