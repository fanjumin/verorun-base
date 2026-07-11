#!/usr/bin/env python3
"""
Payment Plugin Models — 独立数据库 payment.db
==============================================
- payment_logs: 支付交易日志
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'payment.db')

_payment_conn = None


def get_payment_db():
    global _payment_conn
    if _payment_conn is None:
        _payment_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _payment_conn.row_factory = sqlite3.Row
        _payment_conn.execute("PRAGMA journal_mode=WAL")
        _payment_conn.execute("PRAGMA busy_timeout=1000")
        _payment_conn.execute("PRAGMA foreign_keys=ON")
    return _payment_conn


def init_payment_db():
    conn = get_payment_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS payment_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id        TEXT NOT NULL,
        subject         TEXT DEFAULT '',
        amount          REAL DEFAULT 0,
        provider        TEXT DEFAULT '',
        status          TEXT DEFAULT 'pending',
        raw_response    TEXT DEFAULT '',
        created_at      TEXT DEFAULT (datetime('now')),
        completed_at    TEXT
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_payment_logs_order ON payment_logs(order_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_payment_logs_created ON payment_logs(created_at)')
    conn.commit()
    print('[PaymentPlugin] payment.db 已初始化')


ensure_payment_tables = init_payment_db
