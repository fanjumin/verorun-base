"""订单通知独立数据库模型"""
from flask import g


class _PgConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface."""
    def __init__(self, conn):
        self._conn = conn
    def execute(self, sql, params=None):
        import psycopg2.extras
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if params is not None:
            cur.execute(sql.replace('?', '%s'), params)
        else:
            cur.execute(sql)
        return cur
    def commit(self):
        self._conn.commit()
    def close(self):
        self._conn.close()


def get_db():
    """获取本插件的独立数据库连接"""
    if 'order_notify_db' not in g:
        from plugins._base.db import get_raw_connection
        g.order_notify_db = get_raw_connection()
        g.order_notify_db.execute("CREATE SCHEMA IF NOT EXISTS order_notify")
        g.order_notify_db.execute("SET search_path TO order_notify")
    return _PgConnection(g.order_notify_db)


def get_main_db():
    """只读访问主库（用于查询 order_items 等数据）"""
    from models import get_db as main_db
    return main_db()


def init_db():
    """初始化插件自有表"""
    from plugins._base.db import get_raw_connection
    conn = get_raw_connection()
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
