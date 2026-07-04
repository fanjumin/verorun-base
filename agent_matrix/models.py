#!/usr/bin/env python3
"""
Agent Matrix — 数据库模型
======================
4 张新表 + CRUD 操作 + 种子数据。
复用 auth-center/models/database.py 的 get_db() 模式。
"""
import json, os, sys
import sqlite3
from datetime import datetime
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
DB_PATH = os.environ.get('DB_PATH', os.path.join(DATA_DIR, 'x7k2m9a4.db'))
os.makedirs(DATA_DIR, exist_ok=True)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
    finally:
        conn.close()


# ============================================================
# Task ID 生成器
# ============================================================
_task_counter = 0  # Will be overridden by _init_task_counter()

def _init_task_counter():
    """Initialize task counter from DB to avoid UNIQUE constraint violations on restart."""
    global _task_counter
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT MAX(CAST(SUBSTR(task_id, -4) AS INTEGER)) AS max_id FROM agent_tasks "
                "WHERE task_id LIKE 'AT-' || strftime('%Y%m%d', 'now') || '-%'"
            ).fetchone()
            _task_counter = row['max_id'] if row and row['max_id'] else 0
    except Exception:
        _task_counter = 0

_init_task_counter()

def _next_task_id():
    global _task_counter
    _task_counter += 1
    date = datetime.now().strftime('%Y%m%d')
    return f'AT-{date}-{_task_counter:04d}'


