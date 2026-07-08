#!/usr/bin/env python3
"""CMS Models — cms_blocks, cms_posts, cms_settings, cms_categories tables for the database"""
import json
from models import get_db


def init_cms_tables():
    """Create CMS tables if not exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cms_blocks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                page            TEXT NOT NULL,
                section         TEXT NOT NULL,
                block_type      TEXT NOT NULL DEFAULT 'text',
                position        INTEGER NOT NULL DEFAULT 0,
                title           TEXT DEFAULT '',
                subtitle        TEXT DEFAULT '',
                content         TEXT DEFAULT '',
                image_url       TEXT DEFAULT '',
                link_url        TEXT DEFAULT '',
                link_text       TEXT DEFAULT '',
                icon            TEXT DEFAULT '',
                extra_json      TEXT DEFAULT '{}',
                is_published    INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_cms_blocks_page ON cms_blocks(page, position);

            CREATE TABLE IF NOT EXISTS cms_categories (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                icon            TEXT DEFAULT '📄',
                slug            TEXT DEFAULT '',
                audience        TEXT NOT NULL DEFAULT 'public',
                sort_order      INTEGER NOT NULL DEFAULT 0,
                is_active       INTEGER NOT NULL DEFAULT 1,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS cms_posts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                slug            TEXT UNIQUE NOT NULL,
                category        TEXT NOT NULL DEFAULT 'insights',
                title           TEXT NOT NULL DEFAULT '',
                excerpt         TEXT DEFAULT '',
                content         TEXT DEFAULT '',
                content_format  TEXT DEFAULT 'html',
                cover_image     TEXT DEFAULT '',
                author          TEXT DEFAULT '',
                tags            TEXT DEFAULT '[]',
                audience        TEXT NOT NULL DEFAULT 'public',
                is_published    INTEGER NOT NULL DEFAULT 0,
                publish_channels TEXT DEFAULT '[]',
                published_at    TEXT DEFAULT NULL,
                source          TEXT DEFAULT 'manual',
                source_id       INTEGER DEFAULT NULL,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_cms_posts_cat ON cms_posts(category, published_at);

            CREATE TABLE IF NOT EXISTS cms_settings (
                key             TEXT PRIMARY KEY,
                value           TEXT NOT NULL DEFAULT '',
                description     TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS downloads (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                slug            TEXT UNIQUE NOT NULL,
                name            TEXT NOT NULL,
                tagline         TEXT DEFAULT '',
                description     TEXT DEFAULT '',
                category        TEXT NOT NULL DEFAULT 'skills',
                platforms       TEXT DEFAULT '["linux","macos","windows"]',
                version         TEXT NOT NULL DEFAULT '1.0.0',
                release_date    TEXT DEFAULT '',
                repo_url        TEXT DEFAULT '',
                download_url    TEXT DEFAULT '',
                docs_url        TEXT DEFAULT '',
                changelog_url   TEXT DEFAULT '',
                file_size       TEXT DEFAULT '',
                checksum_sha256 TEXT DEFAULT '',
                license         TEXT DEFAULT 'MIT',
                requirements    TEXT DEFAULT '',
                tags            TEXT DEFAULT '[]',
                icon            TEXT DEFAULT '📦',
                sort_order      INTEGER NOT NULL DEFAULT 0,
                is_published    INTEGER NOT NULL DEFAULT 1,
                download_count  INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_downloads_cat ON downloads(category, sort_order);
        """)
        # Seed default categories if empty
        existing = conn.execute("SELECT COUNT(*) FROM cms_categories").fetchone()[0]
        if existing == 0:
            cats = [
                # ── 公开分类 ──
                (1, '快速入门', '🔰', 'getting-started', 'public', 1),
                (2, 'Agent 开发', '🤖', 'agent-dev', 'internal', 2),
                (3, '金融分析', '📈', 'finance', 'public', 3),
                (4, '最佳实践', '⭐', 'best-practices', 'internal', 4),
                (5, '产品动态', '📢', 'insights', 'public', 5),
                (6, '帮助中心', '❓', 'help', 'public', 6),
                (7, '法律合规', '⚖️', 'legal', 'public', 90),
            ]
            for cid, name, icon, slug, audience, sort in cats:
                conn.execute(
                    "INSERT INTO cms_categories (id, name, icon, slug, audience, sort_order) VALUES (?,?,?,?,?,?)",
                    (cid, name, icon, slug, audience, sort)
                )
        # Migration: add source/source_id columns for existing DBs (idempotent)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(cms_posts)").fetchall()]
        if 'source' not in cols:
            conn.execute("ALTER TABLE cms_posts ADD COLUMN source TEXT DEFAULT 'manual'")
        if 'source_id' not in cols:
            conn.execute("ALTER TABLE cms_posts ADD COLUMN source_id INTEGER DEFAULT NULL")
        conn.commit()


