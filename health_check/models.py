#!/usr/bin/env python3
"""
Health Check — Database Models
============================
All health check related database tables. Reuses the main database (site.db).

Table structure:
  health_checks     — Check item definitions (registered checks, configuration, enable/disable)
  check_history     — Detailed results of each check item per inspection run
  check_runs        — Batch information for each inspection run
  alert_config      — Alert rule configuration
  alert_history     — Sent alert records
  health_trend      — Daily aggregated statistics (for trend charts)

@package health_monitor
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
    """Initialize all health check tables (idempotent: IF NOT EXISTS)"""
    with get_db() as conn:
        conn.executescript("""
            -- =============================================
            -- 1. Check item definition table
            -- =============================================
            CREATE TABLE IF NOT EXISTS health_checks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,                    -- Check item name (e.g. "Core API Check")
                check_key       TEXT NOT NULL UNIQUE,             -- Unique key (e.g. "core_api")
                category        TEXT NOT NULL DEFAULT 'system',   -- Category: system/external/workflow/agent/cms/community/ssl/error
                description     TEXT DEFAULT '',                  -- Description
                config          TEXT DEFAULT '{}',                -- JSON config (timeout, URLs, etc.)
                is_active       INTEGER DEFAULT 1,                -- Whether enabled
                severity        TEXT DEFAULT 'warning'            -- Severity level: info/warning/critical
                    CHECK(severity IN ('info','warning','critical')),
                sort_order      INTEGER DEFAULT 0,                -- Sort order
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            -- =============================================
            -- 2. Check run table (each triggered inspection is one batch)
            -- =============================================
            CREATE TABLE IF NOT EXISTS check_runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_type    TEXT NOT NULL DEFAULT 'manual',   -- manual/scheduled/workflow
                trigger_info    TEXT DEFAULT '',                  -- Trigger details (e.g. cron job id)
                total_checks    INTEGER DEFAULT 0,                -- Total check items
                passed          INTEGER DEFAULT 0,                -- Passed count
                warnings        INTEGER DEFAULT 0,                -- Warning count
                errors          INTEGER DEFAULT 0,                -- Error count
                duration_ms     INTEGER DEFAULT 0,                -- Total duration (ms)
                status          TEXT DEFAULT 'completed'          -- completed/running/failed
                    CHECK(status IN ('running','completed','failed')),
                summary         TEXT DEFAULT '',                  -- Run summary
                created_at      TEXT DEFAULT (datetime('now'))
            );

            -- =============================================
            -- 3. Check history/details table
            -- =============================================
            CREATE TABLE IF NOT EXISTS check_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id          INTEGER NOT NULL,                 -- References check_runs.id
                check_id        INTEGER NOT NULL,                 -- References health_checks.id
                check_key       TEXT NOT NULL,                    -- Redundant, for convenient querying
                check_name      TEXT NOT NULL,                    -- Redundant
                category        TEXT NOT NULL,                    -- Redundant
                status          TEXT NOT NULL DEFAULT 'passed'    -- passed/warning/error
                    CHECK(status IN ('passed','warning','error')),
                response_time_ms INTEGER DEFAULT 0,               -- Response time (ms)
                message         TEXT DEFAULT '',                  -- Result message
                detail          TEXT DEFAULT '{}',                -- JSON details
                checked_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_check_history_run
                ON check_history(run_id);
            CREATE INDEX IF NOT EXISTS idx_check_history_key
                ON check_history(check_key);
            CREATE INDEX IF NOT EXISTS idx_check_history_time
                ON check_history(checked_at);

            -- =============================================
            -- 4. Alert rule configuration table
            -- =============================================
            CREATE TABLE IF NOT EXISTS alert_config (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,                    -- Rule name
                check_key       TEXT DEFAULT '*',                 -- Associated check item ('*' means all)
                severity        TEXT DEFAULT 'warning',           -- Trigger severity: warning/critical
                consecutive     INTEGER DEFAULT 1,                -- Alert after N consecutive failures
                notify_method   TEXT DEFAULT 'email',             -- email/internal message/webhook/all
                webhook_url     TEXT DEFAULT '',                  -- Webhook URL
                is_active       INTEGER DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            -- =============================================
            -- 5. Alert history table
            -- =============================================
            CREATE TABLE IF NOT EXISTS alert_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_config_id INTEGER DEFAULT 0,
                check_key       TEXT NOT NULL,
                check_name      TEXT NOT NULL,
                run_id          INTEGER DEFAULT 0,
                status          TEXT NOT NULL,                    -- Status at trigger time
                message         TEXT DEFAULT '',
                notify_method   TEXT DEFAULT '',
                is_read         INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            -- =============================================
            -- 6. Daily health trend table
            -- =============================================
            CREATE TABLE IF NOT EXISTS health_trend (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT NOT NULL,                    -- '2026-05-10'
                total_checks    INTEGER DEFAULT 0,
                passed          INTEGER DEFAULT 0,
                warnings        INTEGER DEFAULT 0,
                errors          INTEGER DEFAULT 0,
                avg_response_ms INTEGER DEFAULT 0,
                health_score    REAL DEFAULT 100.0,              -- Health score 0-100
                created_at      TEXT DEFAULT (datetime('now'))
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_health_trend_date
                ON health_trend(date);
        """)
        print(f'[HealthCheck] ✅ Database tables initialized')


# ─── Seed data: register default check items ───────────────────────────────────────────────

DEFAULT_CHECKS = [
    # (check_key, name, category, description, config, severity, sort)
    ('core_api',       'Core API Check',        'system',    'Health endpoint check for all subsites (Site/Platform/Admin)', '{"timeout":5,"endpoints":["/health"]}', 'warning', 10),
    ('database',       'Database Connection',   'system',    'SQLite/PostgreSQL connection status',  '{"timeout":3}',                                    'critical', 20),
    ('redis',          'Redis Cache',           'system',    'Redis cache service connection status', '{"timeout":3}',                                    'warning', 25),
    ('server_resources','Server Resources',     'system',    'CPU/Memory/Disk usage monitoring',     '{"cpu_threshold":90,"mem_threshold":85,"disk_threshold":85,"timeout":10}', 'warning', 30),
    ('external_apis',  'External Dependencies', 'external',  'Stock quotes/AI API/Payment dependencies', '{"timeout":10,"endpoints":["https://httpbin.org/get"]}', 'warning', 40),
    ('ssl_cert',       'SSL Certificate',       'ssl',       'SSL certificate expiry check for all subdomains', '{"domains":[],"expire_warn_days":30}', 'warning', 50),
    ('workflow_engine','Workflow Engine',       'workflow',  'Cron/Workflow scheduler running status', '{"timeout":5}',                                   'warning', 60),
    ('agent_matrix',   'Agent Matrix',          'agent',     'Primary agent + sub-agent online status','{"timeout":10}',                                   'warning', 70),
    ('content_factory','Content Factory',       'cms',       'Collection channels / processing queue status', '{"timeout":5}',                                    'warning', 80),
    ('media_integrity','Media Integrity',       'cms',       'Scan media files/avatars referenced in DB and verify disk existence',
     '{"dry_run":true,"max_fixes_per_run":20}', 'warning', 85),
    ('sse_ws',         'SSE/WebSocket',         'system',    'SSE push / WebSocket connection status','{"timeout":5}',                                    'warning', 95),
    ('error_logs',     'Error Logs',            'error',     'Error log count in the last 24 hours',  '{"hours":24,"threshold":50}',                      'warning', 100),
    # ── Discovery checkers ──
    ('discovery_modules',   'Module Discovery',           'system',   'Auto-discover project modules and detect changes',               '{}', 'info', 5),
    ('discovery_endpoints', 'Endpoint Discovery',         'system',   'Discover Flask endpoints and detect route changes',               '{}', 'info', 6),
    ('discovery_tables',    'Database Table Discovery',   'database', 'Auto-discover database tables, row counts, and column changes',    '{}', 'info', 7),
    ('discovery_plugins',   'Plugin Discovery',           'system',   'Auto-discover plugins and their health check registration status', '{}', 'info', 8),
]


def seed_default_checks():
    """Initialize default check items (only when the table is empty)"""
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
        print(f'[HealthCheck] ✅ Registered {len(DEFAULT_CHECKS)} default check items')


# ─── Query helpers ──────────────────────────────────────────────────────────────

def get_active_checks():
    """Retrieve all enabled check items"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM health_checks WHERE is_active=1 ORDER BY sort_order'
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_runs(limit=20):
    """Retrieve recent inspection batches"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM check_runs ORDER BY created_at DESC LIMIT ?',
            (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_history_for_run(run_id):
    """Retrieve detailed results for a specific inspection run"""
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM check_history WHERE run_id=? ORDER BY id',
            (run_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_status():
    """Retrieve status statistics from the most recent completed inspection run"""
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
    """Retrieve health trend data for the last N days"""
    with get_db() as conn:
        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        rows = conn.execute(
            'SELECT * FROM health_trend WHERE date>=? ORDER BY date',
            (since,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_alerts(limit=50):
    """Retrieve alert history"""
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
