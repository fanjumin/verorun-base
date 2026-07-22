#!/usr/bin/env python3
"""Douyin / Toutiao Mini-Program Generator

Generates a complete Douyin mini-program project from site builder output.
Compatible with Toutiao (same ByteDance ecosystem).
"""

import os
import json
from .base import BaseMiniAppGenerator


class DouyinGenerator(BaseMiniAppGenerator):
    platform = 'douyin'
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'douyin')

    def _get_page_ext(self, platform: str) -> str:
        return 'ttml'

    def _get_style_ext(self, platform: str) -> str:
        return 'ttss'

    def generate_from_plan(self, ai_plan: dict, platform: str, options: dict) -> dict:
        result = super().generate_from_plan(ai_plan, platform, options)
        result['compatible_with'] = ['toutiao']
        return result

    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        output_dir = os.path.join(self.output_base, 'douyin')
        self._copy_template(output_dir)

        brand_ctx = self._get_brand_context(brand)
        api_ctx = self._get_api_context(options)

        # Determine pages
        pages = list(options.get('include_pages', ['home']))
        if options.get('include_chat', True) and 'chat' not in pages:
            pages.insert(0, 'chat')
        if options.get('include_profile', True) and 'profile' not in pages:
            pages.append('profile')

        # Write app.json
        app_json = {
            'pages': [f'pages/{p}/{p}' for p in pages],
            'window': {
                'navigationBarBackgroundColor': brand_ctx['primary_color'],
                'navigationBarTitleText': brand_ctx['app_name'],
                'navigationBarTextStyle': 'white',
            },
        }
        self._write_file(
            os.path.join(output_dir, 'app.json'),
            json.dumps(app_json, ensure_ascii=False, indent=2)
        )

        # Write app.js
        app_js_context = {**brand_ctx, **api_ctx, 'app_id': options.get('app_id', {}).get('douyin', '')}
        app_js_path = os.path.join(self.template_dir, 'app.js')
        if os.path.exists(app_js_path):
            self._write_file(
                os.path.join(output_dir, 'app.js'),
                self._render_template(app_js_path, app_js_context)
            )

        # Render global stylesheet (app.ttss) with brand context
        app_ttss_path = os.path.join(self.template_dir, 'app.ttss')
        if os.path.exists(app_ttss_path):
            self._write_file(
                os.path.join(output_dir, 'app.ttss'),
                self._render_template(app_ttss_path, {**brand_ctx, **api_ctx})
            )

        # Write project.config.json
        project_config = {
            'appid': options.get('app_id', {}).get('douyin', ''),
            'projectname': brand_ctx['app_name'],
            'setting': {
                'urlCheck': True,
                'es6': True,
                'postcss': True,
                'minified': True,
            },
        }
        self._write_file(
            os.path.join(output_dir, 'project.config.json'),
            json.dumps(project_config, ensure_ascii=False, indent=2)
        )

        # Render each page
        for page in pages:
            page_dir = os.path.join(output_dir, 'pages', page)
            for ext in ['js', 'ttml', 'ttss']:
                template_path = os.path.join(self.template_dir, 'pages', page, f'{page}.{ext}')
                if os.path.exists(template_path):
                    self._write_file(
                        os.path.join(page_dir, f'{page}.{ext}'),
                        self._render_template(template_path, {**brand_ctx, **api_ctx})
                    )

        return {
            'output_dir': output_dir,
            'files': self._collect_files(output_dir),
            'platform': 'douyin',
            'compatible_with': ['toutiao'],
        }