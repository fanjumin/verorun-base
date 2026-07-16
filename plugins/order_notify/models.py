"""订单通知独立数据库模型"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
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
        g.order_notify_db = psycopg2.connect(
            host=os.environ.get('PG_HOST','localhost'),
            port=int(os.environ.get('PG_PORT',5432)),
            dbname=os.environ.get('PG_DB','verorun'),
            user=os.environ.get('PG_USER','verorun'),
            password=os.environ.get('PG_PASSWORD',''),
            cursor_factory=RealDictCursor
        )
        g.order_notify_db.execute("CREATE SCHEMA IF NOT EXISTS order_notify")
        g.order_notify_db.execute("SET search_path TO order_notify")
    return g.order_notify_db


def get_main_db():
    """只读访问主库（用于查询 order_items 等数据）"""
    from models import get_db as main_db
    return main_db()


def init_db():
    """初始化插件自有表"""
    _ensure_dir()
    conn = psycopg2.connect(
        host=os.environ.get('PG_HOST','localhost'),
        port=int(os.environ.get('PG_PORT',5432)),
        dbname=os.environ.get('PG_DB','verorun'),
        user=os.environ.get('PG_USER','verorun'),
        password=os.environ.get('PG_PASSWORD',''),
        cursor_factory=RealDictCursor
    )
    conn.execute("CREATE SCHEMA IF NOT EXISTS order_notify")
    conn.execute("SET search_path TO order_notify")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notification_log (
            id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id     BIGINT NOT NULL,
            event       TEXT    NOT NULL,
            order_id    TEXT    NOT NULL,
            title       TEXT    NOT NULL DEFAULT '',
            content     TEXT    NOT NULL DEFAULT '',
            link_url    TEXT    NOT NULL DEFAULT '',
            created_at  TEXT    NOT NULL DEFAULT NOW()
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_notification_log_user
            ON notification_log(user_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_notification_log_order
            ON notification_log(order_id)
    """)
    conn.commit()
    conn.close()


def close_db(exception=None):
    db = g.pop('order_notify_db', None)
    if db is not None:
        db.close()
