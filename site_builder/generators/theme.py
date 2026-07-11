#!/usr/bin/env python3
"""主题/视觉系统生成器 — 将 LLM 输出的配色方案写入主题系统"""

import os
import json
from models import get_db


class ThemeGenerator:
    """主题生成器"""

    THEMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'themes')

    @staticmethod
    def apply_theme(theme_data: dict):
        """根据品牌数据生成/更新主题配色

        theme_data 期望字段：
            site_name, primary_color, secondary_color, accent_color, font_preference, tone
        """
        theme_slug = 'ai_generated'
        theme_dir = os.path.join(ThemeGenerator.THEMES_DIR, theme_slug)
        os.makedirs(theme_dir, exist_ok=True)

        # 构建 theme.json
        primary = theme_data.get('primary_color', '#2563eb')
        secondary = theme_data.get('secondary_color', '#1e40af')
        accent = theme_data.get('accent_color', '#7c3aed')

        theme_config = {
            'name': theme_data.get('site_name', 'AI Generated'),
            'version': '1.0.0',
            'description': f"AI-generated theme for {theme_data.get('site_name', 'Unknown')}",
            'variables': {
                'preset': 'light',
                'font_scale': 1.0,
                'border_radius': 8,
                '--primary-color': primary,
                '--secondary-color': secondary,
                '--accent-color': accent,
                '--primary-light': ThemeGenerator._lighten(primary, 0.2),
                '--primary-dark': ThemeGenerator._darken(primary, 0.2),
                '--bg-color': '#ffffff',
                '--text-color': '#1a1a2e',
                '--text-muted': '#6b7280',
                '--heading-font': '"Geist", "Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
                '--body-font': '"Geist", "Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
            }
        }

        theme_json_path = os.path.join(theme_dir, 'theme.json')
        with open(theme_json_path, 'w', encoding='utf-8') as f:
            json.dump(theme_config, f, ensure_ascii=False, indent=2)

        print(f'[SiteBuilder] ✅ Theme applied to {theme_json_path}')

        # 激活主题：更新 site_configs 中的 active_theme
        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE site_configs SET active_theme=? WHERE id=1",
                    (theme_slug,)
                )
                conn.commit()
        except Exception:
            pass  # 字段可能不存在，不影响

    @staticmethod
    def _lighten(hex_color: str, factor: float) -> str:
        """将 HEX 颜色变亮"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        """将 HEX 颜色变暗"""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"