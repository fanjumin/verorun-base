#!/usr/bin/env python3
"""MiniAppEngine — Core engine for generating social media mini-programs

Orchestrates platform-specific generators to produce mini-program
projects from Site_builder output (brand, theme, pages).
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MiniAppEngine:
    """Core engine for generating mini-programs across multiple platforms.

    Usage:
        engine = MiniAppEngine(site_config={'tokens': draft_tokens}, brand_settings=brand)
        results = engine.generate(['douyin', 'telegram'], {
            'include_chat': True,
            'include_pages': ['home', 'about'],
            'theme_color': '#1890ff',
            'app_name': '',
        })
    """

    def __init__(self, site_config: dict = None, brand_settings: dict = None):
        self.site_config = site_config or {}
        self.brand = brand_settings or {}

    def generate(self, platforms: list, options: dict = None, output_base: str = None,
                 ai_plan: dict = None) -> dict:
        """Generate mini-programs for the specified platforms.

        Args:
            platforms: List of platform identifiers, e.g.,
                       ['douyin', 'wechat', 'telegram', 'line']
                       'toutiao' is also supported (maps to DouyinGenerator)
            options: Generation options (see _get_generator for details)
            output_base: Base output directory for generated files. When set
                       (e.g. a project/version workspace path), generators write
                       under it instead of the default 'dist/'.
            ai_plan: Optional AI-generated plan dict. When provided, uses
                     generate_from_plan() on each generator instead of the
                     legacy generate() flow.

        Returns:
            {
                'douyin': {
                    'status': 'completed',
                    'output_dir': 'dist/douyin/',
                    'files': ['app.js', 'pages/chat/chat.js', ...],
                    'platform': 'douyin',
                    'compatible_with': ['toutiao'],
                },
                'telegram': {
                    'status': 'completed',
                    'output_dir': 'dist/telegram/',
                    'files': [...],
                    'platform': 'telegram',
                },
                ...
            }
        """
        options = options or {}
        results = {}

        for platform in platforms:
            try:
                generator = self._get_generator(platform, output_base)
                if ai_plan:
                    result = generator.generate_from_plan(ai_plan, platform, options)
                else:
                    result = generator.generate(self.site_config, self.brand, options)
                results[platform] = {'status': 'completed', **result}
                logger.info(f'[MiniAppEngine] {platform} generation completed: {len(result.get("files", []))} files')
            except Exception as e:
                logger.error(f'[MiniAppEngine] {platform} generation failed: {e}')
                import traceback
                traceback.print_exc()
                results[platform] = {'status': 'failed', 'error': str(e)}

        return results

    def _get_generator(self, platform: str, output_base: str = None):
        """Factory: return the appropriate generator for the platform.

        Args:
            platform: 'douyin' | 'toutiao' | 'wechat' | 'telegram' | 'line'
            output_base: Optional base output directory passed to the generator

        Returns:
            BaseMiniAppGenerator subclass instance

        Raises:
            ValueError: If platform is not supported
        """
        from .generators.douyin import DouyinGenerator
        from .generators.wechat import WechatGenerator
        from .generators.telegram import TelegramGenerator
        from .generators.line import LINEGenerator
        from .generators.whatsapp import WhatsAppGenerator

        generators = {
            'douyin': DouyinGenerator,
            'toutiao': DouyinGenerator,
            'wechat': WechatGenerator,
            'telegram': TelegramGenerator,
            'line': LINEGenerator,
            'whatsapp': WhatsAppGenerator,
        }

        generator_cls = generators.get(platform)
        if not generator_cls:
            raise ValueError(f'Unsupported platform: {platform}. Supported: {list(generators.keys())}')

        return generator_cls(output_base=output_base) if output_base else generator_cls()