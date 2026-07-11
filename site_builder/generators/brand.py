#!/usr/bin/env python3
"""品牌/视觉生成器 — 将 LLM 输出的品牌数据写入统一 design_tokens"""

from site_builder.site_settings.models import get_tokens, save_tokens


class BrandGenerator:
    """品牌设置生成器（统一令牌版）"""

    @staticmethod
    def apply(brand_data: dict, site_key='platform'):
        """将品牌数据写入 design_tokens.brand

        brand_data 期望字段：
            site_name, slogan, industry, brand_story, company_name, contact_email
        """
        tokens = get_tokens(site_key)
        current = tokens['token_json']

        current['brand'].update({
            'site_name': brand_data.get('site_name', ''),
            'slogan': brand_data.get('slogan', '') or brand_data.get('tagline', ''),
            'industry': brand_data.get('industry', ''),
            'brand_story': brand_data.get('brand_story', ''),
            'company_name': brand_data.get('company_name', ''),
            'contact_email': brand_data.get('contact_email', ''),
        })
        current['seo'].update({
            'title': brand_data.get('seo_title', '') or brand_data.get('site_name', ''),
            'description': brand_data.get('seo_desc', '') or brand_data.get('brand_story', '')[:160],
        })
        current['footer'].update({
            'copyright': brand_data.get('copyright_text', '') or brand_data.get('copyright', ''),
            'icp_number': brand_data.get('icp_number', ''),
            'security_number': brand_data.get('security_number', ''),
        })

        save_tokens(site_key, current, generated_by='ai', prompt_id=None)
        print(f'[SiteBuilder] ✅ Brand settings applied via design_tokens')

    @staticmethod
    def apply_colors(colors_data: dict, site_key='platform'):
        """写入品牌配色到 design_tokens.colors"""
        tokens = get_tokens(site_key)
        current = tokens['token_json']

        color_map = {
            'primary': 'primary', 'secondary': 'secondary', 'accent': 'accent',
            'primary_color': 'primary', 'secondary_color': 'secondary', 'accent_color': 'accent',
            'background': 'background', 'text_primary': 'text_primary', 'text_secondary': 'text_secondary',
        }
        for k, v in colors_data.items():
            mapped = color_map.get(k, k)
            if mapped in current['colors']:
                current['colors'][mapped] = v

        save_tokens(site_key, current, generated_by='ai', prompt_id=None)
        print(f'[SiteBuilder] ✅ Colors applied via design_tokens')