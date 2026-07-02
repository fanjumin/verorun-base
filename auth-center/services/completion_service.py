#!/usr/bin/env python3
"""
Profile Completion Service — calculates completion % and checks milestone rewards.
"""

import json
import sqlite3
import os
import sys

# ── DB Path Discovery (mirrors brand_service.py / notification_service.py) ──
_DB_PATH = None

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


def _has_user_interests(user_id):
    """Check if user has at least one interest selected in user_interests table."""
    try:
        conn = _get_conn()
        row = conn.execute(
            'SELECT COUNT(*) as cnt FROM user_interests WHERE user_id=?', (user_id,)
        ).fetchone()
        return (row['cnt'] if row else 0) > 0
    except Exception:
        return False


# ── Field definition ──
# Each entry: (field_key, display_name, check_fn)
# check_fn receives a dict {user, profile} and returns bool
FIELD_DEFS = [
    ('display_name',     '显示名',     lambda u, p: bool((u.get('display_name') or '').strip())),
    ('avatar_url',       '头像',       lambda u, p: bool((u.get('avatar_url') or '').strip())),
    ('phone_verified',   '手机验证',   lambda u, p: u.get('phone_verified', 0) == 1),
    ('gender',           '性别',       lambda u, p: bool(p and (p.get('gender') or '').strip())),
    ('birth_date',       '出生日期',   lambda u, p: bool(p and (p.get('birth_date') or '').strip())),
    ('profile_detail',   '详细资料',   lambda u, p: bool(p and (
        p.get('industry_id') or p.get('career_id') or
        (p.get('interests') or '[]') not in ('[]', '') or
        bool((p.get('bio') or '').strip())
    ))),
    ('interests_set',    '兴趣标签',   lambda u, p: _has_user_interests(u['id'])),
    ('email_verified',   '邮箱验证',   lambda u, p: u.get('email_verified', 0) == 1),
]


def calc_completion(user_id):
    """
    Calculate profile completion percentage and detailed breakdown.
    Returns dict: { completion: int, items: [{key, name, done}], total_fields: int, filled: int }
    """
    conn = _get_conn()
    try:
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            return {'completion': 0, 'items': [], 'total_fields': len(FIELD_DEFS), 'filled': 0}
        user = dict(user)
        prof = conn.execute('SELECT * FROM user_profiles WHERE user_id=?', (user_id,)).fetchone()
        prof = dict(prof) if prof else {}

        items = []
        filled = 0
        for key, name, check_fn in FIELD_DEFS:
            done = check_fn(user, prof)
            items.append({'key': key, 'name': name, 'done': done})
            if done:
                filled += 1

        total = len(FIELD_DEFS)
        completion = (filled * 100) // total if total > 0 else 0

        return {
            'completion': completion,
            'items': items,
            'total_fields': total,
            'filled': filled,
        }
    finally:
        conn.close()


def save_completion(user_id):
    """Calculate and persist completion_percentage + timestamp."""
    result = calc_completion(user_id)
    pct = result['completion']
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE users SET completion_percentage=?, completion_last_updated=datetime('now') WHERE id=?",
            (pct, user_id)
        )
        conn.commit()
    finally:
        conn.close()
    return result


def check_milestone_rewards(user_id):
    """
    After profile update, check all unclaimed reward rules and issue rewards.
    Returns list of issued rewards.
    """
    conn = _get_conn()
    issued = []
    try:
        # Get current user state
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            return issued
        user = dict(user)
        prof = conn.execute('SELECT * FROM user_profiles WHERE user_id=?', (user_id,)).fetchone()
        prof = dict(prof) if prof else {}

        # Get completion
        comp_result = calc_completion(user_id)
        completion_pct = comp_result['completion']

        # Load all active rules
        rules = conn.execute('SELECT * FROM reward_rules WHERE is_active=1 ORDER BY sort_order').fetchall()

        for rule in rules:
            rule = dict(rule)
            # Check if already claimed
            claimed = conn.execute(
                'SELECT id FROM reward_claims WHERE user_id=? AND rule_id=?',
                (user_id, rule['id'])
            ).fetchone()
            if claimed:
                continue

            # Evaluate condition
            match = False
            cond_key = rule['condition_key']
            cond_val = rule['condition_value']

            if cond_key == 'completion_percentage':
                threshold = int(cond_val)
                if completion_pct >= threshold:
                    match = True
            elif cond_key == 'phone_verified':
                if user.get('phone_verified', 0) == 1:
                    match = True
            elif cond_key == 'email_verified':
                if user.get('email_verified', 0) == 1:
                    match = True
            elif cond_key == 'avatar_set':
                if bool(user.get('avatar_url', '').strip()):
                    match = True
            elif cond_key == 'has_profile':
                if prof and any([
                    prof.get('gender'), prof.get('birth_date'),
                    prof.get('industry_id'), prof.get('career_id'),
                    prof.get('interests', '[]') not in ('[]', ''),
                    prof.get('bio', '').strip()
                ]):
                    match = True
            else:
                # Generic field check on user or profile
                if cond_key in user:
                    if str(user[cond_key]) == cond_val:
                        match = True
                elif prof and cond_key in prof:
                    if str(prof[cond_key]) == cond_val:
                        match = True

            if not match:
                continue

            # Issue reward
            coupon_id = None
            if rule['reward_type'] == 'coupon' and rule['reward_id']:
                # Create a coupon redemption for this user
                # Find the coupon template
                coupon = conn.execute(
                    'SELECT * FROM coupons WHERE id=? AND is_active=1',
                    (rule['reward_id'],)
                ).fetchone()
                if coupon:
                    coupon = dict(coupon)
                    # Insert into coupon_redemptions
                    now = __import__('datetime').datetime.now().isoformat()
                    # We create a personal coupon assignment by inserting into coupon_redemptions
                    # The coupon system uses coupon_redemptions to track usage
                    cur = conn.execute(
                        'INSERT INTO coupon_redemptions (coupon_id, user_id, order_no, discount_fen, created_at) VALUES (?,?,?,?,?)',
                        (coupon['id'], user_id, 'reward_' + str(rule['id']), coupon.get('value', 0), now)
                    )
                    coupon_id = cur.lastrowid

            # Record claim
            conn.execute(
                'INSERT INTO reward_claims (user_id, rule_id, coupon_id) VALUES (?,?,?)',
                (user_id, rule['id'], coupon_id)
            )
            issued.append({
                'rule_id': rule['id'],
                'rule_name': rule['name'],
                'reward_type': rule['reward_type'],
                'reward_name': rule.get('reward_name', ''),
                'coupon_id': coupon_id,
            })

        if issued:
            conn.commit()
            # Send notifications for each issued reward
            try:
                from services.notification_service import send_notification_by_event
                for item in issued:
                    send_notification_by_event(
                        'reward.issued',
                        user_id,
                        {'reward_name': item['reward_name'] or item['rule_name']}
                    )
            except ImportError:
                pass  # notification service not available, silently skip

    except Exception as e:
        print(f'[RewardChecker] Error for user {user_id}: {e}', file=sys.stderr)
        conn.rollback()
    finally:
        conn.close()

    return issued


def refresh_and_check(user_id):
    """Convenience: save completion + check rewards. Returns completion result + issued rewards."""
    result = save_completion(user_id)
    issued = check_milestone_rewards(user_id)
    result['rewards_issued'] = issued
    return result
