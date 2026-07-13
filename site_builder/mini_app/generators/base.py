#!/usr/bin/env python3
"""Base class for mini-program generators"""

import os
import json
import shutil
from abc import ABC, abstractmethod


class BaseMiniAppGenerator(ABC):
    """Abstract base for platform-specific mini-program generators.

    Each platform generator inherits from this class and implements
    the generate() method to produce platform-specific mini-program files.
    """

    platform: str = ''          # 'douyin' | 'wechat' | 'telegram' | 'line'
    template_dir: str = ''      # Path to platform-specific template directory
    output_base: str = 'dist'   # Base output directory (relative or absolute)

    def __init__(self, output_base: str = None):
        if output_base:
            self.output_base = output_base

    @abstractmethod
    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        """Generate mini-program files for this platform.

        Args:
            site_config: Site configuration (tokens, prompt template, etc.)
            brand: Brand settings dict (site_name, primary_color, logo_url, etc.)
            options: Generation options (include_chat, include_pages, base_url, etc.)

        Returns:
            {
                'output_dir': 'dist/douyin/',
                'files': ['app.js', 'pages/chat/chat.js', ...],
                'platform': 'douyin',
                'compatible_with': ['toutiao']  # optional
            }
        """
        pass

    def _copy_template(self, output_dir: str):
        """Copy template files from self.template_dir to output_dir.

        Clears existing output_dir first for idempotency.
        """
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        if os.path.exists(self.template_dir):
            shutil.copytree(self.template_dir, output_dir)

    def _render_template(self, template_path: str, context: dict) -> str:
        """Render a template file with {{ variable }} substitution.

        Uses simple string replacement (not Jinja2) to avoid dependency.
        """
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for key, value in context.items():
            placeholder = f'{{{{ {key} }}}}'
            content = content.replace(placeholder, str(value))
        return content

    def _write_file(self, path: str, content: str):
        """Write content to a file, creating parent directories as needed."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _get_brand_context(self, brand: dict) -> dict:
        """Extract and normalize brand context for template rendering."""
        return {
            'app_name': brand.get('site_name', 'VeroRun AI'),
            'tagline': brand.get('tagline', ''),
            'primary_color': brand.get('primary_color', '#1890ff'),
            'secondary_color': brand.get('secondary_color', ''),
            'logo_url': brand.get('logo_url', ''),
            'favicon_url': brand.get('favicon_url', ''),
            'brand_story': brand.get('brand_story', ''),
        }

    def _get_api_context(self, options: dict) -> dict:
        """Extract and normalize API context for template rendering."""
        return {
            'base_url': options.get('base_url', 'https://easykai.cn'),
            'api_prefix': options.get('api_prefix', '/api/v1/mini-program'),
            'platform': self.platform,
        }

    def _collect_files(self, output_dir: str) -> list:
        """Collect all file paths relative to output_dir."""
        files = []
        for root, _, filenames in os.walk(output_dir):
            for f in filenames:
                files.append(os.path.relpath(os.path.join(root, f), output_dir))
        return files