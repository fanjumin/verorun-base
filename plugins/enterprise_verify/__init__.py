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

# 模块级 i18n 引用，由 on_enable 注入
_t = lambda text: text


def init_i18n(t_fn):
    """供插件启用时注入 i18n 翻译函数"""
    global _t
    _t = t_fn


class EnterpriseVerifyPlugin(BasePlugin):
    name = 'enterprise_verify'
    version = '1.0.0'
    description = 'Enterprise Verification — OCR license recognition + AI auto-audit'
    author = 'VeroRun'

    def get_config_value(self, key: str, default=None):
        """优先 PluginManager，回退到 plugin.json 默认值"""
        try:
            mgr = getattr(self.app.extensions, 'get', lambda x: None)('plugin_manager')
            if mgr:
                pm_cfg = mgr.get_config(self.identifier) or {}
                if key in pm_cfg:
                    return pm_cfg[key]
        except Exception:
            pass
        return self._config.get(key, default)

    def on_install(self, registry):
        """安装时初始化独立数据库"""
        init_ev_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库 + i18n（幂等）"""
        init_ev_db()
        init_i18n(self.t)
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