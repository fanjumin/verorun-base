#!/usr/bin/env python3
"""Mini App Builder — data models & CRUD for mini-app projects / versions.

v2.1.0 起数据物理迁移至独立数据库 `verorun_miniapp`（不再使用主库），
表位于 mini_app_builder schema，连接走本插件独立的 db.py（MINI_APP_DB_URL
或 MINI_APP_PG_* 环境变量）。
"""

import os
import json
from contextlib import contextmanager

from .db import MiniAppConnection as PgConnection, get_raw_connection

# ── Table Name Constants ──
TABLE_MINIAPP_PROJECTS = 'mini_app_projects'
TABLE_MINIAPP_VERSIONS = 'mini_app_versions'


@contextmanager
def get_db():
    """PostgreSQL connection to the independent DB (mini_app_builder first)."""
    conn = get_raw_connection()
    conn.autocommit = False
    try:
        wrapped = PgConnection(conn)
        wrapped.execute("SET search_path TO mini_app_builder, platform_users, public")
        yield wrapped
    finally:
        conn.close()


def _migrate_mini_app_versions_ai_columns(conn):
    """Add AI-generation columns to existing mini_app_versions tables (safe re-run)."""
    migrations = [
        ("prompt",          "TEXT DEFAULT ''"),
        ("prompt_template", "TEXT DEFAULT ''"),
        ("ai_plan_json",    "TEXT DEFAULT '{}'"),
        ("widgets_json",    "TEXT DEFAULT '[]'"),
    ]
    for col_name, col_def in migrations:
        try:
            conn.execute(f"ALTER TABLE {TABLE_MINIAPP_VERSIONS} ADD COLUMN IF NOT EXISTS {col_name} {col_def}")
        except Exception:
            # SQLite fallback (no IF NOT EXISTS support)
            try:
                conn.execute(f"ALTER TABLE {TABLE_MINIAPP_VERSIONS} ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass  # column already exists


def init_tables():
    """Create mini-app tables (idempotent)."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mini_app_projects (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name            TEXT NOT NULL,
                slug            TEXT UNIQUE NOT NULL,
                description     TEXT DEFAULT '',
                created_by      BIGINT DEFAULT 0,
                created_at      TEXT DEFAULT (NOW()),
                updated_at      TEXT DEFAULT (NOW())
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mini_app_versions (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                project_id      BIGINT NOT NULL,
                version_no      BIGINT NOT NULL,
                platforms_json  TEXT DEFAULT '[]',
                options_json    TEXT DEFAULT '{}',
                result_json     TEXT DEFAULT '{}',
                output_path     TEXT DEFAULT '',
                status          TEXT DEFAULT 'completed',
                prompt          TEXT DEFAULT '',
                prompt_template TEXT DEFAULT '',
                ai_plan_json    TEXT DEFAULT '{}',
                widgets_json    TEXT DEFAULT '[]',
                created_at      TEXT DEFAULT (NOW())
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_map_slug ON mini_app_projects(slug)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mav_project ON mini_app_versions(project_id)")

        # v2.1.0：小程序聊天会话独立存储（替代主库 chatbot_sessions）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mini_app_sessions (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                session_id  TEXT NOT NULL,
                user_id     BIGINT DEFAULT 0,
                platform    TEXT DEFAULT '',
                query_text  TEXT DEFAULT '',
                reply_text  TEXT DEFAULT '',
                intent      TEXT DEFAULT '',
                sentiment   TEXT DEFAULT '',
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_sessions_user ON mini_app_sessions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_miniapp_sessions_session ON mini_app_sessions(session_id)")

        # Migration: add new AI-prompt columns to existing mini_app_versions tables
        _migrate_mini_app_versions_ai_columns(conn)
        conn.commit()


# ══════════════════════════════════════════════════════════════
# Mini-App Projects & Versions
# ══════════════════════════════════════════════════════════════

def _slugify(name: str) -> str:
    """Convert a project name to a filesystem-safe slug."""
    import re
    slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '-', (name or '').strip().lower())
    slug = slug.strip('-')
    return slug or f'project-{_short_id()}'


def _short_id():
    import secrets
    return secrets.token_hex(4)


def create_project(name: str, description: str = '', created_by: int = 0) -> dict:
    """Create a mini-app project. Slug is unique; auto-suffix on collision."""
    base_slug = _slugify(name)
    with get_db() as conn:
        slug = base_slug
        n = 1
        while conn.execute(
            f"SELECT id FROM {TABLE_MINIAPP_PROJECTS} WHERE slug=%s", (slug,)
        ).fetchone():
            n += 1
            slug = f'{base_slug}-{n}'
        cur = conn.execute(
            f"""INSERT INTO {TABLE_MINIAPP_PROJECTS} (name, slug, description, created_by)
                VALUES (%s, %s, %s, %s) RETURNING id""",
            (name, slug, description, created_by)
        )
        conn.commit()
        pid = cur.fetchone()['id']
    return get_project(pid)


def get_project(project_id: int) -> dict:
    """Get a project by id, including its version count."""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT * FROM {TABLE_MINIAPP_PROJECTS} WHERE id=%s", (project_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d['version_count'] = conn.execute(
            f"SELECT COUNT(*) c FROM {TABLE_MINIAPP_VERSIONS} WHERE project_id=%s",
            (project_id,)
        ).fetchone()['c']
    return d


def get_project_by_slug(slug: str) -> dict:
    """Get a project by slug."""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT * FROM {TABLE_MINIAPP_PROJECTS} WHERE slug=%s", (slug,)
        ).fetchone()
    return dict(row) if row else None


def list_projects(created_by=None, limit=100) -> list:
    """List projects (optionally filtered by owner), newest first."""
    with get_db() as conn:
        if created_by:
            rows = conn.execute(
                f"""SELECT p.*, (SELECT COUNT(*) FROM {TABLE_MINIAPP_VERSIONS} v
                        WHERE v.project_id=p.id) AS version_count
                    FROM {TABLE_MINIAPP_PROJECTS} p
                    WHERE p.created_by=%s ORDER BY p.updated_at DESC LIMIT %s""",
                (created_by, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT p.*, (SELECT COUNT(*) FROM {TABLE_MINIAPP_VERSIONS} v
                        WHERE v.project_id=p.id) AS version_count
                    FROM {TABLE_MINIAPP_PROJECTS} p
                    ORDER BY p.updated_at DESC LIMIT %s""",
                (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


def delete_project(project_id: int) -> bool:
    """Delete a project and all its version records (DB only; caller handles files)."""
    with get_db() as conn:
        conn.execute(
            f"DELETE FROM {TABLE_MINIAPP_VERSIONS} WHERE project_id=%s", (project_id,)
        )
        cur = conn.execute(
            f"DELETE FROM {TABLE_MINIAPP_PROJECTS} WHERE id=%s", (project_id,)
        )
        conn.commit()
    return cur.rowcount > 0


def next_version_no(project_id: int) -> int:
    """Return the next version number for a project (1-based)."""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT COALESCE(MAX(version_no), 0) mx FROM {TABLE_MINIAPP_VERSIONS} WHERE project_id=%s",
            (project_id,)
        ).fetchone()
    return (row['mx'] or 0) + 1


def create_version(project_id: int, version_no: int, platforms: list,
                   options: dict, result: dict, output_path: str,
                   status: str = 'completed') -> int:
    """Record a generated version; bump the project's updated_at."""
    with get_db() as conn:
        cur = conn.execute(
            f"""INSERT INTO {TABLE_MINIAPP_VERSIONS}
                (project_id, version_no, platforms_json, options_json,
                 result_json, output_path, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (project_id, version_no,
             json.dumps(platforms, ensure_ascii=False),
             json.dumps(options, ensure_ascii=False),
             json.dumps(result, ensure_ascii=False),
             output_path, status)
        )
        version_id = cur.fetchone()['id']  # 必须在 commit 前取值
        conn.execute(
            f"UPDATE {TABLE_MINIAPP_PROJECTS} SET updated_at=NOW() WHERE id=%s",
            (project_id,)
        )
        conn.commit()
        return version_id


def list_versions(project_id: int) -> list:
    """List all versions of a project, newest first, with JSON fields parsed."""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM {TABLE_MINIAPP_VERSIONS} WHERE project_id=%s ORDER BY version_no DESC",
            (project_id,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for key in ('platforms_json', 'options_json', 'result_json'):
            if d.get(key):
                try:
                    d[key.replace('_json', '')] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    d[key.replace('_json', '')] = None
            del d[key]
        result.append(d)
    return result


def get_version(version_id: int) -> dict:
    """Get a single version by id with JSON fields parsed."""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT * FROM {TABLE_MINIAPP_VERSIONS} WHERE id=%s", (version_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    for key in ('platforms_json', 'options_json', 'result_json', 'ai_plan_json', 'widgets_json'):
        if d.get(key):
            try:
                d[key.replace('_json', '')] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key.replace('_json', '')] = None
        del d[key]
    return d


def get_mini_app_stats() -> dict:
    """Return mini-app statistics for Dashboard."""
    with get_db() as conn:
        projects = conn.execute("SELECT COUNT(*) AS count FROM mini_app_projects").fetchone()
        versions = conn.execute("SELECT COUNT(*) AS count FROM mini_app_versions").fetchone()
    return {
        'total_projects': projects['count'] if projects else 0,
        'total_versions': versions['count'] if versions else 0,
    }
