#!/usr/bin/env python3
"""
Vault Utilities — Shared helpers for backup/restore services.

Provides common functions to eliminate code duplication across modules.
"""

import os
from typing import Dict

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
BACKUP_DIR = os.path.join(BASE_DIR, 'data', 'vault')

_SCHEMA_ENSURED = False


def get_vault_conn():
    """Return a raw psycopg2 connection pinned to the vault schema.

    Follows plugin-standard v1.3 §9.1 (single DB, per-plugin schema):
    plugin tables live in the `vault` schema; unqualified system tables
    (public) still resolve through the trailing 'public'.
    """
    from plugins._base.db import get_raw_connection
    conn = get_raw_connection()
    cur = conn.cursor()
    cur.execute('SET search_path TO vault, public')
    cur.close()
    return conn


def ensure_schema():
    """Idempotently apply vault migrations so all vault_* tables exist.

    Safe to call on every request: the migration SQL only uses
    CREATE SCHEMA / CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS,
    and a module flag short-circuits after the first successful run per process.
    """
    global _SCHEMA_ENSURED
    if _SCHEMA_ENSURED:
        return True
    try:
        migration_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'migrations', '001_initial.sql')
        if not os.path.exists(migration_path):
            print('[Vault] ensure_schema: migration file missing: %s' % migration_path)
            return False
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        conn = get_vault_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        print('[Vault] Database schema ensured (migrations/001_initial.sql)')
        _SCHEMA_ENSURED = True
        return True
    except Exception as e:
        print('[Vault] ensure_schema failed: %s' % e)
        return False


def get_pg_env() -> Dict[str, str]:
    """Read .env for PostgreSQL connection info."""
    env = {}
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env
