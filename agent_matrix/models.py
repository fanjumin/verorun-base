#!/usr/bin/env python3
"""
Agent Matrix — 数据库模型
======================
4 张新表 + CRUD 操作 + 种子数据（基于 YAML 角色定义）。
复用 auth-center/models/database.py 的 get_db() 模式。
"""
from i18n import _
import json, os, sys, re, threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROLES_DIR = os.path.join(BASE_DIR, 'roles')

# ── 复用主应用 PostgreSQL 连接 ──
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center', 'models'))
from database import get_db, get_table_columns


# ── 轻量 YAML 解析器（仅支持角色定义所需子集） ──
def _parse_role_yaml(text):
    """解析简单的 flat key:value / key:\\n  - item 格式 YAML，返回 dict。"""
    data = {}
    current_list_key = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # key: value 行（非缩进）
        m = re.match(r'^(\w[\w_]*)\s*:\s*(.*)', line)
        if m and not line.startswith(' '):
            key, val = m.group(1), m.group(2).strip()
            current_list_key = None
            if val == '':
                # 后面跟列表项
                current_list_key = key
                data[key] = []
            else:
                data[key] = val
        elif stripped.startswith('- ') and current_list_key:
            data[current_list_key].append(stripped[2:].strip())
        else:
            current_list_key = None
    return data


def _to_int(val, default=0):
    """安全转换：'true'/'false'/数字字符串 → int"""
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v == 'true':
            return 1
        if v == 'false':
            return 0
        try:
            return int(v)
        except ValueError:
            return default
    return default


def _load_all_role_yamls():
    """从 ROLES_DIR 加载所有 .yaml 文件，返回角色 dict 列表。"""
    roles = []
    if not os.path.isdir(ROLES_DIR):
        return roles
    for fname in sorted(os.listdir(ROLES_DIR)):
        if not fname.endswith('.yaml') and not fname.endswith('.yml'):
            continue
        fpath = os.path.join(ROLES_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = _parse_role_yaml(f.read())
            # 类型转换
            raw['is_active'] = _to_int(raw.get('is_active', 1))
            raw['is_system'] = _to_int(raw.get('is_system', 0))
            raw['auto_approve'] = _to_int(raw.get('auto_approve', 0))
            raw['managed_modules'] = json.dumps(raw.get('managed_modules', []))
            raw['capabilities'] = json.dumps(raw.get('capabilities', []))
            raw['allowed_tools'] = json.dumps(raw.get('allowed_tools', []))
            roles.append(raw)
        except Exception as e:
            print(f'[RoleYAML] Skipped {fname}: {e}')
    return roles


# ============================================================
# Task ID 生成器
# ============================================================
_task_counter = 0  # Will be overridden by _init_task_counter()
_task_counter_lock = threading.Lock()

def _init_task_counter():
    """Initialize task counter from DB to avoid UNIQUE constraint violations on restart."""
    global _task_counter
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT MAX(CAST(SUBSTR(task_id, -4) AS INTEGER)) AS max_id FROM agent_tasks "
                "WHERE task_id LIKE 'AT-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-%'"
            ).fetchone()
            _task_counter = row['max_id'] if row and row['max_id'] else 0
    except Exception:
        _task_counter = 0

_init_task_counter()

def _next_task_id():
    global _task_counter
    with _task_counter_lock:
        _task_counter += 1
        date = datetime.now().strftime('%Y%m%d')
        return f'AT-{date}-{_task_counter:06d}'


def _next_session_id():
    date = datetime.now().strftime('%Y%m%d')
    import random
    suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    return f'SESSION-{date}-{suffix}'


def get_master_agent_config():
    """从 agent_matrix 表中读取 Master Agent 的 provider/model 配置"""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT provider, model_name FROM agent_matrix WHERE is_master=TRUE LIMIT 1"
            ).fetchone()
            if row:
                return {'provider': row['provider'], 'model_name': row['model_name']}
    except Exception:
        pass
    return {'provider': 'dashscope', 'model_name': 'qwen-turbo'}


# ============================================================
# 建表
# ============================================================

