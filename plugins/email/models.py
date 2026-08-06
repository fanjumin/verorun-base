#!/usr/bin/env python3
"""
Email Plugin Models — PostgreSQL schema: email
===============================================
完全独立于主库，使用独立 PG schema。
"""

from i18n import _
import psycopg2
import psycopg2.extras
from plugins._base.db import get_raw_connection

_email_conn = None


class _PgConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface."""
    def __init__(self, conn):
        self._conn = conn
    def execute(self, sql, params=None):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if params is not None:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        return cur
    def commit(self):
        self._conn.commit()
    def close(self):
        self._conn.close()


def get_email_db():
    """获取邮件插件数据库连接（单例，PG schema: email）"""
    global _email_conn
    if _email_conn is None:
        raw = get_raw_connection()
        raw.autocommit = False
        raw.cursor().execute("CREATE SCHEMA IF NOT EXISTS email")
        raw.commit()
        raw.cursor().execute("SET search_path TO email")
        raw.commit()
        _email_conn = _PgConnection(raw)
    return _email_conn


def init_email_db():
    """初始化邮件插件数据库表（幂等）"""
    conn = get_email_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS email_sent (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        from_addr       TEXT NOT NULL,
        to_addr         TEXT NOT NULL,
        subject         TEXT NOT NULL,
        body_text       TEXT,
        body_html       TEXT,
        in_reply_to     BIGINT,
        sent_at         TIMESTAMPTZ DEFAULT NOW()
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_email_sent_from ON email_sent(from_addr)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_email_sent_sent_at ON email_sent(sent_at)')
    conn.commit()
    print(_('[EmailPlugin] PG schema email initialized'))


# 兼容旧接口名
ensure_email_tables = init_email_db