"""订单通知独立数据库模型"""
import os
import sqlite3
import threading
from flask import g

DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_FILE = os.path.join(DB_DIR, 'order_notify.db')
_local = threading.local()


def _ensure_dir():
    os.makedirs(DB_DIR, exist_ok=True)


def get_db():
    """获取本插件的独立数据库连接"""
    _ensure_dir()
    if 'order_notify_db' not in g:
        g.order_notify_db = sqlite3.connect(DB_FILE)
        g.order_notify_db.row_factory = sqlite3.Row
        g.order_notify_db.execute("PRAGMA journal_mode=WAL")
        g.order_notify_db.execute("PRAGMA foreign_keys=ON")
    return g.order_notify_db


def get_main_db():
    """只读访问主库（用于查询 order_items 等数据）"""
    from models import get_db as main_db
    return main_db()


def init_db():
    """初始化插件自有表"""
    _ensure_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            event       TEXT    NOT NULL,
            order_id    TEXT    NOT NULL,
            title       TEXT    NOT NULL DEFAULT '',
            content     TEXT    NOT NULL DEFAULT '',
            link_url    TEXT    NOT NULL DEFAULT '',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_notification_log_user
            ON notification_log(user_id);
        CREATE INDEX IF NOT EXISTS idx_notification_log_order
            ON notification_log(order_id);
    """)
    conn.commit()
    conn.close()


def close_db(exception=None):
    db = g.pop('order_notify_db', None)
    if db is not None:
        db.close()
