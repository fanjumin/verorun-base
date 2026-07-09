#!/usr/bin/env python3
"""
Enterprise Verification Plugin — 企业认证插件
================================================
独立数据库 enterprise_verify.db
提供 OCR 营业执照识别 + AI 自动审核 + 管理端审批
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin
from .models import get_ev_db, init_ev_db


class EnterpriseVerifyPlugin(BasePlugin):
    name = 'enterprise_verify'
    version = '0.1.0'
    description = 'Enterprise Verification — OCR license recognition + AI auto-audit'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立数据库"""
        init_ev_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库（幂等）"""
        init_ev_db()
        print('[EnterpriseVerifyPlugin] ✅ 企业认证插件已启用')
        return True

    def register_routes(self):
        """注册 Flask 路由（管理端 + 用户端）"""
        from .routes_admin import ev_admin_bp
        from .routes_user import ev_user_bp
        return [ev_admin_bp, ev_user_bp]

    def on_disable(self, registry):
        """禁用时清理"""
        print('[EnterpriseVerifyPlugin] ⚠️  企业认证插件已禁用')
        return True