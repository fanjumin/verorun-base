#!/usr/bin/env python3
"""Developer Accounts — data access layer"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
from models import get_db
from .crypto import encrypt, decrypt, mask


SENSITIVE_FIELDS = ['app_secret', 'bot_token', 'channel_secret', 'access_token']


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


def get_by_id(account_id: int) -> dict | None:
    """Get a single developer account by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM dev_accounts WHERE id=?",
            (account_id,)
        ).fetchone()
    return _sanitize(dict(row)) if row else None


def get_by_platform(platform: str, active_only: bool = True) -> dict | None:
    """Get the first active account for a platform."""
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
    from .crypto import encrypt

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO dev_accounts
               (platform, account_name, app_id, app_secret, bot_token,
                channel_id, channel_secret, access_token, extra_config, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        return cursor.lastrowid


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
            if encrypted and value:
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
    except Exception as e:
        return {'success': False, 'error': str(e)}


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
    except Exception as e:
        return {'success': False, 'error': str(e)}


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
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _sanitize(account: dict) -> dict:
    """Mask sensitive fields for safe display."""
    for field in SENSITIVE_FIELDS:
        if field in account and account[field]:
            account[field] = mask(account[field])
    return account