#!/usr/bin/env python3
"""
OAuth Login Config Plugin — 第三方登录配置管理插件
====================================================
仅【逻辑解耦】：后台 OAuth 凭据配置管理（CRUD + UI）从 auth-center 迁入插件。

重要约束（与 im_gateway / social_push 不同）：
  - 【不使用独立库】。oauth_providers 表被登录回调链路（auth-center 的
    douyin_service / alipay_service / wechat_service._get_config）读取，
    必须继续留在主库。本插件通过 get_main_db() 读写主库 oauth_providers。
  - 登录回调链路（auth.py oauth_login/callback、oauth_service、各 provider
    service）完全不改，本插件不碰 JWT / SSO cookie / users 绑定。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin

# 模块级 i18n 引用，由 on_enable 注入
_t = lambda text: text


def init_i18n(t_fn):
    """供插件启用时注入 i18n 翻译函数"""
    global _t
    _t = t_fn


class OauthConfigPlugin(BasePlugin):
    name = 'oauth_config'
    version = '0.1.0'
    description = 'OAuth Login Config — 多站点第三方登录凭据管理'
    author = 'VeroRun'

    def on_enable(self, registry):
        """启用时注入 i18n（无独立库，不建表）"""
        init_i18n(self.t)
        print('[OauthConfigPlugin] ✅ OAuth 登录配置插件已启用')
        return True

    def register_routes(self):
        """注册 Flask 路由（OAuth 配置管理 API）"""
        from .routes import oauth_cfg_bp
        return [oauth_cfg_bp]

    def on_disable(self, registry):
        print('[OauthConfigPlugin] ⚠️  OAuth 登录配置插件已禁用')
        return True
