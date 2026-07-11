#!/usr/bin/env python3
"""
SMS Plugin Models — 独立数据库 sms.db
=====================================
完全独立于主库，不依赖主系统 models。
- sms_templates: 短信模板（从主库迁移）
- sms_logs: 短信发送日志
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'sms.db')

_sms_conn = None


def get_sms_db():
    """获取短信插件独立数据库连接（单例）"""
    global _sms_conn
    if _sms_conn is None:
        _sms_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _sms_conn.row_factory = sqlite3.Row
        _sms_conn.execute("PRAGMA journal_mode=WAL")
        _sms_conn.execute("PRAGMA busy_timeout=1000")
        _sms_conn.execute("PRAGMA foreign_keys=ON")
    return _sms_conn


def init_sms_db():
    """初始化短信插件数据库表（幂等）"""
    conn = get_sms_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS sms_templates (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        category        TEXT NOT NULL,
        name            TEXT NOT NULL,
        template_code   TEXT NOT NULL,
        note            TEXT DEFAULT '',
        sort_order      INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now')),
        UNIQUE(category, name)
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS sms_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        phone           TEXT NOT NULL,
        code            TEXT DEFAULT '',
        purpose         TEXT DEFAULT '',
        provider        TEXT DEFAULT '',
        status          TEXT DEFAULT 'sent',
        error           TEXT DEFAULT '',
        created_at      TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sms_logs_phone ON sms_logs(phone)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_sms_logs_created ON sms_logs(created_at)')
    conn.commit()
    print('[SmsPlugin] sms.db 已初始化')


def migrate_from_main_db():
    """从主库幂等迁移 sms_templates 数据"""
    import sys
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)

    conn = get_sms_db()
    existing = conn.execute('SELECT COUNT(*) FROM sms_templates').fetchone()[0]
    if existing > 0:
        print('[SmsPlugin] sms_templates 已有数据，跳过迁移')
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
                'INSERT OR IGNORE INTO sms_templates (category, name, template_code, note, sort_order) VALUES (?,?,?,?,?)',
                (r['category'], r['name'], r['template_code'], r['note'], r['sort_order'])
            )
            count += 1
        conn.commit()
        print(f'[SmsPlugin] 从主库迁移 {count} 条 sms_templates 记录')
    except Exception as e:
        print(f'[SmsPlugin] 迁移 sms_templates 失败（主库可能无此表）: {e}')


# 兼容旧接口名
ensure_sms_tables = init_sms_db
