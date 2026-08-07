#!/usr/bin/env python3
"""Telegram Mini App Generator

Generates static HTML/JS files for Telegram Mini App (WebView-based).
"""

import os
import json
from .base import BaseMiniAppGenerator


class TelegramGenerator(BaseMiniAppGenerator):
    platform = 'telegram'
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'telegram')

    def generate_from_plan(self, ai_plan: dict, platform: str, options: dict) -> dict:
        return super().generate_from_plan(ai_plan, platform, options)

    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        output_dir = os.path.join(self.output_base, 'telegram')
        self._copy_template(output_dir)

        brand_ctx = self._get_brand_context(brand)
        api_ctx = self._get_api_context(options)
        render_ctx = {**brand_ctx, **api_ctx, 'deploy_url': options.get('deploy_url', '')}

        # Render main HTML files
        for html_file in ['index.html', 'chat.html']:
            template_path = os.path.join(self.template_dir, html_file)
            if os.path.exists(template_path):
                self._write_file(
                    os.path.join(output_dir, html_file),
                    self._render_template(template_path, render_ctx)
                )

        # Render app.js
        app_js_path = os.path.join(self.template_dir, 'js', 'app.js')
        if os.path.exists(app_js_path):
            self._write_file(
                os.path.join(output_dir, 'js', 'app.js'),
                self._render_template(app_js_path, render_ctx)
            )

        # Render stylesheet
        css_path = os.path.join(self.template_dir, 'css', 'style.css')
        if os.path.exists(css_path):
            self._write_file(
                os.path.join(output_dir, 'css', 'style.css'),
                self._render_template(css_path, render_ctx)
            )

        # Write manifest.json
        manifest = {
            'name': brand_ctx['app_name'],
            'description': brand_ctx.get('tagline', ''),
            'url': options.get('deploy_url', ''),
            'icon': brand_ctx.get('logo_url', ''),
            'platform': 'telegram',
        }
        self._write_file(
            os.path.join(output_dir, 'manifest.json'),
            json.dumps(manifest, ensure_ascii=False, indent=2)
        )

        return {
            'output_dir': output_dir,
            'files': self._collect_files(output_dir),
            'platform': 'telegram',
        }