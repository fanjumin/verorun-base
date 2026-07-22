#!/usr/bin/env python3
"""
Verification Plugin Models — 独立数据库 verification.db
=======================================================
- verification_requests: 实名认证请求记录（从主库迁移）
"""
from i18n import _
import psycopg2
import os
from plugins._base.db import PgConnection
from plugins._base.db import get_raw_connection

_verification_conn = None


def get_verification_db():
    global _verification_conn
    if _verification_conn is None:
        raw = get_raw_connection()
        raw.autocommit = False
        _verification_conn = PgConnection(raw)
        _verification_conn.execute("CREATE SCHEMA IF NOT EXISTS verification")
        _verification_conn.execute("SET search_path TO verification")
        _verification_conn.commit()
    return _verification_conn


def init_verification_db():
    conn = get_verification_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS verification_requests (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id         BIGINT NOT NULL,
        request_id      TEXT UNIQUE NOT NULL,
        provider        TEXT DEFAULT '',
        return_url      TEXT DEFAULT '',
        status          TEXT DEFAULT 'pending',
        created_at      TEXT DEFAULT (NOW()),
        completed_at    TEXT
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ver_requests_user ON verification_requests(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ver_requests_req ON verification_requests(request_id)')
    conn.commit()
    print(_('[VerificationPlugin] verification.db has been initialized'))


def migrate_from_main_db():
    """从主库幂等迁移 verification_requests 数据"""
    import sys
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)

    conn = get_verification_db()
    existing = conn.execute('SELECT COUNT(*) FROM verification_requests').fetchone()['count']
    if existing > 0:
        print(_('[VerificationPlugin] verification_requests already has data, migration skipped'))
        return

    try:
        from models import get_db
        with get_db() as main_conn:
            rows = main_conn.execute(
                'SELECT user_id, request_id, provider, return_url, status, created_at, completed_at FROM verification_requests ORDER BY id'
            ).fetchall()
        count = 0
        for r in rows:
            conn.execute(
                'INSERT INTO verification_requests (user_id, request_id, provider, return_url, status, created_at, completed_at) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (request_id) DO NOTHING',
                (r['user_id'], r['request_id'], r['provider'], r['return_url'], r['status'], r['created_at'], r['completed_at'])
            )
            count += 1
        conn.commit()
        print(f'[VerificationPlugin] Migrated {count} verification_requests records from main database')
    except Exception as e:
        print(f'[VerificationPlugin] Failed to migrate verification_requests: {e}')


ensure_verification_tables = init_verification_db
