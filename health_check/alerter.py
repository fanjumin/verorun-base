#!/usr/bin/env python3
"""
Health Check — Alert Module
============================
Evaluate check results and notify administrators via email/internal message/webhook
when a check status is abnormal.
"""

import os, sys, json, json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))

from .models import get_db


def evaluate_and_alert(run_id: int, check_results: List[dict]):
    """
    Evaluate check results and trigger alerts.
    Iterates over alert_config rules and evaluates whether alerts are needed.
    """
    with get_db() as conn:
        rules = conn.execute(
            'SELECT * FROM alert_config WHERE is_active=1'
        ).fetchall()

        for rule in rules:
            rule = dict(rule)
            # Find matching check results
            relevant_results = [
                r for r in check_results
                if (rule['check_key'] == '*' or r.get('check_key') == rule['check_key'])
                and r.get('status') in ('warning', 'error')
            ]

            if not relevant_results:
                continue

            # Group by check_key and check consecutive failures
            for result in relevant_results:
                key = result.get('check_key', '')
                status = result.get('status', '')

                # Check consecutive failure count
                consecutive_fails = count_consecutive_fails(conn, key)
                if consecutive_fails < rule.get('consecutive', 1):
                    continue

                # Avoid duplicate alerts for the same event within 1 hour
                recent_alert = conn.execute(
                    "SELECT id FROM alert_history WHERE check_key=? AND status=? "
                    "AND created_at>=datetime('now', '-1 hour') LIMIT 1",
                    (key, status)
                ).fetchone()
                if recent_alert:
                    continue

                # Send alert
                notify_method = rule.get('notify_method', 'email')
                message = f'[Health Check] {result.get("check_name", key)} status: {status} - {result.get("message", "")}'

                # Record alert
                conn.execute(
                    'INSERT INTO alert_history (alert_config_id, check_key, check_name, run_id, status, message, notify_method) '
                    'VALUES (?,?,?,?,?,?,?)',
                    (rule['id'], key, result.get('check_name', key), run_id, status, message, notify_method)
                )
                conn.commit()

                # Send notification
                send_notification(notify_method, message, rule)


def count_consecutive_fails(conn, check_key: str) -> int:
    """Count consecutive failures for a given check key."""
    recent = conn.execute(
        "SELECT status FROM check_history WHERE check_key=? "
        "ORDER BY checked_at DESC LIMIT 5",
        (check_key,)
    ).fetchall()

    count = 0
    for r in recent:
        if r['status'] in ('warning', 'error'):
            count += 1
        else:
            break
    return count


def send_notification(method: str, message: str, rule: dict):
    """Send alert notification via the specified method."""
    if method in ('email', 'all'):
        _send_email_alert(message)
    if method in ('internal', 'all'):
        _send_internal_message(message)
    if method in ('webhook', 'all'):
        _send_webhook(message, rule.get('webhook_url', ''))


def _send_email_alert(message: str):
    """Send alert via email (uses existing email service)."""
    try:
        from easykai_auth.services.email_service import send_email
        # Get admin email addresses
        with get_db() as conn:
            admins = conn.execute(
                "SELECT email FROM users WHERE is_admin=1 AND email IS NOT NULL AND email!=''"
            ).fetchall()
        for admin in admins:
            send_email(
                to=admin['email'],
                subject='⚠️ System Health Alert',
                body=f'<div style="background:#0d1117;color:#c9d1d9;padding:20px;font-family:sans-serif">'
                     f'<h2 style="color:#f85149">System Alert</h2>'
                     f'<p>{message}</p>'
                     f'<p style="color:#8b949e;font-size:12px">Sent at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
                     f'<p><a href="{deploy.url("agent")}/admin" style="color:#58a6ff">View details in admin panel</a></p>'
                     f'</div>',
            )
    except Exception as e:
        print(f'[HealthAlert] Failed to send email: {e}')


def _send_internal_message(message: str):
    """Send internal notification."""
    try:
        with get_db() as conn:
            admins = conn.execute("SELECT id FROM users WHERE is_admin=1").fetchall()
            for admin in admins:
                conn.execute(
                    "INSERT INTO admin_notifications (user_id, title, content, is_read, created_at) "
                    "VALUES (?, ?, ?, 0, datetime('now'))",
                    (admin['id'], '⚠️ System Health Alert', message)
                )
            conn.commit()
    except Exception as e:
        print(f'[HealthAlert] Failed to send internal message: {e}')


def _send_webhook(message: str, webhook_url: str):
    """Send alert via webhook."""
    if not webhook_url:
        return
    try:
        import urllib.request
        data = json.dumps({
            'event': 'health_alert',
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'source': 'health-monitor',
        }).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=data,
                                     headers={'Content-Type': 'application/json'},
                                     method='POST')
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f'[HealthAlert] Failed to send webhook: {e}')
