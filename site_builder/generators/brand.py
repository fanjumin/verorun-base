#!/usr/bin/env python3
"""品牌设置生成器 — 将 LLM 输出的品牌数据写入 brand_settings 表"""

import json
from models import get_db


class BrandGenerator:
    """品牌设置生成器"""

    @staticmethod
    def apply(brand_data: dict):
        """将品牌数据写入 brand_settings 表（幂等：UPSERT id=1）

        brand_data 期望字段：
            site_name, tagline, brand_story,
            primary_color, secondary_color, accent_color,
            copyright_text, footer_text
        """
        with get_db() as conn:
            conn.execute("""
                INSERT INTO brand_settings (id, company_name, site_name_cn, site_name_en,
                    slogan, tagline, description, copyright, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    company_name=excluded.company_name,
                    site_name_cn=excluded.site_name_cn,
                    site_name_en=excluded.site_name_en,
                    slogan=excluded.slogan,
                    tagline=excluded.tagline,
                    description=excluded.description,
                    copyright=excluded.copyright,
                    updated_at=datetime('now')
            """, (
                brand_data.get('site_name', ''),
                brand_data.get('site_name', ''),   # site_name_cn
                brand_data.get('site_name', ''),   # site_name_en
                brand_data.get('tagline', ''),
                brand_data.get('tagline', ''),
                brand_data.get('brand_story', ''),
                brand_data.get('copyright_text', ''),
            ))
            conn.commit()
        print('[SiteBuilder] ✅ Brand settings applied')

    @staticmethod
    def apply_colors(colors: dict):
        """仅更新品牌配色（用于最小化修改）"""
        # brand_settings 表没有直接的 color 字段，颜色存入 theme 系统
        # 这里留空，由 ThemeGenerator 处理
        pass