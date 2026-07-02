#!/usr/bin/env python3
"""
easykai-health — 数据库模型
============================
所有健康巡检相关的数据表。复用主库 (site.db)。

表结构:
  health_checks     — 检查项定义（注册了哪些检查、配置、启用/禁用）
  check_history     — 每次巡检的各检查项结果明细
  check_runs        — 每次巡检批次信息
  alert_config      — 告警规则配置
  alert_history     — 已发送的告警记录
  health_trend      — 每日聚合统计（用于趋势图）

@package easykai_health
"""

import os, json, time, sqlite3
from datetime import datetime, timedelta
from contextlib import contextmanager
from collections import defaultdict

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


def init_health_tables():
    """初始化所有健康巡检表（幂等：IF NOT EXISTS）"""
    with get_db() as conn:
        conn.executescript("""
            -- =============================================
            -- 1. 检查项定义表
            -- =============================================
            CREATE TABLE IF NOT EXISTS health_checks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,                    -- 检查项名称（如 "核心API检查"）
                check_key       TEXT NOT NULL UNIQUE,             -- 唯一键（如 "core_api"）
                category        TEXT NOT NULL DEFAULT 'system',   -- 分类: system/external/workflow/agent/cms/community/ssl/error
                description     TEXT DEFAULT '',                  -- 描述
                config          TEXT DEFAULT '{}',                -- JSON 配置（超时时间、URL等）
                is_active       INTEGER DEFAULT 1,                -- 是否启用
                severity        TEXT DEFAULT 'warning'            -- 告警级别: info/warning/critical
                    CHECK(severity IN ('info','warning','critical')),
                sort_order      INTEGER DEFAULT 0,                -- 排序
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            -- =============================================
            -- 2. 巡检批次表（每次触发巡检为一个批次）
            -- =============================================
            CREATE TABLE IF NOT EXISTS check_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_type    TEXT NOT NULL DEFAULT 'manual',   -- manual/scheduled/workflow
                trigger_info    TEXT DEFAULT '',                  -- 触发详情（如 cron job id）
                total_checks    INTEGER DEFAULT 0,                -- 总检查项数
                passed          INTEGER DEFAULT 0,                -- 通过数
                warnings        INTEGER DEFAULT 0,                -- 警告数
                errors          INTEGER DEFAULT 0,                -- 错误数
                duration_ms     INTEGER DEFAULT 0,                -- 总耗时(ms)
                status          TEXT DEFAULT 'completed'          -- completed/running/failed
                    CHECK(status IN ('running','completed','failed')),
                summary         TEXT DEFAULT '',                  -- 运行摘要
                created_at      TEXT DEFAULT (datetime('now'))
            );

            -- =============================================
            -- 3. 检查结果明细表
            -- =============================================
            CREATE TABLE IF NOT EXISTS check_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id          INTEGER NOT NULL,                 -- 关联 check_runs.id
                check_id        INTEGER NOT NULL,                 -- 关联 health_checks.id
                check_key       TEXT NOT NULL,                    -- 冗余，方便查询
                check_name      TEXT NOT NULL,                    -- 冗余
                category        TEXT NOT NULL,                    -- 冗余
                status          TEXT NOT NULL DEFAULT 'passed'    -- passed/warning/error
                    CHECK(status IN ('passed','warning','error')),
                response_time_ms INTEGER DEFAULT 0,               -- 响应时间(ms)
                message         TEXT DEFAULT '',                  -- 结果消息
                detail          TEXT DEFAULT '{}',                -- JSON 详情
                checked_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_check_history_run
                ON check_history(run_id);
            CREATE INDEX IF NOT EXISTS idx_check_history_key
                ON check_history(check_key);
            CREATE INDEX IF NOT EXISTS idx_check_history_time
                ON check_history(checked_at);

            -- =============================================
            -- 4. 告警规则配置表
            -- =============================================
            CREATE TABLE IF NOT EXISTS alert_config (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,                    -- 规则名称
                check_key       TEXT DEFAULT '*',                 -- 关联检查项（'*' 表示全部）
                severity        TEXT DEFAULT 'warning',           -- 触发级别: warning/critical
                consecutive     INTEGER DEFAULT 1,                -- 连续失败N次才告警
                notify_method   TEXT DEFAULT 'email',             -- email/站内信/webhook/全部
                webhook_url     TEXT DEFAULT '',                  -- Webhook URL
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            -- =============================================
            -- 5. 告警历史表
            -- =============================================
            CREATE TABLE IF NOT EXISTS alert_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_config_id INTEGER DEFAULT 0,
                check_key       TEXT NOT NULL,
                check_name      TEXT NOT NULL,
                run_id          INTEGER DEFAULT 0,
                status          TEXT NOT NULL,                    -- 触发时的状态
                message         TEXT DEFAULT '',
                notify_method   TEXT DEFAULT '',
                is_read         INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            -- =============================================
            -- 6. 每日健康趋势表
            -- =============================================
            CREATE TABLE IF NOT EXISTS health_trend (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT NOT NULL,                    -- '2026-05-10'
                total_checks    INTEGER DEFAULT 0,
                passed          INTEGER DEFAULT 0,
                warnings        INTEGER DEFAULT 0,
                errors          INTEGER DEFAULT 0,
                avg_response_ms INTEGER DEFAULT 0,
                health_score    REAL DEFAULT 100.0,              -- 健康分 0-100
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_health_trend_date
                ON health_trend(date);
        """)
        print(f'[HealthCheck] ✅ 数据库表已初始化')


