#!/usr/bin/env python3
"""
Verification Plugin Models — 独立 PostgreSQL schema
=====================================================
- 数据库：PostgreSQL schema = verification（独立 schema，与主库 public 并存于同一 PG 实例）
- verification_requests: 实名认证请求记录（从主库 public.verification_requests 迁移）
"""
import traceback

from plugins._base.db import PgConnection
from plugins._base.db import get_raw_connection

# i18n：由插件 on_install/on_enable 注入 self.t（oauth_config 同款模式，标准 §12.1）
_t = lambda text: text


def init_i18n(t_fn):
    global _t
    _t = t_fn


_verification_conn = None


def get_verification_db():
    global _verification_conn
    if _verification_conn is None:
        raw = get_raw_connection()
        raw.autocommit = False
        _verification_conn = PgConnection(raw)
        _verification_conn.execute("CREATE SCHEMA IF NOT EXISTS verification")
        # F-013: 追加 public 回退，使同连接可读主库 public schema（标准 §9.1 推荐写法）
        _verification_conn.execute("SET search_path TO verification, public")
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
    print(_t('db_initialized'))


def migrate_from_main_db():
    """从主库 public.verification_requests 幂等迁移数据。

    F-002: 插件库与主库为同一 PG 实例，直接用 public. 限定读取，
    不再 sys.path 跨模块导入，避免全局路径污染与模块遮蔽。
    F-006: 迁移失败记录堆栈并返回 0，不阻断插件安装（插件主体为管理 UI）。
    主库无该表时静默跳过。返回迁移的记录数。
    """
    conn = get_verification_db()
    try:
        existing = conn.execute('SELECT COUNT(*) FROM verification_requests').fetchone()['count']
    except Exception:
        # 表未创建等非预期情况 — 记录后跳过（init_verification_db 负责建表）
        traceback.print_exc()
        return 0
    if existing > 0:
        print(_t('migration_skipped'))
        return 0

    try:
        has_table = conn.execute(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public' AND tablename='verification_requests'"
        ).fetchone()
        if not has_table:
            print(_t('migration_no_source'))
            return 0

        rows = conn.execute(
            'SELECT user_id, request_id, provider, return_url, status, created_at, completed_at '
            'FROM public.verification_requests ORDER BY id'
        ).fetchall()
        count = 0
        for r in rows:
            conn.execute(
                'INSERT INTO verification_requests (user_id, request_id, provider, return_url, status, created_at, completed_at) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (request_id) DO NOTHING',
                (r['user_id'], r['request_id'], r['provider'], r['return_url'], r['status'], r['created_at'], r['completed_at'])
            )
            count += 1
        conn.commit()
        print(_t('migration_complete').format(count=count))
        return count
    except Exception as e:
        # F-006: 不静默吞错 — 打印堆栈供排查，返回 0
        traceback.print_exc()
        print(f'[VerificationPlugin] Failed to migrate verification_requests: {e}')
        return 0


ensure_verification_tables = init_verification_db