def init_agent_matrix_tables():
    """创建 4 张新表（幂等）"""
    with get_db() as conn:
        conn.executescript("""
            -- ================================================
            -- 1. Agent 矩阵配置表
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_matrix (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name            TEXT NOT NULL,
                slug            TEXT DEFAULT '',
                role_type       TEXT NOT NULL DEFAULT 'sub'
                                CHECK(role_type IN ('master','sub')),
                description     TEXT DEFAULT '',
                domain          TEXT NOT NULL DEFAULT 'general',
                managed_modules TEXT DEFAULT '[]',
                provider        TEXT NOT NULL DEFAULT 'dashscope',
                model_name      TEXT NOT NULL DEFAULT 'qwen-turbo',
                api_key_ref     TEXT DEFAULT 'dashscope_text_key',
                base_url        TEXT DEFAULT '',
                model_provider_id BIGINT DEFAULT NULL,  -- deprecated
                provider_model_id BIGINT DEFAULT NULL,
                system_prompt   TEXT DEFAULT '',
                role_prompt     TEXT DEFAULT '',
                task_template   TEXT DEFAULT '',
                capabilities    TEXT DEFAULT '[]',
                allowed_tools   TEXT DEFAULT '[]',
                max_concurrency BIGINT DEFAULT 1,
                priority        BIGINT DEFAULT 5,
                auto_approve    BIGINT DEFAULT 0,
                is_active       BIGINT DEFAULT 1,
                is_system       BIGINT DEFAULT 0,
                tasks_total     BIGINT DEFAULT 0,
                tasks_success   BIGINT DEFAULT 0,
                tasks_failed    BIGINT DEFAULT 0,
                last_run_at     TEXT DEFAULT '',
                created_at      TEXT DEFAULT (NOW()),
                updated_at      TEXT DEFAULT (NOW()),
                UNIQUE(name, role_type)
            );

            -- ================================================
            -- 2. 任务调度表
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                task_id         TEXT UNIQUE NOT NULL,
                parent_task_id  TEXT DEFAULT NULL,
                master_task_id  TEXT DEFAULT NULL,
                source_agent_id BIGINT NOT NULL,
                target_agent_id BIGINT NOT NULL,
                task_type       TEXT NOT NULL DEFAULT 'execute'
                                CHECK(task_type IN ('execute','review','approve','composite','cron')),
                title           TEXT NOT NULL,
                description     TEXT DEFAULT '',
                input_data      TEXT DEFAULT '{}',
                expected_output TEXT DEFAULT '{}',
                target_module   TEXT DEFAULT '',
                target_api      TEXT DEFAULT '',
                priority        BIGINT DEFAULT 5,
                max_retries     BIGINT DEFAULT 3,
                retry_count     BIGINT DEFAULT 0,
                timeout_seconds BIGINT DEFAULT 300,
                status          TEXT NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending','running','completed','failed',
                                                 'cancelled','needs_review','retrying')),
                result_data     TEXT DEFAULT '{}',
                confidence      DOUBLE PRECISION DEFAULT 0.0,
                error_message   TEXT DEFAULT '',
                self_review     TEXT DEFAULT '',
                cross_review    TEXT DEFAULT '',
                created_at      TEXT DEFAULT (NOW()),
                started_at      TEXT DEFAULT '',
                completed_at    TEXT DEFAULT '',
                updated_at      TEXT DEFAULT (NOW())
            );

            CREATE INDEX IF NOT EXISTS idx_at_status ON agent_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_at_source ON agent_tasks(source_agent_id);
            CREATE INDEX IF NOT EXISTS idx_at_target ON agent_tasks(target_agent_id);
            CREATE INDEX IF NOT EXISTS idx_at_master ON agent_tasks(master_task_id);
            CREATE INDEX IF NOT EXISTS idx_at_module ON agent_tasks(target_module);

            -- ================================================
            -- 3. 执行日志表
            -- ================================================
            CREATE TABLE IF NOT EXISTS task_logs (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                task_id         TEXT NOT NULL,
                agent_id        BIGINT NOT NULL,
                log_level       TEXT NOT NULL DEFAULT 'info'
                                CHECK(log_level IN ('debug','info','warn','error')),
                log_type        TEXT NOT NULL DEFAULT 'execution'
                                CHECK(log_type IN ('execution','self_review','cross_review','approval','api_call')),
                message         TEXT NOT NULL,
                metadata        TEXT DEFAULT '{}',
                created_at      TEXT DEFAULT (NOW())
            );

            CREATE INDEX IF NOT EXISTS idx_tl_task ON task_logs(task_id);
            CREATE INDEX IF NOT EXISTS idx_tl_type ON task_logs(log_type);

            -- ================================================
            -- 4. 对话记录表
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_conversations (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                master_task_id  TEXT DEFAULT '',
                session_id      TEXT NOT NULL,
                role            TEXT NOT NULL CHECK(role IN ('user','master','sub','system')),
                agent_id        BIGINT DEFAULT NULL,
                agent_name      TEXT DEFAULT '',
                content         TEXT NOT NULL,
                metadata        TEXT DEFAULT '{}',
                created_at      TEXT DEFAULT (NOW())
            );

            CREATE INDEX IF NOT EXISTS idx_ac_session ON agent_conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_ac_task ON agent_conversations(master_task_id);

            -- ================================================
            -- 5. Token 消耗日志表 (2026-05-16)
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_token_logs (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                agent_id        BIGINT NOT NULL,
                agent_name      TEXT DEFAULT '',
                model_name      TEXT DEFAULT '',
                provider        TEXT DEFAULT '',
                prompt_tokens   BIGINT DEFAULT 0,
                completion_tokens BIGINT DEFAULT 0,
                total_tokens    BIGINT DEFAULT 0,
                call_type       TEXT DEFAULT 'chat',
                dimension       TEXT DEFAULT 'text',
                user_id         BIGINT DEFAULT NULL,
                task_id         TEXT DEFAULT '',
                session_id      TEXT DEFAULT '',
                created_at      TEXT DEFAULT (NOW())
            );

            CREATE INDEX IF NOT EXISTS idx_tkl_agent_id   ON agent_token_logs(agent_id);
            CREATE INDEX IF NOT EXISTS idx_tkl_created_at ON agent_token_logs(created_at);
            -- idx_tkl_date and idx_tkl_agent_date removed:
            -- date(text) is STABLE, not IMMUTABLE — PostgreSQL requires IMMUTABLE for index expressions

            -- ================================================
            -- 6. Token 每日汇总表 (2026-05-16)
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_token_daily (
                id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                agent_id        BIGINT NOT NULL,
                agent_name      TEXT DEFAULT '',
                stat_date       TEXT NOT NULL DEFAULT (CURRENT_DATE),
                prompt_tokens   BIGINT DEFAULT 0,
                completion_tokens BIGINT DEFAULT 0,
                total_tokens    BIGINT DEFAULT 0,
                call_count      BIGINT DEFAULT 0,
                updated_at      TEXT DEFAULT (NOW()),
                UNIQUE(agent_id, stat_date)
            );

            CREATE INDEX IF NOT EXISTS idx_tkd_date ON agent_token_daily(stat_date);

            -- ================================================
            -- 7. 模块用量日志表 (Phase 1 模块化订阅)
            -- ================================================
            CREATE TABLE IF NOT EXISTS module_usage_log (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                module_key  TEXT NOT NULL,
                agent_id    BIGINT NOT NULL,
                task_id     TEXT NOT NULL,
                used_at     TIMESTAMP DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_mul_user_module ON module_usage_log(user_id, module_key);
            CREATE INDEX IF NOT EXISTS idx_mul_used_at ON module_usage_log(used_at);
        """)
        conn.commit()

    # 会话标题字段 (v2 迁移) — 单独执行，不能放 executescript 内
    with get_db() as conn:
        cols = get_table_columns(conn, 'agent_conversations')
        if 'session_name' not in cols:
            conn.execute("ALTER TABLE agent_conversations ADD COLUMN session_name TEXT DEFAULT ''")
            conn.commit()

    # ── Migration: add provider_model_id to agent_matrix ──
    with get_db() as conn:
        cols = get_table_columns(conn, 'agent_matrix')
        if 'provider_model_id' not in cols:
            conn.execute("ALTER TABLE agent_matrix ADD COLUMN provider_model_id BIGINT DEFAULT NULL")
            conn.commit()
            print('[Migration] Added agent_matrix.provider_model_id')
        # Migrate old model_provider_id → provider_model_id
        rows = conn.execute(
            "SELECT id, model_provider_id FROM agent_matrix WHERE provider_model_id IS NULL AND model_provider_id IS NOT NULL"
        ).fetchall()
        for a in rows:
            conn.execute("UPDATE agent_matrix SET provider_model_id=%s WHERE id=%s",
                         (a['model_provider_id'], a['id']))
        if rows:
            conn.commit()
            print(f'[Migration] Migrated {len(rows)} agent_matrix rows model_provider_id→provider_model_id')

    # ── Migration: add dimension to agent_token_logs ──
    with get_db() as conn:
        cols = get_table_columns(conn, 'agent_token_logs')
        if 'dimension' not in cols:
            conn.execute("ALTER TABLE agent_token_logs ADD COLUMN dimension TEXT DEFAULT 'text'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tkl_dimension ON agent_token_logs(dimension)")
            conn.commit()
            print('[Migration] Added agent_token_logs.dimension')

    # ── Migration: add module to agent_token_logs ──
    with get_db() as conn:
        cols = get_table_columns(conn, 'agent_token_logs')
        if 'module' not in cols:
            conn.execute("ALTER TABLE agent_token_logs ADD COLUMN module TEXT DEFAULT 'legacy'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tkl_module ON agent_token_logs(module)")
            conn.commit()
            print('[Migration] Added agent_token_logs.module')

    # ── Migration: add index on agent_token_logs.user_id (for token_stats JOINs) ──
    with get_db() as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tkl_user_id ON agent_token_logs(user_id)")
        conn.commit()
        print('[Migration] Added agent_token_logs.user_id index')

    # ── Migration: make legacy agent_matrix fields nullable ──
    with get_db() as conn:
        # provider/model_name no longer required — provider_model_id is the canonical reference
        conn.execute("ALTER TABLE agent_matrix ALTER COLUMN provider DROP NOT NULL")
        conn.execute("ALTER TABLE agent_matrix ALTER COLUMN model_name DROP NOT NULL")
        conn.commit()
        print('[Migration] agent_matrix.provider/model_name made nullable')

    # ── Migration: add slug & is_system to agent_matrix ──
    with get_db() as conn:
        cols = get_table_columns(conn, 'agent_matrix')
        if 'slug' not in cols:
            conn.execute("ALTER TABLE agent_matrix ADD COLUMN slug TEXT DEFAULT ''")
        if 'is_system' not in cols:
            conn.execute("ALTER TABLE agent_matrix ADD COLUMN is_system BIGINT DEFAULT 0")
        if 'slug' not in cols or 'is_system' not in cols:
            conn.commit()
            print('[Migration] Added agent_matrix.slug / is_system')


