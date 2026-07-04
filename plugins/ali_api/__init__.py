#!/usr/bin/env python3
"""
1688 Supply Chain Plugin — AliApiPlugin
=========================================
Provides 1688 product sourcing, AI optimization, and local publishing.

i18n: Uses self.t() for all user-facing strings.
      Translations in:  plugins/ali_api/i18n/{locale}.yml
"""

from plugins.base import BasePlugin
from .plugin_i18n import set_plugin


class AliApiPlugin(BasePlugin):
    name = 'ali_api'
    version = '0.2.1'
    description = '1688 供应链采集插件 — 商品搜索、AI 优化、本地商城发布'
    author = 'VeroRun'

    def on_enable(self, registry):
        """插件启用时设置 i18n 桥接"""
        set_plugin(self)
        return True

    def register_routes(self):
        """注册路由蓝图"""
        from .routes.admin import ali_admin_bp
        return [ali_admin_bp]
