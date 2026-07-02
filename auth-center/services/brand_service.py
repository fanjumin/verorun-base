#!/usr/bin/env python3
"""Brand settings service — shared across all 4 services for global brand config."""

import sqlite3, os

# 项目版本号（从 VERSION 文件读取）
_VERSION_CACHE = None
def _get_project_version():
    global _VERSION_CACHE
    if _VERSION_CACHE:
        return _VERSION_CACHE
    # 从当前文件向上查找 VERSION 文件
    base = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidate = os.path.join(base, 'VERSION')
        if os.path.exists(candidate):
            with open(candidate, 'r') as f:
                _VERSION_CACHE = f.read().strip()
            return _VERSION_CACHE
        base = os.path.dirname(base)
    _VERSION_CACHE = '0.9.5'
    return _VERSION_CACHE

_DB_PATH = None

def _get_db_path():
    """Resolve database path, works from any service."""
    global _DB_PATH
    if _DB_PATH:
        return _DB_PATH
    # Env var or auto-detect
    env_path = os.environ.get('DB_PATH', '')
    if env_path and os.path.exists(env_path):
        _DB_PATH = env_path
        return _DB_PATH
    # Auto-detect from project structure
    base = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidate = os.path.join(base, 'data', 'x7k2m9a4.db')
        if os.path.exists(candidate):
            _DB_PATH = candidate
            return candidate
        base = os.path.dirname(base)
    # Final fallback
    _DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'x7k2m9a4.db')
    return _DB_PATH


def get_brand_settings():
    """Return brand settings dict, or None if table doesn't exist yet."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM brand_settings WHERE id=1").fetchone()
        conn.close()
        if row:
            d = dict(row)
            d['version'] = _get_project_version()
            return d
    except sqlite3.OperationalError:
        # Table not created yet — app hasn't run init_db()
        pass
    return None


def get_tm_brand_settings():
    """Return TradeMind sub-brand settings dict."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM tm_brand_settings WHERE id=1").fetchone()
        conn.close()
        if row:
            return dict(row)
    except sqlite3.OperationalError:
        pass
    return None



