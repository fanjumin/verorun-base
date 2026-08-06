#!/usr/bin/env python3
"""Enterprise Verification Plugin — 数据库模型（PG schema: enterprise_verify）"""
from plugins._base.db import PgConnection
from plugins._base.db import get_raw_connection
from plugin_manager.logger import get_plugin_logger

logger = get_plugin_logger('enterprise_verify')

_ev_conn = None


def get_ev_db():
    """获取企业认证插件独立数据库连接（PG schema: enterprise_verify）"""
    global _ev_conn
    if _ev_conn is None:
        raw = get_raw_connection()
        raw.autocommit = False
        _ev_conn = PgConnection(raw)
        _ev_conn.execute("CREATE SCHEMA IF NOT EXISTS enterprise_verify")
        _ev_conn.execute("SET search_path TO enterprise_verify")
        _ev_conn.commit()
    return _ev_conn


def init_ev_db():
    """初始化企业认证表（幂等）"""
    conn = get_ev_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS enterprise_verifications (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        user_id         BIGINT NOT NULL,
        enterprise_name TEXT NOT NULL,
        tax_id          TEXT NOT NULL,
        license_url     TEXT DEFAULT '',
        ocr_raw         TEXT DEFAULT '',
        status          TEXT NOT NULL DEFAULT 'pending',
        review_notes    TEXT DEFAULT '',
        reviewed_by     BIGINT,
        reviewed_at     TEXT,
        created_at      TEXT DEFAULT NOW(),
        updated_at      TEXT DEFAULT NOW()
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_user ON enterprise_verifications(user_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_status ON enterprise_verifications(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_status_created ON enterprise_verifications(status, created_at)')
    # §4: 插件本地 Agent 注册表（替代直接写主库 agent_matrix）
    conn.execute('''CREATE TABLE IF NOT EXISTS agent_registry (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name            TEXT NOT NULL,
        identifier      TEXT DEFAULT '',
        role_type       TEXT DEFAULT 'sub',
        description     TEXT DEFAULT '',
        domain          TEXT DEFAULT 'enterprise_verify',
        provider        TEXT DEFAULT '',
        model_name      TEXT DEFAULT '',
        system_prompt   TEXT DEFAULT '',
        capabilities    TEXT DEFAULT '[]',
        is_active       BIGINT DEFAULT 1,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ev_agent_registry_id ON agent_registry(identifier)')
    conn.commit()
    logger.info('enterprise_verify schema initialized')


def upsert_agent(name: str, role_type: str, description: str, domain: str,
                 provider: str, model_name: str, system_prompt: str,
                 capabilities: str, is_active: int = 1, identifier: str = ''):
    """注册或更新本地 Agent（幂等，§4）"""
    with get_ev_db() as conn:
        exists = conn.execute(
            'SELECT id FROM agent_registry WHERE name=%s AND role_type=%s',
            (name, role_type)
        ).fetchone()
        if exists:
            conn.execute('''
                UPDATE agent_registry
                SET description=%s, domain=%s, provider=%s, model_name=%s,
                    system_prompt=%s, capabilities=%s, is_active=%s,
                    identifier=%s, updated_at=NOW()
                WHERE id=%s
            ''', (description, domain, provider, model_name,
                  system_prompt, capabilities, is_active, identifier, exists['id']))
        else:
            conn.execute('''
                INSERT INTO agent_registry
                (name, identifier, role_type, description, domain, provider, model_name,
                 system_prompt, capabilities, is_active)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ''', (name, identifier, role_type, description, domain, provider, model_name,
                  system_prompt, capabilities, is_active))
        conn.commit()


def unregister_agents():
    """注销插件本地注册的所有 Agent（§4.2 禁用/卸载流程）"""
    with get_ev_db() as conn:
        conn.execute('DELETE FROM agent_registry')
        conn.commit()


def drop_ev_db():
    """卸载时清理独立 schema（§12.5 卸载零残留）"""
    global _ev_conn
    raw = get_raw_connection()
    try:
        cur = raw.cursor()
        cur.execute('DROP SCHEMA IF EXISTS enterprise_verify CASCADE')
        raw.commit()
        cur.close()
        logger.info('enterprise_verify schema dropped')
    finally:
        raw.close()
        _ev_conn = None
