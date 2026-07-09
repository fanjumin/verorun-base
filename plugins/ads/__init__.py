#!/usr/bin/env python3
"""
Ad Management Plugin — 广告管理插件
=====================================
独立数据库 ads.db，不依赖主库。
提供 /admin/ads API 和管理界面。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin
from .models import init_ad_db
from .routes import ads_bp


class AdsPlugin(BasePlugin):
    name = 'ads'
    version = '0.1.0'
    description = 'Ad Management — Create, edit, and manage ad placements across the site'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立数据库"""
        init_ad_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库（幂等）"""
        init_ad_db()
        print('[AdsPlugin] ✅ 广告管理插件已启用')
        return True

    def register_routes(self):
        """注册 Flask 路由"""
        return [ads_bp]

    def on_disable(self, registry):
        """禁用时清理"""
        print('[AdsPlugin] ⚠️  广告管理插件已禁用')
        return True