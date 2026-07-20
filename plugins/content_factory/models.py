#!/usr/bin/env python3
"""Content Factory Plugin — PostgreSQL schema: content_factory"""
from i18n import _
import psycopg2
import psycopg2.extras
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'content_factory.db')  # 保留用于迁移

_cf_conn = None


class _PgConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface."""
    def __init__(self, conn):
        self._conn = conn
    def execute(self, sql, params=None):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if params is not None:
            cur.execute(sql.replace('?', '%s'), params)
        else:
            cur.execute(sql)
        return cur
    def executescript(self, sql):
        for stmt in sql.split(';'):
            s = stmt.strip()
            if s:
                self.execute(s)
    def commit(self):
        self._conn.commit()
    def close(self):
        self._conn.close()


def get_cf_db():
    """获取内容工厂插件数据库连接（PG schema: content_factory）"""
    global _cf_conn
    if _cf_conn is None:
        raw = psycopg2.connect(
            host=os.environ.get('PG_HOST', 'localhost'),
            port=int(os.environ.get('PG_PORT', 5432)),
            dbname=os.environ.get('PG_DB', 'verorun'),
            user=os.environ.get('PG_USER', 'verorun'),
            password=os.environ.get('PG_PASSWORD', ''),
        )
        raw.autocommit = False
        raw.cursor().execute("CREATE SCHEMA IF NOT EXISTS content_factory")
        raw.commit()
        raw.cursor().execute("SET search_path TO content_factory")
        raw.commit()
        _cf_conn = _PgConnection(raw)
    return _cf_conn


def init_cf_db():
    """初始化内容工厂所有表"""
    conn = get_cf_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS content_sources (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name            TEXT NOT NULL,
            source_type     TEXT NOT NULL DEFAULT 'rss',
            platform        TEXT DEFAULT '',
            url             TEXT DEFAULT '',
            config_json     TEXT DEFAULT '{}',
            crawl_interval  BIGINT DEFAULT 0,
            keywords        TEXT DEFAULT '',
            max_per_run     BIGINT DEFAULT 10,
            is_active       BIGINT DEFAULT 1,
            sort_order      BIGINT DEFAULT 0,
            ai_prompt_template TEXT DEFAULT '',
            skip_review     BIGINT DEFAULT 0,
            auto_publish    BIGINT DEFAULT 0,
            last_crawled_at TIMESTAMPTZ,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            created_by      BIGINT
        );
        CREATE TABLE IF NOT EXISTS raw_contents (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            source_id       BIGINT,
            task_id         BIGINT,
            title           TEXT DEFAULT '',
            author          TEXT DEFAULT '',
            source_url      TEXT DEFAULT '',
            content_text    TEXT DEFAULT '',
            content_html    TEXT DEFAULT '',
            content_json    TEXT DEFAULT '{}',
            summary         TEXT DEFAULT '',
            content_hash    TEXT UNIQUE,
            publish_time    TIMESTAMPTZ,
            language        TEXT DEFAULT 'zh',
            tags            TEXT DEFAULT '',
            status          TEXT DEFAULT 'pending',
            error_msg       TEXT DEFAULT '',
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS processed_contents (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            raw_id          BIGINT,
            content_type    TEXT DEFAULT 'article',
            title           TEXT DEFAULT '',
            summary         TEXT DEFAULT '',
            body            TEXT DEFAULT '',
            body_html       TEXT DEFAULT '',
            keywords        TEXT DEFAULT '',
            risk_level      TEXT DEFAULT 'normal',
            image_url       TEXT DEFAULT '',
            agent_chain     TEXT DEFAULT '[]',
            is_published    BIGINT DEFAULT 0,
            status          TEXT DEFAULT 'draft',
            reviewed_by     BIGINT,
            reviewed_at     TIMESTAMPTZ,
            created_by      BIGINT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS content_tasks (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            source_id       BIGINT,
            task_type       TEXT NOT NULL,
            trigger_type    TEXT DEFAULT 'manual',
            status          TEXT DEFAULT 'pending',
            total_items     BIGINT DEFAULT 0,
            done_items      BIGINT DEFAULT 0,
            error_count     BIGINT DEFAULT 0,
            log_text        TEXT DEFAULT '',
            started_at      TIMESTAMPTZ,
            finished_at     TIMESTAMPTZ,
            created_by      BIGINT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS skill_pushes (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            processed_id    BIGINT,
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            skill_name      TEXT NOT NULL,
            skill_category  TEXT DEFAULT 'content',
            skill_content   TEXT NOT NULL,
            skill_version   TEXT DEFAULT '1.0',
            status          TEXT DEFAULT 'pushed',
            target_agent    TEXT DEFAULT 'hermes',
            push_count      BIGINT DEFAULT 0,
            last_pushed_at  TIMESTAMPTZ,
            created_by      BIGINT,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    print(_('[ContentFactoryPlugin] PG schema content_factory initialized (5 tables)'))