def _next_session_id():
    date = datetime.now().strftime('%Y%m%d')
    import random
    suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    return f'SESSION-{date}-{suffix}'


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
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                role_type       TEXT NOT NULL DEFAULT 'sub'
                                CHECK(role_type IN ('master','sub')),
                description     TEXT DEFAULT '',
                domain          TEXT NOT NULL DEFAULT 'general',
                managed_modules TEXT DEFAULT '[]',
                provider        TEXT NOT NULL DEFAULT 'dashscope',
                model_name      TEXT NOT NULL DEFAULT 'qwen-turbo',
                api_key_ref     TEXT DEFAULT 'dashscope_text_key',
                base_url        TEXT DEFAULT '',
                model_provider_id INTEGER DEFAULT NULL,  -- deprecated
                provider_model_id INTEGER DEFAULT NULL,
                system_prompt   TEXT DEFAULT '',
                role_prompt     TEXT DEFAULT '',
                task_template   TEXT DEFAULT '',
                capabilities    TEXT DEFAULT '[]',
                allowed_tools   TEXT DEFAULT '[]',
                max_concurrency INTEGER DEFAULT 1,
                priority        INTEGER DEFAULT 5,
                auto_approve    INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                tasks_total     INTEGER DEFAULT 0,
                tasks_success   INTEGER DEFAULT 0,
                tasks_failed    INTEGER DEFAULT 0,
                last_run_at     TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now')),
                UNIQUE(name, role_type)
            );

            -- ================================================
            -- 2. 任务调度表
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id         TEXT UNIQUE NOT NULL,
                parent_task_id  TEXT DEFAULT NULL,
                master_task_id  TEXT DEFAULT NULL,
                source_agent_id INTEGER NOT NULL,
                target_agent_id INTEGER NOT NULL,
                task_type       TEXT NOT NULL DEFAULT 'execute'
                                CHECK(task_type IN ('execute','review','approve','composite','cron')),
                title           TEXT NOT NULL,
                description     TEXT DEFAULT '',
                input_data      TEXT DEFAULT '{}',
                expected_output TEXT DEFAULT '{}',
                target_module   TEXT DEFAULT '',
                target_api      TEXT DEFAULT '',
                priority        INTEGER DEFAULT 5,
                max_retries     INTEGER DEFAULT 3,
                retry_count     INTEGER DEFAULT 0,
                timeout_seconds INTEGER DEFAULT 300,
                status          TEXT NOT NULL DEFAULT 'pending'
                                CHECK(status IN ('pending','running','completed','failed',
                                                 'cancelled','needs_review','retrying')),
                result_data     TEXT DEFAULT '{}',
                confidence      REAL DEFAULT 0.0,
                error_message   TEXT DEFAULT '',
                self_review     TEXT DEFAULT '',
                cross_review    TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
                started_at      TEXT DEFAULT '',
                completed_at    TEXT DEFAULT '',
                updated_at      TEXT DEFAULT (datetime('now'))
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
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id         TEXT NOT NULL,
                agent_id        INTEGER NOT NULL,
                log_level       TEXT NOT NULL DEFAULT 'info'
                                CHECK(log_level IN ('debug','info','warn','error')),
                log_type        TEXT NOT NULL DEFAULT 'execution'
                                CHECK(log_type IN ('execution','self_review','cross_review','approval','api_call')),
                message         TEXT NOT NULL,
                metadata        TEXT DEFAULT '{}',
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_tl_task ON task_logs(task_id);
            CREATE INDEX IF NOT EXISTS idx_tl_type ON task_logs(log_type);

            -- ================================================
            -- 4. 对话记录表
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_conversations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                master_task_id  TEXT DEFAULT '',
                session_id      TEXT NOT NULL,
                role            TEXT NOT NULL CHECK(role IN ('user','master','sub','system')),
                agent_id        INTEGER DEFAULT NULL,
                agent_name      TEXT DEFAULT '',
                content         TEXT NOT NULL,
                metadata        TEXT DEFAULT '{}',
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_ac_session ON agent_conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_ac_task ON agent_conversations(master_task_id);

            -- ================================================
            -- 5. Token 消耗日志表 (2026-05-16)
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_token_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id        INTEGER NOT NULL,
                agent_name      TEXT DEFAULT '',
                model_name      TEXT DEFAULT '',
                provider        TEXT DEFAULT '',
                prompt_tokens   INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens    INTEGER DEFAULT 0,
                call_type       TEXT DEFAULT 'chat',
                dimension       TEXT DEFAULT 'text',
                user_id         INTEGER DEFAULT NULL,
                task_id         TEXT DEFAULT '',
                session_id      TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_tkl_agent_id   ON agent_token_logs(agent_id);
            CREATE INDEX IF NOT EXISTS idx_tkl_created_at ON agent_token_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_tkl_date       ON agent_token_logs(date(created_at));
            CREATE INDEX IF NOT EXISTS idx_tkl_agent_date ON agent_token_logs(agent_id, date(created_at));

            -- ================================================
            -- 6. Token 每日汇总表 (2026-05-16)
            -- ================================================
            CREATE TABLE IF NOT EXISTS agent_token_daily (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id        INTEGER NOT NULL,
                agent_name      TEXT DEFAULT '',
                stat_date       TEXT NOT NULL DEFAULT (date('now')),
                prompt_tokens   INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens    INTEGER DEFAULT 0,
                call_count      INTEGER DEFAULT 0,
                updated_at      TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(agent_id, stat_date)
            );

            CREATE INDEX IF NOT EXISTS idx_tkd_date ON agent_token_daily(stat_date);
        """)
        conn.commit()

    # 会话标题字段 (v2 迁移) — 单独执行，不能放 executescript 内
    with get_db() as conn:
        cols = [r['name'] for r in conn.execute("PRAGMA table_info(agent_conversations)").fetchall()]
        if 'session_name' not in cols:
            conn.execute("ALTER TABLE agent_conversations ADD COLUMN session_name TEXT DEFAULT ''")
            conn.commit()

    # ── Migration: add provider_model_id to agent_matrix ──
    with get_db() as conn:
        cols = [r['name'] for r in conn.execute("PRAGMA table_info(agent_matrix)").fetchall()]
        if 'provider_model_id' not in cols:
            conn.execute("ALTER TABLE agent_matrix ADD COLUMN provider_model_id INTEGER DEFAULT NULL")
            conn.commit()
            print('[Migration] Added agent_matrix.provider_model_id')
        # Migrate old model_provider_id → provider_model_id
        rows = conn.execute(
            "SELECT id, model_provider_id FROM agent_matrix WHERE provider_model_id IS NULL AND model_provider_id IS NOT NULL"
        ).fetchall()
        for a in rows:
            conn.execute("UPDATE agent_matrix SET provider_model_id=? WHERE id=?",
                         (a['model_provider_id'], a['id']))
        if rows:
            conn.commit()
            print(f'[Migration] Migrated {len(rows)} agent_matrix rows model_provider_id→provider_model_id')

    # ── Migration: add dimension to agent_token_logs ──
    with get_db() as conn:
        cols = [r['name'] for r in conn.execute("PRAGMA table_info(agent_token_logs)").fetchall()]
        if 'dimension' not in cols:
            conn.execute("ALTER TABLE agent_token_logs ADD COLUMN dimension TEXT DEFAULT 'text'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tkl_dimension ON agent_token_logs(dimension)")
            conn.commit()
            print('[Migration] Added agent_token_logs.dimension')


# ============================================================
# Seed 数据
# ============================================================

DEFAULT_AGENTS = [
    {
        "name": "Athena", "role_type": "master",
        "description": "主 Agent / Coordinator — 任务分解、协调、汇总报告",
        "domain": "orchestration",
        "managed_modules": '["all"]',
        "provider": "openai", "model_name": "gpt-4o",
        "system_prompt": "prompts/master_prompt.md",
        "auto_approve": 0, "is_active": 1
    },
    {
        "name": "CMS Agent", "role_type": "sub",
        "description": "内容管理专家 — CMS文章、评论审核、内容工厂",
        "domain": "cms",
        "managed_modules": '["cms","comments","contentfactory"]',
        "system_prompt": "prompts/sub_cms_prompt.md",
        "is_active": 1
    },
    {
        "name": "Finance Agent", "role_type": "sub",
        "description": "财务专家 — 套餐、订阅、订单、优惠券、收入、扣款",
        "domain": "finance",
        "managed_modules": '["plans","subscriptions","sub_orders","coupons","sub_stats","sub_events"]',
        "system_prompt": "prompts/sub_finance_prompt.md",
        "is_active": 1
    },
    {
        "name": "User System Agent", "role_type": "sub",
        "description": "用户与系统管理专家 — 用户、Agent、API Key、设置、日志",
        "domain": "system",
        "managed_modules": '["users","agents","keys","config","logs"]',
        "system_prompt": "prompts/sub_user_prompt.md",
        "is_active": 1
    },
    {
        "name": "Automation Agent", "role_type": "sub",
        "description": "自动化专家 — Cron任务、Workflow、DAG编排",
        "domain": "automation",
        "managed_modules": '["automation"]',
        "system_prompt": "prompts/sub_automation_prompt.md",
        "is_active": 1
    },
    {
        "name": "Analytics Agent", "role_type": "sub",
        "description": "数据分析师 — 统计分析、数据解读、报告生成",
        "domain": "analytics",
        "managed_modules": '["analytics"]',
        "system_prompt": "prompts/sub_analytics_prompt.md",
        "is_active": 1
    },
    {
        "name": "Ticket Agent", "role_type": "sub",
        "description": "客服专家 — 工单处理、AI客服",
        "domain": "support",
        "managed_modules": '["contacts"]',
        "system_prompt": "prompts/sub_ticket_prompt.md",
        "is_active": 1
    },
    {
        "name": "Kai Assistant", "role_type": "sub",
        "description": "智能客服机器人 — 全站FAQ问答、人工转接、工单创建、飞书通知",
        "domain": "chatbot",
        "managed_modules": '["chatbot","contacts"]',
        "provider": "deepseek", "model_name": "deepseek-chat",
        "system_prompt": "prompts/sub_chatbot_prompt.md",
        "is_active": 1
    },
    {
        "name": "Voice Agent", "role_type": "sub",
        "description": "语音合成专家 — 声音克隆、TTS 文字转语音",
        "domain": "voice",
        "managed_modules": '["voice","tts"]',
        "provider": "volcengine", "model_name": "volc-voice-clone-v2",
        "system_prompt": "prompts/sub_voice_prompt.md",
        "is_active": 1
    },
    {
        "name": "Video Agent", "role_type": "sub",
        "description": "数字人视频专家 — 照片驱动口播视频、抖音发布",
        "domain": "video",
        "managed_modules": '["video","avatar"]',
        "provider": "volcengine", "model_name": "volc-avatar-v3",
        "system_prompt": "prompts/sub_video_prompt.md",
        "is_active": 1
    },
    {
        "name": "Image Agent", "role_type": "sub",
        "description": "图像生成专家 — AI 配图、封面图、社媒素材",
        "domain": "image",
        "managed_modules": '["image","cover"]',
        "provider": "dashscope", "model_name": "wan2.7-image",
        "system_prompt": "prompts/sub_image_prompt.md",
        "is_active": 1
    },
    {
        "name": "Shop Agent", "role_type": "sub",
        "description": "商城运营专家 — 商品管理、分类、SKU、订单、优惠券、AI 优化",
        "domain": "shop",
        "managed_modules": '["products","categories","skus","orders","coupons","cleaner"]',
        "system_prompt": "prompts/sub_shop_prompt.md",
        "is_active": 1
    },
    {
        "name": "Health Check Agent", "role_type": "sub",
        "description": "系统健康监控专家 — 服务监控、异常诊断、告警、修复建议",
        "domain": "health_check",
        "managed_modules": '["health_check","monitor","alerter"]',
        "system_prompt": "prompts/sub_health_check_prompt.md",
        "is_active": 1
    }
]


def seed_default_agents():
    """插入默认 Agent（幂等：已存在则跳过）"""
    with get_db() as conn:
        for a in DEFAULT_AGENTS:
            exists = conn.execute(
                "SELECT id FROM agent_matrix WHERE name=? AND role_type=?",
                (a['name'], a['role_type'])
            ).fetchone()
            if not exists:
                conn.execute("""
                    INSERT INTO agent_matrix
                    (name, role_type, description, domain, managed_modules,
                     provider, model_name, system_prompt, auto_approve, is_active)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    a['name'], a['role_type'], a['description'],
                    a['domain'], a.get('managed_modules', '[]'),
                    a.get('provider', 'dashscope'), a.get('model_name', 'qwen-turbo'),
                    a.get('system_prompt', ''), a.get('auto_approve', 0),
                    a.get('is_active', 1)
                ))
        conn.commit()


