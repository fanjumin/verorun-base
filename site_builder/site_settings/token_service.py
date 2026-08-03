#!/usr/bin/env python3
"""Token Service — 设计令牌业务逻辑"""

import json, copy
from site_builder.site_settings.models import DEFAULT_TOKENS, get_tokens, save_tokens


def validate_tokens(token_dict):
    """验证令牌结构完整性，返回 (valid, errors)"""
    errors = []
    required_sections = ['brand', 'colors', 'typography', 'navigation', 'footer', 'spacing', 'border_radius', 'shadows', 'seo']

    if not isinstance(token_dict, dict):
        return False, ['token_dict must be a dict']

    for section in required_sections:
        if section not in token_dict:
            errors.append(f'Missing required section: {section}')

    # 品牌验证
    brand = token_dict.get('brand', {})
    if not brand.get('site_name'):
        errors.append('brand.site_name is required')

    # 颜色验证
    colors = token_dict.get('colors', {})
    if not colors.get('primary'):
        errors.append('colors.primary is required')

    # 导航验证
    nav = token_dict.get('navigation', {})
    items = nav.get('items', [])
    for item in items:
        if not item.get('title'):
            errors.append(f'navigation item missing title')
        if not item.get('url'):
            errors.append(f'navigation item "{item.get("title", "?")}" missing url')

    return len(errors) == 0, errors


def merge_tokens(base_tokens, override_tokens):
    """深度合并令牌（override 覆盖 base）"""
    result = copy.deepcopy(base_tokens)
    for key, value in override_tokens.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key].update(value)
        else:
            result[key] = value
    return result


def get_token_schema():
    """返回令牌的 JSON Schema 描述（供 LLM 使用）"""
    return {
        "brand": {
            "site_name": "品牌/网站名称",
            "slogan": "品牌口号（10字以内）",
            "industry": "行业分类",
            "brand_story": "品牌故事（200字）",
            "logo_url": "Logo 图片 URL",
            "favicon_url": "Favicon URL",
            "company_name": "公司全称",
            "contact_email": "联系邮箱",
        },
        "colors": {
            "primary": "主色调（hex）",
            "secondary": "辅色调（hex）",
            "accent": "强调色（hex）",
            "background": "背景色（hex）",
            "surface": "卡片/面板背景色（hex）",
            "text_primary": "主文字色（hex）",
            "text_secondary": "次要文字色（hex）",
            "border": "边框色（hex）",
        },
        "typography": {
            "heading_font": "标题字体（CSS font-family）",
            "body_font": "正文字体（CSS font-family）",
            "font_scale": "字体缩放比例（0.8~1.5）",
            "h1_size": "H1 字号",
            "h2_size": "H2 字号",
            "body_size": "正文 字号",
            "line_height": "行高",
        },
        "navigation": {
            "items": [
                {
                    "title": "导航名称",
                    "url": "链接地址",
                    "icon": "图标（可选）",
                    "target": "_self 或 _blank",
                    "children": [{"title": "子菜单名", "url": "子链接"}],
                }
            ],
        },
        "footer": {
            "sections": [{"name": "分组名称", "links": [{"title": "链接名", "url": "链接"}]}],
            "articles": [{"title": "文档标题", "url": "文档链接"}],
            "copyright": "版权信息",
            "icp_number": "ICP 备案号",
        },
        "spacing": {"xs": "4px", "sm": "8px", "md": "16px", "lg": "32px", "xl": "64px"},
        "border_radius": {"sm": "4px", "md": "8px", "lg": "12px", "full": "9999px"},
        "shadows": {"sm": "小阴影", "md": "中阴影", "lg": "大阴影"},
        "seo": {"title": "SEO 标题", "description": "SEO 描述"},
    }