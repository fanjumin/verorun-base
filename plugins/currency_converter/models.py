#!/usr/bin/env python3
"""
Currency Converter Plugin Models — 独立数据库 currency_converter.db
==================================================================
汇率 + 用户币种偏好，完全独立于主库。
"""
import os
import sqlite3

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PLUGIN_DIR, 'currency_converter.db')

_conn = None


def get_db():
    """获取插件独立数据库连接（单例）"""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=1000")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def init_db():
    """创建插件数据库表（幂等）"""
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS exchange_rates (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        currency_code   TEXT UNIQUE NOT NULL,
        rate_to_base    REAL NOT NULL,
        base_currency   TEXT NOT NULL DEFAULT 'CNY',
        source          TEXT DEFAULT '',
        fetched_at      TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS user_currency_prefs (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER UNIQUE NOT NULL,
        preferred_currency  TEXT NOT NULL DEFAULT 'CNY',
        updated_at          TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_exchange_code ON exchange_rates(currency_code)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_user_pref ON user_currency_prefs(user_id)')
    conn.commit()
    print('[CurrencyConverter] currency_converter.db initialized')