# ============================================================
# Seed 数据（从 YAML 角色定义加载）
# ============================================================

def load_system_roles():
    """从 YAML 文件加载系统角色定义列表。"""
    return _load_all_role_yamls()


def seed_default_agents():
    """YAML→DB 同步：从 YAML 角色定义文件同步到 agent_matrix 表。

    同步规则：
    1. YAML 中的角色，DB 中 slug 不存在 → INSERT（新系统角色）
    2. YAML 中的角色，DB 中 slug 已存在 → UPDATE（同步 name/description/managed_modules 等）
    3. DB 中 is_system=1 但 YAML 中已不存在 → DELETE（旧系统角色被删除/重命名）
    4. DB 中 is_system=0 的角色 → 不处理（用户自定义/插件角色，不受 YAML 影响）
    """
    roles = load_system_roles()
    if not roles:
        print(_('[Seed] Role YAML file not found, skipped seed data'))
        return

    yaml_slugs = set()
    with get_db() as conn:
        # ── Phase 1: UPSERT YAML-defined system roles ──
        for a in roles:
            slug = a.get('slug', '')
            if not slug:
                continue
            yaml_slugs.add(slug)

            exists = conn.execute(
                "SELECT id FROM agent_matrix WHERE slug=%s", (slug,)
            ).fetchone()

            if not exists:
                # INSERT new system role
                conn.execute("""
                    INSERT INTO agent_matrix
                    (name, slug, role_type, description, domain, managed_modules,
                     provider, model_name, system_prompt, auto_approve, is_active, is_system)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    a.get('name', ''), slug, a.get('role_type', 'sub'),
                    a.get('description', ''), a.get('domain', 'general'),
                    a.get('managed_modules', '[]'),
                    a.get('provider', 'dashscope'), a.get('model_name', 'qwen-turbo'),
                    a.get('system_prompt', ''),
                    a.get('auto_approve', 0), a.get('is_active', 1), a.get('is_system', 1)
                ))
                print(f'[Seed] Insert system role: {slug}')
            else:
                # UPDATE existing system role — sync all fields from YAML
                conn.execute("""
                    UPDATE agent_matrix SET
                        name=%s, description=%s, domain=%s,
                        managed_modules=%s, provider=%s, model_name=%s,
                        auto_approve=%s, is_system=1,
                        updated_at=NOW()
                    WHERE slug=%s
                """, (
                    a.get('name', ''), a.get('description', ''),
                    a.get('domain', 'general'),
                    a.get('managed_modules', '[]'),
                    a.get('provider', 'dashscope'),
                    a.get('model_name', 'qwen-turbo'),
                    a.get('auto_approve', 0),
                    slug
                ))

        # ── Phase 2: DELETE old system roles no longer in YAML ──
        deleted = 0
        if yaml_slugs:
            deleted = conn.execute("""
                DELETE FROM agent_matrix
                WHERE is_system=1 AND slug NOT IN ({})
                AND slug != ''
            """.format(','.join(['%s'] * len(yaml_slugs))),
                tuple(yaml_slugs)
            ).rowcount
        if deleted:
            print(f'[Seed] Cleaned up {deleted} old system roles')

        conn.commit()


# ============================================================
# Agent CRUD
# ============================================================

def register_plugin_roles(plugin_id, declare_roles_list):
    """注册插件声明的角色到 agent_matrix（幂等）。
    declare_roles_list: [ {name, slug, description, domain, managed_modules, ...} ]
    返回注册数量。
    """
    count = 0
    with get_db() as conn:
        for r in declare_roles_list:
            slug = r.get('slug') or r.get('name', '').lower().replace(' ', '-')
            exists = conn.execute(
                "SELECT id FROM agent_matrix WHERE slug=%s", (slug,)
            ).fetchone()
            if not exists:
                conn.execute("""
                    INSERT INTO agent_matrix
                    (name, slug, role_type, description, domain, managed_modules,
                     provider, model_name, system_prompt, is_active, is_system)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)
                """, (
                    r.get('name', ''), slug, r.get('role_type', 'sub'),
                    r.get('description', ''), r.get('domain', 'general'),
                    json.dumps(r.get('managed_modules', [])),
                    r.get('provider', 'dashscope'),
                    r.get('model_name', 'qwen-turbo'),
                    r.get('system_prompt', ''),
                    r.get('is_active', 1),
                ))
                count += 1
                print(f'[PluginRoles] Register plugin role: {slug} (from {plugin_id})')
        if count:
            conn.commit()
    return count


def unregister_plugin_roles(plugin_id, declare_roles_list):
    """卸载插件对应的角色。"""
    slugs = [
        r.get('slug') or r.get('name', '').lower().replace(' ', '-')
        for r in declare_roles_list
    ]
    with get_db() as conn:
        for slug in slugs:
            conn.execute("DELETE FROM agent_matrix WHERE slug=%s AND is_system=0", (slug,))
            print(f'[PluginRoles] Uninstall plugin role: {slug} (from {plugin_id})')
        conn.commit()


def list_agents(role_type=None, domain=None, active_only=False):
    """列出 Agent，支持筛选"""
    with get_db() as conn:
        sql = "SELECT * FROM agent_matrix WHERE 1=1"
        params = []
        if role_type:
            sql += " AND role_type=%s"
            params.append(role_type)
        if domain:
            sql += " AND domain=%s"
            params.append(domain)
        if active_only:
            sql += " AND is_active=1"
        sql += " ORDER BY priority DESC, created_at ASC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_agent(agent_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM agent_matrix WHERE id=%s", (agent_id,)).fetchone()
        return dict(row) if row else None


def get_agent_by_name(name, role_type='sub'):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM agent_matrix WHERE name=%s AND role_type=%s",
            (name, role_type)
        ).fetchone()
        return dict(row) if row else None


def get_agent_by_slug(slug):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM agent_matrix WHERE slug=%s", (slug,)
        ).fetchone()
        return dict(row) if row else None


def create_agent(data):
    with get_db() as conn:
        row = conn.execute("""
            INSERT INTO agent_matrix
            (name, role_type, description, domain, managed_modules,
             provider, model_name, api_key_ref, base_url, provider_model_id,
             system_prompt, role_prompt, task_template,
             capabilities, allowed_tools,
             max_concurrency, priority, auto_approve, is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            data.get('name', ''),
            data.get('role_type', 'sub'),
            data.get('description', ''),
            data.get('domain', 'general'),
            json.dumps(data.get('managed_modules', [])),
            data.get('provider', 'dashscope'),
            data.get('model_name', 'qwen-turbo'),
            data.get('api_key_ref', 'dashscope_text_key'),
            data.get('base_url', ''),
            data.get('provider_model_id'),
            data.get('system_prompt', ''),
            data.get('role_prompt', ''),
            data.get('task_template', ''),
            json.dumps(data.get('capabilities', [])),
            json.dumps(data.get('allowed_tools', [])),
            data.get('max_concurrency', 1),
            data.get('priority', 5),
            data.get('auto_approve', 0),
            data.get('is_active', 1)
        )).fetchone()
        conn.commit()
        return row[0]



