#!/usr/bin/env python3
"""导航 & 页脚生成器 — 将 LLM 输出的导航/页脚数据写入对应表"""

import json
from models import get_db


class NavigationGenerator:
    """主导航 & 页脚生成器"""

    @staticmethod
    def apply_nav(nav_data: dict, site: str = 'www'):
        """写入主导航 header_nav 表（幂等：先清后写）

        nav_data 期望字段：
            nav_items: [{"title": "...", "url": "/..."}, ...]
        """
        items = nav_data.get('nav_items', [])
        with get_db() as conn:
            # 清空当前 site 的导航
            conn.execute("DELETE FROM header_nav WHERE site=?", (site,))
            for i, item in enumerate(items):
                conn.execute(
                    "INSERT INTO header_nav (site, title, url, sort_order, is_enabled) VALUES (?,?,?,?,1)",
                    (site, item.get('title', ''), item.get('url', '/'), i + 1)
                )
            conn.commit()
        print(f'[SiteBuilder] ✅ Navigation applied: {len(items)} items')

    @staticmethod
    def apply_footer(footer_data: dict):
        """写入页脚结构 — footer_links + footer_articles

        footer_data 期望字段：
            footer_groups: [{"group_name": "...", "links": [{"title": "...", "url": "..."}]}]
        """
        groups = footer_data.get('footer_groups', [])
        with get_db() as conn:
            # 清空 footer_links
            conn.execute("DELETE FROM footer_links")

            section_order = 0
            total_links = 0
            for group in groups:
                section_order += 1
                group_name = group.get('group_name', '')
                links = group.get('links', [])
                for i, link in enumerate(links):
                    conn.execute(
                        "INSERT INTO footer_links (section, title, url, sort_order, is_enabled) VALUES (?,?,?,?,1)",
                        (group_name, link.get('title', ''), link.get('url', '/'), i + 1)
                    )
                    total_links += 1
            conn.commit()
        print(f'[SiteBuilder] ✅ Footer applied: {len(groups)} groups, {total_links} links')

    @staticmethod
    def apply_footer_articles(documents: list):
        """写入页脚法律文档链接 footer_articles 表

        documents: [{"id": "privacy_policy", "name": "隐私政策"}, ...]
        """
        article_slugs = [d.get('id', '') for d in documents]
        articles = []
        for doc in documents:
            slug = doc.get('id', '')
            name = doc.get('name', '')
            if slug and name:
                articles.append({
                    'title': name,
                    'url': f'/page/{slug}'
                })

        with get_db() as conn:
            # 清空
            conn.execute("DELETE FROM footer_articles")
            for i, article in enumerate(articles):
                conn.execute(
                    "INSERT INTO footer_articles (title, url, sort_order, is_enabled) VALUES (?,?,?,1)",
                    (article['title'], article['url'], i + 1)
                )
            conn.commit()
        print(f'[SiteBuilder] ✅ Footer articles applied: {len(articles)} items')