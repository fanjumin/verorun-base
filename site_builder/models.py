#!/usr/bin/env python3
"""Site Builder — 数据模型 & CRUD"""

import os, json, yaml
from models import get_db

# ── 表名常量 ──
TABLE_PROMPTS = 'site_builder_prompts'
TABLE_TASKS = 'site_builder_tasks'


def init_tables():
    """创建 site_builder 所需的数据库表（幂等）"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS site_builder_prompts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier      TEXT UNIQUE NOT NULL,
                name            TEXT NOT NULL,
                description     TEXT DEFAULT '',
                icon            TEXT DEFAULT '📄',
                industry        TEXT DEFAULT '',
                tags_json       TEXT DEFAULT '[]',
                is_builtin      INTEGER DEFAULT 1,
                is_active       INTEGER DEFAULT 1,
                defaults_json   TEXT DEFAULT '{}',
                pages_json      TEXT DEFAULT '[]',
                documents_json  TEXT DEFAULT '[]',
                prompts_json    TEXT DEFAULT '{}',
                created_by      INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS site_builder_tasks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id         TEXT UNIQUE NOT NULL,
                user_id         INTEGER NOT NULL,
                site_config_id  INTEGER DEFAULT 1,
                prompt_id       INTEGER,
                user_input      TEXT DEFAULT '',
                status          TEXT DEFAULT 'pending',
                plan_json       TEXT DEFAULT '{}',
                result_json     TEXT DEFAULT '{}',
                current_step    TEXT DEFAULT '',
                error_message   TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now')),
                finished_at     TEXT DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_sbp_identifier ON site_builder_prompts(identifier);
            CREATE INDEX IF NOT EXISTS idx_sbp_industry ON site_builder_prompts(industry);
            CREATE INDEX IF NOT EXISTS idx_sbt_user ON site_builder_tasks(user_id);
            CREATE INDEX IF NOT EXISTS idx_sbt_status ON site_builder_tasks(status);
        """)
        conn.commit()
    print('[SiteBuilder] ✅ Tables initialized')


def seed_default_prompts():
    """播种内置行业提示词模板（幂等，已存在则跳过）"""
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
            print(f'[SiteBuilder] ⚠️ 加载提示词模板失败 {fname}: {e}')
            continue

        identifier = data.get('identifier', fname.replace('.yml', ''))
        with get_db() as conn:
            exist = conn.execute(
                f"SELECT id FROM {TABLE_PROMPTS} WHERE identifier=?",
                (identifier,)
            ).fetchone()
            if exist:
                continue

            conn.execute(
                f'''INSERT OR IGNORE INTO {TABLE_PROMPTS}
                    (identifier, name, description, icon, industry, tags_json,
                     is_builtin, defaults_json, pages_json, documents_json, prompts_json)
                    VALUES (?,?,?,?,?,?,1,?,?,?,?)''',
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


# ── CRUD 辅助函数 ──

def get_prompt(identifier_or_id):
    """获取单个提示词模板"""
    with get_db() as conn:
        if isinstance(identifier_or_id, int):
            row = conn.execute(
                f"SELECT * FROM {TABLE_PROMPTS} WHERE id=?", (identifier_or_id,)
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT * FROM {TABLE_PROMPTS} WHERE identifier=?", (identifier_or_id,)
            ).fetchone()
        if not row:
            return None
        return _parse_prompt_row(row)


def list_prompts(active_only=False, industry=None):
    """列出所有提示词模板"""
    with get_db() as conn:
        conditions = []
        params = []
        if active_only:
            conditions.append("is_active=1")
        if industry:
            conditions.append("industry=?")
            params.append(industry)
        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"SELECT * FROM {TABLE_PROMPTS} WHERE {where} ORDER BY is_builtin DESC, id ASC",
            params
        ).fetchall()
    return [_parse_prompt_row(r) for r in rows]


def create_prompt(data: dict) -> int:
    """创建自定义提示词模板，返回新 ID"""
    identifier = data.get('identifier', '').strip()
    if not identifier:
        identifier = 'custom_' + _short_id()
    with get_db() as conn:
        conn.execute(
            f'''INSERT INTO {TABLE_PROMPTS}
                (identifier, name, description, icon, industry, tags_json,
                 is_builtin, is_active, defaults_json, pages_json, documents_json, prompts_json, created_by)
                VALUES (?,?,?,?,?,?,0,1,?,?,?,?,?)''',
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
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return new_id


def update_prompt(prompt_id: int, data: dict):
    """更新提示词模板"""
    fields = []
    params = []
    for key in ['name', 'description', 'icon', 'industry', 'is_active']:
        if key in data:
            fields.append(f"{key}=?")
            params.append(data[key])
    for key in ['tags', 'defaults', 'pages', 'documents', 'prompts']:
        json_key = f"{key}_json" if key == 'tags' else f"{key}_json"
        if key in data:
            fields.append(f"{json_key}=?")
            params.append(json.dumps(data[key], ensure_ascii=False))
    fields.append("updated_at=datetime('now')")
    params.append(prompt_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE {TABLE_PROMPTS} SET {', '.join(fields)} WHERE id=?",
            params
        )
        conn.commit()


def delete_prompt(prompt_id: int):
    """删除提示词模板（仅允许删除用户创建的）"""
    with get_db() as conn:
        conn.execute(
            f"DELETE FROM {TABLE_PROMPTS} WHERE id=? AND is_builtin=0",
            (prompt_id,)
        )
        conn.commit()


# ── 任务管理 ──

def create_task(user_id: int, prompt_id: int, user_input: str, site_config_id: int = 1) -> str:
    """创建建站任务，返回 task_id"""
    import datetime, secrets
    task_id = f"SB-{datetime.datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
    with get_db() as conn:
        conn.execute(
            f'''INSERT INTO {TABLE_TASKS}
                (task_id, user_id, site_config_id, prompt_id, user_input, status)
                VALUES (?,?,?,?,?,'pending')''',
            (task_id, user_id, site_config_id, prompt_id, user_input)
        )
        conn.commit()
    return task_id


def update_task(task_id: str, **kwargs):
    """更新任务状态"""
    allowed = ['status', 'plan_json', 'result_json', 'current_step', 'error_message']
    fields = []
    params = []
    for key in allowed:
        if key in kwargs:
            fields.append(f"{key}=?")
            val = kwargs[key]
            if isinstance(val, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)
            params.append(val)
    if kwargs.get('status') in ('completed', 'failed'):
        fields.append("finished_at=datetime('now')")
    fields.append("updated_at=datetime('now')")
    params.append(task_id)
    with get_db() as conn:
        conn.execute(
            f"UPDATE {TABLE_TASKS} SET {', '.join(fields)} WHERE task_id=?",
            params
        )
        conn.commit()


def get_task(task_id: str):
    """获取任务详情"""
    with get_db() as conn:
        row = conn.execute(
            f"SELECT * FROM {TABLE_TASKS} WHERE task_id=?", (task_id,)
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
    """列出任务"""
    with get_db() as conn:
        if user_id:
            rows = conn.execute(
                f"SELECT * FROM {TABLE_TASKS} WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM {TABLE_TASKS} ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


# ── 内部辅助 ──

def _parse_prompt_row(row):
    """将数据库行转为字典，解析 JSON 字段"""
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