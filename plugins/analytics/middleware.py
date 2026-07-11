#!/usr/bin/env python3
"""
analytics/middleware.py — Flask 请求捕获中间件

职责（按执行顺序）:
  1. 请求开始时: 记录开始时间 + 扩展请求属性
  2. 请求结束时: 采集所有数据 → 匿名化 IP → 生成 Visitor Hash / Session Hash
     → 写入 analytics_logs + 更新会话
  3. IP 匿名化在接收请求的第一时间完成
  4. 自动区分真实用户 / AI 爬虫 / 内部测试

集成方式:
  from analytics.middleware import AnalyticsMiddleware
  AnalyticsMiddleware(app, service_name='trademind')

或者手动注册 before_request / after_request:
  from analytics.middleware import capture_before, capture_after
  app.before_request(capture_before)
  app.after_request(capture_after)
"""

import time
import re
import os
import sys
import sqlite3
import fnmatch
from datetime import datetime

# ─── 本地导入 ──────────────────────────────────────────────────────────────────
from . import models as am
from .geoip import geoip_lookup, init_geoip
from .ua_parser import parse_ua

# ─── 全局状态 ──────────────────────────────────────────────────────────────────

# 排除规则（从隐私配置读取，启动时也设默认值）
EXCLUDE_PATHS = [
    '/static/*', '/favicon.ico', '/robots.txt', '/health',
]
EXCLUDE_PATH_REGEX = None

INTERNAL_IP_RANGES = [
    '127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
]

ANALYTICS_ENABLED = True
SERVICE_NAME = 'unknown'

# 性能采样率：高流量下可降采样（1.0 = 全部记录）
SAMPLE_RATE = 1.0

# 数据库写入重试配置
_DB_RETRIES = 3
_DB_RETRY_DELAY = 0.1  # 100ms


def _db_write(func):
    """装饰器：遇到 database is locked 时自动重试"""
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(_DB_RETRIES):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e) and attempt < _DB_RETRIES - 1:
                    time.sleep(_DB_RETRY_DELAY * (attempt + 1))
                    continue
                raise
    return wrapper


def _init_exclude_patterns():
    """编译排除路径的正则模式"""
    global EXCLUDE_PATH_REGEX
    patterns = []
    for p in EXCLUDE_PATHS:
        if '*' in p:
            regex = fnmatch.translate(p)
        else:
            regex = f'^{re.escape(p)}$'
        patterns.append(regex)
    EXCLUDE_PATH_REGEX = re.compile('|'.join(patterns)) if patterns else None


def _should_exclude(path: str) -> bool:
    """检查路径是否应被排除"""
    if not EXCLUDE_PATH_REGEX:
        return False
    return bool(EXCLUDE_PATH_REGEX.search(path))


def _should_exclude_ip(ip: str) -> bool:
    """检查 IP 是否在排除范围（内部IP）"""
    try:
        import ipaddress
        ip_obj = ipaddress.ip_address(ip)
        for r in INTERNAL_IP_RANGES:
            try:
                net = ipaddress.ip_network(r, strict=False)
                if ip_obj in net:
                    return True
            except:
                continue
    except:
        pass
    return False


# ─── 中间件类 ──────────────────────────────────────────────────────────────────

