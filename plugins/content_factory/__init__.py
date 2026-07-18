#!/usr/bin/env python3
"""
Content Factory Plugin — 内容工厂插件
========================================
独立数据库 content_factory.db
提供多源采集、AI加工、审核发布、Skill推送、静态页面生成
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin
from .models import get_cf_db, init_cf_db

# 模块级 i18n 引用，由 on_enable 注入
_t = lambda text: text


def init_i18n(t_fn):
    """供插件启用时注入 i18n 翻译函数"""
    global _t
    _t = t_fn


class ContentFactoryPlugin(BasePlugin):
    name = 'content_factory'
    version = '1.0.0'
    description = 'Content Factory — Collection, AI processing, review, publishing, skill push'
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

    def set_config_value(self, key: str, value) -> bool:
        """优先 PluginManager"""
        try:
            mgr = getattr(self.app.extensions, 'get', lambda x: None)('plugin_manager')
            if mgr:
                mgr.set_config_batch(self.identifier, {key: str(value)}, coerce=True)
                self._config[key] = value
                return True
        except Exception:
            pass
        self._config[key] = value
        return True

    def on_install(self, registry):
        """安装时初始化独立数据库"""
        init_cf_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库 + i18n（幂等）"""
        init_cf_db()
        init_i18n(self.t)
        print(_('[ContentFactoryPlugin] ✅ Content Factory plugin enabled'))
        return True

    def register_routes(self):
        """注册 Flask 路由"""
        from .routes import cf_bp
        return [cf_bp]

    def on_disable(self, registry):
        """禁用时清理"""
        print(_('[ContentFactoryPlugin] ⚠️ Content Factory plugin disabled'))
        return True