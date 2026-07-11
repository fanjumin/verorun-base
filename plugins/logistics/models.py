#!/usr/bin/env python3
"""
Logistics Plugin Models — 独立数据库 logistics.db
==================================================
完全独立于主库。
- logistics_queries: 物流查询日志
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'logistics.db')

_logistics_conn = None


def get_logistics_db():
    """获取物流插件独立数据库连接（单例）"""
    global _logistics_conn
    if _logistics_conn is None:
        _logistics_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _logistics_conn.row_factory = sqlite3.Row
        _logistics_conn.execute("PRAGMA journal_mode=WAL")
        _logistics_conn.execute("PRAGMA busy_timeout=1000")
        _logistics_conn.execute("PRAGMA foreign_keys=ON")
    return _logistics_conn


def init_logistics_db():
    """初始化物流插件数据库表（幂等）"""
    conn = get_logistics_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS logistics_queries (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        shipper_code    TEXT NOT NULL,
        logistic_code   TEXT NOT NULL,
        order_code      TEXT DEFAULT '',
        success         INTEGER DEFAULT 0,
        error_msg       TEXT DEFAULT '',
        queried_at      TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_logistics_queries_code ON logistics_queries(logistic_code)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_logistics_queries_at ON logistics_queries(queried_at)')
    conn.commit()
    print('[LogisticsPlugin] logistics.db 已初始化')


# 兼容旧接口名
ensure_logistics_tables = init_logistics_db
