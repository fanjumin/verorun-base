#!/usr/bin/env python3
"""Plugin shared DB connection utilities.

为各插件提供统一的 psycopg2 连接包装类，替代各插件重复定义的内联包装类。
"""
import psycopg2
import os
from psycopg2.extras import RealDictCursor


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
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self.close()
