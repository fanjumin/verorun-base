#!/usr/bin/env python3
"""Enterprise Verification Plugin — 数据库模型"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'enterprise_verify.db')

_ev_conn = None


def get_ev_db():
    """获取企业认证插件独立数据库连接"""
    global _ev_conn
    if _ev_conn is None:
        _ev_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _ev_conn.row_factory = sqlite3.Row
        _ev_conn.execute("PRAGMA journal_mode=WAL")
        _ev_conn.execute("PRAGMA busy_timeout=1000")
        _ev_conn.execute("PRAGMA foreign_keys=ON")
    return _ev_conn


def init_ev_db():
    """初始化企业认证表"""
    conn = get_ev_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS enterprise_verifications (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        enterprise_name TEXT NOT NULL,
        tax_id          TEXT NOT NULL,
        license_url     TEXT DEFAULT '',
        ocr_raw         TEXT DEFAULT '',
        status          TEXT NOT NULL DEFAULT 'pending',
        review_notes    TEXT DEFAULT '',
        reviewed_by     INTEGER,
        reviewed_at     TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_user ON enterprise_verifications(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_status ON enterprise_verifications(status)')
    conn.commit()
    print('[EnterpriseVerifyPlugin] enterprise_verify.db 已初始化')