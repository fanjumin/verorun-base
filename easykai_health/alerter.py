#!/usr/bin/env python3
"""
Health Monitor — 告警模块
=========================
当检查项状态异常时，通过邮件/站内信/Webhook 通知管理员。
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
    评估检查结果并触发告警。
    遍历 alert_config 中的规则，检查是否需要发送告警。
    """
    with get_db() as conn:
        rules = conn.execute(
            'SELECT * FROM alert_config WHERE is_active=1'
        ).fetchall()

        for rule in rules:
            rule = dict(rule)
            # 找到与此规则匹配的检查结果
            relevant_results = [
                r for r in check_results
                if (rule['check_key'] == '*' or r.get('check_key') == rule['check_key'])
                and r.get('status') in ('warning', 'error')
            ]

            if not relevant_results:
                continue

            # 按 check_key 分组，检查连续失败次数
            for result in relevant_results:
                key = result.get('check_key', '')
                status = result.get('status', '')

                # 检查连续失败次数
                consecutive_fails = count_consecutive_fails(conn, key)
                if consecutive_fails < rule.get('consecutive', 1):
                    continue

                # 检查是否已经为此事件发过告警（避免重复）
                recent_alert = conn.execute(
                    "SELECT id FROM alert_history WHERE check_key=? AND status=? "
                    "AND created_at>=datetime('now', '-1 hour') LIMIT 1",
                    (key, status)
                ).fetchone()
                if recent_alert:
                    continue

                # 发送告警
                notify_method = rule.get('notify_method', 'email')
                message = f'[健康巡检] {result.get("check_name", key)} 状态: {status} - {result.get("message", "")}'

                # 记录告警
                conn.execute(
                    'INSERT INTO alert_history (alert_config_id, check_key, check_name, run_id, status, message, notify_method) '
                    'VALUES (?,?,?,?,?,?,?)',
                    (rule['id'], key, result.get('check_name', key), run_id, status, message, notify_method)
                )
                conn.commit()

                # 实际发送通知
                send_notification(notify_method, message, rule)


def count_consecutive_fails(conn, check_key: str) -> int:
    """统计某个检查项连续失败次数"""
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
    """发送告警通知"""
    if method in ('email', '全部'):
        _send_email_alert(message)
    if method in ('站内信', '全部'):
        _send_internal_message(message)
    if method in ('webhook', '全部'):
        _send_webhook(message, rule.get('webhook_url', ''))


def _send_email_alert(message: str):
    """通过邮件发送告警（使用现有邮件服务）"""
    try:
        from easykai_auth.services.email_service import send_email
        # 获取管理员邮箱
        with get_db() as conn:
            admins = conn.execute(
                "SELECT email FROM users WHERE is_admin=1 AND email IS NOT NULL AND email!=''"
            ).fetchall()
        for admin in admins:
            send_email(
                to=admin['email'],
                subject='⚠️ 系统健康巡检告警',
                body=f'<div style="background:#0d1117;color:#c9d1d9;padding:20px;font-family:sans-serif">'
                     f'<h2 style="color:#f85149">系统告警</h2>'
                     f'<p>{message}</p>'
                     f'<p style="color:#8b949e;font-size:12px">发送时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
                     f'<p><a href="{deploy.url("agent")}/admin" style="color:#58a6ff">前往管理后台查看详情</a></p>'
                     f'</div>',
            )
    except Exception as e:
        print(f'[HealthAlert] 邮件发送失败: {e}')


def _send_internal_message(message: str):
    """站内信通知"""
    try:
        with get_db() as conn:
            admins = conn.execute("SELECT id FROM users WHERE is_admin=1").fetchall()
            for admin in admins:
                conn.execute(
                    "INSERT INTO admin_notifications (user_id, title, content, is_read, created_at) "
                    "VALUES (?, ?, ?, 0, datetime('now'))",
                    (admin['id'], '⚠️ 系统健康告警', message)
                )
            conn.commit()
    except Exception as e:
        print(f'[HealthAlert] 站内信发送失败: {e}')


def _send_webhook(message: str, webhook_url: str):
    """Webhook 通知"""
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
        print(f'[HealthAlert] Webhook 发送失败: {e}')