# ─── 种子数据：注册默认检查项 ───────────────────────────────────────────────

DEFAULT_CHECKS = [
    # (check_key, name, category, description, config, severity, sort)
    ('core_api',       '核心API检查',      'system',    '所有子站 API 健康端点检查',    '{"timeout":5,"endpoints":["/health","/admin/dashboard"]}', 'warning', 10),
    ('database',       '数据库连接检查',    'system',    'SQLite/PostgreSQL 连接状态',   '{"timeout":3}',                                    'critical', 20),
    ('redis',          'Redis缓存检查',     'system',    'Redis 缓存服务连接状态',       '{"timeout":3}',                                    'warning', 25),
    ('server_resources','服务器资源检查',   'system',    'CPU/内存/磁盘使用率',          '{"cpu_threshold":90,"mem_threshold":85,"disk_threshold":85,"timeout":10}', 'warning', 30),
    ('external_apis',  '外部依赖API检查',   'external',  '股票行情/AI接口/支付等依赖',    '{"timeout":10,"endpoints":["https://httpbin.org/get"]}', 'warning', 40),
    ('ssl_cert',       'SSL证书检查',      'ssl',       '各子域名 SSL 证书到期时间',     '{"domains":[],"expire_warn_days":30}', 'warning', 50),
    ('workflow_engine','工作流引擎检查',    'workflow',  'Cron/Workflow 调度器运行状态',  '{"timeout":5}',                                    'warning', 60),
    ('agent_matrix',   'Agent矩阵检查',    'agent',     '主Agent + 子Agent在线状态',     '{"timeout":10}',                                   'warning', 70),
    ('content_factory','内容工厂检查',      'cms',       '采集通道/加工队列状态',         '{"timeout":5}',                                    'warning', 80),
    ('sse_ws',         'SSE/WS连接检查',    'system',    'SSE推送/WebSocket连接状态',    '{"timeout":5}',                                    'warning', 95),
    ('error_logs',     '错误日志统计',      'error',     '最近24小时错误日志统计',        '{"hours":24,"threshold":50}',                      'warning', 100),
]


def seed_default_checks():
    """初始化默认检查项（仅当表为空时）"""
    with get_db() as conn:
        count = conn.execute('SELECT COUNT(*) as c FROM health_checks').fetchone()['c']
        if count > 0:
            return
        for ck, name, cat, desc, cfg, sev, sort in DEFAULT_CHECKS:
            conn.execute(
                'INSERT INTO health_checks (check_key, name, category, description, config, severity, sort_order) '
                'VALUES (?,?,?,?,?,?,?)',
                (ck, name, cat, desc, cfg, sev, sort)
            )
        conn.commit()
        print(f'[HealthCheck] ✅ 已注册 {len(DEFAULT_CHECKS)} 个默认检查项')


# ─── 查询辅助 ──────────────────────────────────────────────────────────────

def get_active_checks():
    """获取所有启用的检查项"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM health_checks WHERE is_active=1 ORDER BY sort_order'
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_runs(limit=20):
    """获取最近的巡检批次"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM check_runs ORDER BY created_at DESC LIMIT ?',
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_history_for_run(run_id):
    """获取某次巡检的详细结果"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM check_history WHERE run_id=? ORDER BY id',
            (run_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_status():
    """获取最近一次已完成巡检的状态统计"""
    with get_db() as conn:
        run = conn.execute(
            "SELECT * FROM check_runs WHERE status='completed' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not run:
            return None
        run = dict(run)
        history = conn.execute(
            'SELECT * FROM check_history WHERE run_id=? ORDER BY category, id',
            (run['id'],)
        ).fetchall()
        run['items'] = [dict(h) for h in history]
        return run


def get_health_trend(days=7):
    """获取最近 N 天的健康趋势"""
    with get_db() as conn:
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        rows = conn.execute(
            'SELECT * FROM health_trend WHERE date>=? ORDER BY date',
            (since,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_alerts(limit=50):
    """获取告警历史"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM alert_history ORDER BY created_at DESC LIMIT ?',
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_unread_alert_count():
    with get_db() as conn:
        r = conn.execute(
            "SELECT COUNT(*) as c FROM alert_history WHERE is_read=0"
        ).fetchone()
    return r['c'] if r else 0