# ── Block helpers ──────────────────────────────────────────

def get_page_blocks(page: str):
    """Get all published blocks for a page, ordered by position."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM cms_blocks WHERE page=? AND is_published=1 ORDER BY position",
            (page,)
        ).fetchall()
        return [dict(r) for r in rows]


def upsert_block(data: dict):
    """Insert or update a content block."""
    with get_db() as conn:
        if data.get('id'):
            conn.execute("""
                UPDATE cms_blocks SET
                    page=?, section=?, block_type=?, position=?,
                    title=?, subtitle=?, content=?, image_url=?,
                    link_url=?, link_text=?, icon=?, extra_json=?,
                    is_published=?, updated_at=datetime('now')
                WHERE id=?
            """, (
                data.get('page', ''), data.get('section', ''), data.get('block_type', 'text'),
                data.get('position', 0), data.get('title', ''), data.get('subtitle', ''),
                data.get('content', ''), data.get('image_url', ''), data.get('link_url', ''),
                data.get('link_text', ''), data.get('icon', ''), data.get('extra_json', '{}'),
                data.get('is_published', 1), data['id']
            ))
        else:
            cur = conn.execute("""
                INSERT INTO cms_blocks (page, section, block_type, position, title, subtitle,
                    content, image_url, link_url, link_text, icon, extra_json, is_published)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data.get('page', ''), data.get('section', ''), data.get('block_type', 'text'),
                data.get('position', 0), data.get('title', ''), data.get('subtitle', ''),
                data.get('content', ''), data.get('image_url', ''), data.get('link_url', ''),
                data.get('link_text', ''), data.get('icon', ''), data.get('extra_json', '{}'),
                data.get('is_published', 1)
            ))
            data['id'] = cur.lastrowid
        conn.commit()
    return data


