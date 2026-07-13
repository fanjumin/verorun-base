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
            'app_name': 'VeroRun AI',
        })
    """

    def __init__(self, site_config: dict = None, brand_settings: dict = None):
        self.site_config = site_config or {}
        self.brand = brand_settings or {}

    def generate(self, platforms: list, options: dict = None) -> dict:
        """Generate mini-programs for the specified platforms.

        Args:
            platforms: List of platform identifiers, e.g.,
                       ['douyin', 'wechat', 'telegram', 'line']
                       'toutiao' is also supported (maps to DouyinGenerator)
            options: Generation options (see _get_generator for details)

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
                generator = self._get_generator(platform)
                result = generator.generate(self.site_config, self.brand, options)
                results[platform] = {'status': 'completed', **result}
                logger.info(f'[MiniAppEngine] {platform} generation completed: {len(result.get("files", []))} files')
            except Exception as e:
                logger.error(f'[MiniAppEngine] {platform} generation failed: {e}')
                import traceback
                traceback.print_exc()
                results[platform] = {'status': 'failed', 'error': str(e)}

        return results

    def _get_generator(self, platform: str):
        """Factory: return the appropriate generator for the platform.

        Args:
            platform: 'douyin' | 'toutiao' | 'wechat' | 'telegram' | 'line'

        Returns:
            BaseMiniAppGenerator subclass instance

        Raises:
            ValueError: If platform is not supported
        """
        from .generators.douyin import DouyinGenerator
        from .generators.wechat import WechatGenerator
        from .generators.telegram import TelegramGenerator
        from .generators.line import LINEGenerator

        generators = {
            'douyin': DouyinGenerator,
            'toutiao': DouyinGenerator,  # Toutiao shares Douyin ecosystem
            'wechat': WechatGenerator,
            'telegram': TelegramGenerator,
            'line': LINEGenerator,
        }

        generator_cls = generators.get(platform)
        if not generator_cls:
            raise ValueError(f'Unsupported platform: {platform}. Supported: {list(generators.keys())}')

        return generator_cls()