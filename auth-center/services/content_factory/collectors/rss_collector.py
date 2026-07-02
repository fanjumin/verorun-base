#!/usr/bin/env python3
"""RSS/Atom 通用采集器 — 基于 feedparser"""
from datetime import datetime
from typing import List, Optional
from ..base_collector import BaseCollector, CollectResult

try:
    import feedparser
except ImportError:
    feedparser = None


class RSSCollector(BaseCollector):
    """通用 RSS 采集器

    用法:
        col = RSSCollector(source_id, config={'url': 'https://example.com/feed.xml'})
        results = col.collect(count=10)
    """

    name = 'rss'
    source_type = 'rss'

    def collect(self, **kwargs) -> List[CollectResult]:
        if feedparser is None:
            raise ImportError("请先 pip install feedparser")

        url = kwargs.get('url') or self.config.get('url', '')
        if not url:
            return []

        feed = feedparser.parse(url, agent=self._random_ua())
        if not feed.entries:
            return []

        results = []
        limit = kwargs.get('count') or self.config.get('max_per_run', 10)

        for entry in feed.entries[:limit]:
            content_text = ''
            content_html = ''
            if hasattr(entry, 'content') and entry.content:
                raw = entry.content[0].get('value', '')
                content_html = raw
                content_text = self._strip_html(raw)
            elif hasattr(entry, 'summary'):
                raw = entry.summary or ''
                content_html = raw
                content_text = self._strip_html(raw)
            elif hasattr(entry, 'description'):
                raw = entry.description or ''
                content_html = raw
                content_text = self._strip_html(raw)

            # 提取第一张图片作为封面
            cover_url = ''
            if content_html:
                import re
                m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_html)
                if m:
                    cover_url = m.group(1)

            pub_time = ''
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_time = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_time = datetime(*entry.updated_parsed[:6]).strftime('%Y-%m-%d %H:%M:%S')

            tags = []
            if hasattr(entry, 'tags'):
                tags = [t.get('term', '') for t in entry.tags if t.get('term')]
            tags_str = ','.join(tags)

            results.append(CollectResult(
                title=getattr(entry, 'title', ''),
                content_text=content_text,
                content_html=content_html,
                source_url=entry.get('link', ''),
                author=getattr(entry, 'author', ''),
                publish_time=pub_time,
                summary=content_text[:300],
                tags=tags_str,
                content_json={'cover_url': cover_url},
            ))

        return results