# ============================================================
# Agent CRUD
# ============================================================

def list_agents(role_type=None, domain=None, active_only=False):
    """列出 Agent，支持筛选"""
    with get_db() as conn:
        sql = "SELECT * FROM agent_matrix WHERE 1=1"
        params = []
        if role_type:
            sql += " AND role_type=?"
            params.append(role_type)
        if domain:
            sql += " AND domain=?"
            params.append(domain)
        if active_only:
            sql += " AND is_active=1"
        sql += " ORDER BY priority DESC, created_at ASC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_agent(agent_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM agent_matrix WHERE id=?", (agent_id,)).fetchone()
        return dict(row) if row else None


def get_agent_by_name(name, role_type='sub'):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM agent_matrix WHERE name=? AND role_type=?",
            (name, role_type)
        ).fetchone()
        return dict(row) if row else None


def create_agent(data):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO agent_matrix
            (name, role_type, description, domain, managed_modules,
             provider, model_name, api_key_ref, base_url, model_provider_id,
             system_prompt, role_prompt, task_template,
             capabilities, allowed_tools,
             max_concurrency, priority, auto_approve, is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            data.get('provider_model_id') or data.get('model_provider_id'),
            data.get('system_prompt', ''),
            data.get('role_prompt', ''),
            data.get('task_template', ''),
            json.dumps(data.get('capabilities', [])),
            json.dumps(data.get('allowed_tools', [])),
            data.get('max_concurrency', 1),
            data.get('priority', 5),
            data.get('auto_approve', 0),
            data.get('is_active', 1)
        ))
        conn.commit()
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_agent(agent_id, data):
    with get_db() as conn:
        fields = []
        values = []
        for key in ['name', 'role_type', 'description', 'domain',
                     'provider', 'model_name', 'api_key_ref', 'base_url', 'model_provider_id', 'provider_model_id',
                     'system_prompt', 'role_prompt', 'task_template',
                     'max_concurrency', 'priority', 'auto_approve', 'is_active']:
            if key in data:
                fields.append(f"{key}=?")
                values.append(data[key])
        for key in ['managed_modules', 'capabilities', 'allowed_tools']:
            if key in data:
                fields.append(f"{key}=?")
                values.append(json.dumps(data[key]) if isinstance(data[key], list) else data[key])
        if not fields:
            return False
        fields.append("updated_at=datetime('now')")
        values.append(agent_id)
        conn.execute(
            f"UPDATE agent_matrix SET {','.join(fields)} WHERE id=?",
            values
        )
        conn.commit()
        return True


