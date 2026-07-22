#!/usr/bin/env python3
"""Enterprise Verification Plugin — 数据库模型"""
from i18n import _
import psycopg2, os
from plugins._base.db import PgConnection
from plugins._base.db import get_raw_connection

DB_PATH = os.path.join(os.path.dirname(__file__), 'enterprise_verify.db')

_ev_conn = None


def get_ev_db():
    """获取企业认证插件独立数据库连接"""
    global _ev_conn
    if _ev_conn is None:
        raw = get_raw_connection()
        raw.autocommit = False
        _ev_conn = PgConnection(raw)
        _ev_conn.execute("CREATE SCHEMA IF NOT EXISTS enterprise_verify")
        _ev_conn.execute("SET search_path TO enterprise_verify")
        _ev_conn.commit()
    return _ev_conn


def init_ev_db():
    """初始化企业认证表"""
    conn = get_ev_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS enterprise_verifications (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id         BIGINT NOT NULL,
        enterprise_name TEXT NOT NULL,
        tax_id          TEXT NOT NULL,
        license_url     TEXT DEFAULT '',
        ocr_raw         TEXT DEFAULT '',
        status          TEXT NOT NULL DEFAULT 'pending',
        review_notes    TEXT DEFAULT '',
        reviewed_by     BIGINT,
        reviewed_at     TEXT,
        created_at      TEXT DEFAULT NOW(),
        updated_at      TEXT DEFAULT NOW()
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_user ON enterprise_verifications(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_status ON enterprise_verifications(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_status_created ON enterprise_verifications(status, created_at)')
    conn.commit()
    print(_('[EnterpriseVerifyPlugin] enterprise_verify.db initialized'))
