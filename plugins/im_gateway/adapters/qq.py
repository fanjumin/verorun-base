#!/usr/bin/env python3
"""IM Gateway — QQ 适配器

QQ 开放平台无统一短测 token 接口，仅做参数校验。
"""
from .base import BaseIMAdapter
from i18n import _


class QQAdapter(BaseIMAdapter):
    channel = 'qq'
    supports_test = False

    def get_config_fields(self):
        return [
            {'key': 'app_id', 'label': 'App ID', 'type': 'text'},
            {'key': 'app_key', 'label': 'App Key', 'type': 'password'},
            {'key': 'admin_uin', 'label': 'Admin UIN', 'type': 'text'},
        ]

    def test_connection(self, data):
        app_id = (data.get('app_id') or '').strip()
        app_key = (data.get('app_key') or '').strip()
        if not app_id or not app_key:
            return False, _('App ID 和 App Key 不能为空')
        # 无标准单次 token 接口，仅参数校验
        return True, _('QQ 凭证已接受（未做第三方 API 调用）')
