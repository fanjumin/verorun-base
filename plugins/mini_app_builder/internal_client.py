#!/usr/bin/env python3
"""mini_app_builder — internal service client (v2.1.0).

插件数据库解耦后，品牌信息、已发布页面、draft tokens 等共享数据不再直连
主库，改为调用 main_site 提供的内部 API（/api/internal/*），带 LRU 缓存与
超时兜底，避免主站短暂不可用时插件功能完全失效。

环境变量：
    MAIN_SITE_INTERNAL_URL  内部 API 基地址（默认 http://127.0.0.1:8081）
    INTERNAL_SERVICE_TOKEN  内部服务令牌（与 main_site 配置一致）
"""

import os
import time
import json
import urllib.error
import urllib.parse
import urllib.request

_BASE = os.environ.get('MAIN_SITE_INTERNAL_URL', 'http://127.0.0.1:8081')
_TOKEN = os.environ.get('INTERNAL_SERVICE_TOKEN', '')

# key -> (fetched_at, value)
_cache = {}

# key 缓存有效期（秒）
_CACHE_TTL = {
    'site_info': 300,
    'brand': 300,
    'pages': 300,
    'page': 300,
    'draft_tokens': 60,
}

_DEFAULT_BRAND = {
    'site_name': 'VeroRun',
    'tagline': '',
    'primary_color': '#1890ff',
    'secondary_color': '',
    'logo_url': '',
    'favicon_url': '',
}


def _http_get(path: str, params: dict = None, timeout: float = 5.0):
    """GET 内部 API，返回解析后的 dict/list。失败抛异常由调用方兜底。"""
    url = _BASE + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'X-Internal-Token': _TOKEN})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8') or '{}')


def _cached(key: str, ttl: int, fetch):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = fetch()
    _cache[key] = (now, value)
    return value


def get_brand_settings() -> dict:
    """品牌设置（带缓存 + 默认兜底）。

    返回完整品牌 dict（site_name/tagline/brand_story/colors/logo 等），
    由 MiniAppEngine 透传给各平台 generators。
    """
    def _f():
        data = _http_get('/api/internal/brand') or {}
        if not data or 'site_name' not in data:
            return dict(_DEFAULT_BRAND)
        return data
    try:
        return _cached('brand', _CACHE_TTL['brand'], _f)
    except Exception:
        return dict(_DEFAULT_BRAND)


def get_published_pages() -> list:
    """已发布页面列表（slug/title/meta）。"""
    def _f():
        data = _http_get('/api/internal/cms/pages')
        return data if isinstance(data, list) else []
    try:
        return _cached('pages', _CACHE_TTL['pages'], _f)
    except Exception:
        return []


def get_published_page(slug: str) -> dict | None:
    """单个已发布页面（含 blocks）。"""
    def _f():
        try:
            data = _http_get(f'/api/internal/cms/page/{urllib.parse.quote(slug)}')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        return data if isinstance(data, dict) else None
    try:
        return _cached(f'page_{slug}', _CACHE_TTL['page'], _f)
    except Exception:
        return None


def get_draft_tokens() -> dict:
    """site_builder draft tokens（生成站点时使用，短缓存）。"""
    def _f():
        data = _http_get('/api/internal/site/draft-tokens')
        return data if isinstance(data, dict) else {}
    try:
        return _cached('draft_tokens', _CACHE_TTL['draft_tokens'], _f)
    except Exception:
        return {}