def delete_block(block_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM cms_blocks WHERE id=?", (block_id,))
        conn.commit()


def reorder_blocks(page: str, block_ids: list):
    with get_db() as conn:
        for i, bid in enumerate(block_ids):
            conn.execute("UPDATE cms_blocks SET position=?, updated_at=datetime('now') WHERE id=? AND page=?",
                         (i, bid, page))
        conn.commit()


# ── Post helpers ──────────────────────────────────────────

def get_posts(category: str = None, limit: int = 20, offset: int = 0, published_only: bool = True,
              audience: str = None):
    with get_db() as conn:
        sql = "SELECT * FROM cms_posts WHERE 1=1 "
        params = []
        if category:
            sql += "AND category=? "
            params.append(category)
        if audience:
            sql += "AND audience=? "
            params.append(audience)
        if published_only:
            sql += "AND is_published=1 "
        sql += "ORDER BY published_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        posts = [dict(r) for r in rows]
        for p in posts:
            if isinstance(p.get('publish_channels'), str):
                p['publish_channels'] = json.loads(p['publish_channels'])
        return posts


def get_post_by_slug(slug: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM cms_posts WHERE slug=? AND is_published=1", (slug,)).fetchone()
        return dict(row) if row else None


def get_post_by_slug_preview(slug: str):
    """Get article by slug for preview (bypass is_published filter for admin preview)."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM cms_posts WHERE slug=?", (slug,)).fetchone()
        return dict(row) if row else None


def get_all_posts(limit: int = 50, offset: int = 0, status_filter: str = None, audience: str = None,
                  source: str = None):
    with get_db() as conn:
        sql = "SELECT * FROM cms_posts"
        params = []
        conditions = []
        if status_filter == 'draft':
            conditions.append("is_published=0")
        elif status_filter == 'published':
            conditions.append("is_published=1")
        if source and source != 'all':
            conditions.append("source=?")
            params.append(source)
        if audience:
            conditions.append(f"audience=?" if '?' not in audience else "audience IN ({})".format(audience))
            params.append(audience)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        posts = [dict(r) for r in rows]
        for p in posts:
            if isinstance(p.get('publish_channels'), str):
                p['publish_channels'] = json.loads(p['publish_channels'])
        return posts


def sanitize_html(raw: str) -> str:
    """白名单式 HTML 内容净化（不依赖外部库）。"""
    import re

    ALLOWED_TAGS = {
        'p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'a', 'img', 'br', 'hr',
        'strong', 'em', 'b', 'i', 'u', 's', 'sub', 'sup',
        'table', 'tr', 'td', 'th', 'thead', 'tbody', 'tfoot',
        'blockquote', 'pre', 'code', 'figure', 'figcaption',
    }
    DANGEROUS_TAG_PATTERN = re.compile(
        r'<\s*(script|iframe|object|embed|form|input|textarea|select|button|'
        r'meta|link|style|base|noscript|applet|audio|video)\b[^>]*>.*?'
        r'<\s*/\s*\1\s*>',
        re.DOTALL | re.IGNORECASE
    )
    DANGEROUS_SELF_CLOSING = re.compile(
        r'<\s*(input|meta|link|br|hr|img|embed|param|source|area|base|col)\b[^>]*/?>',
        re.IGNORECASE
    )

    # 阶段1：移除危险标签及其内容（不保留内部文本）
    cleaned = DANGEROUS_TAG_PATTERN.sub('', raw)

    # 阶段2：移除自闭合危险标签
    cleaned = DANGEROUS_SELF_CLOSING.sub('', cleaned)

    # 阶段3：清理所有标签的白名单和属性
    def _clean_tag(m):
        tag_text = m.group(0)
        if tag_text.startswith('</'):
            # 闭合标签，只检查标签名是否在白名单
            tag_name = tag_text[2:-1].strip().lower()
            return f'</{tag_name}>' if tag_name in ALLOWED_TAGS else ''
        # 开始标签或自闭合标签
        m2 = re.match(r'<(\w+)(.*?)(\s*/?\s*)>', tag_text, re.DOTALL)
        if not m2:
            return ''
        tag_name = m2.group(1).lower()
        if tag_name not in ALLOWED_TAGS:
            return ''
        # 如果在白名单中，保留标签并清理属性
        attrs_str = m2.group(2)
        closing = m2.group(3)

        # 清理属性：只保留白名单属性，且值不能含危险协议
        SAFE_ATTRS = {'href', 'src', 'alt', 'title', 'class', 'id', 'style', 'target', 'rel', 'width', 'height', 'loading', 'decoding'}
        cleaned_attrs = []
        for attr_match in re.finditer(r'''([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')''', attrs_str):
            attr_name = attr_match.group(1).lower()
            attr_val = attr_match.group(2) or attr_match.group(3) or ''
            # 跳过事件处理器
            if attr_name.startswith('on'):
                continue
            # 跳过非白名单属性
            if attr_name not in SAFE_ATTRS:
                continue
            # 检查危险协议
            lowered_val = attr_val.strip().lower()
            if any(lowered_val.startswith(p) for p in ['javascript:', 'vbscript:', 'data:', 'expression']):
                continue
            cleaned_attrs.append(f'{attr_name}="{attr_val}"')

        attr_space = ' ' + ' '.join(cleaned_attrs) if cleaned_attrs else ''
        return f'<{tag_name}{attr_space}{closing}>'

    # 递归清理所有标签
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = re.sub(r'<[^>]*>', _clean_tag, cleaned)

    return cleaned


def upsert_post(data: dict):
    import re
    # HTML 内容净化（白名单式）
    content = data.get('content', '')
    data['content'] = sanitize_html(content)
    channels_json = json.dumps(data.get('publish_channels', []), ensure_ascii=False)
    tags_json = json.dumps(data.get('tags', []), ensure_ascii=False) if isinstance(data.get('tags'), list) else data.get('tags', '[]')
    with get_db() as conn:
        if data.get('id'):
            conn.execute("""
                UPDATE cms_posts SET
                    slug=?, category=?, title=?, excerpt=?, content=?,
                    content_format=?, cover_image=?, author=?,
                    tags=?, audience=?,
                    is_published=?,
                    publish_channels=?,
                    source=?, source_id=?,
                    published_at=COALESCE(?, published_at),
                    updated_at=datetime('now')
                WHERE id=?
            """, (
                data.get('slug', ''), data.get('category', 'insights'),
                data.get('title', ''), data.get('excerpt', ''), data.get('content', ''),
                data.get('content_format', 'html'), data.get('cover_image', ''), data.get('author', ''),
                tags_json, data.get('audience', 'public'),
                data.get('is_published', 0),
                channels_json,
                data.get('source', 'manual'), data.get('source_id'),
                data.get('published_at') if data.get('is_published') in (1, True) else None,
                data['id']
            ))
        else:
            cur = conn.execute("""
                INSERT INTO cms_posts (slug, category, title, excerpt, content, content_format, cover_image, author, tags, audience, is_published, publish_channels, source, source_id, published_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, CASE WHEN ? THEN datetime('now') ELSE NULL END)
            """, (
                data.get('slug', ''), data.get('category', 'insights'),
                data.get('title', ''), data.get('excerpt', ''), data.get('content', ''),
                data.get('content_format', 'html'), data.get('cover_image', ''), data.get('author', ''),
                tags_json, data.get('audience', 'public'),
                data.get('is_published', 0),
                channels_json,
                data.get('source', 'manual'), data.get('source_id'),
                1 if data.get('is_published') in (1, True) else 0
            ))
            data['id'] = cur.lastrowid
        conn.commit()
    return data


def delete_post(post_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM cms_posts WHERE id=?", (post_id,))
        conn.commit()


# ── Settings helpers ──────────────────────────────────────

def get_setting(key: str, default: str = ''):
    with get_db() as conn:
        row = conn.execute("SELECT value FROM cms_settings WHERE key=?", (key,)).fetchone()
        return row['value'] if row else default


def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO cms_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value)
        )
        conn.commit()


def get_all_settings():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM cms_settings").fetchall()
        return {r['key']: r['value'] for r in rows}


# ── Category helpers ──────────────────────────────────────

def get_categories(active_only=True, audience: str = None):
    with get_db() as conn:
        sql = "SELECT * FROM cms_categories"
        conditions = []
        params = []
        if active_only:
            conditions.append("is_active=1")
        if audience:
            conditions.append("audience=?")
            params.append(audience)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY sort_order, id"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def upsert_category(data: dict):
    with get_db() as conn:
        if data.get('id'):
            conn.execute(
                "UPDATE cms_categories SET name=?, icon=?, slug=?, audience=?, sort_order=?, is_active=? WHERE id=?",
                (data['name'], data.get('icon', '📄'), data.get('slug', ''),
                 data.get('audience', 'public'), int(data.get('sort_order', 0)),
                 data.get('is_active', 1), data['id'])
            )
        else:
            cur = conn.execute(
                "INSERT INTO cms_categories (name, icon, slug, audience, sort_order, is_active) VALUES (?,?,?,?,?,?)",
                (data['name'], data.get('icon', '📄'), data.get('slug', ''),
                 data.get('audience', 'public'), int(data.get('sort_order', 0)),
                 data.get('is_active', 1))
            )
            data['id'] = cur.lastrowid
        conn.commit()
    return data


def delete_category(cat_id: int):
    with get_db() as conn:
        # 检查是否有文章引用此分类
        ref_count = conn.execute(
            "SELECT COUNT(*) FROM cms_posts WHERE category=(SELECT name FROM cms_categories WHERE id=?)",
            (cat_id,)
        ).fetchone()[0]
        if ref_count > 0:
            raise ValueError(f'该分类下有 {ref_count} 篇文章，请先移除或更改文章分类后再删除')
        conn.execute("DELETE FROM cms_categories WHERE id=?", (cat_id,))
        conn.commit()


def reorder_categories(ids: list):
    with get_db() as conn:
        for i, cid in enumerate(ids):
            conn.execute("UPDATE cms_categories SET sort_order=? WHERE id=?", (i, cid))
        conn.commit()


# ── Downloads helpers ─────────────────────────────────────

def get_downloads(category: str = None, published_only: bool = True, limit: int = 50):
    """Get downloads list, optionally filtered by category."""
    with get_db() as conn:
        sql = "SELECT * FROM downloads WHERE 1=1 "
        params = []
        if category:
            sql += "AND category=? "
            params.append(category)
        if published_only:
            sql += "AND is_published=1 "
        sql += "ORDER BY sort_order, id LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        items = [dict(r) for r in rows]
        for it in items:
            for field in ('platforms', 'tags'):
                if isinstance(it.get(field), str):
                    try:
                        it[field] = json.loads(it[field])
                    except Exception:
                        it[field] = []
        return items


def get_download_by_slug(slug: str):
    """Get a single download item by slug."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM downloads WHERE slug=? AND is_published=1", (slug,)
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    try:
        item['tags'] = json.loads(item['tags']) if item.get('tags') else []
    except Exception:
        item['tags'] = []
    return item


def get_download(dl_id: int):
    """Get a single download item by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM downloads WHERE id=?", (dl_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    try:
        item['tags'] = json.loads(item['tags']) if item.get('tags') else []
    except Exception:
        item['tags'] = []
    return item


def get_all_downloads(limit: int = 100):
    """Get all downloads (including unpublished) for admin."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM downloads ORDER BY sort_order, id LIMIT ?", (limit,)
        ).fetchall()
        items = [dict(r) for r in rows]
        for it in items:
            for field in ('platforms', 'tags'):
                if isinstance(it.get(field), str):
                    try:
                        it[field] = json.loads(it[field])
                    except Exception:
                        it[field] = []
        return items


def upsert_download(data: dict):
    """Insert or update a download item."""
    platforms_json = json.dumps(data.get('platforms', []), ensure_ascii=False) if isinstance(data.get('platforms'), list) else data.get('platforms', '[]')
    tags_json = json.dumps(data.get('tags', []), ensure_ascii=False) if isinstance(data.get('tags'), list) else data.get('tags', '[]')
    with get_db() as conn:
        if data.get('id'):
            conn.execute("""
                UPDATE downloads SET
                    slug=?, name=?, tagline=?, description=?, category=?,
                    platforms=?, version=?, release_date=?, repo_url=?,
                    download_url=?, docs_url=?, changelog_url=?,
                    file_size=?, checksum_sha256=?, license=?, requirements=?,
                    tags=?, icon=?, sort_order=?, is_published=?,
                    updated_at=datetime('now')
                WHERE id=?
            """, (
                data.get('slug', ''), data.get('name', ''), data.get('tagline', ''),
                data.get('description', ''), data.get('category', 'skills'),
                platforms_json, data.get('version', '1.0.0'), data.get('release_date', ''),
                data.get('repo_url', ''), data.get('download_url', ''),
                data.get('docs_url', ''), data.get('changelog_url', ''),
                data.get('file_size', ''), data.get('checksum_sha256', ''),
                data.get('license', 'MIT'), data.get('requirements', ''),
                tags_json, data.get('icon', '📦'),
                int(data.get('sort_order', 0)), data.get('is_published', 1),
                data['id']
            ))
        else:
            cur = conn.execute("""
                INSERT INTO downloads (slug, name, tagline, description, category,
                    platforms, version, release_date, repo_url, download_url,
                    docs_url, changelog_url, file_size, checksum_sha256,
                    license, requirements, tags, icon, sort_order, is_published)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data.get('slug', ''), data.get('name', ''), data.get('tagline', ''),
                data.get('description', ''), data.get('category', 'skills'),
                platforms_json, data.get('version', '1.0.0'), data.get('release_date', ''),
                data.get('repo_url', ''), data.get('download_url', ''),
                data.get('docs_url', ''), data.get('changelog_url', ''),
                data.get('file_size', ''), data.get('checksum_sha256', ''),
                data.get('license', 'MIT'), data.get('requirements', ''),
                tags_json, data.get('icon', '📦'),
                int(data.get('sort_order', 0)), data.get('is_published', 1)
            ))
            data['id'] = cur.lastrowid
        conn.commit()
    return data


def delete_download(dl_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM downloads WHERE id=?", (dl_id,))
        conn.commit()


def reorder_downloads(ids: list):
    with get_db() as conn:
        for i, did in enumerate(ids):
            conn.execute("UPDATE downloads SET sort_order=?, updated_at=datetime('now') WHERE id=?",
                         (i, did))
        conn.commit()


def increment_download_count(slug: str):
    with get_db() as conn:
        conn.execute("UPDATE downloads SET download_count=download_count+1 WHERE slug=?", (slug,))
        conn.commit()
