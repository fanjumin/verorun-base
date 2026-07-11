#!/usr/bin/env python3
"""导航 & 页脚生成器 — 将 LLM 输出的导航/页脚数据写入统一 design_tokens"""

from site_builder.site_settings.models import get_tokens, save_tokens


class NavigationGenerator:
    """主导航 & 页脚生成器（统一令牌版）"""

    @staticmethod
    def apply_nav(nav_data: dict, site_key='platform'):
        """写入主导航到 design_tokens.navigation.items

        nav_data 期望字段：
            nav_items: [{"title": "...", "url": "/...", "icon": "", "children": [...]}, ...]
        """
        items = nav_data.get('nav_items', [])
        formatted = []
        for i, item in enumerate(items):
            formatted.append({
                'id': i + 1,
                'title': item.get('title', ''),
                'url': item.get('url', '/'),
                'icon': item.get('icon', ''),
                'target': item.get('target', '_self'),
                'children': item.get('children', []),
            })

        tokens = get_tokens(site_key)
        current = tokens['token_json']
        current['navigation']['items'] = formatted
        save_tokens(site_key, current, generated_by='ai', prompt_id=None)
        print(f'[SiteBuilder] ✅ Navigation applied via design_tokens: {len(formatted)} items')

    @staticmethod
    def apply_footer(footer_data: dict, site_key='platform'):
        """写入页脚分组到 design_tokens.footer.sections

        footer_data 期望字段：
            footer_groups: [{"group_name": "...", "links": [{"title": "...", "url": "..."}]}]
        """
        groups = footer_data.get('footer_groups', [])
        sections = []
        for group in groups:
            sections.append({
                'name': group.get('group_name', ''),
                'links': group.get('links', []),
            })

        tokens = get_tokens(site_key)
        current = tokens['token_json']
        current['footer']['sections'] = sections
        save_tokens(site_key, current, generated_by='ai', prompt_id=None)
        print(f'[SiteBuilder] ✅ Footer applied via design_tokens: {len(sections)} groups')

    @staticmethod
    def apply_footer_articles(documents: list, site_key='platform'):
        """写入页脚法律文档链接到 design_tokens.footer.articles

        documents: [{"id": "privacy_policy", "name": "隐私政策"}, ...]
        """
        articles = []
        for doc in documents:
            slug = doc.get('id', '')
            name = doc.get('name', '')
            if slug and name:
                articles.append({
                    'title': name,
                    'url': f'/page/{slug}',
                })

        tokens = get_tokens(site_key)
        current = tokens['token_json']
        current['footer']['articles'] = articles
        save_tokens(site_key, current, generated_by='ai', prompt_id=None)
        print(f'[SiteBuilder] ✅ Footer articles applied via design_tokens: {len(articles)}')