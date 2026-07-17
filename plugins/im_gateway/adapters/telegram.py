#!/usr/bin/env python3
"""IM Gateway — Telegram 适配器"""
import os
import json as _json
import urllib.request as _ur

from .base import BaseIMAdapter


class TelegramAdapter(BaseIMAdapter):
    channel = 'telegram'
    supports_test = True

    def get_config_fields(self):
        return [
            {'key': 'bot_token', 'label': 'Bot Token', 'type': 'password'},
            {'key': 'webhook_url', 'label': 'Webhook URL', 'type': 'text'},
            {'key': 'allow_groups', 'label': 'Allow Group Chat (true/false)', 'type': 'text'},
        ]

    def test_connection(self, data):
        token = (data.get('bot_token') or '').strip()
        if not token:
            return False, 'Bot Token 不能为空'
        try:
            resp = _json.loads(_ur.urlopen(
                _ur.Request(f'https://api.telegram.org/bot{token}/getMe'),
                timeout=10
            ).read())
            if resp.get('ok'):
                bot_name = resp['result'].get('first_name', '')
                return True, f'Telegram 连接成功！Bot: {bot_name}'
            return False, f"Telegram 返回错误: {resp.get('description', '未知')}"
        except Exception as e:
            return False, f'连接失败: {str(e)}'

    def get_env_fallback(self):
        cfg = {}
        token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        webhook = os.environ.get('TELEGRAM_WEBHOOK_URL', '')
        if token:
            cfg['bot_token'] = self._mask(token)
        if webhook:
            cfg['webhook_url'] = webhook
        return cfg