def delete_agent(agent_id):
    with get_db() as conn:
        conn.execute("DELETE FROM agent_matrix WHERE id=?", (agent_id,))
        conn.commit()


def toggle_agent(agent_id):
    """切换启用/禁用状态"""
    with get_db() as conn:
        row = conn.execute("SELECT is_active FROM agent_matrix WHERE id=?", (agent_id,)).fetchone()
        if not row:
            return None
        new = 0 if row['is_active'] else 1
        conn.execute("UPDATE agent_matrix SET is_active=?, updated_at=datetime('now') WHERE id=?", (new, agent_id))
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
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
        row = conn.execute("SELECT * FROM agent_tasks WHERE task_id=?", (task_id,)).fetchone()
        return dict(row) if row else None


def list_tasks(status=None, module=None, agent_id=None, limit=50):
    with get_db() as conn:
        sql = "SELECT * FROM agent_tasks WHERE 1=1"
        params = []
        if status:
            sql += " AND status=?"
            params.append(status)
        if module:
            sql += " AND target_module=?"
            params.append(module)
        if agent_id:
            sql += " AND (source_agent_id=? OR target_agent_id=?)"
            params.extend([agent_id, agent_id])
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def update_task_status(task_id, status, result_data=None, confidence=None,
                       error_message=None, self_review=None):
    with get_db() as conn:
        fields = ["status=?", "updated_at=datetime('now')"]
        values = [status]
        if result_data is not None:
            fields.append("result_data=?")
            values.append(json.dumps(result_data) if not isinstance(result_data, str) else result_data)
        if confidence is not None:
            fields.append("confidence=?")
            values.append(confidence)
        if error_message is not None:
            fields.append("error_message=?")
            values.append(error_message)
        if self_review is not None:
            fields.append("self_review=?")
            values.append(self_review)
        if status == 'running':
            fields.append("started_at=datetime('now')")
        if status in ('completed', 'failed', 'cancelled'):
            fields.append("completed_at=datetime('now')")
        values.append(task_id)
        conn.execute(
            f"UPDATE agent_tasks SET {','.join(fields)} WHERE task_id=?",
            values
        )
        conn.commit()


