#!/usr/bin/env python3
"""
Payment Plugin — 独立数据库模型
==============================
- payment_logs: 支付交易日志（已有）
- payment_configs: 支付提供商凭证（新增，替代主库 system_config）
"""
import sqlite3
import os
import json

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_PLUGIN_DIR, 'data')
_DB_PATH = os.path.join(_DATA_DIR, 'payment.db')
os.makedirs(_DATA_DIR, exist_ok=True)

_payment_conn = None
_conn_lock = __import__('threading').Lock()


def get_payment_db():
    """获取支付数据库连接（线程安全，自动重连）"""
    global _payment_conn
    with _conn_lock:
        if _payment_conn is None:
            _payment_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
            _payment_conn.row_factory = sqlite3.Row
            _payment_conn.execute("PRAGMA journal_mode=WAL")
            _payment_conn.execute("PRAGMA busy_timeout=5000")
        else:
            try:
                _payment_conn.execute("SELECT 1").fetchone()
            except sqlite3.ProgrammingError:
                _payment_conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
                _payment_conn.row_factory = sqlite3.Row
                _payment_conn.execute("PRAGMA journal_mode=WAL")
                _payment_conn.execute("PRAGMA busy_timeout=5000")
    return _payment_conn


def init_payment_tables():
    """创建所有支付插件表（幂等）"""
    conn = get_payment_db()

    # 交易日志（已有）
    conn.execute('''CREATE TABLE IF NOT EXISTS payment_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id        TEXT NOT NULL,
        subject         TEXT DEFAULT '',
        amount          REAL DEFAULT 0,
        provider        TEXT DEFAULT '',
        status          TEXT DEFAULT 'pending',
        raw_response    TEXT DEFAULT '',
        created_at      TEXT DEFAULT (datetime('now')),
        completed_at    TEXT
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_payment_logs_order ON payment_logs(order_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_payment_logs_created ON payment_logs(created_at)')

    # 支付提供商凭证（替代主库 system_config）
    conn.execute('''CREATE TABLE IF NOT EXISTS payment_configs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        provider    TEXT NOT NULL,           -- 'alipay' | 'wechat' | 'stripe' | 'paypal'
        config_key  TEXT NOT NULL,           -- e.g. 'app_id', 'secret_key', 'public_key'
        config_value TEXT NOT NULL DEFAULT '',
        updated_at  TEXT DEFAULT (datetime('now')),
        UNIQUE(provider, config_key)
    )''')
    conn.commit()
    print(f'[PaymentPlugin] ✅ 独立数据库已就绪（{_DB_PATH}）')


# ── 配置读写（替代主库 scfg/gc） ──

def get_payment_config(provider: str, config_key: str, default=''):
    """读取单条支付配置"""
    conn = get_payment_db()
    r = conn.execute(
        'SELECT config_value FROM payment_configs WHERE provider=? AND config_key=?',
        (provider, config_key)
    ).fetchone()
    return r['config_value'] if r else default


def get_provider_configs(provider: str) -> dict:
    """读取某提供商全部配置"""
    conn = get_payment_db()
    rows = conn.execute(
        'SELECT config_key, config_value FROM payment_configs WHERE provider=?',
        (provider,)
    ).fetchall()
    return {r['config_key']: r['config_value'] for r in rows}


def set_payment_config(provider: str, config_key: str, config_value: str):
    """保存单条支付配置"""
    conn = get_payment_db()
    conn.execute('''
        INSERT INTO payment_configs (provider, config_key, config_value, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(provider, config_key) DO UPDATE SET
            config_value=excluded.config_value,
            updated_at=datetime('now')
    ''', (provider, config_key, config_value))
    conn.commit()


def set_provider_configs(provider: str, configs: dict):
    """批量保存某提供商全部配置"""
    for k, v in configs.items():
        set_payment_config(provider, k, v)


def get_all_providers_summary() -> list:
    """获取所有提供商配置概览（供管理 UI 使用）"""
    init_payment_tables()
    conn = get_payment_db()
    rows = conn.execute(
        'SELECT provider, config_key, config_value FROM payment_configs ORDER BY provider, config_key'
    ).fetchall()
    summary = {}
    for r in rows:
        p = r['provider']
        if p not in summary:
            summary[p] = {}
        summary[p][r['config_key']] = r['config_value']
    return [{'provider': k, 'configs': v} for k, v in summary.items()]


def migrate_from_main_db():
    """从主库 system_config 迁移支付凭证到独立库（幂等）"""
    try:
        from models import get_db
        with get_db() as conn:
            # 支付宝
            for key in ['alipay_app_id', 'alipay_private_key', 'alipay_public_key']:
                r = conn.execute('SELECT value FROM system_config WHERE key=?', (key,)).fetchone()
                if r and r['value']:
                    set_payment_config('alipay', key.replace('alipay_', ''), r['value'])
            # 回调域名
            r = conn.execute('SELECT value FROM system_config WHERE key="payment.notify_base"').fetchone()
            if r and r['value']:
                set_payment_config('alipay', 'notify_base', r['value'])
            # 微信
            for key in ['wechat_app_id', 'wechat_mchid', 'wechat_api_v3_key', 'wechat_cert_serial', 'wechat_plan_id']:
                r = conn.execute('SELECT value FROM system_config WHERE key=?', (key,)).fetchone()
                if r and r['value']:
                    set_payment_config('wechat', key.replace('wechat_', ''), r['value'])
        print('[PaymentPlugin] ✅ 主库支付凭证已迁移至独立库')
    except Exception as e:
        print(f'[PaymentPlugin] ⚠️ 迁移支付凭证失败（首次运行正常）: {e}')


ensure_payment_tables = init_payment_tables
