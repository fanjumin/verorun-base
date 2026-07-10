#!/usr/bin/env python3
"""IM Gateway — 钉钉适配器

迁移自 auth-center/routes/admin.py。使用 appkey/appsecret 获取 access_token 测试连接。
"""
from .base import BaseIMAdapter


class DingTalkAdapter(BaseIMAdapter):
    channel = 'dingtalk'
    supports_test = True

    def get_config_fields(self):
        return [
            {'key': 'app_key', 'label': 'AppKey', 'type': 'text'},
            {'key': 'app_secret', 'label': 'AppSecret', 'type': 'password'},
            {'key': 'agent_id', 'label': 'AgentId', 'type': 'text'},
            {'key': 'corp_id', 'label': 'CorpId', 'type': 'text'},
        ]

    def test_connection(self, data):
        app_key = (data.get('app_key') or '').strip() or (data.get('appId') or '').strip()
        app_secret = (data.get('app_secret') or '').strip() or (data.get('appSecret') or '').strip()
        if not app_key or not app_secret:
            return False, 'AppKey 和 AppSecret 不能为空'
        try:
            import requests as _req
            resp = _req.get(
                f'https://oapi.dingtalk.com/gettoken?appkey={app_key}&appsecret={app_secret}',
                timeout=10
            )
            rd = resp.json()
            if rd.get('access_token'):
                return True, '钉钉连接成功！'
            return False, f"钉钉返回: {rd.get('errmsg', '未知')} (errcode={rd.get('errcode')})"
        except Exception as e:
            return False, f'连接失败: {str(e)}'
