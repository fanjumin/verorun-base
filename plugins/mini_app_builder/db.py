#!/usr/bin/env python3
"""mini_app_builder — independent PostgreSQL connection factory.

v2.1.0 起插件数据从主库 `verorun` 物理迁移到独立库 `mini_app`。
本文件不再依赖 plugins/_base/db.py（主库共享连接），而是使用独立的
`MINI_APP_DB_URL`（优先）或 `MINI_APP_PG_*` 环境变量建立连接。

连接优先级：
    1. MINI_APP_DB_URL        （完整 postgres:// URL）
    2. MINI_APP_PG_HOST/PORT/DB/USER/PASSWORD
       （未设单项时回退到通用 PG_* 环境变量，DB 名固定为 mini_app）
"""

import os
import re

import psycopg2
from psycopg2.extras import RealDictCursor

# 匹配单引号字符串字面量（含 '' 转义）或单个 ? 占位符。
# 仅替换字面量之外的 ?，避免 SQL 字符串内的 ?（如 LIKE 模式）被误替换。
_PLACEHOLDER_RE = re.compile(r"'(''|[^'])*'|\?")


def _replace_placeholders(sql: str) -> str:
    """将 SQL 中的 ? 占位符替换为 %s，跳过单引号字符串字面量内的 ?。"""
    def _repl(m):
        return '%s' if m.group(0) == '?' else m.group(0)
    return _PLACEHOLDER_RE.sub(_repl, sql)


class MiniAppConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface.

    与 plugins/_base/db.PgConnection 行为一致，方便插件代码无感切换数据源。
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
    """返回指向独立数据库的 psycopg2 连接。

    优先使用 MINI_APP_DB_URL；未设置时用 MINI_APP_PG_*（单项回退 PG_*），
    数据库名固定为 mini_app。
    """
    db_url = os.environ.get('MINI_APP_DB_URL', '')
    if db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.environ.get('MINI_APP_PG_HOST', os.environ.get('PG_HOST', '')),
        port=int(os.environ.get('MINI_APP_PG_PORT', os.environ.get('PG_PORT', 5432))),
        dbname=os.environ.get('MINI_APP_PG_DB', 'mini_app'),
        user=os.environ.get('MINI_APP_PG_USER', os.environ.get('PG_USER', 'verorun')),
        password=os.environ.get('MINI_APP_PG_PASSWORD', os.environ.get('PG_PASSWORD', '')),
        connect_timeout=10,  # 建连最多等 10 秒，避免低配机器上无限挂死
    )


def get_db():
    """返回独立库连接（search_path: mini_app_builder, platform_users, public）。"""
    conn = get_raw_connection()
    conn.autocommit = False
    try:
        wrapped = MiniAppConnection(conn)
        wrapped.execute("SET search_path TO mini_app_builder, platform_users, public")
        return wrapped
    except Exception:
        conn.close()
        raise
