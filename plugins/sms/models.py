#!/usr/bin/env python3
"""
SMS Plugin Models — 独立数据库 sms.db
=====================================
完全独立于主库，不依赖主系统 models。
- sms_templates: 短信模板（从主库迁移）
- sms_logs: 短信发送日志
"""
import psycopg2
import os
from plugins._base.db import PgConnection


_sms_conn = None


def get_sms_db():
    """获取短信插件独立数据库连接（单例）"""
    global _sms_conn
    if _sms_conn is None:
        raw = psycopg2.connect(
            host=os.environ.get('PG_HOST', 'localhost'),
            port=int(os.environ.get('PG_PORT', 5432)),
            dbname=os.environ.get('PG_DB', 'verorun'),
            user=os.environ.get('PG_USER', 'verorun'),
            password=os.environ.get('PG_PASSWORD', ''),
        )
        raw.autocommit = False
        _sms_conn = PgConnection(raw)
        _sms_conn.execute("CREATE SCHEMA IF NOT EXISTS sms")
        _sms_conn.execute("SET search_path TO sms")
        _sms_conn.commit()
    return _sms_conn


def init_sms_db():
    """初始化短信插件数据库表（幂等）"""
    conn = get_sms_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS sms_templates (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        category        TEXT NOT NULL,
        name            TEXT NOT NULL,
        template_code   TEXT NOT NULL,
        note            TEXT DEFAULT '',
        sort_order      BIGINT DEFAULT 0,
        created_at      TEXT DEFAULT (NOW()),
        updated_at      TEXT DEFAULT (NOW()),
        UNIQUE(category, name)
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS sms_logs (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        phone           TEXT NOT NULL,
        code            TEXT DEFAULT '',
        purpose         TEXT DEFAULT '',
        provider        TEXT DEFAULT '',
        status          TEXT DEFAULT 'sent',
        error           TEXT DEFAULT '',
        created_at      TEXT DEFAULT (NOW())
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sms_logs_phone ON sms_logs(phone)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sms_logs_created ON sms_logs(created_at)')
    conn.commit()
    print(_('[SmsPlugin] sms.db has been initialized'))


def migrate_from_main_db():
    """从主库幂等迁移 sms_templates 数据"""
    import sys
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)

    conn = get_sms_db()
    existing = conn.execute('SELECT COUNT(*) FROM sms_templates').fetchone()['count']
    if existing > 0:
        print(_('[SmsPlugin] sms_templates already has data, migration skipped'))
        return

    try:
        from models import get_db
        with get_db() as main_conn:
            rows = main_conn.execute(
                'SELECT category, name, template_code, note, sort_order FROM sms_templates ORDER BY sort_order'
            ).fetchall()
        count = 0
        for r in rows:
            conn.execute(
                'INSERT INTO sms_templates (category, name, template_code, note, sort_order) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (category, name) DO NOTHING',
                (r['category'], r['name'], r['template_code'], r['note'], r['sort_order'])
            )
            count += 1
        conn.commit()
        print(f'[SmsPlugin] Migrated {count} sms_templates records from main database')
    except Exception as e:
        print(f'[SmsPlugin] Failed to migrate sms_templates (main database may not have this table): {e}')


# 兼容旧接口名
ensure_sms_tables = init_sms_db
