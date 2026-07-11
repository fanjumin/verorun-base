#!/usr/bin/env python3
"""Site Settings Models — 统一设计令牌数据模型"""

import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))

from models.database import get_db

# ── 默认令牌模板 ──
DEFAULT_TOKENS = {
    "brand": {
        "site_name": "",
        "slogan": "",
        "industry": "",
        "brand_story": "",
        "logo_url": "",
        "favicon_url": "",
        "company_name": "",
        "contact_email": "",
    },
    "colors": {
        "primary": "#6366f1",
        "secondary": "#8b5cf6",
        "accent": "#f59e0b",
        "background": "#ffffff",
        "surface": "#f7fafc",
        "text_primary": "#1a202c",
        "text_secondary": "#718096",
        "border": "#e2e8f0",
        "error": "#ef4444",
        "success": "#10b981",
    },
    "typography": {
        "heading_font": "Inter, sans-serif",
        "body_font": "Inter, -apple-system, sans-serif",
        "font_scale": 1.0,
        "h1_size": "2.5rem",
        "h2_size": "1.875rem",
        "h3_size": "1.5rem",
        "body_size": "1rem",
        "small_size": "0.875rem",
        "line_height": 1.75,
    },
    "navigation": {
        "items": [],
    },
    "footer": {
        "sections": [],
        "articles": [],
        "copyright": "",
        "icp_number": "",
        "security_number": "",
    },
    "spacing": {
        "xs": "4px", "sm": "8px", "md": "16px", "lg": "32px", "xl": "64px",
        "section_gap": "64px", "card_padding": "24px",
    },
    "border_radius": {
        "sm": "4px", "md": "8px", "lg": "12px", "full": "9999px",
    },
    "shadows": {
        "sm": "0 1px 2px rgba(0,0,0,0.05)",
        "md": "0 4px 6px rgba(0,0,0,0.1)",
        "lg": "0 10px 15px rgba(0,0,0,0.1)",
    },
    "seo": {
        "title": "",
        "description": "",
    },
    "meta": {
        "generated_by": "manual",
        "version": 1,
    },
}


