#!/usr/bin/env python3
"""CMS 页面生成器 — 将 LLM 输出的页面内容写入 cms_blocks / cms_posts 表"""

import json
from models import get_db


class PageGenerator:
    """CMS 页面区块生成器"""

    @staticmethod
    def apply_page_blocks(page: str, sections_data: list):
        """将页面区块数据写入 cms_blocks 表（幂等：先清后写）

        page: 页面标识，如 'home', 'about', 'services'
        sections_data: LLM 返回的 sections 列表
        """
        with get_db() as conn:
            # 清空当前页面的所有区块
            conn.execute("DELETE FROM cms_blocks WHERE page=?", (page,))

            position = 0
            for section in sections_data:
                position += 1
                block_type = section.get('block_type', 'text')
                title = section.get('title', '')
                subtitle = section.get('subtitle', '')
                section_name = section.get('section_name', block_type)

                # 处理 items 列表（features, services 等区块）
                items = section.get('items', [])
                if items:
                    # 每个 item 作为独立区块
                    for item in items:
                        position += 1
                        conn.execute(
                            """INSERT INTO cms_blocks
                               (page, section, block_type, position, title, subtitle, content, link_text, link_url, icon)
                               VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (
                                page,
                                section_name,
                                'feature' if block_type == 'features' else 'text',
                                position,
                                item.get('title', ''),
                                item.get('description', ''),
                                item.get('description', ''),
                                '了解更多',
                                f"/{page}",
                                item.get('icon', ''),
                            )
                        )
                else:
                    # 单区块（hero, cta, text）
                    conn.execute(
                        """INSERT INTO cms_blocks
                           (page, section, block_type, position, title, subtitle, content, link_text, link_url)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            page,
                            section_name,
                            block_type,
                            position,
                            title,
                            subtitle,
                            section.get('description', subtitle),
                            section.get('cta_text', ''),
                            section.get('cta_url', '/'),
                        )
                    )
            conn.commit()
        print(f'[SiteBuilder] ✅ Page "{page}" applied: {len(sections_data)} sections')

    @staticmethod
    def apply_page_text(page: str, text_data: dict):
        """写入简单文本页面（如关于我们、服务领域等非区块化页面）

        text_data: LLM 返回的 JSON（包含 content 或 sections 字段）
        """
        # 尝试提取 sections
        sections = text_data.get('sections', [])
        if sections:
            PageGenerator.apply_page_blocks(page, sections)
            return

        # 纯文本页面：写入单个 text 区块
        content = text_data.get('content', '') or json.dumps(text_data, ensure_ascii=False)
        with get_db() as conn:
            conn.execute("DELETE FROM cms_blocks WHERE page=?", (page,))
            conn.execute(
                """INSERT INTO cms_blocks (page, section, block_type, position, title, content)
                   VALUES (?,?,?,?,?,?)""",
                (page, 'main', 'text', 1, page, content)
            )
            conn.commit()
        print(f'[SiteBuilder] ✅ Page "{page}" applied (text mode)')

    @staticmethod
    def apply_document(slug: str, title: str, html_content: str):
        """写入法律文档到 cms_posts 表

        slug: 文档标识（如 privacy_policy, terms_of_service）
        title: 文档标题
        html_content: LLM 生成的 HTML 内容
        """
        with get_db() as conn:
            # UPSERT
            existing = conn.execute(
                "SELECT id FROM cms_posts WHERE slug=?", (slug,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE cms_posts SET title=?, content=?, updated_at=datetime('now') WHERE slug=?",
                    (title, html_content, slug)
                )
            else:
                conn.execute(
                    """INSERT INTO cms_posts (slug, title, content, category, status, is_published, created_at)
                       VALUES (?,?,?,'legal','published',1,datetime('now'))""",
                    (slug, title, html_content)
                )
            conn.commit()
        print(f'[SiteBuilder] ✅ Document "{slug}" applied')

    @staticmethod
    def modify_block(block_id: int, changes: dict):
        """最小化修改：更新单个区块的指定字段

        changes: {"title": "新标题", "content": "新内容", ...}
        """
        allowed_fields = ['title', 'subtitle', 'content', 'link_text', 'link_url', 'image_url', 'icon']
        fields = []
        params = []
        for key, val in changes.items():
            if key in allowed_fields:
                fields.append(f"{key}=?")
                params.append(val)
        if not fields:
            return False

        params.append(block_id)
        with get_db() as conn:
            conn.execute(
                f"UPDATE cms_blocks SET {', '.join(fields)} WHERE id=?",
                params
            )
            conn.commit()
        print(f'[SiteBuilder] ✅ Block #{block_id} modified: {list(changes.keys())}')
        return True

    @staticmethod
    def get_page_summary(page: str) -> list:
        """获取页面所有区块的摘要（用于 LLM 修改上下文）"""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, block_type, section, title, subtitle, content FROM cms_blocks WHERE page=? ORDER BY position",
                (page,)
            ).fetchall()
        return [{
            'id': r['id'],
            'block_type': r['block_type'],
            'section': r['section'],
            'title': (r['title'] or '')[:80],
            'content_preview': (r['content'] or '')[:100],
        } for r in rows]