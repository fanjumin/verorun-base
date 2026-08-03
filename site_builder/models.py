#!/usr/bin/env python3
"""Site Builder — Data Models & CRUD"""

import os, json, yaml
from models import get_db

# ── Table Name Constants ──
TABLE_PROMPTS = 'site_builder_prompts'
TABLE_TASKS = 'site_builder_tasks'
TABLE_MINIAPP_PROJECTS = 'mini_app_projects'
TABLE_MINIAPP_VERSIONS = 'mini_app_versions'


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
    """Create site_builder DB tables (idempotent)"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS site_builder_prompts (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                identifier      TEXT UNIQUE NOT NULL,
                name            TEXT NOT NULL,
                description     TEXT DEFAULT '',
                icon            TEXT DEFAULT '📄',
                industry        TEXT DEFAULT '',
                tags_json       TEXT DEFAULT '[]',
                is_builtin      BIGINT DEFAULT 1,
                is_active       BIGINT DEFAULT 1,
                defaults_json   TEXT DEFAULT '{}',
                pages_json      TEXT DEFAULT '[]',
                documents_json  TEXT DEFAULT '[]',
                prompts_json    TEXT DEFAULT '{}',
                created_by      BIGINT DEFAULT 0,
                created_at      TEXT DEFAULT (NOW()),
                updated_at      TEXT DEFAULT (NOW())
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS site_builder_tasks (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                task_id         TEXT UNIQUE NOT NULL,
                user_id         BIGINT NOT NULL,
                site_config_id  BIGINT DEFAULT 1,
                prompt_id       BIGINT,
                user_input      TEXT DEFAULT '',
                status          TEXT DEFAULT 'pending',
                plan_json       TEXT DEFAULT '{}',
                result_json     TEXT DEFAULT '{}',
                current_step    TEXT DEFAULT '',
                error_message   TEXT DEFAULT '',
                created_at      TEXT DEFAULT (NOW()),
                updated_at      TEXT DEFAULT (NOW()),
                finished_at     TEXT DEFAULT ''
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sbp_identifier ON site_builder_prompts(identifier)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sbp_industry ON site_builder_prompts(industry)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sbt_user ON site_builder_tasks(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sbt_status ON site_builder_tasks(status)")
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

        # Migration: add new AI-prompt columns to existing mini_app_versions tables
        _migrate_mini_app_versions_ai_columns(conn)
        conn.commit()
    print('[SiteBuilder] ✅ Tables initialized')


def seed_default_prompts():
    """Seed built-in industry prompt templates (idempotent, skip if exists)"""
    prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')
    if not os.path.isdir(prompts_dir):
        return 0

    count = 0
    for fname in sorted(os.listdir(prompts_dir)):
        if not fname.endswith('.yml'):
            continue
        fpath = os.path.join(prompts_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f'[SiteBuilder] Failed to load prompt template {fname}: {e}')
            continue

        identifier = data.get('identifier', fname.replace('.yml', ''))
        with get_db() as conn:
            exist = conn.execute(
                f"SELECT id FROM {TABLE_PROMPTS} WHERE identifier=%s",
                (identifier,)
            ).fetchone()
            if exist:
                continue

            conn.execute(
                f'''INSERT INTO {TABLE_PROMPTS}
                    (identifier, name, description, icon, industry, tags_json,
                     is_builtin, defaults_json, pages_json, documents_json, prompts_json)
                    VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s)
                    ON CONFLICT (identifier) DO NOTHING''',
                (
                    identifier,
                    data.get('name', identifier),
                    data.get('description', ''),
                    data.get('icon', '📄'),
                    data.get('industry', ''),
                    json.dumps(data.get('tags', []), ensure_ascii=False),
                    json.dumps(data.get('defaults', {}), ensure_ascii=False),
                    json.dumps(data.get('pages', []), ensure_ascii=False),
                    json.dumps(data.get('documents', []), ensure_ascii=False),
                    json.dumps(data.get('prompts', {}), ensure_ascii=False),
                )
            )
            conn.commit()
            count += 1
    if count:
        print(f'[SiteBuilder] ✅ Seeded {count} built-in prompt templates')
    return count


# ── CRUD Helpers ──

def get_prompt(identifier_or_id):
    """Get a single prompt template"""
    with get_db() as conn:
        if isinstance(identifier_or_id, int):
            row = conn.execute(
                f"SELECT * FROM {TABLE_PROMPTS} WHERE id=%s", (identifier_or_id,)
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT * FROM {TABLE_PROMPTS} WHERE identifier=%s", (identifier_or_id,)
            ).fetchone()
        if not row:
            return None
        return _parse_prompt_row(row)


def list_prompts(active_only=False, industry=None):
    """List all prompt templates"""
    with get_db() as conn:
        conditions = []
        params = []
        if active_only:
            conditions.append("is_active=1")
        if industry:
            conditions.append("industry=%s")
            params.append(industry)
        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"SELECT * FROM {TABLE_PROMPTS} WHERE {where} ORDER BY is_builtin DESC, id ASC",
            params
        ).fetchall()
    return [_parse_prompt_row(r) for r in rows]


def create_prompt(data: dict) -> int:
    """Create a custom prompt template, return new ID"""
    identifier = data.get('identifier', '').strip()
    if not identifier:
        identifier = 'custom_' + _short_id()
    with get_db() as conn:
        conn.execute(
            f'''INSERT INTO {TABLE_PROMPTS}
                (identifier, name, description, icon, industry, tags_json,
                 is_builtin, is_active, defaults_json, pages_json, documents_json, prompts_json, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,0,1,%s,%s,%s,%s,%s)''',
            (
                identifier,
                data.get('name', ''),
                data.get('description', ''),
                data.get('icon', '📄'),
                data.get('industry', ''),
                json.dumps(data.get('tags', []), ensure_ascii=False),
                json.dumps(data.get('defaults', {}), ensure_ascii=False),
                json.dumps(data.get('pages', []), ensure_ascii=False),
                json.dumps(data.get('documents', []), ensure_ascii=False),
                json.dumps(data.get('prompts', {}), ensure_ascii=False),
                data.get('created_by', 0),
            )
        )
        conn.commit()
        new_id = conn.execute("SELECT lastval()").fetchone()['lastval']
    return new_id


def update_prompt(prompt_id: int, data: dict):
    """Update prompt template"""
    fields = []
    params = []
    for key in ['name', 'description', 'icon', 'industry', 'is_active']:
        if key in data:
            fields.append(f"{key}=%s")
            params.append(data[key])
    for key in ['tags', 'defaults', 'pages', 'documents', 'prompts']:
        json_key = f"{key}_json" if key == 'tags' else f"{key}_json"
        if key in data:
            fields.append(f"{json_key}=%s")
            params.append(json.dumps(data[key], ensure_ascii=False))
    fields.append("updated_at=NOW()")
    params.append(prompt_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE {TABLE_PROMPTS} SET {', '.join(fields)} WHERE id=%s",
            params
        )
        conn.commit()


def delete_prompt(prompt_id: int):
    """Delete prompt template (only user-created)"""
    with get_db() as conn:
        conn.execute(
            f"DELETE FROM {TABLE_PROMPTS} WHERE id=%s AND is_builtin=0",
            (prompt_id,)
        )
        conn.commit()


# ── Task Management ──

def create_task(user_id: int, prompt_id: int, user_input: str, site_config_id: int = 1) -> str:
    """Create a build task, return task_id"""
    import datetime, secrets
    task_id = f"SB-{datetime.datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
    with get_db() as conn:
        conn.execute(
            f'''INSERT INTO {TABLE_TASKS}
                (task_id, user_id, site_config_id, prompt_id, user_input, status)
                VALUES (%s,%s,%s,%s,%s,'pending')''',
            (task_id, user_id, site_config_id, prompt_id, user_input)
        )
        conn.commit()
    return task_id


def update_task(task_id: str, **kwargs):
    """Update task status"""
    allowed = ['status', 'plan_json', 'result_json', 'current_step', 'error_message']
    fields = []
    params = []
    for key in allowed:
        if key in kwargs:
            fields.append(f"{key}=%s")
            val = kwargs[key]
            if isinstance(val, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)
            params.append(val)
    if kwargs.get('status') in ('completed', 'failed'):
        fields.append("finished_at=NOW()")
    fields.append("updated_at=NOW()")
    params.append(task_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE {TABLE_TASKS} SET {', '.join(fields)} WHERE task_id=%s",
            params
        )
        conn.commit()


def get_task(task_id: str):
    """Get task details"""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT * FROM {TABLE_TASKS} WHERE task_id=%s", (task_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ('plan_json', 'result_json'):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d


def list_tasks(user_id=None, limit=20):
    """List tasks"""
    with get_db() as conn:
        if user_id:
            rows = conn.execute(
                f"SELECT * FROM {TABLE_TASKS} WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
                (user_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM {TABLE_TASKS} ORDER BY created_at DESC LIMIT %s",
                (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


# ── Internal Helpers ──

def _parse_prompt_row(row):
    """Convert DB row to dict, parse JSON fields"""
    d = dict(row)
    for key in ('tags_json', 'defaults_json', 'pages_json', 'documents_json', 'prompts_json'):
        if d.get(key):
            try:
                d[key.replace('_json', '')] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                d[key.replace('_json', '')] = {}
        del d[key]
    return d


def _short_id():
    import secrets
    return secrets.token_hex(4)


# ══════════════════════════════════════════════════════════════
# Mini-App Projects & Versions
# ══════════════════════════════════════════════════════════════

def _slugify(name: str) -> str:
    """Convert a project name to a filesystem-safe slug."""
    import re
    slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]+', '-', (name or '').strip().lower())
    slug = slug.strip('-')
    return slug or f'project-{_short_id()}'


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
