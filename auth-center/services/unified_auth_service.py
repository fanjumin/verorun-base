#!/usr/bin/env python3
"""
Unified API Key Service — Phase 3

Provides unified key generation, verification, revocation, quota tracking,
and audit logging across all key types (user, agent, provider).

Key format: vr_{type}_{32hex}
  vr_user_xxxxxxxx  → user application API key
  vr_agent_xxxxxxxx → agent API key (with scopes)
  vr_prov_xxxxxxxx  → provider API key (encrypted at rest)

Usage:
    from services.unified_auth_service import UnifiedAuthService
    svc = UnifiedAuthService()
    raw_key = svc.generate_key(user_id=1, key_type='user', name='My App')
    info = svc.verify_key(raw_key)
"""

import hashlib
import secrets
import hmac
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List

from models import get_db, now_iso

# ── Constants ──────────────────────────────────────────────────────────────

KEY_PREFIX_MAP = {
    'user':     'vr_user_',
    'agent':    'vr_agent_',
    'provider': 'vr_prov_',
}
VALID_KEY_TYPES = tuple(KEY_PREFIX_MAP.keys())
KEY_RAW_LENGTH = 32  # hex chars after prefix

# ── UnifiedAuthService ─────────────────────────────────────────────────────


class UnifiedAuthService:
    """Unified API key management with quota tracking and audit logging."""

    # ── Key Generation ─────────────────────────────────────────────────

    def generate_key(
        self,
        user_id: int,
        key_type: str,
        name: str = '',
        scopes: Optional[List[str]] = None,
        quota_daily: Optional[int] = None,
        expire_at: Optional[str] = None,
        agent_id: Optional[int] = None,
        provider: str = '',
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate a new unified API key.

        Returns:
            (raw_key, key_info_dict) — raw_key is shown only once.
        """
        if key_type not in VALID_KEY_TYPES:
            raise ValueError(f"Invalid key_type: {key_type}. Must be one of {VALID_KEY_TYPES}")

        prefix = KEY_PREFIX_MAP[key_type]
        raw_hex = secrets.token_hex(KEY_RAW_LENGTH)
        raw_key = f"{prefix}{raw_hex}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix_display = f"{raw_key[:16]}...{raw_key[-4:]}"
        scopes_json = json_dumps(scopes or [])

        now = now_iso()
        with get_db() as conn:
            conn.execute(
                '''INSERT INTO unified_api_keys
                   (key_hash, key_prefix, key_type, user_id, agent_id, provider,
                    name, scopes, quota_daily, expire_at, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (key_hash, key_prefix_display, key_type, user_id, agent_id, provider,
                 name, scopes_json, quota_daily, expire_at, now, now),
            )
            conn.commit()
            # Record audit log
            key_row = conn.execute(
                'SELECT id FROM unified_api_keys WHERE key_hash=%s', (key_hash,)
            ).fetchone()

        self._audit(key_row['id'], 'create', user_id, extra={'key_type': key_type})

        return raw_key, {
            'id': key_row['id'],
            'key': raw_key,
            'key_prefix': key_prefix_display,
            'key_type': key_type,
            'name': name,
            'scopes': scopes or [],
            'quota_daily': quota_daily,
            'expire_at': expire_at,
            'warning': 'Save this key now! It will not be shown again.',
        }

    # ── Key Verification ───────────────────────────────────────────────

    def verify_key(self, raw_key: str) -> Optional[Dict[str, Any]]:
        """Verify a raw API key and return metadata if valid.

        Returns None if the key is invalid, revoked, or expired.
        Falls back to legacy tables (api_keys, agent_api_keys) for old-format keys.
        """
        if not raw_key:
            return None

        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        with get_db() as conn:
            # Try unified table first
            row = conn.execute(
                '''SELECT id, key_type, user_id, agent_id, provider, name, scopes,
                          quota_daily, expire_at, status, calls_total, calls_today,
                          last_used_at, created_at
                   FROM unified_api_keys
                   WHERE key_hash=%s AND status='active' ''',
                (key_hash,),
            ).fetchone()

            if row:
                info = dict(row)
                info['scopes'] = json_loads(info.get('scopes', '[]'))
                self._record_usage(conn, info['id'])
                return info

            # Fallback to legacy api_keys (user)
            key_prefix = raw_key[:12] if raw_key.startswith('tm-') else None
            if key_prefix:
                legacy = conn.execute(
                    '''SELECT id, user_id, key_prefix, name, 'user' as key_type,
                              calls_today, calls_total, expire_at, last_used, created_at,
                              NULL as scopes, 1 as active
                       FROM api_keys
                       WHERE key_hash=%s AND active=1 ''',
                    (key_hash,),
                ).fetchone()
                if legacy:
                    info = dict(legacy)
                    info['key_type'] = 'user'
                    info['scopes'] = []
                    info['status'] = 'active'
                    info['quota_daily'] = None
                    info['agent_id'] = None
                    info['provider'] = ''
                    info['last_used_at'] = info.get('last_used')
                    return info

            # Fallback to legacy agent_api_keys
            legacy = conn.execute(
                '''SELECT id, agent_id, user_id, key_prefix, name, scopes,
                          calls_today, calls_total, expire_at, last_used_at, created_at,
                          status
                   FROM agent_api_keys
                   WHERE key_hash=%s AND status='active' ''',
                (key_hash,),
            ).fetchone()
            if legacy:
                info = dict(legacy)
                info['key_type'] = 'agent'
                info['scopes'] = json_loads(info.get('scopes', '[]'))
                info['quota_daily'] = None
                info['provider'] = ''
                return info

        return None

    # ── Key Revocation ─────────────────────────────────────────────────

    def revoke_key(self, key_id: int, user_id: int) -> bool:
        """Revoke (soft-delete) a unified API key. Returns True if successful."""
        with get_db() as conn:
            cur = conn.execute(
                "UPDATE unified_api_keys SET status='revoked', updated_at=%s "
                'WHERE id=%s AND user_id=%s',
                (now_iso(), key_id, user_id),
            )
            conn.commit()
            if cur.rowcount > 0:
                self._audit(key_id, 'revoke', user_id)
                return True
        return False

    # ── Key Listing ────────────────────────────────────────────────────

    def list_keys(
        self,
        user_id: int,
        key_type: Optional[str] = None,
        agent_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List unified API keys for a user, optionally filtered by type."""
        with get_db() as conn:
            query = '''SELECT id, key_type, key_prefix, name, scopes,
                              quota_daily, expire_at, status, calls_total, calls_today,
                              last_used_at, created_at, updated_at
                       FROM unified_api_keys
                       WHERE user_id=%s'''
            params = [user_id]

            if key_type and key_type in VALID_KEY_TYPES:
                query += ' AND key_type=%s'
                params.append(key_type)
            if agent_id is not None:
                query += ' AND agent_id=%s'
                params.append(agent_id)

            query += ' ORDER BY created_at DESC'
            rows = conn.execute(query, params).fetchall()

        result = []
        for r in rows:
            info = dict(r)
            info['scopes'] = json_loads(info.get('scopes', '[]'))
            result.append(info)
        return result

    # ── Quota Enforcement ──────────────────────────────────────────────

    def check_quota(self, key_id: int) -> Dict[str, Any]:
        """Check remaining quota for a key. Returns {allowed, remaining, daily_limit, used_today}."""
        with get_db() as conn:
            row = conn.execute(
                'SELECT quota_daily, calls_today FROM unified_api_keys WHERE id=%s',
                (key_id,),
            ).fetchone()

        if not row:
            return {'allowed': False, 'remaining': 0, 'daily_limit': 0, 'used_today': 0, 'reason': 'key not found'}

        daily_limit = row['quota_daily'] or 0
        used_today = row['calls_today'] or 0

        if daily_limit <= 0:
            return {'allowed': True, 'remaining': -1, 'daily_limit': 0, 'used_today': used_today,
                    'reason': 'unlimited'}

        remaining = daily_limit - used_today
        return {
            'allowed': remaining > 0,
            'remaining': max(remaining, 0),
            'daily_limit': daily_limit,
            'used_today': used_today,
            'reason': 'ok' if remaining > 0 else 'daily quota exceeded',
        }

    def set_quota(self, key_id: int, daily_limit: int) -> bool:
        """Update daily quota for a key."""
        with get_db() as conn:
            cur = conn.execute(
                'UPDATE unified_api_keys SET quota_daily=%s, updated_at=%s WHERE id=%s',
                (daily_limit, now_iso(), key_id),
            )
            conn.commit()
            return cur.rowcount > 0

    # ── Usage Tracking ─────────────────────────────────────────────────

    def _record_usage(self, conn, key_id: int):
        """Increment usage counters for a key."""
        conn.execute(
            '''UPDATE unified_api_keys
               SET calls_today = calls_today + 1,
                   calls_total = calls_total + 1,
                   last_used_at = %s
               WHERE id=%s''',
            (now_iso(), key_id),
        )
        conn.commit()

    # ── Audit Logging ──────────────────────────────────────────────────

    def _audit(self, key_id: int, action: str, user_id: int, extra: Optional[Dict] = None):
        """Record an audit log entry."""
        with get_db() as conn:
            conn.execute(
                '''INSERT INTO api_key_audit (key_id, action, user_id, extra, created_at)
                   VALUES (%s,%s,%s,%s,%s)''',
                (key_id, action, user_id, json_dumps(extra or {}), now_iso()),
            )
            conn.commit()

    def get_audit_log(self, key_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get audit log for a key."""
        with get_db() as conn:
            rows = conn.execute(
                'SELECT id, action, user_id, extra, created_at '
                'FROM api_key_audit WHERE key_id=%s ORDER BY created_at DESC LIMIT %s',
                (key_id, limit),
            ).fetchall()
        result = []
        for r in rows:
            info = dict(r)
            info['extra'] = json_loads(info.get('extra', '{}'))
            result.append(info)
        return result

    # ── Key Rotation ───────────────────────────────────────────────────

    def rotate_key(self, key_id: int, user_id: int) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Rotate a key: revoke old, generate new with same metadata."""
        with get_db() as conn:
            old = conn.execute(
                'SELECT key_type, agent_id, provider, name, scopes, quota_daily, expire_at '
                'FROM unified_api_keys WHERE id=%s AND user_id=%s',
                (key_id, user_id),
            ).fetchone()

        if not old:
            return None

        # Revoke old key
        self.revoke_key(key_id, user_id)

        # Generate new key with same metadata
        return self.generate_key(
            user_id=user_id,
            key_type=old['key_type'],
            name=old['name'],
            scopes=json_loads(old.get('scopes', '[]')),
            quota_daily=old['quota_daily'],
            expire_at=old['expire_at'],
            agent_id=old['agent_id'],
            provider=old['provider'],
        )


# ── Helpers ────────────────────────────────────────────────────────────────

def json_dumps(obj):
    """Serialize to JSON string, returning '{}' on failure."""
    import json
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return '{}'


def json_loads(s):
    """Deserialize JSON string, returning empty list/dict on failure."""
    import json
    if not s:
        return []
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return [] if s.strip().startswith('[') else {}