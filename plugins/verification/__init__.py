#!/usr/bin/env python3
"""
Identity Verification Plugin — 实名认证插件
============================================
提供支付宝实人认证的前端配置面板。
认证流程由 auth-center 路由处理，插件提供管理 UI。
- 数据库：PostgreSQL schema = verification（独立 schema，表 verification_requests）
"""
from plugin_manager.base import BasePlugin


class VerificationPlugin(BasePlugin):
    name = 'verification'
    version = '1.0.0'
    description = 'Identity Verification — real-name verification via Alipay identity service'
    author = 'VeroRun'

    def on_install(self, registry):
        from .models import init_i18n as _init_models_i18n
        _init_models_i18n(self.t)
        from .models import init_verification_db, migrate_from_main_db
        init_verification_db()
        migrate_from_main_db()
        return True

    def on_enable(self, registry):
        from .models import init_i18n as _init_models_i18n
        _init_models_i18n(self.t)
        from .models import init_verification_db
        init_verification_db()
        self.log(self.t('plugin_enabled'))
        return True

    def register_routes(self):
        """返回空列表 — 认证路由保留在 auth-center"""
        return []

    # ── 功能注册 ──

    def register_health_checks(self):
        """F-009: 健康检查 — verification schema 连通性（标准 §4 可选推荐）。"""
        return [{
            'check_id': 'verification_db',
            'check_key': 'verification_db',
            'name': self.t('Verification Schema Connectivity'),
            'category': 'database',
            'func': self._check_verification_db,
            'severity': 'error',
            'interval_seconds': 300,
        }]

    def _check_verification_db(self):
        try:
            from .models import get_verification_db
            conn = get_verification_db()
            conn.execute('SELECT 1')
            return {'status': 'pass', 'message': 'verification schema is accessible'}
        except Exception as e:
            return {'status': 'fail', 'message': str(e)}

    # ── 生命周期 ──

    def on_disable(self, registry):
        self.log(self.t('plugin_disabled'), 'warning')
        return True

    def on_uninstall(self, registry):
        """F-010: 卸载清理 — 删除插件表（标准 §12.5 卸载零残留）。"""
        try:
            from .models import get_verification_db
            conn = get_verification_db()
            conn.execute('DROP TABLE IF EXISTS verification_requests CASCADE')
            conn.commit()
            self.log(self.t('uninstall_cleanup_complete'))
        except Exception as e:
            self.log(f'on_uninstall cleanup failed: {e}', 'error')
        return True

    # ── 对外接口 ──
    # 签名与 auth-center/routes/user.py 调用方保持一致，保证插件启用时代理可用

    def initiate_verification(self, user_id, return_url='', cert_name='', cert_no=''):
        from .services import initiate_verification as _i
        return _i(user_id, return_url, cert_name=cert_name, cert_no=cert_no)

    def verify_callback(self, user_id, params=None):
        from .services import verify_callback as _v
        return _v(user_id, params)
