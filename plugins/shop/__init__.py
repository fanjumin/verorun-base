#!/usr/bin/env python3
"""
Shop/Mall Plugin — 商城核心插件
================================
Product management, categories, orders, cart, checkout.
Decoupled from core system as a standalone plugin.
"""
from i18n import _
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin


class ShopPlugin(BasePlugin):
    name = 'shop'
    version = '1.0.0'
    description = 'Shop/Mall — Product & Order Management'
    author = 'VeroRun'

    def on_install(self, registry):
        self._init_db()
        return True

    def on_enable(self, registry):
        self._init_db()
        print(_('[ShopPlugin] ✅ Shop plugin enabled'))
        return True

    def _init_db(self):
        from .models.database import init_shop_db
        init_shop_db()

    def register_routes(self):
        from .routes.admin import shop_admin_bp
        from .routes.public import shop_public_bp
        print('[ShopPlugin] ✅ /shop/* routes registered')
        return [shop_admin_bp, shop_public_bp]

    def on_disable(self, registry):
        print(_('[ShopPlugin] ⚠️ Shop plugin disabled'))
        return True
