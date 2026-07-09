#!/usr/bin/env python3
"""Ad Management Plugin — 数据库模型"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'ads.db')

_ads_conn = None


def get_ads_db():
    """获取广告插件独立数据库连接"""
    global _ads_conn
    if _ads_conn is None:
        _ads_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _ads_conn.row_factory = sqlite3.Row
        _ads_conn.execute("PRAGMA journal_mode=WAL")
        _ads_conn.execute("PRAGMA busy_timeout=1000")
        _ads_conn.execute("PRAGMA foreign_keys=ON")
    return _ads_conn


def init_ad_db():
    """初始化广告表"""
    conn = get_ads_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_placements (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        position        TEXT NOT NULL DEFAULT 'sidebar',
        page            TEXT NOT NULL DEFAULT '*',
        ad_type         TEXT NOT NULL DEFAULT 'image',
        image_url       TEXT DEFAULT '',
        link_url        TEXT DEFAULT '',
        ad_code         TEXT DEFAULT '',
        width           INTEGER DEFAULT 320,
        height          INTEGER DEFAULT 0,
        is_active       INTEGER DEFAULT 1,
        sort_order      INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_page ON ad_placements(page, position)')
    conn.commit()
    print('[AdsPlugin] ads.db 已初始化')