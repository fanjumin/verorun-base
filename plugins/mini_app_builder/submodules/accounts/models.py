#!/usr/bin/env python3
"""Developer Credentials — data access layer (merged from plugins/dev_accounts).

Tables live in the `mini_app_builder` schema (see migrate.py); a public view
keeps backward compatibility for any external readers.  Connections go through
plugins/_base/db.py and explicitly SET search_path so both the moved tables
and shared public tables resolve correctly.
"""

import json
from contextlib import contextmanager
from urllib.error import URLError

from plugins._base.db import PgConnection, get_raw_connection
from .crypto import encrypt, decrypt, mask


SENSITIVE_FIELDS = ['app_secret', 'bot_token', 'channel_secret', 'access_token']


@contextmanager
def get_db():
    """PostgreSQL connection (mini_app_builder schema first, then public).

    dev_accounts / schema_meta tables were moved to the mini_app_builder schema
    by the v2.0.0 migration; shared public tables (users etc.) still resolve via
    the trailing `public` search path entry.
    """
    conn = get_raw_connection()
    conn.autocommit = False
    try:
        wrapped = PgConnection(conn)
        wrapped.execute("SET search_path TO mini_app_builder, public")
        yield wrapped
    finally:
        conn.close()


def init_db():
    """Create dev_accounts / schema_meta tables if they don't exist (PostgreSQL)."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dev_accounts (
                id               SERIAL PRIMARY KEY,
                platform         TEXT NOT NULL,
                account_name     TEXT NOT NULL,
                app_id           TEXT DEFAULT '',
                app_secret       TEXT DEFAULT '',
                bot_token        TEXT DEFAULT '',
                channel_id       TEXT DEFAULT '',
                channel_secret   TEXT DEFAULT '',
                access_token     TEXT DEFAULT '',
                extra_config     TEXT DEFAULT '{}',
                is_active        INTEGER DEFAULT 1,
                created_at       TEXT DEFAULT NOW(),
                updated_at       TEXT DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_dev_accounts_platform
                ON dev_accounts(platform)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_meta (
                key        TEXT PRIMARY KEY,
                value      TEXT DEFAULT '',
                updated_at TEXT DEFAULT NOW()
            )
        """)
        conn.commit()


