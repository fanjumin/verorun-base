#!/usr/bin/env python3
"""Notification Service — centralized notification creation and event-driven sending."""

import json
import re
import time
import sqlite3
import os

_DB_PATH = None

# ── Rate limiting ──
_rate_limit_cache = {}  # { user_id: [timestamps...] }
RATE_LIMIT_PER_MIN = 10


def _get_db_path():
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


def _get_conn():
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _check_rate_limit(user_id):
    """Rate limit: max RATE_LIMIT_PER_MIN notifications per user per minute."""
    now = time.time()
    timestamps = _rate_limit_cache.get(user_id, [])
    # Keep only timestamps within the last 60s
    timestamps = [t for t in timestamps if now - t < 60]
    if len(timestamps) >= RATE_LIMIT_PER_MIN:
        return False
    timestamps.append(now)
    _rate_limit_cache[user_id] = timestamps
    return True


def _substitute_vars(template, context_vars):
    """Replace {var} placeholders with values from context_vars dict."""
    def replacer(m):
        key = m.group(1)
        return str(context_vars.get(key, m.group(0)))
    return re.sub(r'\{(\w+)\}', replacer, template)


# ══════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════

def create_notification(user_id, ntype, title, content, link_url=None, extra_data=None):
    """Create a single notification for a user. Returns the notification ID or None if rate limited."""
    if not _check_rate_limit(user_id):
        return None
    if extra_data is None:
        extra_data = {}
    conn = _get_conn()
    try:
        cur = conn.execute(
            'INSERT INTO user_notifications (user_id, type, title, content, link_url, extra_data) VALUES (?,?,?,?,?,?)',
            (user_id, ntype, title, content, link_url or '', json.dumps(extra_data, ensure_ascii=False))
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        return None
    finally:
        conn.close()


def send_notification_by_event(event_type, user_id, context_vars=None):
    """
    Event-driven notification: looks up a matching template, substitutes variables,
    creates the notification. Returns dict with notification_id or error.
    
    context_vars example: {'username': '张三', 'reward_name': '新人优惠券', 'friend_name': '李四'}
    """
    if context_vars is None:
        context_vars = {}
    conn = _get_conn()
    try:
        # Find the active template for this event_type
        template = conn.execute(
            'SELECT * FROM notification_templates WHERE event_type=? AND is_active=1',
            (event_type,)
        ).fetchone()
        if not template:
            return {'success': False, 'error': f'No active template for event: {event_type}'}

        template = dict(template)

        # Substitute variables
        title = _substitute_vars(template['title_template'], context_vars)
        content = _substitute_vars(template['content_template'], context_vars)
        link_url = ''
        if template.get('link_url_template'):
            link_url = _substitute_vars(template['link_url_template'], context_vars)

        # Create notification
        nid = create_notification(
            user_id=user_id,
            ntype=template.get('type', 'system'),
            title=title,
            content=content,
            link_url=link_url,
            extra_data={'event_type': event_type}
        )
        if nid is None:
            return {'success': False, 'error': 'Rate limited or creation failed'}

        # Log the send
        conn.execute(
            'INSERT INTO notification_logs (template_id, user_id, event_type, notification_id, result) VALUES (?,?,?,?,?)',
            (template['id'], user_id, event_type, nid, 'success')
        )
        conn.commit()

        return {'success': True, 'notification_id': nid}

    except Exception as e:
        return {'success': False, 'error': str(e)}
    finally:
        conn.close()


def get_unread_count(user_id):
    """Return the number of unread notifications for a user."""
    conn = _get_conn()
    try:
        row = conn.execute(
            'SELECT COUNT(*) as c FROM user_notifications WHERE user_id=? AND is_read=0',
            (user_id,)
        ).fetchone()
        return row['c'] if row else 0
    finally:
        conn.close()


def mark_read(user_id, nid=None):
    """Mark a notification (or all) as read. Updates read_at timestamp."""
    conn = _get_conn()
    try:
        if nid:
            conn.execute(
                "UPDATE user_notifications SET is_read=1, read_at=datetime('now') WHERE user_id=? AND id=?",
                (user_id, nid)
            )
        else:
            conn.execute(
                "UPDATE user_notifications SET is_read=1, read_at=datetime('now') WHERE user_id=?",
                (user_id,)
            )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def send_to_all_users(ntype, title, content, link_url=None, limit=1000):
    """
    Send a notification to all active users.
    Returns count of notifications sent.
    """
    conn = _get_conn()
    try:
        users = conn.execute(
            'SELECT id FROM users WHERE active=1 ORDER BY id LIMIT ?',
            (limit,)
        ).fetchall()
        sent = 0
        for u in users:
            nid = create_notification(u['id'], ntype, title, content, link_url)
            if nid:
                sent += 1
        return sent
    finally:
        conn.close()
