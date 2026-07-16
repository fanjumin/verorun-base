#!/usr/bin/env python3
"""Ad Management Plugin — PostgreSQL schema: ads"""
import psycopg2
import psycopg2.extras
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), 'ads.db')  # 保留用于迁移

_ads_conn = None


class _PgConnection:
    """psycopg2 connection adapter with sqlite3-compatible interface."""
    def __init__(self, conn):
        self._conn = conn
    def execute(self, sql, params=None):
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if params is not None:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        return cur
    def commit(self):
        self._conn.commit()
    def close(self):
        self._conn.close()


def get_ads_db():
    """获取广告插件数据库连接（PG schema: ads）"""
    global _ads_conn
    if _ads_conn is None:
        raw = psycopg2.connect(
            host=os.environ.get('PG_HOST', 'localhost'),
            port=int(os.environ.get('PG_PORT', 5432)),
            dbname=os.environ.get('PG_DB', 'verorun'),
            user=os.environ.get('PG_USER', 'verorun'),
            password=os.environ.get('PG_PASSWORD', ''),
        )
        raw.autocommit = False
        raw.cursor().execute("CREATE SCHEMA IF NOT EXISTS ads")
        raw.commit()
        raw.cursor().execute("SET search_path TO ads")
        raw.commit()
        _ads_conn = _PgConnection(raw)
    return _ads_conn


def _column_exists(conn, table, column):
    """检查表中是否存在指定列"""
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
        (table, column)
    ).fetchall()
    return len(rows) > 0


def init_ad_db():
    """初始化广告表（幂等，支持从旧版本升级）"""
    conn = get_ads_db()

    # ── 广告位表 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_placements (
        id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        name            TEXT NOT NULL,
        site_key        TEXT NOT NULL DEFAULT 'default',
        zone_id         BIGINT DEFAULT 0,
        position        TEXT NOT NULL DEFAULT 'sidebar',
        page            TEXT NOT NULL DEFAULT '*',
        ad_type         TEXT NOT NULL DEFAULT 'image',
        image_url       TEXT DEFAULT '',
        link_url        TEXT DEFAULT '',
        ad_code         TEXT DEFAULT '',
        width           BIGINT DEFAULT 320,
        height          BIGINT DEFAULT 0,
        targeting_rules TEXT DEFAULT '{}',
        schedule_start  TEXT DEFAULT '',
        schedule_end    TEXT DEFAULT '',
        weight          BIGINT DEFAULT 1,
        freq_cap        BIGINT DEFAULT 0,
        click_tag       TEXT DEFAULT '',
        utm_source      TEXT DEFAULT '',
        is_active       BIGINT DEFAULT 1,
        sort_order      BIGINT DEFAULT 0,
        impressions     BIGINT DEFAULT 0,
        clicks          BIGINT DEFAULT 0,
        created_at      TIMESTAMPTZ DEFAULT NOW(),
        updated_at      TIMESTAMPTZ DEFAULT NOW()
    )''')

    # 兼容旧表：动态添加新增列
    new_columns = [
        ('site_key',        "TEXT NOT NULL DEFAULT 'default'"),
        ('zone_id',         "BIGINT DEFAULT 0"),
        ('targeting_rules', "TEXT DEFAULT '{}'"),
        ('schedule_start',  "TEXT DEFAULT ''"),
        ('schedule_end',    "TEXT DEFAULT ''"),
        ('weight',          "BIGINT DEFAULT 1"),
        ('freq_cap',        "BIGINT DEFAULT 0"),
        ('click_tag',       "TEXT DEFAULT ''"),
        ('utm_source',      "TEXT DEFAULT ''"),
        ('impressions',     "BIGINT DEFAULT 0"),
        ('clicks',          "BIGINT DEFAULT 0"),
    ]
    for col, dtype in new_columns:
        if not _column_exists(conn, 'ad_placements', col):
            conn.execute(f"ALTER TABLE ad_placements ADD COLUMN {col} {dtype}")

    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_page ON ad_placements(page, position)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_site_zone ON ad_placements(site_key, zone_id, is_active)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_render ON ad_placements(is_active, site_key, zone_id, position, page, sort_order, id)')

    # ── 广告位区域表 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_zones (
        id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        site_key    TEXT NOT NULL DEFAULT 'default',
        name        TEXT NOT NULL,
        identifier  TEXT NOT NULL,
        description TEXT DEFAULT '',
        width       BIGINT DEFAULT 0,
        height      BIGINT DEFAULT 0,
        is_active   BIGINT DEFAULT 1,
        sort_order  BIGINT DEFAULT 0,
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        updated_at  TIMESTAMPTZ DEFAULT NOW()
    )''')
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_identifier ON ad_zones(site_key, identifier)')

    # ── 每日统计表 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_stats (
        id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        ad_id       BIGINT NOT NULL,
        stat_date   TEXT NOT NULL,
        impressions BIGINT DEFAULT 0,
        clicks      BIGINT DEFAULT 0,
        UNIQUE(ad_id, stat_date)
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_stats_date ON ad_stats(ad_id, stat_date)')

    # ── 点击明细表（采样，用于排查刷量） ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_clicks (
        id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        ad_id       BIGINT NOT NULL,
        page        TEXT DEFAULT '',
        position    TEXT DEFAULT '',
        ip          TEXT DEFAULT '',
        user_agent  TEXT DEFAULT '',
        referrer    TEXT DEFAULT '',
        created_at  TIMESTAMPTZ DEFAULT NOW()
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_clicks_ad ON ad_clicks(ad_id, created_at)')

    conn.commit()
    print('[AdsPlugin] PG schema ads 已初始化')