def get_all(platform: str = None) -> list:
    """Get all developer accounts, optionally filtered by platform."""
    with get_db() as conn:
        if platform:
            rows = conn.execute(
                "SELECT * FROM dev_accounts WHERE platform=? ORDER BY created_at DESC",
                (platform,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM dev_accounts ORDER BY platform, created_at DESC"
            ).fetchall()
    return [_sanitize(dict(r)) for r in rows]


def get_all_raw(platform: str = None) -> list:
    """Get all developer accounts with raw (still-encrypted) fields.

    Unlike get_all(), this does NOT mask sensitive fields.  Intended for
    internal consumers (e.g. the plugin public API) that call decrypt()
    themselves.
    """
    with get_db() as conn:
        if platform:
            rows = conn.execute(
                "SELECT * FROM dev_accounts WHERE platform=? ORDER BY created_at DESC",
                (platform,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM dev_accounts ORDER BY platform, created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(account_id: int) -> dict | None:
    """Get a single developer account by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM dev_accounts WHERE id=?",
            (account_id,)
        ).fetchone()
    return _sanitize(dict(row)) if row else None


def get_by_platform(platform: str, active_only: bool = True) -> dict | None:
    """Get the first active account for a platform (sensitive fields masked)."""
    row = get_by_platform_raw(platform, active_only=active_only)
    return _sanitize(dict(row)) if row else None


def get_by_platform_raw(platform: str, active_only: bool = True) -> dict | None:
    """Get the first account for a platform with raw (encrypted) fields.

    Intended for internal runtime consumers (deploy, Telegram login) that call
    decrypt() themselves.  Prefer get_by_platform() for display purposes.
    """
    with get_db() as conn:
        if active_only:
            row = conn.execute(
                "SELECT * FROM dev_accounts WHERE platform=? AND is_active=1 LIMIT 1",
                (platform,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM dev_accounts WHERE platform=? LIMIT 1",
                (platform,)
            ).fetchone()
    return dict(row) if row else None


def create(platform: str, account_name: str, **kwargs) -> int:
    """Create a new developer account. Returns the new row ID."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO dev_accounts
               (platform, account_name, app_id, app_secret, bot_token,
                channel_id, channel_secret, access_token, extra_config, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (
                platform,
                account_name,
                kwargs.get('app_id', ''),
                encrypt(kwargs.get('app_secret', '')),
                encrypt(kwargs.get('bot_token', '')),
                kwargs.get('channel_id', ''),
                encrypt(kwargs.get('channel_secret', '')),
                encrypt(kwargs.get('access_token', '')),
                json.dumps(kwargs.get('extra_config', {})),
                kwargs.get('is_active', 1),
            )
        )
        conn.commit()
        return cursor.fetchone()['id']


def update(account_id: int, **kwargs) -> bool:
    """Update an existing developer account."""
    fields = []
    values = []

    field_map = {
        'platform': ('platform', False),
        'account_name': ('account_name', False),
        'app_id': ('app_id', False),
        'app_secret': ('app_secret', True),
        'bot_token': ('bot_token', True),
        'channel_id': ('channel_id', False),
        'channel_secret': ('channel_secret', True),
        'access_token': ('access_token', True),
        'extra_config': ('extra_config', False),
        'is_active': ('is_active', False),
    }

    for key, value in kwargs.items():
        if key in field_map:
            col_name, encrypted = field_map[key]
            if encrypted:
                # 敏感字段留空表示不修改，避免编辑时误清空已存凭证
                if not value:
                    continue
                value = encrypt(value)
            elif key == 'extra_config' and isinstance(value, dict):
                value = json.dumps(value)
            fields.append(f"{col_name}=?")
            values.append(value)

    if not fields:
        return False

    values.append(account_id)
    sql = f"UPDATE dev_accounts SET {', '.join(fields)}, updated_at=NOW() WHERE id=%s"

    with get_db() as conn:
        conn.execute(sql, values)
        conn.commit()
    return True


def delete(account_id: int) -> bool:
    """Delete a developer account."""
    with get_db() as conn:
        conn.execute("DELETE FROM dev_accounts WHERE id=?", (account_id,))
        conn.commit()
    return True


def test_connection(account_id: int) -> dict:
    """Test platform connection for a developer account."""
    account = get_by_id(account_id)
    if not account:
        return {'success': False, 'error': 'Account not found'}

    platform = account['platform']
    try:
        if platform == 'telegram':
            return _test_telegram(account)
        elif platform == 'line':
            return _test_line(account)
        elif platform in ('douyin', 'wechat'):
            return {'success': True, 'message': f'{platform} connection test not implemented (requires SDK). Verify credentials manually.'}
        else:
            return {'success': False, 'error': f'Unknown platform: {platform}'}
    except URLError:
        return {'success': False, 'error': 'Connection test failed: cannot reach platform API. Check network connectivity.'}
    except Exception as e:
        import logging
        logging.getLogger('dev_accounts').warning('Connection test failed for account %s: %s', account_id, e)
        return {'success': False, 'error': 'Connection test failed due to an unexpected error.'}


def _test_telegram(account: dict) -> dict:
    """Test Telegram Bot API connection."""
    import urllib.request as _ur
    bot_token = decrypt(account.get('bot_token', ''))
    if not bot_token:
        return {'success': False, 'error': 'No bot_token configured'}
    try:
        resp = json.loads(_ur.urlopen(
            f'https://api.telegram.org/bot{bot_token}/getMe',
            timeout=10
        ).read())
        if resp.get('ok'):
            return {'success': True, 'message': f"Connected as @{resp['result'].get('username', 'unknown')}"}
        return {'success': False, 'error': resp.get('description', 'Unknown error')}
    except URLError:
        return {'success': False, 'error': 'Connection test failed: cannot reach Telegram API. Check network connectivity.'}
    except Exception as e:
        import logging
        logging.getLogger('dev_accounts').warning('Telegram connection test error: %s', e)
        return {'success': False, 'error': 'Connection test failed due to an unexpected error.'}


def _test_line(account: dict) -> dict:
    """Test LINE Messaging API connection."""
    import urllib.request as _ur
    access_token = decrypt(account.get('access_token', ''))
    if not access_token:
        return {'success': False, 'error': 'No access_token configured'}
    try:
        req = _ur.Request(
            'https://api.line.me/v2/bot/info',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        resp = json.loads(_ur.urlopen(req, timeout=10).read())
        if 'userId' in resp:
            return {'success': True, 'message': f"Connected as {resp.get('displayName', 'unknown')}"}
        return {'success': False, 'error': resp.get('message', 'Unknown error')}
    except URLError:
        return {'success': False, 'error': 'Connection test failed: cannot reach LINE API. Check network connectivity.'}
    except Exception as e:
        import logging
        logging.getLogger('dev_accounts').warning('LINE connection test error: %s', e)
        return {'success': False, 'error': 'Connection test failed due to an unexpected error.'}


def _sanitize(account: dict) -> dict:
    """Mask sensitive fields for safe display."""
    for field in SENSITIVE_FIELDS:
        if field in account and account[field]:
            account[field] = mask(account[field])
    return account


def get_account_stats() -> dict:
    """Return account statistics for Dashboard (P2-7)."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) AS count FROM dev_accounts").fetchone()
        active = conn.execute(
            "SELECT COUNT(*) AS count FROM dev_accounts WHERE is_active=1"
        ).fetchone()
    return {
        'total_accounts': total['count'] if total else 0,
        'active_accounts': active['count'] if active else 0,
    }


def set_schema_version(version: str):
    """Record current schema version in schema_meta (标准 §10.6)."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO schema_meta (key, value, updated_at) "
            "VALUES ('schema_version', ?, NOW()) "
            "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()",
            (version,)
        )
        conn.commit()


def get_schema_version() -> str:
    """Read current schema version from schema_meta."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
            return row['value'] if row else '0.0.0'
    except Exception:
        return '0.0.0'
