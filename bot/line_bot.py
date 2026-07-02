#!/usr/bin/env python3
"""LINE Bot — Webhook-based message handler.

Environment variables:
    LINE_CHANNEL_ACCESS_TOKEN
    LINE_CHANNEL_SECRET

Routes to register in platform/app.py:
    @app.route('/bot/line/webhook', methods=['POST'])
    def line_webhook():
        return bot.handle_webhook(request.get_data(), request.headers)
"""
import os, json, hashlib, hmac, base64, logging
from typing import Optional

logger = logging.getLogger(__name__)

API_BASE = 'https://api.line.me/v2/bot'


class LineBot:
    """LINE Messaging API Bot."""

    def __init__(self):
        self.channel_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
        self.channel_secret = os.environ.get('LINE_CHANNEL_SECRET', '')

    def is_configured(self) -> bool:
        return bool(self.channel_token)

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.channel_token}',
            'Content-Type': 'application/json',
        }

    def verify_signature(self, raw_body: bytes, signature: str) -> bool:
        """Verify LINE webhook signature."""
        if not self.channel_secret:
            return False
        expected = base64.b64encode(
            hmac.new(self.channel_secret.encode(), raw_body, hashlib.sha256).digest()
        ).decode()
        return hmac.compare_digest(expected, signature)

    def reply_message(self, reply_token: str, text: str) -> dict:
        """Reply to a user message."""
        if not self.is_configured():
            return {'success': False, 'error': 'Bot not configured'}
        try:
            import urllib.request
            body = json.dumps({
                'replyToken': reply_token,
                'messages': [{'type': 'text', 'text': text}],
            }).encode()
            req = urllib.request.Request(
                f'{API_BASE}/message/reply',
                data=body, headers=self._headers(), method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read().decode())
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def handle_webhook(self, raw_body: bytes, headers: dict) -> dict:
        """Process incoming webhook from LINE."""
        if not self.is_configured():
            return {'ok': False, 'error': 'Bot not configured'}

        signature = headers.get('X-Line-Signature', '')
        if not self.verify_signature(raw_body, signature):
            return {'ok': False, 'error': 'Invalid signature'}, 400

        try:
            body = json.loads(raw_body.decode())
            events = body.get('events', [])
            for event in events:
                if event.get('type') == 'message':
                    msg = event.get('message', {})
                    reply_token = event.get('replyToken', '')
                    text = msg.get('text', '')
                    if reply_token and text:
                        self.reply_message(reply_token, text)
            return {'ok': True}
        except Exception as e:
            logger.exception(f'[LineBot] webhook error: {e}')
            return {'ok': False, 'error': str(e)}
