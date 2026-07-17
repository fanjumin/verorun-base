#!/usr/bin/env python3
"""
Identity Verification Plugin — 实名认证插件
============================================
提供支付宝实人认证的前端配置面板。
认证流程由 auth-center 路由处理，插件提供管理 UI。
- 独立数据库：verification.db（认证请求记录）
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin


class VerificationPlugin(BasePlugin):
    name = 'verification'
    version = '0.1.0'
    description = 'Identity Verification — real-name verification via Alipay identity service'
    author = 'VeroRun'

    def on_install(self, registry):
        from .models import init_verification_db, migrate_from_main_db
        init_verification_db()
        migrate_from_main_db()
        return True

    def on_enable(self, registry):
        from .models import init_verification_db
        init_verification_db()
        print(_'[VerificationPlugin] ✅ Real-name verification plugin is enabled (verification.db)')
        return True

    def register_routes(self):
        """返回空列表 — 认证路由保留在 auth-center"""
        return []

    def on_disable(self, registry):
        print(_'[VerificationPlugin] ⚠️ Real-name verification plugin is disabled')
        return True

    # ── 对外接口 ──

    def initiate_verification(self, user_id, return_url=''):
        from .services import initiate_verification as _i
        return _i(user_id, return_url)

    def verify_callback(self):
        from .services import verify_callback as _v
        return _v()
