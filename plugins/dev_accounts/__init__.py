#!/usr/bin/env python3
"""Developer Account Management Plugin

数据解耦模式说明（标准 §12.10）：
  - dev_accounts 表保留在主库 public schema，不迁移到独立 schema。
  - 原因：该表被 main_site/routes/mini_program.py（直接 SQL 读取 bot_token）
    与 site_builder/routes.py（经 models 读取凭证）跨模块共享读取，
    迁移会破坏核心链路。连接统一走 plugins/_base/db.py（见 models.py get_db()）。
"""

from plugin_manager.base import BasePlugin


class DevAccountsPlugin(BasePlugin):
    name = 'Developer Accounts'
    identifier = 'dev_accounts'
    version = '1.1.0'
    description = 'Manage developer accounts for social media platforms (Douyin, WeChat, Telegram, LINE)'
    author = 'VeroRun'

    def setup(self):
        super().setup()
        from .routes import dev_accounts_bp
        self.app.register_blueprint(dev_accounts_bp)

    def on_install(self, registry=None) -> bool:
        from .models import init_db, set_schema_version
        init_db()
        try:
            set_schema_version(self.version)
        except Exception:
            self.log('dev_accounts: failed to record schema version', level='warning')
        return True

    def get_schema_version(self) -> str:
        """Read current schema version (标准 §10.6)."""
        try:
            from .models import get_schema_version as _get_version
            return _get_version()
        except Exception:
            return '0.0.0'

    def migrate(self, from_version: str, to_version: str) -> bool:
        """Run schema migrations (标准 §10.6).

        当前无破坏性迁移：幂等建表并更新 schema 版本记录。
        """
        try:
            from .models import init_db, set_schema_version
            init_db()
            set_schema_version(to_version)
            return True
        except Exception:
            return False

    def on_uninstall(self, registry=None) -> bool:
        """卸载处理：逻辑解耦模式，保留数据不删表。

        dev_accounts 表被 main_site / site_builder 跨模块共享读取（见模块顶部注释），
        DROP TABLE 会破坏依赖链路，因此卸载仅记录日志、保留数据。
        """
        self.log('dev_accounts uninstalled: table kept in main DB (shared by main_site/site_builder)')
        return True

    def get_dashboard_stats(self):
        """Dashboard 统计：账号总数、活跃账号数。"""
        try:
            from .models import get_account_stats
            return get_account_stats()
        except Exception:
            return {'total_accounts': 0, 'active_accounts': 0}
