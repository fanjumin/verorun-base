#!/usr/bin/env python3
"""
AI Tools Plugin — PPT Generation + Image Generation
=====================================================
完全解耦版：独立数据库 data/ai_tools.db，零 auth-center 业务导入。

端点:
  POST /admin/generate-ppt     → PPT 生成（DeepSeek 驱动）
  POST /admin/generate-image   → 图像生成
  GET  /admin/media/download/<filename> → 媒体文件下载

配置:
  deepseek_api_key  → 插件自有配置表 plugin_config（回退环境变量 DEEPSEEK_API_KEY）
"""

from plugin_manager.base import BasePlugin


class AIToolsPlugin(BasePlugin):
    name = 'ai_tools'
    version = '0.1.0'
    description = 'AI Tools — PPT Generation + Image Generation (fully decoupled)'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立数据库"""
        from .routes import init_ai_tools_tables
        init_ai_tools_tables()
        print('[AITools] Independent DB initialized (data/ai_tools.db)')
        return True

    def on_enable(self, registry):
        """启用时确保表存在"""
        try:
            from .routes import init_ai_tools_tables, init_routes
            init_ai_tools_tables()
            init_routes(t_func=self.t)
        except Exception as e:
            print(f'[AITools] DB init warning: {e}')
        print('[AITools] AI Tools routes registered')
        return True

    def register_routes(self):
        from .routes import init_routes, ai_tools_bp
        init_routes(t_func=self.t)
        return [ai_tools_bp]

    def on_disable(self, registry):
        print('[AITools] Disabled')
        return True