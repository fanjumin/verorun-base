#!/usr/bin/env python3
"""mini_app_builder — idempotent schema migration runner.

v2.0.0 把旧表从 public schema 移到 mini_app_builder schema（主库内移动，
保留数据/索引/序列），并创建 public 视图向后兼容。

v2.1.0 起数据物理迁移到独立数据库 `verorun_miniapp`：连接切换到独立库，
run_migrations 仅确保 schema 存在；若独立库 public 中残留未迁移表（迁移
中断场景），仍会将其移动到 mini_app_builder schema。

Migration SQL 归档于 migrations/v2.1.0.sql / v2.1.0_rollback.sql 与
v2.1.0_migrate_to_independent.sql（主库→独立库数据迁移指引）。
"""

import logging

from .db import get_raw_connection

logger = logging.getLogger(__name__)

_TABLES = ('dev_accounts', 'schema_meta', 'mini_app_projects', 'mini_app_versions')


def run_migrations():
    """Ensure the dedicated schemas exist (idempotent, independent DB).

    独立库中不存在主库的 public 旧表；此处额外处理「迁移中断」场景——
    若独立库 public schema 中仍有这些表，则移动到 mini_app_builder。
    """
    conn = get_raw_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS mini_app_builder")
            cur.execute("CREATE SCHEMA IF NOT EXISTS platform_users")
            for table in _TABLES:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name=%s",
                    (table,)
                )
                if cur.fetchone():
                    cur.execute(f"ALTER TABLE public.{table} SET SCHEMA mini_app_builder")
                    logger.info('[MiniAppBuilder] moved %s -> mini_app_builder schema', table)
    finally:
        conn.close()


def ensure_public_views():
    """Create backward-compatible public views for moved tables (idempotent)."""
    conn = get_raw_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for table in _TABLES:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='mini_app_builder' AND table_name=%s",
                    (table,)
                )
                if cur.fetchone():
                    cur.execute(
                        f"CREATE OR REPLACE VIEW public.{table} AS "
                        f"SELECT * FROM mini_app_builder.{table}"
                    )
    finally:
        conn.close()
