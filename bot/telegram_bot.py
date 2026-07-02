#!/usr/bin/env python3
"""Telegram Bot — Webhook-based message handler.

Environment variables:
    TELEGRAM_BOT_TOKEN
    TELEGRAM_WEBHOOK_URL   (e.g. https://your-platform-domain.com/bot/telegram/webhook)

Usage:
    from bot.telegram_bot import TelegramBot
    bot = TelegramBot()

Routes to register in platform/app.py:
    @app.route('/bot/telegram/webhook', methods=['POST'])
    def telegram_webhook():
        return bot.handle_webhook(request.get_data(), request.headers)
"""
import os, json, hashlib, hmac, logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

API_BASE = 'https://api.telegram.org'


class TelegramBot:
    """Telegram Bot — handles messages via webhook."""

    def __init__(self):
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
        self.webhook_url = os.environ.get('TELEGRAM_WEBHOOK_URL', '')
        self._me = None

    def is_configured(self) -> bool:
        return bool(self.token)

    def _api_url(self, method: str) -> str:
        return f'{API_BASE}/bot{self.token}/{method}'

    def set_webhook(self) -> dict:
        """Register webhook URL with Telegram."""
        if not self.is_configured():
            return {'success': False, 'error': 'Bot not configured'}
        try:
            import urllib.request, urllib.parse
            data = urllib.parse.urlencode({'url': self.webhook_url}).encode()
            req = urllib.request.Request(self._api_url('setWebhook'), data=data)
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read().decode())
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def send_message(self, chat_id: int, text: str,
                     parse_mode: str = 'HTML') -> dict:
        """Send a text message to a chat."""
        if not self.is_configured():
            return {'success': False, 'error': 'Bot not configured'}
        try:
            import urllib.request, urllib.parse
            data = urllib.parse.urlencode({
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
            }).encode()
            req = urllib.request.Request(self._api_url('sendMessage'), data=data)
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read().decode())
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def handle_webhook(self, raw_body: bytes, headers: dict) -> dict:
        """Process incoming webhook update from Telegram."""
        if not self.is_configured():
            return {'ok': False, 'error': 'Bot not configured'}
        try:
            update = json.loads(raw_body.decode())
            message = update.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')

            if not chat_id or not text:
                return {'ok': True}  # Ignore non-text messages

            # Simple echo / help handler (extend with AI integration)
            response = self._generate_reply(text, message)
            self.send_message(chat_id, response)
            return {'ok': True}
        except Exception as e:
            logger.exception(f'[TelegramBot] webhook error: {e}')
            return {'ok': False, 'error': str(e)}

    def _generate_reply(self, text: str, message: dict) -> str:
        """Generate a reply to a user message.
        Override with AI-powered response generation.
        """
        cmd = text.strip().lower()
        if cmd == '/start':
            return ('Hello! I am the EasyKai AI Assistant bot.\n\n'
                    'Commands:\n'
                    '/help — Show available commands\n'
                    '/status — Check your subscription status\n'
                    '/site — Manage your website')
        elif cmd == '/help':
            return ('Available commands:\n'
                    '/start — Start the bot\n'
                    '/help — This message\n'
                    '/status — Your subscription info')
        return (f'You said: {text}\n\n'
                'Type /help to see available commands.')
