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
        # 注册管理后台路由 + 公开 Webhook
        from .routes import chatbot_bp, webhook_bp
        self.app.register_blueprint(chatbot_bp, url_prefix='/admin/chatbot')
        self.app.register_blueprint(webhook_bp)

    def on_install(self, registry=None) -> bool:
        from .models import init_chatbot_tables, seed_defaults, migrate_from_main
        init_chatbot_tables()
        self._seed_default_config()
        # 从主库迁移已有数据（幂等，首次运行自动执行）
        self.log('正在从主库迁移数据...')
        migrate_from_main()
        return True

    def on_enable(self, registry=None) -> bool:
        self.register_agents()
        return True

    def register_routes(self):
        from .routes import chatbot_bp, webhook_bp
        return [chatbot_bp, webhook_bp]

    def register_agents(self):
        """注册 Advisor Agent 到独立库 agent_registry 表"""
        try:
            from .models import upsert_agent

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
            upsert_agent(
                name=agent['name'],
                role_type=agent['role_type'],
                description=f"AI Advisor Agent — {agent['domain']}",
                domain=agent.get('domain', 'chatbot'),
                provider='dashscope',
                model_name='qwen-turbo',
                system_prompt=system_prompt,
                capabilities=json.dumps(agent.get('capabilities', [])),
                is_active=1 if agent.get('enabled_by_default', True) else 0
            )
        except Exception as e:
            self.log(f'Register agents failed: {e}', 'warning')

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """从独立库 plugin_configs 读取；fallback 到 plugin.json 默认值"""
        try:
            from .models import get_config
            val = get_config(self.identifier, key)
            if val:
                return val
        except Exception:
            pass
        return self._config.get(key, default)

    def set_config_value(self, key: str, value: Any) -> bool:
        """持久化到独立库 plugin_configs"""
        try:
            from .models import set_config
            set_config(self.identifier, key, str(value))
            self._config[key] = value
            return True
        except Exception as e:
            self.log(f'Set config failed: {e}', 'error')
            return False

    def _seed_default_config(self):
        """仅当独立库中无该配置行时写入默认值"""
        defaults = self._config or {}
        if not defaults:
            return
        try:
            from .models import seed_defaults
            seed_defaults(self.identifier, defaults)
        except Exception as e:
            self.log(f'Seed default config failed: {e}', 'warning')