#!/usr/bin/env python3
"""WhatsApp Mini App Generator (WebView-based, reuses Telegram templates)."""

import os, json
from .base import BaseMiniAppGenerator


class WhatsAppGenerator(BaseMiniAppGenerator):
    platform = 'whatsapp'
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'telegram')

    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        output_dir = os.path.join(self.output_base or '', 'whatsapp')
        self._copy_template(output_dir)

        brand_ctx = self._get_brand_context(brand)
        api_ctx = self._get_api_context(options)

        index_path = os.path.join(self.template_dir, 'index.html')
        if os.path.exists(index_path):
            self._write_file(
                os.path.join(output_dir, 'index.html'),
                self._render_template(index_path, {**brand_ctx, **api_ctx}))

        chat_path = os.path.join(self.template_dir, 'chat.html')
        if os.path.exists(chat_path):
            self._write_file(
                os.path.join(output_dir, 'chat.html'),
                self._render_template(chat_path, {**brand_ctx, **api_ctx}))

        manifest = {
            'name': brand_ctx['app_name'],
            'short_name': brand_ctx['app_name'],
            'description': f"{brand_ctx['app_name']} WhatsApp Mini App",
            'start_url': '/chat.html',
            'display': 'standalone',
            'theme_color': brand_ctx.get('primary_color', '#1890ff'),
            'background_color': '#ffffff',
        }
        self._write_file(
            os.path.join(output_dir, 'manifest.json'),
            json.dumps(manifest, ensure_ascii=False, indent=2))

        return {
            'output_dir': output_dir,
            'files': self._collect_files(output_dir),
            'platform': 'whatsapp',
        }

    def generate_from_plan(self, ai_plan: dict, platform: str, options: dict) -> dict:
        return self.generate({}, ai_plan.get('brand', {}), options)