class AnalyticsMiddleware:
    """
    Flask 分析中间件

    用法:
        from analytics.middleware import AnalyticsMiddleware
        app = Flask(__name__)
        AnalyticsMiddleware(app, service_name='platform', geoip_enabled=True)
    """

    def __init__(self, app, service_name: str = 'unknown',
                 geoip_enabled: bool = True, sample_rate: float = 1.0):
        global SERVICE_NAME, SAMPLE_RATE
        SERVICE_NAME = service_name
        SAMPLE_RATE = sample_rate

        # 初始化数据库表
        am.init_analytics_tables()

        # 初始化 GeoIP
        if geoip_enabled:
            init_geoip()

        # 编译排除规则
        self._load_privacy_config()
        _init_exclude_patterns()

        # 注册钩子
        app.before_request(self.before_request)
        app.after_request(self.after_request)

        print(f'[Analytics] ✅ 中间件已注册 [{service_name}] 采样率={sample_rate}')

    def _load_privacy_config(self):
        """从数据库加载隐私配置"""
        try:
            conn = am.get_db()
            config = am.get_privacy_config(conn)
            if config.get('exclude_paths'):
                global EXCLUDE_PATHS
                try:
                    import json
                    paths = json.loads(config['exclude_paths'])
                    if isinstance(paths, list):
                        EXCLUDE_PATHS = paths
                except:
                    pass
            if config.get('internal_ip_ranges'):
                try:
                    import json
                    ranges = json.loads(config['internal_ip_ranges'])
                    if isinstance(ranges, list):
                        global INTERNAL_IP_RANGES
                        INTERNAL_IP_RANGES = ranges
                except:
                    pass
            conn.close()
        except:
            pass

    def _get_client_ip(self):
        """获取真实客户端 IP（优先 X-Forwarded-For，回退 remote_addr）"""
        from flask import request
        forwarded = request.headers.get('X-Forwarded-For', '')
        if forwarded:
            # 取第一个 IP（最原始的客户端 IP）
            return forwarded.split(',')[0].strip()
        return request.remote_addr or ''

    def before_request(self):
        """请求开始：记录开始时间"""
        from flask import request, g
        g._analytics_start = time.time()
        g._analytics_skip = False

        # 检查排除条件
        path = request.path
        ip = self._get_client_ip()

        should_skip = (
            not ANALYTICS_ENABLED
            or _should_exclude(path)
            or _should_exclude_ip(ip)
        )

        if should_skip:
            g._analytics_skip = True

    def after_request(self, response):
        """请求结束：采集数据 → 匿名化 → 哈希 → 写入"""
        from flask import request, g, current_app

        # 跳过标记
        if getattr(g, '_analytics_skip', False):
            return response

        # 采样
        if SAMPLE_RATE < 1.0:
            import random
            if random.random() > SAMPLE_RATE:
                return response

        try:
            start_time = getattr(g, '_analytics_start', None)
            if start_time is None:
                return response

            response_time = int((time.time() - start_time) * 1000)
            now = int(time.time())
            today_str = datetime.now().strftime('%Y-%m-%d')

            # 1. 获取原始数据
            raw_ip = self._get_client_ip()
            user_agent = request.headers.get('User-Agent', '')
            path = request.path
            query_string = am.anonymize_query_string(request.query_string.decode('utf-8') if hasattr(request.query_string, 'decode') else (request.query_string or ''))
            referer = request.headers.get('Referer', '') or ''
            language = request.headers.get('Accept-Language', '')[:64]
            method = request.method
            status = response.status_code
            content_type = response.headers.get('Content-Type', 'text/html')

            # 构建完整 URL
            host = request.headers.get('Host', '')
            scheme = request.headers.get('X-Forwarded-Proto', 'https')
            full_url = f'{scheme}://{host}{path}'
            if query_string:
                full_url += f'?{query_string}'

            # 2. 立即匿名化 IP（第一步！）
            ip_prefix = am.hash_ip(raw_ip)

            # 3. 检测爬虫
            is_bot = am.is_bot(user_agent)

            # 4. 解析 UA（非爬虫才解析以节省资源）
            browser = ''
            browser_version = ''
            os_name = ''
            device_type = 'desktop'
            if not is_bot and user_agent:
                ua_data = parse_ua(user_agent)
                browser = ua_data.get('browser', '')
                browser_version = ua_data.get('browser_version', '')
                os_name = ua_data.get('os_name', '')
                device_type = ua_data.get('device_type', 'desktop')
                # 如果 UA 解析器也返回 is_bot，采纳
                if ua_data.get('is_bot'):
                    is_bot = True

            # 5. 地理定位（仅对真实用户）
            country = ''
            city = ''
            if not is_bot and raw_ip and raw_ip != '127.0.0.1':
                geo = geoip_lookup(raw_ip)
                country = geo.get('country', '')
                city = geo.get('city', '')

            # 6. 生成访客哈希
            visitor_hash = am.make_visitor_hash(ip_prefix, user_agent, today_str)

            # 7. 生成会话哈希
            session_hash = am.make_session_hash(visitor_hash, now)

            # 8. 来源分类
            source_type, source_name = am.classify_source(referer)
            ref_domain = am.normalize_referer(referer)

            # 9. UTM 参数提取
            from urllib.parse import parse_qs as pqs
            utm_source = ''
            utm_medium = ''
            utm_campaign = ''
            if query_string:
                qs_parsed = pqs(query_string)
                utm_source = qs_parsed.get('utm_source', [''])[0]
                utm_medium = qs_parsed.get('utm_medium', [''])[0]
                utm_campaign = qs_parsed.get('utm_campaign', [''])[0]

            # 10. 写入原始日志（带重试）
            @_db_write
            def _do_write():
                conn = am.get_db()
                try:
                    am.insert_log(conn, {
                        'timestamp': now,
                        'visitor_hash': visitor_hash,
                        'session_hash': session_hash,
                        'ip_prefix': ip_prefix,
                        'country': country,
                        'city': city,
                        'user_agent': user_agent[:512],
                        'browser': browser,
                        'browser_version': browser_version,
                        'os_name': os_name,
                        'device_type': device_type,
                        'is_bot': is_bot,
                        'path': path,
                        'query_string': query_string[:512],
                        'referer': referer[:1024],
                        'referer_domain': ref_domain,
                        'utm_source': utm_source,
                        'utm_medium': utm_medium,
                        'utm_campaign': utm_campaign,
                        'language': language,
                        'status_code': status,
                        'response_time': response_time,
                        'request_method': method,
                        'service_name': SERVICE_NAME,
                        'full_url': full_url[:2048],
                        'content_type': content_type,
                    })

                    # 11. 管理会话（非爬虫）
                    if not is_bot:
                        existing_session = conn.execute(
                            "SELECT id, page_views FROM analytics_visitor_sessions WHERE session_hash=?",
                            (session_hash,)
                        ).fetchone()

                        if existing_session:
                            am.update_session(
                                conn, session_hash,
                                exit_path=path,
                                page_views=existing_session['page_views'] + 1,
                                duration=int(time.time()) - start_time
                            )
                        else:
                            existing_visitor = conn.execute(
                                "SELECT id FROM analytics_visitor_sessions WHERE visitor_hash=? AND date=?",
                                (visitor_hash, today_str)
                            ).fetchone()
                            is_new = 1 if existing_visitor is None else 0

                            am.track_session(
                                conn, session_hash, visitor_hash, today_str,
                                start_time=now,
                                entry_path=path,
                                referer=ref_domain or '',
                                browser=browser,
                                os_name=os_name,
                                device_type=device_type,
                                country=country,
                                city=city,
                                is_bot=0,
                                is_new=is_new,
                            )
                finally:
                    conn.close()

            _do_write()
        except Exception as e:
            # 中间件绝不能影响主请求
            import traceback
            print(f'[Analytics] ⚠️ 采集异常: {e}')
            traceback.print_exc()

        return response


