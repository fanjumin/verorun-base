#!/usr/bin/env python3
"""
SMS Service Plugin — 短信服务插件（完全独立）
============================================
验证码发送、模板管理、提供商配置。
- 独立数据库：sms.db（不依赖主库）
- 独立 i18n：插件自带翻译文件
"""
from i18n import _
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


class SmsPlugin(BasePlugin):
    name = 'sms'
    version = '1.1.0'
    description = 'SMS Service — phone verification code sending with Aliyun/Twilio providers'
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
        """安装时初始化独立 sms.db + 迁移历史数据"""
        from .models import init_sms_db, migrate_from_main_db
        init_sms_db()
        migrate_from_main_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库 + i18n（幂等）"""
        from .models import init_sms_db
        init_sms_db()
        init_i18n(self.t)
        print(_('[SmsPlugin] ✅ SMS service plugin is enabled (sms.db)'))
        return True

    def register_routes(self):
        """注册 Flask 路由"""
        from .routes import sms_bp
        return [sms_bp]

    def on_disable(self, registry):
        """禁用时清理"""
        print(_('[SmsPlugin] ⚠️ SMS service plugin is disabled'))
        return True

    # ── 对外接口（供其他模块通过 get_instance('sms') 调用）──

    def send_sms(self, phone, code, purpose='login'):
        """发送验证码（委托给 providers/sms/）"""
        from .services import send_sms as _send
        return _send(phone, code, purpose)

    def generate_code(self, length=6):
        """生成随机验证码"""
        from .services import generate_code as _gen
        return _gen(length)

    def validate_phone(self, phone, country_code=''):
        """验证手机号格式"""
        from .services import validate_phone as _val
        return _val(phone, country_code)

    def get_countries(self):
        """获取支持的国家列表"""
        from .countries import COUNTRIES
        return COUNTRIES

    def check_rate_limit(self, phone, max_per_hour=5):
        """检查手机号是否超出频率限制"""
        from .services import check_rate_limit as _chk
        return _chk(phone, max_per_hour)
