#!/usr/bin/env python3
"""LINE MINI App Generator

Generates static HTML/JS files for LINE MINI App (LIFF-based).
"""

import os
import json
from .base import BaseMiniAppGenerator


class LINEGenerator(BaseMiniAppGenerator):
    platform = 'line'
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'line')

    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        output_dir = os.path.join(self.output_base, 'line')
        self._copy_template(output_dir)

        brand_ctx = self._get_brand_context(brand)
        api_ctx = self._get_api_context(options)
        render_ctx = {**brand_ctx, **api_ctx, 'liff_id': options.get('liff_id', '')}

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
            'liffId': options.get('liff_id', ''),
            'platform': 'line',
        }
        self._write_file(
            os.path.join(output_dir, 'manifest.json'),
            json.dumps(manifest, ensure_ascii=False, indent=2)
        )

        return {
            'output_dir': output_dir,
            'files': self._collect_files(output_dir),
            'platform': 'line',
        }