# ─── 快捷函数 ──────────────────────────────────────────────────────────────────

def capture_before():
    """方便手动注册的 before_request 函数"""
    from flask import request, g
    g._analytics_start = time.time()
    g._analytics_skip = False

    path = request.path
    ip = request.remote_addr or ''
    if not ANALYTICS_ENABLED or _should_exclude(path) or _should_exclude_ip(ip):
        g._analytics_skip = True


def capture_after(response):
    """方便手动注册的 after_request 函数"""
    from flask import request, g

    if getattr(g, '_analytics_skip', False):
        return response
    if SAMPLE_RATE < 1.0:
        import random
        if random.random() > SAMPLE_RATE:
            return response

    try:
        start_time = getattr(g, '_analytics_start', None)
        if start_time is None:
            return response

        response_time = int((time.time() - start_time) * 1000)
        now = int(time.time())
        today_str = datetime.now().strftime('%Y-%m-%d')

        raw_ip = request.remote_addr or ''
        user_agent = request.headers.get('User-Agent', '')
        path = request.path
        query_string = am.anonymize_query_string(
            request.query_string.decode('utf-8') if hasattr(request.query_string, 'decode') else (request.query_string or '')
        )
        referer = request.headers.get('Referer', '') or ''
        language = request.headers.get('Accept-Language', '')[:64]
        method = request.method
        status = response.status_code

        ip_prefix = am.hash_ip(raw_ip)
        is_bot = am.is_bot(user_agent)

        browser, browser_version, os_name = '', '', ''
        device_type = 'desktop'
        if not is_bot and user_agent:
            ua_data = parse_ua(user_agent)
            browser = ua_data.get('browser', '')
            browser_version = ua_data.get('browser_version', '')
            os_name = ua_data.get('os_name', '')
            device_type = ua_data.get('device_type', 'desktop')
            if ua_data.get('is_bot'):
                is_bot = True

        visitor_hash = am.make_visitor_hash(ip_prefix, user_agent, today_str)
        session_hash = am.make_session_hash(visitor_hash, now)

        source_type, source_name = am.classify_source(referer)
        ref_domain = am.normalize_referer(referer)

        country, city = '', ''
        if not is_bot and raw_ip and raw_ip != '127.0.0.1':
            geo = geoip_lookup(raw_ip)
            country = geo.get('country', '')
            city = geo.get('city', '')

        @_db_write
        def _do_write_capture():
            conn = am.get_db()
            try:
                am.insert_log(conn, {
                    'timestamp': now, 'visitor_hash': visitor_hash,
                    'session_hash': session_hash, 'ip_prefix': ip_prefix,
                    'country': country, 'city': city,
                    'user_agent': user_agent[:512], 'browser': browser,
                    'browser_version': browser_version, 'os_name': os_name,
                    'device_type': device_type, 'is_bot': is_bot,
                    'path': path, 'query_string': query_string[:512],
                    'referer': referer[:1024], 'referer_domain': ref_domain,
                    'language': language, 'status_code': status,
                    'response_time': response_time, 'request_method': method,
                    'service_name': SERVICE_NAME,
                })
            finally:
                conn.close()

        _do_write_capture()
    except Exception as e:
        print(f'[Analytics] ⚠️ capture_after: {e}')

    return response
