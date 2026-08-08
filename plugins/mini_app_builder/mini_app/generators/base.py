#!/usr/bin/env python3
"""Base class for mini-program generators"""

import os
import json
import shutil
from abc import ABC, abstractmethod


class BaseMiniAppGenerator(ABC):
    """Abstract base for platform-specific mini-program generators.

    Each platform generator inherits from this class and implements
    the generate() method to produce platform-specific mini-program files.
    """

    platform: str = ''          # 'douyin' | 'wechat' | 'telegram' | 'line'
    template_dir: str = ''      # Path to platform-specific template directory
    output_base: str = 'dist'   # Base output directory (relative or absolute)

    def __init__(self, output_base: str = None):
        if output_base:
            self.output_base = output_base

    @abstractmethod
    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        """Generate mini-program files for this platform.

        Args:
            site_config: Site configuration (tokens, prompt template, etc.)
            brand: Brand settings dict (site_name, primary_color, logo_url, etc.)
            options: Generation options (include_chat, include_pages, base_url, etc.)

        Returns:
            {
                'output_dir': 'dist/douyin/',
                'files': ['app.js', 'pages/chat/chat.js', ...],
                'platform': 'douyin',
                'compatible_with': ['toutiao']  # optional
            }
        """
        pass

    def _copy_template(self, output_dir: str):
        """Copy template files from self.template_dir to output_dir.

        Clears existing output_dir first for idempotency.
        """
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        if os.path.exists(self.template_dir):
            shutil.copytree(self.template_dir, output_dir)

    def _render_template(self, template_path: str, context: dict) -> str:
        """Render a template file with {{ variable }} substitution.

        Uses simple string replacement (not Jinja2) to avoid dependency.
        """
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for key, value in context.items():
            placeholder = f'{{{{ {key} }}}}'
            content = content.replace(placeholder, str(value))
        return content

    def _write_file(self, path: str, content: str):
        """Write content to a file, creating parent directories as needed."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _get_brand_context(self, brand: dict) -> dict:
        """Extract and normalize brand context for template rendering."""
        return {
            'app_name': brand.get('site_name', ''),
            'tagline': brand.get('tagline', ''),
            'primary_color': brand.get('primary_color', '#1890ff'),
            'secondary_color': brand.get('secondary_color', ''),
            'logo_url': brand.get('logo_url', ''),
            'favicon_url': brand.get('favicon_url', ''),
            'brand_story': brand.get('brand_story', ''),
        }

    def _get_api_context(self, options: dict) -> dict:
        """Extract and normalize API context for template rendering."""
        return {
            'base_url': options.get('base_url', 'https://your-domain.com'),
            'api_prefix': options.get('api_prefix', '/api/v1/mini-program'),
            'platform': self.platform,
        }

    def _collect_files(self, output_dir: str) -> list:
        """Collect all file paths relative to output_dir."""
        files = []
        for root, _, filenames in os.walk(output_dir):
            for f in filenames:
                files.append(os.path.relpath(os.path.join(root, f), output_dir))
        return files

    # ── AI Plan Generation ─────────────────────────────

    def generate_from_plan(self, ai_plan: dict, platform: str, options: dict) -> dict:
        """Generate mini-app code from an AI-generated plan.

        Args:
            ai_plan: { brand, theme, tabBar, pages, widgets }
            platform: Target platform identifier
            options: Generation options

        Returns:
            { output_dir, files, platform }
        """
        output_dir = os.path.join(self.output_base, platform)
        self._copy_template(output_dir)

        # 1. Build app.json
        app_config = self._build_app_config_from_plan(ai_plan, platform)
        self._write_file(
            os.path.join(output_dir, 'app.json'),
            json.dumps(app_config, ensure_ascii=False, indent=2)
        )

        # 2. Generate global stylesheet
        global_css = self._render_global_css_from_plan(ai_plan, platform)
        style_path = os.path.join(output_dir, 'app.%s' % self._get_style_ext(platform))
        self._write_file(style_path, global_css)

        # 3. Generate each page from plan
        context = {
            'brand': ai_plan.get('brand', {}),
            'theme': ai_plan.get('theme', {}),
            'widgets': ai_plan.get('widgets', []),
            'api': self._get_api_context(options),
        }
        for page in ai_plan.get('pages', []):
            self._generate_page_from_plan(page, context, output_dir, platform)

        # 4. Inject widget JS
        self._inject_widgets_from_plan(ai_plan.get('widgets', []), platform, output_dir)

        return {
            'output_dir': output_dir,
            'files': self._collect_files(output_dir),
            'platform': platform,
        }

    # ── Page Extension Helpers (overridable) ───────────

    def _get_page_ext(self, platform: str) -> str:
        """Return view file extension for the platform."""
        return 'html'

    def _get_style_ext(self, platform: str) -> str:
        """Return stylesheet file extension for the platform."""
        return 'css'

    # ── Plan → Config / CSS / Pages ────────────────────

    def _build_app_config_from_plan(self, ai_plan: dict, platform: str) -> dict:
        """Build app.json from AI plan."""
        pages = ['pages/%s/%s' % (p['slug'], p['slug']) for p in ai_plan.get('pages', [])]
        theme = ai_plan.get('theme', {})
        brand = ai_plan.get('brand', {})

        config = {
            'pages': pages,
            'window': {
                'navigationBarBackgroundColor': theme.get('primary_color', '#4F46E5'),
                'navigationBarTitleText': brand.get('app_name', ''),
                'navigationBarTextStyle': 'white',
                'backgroundColor': '#F8FAFC',
            },
        }

        tabBar = ai_plan.get('tabBar', [])
        if tabBar:
            config['tabBar'] = {
                'color': '#999999',
                'selectedColor': theme.get('primary_color', '#4F46E5'),
                'backgroundColor': '#FFFFFF',
                'borderStyle': 'black',
                'list': [
                    {
                        'pagePath': 'pages/%s/%s' % (t['page'], t['page']),
                        'text': t['label'],
                        'iconPath': 'icons/%s.png' % t.get('icon', 'home'),
                        'selectedIconPath': 'icons/%s-active.png' % t.get('icon', 'home'),
                    }
                    for t in tabBar
                ],
            }

        return config

    def _render_global_css_from_plan(self, ai_plan: dict, platform: str) -> str:
        """Generate global stylesheet with CSS variables from AI plan theme."""
        theme = ai_plan.get('theme', {})
        return (
            'page {\n'
            '  --color-primary: %s;\n'
            '  --color-secondary: %s;\n'
            '  --color-accent: %s;\n'
            '  --color-background: #FFFFFF;\n'
            '  --color-surface: #F8FAFC;\n'
            '  --color-text-primary: #1F2937;\n'
            '  --color-text-secondary: #64748B;\n'
            '  --color-border: #E2E8F0;\n'
            '  --font-family: system-ui, -apple-system, sans-serif;\n'
            '}\n'
            '.container { padding: 16px; }\n'
            '.card { background: var(--color-surface); border-radius: 12px; padding: 16px; margin-bottom: 12px; }\n'
            '.btn-primary { background: var(--color-primary); color: #fff; border: none; border-radius: 8px; padding: 12px 24px; font-size: 16px; font-weight: 600; }\n'
        ) % (
            theme.get('primary_color', '#4F46E5'),
            theme.get('secondary_color', '#10B981'),
            theme.get('accent_color', '#F59E0B'),
        )

    def _generate_page_from_plan(self, page: dict, context: dict, output_dir: str, platform: str):
        """Generate a single page from AI plan section data."""
        slug = page.get('slug', '')
        title = page.get('title', slug)
        page_dir = os.path.join(output_dir, 'pages', slug)
        os.makedirs(page_dir, exist_ok=True)

        ext = self._get_page_ext(platform)
        style_ext = self._get_style_ext(platform)

        # Render sections and widgets
        sections_html = self._render_sections(page.get('sections', []))
        widget_html = self._render_page_widgets(context.get('widgets', []), slug)

        # Build page template
        view = (
            '<view class="container">\n'
            '  <text class="page-title">%s</text>\n'
            '%s\n'
            '%s\n'
            '</view>\n'
        ) % (title, sections_html, widget_html)

        self._write_file(os.path.join(page_dir, '%s.%s' % (slug, ext)), view)

        # Write stylesheet
        style = (
            '.page-title { font-size: 22px; font-weight: 700; color: var(--color-text-primary); margin-bottom: 16px; }\n'
        )
        self._write_file(os.path.join(page_dir, '%s.%s' % (slug, style_ext)), style)

    def _render_sections(self, sections: list) -> str:
        """Render AI plan sections to platform template markup."""
        parts = []
        for section in sections:
            btype = section.get('block_type', 'text')
            title = section.get('title', '')

            if btype == 'hero':
                parts.append(
                    '<view class="hero-section">\n'
                    '  <view class="hero-content">\n'
                    '    <text class="hero-title">%s</text>\n'
                    '    <text class="hero-subtitle">%s</text>\n'
                    '    <button class="btn-primary hero-cta">%s</button>\n'
                    '  </view>\n'
                    '</view>' % (
                        title,
                        section.get('subtitle', ''),
                        section.get('cta_text', 'Learn More'),
                    )
                )
            elif btype == 'grid' and 'items' in section:
                items_html = ''
                for item in section['items']:
                    items_html += (
                        '<view class="grid-item">\n'
                        '  <text class="grid-icon">%s</text>\n'
                        '  <text class="grid-title">%s</text>\n'
                        '  <text class="grid-desc">%s</text>\n'
                        '</view>\n' % (
                            item.get('icon', ''),
                            item.get('title', ''),
                            item.get('description', ''),
                        )
                    )
                parts.append(
                    '<view class="section-block">\n'
                    '  <text class="section-title">%s</text>\n'
                    '  <view class="grid-container">%s</view>\n'
                    '</view>' % (title, items_html)
                )
            else:
                parts.append(
                    '<view class="section-block">\n'
                    '  <text class="section-title">%s</text>\n'
                    '  <text class="section-content">%s</text>\n'
                    '</view>' % (title, section.get('description', section.get('subtitle', '')))
                )

        return '\n'.join(parts)

    def _render_page_widgets(self, widgets: list, page_slug: str) -> str:
        """Generate page-level widget placeholders."""
        parts = []
        for w in widgets:
            if w.get('page') == page_slug or w.get('position') == 'inline_section':
                wtype = w.get('widget_type', '')
                if wtype == 'hot_products' or w.get('widget_id') == 'W05':
                    parts.append(
                        '<view class="widget-section" data-widget="hot_products">\n'
                        '  <text class="widget-title">%s</text>\n'
                        '  <view class="widget-content" id="hot-products-%s"></view>\n'
                        '</view>' % (w.get('title', 'Hot Products'), page_slug)
                    )
                elif wtype == 'ad_placement' or w.get('widget_id') == 'W08':
                    parts.append(
                        '<view class="widget-section" data-widget="ad">\n'
                        '  <ad unit-id="%s" ad-type="banner" ad-intervals="%s"></ad>\n'
                        '</view>' % (w.get('ad_unit_id', ''), w.get('ad_intervals', 30))
                    )
        return '\n'.join(parts)

    def _inject_widgets_from_plan(self, widgets: list, platform: str, output_dir: str):
        """Write widgets.js with initialization logic."""
        if not widgets:
            return

        widget_js = (
            '// Auto-generated Widget Initialization\n'
            'var MiniAppWidgets = {\n'
            '  init: function() {\n'
            '    var el;\n'
            '    el = document.querySelector(\'[data-widget="hot_products"]\');\n'
            '    if (el) { this.loadHotProducts(el); }\n'
            '    el = document.querySelector(\'[data-widget="ad"]\');\n'
            '    if (el) { this.initAd(el); }\n'
            '  },\n'
            '  loadHotProducts: function(el) {\n'
            '    var count = el.getAttribute("data-count") || 4;\n'
            '    fetch("/shop/api/products?sort_by=sales_count&limit=" + count)\n'
            '      .then(function(r) { return r.json(); })\n'
            '      .then(function(data) { /* render product cards */ });\n'
            '  },\n'
            '  initAd: function(el) {\n'
            '    /* Platform-specific ad initialization */\n'
            '  }\n'
            '};\n'
            'MiniAppWidgets.init();\n'
        )

        utils_dir = os.path.join(output_dir, 'utils')
        os.makedirs(utils_dir, exist_ok=True)
        self._write_file(os.path.join(utils_dir, 'widgets.js'), widget_js)