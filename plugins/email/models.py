#!/usr/bin/env python3
"""
Email Plugin Models — 独立数据库 email.db
==========================================
完全独立于主库，不依赖主系统 models。
参考 ads 插件模式设计。
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'email.db')

_email_conn = None


def get_email_db():
    """获取邮件插件独立数据库连接（单例）"""
    global _email_conn
    if _email_conn is None:
        _email_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _email_conn.row_factory = sqlite3.Row
        _email_conn.execute("PRAGMA journal_mode=WAL")
        _email_conn.execute("PRAGMA busy_timeout=1000")
        _email_conn.execute("PRAGMA foreign_keys=ON")
    return _email_conn


def init_email_db():
    """初始化邮件插件数据库表（幂等）"""
    conn = get_email_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS email_sent (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        from_addr       TEXT NOT NULL,
        to_addr         TEXT NOT NULL,
        subject         TEXT NOT NULL,
        body_text       TEXT,
        body_html       TEXT,
        in_reply_to     INTEGER,
        sent_at         TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_email_sent_from ON email_sent(from_addr)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_email_sent_sent_at ON email_sent(sent_at)')
    conn.commit()
    print('[EmailPlugin] email.db 已初始化')


# 兼容旧接口名
ensure_email_tables = init_email_db