#!/usr/bin/env python3
"""
Plugin Manager — 商店客户端
=============================
连接远程插件商店 API，本地缓存插件目录。
远程 API 未就绪时使用内置 Mock 数据。

SPI 模式: store.py 与 license.py 共享 _call_remote() 通信层。
"""

import json
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models_store import (
    StorePlugin, init_license_store_tables, get_registry_db,
)
from .license import _call_remote


class StoreAPIClient:
    """插件商店 API 客户端"""

    def __init__(self):
        self._cache_lock = threading.Lock()
        init_license_store_tables()

    # ── 搜索/列表 ──────────────────────────────────────────────────

    def search(self, query: str = '', category: str = '',
               price_type: str = '', page: int = 1,
               page_size: int = 20) -> dict:
        """搜索商店插件

        先尝试远程 API，失败后从本地缓存查询。
        """
        remote = _call_remote('GET', '/plugins/search', {
            'query': query,
            'category': category,
            'price_type': price_type,
            'page': page,
            'page_size': page_size,
        })

        if remote.get('success') and remote.get('data', {}).get('plugins'):
            plugins_data = remote['data']['plugins']
            # 同步到本地缓存
            for pdata in plugins_data:
                self._upsert_cache(pdata)
            return remote['data']

        # 降级：本地缓存
        return self._search_local(query, category, price_type, page, page_size)

    def list_by_category(self, category: str = '') -> List[dict]:
        """按分类列出（从本地缓存）"""
        with self._cache_lock:
            with get_registry_db() as conn:
                if category:
                    rows = conn.execute(
                        'SELECT * FROM store_plugins WHERE enabled=1 AND category=? ORDER BY downloads DESC',
                        (category,)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        'SELECT * FROM store_plugins WHERE enabled=1 ORDER BY downloads DESC'
                    ).fetchall()
                return [StorePlugin.from_row(dict(r)).to_dict() for r in rows]

    def get_detail(self, identifier: str) -> Optional[dict]:
        """获取插件详情"""
        # 尝试远程
        remote = _call_remote('GET', f'/plugins/{identifier}')
        if remote.get('success') and remote.get('data'):
            pdata = remote['data']
            self._upsert_cache(pdata)
            return pdata

        # 降级：本地缓存
        with get_registry_db() as conn:
            row = conn.execute(
                'SELECT * FROM store_plugins WHERE identifier=?',
                (identifier,)
            ).fetchone()
            if row:
                return StorePlugin.from_row(dict(row)).to_dict()
        return None

    # ── 下载 ────────────────────────────────────────────────────────

    def get_download_url(self, identifier: str) -> Optional[str]:
        """获取插件下载地址"""
        remote = _call_remote('GET', f'/plugins/{identifier}/download')
        if remote.get('success') and remote.get('data', {}).get('download_url'):
            return remote['data']['download_url']
        # 本地缓存
        with get_registry_db() as conn:
            row = conn.execute(
                'SELECT download_url FROM store_plugins WHERE identifier=?',
                (identifier,)
            ).fetchone()
            return row['download_url'] if row else None

    # ── 本地缓存 ────────────────────────────────────────────────────

    def _search_local(self, query: str, category: str,
                      price_type: str, page: int,
                      page_size: int) -> dict:
        """从本地缓存搜索"""
        with self._cache_lock:
            with get_registry_db() as conn:
                sql = 'SELECT * FROM store_plugins WHERE enabled=1'
                params = []

                if query:
                    sql += ' AND (name LIKE ? OR description LIKE ? OR identifier LIKE ?)'
                    like = f'%{query}%'
                    params.extend([like, like, like])
                if category:
                    sql += ' AND category=?'
                    params.append(category)
                if price_type:
                    sql += ' AND price_type=?'
                    params.append(price_type)

                sql += ' ORDER BY downloads DESC'

                # 总数
                count_sql = sql.replace('SELECT *', 'SELECT COUNT(*) as cnt')
                total = conn.execute(count_sql, params).fetchone()['cnt']

                # 分页
                offset = (page - 1) * page_size
                sql += f' LIMIT ? OFFSET ?'
                params.extend([page_size, offset])

                rows = conn.execute(sql, params).fetchall()
                plugins = [StorePlugin.from_row(dict(r)).to_dict() for r in rows]

                return {
                    'plugins': plugins,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                }

    def _upsert_cache(self, pdata: dict):
        """插入或更新本地缓存"""
        with self._cache_lock:
            with get_registry_db() as conn:
                conn.execute("""
                    INSERT INTO store_plugins (
                        identifier, name, description, version, author,
                        author_url, icon_url, price_type, price_amount,
                        price_interval, trial_days, download_url, package_hash,
                        file_size, category, tags, min_app_version, depends_on,
                        screenshots, readme_url, downloads, rating, enabled
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
                    ON CONFLICT(identifier) DO UPDATE SET
                        name=excluded.name,
                        description=excluded.description,
                        version=excluded.version,
                        price_type=excluded.price_type,
                        price_amount=excluded.price_amount,
                        price_interval=excluded.price_interval,
                        download_url=excluded.download_url,
                        package_hash=excluded.package_hash,
                        file_size=excluded.file_size,
                        category=excluded.category,
                        tags=excluded.tags,
                        downloads=excluded.downloads,
                        rating=excluded.rating,
                        updated_at=datetime('now')
                """, (
                    pdata.get('identifier', ''),
                    pdata.get('name', ''),
                    pdata.get('description', ''),
                    pdata.get('version', '0.1.0'),
                    pdata.get('author', ''),
                    pdata.get('author_url', ''),
                    pdata.get('icon_url', ''),
                    pdata.get('price_type', 'free'),
                    pdata.get('price_amount', 0),
                    pdata.get('price_interval', 'onetime'),
                    pdata.get('trial_days', 0),
                    pdata.get('download_url', ''),
                    pdata.get('package_hash', ''),
                    pdata.get('file_size', 0),
                    pdata.get('category', ''),
                    json.dumps(pdata.get('tags', [])),
                    pdata.get('min_app_version', '0.10.0'),
                    json.dumps(pdata.get('depends_on', {})),
                    json.dumps(pdata.get('screenshots', [])),
                    pdata.get('readme_url', ''),
                    pdata.get('downloads', 0),
                    pdata.get('rating', 0.0),
                ))
                conn.commit()

    def sync_all(self) -> int:
        """从远程同步全部插件目录

        Returns:
            同步的插件数量
        """
        remote = _call_remote('GET', '/plugins', {'page_size': 200})
        if not remote.get('success'):
            return 0

        plugins_data = remote.get('data', {}).get('plugins', [])
        for pdata in plugins_data:
            self._upsert_cache(pdata)
        return len(plugins_data)


# ── 模块级单例 ──────────────────────────────────────────────────────

_STORE_CLIENT = None
_STORE_CLIENT_LOCK = threading.Lock()


def get_store_client() -> StoreAPIClient:
    global _STORE_CLIENT
    if _STORE_CLIENT is None:
        with _STORE_CLIENT_LOCK:
            if _STORE_CLIENT is None:
                _STORE_CLIENT = StoreAPIClient()
    return _STORE_CLIENT
