#!/usr/bin/env python3
"""site_builder — idempotent schema migration runner.

v2.1.0 起插件数据物理迁移到独立数据库 `site_builder`：连接切换到
独立库，run_migrations 仅确保 schema 存在；若独立库 public schema 中残留
未迁移表（迁移中断场景），仍会将其移动到 site_builder schema。

Migration SQL 归档于 migrations/v2.1.0.sql / v2.1.0_rollback.sql 与
v2.1.0_migrate_to_independent.sql（主库→独立库数据迁移指引）。
"""

import logging

from .db import get_raw_connection

logger = logging.getLogger(__name__)

_TABLES = ('site_builder_prompts', 'site_builder_tasks', 'design_tokens', 'site_versions')


def run_migrations():
    """Ensure the dedicated schema exists (idempotent, independent DB).

    独立库中不存在主库的 public 旧表；此处额外处理「迁移中断」场景——
    若独立库 public schema 中仍有这些表，则移动到 site_builder。
    """
    conn = get_raw_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS site_builder")
            for table in _TABLES:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name=%s",
                    (table,)
                )
                if cur.fetchone():
                    cur.execute(f"ALTER TABLE public.{table} SET SCHEMA site_builder")
                    logger.info('[SiteBuilder] moved %s -> site_builder schema', table)
    finally:
        conn.close()
