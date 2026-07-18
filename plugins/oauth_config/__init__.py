#!/usr/bin/env python3
"""
OAuth Login Config Plugin — 完整的第三方登录插件
===================================================
自 v0.13.5 起，本插件集成了：
1. 后台 OAuth 配置管理（CRUD + UI）
2. OAuth 登录/回调路由（抖音/微信/支付宝/Google/GitHub/Facebook/Telegram）
3. Provider 实现（多租户 DB + 环境变量兜底）

架构：所有 OAuth 相关代码收敛至本插件，auth-center 通过 try/except 调用。
"""
import os
import sys

# 不添加 sys.path — 由宿主服务（admin / auth-center）负责路径设置

# 延迟加载 BasePlugin：admin 加载 oauth_cfg_bp 时 plugin_manager 可能未就绪
try:
    from plugin_manager.base import BasePlugin
    _BASE_CLS = BasePlugin
except ImportError:
    _BASE_CLS = object

_t = lambda text: text

def init_i18n(t_fn):
    global _t
    _t = t_fn

class OauthConfigPlugin(_BASE_CLS):
    name = 'oauth_config'
    version = '1.0.0'
    description = 'OAuth 第三方登录 — 完整的登录/回调/配置管理插件'
    author = 'VeroRun'

    def on_enable(self, registry):
        init_i18n(self.t)
        # 自动初始化插件独立数据库
        from .models import init_oauth_tables
        init_oauth_tables()
        print(_('[OauthConfigPlugin] ✅ OAuth login & configuration plugin enabled'))
        return True

    def register_routes(self):
        """注册后台配置路由（首次加载时自动初始化独立数据库）"""
        from .models import init_oauth_tables
        init_oauth_tables()
        from .routes.admin import oauth_cfg_bp
        return [oauth_cfg_bp]

    def on_disable(self, registry):
        print(_('[OauthConfigPlugin] ⚠️ OAuth plugin disabled'))
        return True
