#!/usr/bin/env python3
"""Developer Account Management Plugin"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from plugin_manager.base import BasePlugin


class DevAccountsPlugin(BasePlugin):
    name = 'Developer Accounts'
    identifier = 'dev_accounts'
    version = '1.0.0'
    description = 'Manage developer accounts for social media platforms (Douyin, WeChat, Telegram, LINE)'
    author = 'VeroRun'

    def setup(self):
        super().setup()
        from .routes import dev_accounts_bp
        self.app.register_blueprint(dev_accounts_bp)

    def on_install(self, registry=None) -> bool:
        self._ensure_table()
        return True

    def _ensure_table(self):
        """Create dev_accounts table if it doesn't exist."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
        from models import get_db
        with get_db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS dev_accounts (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform         TEXT NOT NULL,
                    account_name     TEXT NOT NULL,
                    app_id           TEXT DEFAULT '',
                    app_secret       TEXT DEFAULT '',
                    bot_token        TEXT DEFAULT '',
                    channel_id       TEXT DEFAULT '',
                    channel_secret   TEXT DEFAULT '',
                    access_token     TEXT DEFAULT '',
                    extra_config     TEXT DEFAULT '{}',
                    is_active        INTEGER DEFAULT 1,
                    created_at       TEXT DEFAULT (datetime('now')),
                    updated_at       TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_dev_accounts_platform
                    ON dev_accounts(platform);
            """)
            conn.commit()