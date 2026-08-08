#!/usr/bin/env python3
"""Platform user mapping — 联邦身份映射表数据层 (v2.1.0).

独立库 `mini_app` 中维护 平台身份 → 主库用户(user_id) 的映射，
插件不再直接访问主库 users 表。用户真正的账号由 auth-center 管理；
本插件仅记录「平台用户」对应的主库用户 ID，用于登录后签发共享 JWT。

表: platform_users.platform_user_mappings（独立库）
"""

from .db import get_db


TABLE_MAPPINGS = 'platform_users.platform_user_mappings'


def init_tables():
    """创建平台用户映射表（幂等，独立库）。"""
    with get_db() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS platform_users")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_MAPPINGS} (
                id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                platform         TEXT NOT NULL,
                platform_user_id TEXT NOT NULL,
                user_id          BIGINT NOT NULL,
                username         TEXT DEFAULT '',
                display_name     TEXT DEFAULT '',
                avatar           TEXT DEFAULT '',
                created_at       TIMESTAMP DEFAULT NOW(),
                last_login       TIMESTAMP DEFAULT NOW(),
                UNIQUE (platform, platform_user_id)
            )
        """)
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_platform_mapping_user
            ON {TABLE_MAPPINGS} (user_id)
        """)


def get_mapping(platform: str, platform_user_id: str):
    """按平台身份查询映射，返回 RealDictRow 或 None。"""
    with get_db() as conn:
        return conn.execute(
            f"SELECT * FROM {TABLE_MAPPINGS} WHERE platform=%s AND platform_user_id=%s",
            (platform, platform_user_id)
        ).fetchone()


def get_mapping_by_user(platform: str, user_id: int):
    """按主库用户查询其在某平台的映射（可能多条），返回列表。"""
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM {TABLE_MAPPINGS} WHERE platform=%s AND user_id=%s",
            (platform, user_id)
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_mapping(platform: str, platform_user_id: str, user_id: int,
                   username: str = '', display_name: str = '',
                   avatar: str = '') -> dict:
    """记录/更新平台身份 → 主库用户映射（幂等）。返回映射 dict。"""
    with get_db() as conn:
        conn.execute(f"""
            INSERT INTO {TABLE_MAPPINGS}
                (platform, platform_user_id, user_id, username, display_name, avatar)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (platform, platform_user_id)
            DO UPDATE SET
                user_id      = EXCLUDED.user_id,
                username     = EXCLUDED.username,
                display_name = EXCLUDED.display_name,
                avatar       = EXCLUDED.avatar,
                last_login   = NOW()
        """, (platform, platform_user_id, user_id, username, display_name, avatar))
        row = conn.execute(
            f"SELECT * FROM {TABLE_MAPPINGS} WHERE platform=%s AND platform_user_id=%s",
            (platform, platform_user_id)
        ).fetchone()
        return dict(row)


def touch_last_login(platform: str, platform_user_id: str):
    """更新最后登录时间（幂等）。"""
    try:
        with get_db() as conn:
            conn.execute(
                f"UPDATE {TABLE_MAPPINGS} SET last_login=NOW() "
                f"WHERE platform=%s AND platform_user_id=%s",
                (platform, platform_user_id)
            )
    except Exception:
        pass  # 登录统计失败不影响主流程


def get_total_mappings() -> int:
    """映射总数（用于 dashboard 统计）。"""
    try:
        with get_db() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {TABLE_MAPPINGS}").fetchone()
            return row['cnt'] if row else 0
    except Exception:
        return 0
