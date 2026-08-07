#!/usr/bin/env python3
"""mini_app_builder — idempotent schema migration runner.

v2.0.0 moves the legacy tables (dev_accounts, schema_meta, mini_app_projects,
mini_app_versions) from the `public` schema into the dedicated
`mini_app_builder` schema using `ALTER TABLE ... SET SCHEMA`, which preserves
all data, indexes and sequences.  Backward-compatible public views are created
so any external SQL readers keep working.

Migration SQL is also archived under migrations/v2.0.0.sql / v2.0.0_rollback.sql
for standalone execution / rollback.
"""

import logging

from plugins._base.db import get_raw_connection

logger = logging.getLogger(__name__)

_TABLES = ('dev_accounts', 'schema_meta', 'mini_app_projects', 'mini_app_versions')


def run_migrations():
    """Create the schema and move legacy public tables into it (idempotent)."""
    conn = get_raw_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS mini_app_builder")
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