def update_agent(agent_id, data):
    with get_db() as conn:
        fields = []
        values = []
        for key in ['name', 'role_type', 'description', 'domain',
                     'provider', 'model_name', 'api_key_ref', 'base_url', 'provider_model_id',
                     'system_prompt', 'role_prompt', 'task_template',
                     'max_concurrency', 'priority', 'auto_approve', 'is_active']:
            if key in data:
                fields.append(f"{key}=%s")
                values.append(data[key])
        for key in ['managed_modules', 'capabilities', 'allowed_tools']:
            if key in data:
                fields.append(f"{key}=%s")
                values.append(json.dumps(data[key]) if isinstance(data[key], list) else data[key])
        if not fields:
            return False
        fields.append("updated_at=NOW()")
        values.append(agent_id)
        conn.execute(
            f"UPDATE agent_matrix SET {','.join(fields)} WHERE id=%s",
            values
        )
        conn.commit()
        return True


def delete_agent(agent_id):
    """删除 Agent。系统角色（is_system=1）不可删除。"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT is_system FROM agent_matrix WHERE id=%s", (agent_id,)
        ).fetchone()
        if not row:
            return False
        if row['is_system']:
            raise PermissionError(_("System roles cannot be deleted, only disabled"))
        conn.execute("DELETE FROM agent_matrix WHERE id=%s", (agent_id,))
        conn.commit()
        return True


def toggle_agent(agent_id):
    """切换启用/禁用状态"""
    with get_db() as conn:
        row = conn.execute("SELECT is_active FROM agent_matrix WHERE id=%s", (agent_id,)).fetchone()
        if not row:
            return None
        new = 0 if row['is_active'] else 1
        conn.execute("UPDATE agent_matrix SET is_active=%s, updated_at=NOW() WHERE id=%s", (new, agent_id))
        conn.commit()
        return new


# ============================================================
# Task CRUD
# ============================================================

def create_task(data):
    task_id = _next_task_id()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO agent_tasks
            (task_id, parent_task_id, master_task_id,
             source_agent_id, target_agent_id,
             task_type, title, description,
             input_data, expected_output,
             target_module, target_api,
             priority, max_retries, timeout_seconds, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            task_id,
            data.get('parent_task_id'),
            data.get('master_task_id', task_id) if not data.get('parent_task_id') else data.get('master_task_id'),
            data['source_agent_id'],
            data['target_agent_id'],
            data.get('task_type', 'execute'),
            data.get('title', ''),
            data.get('description', ''),
            json.dumps(data.get('input_data', {})),
            json.dumps(data.get('expected_output', {})),
            data.get('target_module', ''),
            data.get('target_api', ''),
            data.get('priority', 5),
            data.get('max_retries', 3),
            data.get('timeout_seconds', 600),
            'pending'
        ))
        conn.commit()
        return task_id


def get_task(task_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM agent_tasks WHERE task_id=%s", (task_id,)).fetchone()
        return dict(row) if row else None


def list_tasks(status=None, module=None, agent_id=None, limit=50):
    with get_db() as conn:
        sql = "SELECT * FROM agent_tasks WHERE 1=1"
        params = []
        if status:
            sql += " AND status=%s"
            params.append(status)
        if module:
            sql += " AND target_module=%s"
            params.append(module)
        if agent_id:
            sql += " AND (source_agent_id=%s OR target_agent_id=%s)"
            params.extend([agent_id, agent_id])
        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def update_task_status(task_id, status, result_data=None, confidence=None,
                       error_message=None, self_review=None):
    with get_db() as conn:
        fields = ["status=%s", "updated_at=NOW()"]
        values = [status]
        if result_data is not None:
            fields.append("result_data=%s")
            values.append(json.dumps(result_data) if not isinstance(result_data, str) else result_data)
        if confidence is not None:
            fields.append("confidence=%s")
            values.append(confidence)
        if error_message is not None:
            fields.append("error_message=%s")
            values.append(error_message)
        if self_review is not None:
            fields.append("self_review=%s")
            values.append(self_review)
        if status == 'running':
            fields.append("started_at=NOW()")
        if status in ('completed', 'failed', 'cancelled'):
            fields.append("completed_at=NOW()")
        values.append(task_id)
        conn.execute(
            f"UPDATE agent_tasks SET {','.join(fields)} WHERE task_id=%s",
            values
        )
        conn.commit()


def get_sub_tasks(master_task_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_tasks WHERE master_task_id=%s ORDER BY created_at ASC",
            (master_task_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def cancel_task(task_id):
    update_task_status(task_id, 'cancelled')


# ============================================================
# 日志 CRUD
# ============================================================

def add_log(task_id, agent_id, level='info', log_type='execution', message='', metadata=None):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO task_logs (task_id, agent_id, log_level, log_type, message, metadata)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (task_id, agent_id, level, log_type, message,
              json.dumps(metadata or {})))
        conn.commit()


def get_task_logs(task_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM task_logs WHERE task_id=%s ORDER BY created_at ASC",
            (task_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 对话 CRUD
# ============================================================

def create_session():
    return _next_session_id()


def add_message(session_id, role, content, agent_id=None, agent_name='', master_task_id='', metadata=None):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO agent_conversations
            (session_id, role, agent_id, agent_name, content, master_task_id, metadata)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (session_id, role, agent_id, agent_name, content,
              master_task_id, json.dumps(metadata or {})))
        # 第一条用户消息设为会话标题
        if role == 'user':
            existing = conn.execute(
                "SELECT COUNT(*) as c FROM agent_conversations WHERE session_id=%s AND role='user'",
                (session_id,)
            ).fetchone()['c']
            if existing == 1:
                title = content.strip()[:40]
                conn.execute(
                    "UPDATE agent_conversations SET session_name=%s WHERE session_id=%s",
                    (title, session_id)
                )
        conn.commit()


def get_conversation(session_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_conversations WHERE session_id=%s ORDER BY created_at ASC",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_sessions(limit=20):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT session_id, MAX(created_at) as last_msg,
                   (SELECT content FROM agent_conversations WHERE session_id=ac.session_id
                    AND role='user' ORDER BY created_at ASC LIMIT 1) as first_query,
                   MAX(session_name) as session_name
            FROM agent_conversations ac
            GROUP BY session_id
            ORDER BY last_msg DESC
            LIMIT %s
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def search_conversations(keyword, limit=50):
    """全文检索对话内容（关键词匹配 content 字段）"""
    with get_db() as conn:
        like = f'%{keyword}%'
        rows = conn.execute("""
            SELECT ac.*,
                   (SELECT session_name FROM agent_conversations
                    WHERE session_id=ac.session_id AND session_name!=''
                    LIMIT 1) as session_name
            FROM agent_conversations ac
            WHERE content LIKE %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (like, limit)).fetchall()
        return [dict(r) for r in rows]


