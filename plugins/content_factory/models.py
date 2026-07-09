#!/usr/bin/env python3
"""Content Factory Plugin — 数据库模型"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'content_factory.db')

_cf_conn = None


def get_cf_db():
    """获取内容工厂插件独立数据库连接"""
    global _cf_conn
    if _cf_conn is None:
        _cf_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _cf_conn.row_factory = sqlite3.Row
        _cf_conn.execute("PRAGMA journal_mode=WAL")
        _cf_conn.execute("PRAGMA busy_timeout=1000")
        _cf_conn.execute("PRAGMA foreign_keys=ON")
    return _cf_conn


def init_cf_db():
    """初始化内容工厂所有表"""
    conn = get_cf_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS content_sources (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            source_type     TEXT NOT NULL DEFAULT 'rss',
            platform        TEXT DEFAULT '',
            url             TEXT DEFAULT '',
            config_json     TEXT DEFAULT '{}',
            crawl_interval  INTEGER DEFAULT 0,
            keywords        TEXT DEFAULT '',
            max_per_run     INTEGER DEFAULT 10,
            is_active       INTEGER DEFAULT 1,
            sort_order      INTEGER DEFAULT 0,
            ai_prompt_template TEXT DEFAULT '',
            skip_review     INTEGER DEFAULT 0,
            auto_publish    INTEGER DEFAULT 0,
            last_crawled_at TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            created_by      INTEGER
        );
        CREATE TABLE IF NOT EXISTS raw_contents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id       INTEGER,
            task_id         INTEGER,
            title           TEXT DEFAULT '',
            author          TEXT DEFAULT '',
            source_url      TEXT DEFAULT '',
            content_text    TEXT DEFAULT '',
            content_html    TEXT DEFAULT '',
            content_json    TEXT DEFAULT '{}',
            summary         TEXT DEFAULT '',
            content_hash    TEXT UNIQUE,
            publish_time    TEXT,
            language        TEXT DEFAULT 'zh',
            tags            TEXT DEFAULT '',
            status          TEXT DEFAULT 'pending',
            error_msg       TEXT DEFAULT '',
            created_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS processed_contents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_id          INTEGER,
            content_type    TEXT DEFAULT 'article',
            title           TEXT DEFAULT '',
            summary         TEXT DEFAULT '',
            body            TEXT DEFAULT '',
            body_html       TEXT DEFAULT '',
            keywords        TEXT DEFAULT '',
            risk_level      TEXT DEFAULT 'normal',
            image_url       TEXT DEFAULT '',
            agent_chain     TEXT DEFAULT '[]',
            is_published    INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'draft',
            reviewed_by     INTEGER,
            reviewed_at     TEXT,
            created_by      INTEGER,
            created_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS content_tasks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id       INTEGER,
            task_type       TEXT NOT NULL,
            trigger_type    TEXT DEFAULT 'manual',
            status          TEXT DEFAULT 'pending',
            total_items     INTEGER DEFAULT 0,
            done_items      INTEGER DEFAULT 0,
            error_count     INTEGER DEFAULT 0,
            log_text        TEXT DEFAULT '',
            started_at      TEXT,
            finished_at     TEXT,
            created_by      INTEGER,
            created_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS skill_pushes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            processed_id    INTEGER,
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            skill_name      TEXT NOT NULL,
            skill_category  TEXT DEFAULT 'content',
            skill_content   TEXT NOT NULL,
            skill_version   TEXT DEFAULT '1.0',
            status          TEXT DEFAULT 'pushed',
            target_agent    TEXT DEFAULT 'hermes',
            push_count      INTEGER DEFAULT 0,
            last_pushed_at  TEXT,
            created_by      INTEGER,
            created_at      TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    print('[ContentFactoryPlugin] content_factory.db 已初始化 (5 tables)')