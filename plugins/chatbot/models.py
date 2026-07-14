#!/usr/bin/env python3
"""
AI Advisor (Chatbot) Plugin — 独立数据库模型
============================================
- plugin_configs: 插件配置（替代主库 plugin_configs）
- agent_registry: 本地 Agent 注册（替代主库 agent_matrix 写入）
- chatbot_sessions: 对话统计/日志（替代主库 chatbot_sessions）
"""
import sqlite3
import os

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_PLUGIN_DIR, 'data')
_DB_PATH = os.path.join(_DATA_DIR, 'chatbot.db')
os.makedirs(_DATA_DIR, exist_ok=True)

_chatbot_conn = None


def get_chatbot_db():
    """获取插件独立数据库连接（单例）"""
    global _chatbot_conn
    if _chatbot_conn is None:
        _chatbot_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _chatbot_conn.row_factory = sqlite3.Row
        _chatbot_conn.execute("PRAGMA journal_mode=WAL")
        _chatbot_conn.execute("PRAGMA busy_timeout=5000")
    return _chatbot_conn


def init_chatbot_tables():
    """创建所有 chatbot 插件表（幂等）"""
    conn = get_chatbot_db()

    # 1. 插件配置表
    conn.execute('''CREATE TABLE IF NOT EXISTS plugin_configs (
        plugin_name TEXT NOT NULL,
        key         TEXT NOT NULL,
        value       TEXT DEFAULT '',
        updated_at  TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (plugin_name, key)
    )''')

    # 2. Agent 注册表（本地，替代主库 agent_matrix 写入）
    conn.execute('''CREATE TABLE IF NOT EXISTS agent_registry (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        role_type       TEXT DEFAULT 'sub',
        description     TEXT DEFAULT '',
        domain          TEXT DEFAULT 'chatbot',
        provider        TEXT DEFAULT 'dashscope',
        model_name      TEXT DEFAULT 'qwen-turbo',
        system_prompt   TEXT DEFAULT '',
        capabilities    TEXT DEFAULT '[]',
        is_active       INTEGER DEFAULT 1,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )''')

    # 3. 对话会话日志表
    conn.execute('''CREATE TABLE IF NOT EXISTS chatbot_sessions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL,
        user_query  TEXT DEFAULT '',
        ai_reply    TEXT DEFAULT '',
        escalated   INTEGER DEFAULT 0,
        csat_score  INTEGER DEFAULT 0,
        source      TEXT DEFAULT 'chatbot',
        intent      TEXT DEFAULT '',
        sentiment   TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_cs_created ON chatbot_sessions(created_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_cs_session ON chatbot_sessions(session_id)')

    conn.commit()
    print(f'[ChatbotPlugin] 独立数据库已就绪（{_DB_PATH}）')


# ── 配置读写 ──

def get_config(plugin_name: str, key: str, default=''):
    """读取单条配置"""
    conn = get_chatbot_db()
    r = conn.execute(
        'SELECT value FROM plugin_configs WHERE plugin_name=? AND key=?',
        (plugin_name, key)
    ).fetchone()
    return r['value'] if r else default


def set_config(plugin_name: str, key: str, value: str):
    """保存单条配置"""
    conn = get_chatbot_db()
    conn.execute('''
        INSERT INTO plugin_configs (plugin_name, key, value, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(plugin_name, key) DO UPDATE SET
            value=excluded.value,
            updated_at=datetime('now')
    ''', (plugin_name, key, str(value)))
    conn.commit()


def get_all_configs(plugin_name: str) -> dict:
    """读取某插件全部配置"""
    conn = get_chatbot_db()
    rows = conn.execute(
        'SELECT key, value FROM plugin_configs WHERE plugin_name=?',
        (plugin_name,)
    ).fetchall()
    return {r['key']: r['value'] for r in rows}


def seed_defaults(plugin_name: str, defaults: dict):
    """仅当 DB 中无该配置行时写入默认值"""
    conn = get_chatbot_db()
    existing_keys = {
        r['key'] for r in conn.execute(
            'SELECT key FROM plugin_configs WHERE plugin_name=?',
            (plugin_name,)
        ).fetchall()
    }
    for key, value in defaults.items():
        if key not in existing_keys:
            set_config(plugin_name, key, str(value))


# ── Agent 注册 ──

def upsert_agent(name: str, role_type: str, description: str, domain: str,
                 provider: str, model_name: str, system_prompt: str,
                 capabilities: str, is_active: int = 1):
    """注册或更新 Agent"""
    conn = get_chatbot_db()
    exists = conn.execute(
        'SELECT id FROM agent_registry WHERE name=? AND role_type=?',
        (name, role_type)
    ).fetchone()
    if exists:
        conn.execute('''
            UPDATE agent_registry
            SET description=?, domain=?, provider=?, model_name=?,
                system_prompt=?, capabilities=?, is_active=?,
                updated_at=datetime('now')
            WHERE id=?
        ''', (description, domain, provider, model_name,
              system_prompt, capabilities, is_active, exists['id']))
    else:
        conn.execute('''
            INSERT INTO agent_registry
            (name, role_type, description, domain, provider, model_name,
             system_prompt, capabilities, is_active)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', (name, role_type, description, domain, provider, model_name,
              system_prompt, capabilities, is_active))
    conn.commit()


