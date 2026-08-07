#!/usr/bin/env python3
"""MiniAppDeployer — Deploy / configure mini-programs on social platforms

Supports:
- Telegram: Set menu button via Bot API
- LINE: Update LIFF endpoint URL
- Douyin/WeChat: Provide manual deployment instructions (IDE upload required)
"""

import json
import logging
import urllib.request as _ur

logger = logging.getLogger(__name__)


class MiniAppDeployer:
    """Deploy mini-programs to target social media platforms.

    Usage:
        deployer = MiniAppDeployer(dev_accounts={
            'telegram': {'bot_token': '...'},
            'line': {'access_token': '...', 'liff_id': '...'},
        })
        result = deployer.deploy_telegram('https://your-domain.com/static/mini-apps/telegram/')
    """

    def __init__(self, dev_accounts: dict = None):
        """
        Args:
            dev_accounts: Dict of platform credentials, e.g.:
                {
                    'telegram': {'bot_token': '...'},
                    'line': {'channel_id': '...', 'access_token': '...'},
                    'douyin': {'app_id': '...', 'app_secret': '...'},
                    'wechat': {'app_id': '...', 'app_secret': '...'},
                }
        """
        self.dev_accounts = dev_accounts or {}

    def deploy_telegram(self, webapp_url: str, bot_token: str = None) -> dict:
        """Set Telegram Mini App menu button.

        POST https://api.telegram.org/bot{token}/setChatMenuButton

        Args:
            webapp_url: Public HTTPS URL of the deployed Mini App
            bot_token: Telegram Bot token (falls back to dev_accounts)

        Returns:
            {'success': True/False, 'data': {...}} or {'success': False, 'error': '...'}
        """
        token = bot_token or self.dev_accounts.get('telegram', {}).get('bot_token', '')
        if not token:
            return {'success': False, 'error': 'No bot_token configured'}

        try:
            payload = json.dumps({
                'menu_button': {
                    'type': 'web_app',
                    'text': 'Open App',
                    'web_app': {'url': webapp_url}
                }
            }).encode('utf-8')

            req = _ur.Request(
                f'https://api.telegram.org/bot{token}/setChatMenuButton',
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            resp = json.loads(_ur.urlopen(req, timeout=10).read())
            return {'success': resp.get('ok', False), 'data': resp}
        except Exception as e:
            logger.error(f'[Deployer] Telegram deploy failed: {e}')
            return {'success': False, 'error': str(e)}

    def deploy_line(self, liff_id: str, endpoint_url: str, channel_token: str = None) -> dict:
        """Update LINE LIFF endpoint URL.

        PUT https://api.line.me/liff/v1/apps/{liffId}

        Args:
            liff_id: LIFF application ID
            endpoint_url: Public HTTPS URL of the deployed LIFF app
            channel_token: LINE channel access token

        Returns:
            {'success': True/False, 'data': {...}} or {'success': False, 'error': '...'}
        """
        token = channel_token or self.dev_accounts.get('line', {}).get('access_token', '')
        if not token:
            return {'success': False, 'error': 'No channel access_token configured'}
        if not liff_id:
            liff_id = self.dev_accounts.get('line', {}).get('liff_id', '')

        try:
            payload = json.dumps({
                'view': {
                    'type': 'tall',
                    'url': endpoint_url
                }
            }).encode('utf-8')

            req = _ur.Request(
                f'https://api.line.me/liff/v1/apps/{liff_id}',
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                },
                method='PUT'
            )
            resp = json.loads(_ur.urlopen(req, timeout=10).read())
            return {'success': True, 'data': resp}
        except Exception as e:
            logger.error(f'[Deployer] LINE deploy failed: {e}')
            return {'success': False, 'error': str(e)}

    def get_manual_deploy_hint(self, platform: str) -> str:
        """Return manual deployment instructions for platforms that need IDE upload.

        Args:
            platform: 'douyin' or 'wechat'

        Returns:
            Multi-line deployment instruction string
        """
        hints = {
            'douyin': (
                'Douyin/Toutiao Mini-Program Deployment:\n'
                '1. Download the generated package from the admin panel\n'
                '2. Open ByteDance DevTools (字节跳动开发者工具)\n'
                '3. Import the dist/douyin/ directory\n'
                '4. Verify the app runs correctly in the simulator\n'
                '5. Click "Upload" (上传) to submit for review\n'
                '6. Wait for review approval (typically 1-3 business days)\n'
                '7. After approval, the mini-program will be live'
            ),
            'wechat': (
                'WeChat Mini-Program Deployment:\n'
                '1. Download the generated package from the admin panel\n'
                '2. Open WeChat DevTools (微信开发者工具)\n'
                '3. Import the dist/wechat/ directory\n'
                '4. Verify the app runs correctly in the simulator\n'
                '5. Click "Upload" (上传) to submit for review\n'
                '6. Wait for review approval (typically 1-7 business days)\n'
                '7. After approval, publish from the WeChat Official Account Platform'
            ),
        }
        return hints.get(platform, f'Manual deployment required for {platform}. See documentation.')