def get_sub_tasks(master_task_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_tasks WHERE master_task_id=? ORDER BY created_at ASC",
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
            VALUES (?,?,?,?,?,?)
        """, (task_id, agent_id, level, log_type, message,
              json.dumps(metadata or {})))
        conn.commit()


def get_task_logs(task_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM task_logs WHERE task_id=? ORDER BY created_at ASC",
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
            VALUES (?,?,?,?,?,?,?)
        """, (session_id, role, agent_id, agent_name, content,
              master_task_id, json.dumps(metadata or {})))
        # 第一条用户消息设为会话标题
        if role == 'user':
            existing = conn.execute(
                "SELECT COUNT(*) as c FROM agent_conversations WHERE session_id=? AND role='user'",
                (session_id,)
            ).fetchone()['c']
            if existing == 1:
                title = content.strip()[:40]
                conn.execute(
                    "UPDATE agent_conversations SET session_name=? WHERE session_id=?",
                    (title, session_id)
                )
        conn.commit()


def get_conversation(session_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_conversations WHERE session_id=? ORDER BY created_at ASC",
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
            LIMIT ?
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
            WHERE content LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (like, limit)).fetchall()
        return [dict(r) for r in rows]


def batch_delete_sessions(session_ids):
    """批量删除指定会话的所有消息"""
    if not session_ids:
        return 0
    with get_db() as conn:
        placeholders = ','.join('?' * len(session_ids))
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
                last_run_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
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
            "SELECT COUNT(*) as c FROM agent_tasks WHERE created_at >= ?", (today,)
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
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
