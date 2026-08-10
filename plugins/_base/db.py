#!/usr/bin/env python3
"""Plugin shared DB connection utilities.

为各插件提供统一的 psycopg2 连接包装类，替代各插件重复定义的内联包装类。
"""
import psycopg2
import os
import re
from psycopg2.extras import RealDictCursor


# 匹配单引号字符串字面量（含 '' 转义）或单个 ? 占位符。
# 仅替换字面量之外的 ?，避免 SQL 字符串内的 ?（如 LIKE 模式）被误替换。
_PLACEHOLDER_RE = re.compile(r"'(''|[^'])*'|\?")


def _replace_placeholders(sql: str) -> str:
    """将 SQL 中的 ? 占位符替换为 %s，跳过单引号字符串字面量内的 ?。"""
    def _repl(m):
        return '%s' if m.group(0) == '?' else m.group(0)
    return _PLACEHOLDER_RE.sub(_repl, sql)


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
        self._cur.execute(_replace_placeholders(sql), params or ())
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


def get_raw_connection():
    """Return a raw psycopg2 connection using env-configured PG credentials.

    All plugins and modules should use this single factory instead of
    inlining psycopg2.connect() calls with repeated env var lookups.
    """
    return psycopg2.connect(
        host=os.environ.get('PG_HOST', ''),
        port=int(os.environ.get('PG_PORT', 5432)),
        dbname=os.environ.get('PG_DB', 'appdb'),
        user=os.environ.get('PG_USER', 'app'),
        password=os.environ.get('PG_PASSWORD', ''),
        connect_timeout=10,  # 建连最多等 10 秒，避免低配机器上无限挂死
    )