def init_tables():
    """创建 design_tokens 表"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS design_tokens (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                site_key    TEXT NOT NULL DEFAULT 'platform',
                token_json  TEXT DEFAULT '{}',
                generated_by TEXT DEFAULT 'manual',
                prompt_id   INTEGER DEFAULT NULL,
                version     INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now')),
                UNIQUE(site_key)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dt_site_key ON design_tokens(site_key)")
        conn.commit()


def get_tokens(site_key='platform'):
    """获取站点令牌，不存在则返回默认"""
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM design_tokens WHERE site_key=?', (site_key,)
        ).fetchone()
    if row:
        data = dict(row)
        data['token_json'] = json.loads(data.get('token_json', '{}'))
        return data
    return {'site_key': site_key, 'token_json': dict(DEFAULT_TOKENS), 'generated_by': 'manual', 'version': 1}


def save_tokens(site_key, token_dict, generated_by='manual', prompt_id=None):
    """保存站点令牌"""
    token_json = json.dumps(token_dict, ensure_ascii=False)
    with get_db() as conn:
        existing = conn.execute(
            'SELECT id, version FROM design_tokens WHERE site_key=?', (site_key,)
        ).fetchone()
        if existing:
            new_version = existing['version'] + 1
            conn.execute(
                'UPDATE design_tokens SET token_json=?, generated_by=?, prompt_id=?, version=?, updated_at=datetime(\'now\') WHERE site_key=?',
                (token_json, generated_by, prompt_id, new_version, site_key)
            )
        else:
            conn.execute(
                'INSERT INTO design_tokens (site_key, token_json, generated_by, prompt_id) VALUES (?,?,?,?)',
                (site_key, token_json, generated_by, prompt_id)
            )
        conn.commit()
    return True


def _parse_json_field(val):
    """安全解析 JSON 字段"""
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def migrate_from_legacy():
    """迁移旧表数据到 design_tokens（仅首次）"""
    with get_db() as conn:
        # 检查是否已迁移
        existing = conn.execute(
            "SELECT id FROM design_tokens WHERE site_key='platform'"
        ).fetchone()
        if existing:
            return  # 已迁移

        tokens = dict(DEFAULT_TOKENS)

        # ── 1. 品牌设置 ──
        try:
            brand = conn.execute('SELECT * FROM brand_settings WHERE id=1').fetchone()
            if brand:
                b = dict(brand)
                tokens['brand'].update({
                    'site_name': b.get('site_name_cn', '') or b.get('company_name', ''),
                    'slogan': b.get('slogan', ''),
                    'company_name': b.get('company_name', ''),
                    'logo_url': b.get('logo_url', ''),
                    'favicon_url': b.get('favicon_url', ''),
                    'contact_email': b.get('contact_email', ''),
                })
                tokens['footer']['copyright'] = b.get('copyright', '')
                tokens['footer']['icp_number'] = b.get('icp_number', '')
                tokens['footer']['security_number'] = b.get('security_number', '')
                tokens['seo']['title'] = b.get('seo_title', '')
                tokens['seo']['description'] = b.get('seo_desc', '')
        except Exception:
            pass

        # ── 2. 导航 ──
        try:
            nav_rows = conn.execute(
                "SELECT title, url, sort_order FROM header_nav WHERE site='platform' AND is_enabled=1 ORDER BY sort_order"
            ).fetchall()
            if nav_rows:
                tokens['navigation']['items'] = [
                    {'id': i + 1, 'title': r['title'], 'url': r['url'],
                     'icon': '', 'target': '_self', 'children': []}
                    for i, r in enumerate(nav_rows)
                ]
        except Exception:
            pass

        # ── 3. 页脚链接 ──
        try:
            fl_rows = conn.execute(
                "SELECT section, title, url FROM footer_links WHERE is_enabled=1 ORDER BY section, sort_order"
            ).fetchall()
            sections = {}
            for r in fl_rows:
                sec = r['section']
                if sec not in sections:
                    sections[sec] = {'name': sec, 'links': []}
                sections[sec]['links'].append({'title': r['title'], 'url': r['url']})
            if sections:
                tokens['footer']['sections'] = list(sections.values())
        except Exception:
            pass

        # ── 4. 页脚文章/文档 ──
        try:
            fa_rows = conn.execute(
                "SELECT title, url FROM footer_articles WHERE is_enabled=1 ORDER BY sort_order"
            ).fetchall()
            if fa_rows:
                tokens['footer']['articles'] = [
                    {'title': r['title'], 'url': r['url']} for r in fa_rows
                ]
        except Exception:
            pass

        # ── 5. 主题配置 ──
        try:
            theme_row = conn.execute(
                "SELECT t.config_json FROM site_theme_config s "
                "LEFT JOIN themes t ON s.theme_id = t.id "
                "WHERE s.site_key='main'"
            ).fetchone()
            if theme_row and theme_row['config_json']:
                th_cfg = _parse_json_field(theme_row['config_json'])
                if isinstance(th_cfg, dict):
                    variables = th_cfg.get('variables', {})
                    if isinstance(variables, dict):
                        if 'preset' in variables:
                            is_dark = variables['preset'] == 'dark'
                            if is_dark:
                                tokens['colors'].update({
                                    'background': '#0f172a',
                                    'surface': '#1e293b',
                                    'text_primary': '#f1f5f9',
                                    'text_secondary': '#94a3b8',
                                    'border': '#334155',
                                })
                        if 'font_scale' in variables:
                            tokens['typography']['font_scale'] = variables['font_scale']
                        if 'border_radius' in variables:
                            tokens['border_radius']['md'] = f"{variables['border_radius']}px"
        except Exception:
            pass

        # ── 保存 ──
        token_json = json.dumps(tokens, ensure_ascii=False)
        conn.execute(
            'INSERT INTO design_tokens (site_key, token_json, generated_by, version) VALUES (?,?,?,?)',
            ('platform', token_json, 'migrated', 1)
        )
        conn.commit()
        print('[SiteSettings] Legacy data migrated to design_tokens (platform)')