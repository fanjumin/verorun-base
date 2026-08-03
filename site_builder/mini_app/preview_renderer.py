#!/usr/bin/env python3
"""MiniAppPreviewRenderer — AI plan JSON  →  HTML preview page

Reuses the existing `ai_site_preview.html` template from admin/templates/.
"""

import json
import os

from flask import render_template_string


class MiniAppPreviewRenderer:
    """Render an AI-generated Mini App plan as an editable HTML preview."""

    def __init__(self, template_path=None):
        if template_path is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_path = os.path.join(base, 'admin', 'templates', 'ai_site_preview.html')

        with open(template_path, 'r', encoding='utf-8') as f:
            self._template = f.read()

    # ── Public API ──────────────────────────────────────

    def render(self, plan, draft_tokens=None):
        """Convert an AI plan dict into a complete HTML preview page.

        Args:
            plan: AI-generated plan dict with keys:
                brand, theme, tabBar, pages, widgets
            draft_tokens: existing design_tokens (optional).  Built from plan
                when omitted.

        Returns:
            HTML string rendered via ai_site_preview.html.
        """
        blocks = self._build_draft_blocks(plan.get('pages', []))
        tokens = draft_tokens or self._build_draft_tokens(plan)
        widget_html = self._build_widget_html(plan.get('widgets', []))
        tabbar_html = self._build_tabbar_html(plan.get('tabBar', []))

        return render_template_string(
            self._template,
            draft_tokens=tokens,
            draft_blocks=blocks,
            preview_mode=True,
            mini_app_tabbar=tabbar_html,
            mini_app_widgets=widget_html,
            default_device='iphone-12',
        )

    # ── Block Builders ──────────────────────────────────

    def _build_draft_blocks(self, pages):
        """Convert AI page sections into ai_site_preview.html block format.

        Returns dict:  {page_slug: [{id, title, content, icon, ...}, ...]}
        """
        blocks = {}
        for page in pages:
            slug = page.get('slug', '')
            page_blocks = []
            for section in page.get('sections', []):
                btype = section.get('block_type', 'text')
                title = section.get('title', '')
                bid = '%s_%d' % (slug, len(page_blocks))

                if btype == 'hero':
                    page_blocks.append({
                        'id': bid,
                        'title': title,
                        'content': section.get('subtitle', ''),
                        'icon': section.get('icon', ''),
                        'link_text': section.get('cta_text', ''),
                        'link_url': section.get('cta_url', '/'),
                    })
                elif btype == 'grid' and 'items' in section:
                    for item in section['items']:
                        page_blocks.append({
                            'id': '%s_%d' % (slug, len(page_blocks)),
                            'title': item.get('title', ''),
                            'content': item.get('description', ''),
                            'icon': item.get('icon', ''),
                        })
                else:
                    page_blocks.append({
                        'id': bid,
                        'title': title,
                        'content': section.get('description', section.get('subtitle', '')),
                        'icon': section.get('icon', ''),
                    })

            blocks[slug] = page_blocks
        return blocks

    def _build_draft_tokens(self, plan):
        """Build design_tokens dict from AI plan (brand / theme / pages)."""
        brand = plan.get('brand', {})
        theme = plan.get('theme', {})

        return {
            'brand': {
                'site_name': brand.get('app_name', ''),
                'tagline': brand.get('tagline', ''),
                'brand_story': brand.get('brand_story', ''),
                'slogan': brand.get('tagline', ''),
            },
            'colors': {
                'primary': theme.get('primary_color', '#4F46E5'),
                'secondary': theme.get('secondary_color', '#10B981'),
                'accent': theme.get('accent_color', '#F59E0B'),
                'background': '#FFFFFF',
                'surface': '#F8FAFC',
                'text_primary': '#1F2937',
                'text_secondary': '#64748B',
                'border': '#E2E8F0',
                'error': '#EF4444',
                'success': '#10B981',
            },
            'typography': {
                'body_font': 'system-ui',
                'heading_font': 'system-ui',
                'h1_size': '28px',
                'h2_size': '22px',
                'h3_size': '18px',
                'body_size': '14px',
                'small_size': '12px',
                'line_height': '1.6',
            },
            'navigation': {
                'items': [
                    {'label': p.get('title', p.get('slug', '')), 'href': '/%s' % p.get('slug', ''), 'order': i}
                    for i, p in enumerate(plan.get('pages', []))
                ]
            },
            'footer': {
                'copyright': '\u00a9 %s' % brand.get('app_name', ''),
                'groups': [],
            },
            'spacing': {
                'section_gap': '40px',
                'card_padding': '16px',
                'xs': '4px',
                'sm': '8px',
                'md': '16px',
                'lg': '24px',
                'xl': '40px',
            },
            'seo': {
                'title_template': '%s | Mini App' % brand.get('app_name', ''),
            },
            'meta': {
                'schema_version': '1.0',
                'mini_app': True,
            },
        }

    # ── Widget Helpers ──────────────────────────────────

    def _build_widget_html(self, widgets):
        """Generate widget placeholder HTML snippets."""
        if not widgets:
            return ''

        parts = []
        for w in widgets:
            wtype = w.get('widget_type', '')
            wid = w.get('widget_id', '')
            position = w.get('position', 'inline_section')

            if wtype == 'hot_products' or wid == 'W05':
                parts.append(
                    '<div class="widget-hot-products" data-widget="hot_products"'
                    ' data-count="%s" data-layout="%s" data-columns="%s"'
                    ' data-widget-position="%s">'
                    '<h2 class="widget-title">%s</h2>'
                    '<div class="widget-loading">Loading...</div>'
                    '</div>' % (
                        w.get('count', 4),
                        w.get('layout', 'grid'),
                        w.get('columns', 2),
                        position,
                        w.get('title', 'Hot Products'),
                    )
                )
            elif wtype == 'ad_placement' or wid == 'W08':
                parts.append(
                    '<div data-ad-position="%s" data-ad-page="home"'
                    ' data-ad-width="%s" data-ad-height="%s"'
                    ' data-widget-position="%s"></div>' % (
                        w.get('ad_position', 'home_banner'),
                        w.get('width', 320),
                        w.get('height', 0),
                        position,
                    )
                )
            elif wtype == 'latest_articles' or wid == 'W01':
                parts.append(
                    '<div class="widget-latest-articles" data-widget="latest_articles"'
                    ' data-count="%s" data-layout="%s" data-widget-position="%s">'
                    '<h2 class="widget-title">%s</h2>'
                    '<div class="widget-loading">Loading...</div>'
                    '</div>' % (
                        w.get('count', 3),
                        w.get('layout', 'card'),
                        position,
                        w.get('title', 'Latest'),
                    )
                )
            elif wtype == 'product_reviews' or wid == 'W07':
                parts.append(
                    '<div class="widget-reviews" data-widget="product_reviews"'
                    ' data-product-id="%s" data-count="%s" data-show-stats="%s"'
                    ' data-widget-position="%s">'
                    '<h2 class="widget-title">%s</h2>'
                    '<div class="widget-loading">Loading...</div>'
                    '</div>' % (
                        w.get('product_id', 0),
                        w.get('count', 10),
                        w.get('show_stats', 'true'),
                        position,
                        w.get('title', 'Reviews'),
                    )
                )
            elif wtype == 'search' or wid == 'W12':
                parts.append(
                    '<div class="widget-search" data-widget="search"'
                    ' data-scope="%s" data-placeholder="%s" data-position="%s"'
                    ' data-widget-position="%s"></div>' % (
                        w.get('scope', 'products'),
                        w.get('placeholder', 'Search...'),
                        w.get('search_position', 'inline'),
                        position,
                    )
                )

        return '\n'.join(parts)

    def _build_tabbar_html(self, tabBar):
        """Generate mini-app bottom tabBar HTML."""
        if not tabBar:
            return ''

        icon_map = {
            'home': '\U0001f3e0', 'shop': '\U0001f6cd\ufe0f',
            'cart': '\U0001f6d2', 'user': '\U0001f464',
            'chat': '\U0001f4ac', 'search': '\U0001f50d',
            'heart': '\u2764\ufe0f', 'star': '\u2b50',
            'settings': '\u2699\ufe0f',
        }

        items = []
        for i, tab in enumerate(tabBar):
            label = tab.get('label', '')
            icon = icon_map.get(tab.get('icon', ''), tab.get('icon', '\U0001f4c4'))
            active = 'active' if i == 0 else ''
            items.append(
                '<div class="tab-item %s" data-tab-page="%s">'
                '<span class="tab-icon">%s</span>'
                '<span class="tab-label">%s</span>'
                '</div>' % (active, tab.get('page', ''), icon, label)
            )

        return '<div class="mini-app-tabbar">%s</div>' % ''.join(items)
