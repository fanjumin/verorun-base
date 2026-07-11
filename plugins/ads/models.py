#!/usr/bin/env python3
"""Ad Management Plugin — 数据库模型"""
import sqlite3, os, json

DB_PATH = os.path.join(os.path.dirname(__file__), 'ads.db')

_ads_conn = None


def get_ads_db():
    """获取广告插件独立数据库连接"""
    global _ads_conn
    if _ads_conn is None:
        _ads_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _ads_conn.row_factory = sqlite3.Row
        _ads_conn.execute("PRAGMA journal_mode=WAL")
        _ads_conn.execute("PRAGMA busy_timeout=1000")
        _ads_conn.execute("PRAGMA foreign_keys=ON")
    return _ads_conn


def _column_exists(conn, table, column):
    """检查表中是否存在指定列"""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r['name'] == column for r in rows)


def init_ad_db():
    """初始化广告表（幂等，支持从旧版本升级）"""
    conn = get_ads_db()

    # ── 广告位表 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_placements (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        site_key        TEXT NOT NULL DEFAULT 'default',
        zone_id         INTEGER DEFAULT 0,
        position        TEXT NOT NULL DEFAULT 'sidebar',
        page            TEXT NOT NULL DEFAULT '*',
        ad_type         TEXT NOT NULL DEFAULT 'image',
        image_url       TEXT DEFAULT '',
        link_url        TEXT DEFAULT '',
        ad_code         TEXT DEFAULT '',
        width           INTEGER DEFAULT 320,
        height          INTEGER DEFAULT 0,
        targeting_rules TEXT DEFAULT '{}',
        schedule_start  TEXT DEFAULT '',
        schedule_end    TEXT DEFAULT '',
        weight          INTEGER DEFAULT 1,
        freq_cap        INTEGER DEFAULT 0,
        click_tag       TEXT DEFAULT '',
        utm_source      TEXT DEFAULT '',
        is_active       INTEGER DEFAULT 1,
        sort_order      INTEGER DEFAULT 0,
        impressions     INTEGER DEFAULT 0,
        clicks          INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )''')

    # 兼容旧表：动态添加新增列
    new_columns = [
        ('site_key',        "TEXT NOT NULL DEFAULT 'default'"),
        ('zone_id',         "INTEGER DEFAULT 0"),
        ('targeting_rules', "TEXT DEFAULT '{}'"),
        ('schedule_start',  "TEXT DEFAULT ''"),
        ('schedule_end',    "TEXT DEFAULT ''"),
        ('weight',          "INTEGER DEFAULT 1"),
        ('freq_cap',        "INTEGER DEFAULT 0"),
        ('click_tag',       "TEXT DEFAULT ''"),
        ('utm_source',      "TEXT DEFAULT ''"),
        ('impressions',     "INTEGER DEFAULT 0"),
        ('clicks',          "INTEGER DEFAULT 0"),
    ]
    for col, dtype in new_columns:
        if not _column_exists(conn, 'ad_placements', col):
            conn.execute(f"ALTER TABLE ad_placements ADD COLUMN {col} {dtype}")

    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_page ON ad_placements(page, position)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_site_zone ON ad_placements(site_key, zone_id, is_active)')

    # ── 广告位区域表 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_zones (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        site_key    TEXT NOT NULL DEFAULT 'default',
        name        TEXT NOT NULL,
        identifier  TEXT NOT NULL,
        description TEXT DEFAULT '',
        width       INTEGER DEFAULT 0,
        height      INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1,
        sort_order  INTEGER DEFAULT 0,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_identifier ON ad_zones(site_key, identifier)')

    # ── 每日统计表 ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_stats (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_id       INTEGER NOT NULL,
        stat_date   TEXT NOT NULL,
        impressions INTEGER DEFAULT 0,
        clicks      INTEGER DEFAULT 0,
        UNIQUE(ad_id, stat_date)
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_stats_date ON ad_stats(ad_id, stat_date)')

    # ── 点击明细表（采样，用于排查刷量） ──
    conn.execute('''CREATE TABLE IF NOT EXISTS ad_clicks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_id       INTEGER NOT NULL,
        page        TEXT DEFAULT '',
        position    TEXT DEFAULT '',
        ip          TEXT DEFAULT '',
        user_agent  TEXT DEFAULT '',
        referrer    TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now'))
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ad_clicks_ad ON ad_clicks(ad_id, created_at)')

    conn.commit()
    print('[AdsPlugin] ads.db 已初始化')


def migrate_ad_db():
    """显式迁移入口（与 init_ad_db 相同逻辑，供外部调用）"""
    init_ad_db()


# ── 区域管理辅助函数 ──

def list_zones(site_key='default', active_only=False):
    conn = get_ads_db()
    sql = 'SELECT * FROM ad_zones WHERE site_key=?'
    params = [site_key]
    if active_only:
        sql += ' AND is_active=1'
    sql += ' ORDER BY sort_order, id'
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_zone(zone_id):
    conn = get_ads_db()
    row = conn.execute('SELECT * FROM ad_zones WHERE id=?', (zone_id,)).fetchone()
    return dict(row) if row else None


def create_zone(data):
    conn = get_ads_db()
    cur = conn.execute('''INSERT INTO ad_zones
        (site_key, name, identifier, description, width, height, is_active, sort_order)
        VALUES (?,?,?,?,?,?,?,?)''',
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
        site_key=?, name=?, identifier=?, description=?, width=?, height=?,
        is_active=?, sort_order=?, updated_at=datetime('now')
        WHERE id=?''',
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
    conn.execute('DELETE FROM ad_zones WHERE id=?', (zone_id,))
    conn.commit()


# ── 统计辅助函数 ──

def record_impression(ad_id):
    """记录一次展示（累计 + 每日）"""
    conn = get_ads_db()
    today = __import__('datetime').date.today().isoformat()
    conn.execute('UPDATE ad_placements SET impressions = impressions + 1, updated_at=datetime("now") WHERE id=?', (ad_id,))
    conn.execute('''INSERT INTO ad_stats (ad_id, stat_date, impressions, clicks)
        VALUES (?, ?, 1, 0)
        ON CONFLICT(ad_id, stat_date) DO UPDATE SET
            impressions = impressions + 1''', (ad_id, today))
    conn.commit()


def record_click(ad_id, page='', position='', ip='', user_agent='', referrer=''):
    """记录一次点击（累计 + 每日 + 明细）"""
    conn = get_ads_db()
    today = __import__('datetime').date.today().isoformat()
    conn.execute('UPDATE ad_placements SET clicks = clicks + 1, updated_at=datetime("now") WHERE id=?', (ad_id,))
    conn.execute('''INSERT INTO ad_stats (ad_id, stat_date, impressions, clicks)
        VALUES (?, ?, 0, 1)
        ON CONFLICT(ad_id, stat_date) DO UPDATE SET
            clicks = clicks + 1''', (ad_id, today))
    conn.execute('''INSERT INTO ad_clicks (ad_id, page, position, ip, user_agent, referrer)
        VALUES (?, ?, ?, ?, ?, ?)''', (ad_id, page, position, ip, user_agent, referrer))
    conn.commit()


def get_ad_stats(ad_id=None, days=7):
    """查询广告统计，返回每日列表和汇总"""
    conn = get_ads_db()
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=days - 1)

    where = "WHERE stat_date >= ? AND stat_date <= ?"
    params = [start.isoformat(), end.isoformat()]
    if ad_id:
        where += " AND ad_id=?"
        params.append(ad_id)

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