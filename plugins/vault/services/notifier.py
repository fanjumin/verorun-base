#!/usr/bin/env python3
"""
Vault Notifier — Multi-channel alert notification.

Supports: Email / Webhook / Feishu / DingTalk / WeCom
"""

import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List


class VaultNotifier:
    """Unified notification dispatcher."""

    def __init__(self):
        self._channels = self._load_channels()

    def _load_channels(self) -> List[Dict]:
        """Load enabled notification channels from plugin config."""
        channels = []
        try:
            from plugins._base.db import get_raw_connection
            conn = get_raw_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT config FROM plugin_registry WHERE identifier = 'vault'"
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row and row[0]:
                cfg = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                notify = cfg.get('notifications', {})
                if notify.get('email', {}).get('enabled'):
                    channels.append({'type': 'email', 'config': notify['email']})
                if notify.get('webhook', {}).get('enabled'):
                    channels.append({'type': 'webhook', 'config': notify['webhook']})
                if notify.get('feishu', {}).get('enabled'):
                    channels.append({'type': 'feishu', 'config': notify['feishu']})
                if notify.get('dingtalk', {}).get('enabled'):
                    channels.append({'type': 'dingtalk', 'config': notify['dingtalk']})
        except Exception as e:
            print(f'[Vault] Failed to load notification channels: {e}')

        return channels

    def send(self, event: str, message: str, level: str = 'info',
             details: Dict = None) -> List[Dict]:
        """
        Send notification to all enabled channels.

        Args:
            event: event type (backup.success, backup.failed, storage.low, health.warning)
            message: notification message
            level: severity level (info, warning, error, critical)
            details: additional details
        """
        results = []
        for channel in self._channels:
            handler = {
                'email': self._send_email,
                'webhook': self._send_webhook,
                'feishu': self._send_feishu,
                'dingtalk': self._send_dingtalk,
            }.get(channel['type'])

            if handler:
                try:
                    ok = handler(event, message, level, details, channel['config'])
                    results.append({'channel': channel['type'], 'sent': ok})
                except Exception as e:
                    results.append({
                        'channel': channel['type'],
                        'sent': False,
                        'error': str(e),
                    })

        return results

    def _send_email(self, event, message, level, details, config) -> bool:
        recipients = config.get('recipients', [])
        if not recipients:
            return False

        msg = MIMEMultipart()
        msg['Subject'] = f'[VeroRun Vault] [{level.upper()}] {event}'
        msg['From'] = config.get('smtp_user', '')
        msg['To'] = ', '.join(recipients)

        body = f"""
        <h2>{event}</h2>
        <p><strong>Level:</strong> {level}</p>
        <p>{message}</p>
        <pre>{json.dumps(details or {}, indent=2)}</pre>
        """
        msg.attach(MIMEText(body, 'html'))

        try:
            smtp_host = config.get('smtp_host', '')
            smtp_port = int(config.get('smtp_port', 465))
            smtp_user = config.get('smtp_user', '')
            smtp_password = config.get('smtp_password', '')

            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as smtp:
                    smtp.login(smtp_user, smtp_password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
                    smtp.starttls()
                    smtp.login(smtp_user, smtp_password)
                    smtp.send_message(msg)
            return True
        except Exception as e:
            print(f'[Vault] Email notification failed: {e}')
            return False

    def _send_webhook(self, event, message, level, details, config) -> bool:
        url = config.get('url', '')
        if not url:
            return False
        payload = {
            'event': event,
            'level': level,
            'message': message,
            'details': details,
            'timestamp': datetime.utcnow().isoformat(),
        }
        headers = config.get('headers', {})
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        return resp.status_code < 400

    def _send_feishu(self, event, message, level, details, config) -> bool:
        """Feishu bot notification."""
        url = config.get('webhook_url', '')
        if not url:
            return False

        level_colors = {'info': 'blue', 'warning': 'yellow',
                        'error': 'red', 'critical': 'purple'}
        payload = {
            'msg_type': 'interactive',
            'card': {
                'header': {
                    'title': {'tag': 'plain_text', 'content': f'Vault {event}'},
                    'template': level_colors.get(level, 'blue'),
                },
                'elements': [
                    {'tag': 'div', 'text': {'tag': 'lark_md', 'content': message}},
                    {'tag': 'hr'},
                    {'tag': 'div', 'text': {
                        'tag': 'lark_md',
                        'content': (
                            f"Level: **{level}**\n"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        ),
                    }},
                ],
            },
        }
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        return result.get('code') == 0

    def _send_dingtalk(self, event, message, level, details, config) -> bool:
        """DingTalk bot notification."""
        url = config.get('webhook_url', '')
        if not url:
            return False
        payload = {
            'msgtype': 'markdown',
            'markdown': {
                'title': f'Vault - {event}',
                'text': f"## Vault {event}\n\n**Level:** {level}\n\n{message}",
            },
        }
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json().get('errcode') == 0
