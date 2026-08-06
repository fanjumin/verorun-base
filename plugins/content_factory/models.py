#!/usr/bin/env python3
"""Content Factory Plugin — PostgreSQL schema: content_factory"""
from i18n import _
import psycopg2
import psycopg2.extras
import os
import re
from plugins._base.db import get_raw_connection
from plugin_manager.logger import get_plugin_logger

logger = get_plugin_logger('content_factory')

DB_PATH = os.path.join(os.path.dirname(__file__), 'content_factory.db')  # 保留用于迁移

_cf_conn = None


# `?` → `%s` 转换：跳过单引号字符串字面量内的 `?`
_SQL_Q = re.compile(r"'(?:[^']|'')*'|\?")


def _to_psql_placeholders(sql: str) -> str:
    """sqlite `?` → psycopg2 `%s`，字符串字面量内的 `?` 不被替换。"""
    return _SQL_Q.sub(lambda m: m.group(0) if m.group(0).startswith("'") else '%s', sql)


def _split_sql_statements(sql: str) -> list:
    """按 `;` 分割 SQL，忽略字符串字面量内的 `;`。"""
    parts = []
    buf = []
    in_str = False
    for ch in sql:
        if ch == "'":
            in_str = not in_str
        if ch == ';' and not in_str:
            stmt = ''.join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
        else:
            buf.append(ch)
    stmt = ''.join(buf).strip()
    if stmt:
        parts.append(stmt)
    return parts


class _PgConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface."""
    def __init__(self, conn):
        self._conn = conn
    def execute(self, sql, params=None):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if params is not None:
            cur.execute(_to_psql_placeholders(sql), params)
        else:
            cur.execute(sql)
        return cur
    def executescript(self, sql):
        for stmt in _split_sql_statements(sql):
            self.execute(stmt)
    def commit(self):
        self._conn.commit()
    def close(self):
        self._conn.close()


def get_cf_db():
    """获取内容工厂插件数据库连接（PG schema: content_factory）"""
    global _cf_conn
    if _cf_conn is None:
        raw = get_raw_connection()
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
        CREATE TABLE IF NOT EXISTS agent_registry (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name            TEXT NOT NULL,
            identifier      TEXT DEFAULT '',
            role_type       TEXT DEFAULT 'sub',
            description     TEXT DEFAULT '',
            domain          TEXT DEFAULT 'content',
            provider        TEXT DEFAULT '',
            model_name      TEXT DEFAULT '',
            system_prompt   TEXT DEFAULT '',
            capabilities    TEXT DEFAULT '[]',
            is_active       BIGINT DEFAULT 1,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            updated_at      TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_cf_agent_registry_identifier ON agent_registry(identifier);
        CREATE TABLE IF NOT EXISTS schema_meta (
            key         TEXT PRIMARY KEY,
            value       TEXT DEFAULT '',
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    logger.info(_('[ContentFactoryPlugin] PG schema content_factory initialized (7 tables)'))


def upsert_agent(name: str, identifier: str, role_type: str, description: str, domain: str,
                 provider: str, model_name: str, system_prompt: str,
                 capabilities: str, is_active: int = 1):
    """注册或更新本地 Agent（幂等，§4.1）。写入插件自有 schema 的 agent_registry 表。"""
    conn = get_cf_db()
    exists = conn.execute('SELECT id FROM agent_registry WHERE identifier=?', (identifier,)).fetchone()
    if exists:
        conn.execute('''
            UPDATE agent_registry
            SET name=?, role_type=?, description=?, domain=?, provider=?, model_name=?,
                system_prompt=?, capabilities=?, is_active=?, updated_at=NOW()
            WHERE id=?
        ''', (name, role_type, description, domain, provider, model_name,
              system_prompt, capabilities, is_active, exists['id']))
    else:
        conn.execute('''
            INSERT INTO agent_registry
            (name, identifier, role_type, description, domain, provider, model_name,
             system_prompt, capabilities, is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', (name, identifier, role_type, description, domain, provider, model_name,
              system_prompt, capabilities, is_active))
    conn.commit()


def unregister_agents():
    """注销插件注册的所有 Agent（§4.2 禁用/卸载流程）"""
    conn = get_cf_db()
    conn.execute('DELETE FROM agent_registry')
    conn.commit()


def get_schema_version() -> str:
    """从 schema_meta 表读取当前 schema 版本（§10.6）"""
    try:
        conn = get_cf_db()
        row = conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
        return row['value'] if row else '0.0.0'
    except Exception:
        return '0.0.0'


def set_schema_version(version: str):
    """写入当前 schema 版本（§10.6）"""
    conn = get_cf_db()
    conn.execute('''
        INSERT INTO schema_meta (key, value, updated_at)
        VALUES ('schema_version', ?, NOW())
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()
    ''', (version,))
    conn.commit()