def get_agent(agent_id: str):
    """按 name 或 identifier 查询 Agent"""
    conn = get_chatbot_db()
    row = conn.execute(
        'SELECT * FROM agent_registry WHERE (name=? OR name=?) AND is_active=1 LIMIT 1',
        (agent_id, agent_id)
    ).fetchone()
    return dict(row) if row else None


# ── 从主库迁移已有数据（幂等，首次运行自动执行） ──

def migrate_from_main():
    """从主库迁移 plugin_configs 和 chatbot_sessions 到独立库（幂等）"""
    try:
        import sys as _s, os as _o
        _s.path.insert(0, _o.path.join(_o.path.dirname(__file__), '..', '..', 'auth-center'))
        from models import get_db as get_main_db

        with get_main_db() as mc:
            # 迁移 plugin_configs
            rows = mc.execute(
                "SELECT key, value FROM plugin_configs WHERE plugin_name='chatbot'"
            ).fetchall()
            if rows:
                for r in rows:
                    set_config('chatbot', r['key'], r['value'])
                print(f'[ChatbotPlugin] 已迁移 {len(rows)} 条 plugin_configs')

            # 迁移 agent（仅迁移 chatbot 相关的 agent_matrix 记录）
            agent_rows = mc.execute(
                "SELECT * FROM agent_matrix WHERE domain='chatbot' OR managed_modules LIKE '%chatbot%'"
            ).fetchall()
            if agent_rows:
                for r in agent_rows:
                    upsert_agent(
                        name=r['name'], role_type=r.get('role_type', 'sub'),
                        description=r.get('description', ''), domain=r.get('domain', 'chatbot'),
                        provider=r.get('provider', 'dashscope'), model_name=r.get('model_name', 'qwen-turbo'),
                        system_prompt=r.get('system_prompt', ''),
                        capabilities=r.get('capabilities', '[]'),
                        is_active=r.get('is_active', 1)
                    )
                print(f'[ChatbotPlugin] 已迁移 {len(agent_rows)} 条 agent_registry')

            # 迁移 chatbot_sessions（仅最近 30 天）
            session_rows = mc.execute(
                "SELECT * FROM chatbot_sessions WHERE created_at >= datetime('now', '-30 days')"
            ).fetchall()
            if session_rows:
                conn = get_chatbot_db()
                for r in session_rows:
                    conn.execute(
                        '''INSERT OR IGNORE INTO chatbot_sessions
                           (session_id, user_query, ai_reply, escalated, csat_score,
                            source, intent, sentiment, created_at)
                           VALUES (?,?,?,?,?,?,?,?,?)''',
                        (r['session_id'], r.get('user_query', ''), r.get('ai_reply', ''),
                         r.get('escalated', 0), r.get('csat_score', 0),
                         r.get('source', 'chatbot'), r.get('intent', ''),
                         r.get('sentiment', ''), r.get('created_at', ''))
                    )
                conn.commit()
                print(f'[ChatbotPlugin] 已迁移 {len(session_rows)} 条 chatbot_sessions')
    except Exception as e:
        print(f'[ChatbotPlugin] 迁移主库数据失败（首次运行正常）: {e}')