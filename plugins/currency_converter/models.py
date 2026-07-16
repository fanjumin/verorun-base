#!/usr/bin/env python3
"""
Currency Converter Plugin Models — PostgreSQL schema: currency_converter
=========================================================================
汇率 + 用户币种偏好，完全独立于主库。
"""
import os
import psycopg2
import psycopg2.extras

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, 'currency_converter.db')  # 保留用于迁移

_conn = None


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


def get_db():
    """获取插件数据库连接（单例，PG schema: currency_converter）"""
    global _conn
    if _conn is None:
        raw = psycopg2.connect(
            host=os.environ.get('PG_HOST', 'localhost'),
            port=int(os.environ.get('PG_PORT', 5432)),
            dbname=os.environ.get('PG_DB', 'verorun'),
            user=os.environ.get('PG_USER', 'verorun'),
            password=os.environ.get('PG_PASSWORD', ''),
        )
        raw.autocommit = False
        raw.cursor().execute("CREATE SCHEMA IF NOT EXISTS currency_converter")
        raw.commit()
        raw.cursor().execute("SET search_path TO currency_converter")
        raw.commit()
        _conn = _PgConnection(raw)
    return _conn


def init_db():
    """创建插件数据库表（幂等）"""
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS exchange_rates (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        currency_code   TEXT UNIQUE NOT NULL,
        rate_to_base    DOUBLE PRECISION NOT NULL,
        base_currency   TEXT NOT NULL DEFAULT 'CNY',
        source          TEXT DEFAULT '',
        fetched_at      TIMESTAMPTZ DEFAULT NOW()
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS user_currency_prefs (
        id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id             BIGINT UNIQUE NOT NULL,
        preferred_currency  TEXT NOT NULL DEFAULT 'CNY',
        updated_at          TIMESTAMPTZ DEFAULT NOW()
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_exchange_code ON exchange_rates(currency_code)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_user_pref ON user_currency_prefs(user_id)')
    conn.commit()
    print('[CurrencyConverter] PG schema currency_converter initialized')