def migrate_ad_db():
    """显式迁移入口（与 init_ad_db 相同逻辑，供外部调用）"""
    init_ad_db()


# ── 区域管理辅助函数 ──

def list_zones(site_key='default', active_only=False):
    conn = get_ads_db()
    sql = 'SELECT * FROM ad_zones WHERE site_key=%s'
    params = [site_key]
    if active_only:
        sql += ' AND is_active=1'
    sql += ' ORDER BY sort_order, id'
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_zone(zone_id):
    conn = get_ads_db()
    row = conn.execute('SELECT * FROM ad_zones WHERE id=%s', (zone_id,)).fetchone()
    return dict(row) if row else None


def create_zone(data):
    conn = get_ads_db()
    cur = conn.execute('''INSERT INTO ad_zones
        (site_key, name, identifier, description, width, height, is_active, sort_order)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
        (data.get('site_key', 'default'),
         data.get('name', ''),
         data.get('identifier', ''),
         data.get('description', ''),
         data.get('width', 0),
         data.get('height', 0),
         data.get('is_active', 1),
         data.get('sort_order', 0)))
    conn.commit()
    return cur.lastrowid


def update_zone(zone_id, data):
    conn = get_ads_db()
    conn.execute('''UPDATE ad_zones SET
        site_key=%s, name=%s, identifier=%s, description=%s, width=%s, height=%s,
        is_active=%s, sort_order=%s, updated_at=NOW()
        WHERE id=%s''',
        (data.get('site_key', 'default'),
         data.get('name', ''),
         data.get('identifier', ''),
         data.get('description', ''),
         data.get('width', 0),
         data.get('height', 0),
         data.get('is_active', 1),
         data.get('sort_order', 0),
         zone_id))
    conn.commit()


def delete_zone(zone_id):
    conn = get_ads_db()
    conn.execute('DELETE FROM ad_zones WHERE id=%s', (zone_id,))
    conn.commit()


# ── 统计辅助函数 ──

def record_impression(ad_id):
    """记录一次展示（累计 + 每日）"""
    conn = get_ads_db()
    today = __import__('datetime').date.today().isoformat()
    conn.execute('UPDATE ad_placements SET impressions = impressions + 1, updated_at=NOW() WHERE id=%s', (ad_id,))
    conn.execute('''INSERT INTO ad_stats (ad_id, stat_date, impressions, clicks)
        VALUES (%s, %s, 1, 0)
        ON CONFLICT(ad_id, stat_date) DO UPDATE SET
            impressions = impressions + 1''', (ad_id, today))
    conn.commit()


def record_click(ad_id, page='', position='', ip='', user_agent='', referrer=''):
    """记录一次点击（累计 + 每日 + 明细）"""
    conn = get_ads_db()
    today = __import__('datetime').date.today().isoformat()
    conn.execute('UPDATE ad_placements SET clicks = clicks + 1, updated_at=NOW() WHERE id=%s', (ad_id,))
    conn.execute('''INSERT INTO ad_stats (ad_id, stat_date, impressions, clicks)
        VALUES (%s, %s, 0, 1)
        ON CONFLICT(ad_id, stat_date) DO UPDATE SET
            clicks = clicks + 1''', (ad_id, today))
    conn.execute('''INSERT INTO ad_clicks (ad_id, page, position, ip, user_agent, referrer)
        VALUES (%s, %s, %s, %s, %s, %s)''', (ad_id, page, position, ip, user_agent, referrer))
    conn.commit()


def get_ad_stats(ad_id=None, site_key=None, days=7):
    """查询广告统计，返回每日列表和汇总"""
    conn = get_ads_db()
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=days - 1)

    where = "WHERE stat_date >= %s AND stat_date <= %s"
    params = [start.isoformat(), end.isoformat()]
    if ad_id:
        where += " AND ad_id=%s"
        params.append(ad_id)
    elif site_key:
        where += " AND ad_id IN (SELECT id FROM ad_placements WHERE site_key=%s AND is_active=1)"
        params.append(site_key)

    rows = conn.execute(
        f'SELECT stat_date, SUM(impressions) AS impressions, SUM(clicks) AS clicks FROM ad_stats {where} GROUP BY stat_date ORDER BY stat_date',
        params
    ).fetchall()

    total_imp = sum(r['impressions'] or 0 for r in rows)
    total_clk = sum(r['clicks'] or 0 for r in rows)
    ctr = round(total_clk / total_imp * 100, 2) if total_imp else 0.0

    return {
        'daily': [dict(r) for r in rows],
        'total': {'impressions': total_imp, 'clicks': total_clk, 'ctr': ctr}
    }