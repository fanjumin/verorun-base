#!/usr/bin/env python3
"""Captcha Embedded Plugin — 数据存储策略声明 + PostgreSQL schema 预留
（plugin-standard v1.4 §9.1 单库多 Schema / §11.2 数据隔离）

存储策略（2026-08-06 决策，审计 C4）：
  - 生产环境使用 Redis + 内存回退存储验证码临时状态（challenge token、IP 限流、
    IP 封禁、统计）。Redis 本身即持久化方案（RDB/AOF），对 TTL≤300s 的短生命周期
    验证码数据是合理选择，热路径（每次 generate/verify/consume）延迟远低于 PG。
  - 本文件提供 PostgreSQL schema `captcha_embedded` 的表定义与初始化入口
    （init_captcha_db）作为未来全量迁移 PG 的预留；当前 store.py 暂不读写 PG。
  - 如需切换为 PG，调用 init_captcha_db() 建表后，将 store.py 的读写改为本 schema。
"""
import threading

import psycopg2
import psycopg2.extras

from plugins._base.db import get_raw_connection

# 每线程独立连接（解决全局单连接在 gunicorn 多线程下非线程安全 / 连接泄漏问题）
_local = threading.local()


class _PgConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface."""
    def __init__(self, conn):
        self._conn = conn

    def _is_alive(self):
        """检测连接是否存活（gunicorn pre-fork 后连接可能已失效）"""
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True
        except Exception:
            return False

    def execute(self, sql, params=None):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_captcha_db():
    """获取验证码插件 PG 连接（schema: captcha_embedded，预留）

    gunicorn pre-fork 模式下连接可能失效，每次获取时检测存活，失效自动重建。
    连接按线程隔离，避免竞态与泄漏。
    """
    conn = getattr(_local, 'conn', None)
    if conn is not None and not conn._is_alive():
        try:
            conn.close()
        except Exception:
            pass
        conn = None
    if conn is None:
        raw = get_raw_connection()
        raw.autocommit = False
        raw.cursor().execute("CREATE SCHEMA IF NOT EXISTS captcha_embedded")
        raw.commit()
        raw.cursor().execute("SET search_path TO captcha_embedded")
        raw.commit()
        conn = _PgConnection(raw)
        _local.conn = conn
    return conn


def init_captcha_db():
    """初始化预留 schema 表（幂等；当前 store.py 仍走 Redis，表仅供未来迁移使用）"""
    conn = get_captcha_db()

    # ── 验证码挑战（token 一次性消费） ──
    conn.execute('''CREATE TABLE IF NOT EXISTS challenges (
        id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        token       TEXT NOT NULL UNIQUE,
        target_x    BIGINT NOT NULL,
        y_position  BIGINT NOT NULL DEFAULT 0,
        image_id    TEXT DEFAULT '',
        piece_w     BIGINT DEFAULT 0,
        piece_h     BIGINT DEFAULT 0,
        used        BIGINT DEFAULT 0,
        expire_at   TIMESTAMPTZ NOT NULL,
        created_at  TIMESTAMPTZ DEFAULT NOW()
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_challenges_expire ON challenges(expire_at)')

    # ── IP 限流窗口 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS rate_limits (
        id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        ip           TEXT NOT NULL UNIQUE,
        fail_count   BIGINT DEFAULT 0,
        window_start TIMESTAMPTZ DEFAULT NOW()
    )''')

    # ── IP 封禁记录 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ip_blocks (
        id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        ip         TEXT NOT NULL UNIQUE,
        blocked_at TIMESTAMPTZ DEFAULT NOW(),
        reason     TEXT DEFAULT ''
    )''')

    # ── 小时粒度统计 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS stats_hourly (
        id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        hour_key  TEXT NOT NULL UNIQUE,
        total     BIGINT DEFAULT 0,
        passed    BIGINT DEFAULT 0,
        risk_sum  DOUBLE PRECISION DEFAULT 0
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_stats_hourly_key ON stats_hourly(hour_key)')

    conn.commit()
    print('[CaptchaEmbedded] PG schema captcha_embedded initialized (reserved for migration)')


def migrate_captcha_db():
    """显式迁移入口（与 init_captcha_db 相同逻辑，供外部调用）"""
    init_captcha_db()
