#!/usr/bin/env python3
"""
Plugin Manager — 商店客户端
=============================
从 GitHub Raw 拉取 store_catalog.json，本地缓存插件目录。
"""

import os
import json
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

from .models_store import (
    StorePlugin, init_license_store_tables, get_registry_db,
)
from .discovery import parse_version

# Store catalog URL (configurable via environment variable)
STORE_CATALOG_URL = os.environ.get(
    'APP_STORE_CATALOG_URL',
    'https://raw.githubusercontent.com/fanjumin/verorun-store/main/store_catalog.json'
)


class StoreAPIClient:
    """插件商店 API 客户端"""

    def __init__(self):
        self._cache_lock = threading.Lock()
        init_license_store_tables()

    # ── 缓存获取 ──────────────────────────────────────────────────

    def _fetch_catalog(self) -> dict:
        """Fetch store_catalog.json from GitHub Raw.

        Returns:
            {'plugins': [...], 'version': '...', 'updated_at': '...'}
            Empty dict on failure.
        """
        try:
            req = Request(STORE_CATALOG_URL, headers={
                'User-Agent': 'VeroRun-PluginManager/1.0',
            })
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            print(f'[StoreAPIClient] fetch catalog failed: {e}')
            return {}

    # ── 搜索/列表 ──────────────────────────────────────────────────

    def search(self, query: str = '', category: str = '',
               price_type: str = '', page: int = 1,
               page_size: int = 20, sort_by: str = 'downloads') -> dict:
        """搜索商店插件

        从本地缓存查询（缓存由 sync_all() 定期刷新）。
        """
        return self._search_local(query, category, price_type, page, page_size, sort_by)

    def list_by_category(self, category: str = '') -> List[dict]:
        """按分类列出（从本地缓存）"""
        with self._cache_lock:
            with get_registry_db() as conn:
                if category:
                    rows = conn.execute(
                        'SELECT * FROM store_plugins WHERE enabled=1 AND category=%s ORDER BY downloads DESC',
                        (category,)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        'SELECT * FROM store_plugins WHERE enabled=1 ORDER BY downloads DESC'
                    ).fetchall()
                return [StorePlugin.from_row(dict(r)).to_dict() for r in rows]

    def get_detail(self, identifier: str) -> Optional[dict]:
        """获取插件详情（从本地缓存）"""
        with get_registry_db() as conn:
            row = conn.execute(
                'SELECT * FROM store_plugins WHERE identifier=%s',
                (identifier,)
            ).fetchone()
            if row:
                plugin = StorePlugin.from_row(dict(row)).to_dict()
                plugin['_reviews'] = self._get_review_summary(identifier, conn)
                return plugin
        return None

    def _get_review_summary(self, identifier: str, conn=None) -> dict:
        """获取评价统计摘要"""
        if conn is None:
            with get_registry_db() as c:
                return self._get_review_summary(identifier, c)
        row = conn.execute(
            "SELECT COUNT(*) as cnt, AVG(rating) as avg_rating FROM plugin_reviews "
            "WHERE plugin_identifier=%s AND is_active=1",
            (identifier,)
        ).fetchone()
        return {
            'total': row['cnt'] if row else 0,
            'average': round(row['avg_rating'], 1) if row and row['avg_rating'] else 0.0,
        }

    # ── 下载 ────────────────────────────────────────────────────────

    def get_download_url(self, identifier: str, app_version: str = '') -> Optional[str]:
        """获取插件下载地址（从本地缓存，含版本兼容校验）

        Args:
            identifier: 插件标识符
            app_version: 当前系统版本号（如 '0.44.2'），用于兼容性校验

        Returns:
            下载 URL，或 None（不兼容时返回 None）
        """
        with get_registry_db() as conn:
            row = conn.execute(
                'SELECT download_url, min_app_version FROM store_plugins WHERE identifier=%s',
                (identifier,)
            ).fetchone()
            if not row or not row['download_url']:
                return None
            if app_version and row['min_app_version']:
                if not self._version_compatible(app_version, row['min_app_version']):
                    return None
            return row['download_url']

    @staticmethod
    def _version_compatible(current: str, required: str) -> bool:
        """检查当前版本是否满足最低版本要求（semver）"""
        try:
            from packaging.version import Version
            return Version(current) >= Version(required)
        except ImportError:
            def _parse(v):
                try:
                    return tuple(int(x) for x in v.split('.'))
                except (ValueError, AttributeError):
                    return (0,)
            return _parse(current) >= _parse(required)

    # ── 本地缓存 ────────────────────────────────────────────────────

    def _search_local(self, query: str, category: str,
                      price_type: str, page: int,
                      page_size: int, sort_by: str = 'downloads') -> dict:
        """从本地缓存搜索"""
        with self._cache_lock:
            with get_registry_db() as conn:
                sql = 'SELECT s.* FROM store_plugins s WHERE s.enabled=1'
                params = []

                if query:
                    sql += ' AND (s.name LIKE %s OR s.description LIKE %s OR s.identifier LIKE %s)'
                    like = f'%{query}%'
                    params.extend([like, like, like])
                if category:
                    sql += ' AND s.category=%s'
                    params.append(category)
                if price_type:
                    sql += ' AND s.price_type=%s'
                    params.append(price_type)

                # 排序
                sort_map = {
                    'downloads': 's.downloads DESC',
                    'rating': 's.rating DESC',
                    'newest': 's.created_at DESC',
                    'price_asc': 's.price_amount ASC',
                    'price_desc': 's.price_amount DESC',
                }
                sql += f' ORDER BY {sort_map.get(sort_by, "s.downloads DESC")}'

                # 总数（去掉 ORDER BY，PG 不允许 count 查询带排序列）
                count_sql = sql.replace('SELECT s.* FROM', 'SELECT COUNT(*) as cnt FROM')
                order_pos = count_sql.find(' ORDER BY ')
                if order_pos != -1:
                    count_sql = count_sql[:order_pos]
                total = conn.execute(count_sql, params).fetchone()['cnt']

                # 分页
                offset = (page - 1) * page_size
                sql += ' LIMIT %s OFFSET %s'
                params.extend([page_size, offset])

                rows = conn.execute(sql, params).fetchall()
                plugins = []
                for r in rows:
                    p = StorePlugin.from_row(dict(r)).to_dict()
                    p['_reviews'] = self._get_review_summary(p['identifier'], conn)
                    plugins.append(p)

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
                        screenshots, readme_url, downloads, rating, review_count, enabled
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1)
                    -- ★ ON CONFLICT: 仅更新商店侧管理的字段。author/author_url/icon_url/trial_days/
                    --    min_app_version/depends_on/screenshots/readme_url 不在更新列表中，
                    --    以防止缓存同步覆盖 Store Admin 手动录入的内容。
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
                        review_count=excluded.review_count,
                        updated_at=NOW()
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
                    pdata.get('review_count', 0),
                ))
                conn.commit()

    def sync_all(self) -> int:
        """从 GitHub Raw 同步全部插件目录到本地缓存

        Returns:
            同步的插件数量；-1 表示目录源拉取失败但本地已有缓存
            （保留缓存继续可用），0 表示拉取失败且本地无缓存（首次拉取）。
        """
        catalog = self._fetch_catalog()
        if not catalog:
            # 目录源拉取失败：保留本地缓存，向上层明确反馈失败状态
            cached = 0
            try:
                with get_registry_db() as conn:
                    cached = conn.execute(
                        'SELECT COUNT(*) AS cnt FROM store_plugins'
                    ).fetchone()['cnt']
            except Exception as e:
                print(f'[StoreAPIClient] sync_all: 查询本地缓存失败: {e}')
            if cached and cached > 0:
                print(f'[StoreAPIClient] sync_all: 目录拉取失败，保留本地缓存 {cached} 条 (return -1)')
                return -1
            print('[StoreAPIClient] sync_all: 目录拉取失败，且无本地缓存 (return 0)')
            return 0

        plugins_data = catalog.get('plugins', [])
        for pdata in plugins_data:
            self._upsert_cache(pdata)
        return len(plugins_data)

    def check_updates(self, local_versions: dict) -> dict:
        """对比本地已安装版本与商店目录版本，返回各插件的更新状态。

        Args:
            local_versions: {identifier: installed_version}，
                            如 {'ads': '1.0.0'}（来源：plugin_registry）

        Returns:
            {identifier: {installed, latest, has_update, min_app_version}}
            仅包含"本地已安装 且 商店目录上架"的插件。
        """
        print(f'[StoreAPIClient] check_updates: 收到本地已安装插件 {len(local_versions)} 个: {local_versions}')
        if not local_versions:
            print('[StoreAPIClient] check_updates: local_versions 为空，无可对比项，直接返回空结果')
            return {}

        # 读取商店目录（本地缓存表 store_plugins，仅 enabled=1 上架项）
        try:
            with get_registry_db() as conn:
                rows = conn.execute(
                    'SELECT identifier, version, min_app_version FROM store_plugins WHERE enabled=1'
                ).fetchall()
        except Exception as e:
            print(f'[StoreAPIClient] check_updates: 查询 store_plugins 失败: {e}，返回空结果')
            return {}
        print(f'[StoreAPIClient] check_updates: 商店目录上架插件 {len(rows)} 条')

        result = {}
        matched = 0
        skipped = 0
        for r in rows:
            identifier = r['identifier']
            latest = r['version']
            installed = local_versions.get(identifier)
            if installed is None:
                skipped += 1
                print(f'[StoreAPIClient] check_updates: 跳过 {identifier} — 本地未安装（商店 v{latest}）')
                continue
            matched += 1

            # 解析版本号；任一非法版本退化为字符串比较
            latest_ver = parse_version(latest)
            installed_ver = parse_version(installed)
            if latest_ver is None or installed_ver is None:
                print(f'[StoreAPIClient] check_updates: ⚠️ {identifier} 版本号无法解析 '
                      f'(installed={installed!r}, latest={latest!r})，退化为字符串比较')
                has_update = latest != installed
            else:
                has_update = latest_ver > installed_ver

            print(f'[StoreAPIClient] check_updates: {identifier} '
                  f'installed={installed} latest={latest} has_update={has_update} '
                  f'min_app_version={r["min_app_version"]}')
            result[identifier] = {
                'installed': installed,
                'latest': latest,
                'has_update': has_update,
                'min_app_version': r['min_app_version'],
            }

        updatable = sum(1 for v in result.values() if v['has_update'])
        print(f'[StoreAPIClient] check_updates: 完成 — 匹配 {matched} 个已安装插件，跳过 {skipped} 个未安装，'
              f'其中可更新 {updatable} 个')
        return result


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
