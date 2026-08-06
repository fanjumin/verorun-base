#!/usr/bin/env python3
"""Social Push Plugin — 数据库模型

独立数据库 social_push.db，存放社媒发布日志表 social_push_logs。
从主库迁移而来，表结构保持一致。
"""
import threading
from plugins._base.db import PgConnection
from plugins._base.db import get_raw_connection

# 每线程独立连接，避免多线程共享全局 cursor 造成数据竞争
_local = threading.local()


def get_sp_db():
    """获取 Social Push 插件独立数据库连接（线程局部，非全局共享）"""
    conn = getattr(_local, 'conn', None)
    if conn is None:
        raw = get_raw_connection()
        raw.autocommit = False
        conn = PgConnection(raw)
        conn.execute("CREATE SCHEMA IF NOT EXISTS social_push")
        conn.execute("SET search_path TO social_push")
        conn.commit()
        _local.conn = conn
    return _local.conn


def init_sp_db():
    """初始化社媒发布日志表（幂等）。

    表结构与主库 social_push_logs 保持一致，便于数据迁移。
    admin_id 原主库为 REFERENCES users(id) 外键；插件独立库不跨库外键，
    仅保留列（值仍是主库 users.id），符合_("Independent Database + Primary Database Read-Only")契约。
    """
    conn = get_sp_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS social_push_logs (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            platform        TEXT NOT NULL DEFAULT 'wechat',
            content_type    TEXT DEFAULT 'article',
            title           TEXT DEFAULT '',
            summary         TEXT DEFAULT '',
            article_json    TEXT DEFAULT '',
            media_id        TEXT DEFAULT '',
            publish_id      TEXT DEFAULT '',
            status          TEXT DEFAULT 'draft',
            push_time       TEXT,
            admin_id        BIGINT,
            error_msg       TEXT DEFAULT '',
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    conn.commit()

    # 幂等迁移：历史 TEXT 列一次性转 TIMESTAMPTZ；已是 TIMESTAMPTZ 时为无操作
    try:
        conn.execute(
            "ALTER TABLE social_push_logs ALTER COLUMN created_at TYPE TIMESTAMPTZ "
            "USING created_at::timestamptz"
        )
        conn.commit()
    except Exception:
        conn.rollback()


def migrate_from_main_db():
    """从主库 social_push_logs 迁移历史发布记录到插件库（幂等）。

    仅当插件库为空时导入（避免重复导入 / 覆盖新数据）。
    主库无该表时静默跳过。返回迁移的记录数。
    """
    try:
        from models import get_db as get_main_db
    except Exception:
        return 0

    conn = get_sp_db()
    # 插件库已有数据则跳过，保证幂等且不重复导入
    existing = conn.execute("SELECT COUNT(*) AS c FROM social_push_logs").fetchone()
    if existing and existing['c'] > 0:
        return 0

    try:
        with get_main_db() as main:
            has_table = main.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name='social_push_logs'"
            ).fetchone()
            if not has_table:
                return 0
            rows = main.execute(
                "SELECT platform, content_type, title, summary, article_json, media_id, "
                "publish_id, status, push_time, admin_id, error_msg, created_at "
                "FROM social_push_logs ORDER BY id"
            ).fetchall()
    except Exception:
        return 0

    migrated = 0
    for r in rows:
        conn.execute(
            """INSERT INTO social_push_logs
               (platform, content_type, title, summary, article_json, media_id,
                publish_id, status, push_time, admin_id, error_msg, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (r['platform'], r['content_type'], r['title'], r['summary'],
             r['article_json'], r['media_id'], r['publish_id'], r['status'],
             r['push_time'], r['admin_id'], r['error_msg'], r['created_at'])
        )
        migrated += 1
    conn.commit()
    return migrated