def batch_delete_sessions(session_ids):
    """批量删除指定会话的所有消息"""
    if not session_ids:
        return 0
    with get_db() as conn:
        placeholders = ','.join(['%s'] * len(session_ids))
        count = conn.execute(
            f"DELETE FROM agent_conversations WHERE session_id IN ({placeholders})",
            session_ids
        ).rowcount
        conn.commit()
        return count


# ============================================================
# Agent 统计更新
# ============================================================

def update_agent_stats(agent_id, success=True):
    """更新 Agent 的任务统计"""
    with get_db() as conn:
        field = 'tasks_success' if success else 'tasks_failed'
        conn.execute(f"""
            UPDATE agent_matrix
            SET tasks_total = tasks_total + 1,
                {field} = {field} + 1,
                last_run_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
        """, (agent_id,))
        conn.commit()


# ============================================================
# 统计
# ============================================================

def get_matrix_stats():
    with get_db() as conn:
        total_agents = conn.execute("SELECT COUNT(*) as c FROM agent_matrix").fetchone()['c']
        active_agents = conn.execute("SELECT COUNT(*) as c FROM agent_matrix WHERE is_active=1").fetchone()['c']
        master_count = conn.execute("SELECT COUNT(*) as c FROM agent_matrix WHERE role_type='master' AND is_active=1").fetchone()['c']
        sub_count = conn.execute("SELECT COUNT(*) as c FROM agent_matrix WHERE role_type='sub' AND is_active=1").fetchone()['c']

        total_tasks = conn.execute("SELECT COUNT(*) as c FROM agent_tasks").fetchone()['c']
        today = datetime.now().strftime('%Y-%m-%d')
        today_tasks = conn.execute(
            "SELECT COUNT(*) as c FROM agent_tasks WHERE created_at >= %s", (today,)
        ).fetchone()['c']
        completed = conn.execute(
            "SELECT COUNT(*) as c FROM agent_tasks WHERE status='completed'"
        ).fetchone()['c']
        failed = conn.execute(
            "SELECT COUNT(*) as c FROM agent_tasks WHERE status='failed'"
        ).fetchone()['c']
        running = conn.execute(
            "SELECT COUNT(*) as c FROM agent_tasks WHERE status='running'"
        ).fetchone()['c']
        pending = conn.execute(
            "SELECT COUNT(*) as c FROM agent_tasks WHERE status='pending'"
        ).fetchone()['c']

        success_rate = round(completed / total_tasks * 100, 1) if total_tasks > 0 else 100.0

        return {
            'agents': {
                'total': total_agents,
                'active': active_agents,
                'master': master_count,
                'sub': sub_count
            },
            'tasks': {
                'total': total_tasks,
                'today': today_tasks,
                'completed': completed,
                'failed': failed,
                'running': running,
                'pending': pending,
                'success_rate': success_rate
            }
        }


def get_recent_tasks(limit=10):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT t.*, s.name as source_name, tg.name as target_name
            FROM agent_tasks t
            LEFT JOIN agent_matrix s ON t.source_agent_id = s.id
            LEFT JOIN agent_matrix tg ON t.target_agent_id = tg.id
            ORDER BY t.created_at DESC
            LIMIT %s
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
