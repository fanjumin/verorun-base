import json
import os
from typing import Any

from plugin_manager.base import BasePlugin


class ChatbotPlugin(BasePlugin):
    name = 'AI Advisor'
    identifier = 'chatbot'

    def setup(self):
        # 先执行父类 setup()，触发 on_install（建表/写种子）和 on_enable（注册Agent）
        super().setup()
        # 然后注册管理后台路由
        from .routes import chatbot_bp
        self.app.register_blueprint(chatbot_bp, url_prefix='/admin/chatbot')

    def on_install(self, registry=None) -> bool:
        self._ensure_config_table()
        self._seed_default_config()
        return True

    def on_enable(self, registry=None) -> bool:
        self.register_agents()
        return True

    def register_routes(self):
        from .routes import chatbot_bp
        return [chatbot_bp]

    def register_agents(self):
        """Register Kai Assistant into agent_matrix table."""
        try:
            from agent_matrix.models import get_db

            plugin_info = getattr(self, 'plugin_info', None)
            metadata = plugin_info.metadata if plugin_info else {}
            agents = metadata.get('agents', [])
            if not agents:
                return

            prompt_path = os.path.join(os.path.dirname(__file__), agents[0].get('prompt_file', ''))
            system_prompt = ''
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    system_prompt = f.read().strip()

            agent = agents[0]
            with get_db() as conn:
                exists = conn.execute(
                    "SELECT id FROM agent_matrix WHERE name=? AND role_type=?",
                    (agent['name'], agent['role_type'])
                ).fetchone()
                if exists:
                    conn.execute("""
                        UPDATE agent_matrix
                        SET description=?, domain=?, managed_modules=?,
                            system_prompt=?, capabilities=?, is_active=?
                        WHERE id=?
                    """, (
                        f"AI Advisor Agent — {agent['domain']}",
                        agent.get('domain', 'chatbot'),
                        '["chatbot"]',
                        system_prompt,
                        json.dumps(agent.get('capabilities', [])),
                        1 if agent.get('enabled_by_default', True) else 0,
                        exists['id']
                    ))
                else:
                    conn.execute("""
                        INSERT INTO agent_matrix
                        (name, role_type, description, domain, managed_modules,
                         provider, model_name, system_prompt, capabilities,
                         is_active, auto_approve)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        agent['name'], agent['role_type'],
                        f"AI Advisor Agent — {agent['domain']}",
                        agent.get('domain', 'chatbot'),
                        '["chatbot"]',
                        'dashscope', 'qwen-turbo',
                        system_prompt,
                        json.dumps(agent.get('capabilities', [])),
                        1 if agent.get('enabled_by_default', True) else 0,
                        0
                    ))
                conn.commit()
        except Exception as e:
            self.log(f'Register agents failed: {e}', 'warning')

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Read from plugin_configs table; fallback to plugin.json defaults."""
        try:
            from models import get_db
            with get_db() as conn:
                row = conn.execute(
                    "SELECT value FROM plugin_configs WHERE plugin_name=? AND key=?",
                    (self.identifier, key)
                ).fetchone()
            if row and row['value'] is not None:
                return row['value']
        except Exception:
            pass
        return self._config.get(key, default)

    def set_config_value(self, key: str, value: Any) -> bool:
        """Persist to plugin_configs table."""
        try:
            from models import get_db
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO plugin_configs (plugin_name, key, value, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                    ON CONFLICT(plugin_name, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """, (self.identifier, key, str(value)))
                conn.commit()
            self._config[key] = value
            return True
        except Exception as e:
            self.log(f'Set config failed: {e}', 'error')
            return False

    def _ensure_config_table(self):
        try:
            from models import get_db
            with get_db() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS plugin_configs (
                        plugin_name TEXT NOT NULL,
                        key         TEXT NOT NULL,
                        value       TEXT DEFAULT '',
                        updated_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (plugin_name, key)
                    )
                """)
                conn.commit()
        except Exception as e:
            self.log(f'Create plugin_configs table failed: {e}', 'error')

    def _seed_default_config(self):
        """仅当 DB 中无该配置行时写入默认值。"""
        defaults = self._config or {}
        if not defaults:
            return
        try:
            from models import get_db
            with get_db() as conn:
                existing_keys = {
                    r['key'] for r in conn.execute(
                        "SELECT key FROM plugin_configs WHERE plugin_name=?",
                        (self.identifier,)
                    ).fetchall()
                }
            for key, value in defaults.items():
                if key not in existing_keys:
                    self.set_config_value(key, value)
        except Exception as e:
            self.log(f'Seed default config failed: {e}', 'warning')
