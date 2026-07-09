#!/usr/bin/env python3
"""
Captcha Embedded Plugin — Slider Captcha (滑块验证码)
======================================================
从 captcha-service/ 加载核心逻辑（生成器、安全、行为分析），
通过 Flask Blueprint 暴露 REST API。

端点:
  GET  /api/captcha/generate   → 生成拼图挑战
  POST /api/captcha/verify     → 验证位置 + 行为分析
  POST /api/captcha/consume    → 一次性消费 Token
  GET  /api/admin/captcha/stats → 统计数据
"""

from plugin_manager.base import BasePlugin


class CaptchaEmbeddedPlugin(BasePlugin):
    name = 'captcha_embedded'
    version = '0.1.0'
    description = 'Slider Captcha — Puzzle generation + behavior analysis + rate limiting'
    author = 'VeroRun'

    def on_enable(self, registry):
        """启用时注册 admin stats 端点和 i18n"""
        from captcha_bp import register_admin_stats, init_i18n
        register_admin_stats(self.app)
        init_i18n(self.t)
        print('[CaptchaEmbedded] Admin stats endpoint registered')
        return True

    def register_routes(self):
        """注册 Captcha Blueprint"""
        from captcha_bp import captcha_bp, init_i18n
        init_i18n(self.t)
        return [captcha_bp]

    def on_disable(self, registry):
        """禁用时卸载 Blueprint（stats 端点需重启后移除）"""
        print('[CaptchaEmbedded] Disabled')
        return True