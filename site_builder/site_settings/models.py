#!/usr/bin/env python3
"""Site Settings Models — Unified Design Token Data Model"""

import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))

from models.database import get_db

# ── Default Token Template ──
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
    """Create design_tokens table"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS design_tokens (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                site_key    TEXT NOT NULL DEFAULT 'platform',
                token_json  TEXT DEFAULT '{}',
                generated_by TEXT DEFAULT 'manual',
                prompt_id   INTEGER DEFAULT NULL,
                version     INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT NOW(),
                updated_at  TEXT DEFAULT NOW(),
                UNIQUE(site_key)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dt_site_key ON design_tokens(site_key)")
        # Migration: add draft_json column if not exists
        try:
            conn.execute("ALTER TABLE design_tokens ADD COLUMN draft_json TEXT DEFAULT '{}'")
        except Exception:
            pass  # column already exists
        conn.commit()


def get_tokens(site_key='platform'):
    """Get site tokens, return defaults if not found"""
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM design_tokens WHERE site_key=%s', (site_key,)
        ).fetchone()
    if row:
        data = dict(row)
        data['token_json'] = json.loads(data.get('token_json', '{}'))
        return data
    return {'site_key': site_key, 'token_json': dict(DEFAULT_TOKENS), 'generated_by': 'manual', 'version': 1}


def save_tokens(site_key, token_dict, generated_by='manual', prompt_id=None):
    """Save site tokens"""
    token_json = json.dumps(token_dict, ensure_ascii=False)
    with get_db() as conn:
        existing = conn.execute(
            'SELECT id, version FROM design_tokens WHERE site_key=%s', (site_key,)
        ).fetchone()
        if existing:
            new_version = existing['version'] + 1
            conn.execute(
                'UPDATE design_tokens SET token_json=%s, generated_by=%s, prompt_id=%s, version=%s, updated_at=datetime(\'now\') WHERE site_key=%s',
                (token_json, generated_by, prompt_id, new_version, site_key)
            )
        else:
            conn.execute(
                'INSERT INTO design_tokens (site_key, token_json, generated_by, prompt_id) VALUES (%s,%s,%s,%s)',
                (site_key, token_json, generated_by, prompt_id)
            )
        conn.commit()
    return True


def _parse_json_field(val):
    """Safely parse JSON field"""
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def migrate_from_legacy():
    """Migrate legacy table data to design_tokens (first-time only)"""
    with get_db() as conn:
        # Check if already migrated
        existing = conn.execute(
            "SELECT id FROM design_tokens WHERE site_key='platform'"
        ).fetchone()
        if existing:
            return  # Already migrated

        tokens = dict(DEFAULT_TOKENS)

        # ── 1. Brand Settings ──
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

        # ── 2. Navigation ──
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

        # ── 3. Footer Links ──
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

        # ── 4. Footer Articles / Documents ──
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

        # ── 5. Theme Config ──
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

        # ── Save ──
        token_json = json.dumps(tokens, ensure_ascii=False)
        conn.execute(
            'INSERT INTO design_tokens (site_key, token_json, generated_by, version) VALUES (%s,%s,%s,%s)',
            ('platform', token_json, 'migrated', 1)
        )
        conn.commit()
        print('[SiteSettings] Legacy data migrated to design_tokens (platform)')


# ── Draft / Preview / Publish ─────────────────────────────────


def get_draft_tokens(site_key='platform'):
    """Get draft tokens from design_tokens.draft_json"""
    with get_db() as conn:
        row = conn.execute(
            'SELECT draft_json FROM design_tokens WHERE site_key=%s', (site_key,)
        ).fetchone()
    if row and row['draft_json']:
        try:
            return json.loads(row['draft_json'])
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def save_draft_tokens(site_key, token_dict):
    """Save draft tokens to design_tokens.draft_json (does NOT touch token_json)"""
    draft_json = json.dumps(token_dict, ensure_ascii=False)
    with get_db() as conn:
        existing = conn.execute(
            'SELECT id FROM design_tokens WHERE site_key=%s', (site_key,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE design_tokens SET draft_json=%s, updated_at=NOW() WHERE site_key=%s",
                (draft_json, site_key)
            )
        else:
            conn.execute(
                'INSERT INTO design_tokens (site_key, token_json, draft_json, generated_by) VALUES (%s,%s,%s,%s)',
                (site_key, '{}', draft_json, 'ai_draft')
            )
        conn.commit()
    return True


def promote_draft_tokens(site_key='platform'):
    """Promote draft tokens to production (draft_json → token_json)"""
    draft = get_draft_tokens(site_key)
    if draft is None:
        return False
    return save_tokens(site_key, draft, generated_by='ai_published')


def backup_tokens(site_key='platform'):
    """Backup current production tokens into a field before overwriting"""
    data = get_tokens(site_key)
    # Save backup alongside current data (simply store as token_json backup)
    backup_label = f'_backup_{data["version"]}'
    backup_val = json.dumps(data['token_json'], ensure_ascii=False)
    with get_db() as conn:
        try:
            conn.execute(
                f"UPDATE design_tokens SET {backup_label}=%s WHERE site_key=%s",
                (backup_val, site_key)
            )
        except Exception:
            pass  # column may not exist — non-critical
        conn.commit()
