#!/usr/bin/env python3
"""Plugin shared DB connection utilities.

为各插件提供统一的 psycopg2 连接包装类，替代各插件重复定义的内联包装类。
"""
import psycopg2
import psycopg2.pool
import os
import threading
from psycopg2.extras import RealDictCursor

# P2-2: 连接池（避免高并发时耗尽连接数）
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    """获取或创建连接池（线程安全、懒加载）"""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                minconn = int(os.environ.get('PG_POOL_MIN', '2'))
                maxconn = int(os.environ.get('PG_POOL_MAX', '20'))
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=minconn,
                    maxconn=maxconn,
                    host=os.environ.get('PG_HOST', ''),
                    port=int(os.environ.get('PG_PORT', 5432)),
                    dbname=os.environ.get('PG_DB', 'verorun'),
                    user=os.environ.get('PG_USER', 'easykai'),
                    password=os.environ.get('PG_PASSWORD', ''),
                )
    return _pool


class PgConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface.

    提供 `.execute()` / `.commit()` / `.rollback()` / `.close()` 方法和
    context manager 支持，兼容从 SQLite 迁移到 PG 的插件代码。
    """
    def __init__(self, conn):
        self._conn = conn
        self._cur = None

    def cursor(self):
        return self._conn.cursor()

    def execute(self, sql, params=None):
        if self._cur is None:
            self._cur = self._conn.cursor(cursor_factory=RealDictCursor)
        self._cur.execute(sql.replace('?', '%s'), params or ())
        return self._cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._cur:
            self._cur.close()
        # 归还连接到连接池（而非关闭连接）
        _get_pool().putconn(self._conn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self.close()


def get_raw_connection():
    """从连接池获取一个 psycopg2 连接。

    所有插件和模块应使用此工厂函数获取连接，而不是
    内联 psycopg2.connect() 调用。
    """
    return _get_pool().getconn()
