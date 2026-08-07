#!/usr/bin/env python3
"""Mini App Builder Plugin (v2.0.0)

v2.0.0 解耦与合并：
  - 小程序生成能力从核心模块 site_builder/mini_app/ 解耦至此插件。
  - 原独立插件 Developer Accounts (dev_accounts) 已合并进本插件
    （submodules/accounts/），不再存在独立 dev_accounts 插件。
  - 数据表（dev_accounts / schema_meta / mini_app_projects /
    mini_app_versions）由 v2.0.0 迁移移至独立 schema `mini_app_builder`，
    public 视图保持向后兼容（见 migrate.py）。
  - 运行时 API（原 main_site/routes/mini_program.py，前缀
    /api/v1/mini-program）整体迁入 public_api.py。

元数据以 plugin.json（plugin_info）为唯一数据源，类内仅保留兜底值。
"""
import os
import sys

_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
if os.path.isdir(_ROOT) and _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from plugin_manager.base import BasePlugin
from plugin_manager.logger import get_plugin_logger

logger = get_plugin_logger('mini_app_builder')


class MiniAppBuilderPlugin(BasePlugin):
    """Mini App Builder — mini-program generation + developer account management."""

    @property
    def name(self):
        info = getattr(self, 'plugin_info', None)
        return getattr(info, 'name', None) or 'Mini App Builder'

    @property
    def version(self):
        info = getattr(self, 'plugin_info', None)
        return getattr(info, 'version', None) or '2.0.0'

    @property
    def description(self):
        info = getattr(self, 'plugin_info', None)
        return getattr(info, 'description', None) or (
            'Mini-program generation & developer account management '
            '(merged with dev_accounts)'
        )

    @property
    def author(self):
        info = getattr(self, 'plugin_info', None)
        return getattr(info, 'author', None) or 'VeroRun'

    def setup(self):
        super().setup()
        self._init_db()

    def on_install(self, registry=None) -> bool:
        self._init_db()
        return True

    def on_enable(self, registry=None) -> bool:
        self._init_db()
        return True

    def _init_db(self):
        """v2.0.0 schema migration + idempotent table creation (safe to rerun).

        顺序：
          1. run_migrations()   —— 旧 public 表 ALTER TABLE SET SCHEMA 至
                                   mini_app_builder schema（幂等）。
          2. init_tables()      —— mini_app_projects / mini_app_versions
                                   CREATE TABLE IF NOT EXISTS（search_path 已含
                                   mini_app_builder，全新安装时建在独立 schema）。
          3. accounts init_db() —— dev_accounts / schema_meta 建表。
          4. ensure_public_views() —— 重建 public 视图向后兼容。
        """
        try:
            from .migrate import run_migrations
            run_migrations()
        except Exception as e:
            logger.warning('[MiniAppBuilder] schema migration skipped: %s', e)

        try:
            from .models import init_tables
            init_tables()
        except Exception as e:
            logger.warning('[MiniAppBuilder] init_tables failed: %s', e)

        try:
            from .submodules.accounts.models import init_db as _init_accounts_db
            _init_accounts_db()
        except Exception as e:
            logger.warning('[MiniAppBuilder] accounts init_db failed: %s', e)

        try:
            from .migrate import ensure_public_views
            ensure_public_views()
        except Exception as e:
            logger.warning('[MiniAppBuilder] public views refresh failed: %s', e)

    def register_routes(self):
        """挂载 3 个蓝图（url_prefix 各自自定义，由 mount_all_routes 沿用）。

        - /admin/site-builder/*        小程序管理（原 site_builder/routes.py）
        - /admin/dev-accounts/*        开发者账号管理（原 dev_accounts 插件）
        - /api/v1/mini-program/*       小程序运行时 API（原 main_site/routes/mini_program.py）
        """
        from .routes import mini_app_admin_bp
        from .submodules.accounts.routes import dev_accounts_bp
        from .public_api import mini_program_bp
        return [mini_app_admin_bp, dev_accounts_bp, mini_program_bp]

    def get_schema_version(self) -> str:
        """Read current schema version (标准 §10.6)."""
        try:
            from .submodules.accounts.models import get_schema_version as _get_version
            return _get_version()
        except Exception:
            return '0.0.0'

    def migrate(self, from_version: str, to_version: str) -> bool:
        """Run schema migrations (标准 §10.6)."""
        try:
            self._init_db()
            from .submodules.accounts.models import set_schema_version
            set_schema_version(to_version)
            return True
        except Exception as e:
            logger.error('[MiniAppBuilder] migrate failed: %s', e)
            return False

    def on_uninstall(self, registry=None) -> bool:
        """卸载：保留数据与表（public 视图保持向后兼容），仅移除 registry 记录。"""
        self.log('mini_app_builder uninstalled: schema/data preserved '
                 '(public views kept for compatibility)')
        return True

    def get_dashboard_stats(self) -> dict:
        """Dashboard 统计：账号 + 小程序项目/版本汇总。"""
        stats = {}
        try:
            from .submodules.accounts.models import get_account_stats
            stats.update(get_account_stats())
        except Exception:
            stats.update({'total_accounts': 0, 'active_accounts': 0})
        try:
            from .models import get_mini_app_stats
            stats.update(get_mini_app_stats())
        except Exception:
            stats.update({'total_projects': 0, 'total_versions': 0})
        return stats

    # ─── 公开 API（供其他插件/模块调用）───

    def get_accounts_for_platform(self, platform: str) -> dict | None:
        """获取指定平台的有效凭证（敏感字段已脱敏，用于展示/校验）。"""
        from .submodules.accounts.models import get_by_platform
        return get_by_platform(platform, active_only=True)

    def get_all_platform_credentials(self) -> dict:
        """获取所有平台凭证（含解密后的敏感字段，仅供内部可信调用方）。

        返回结构: {platform: {id, account_name, app_id, app_secret,
                              bot_token, access_token, channel_id,
                              channel_secret, extra_config}}
        """
        from .submodules.accounts.models import get_all_raw
        from .submodules.accounts.crypto import decrypt

        creds = {}
        for acct in get_all_raw():
            if not acct.get('is_active'):
                continue
            platform = acct['platform']
            creds[platform] = {
                'id': acct.get('id'),
                'account_name': acct.get('account_name'),
                'app_id': acct.get('app_id'),
                'app_secret': decrypt(acct.get('app_secret')) if acct.get('app_secret') else None,
                'bot_token': decrypt(acct.get('bot_token')) if acct.get('bot_token') else None,
                'access_token': decrypt(acct.get('access_token')) if acct.get('access_token') else None,
                'channel_id': acct.get('channel_id'),
                'channel_secret': decrypt(acct.get('channel_secret')) if acct.get('channel_secret') else None,
                'extra_config': acct.get('extra_config'),
            }
        return creds
