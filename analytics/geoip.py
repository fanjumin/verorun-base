#!/usr/bin/env python3
"""
analytics/geoip.py — IP 地理解析（ip2region / MaxMind GeoLite2 / ip-api 回退）

设计:
  - 优先使用 ip2region（中国 IP 城市覆盖最佳）
  - 其次 MaxMind GeoLite2 数据库（国际 IP）
  - 如果都不存在，回退到 ip-api.com 在线查询（带缓存）
  - 绝不存储精确 IP
  - 国家 + 城市级别（不存储经纬度）

依赖:
  pip install geoip2         # MaxMind 客户端
  # ip2region 已 vendor 到 analytics/ip2region/
  # 或使用内置的 ip-api 回退（无需额外依赖）

安装:
  1. ip2region: 下载 ip2region_v4.xdb → analytics/data/
  2. GeoLite2: wget https://git.io/GeoLite2-City.mmdb -O /path/to/GeoLite2-City.mmdb
"""

import os
import sys
import time
import json
from urllib.request import urlopen
from urllib.parse import urlencode

# ─── 配置 ──────────────────────────────────────────────────────────────────────

# ip2region xdb 数据库路径
IP2REGION_DB = os.path.join(os.path.dirname(__file__), 'data', 'ip2region_v4.xdb')

# GeoLite2 数据库路径（自动探测）
GEOIP_DB_CANDIDATES = [
    '/home/easykai/easykai-workspace/GeoLite2-City.mmdb',
    '/home/easykai/data/GeoLite2-City.mmdb',
    '/usr/share/GeoIP/GeoLite2-City.mmdb',
    './data/GeoLite2-City.mmdb',
    '../data/GeoLite2-City.mmdb',
]

# ip-api 缓存（避免限流）
IPAPI_CACHE = {}
IPAPI_CACHE_TTL = 3600  # 1 小时缓存

_geoip_reader = None
_ip2region_searcher = None


# ─── ip2region ───────────────────────────────────────────────────────────────────

def _init_ip2region() -> bool:
    """初始化 ip2region（优先于 MaxMind）"""
    global _ip2region_searcher
    if not os.path.exists(IP2REGION_DB):
        print(f'[Analytics] ℹ️ ip2region 数据库未找到: {IP2REGION_DB}')
        return False
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ip2region import util
        from ip2region.searcher import new_with_buffer
        with open(IP2REGION_DB, 'rb') as f:
            _ip2region_searcher = new_with_buffer(util.IPv4, f.read())
        print(f'[Analytics] ✅ ip2region 已加载: {IP2REGION_DB}')
        return True
    except Exception as e:
        print(f'[Analytics] ⚠️ ip2region 加载失败: {e}')
        return False


def _ip2region_lookup(ip: str) -> dict:
    """
    ip2region 查询，解析 "国家|区域|省份|城市|ISP" 格式
    返回: {'country': '中国', 'city': '南京'}
    """
    global _ip2region_searcher
    if not _ip2region_searcher:
        return {}
    try:
        result = _ip2region_searcher.search(ip)
        if not result:
            return {}
        # 格式: "国家|省份|城市|ISP|备用"
        parts = result.split('|')
        country = parts[0] if len(parts) > 0 else ''
        city = parts[2] if len(parts) > 2 and parts[2] != '0' else ''
        # 国家代码映射（ip2region 返回中文名，统一转为 ISO 代码）
        cc = _country_name_to_code(country)
        return {'country': cc, 'city': city}
    except Exception:
        return {}


# 常用国家名 → ISO 代码映射（中文 + 英文）
_COUNTRY_MAP = {
    '中国': 'CN', 'China': 'CN',
    '美国': 'US', 'United States': 'US',
    '日本': 'JP', 'Japan': 'JP',
    '韩国': 'KR', 'South Korea': 'KR', 'Korea': 'KR',
    '英国': 'GB', 'United Kingdom': 'GB',
    '德国': 'DE', 'Germany': 'DE',
    '法国': 'FR', 'France': 'FR',
    '俄罗斯': 'RU', 'Russia': 'RU',
    '印度': 'IN', 'India': 'IN',
    '巴西': 'BR', 'Brazil': 'BR',
    '加拿大': 'CA', 'Canada': 'CA',
    '澳大利亚': 'AU', 'Australia': 'AU',
    '新加坡': 'SG', 'Singapore': 'SG',
    '马来西亚': 'MY', 'Malaysia': 'MY',
    '泰国': 'TH', 'Thailand': 'TH',
    '越南': 'VN', 'Vietnam': 'VN',
    '印度尼西亚': 'ID', 'Indonesia': 'ID',
    '菲律宾': 'PH', 'Philippines': 'PH',
    '荷兰': 'NL', 'Netherlands': 'NL',
    '意大利': 'IT', 'Italy': 'IT',
    '西班牙': 'ES', 'Spain': 'ES',
    '瑞典': 'SE', 'Sweden': 'SE',
    '瑞士': 'CH', 'Switzerland': 'CH',
    '香港': 'HK', 'Hong Kong': 'HK',
    '台湾': 'TW', 'Taiwan': 'TW',
    '澳门': 'MO', 'Macau': 'MO',
    '阿联酋': 'AE', 'United Arab Emirates': 'AE',
    '沙特阿拉伯': 'SA', 'Saudi Arabia': 'SA',
}

def _country_name_to_code(name: str) -> str:
    """中文国家名 → ISO 代码"""
    return _COUNTRY_MAP.get(name, name) if name else ''

def _find_db() -> str:
    """查找本地 GeoLite2 数据库"""
    for p in GEOIP_DB_CANDIDATES:
        if os.path.exists(p):
            return p
    return ''


def init_geoip():
    """初始化 GeoIP（ip2region + MaxMind）"""
    global _geoip_reader, _ip2region_searcher

    # 初始化 ip2region（优先级最高）
    _init_ip2region()

    # 初始化 MaxMind
    db_path = _find_db()
    if not db_path:
        if not _ip2region_searcher:
            print(f'[Analytics] ℹ️ GeoIP 数据库均未找到，使用 ip-api 在线回退')
        else:
            print(f'[Analytics] ℹ️ GeoLite2 数据库未找到，ip2region + ip-api 可用')
        return _ip2region_searcher is not None
    try:
        import geoip2.database
        _geoip_reader = geoip2.database.Reader(db_path)
        print(f'[Analytics] ✅ GeoIP 已加载: {db_path}')
        return True
    except Exception as e:
        print(f'[Analytics] ⚠️ GeoIP 加载失败: {e}')
        return _ip2region_searcher is not None


def geoip_lookup(ip: str) -> dict:
    """
    IP 地理查询（ip2region → MaxMind → ip-api）
    返回: {'country': 'CN', 'city': '南京'}
    失败返回空 dict
    """
    global _geoip_reader, _ip2region_searcher
    if not ip or ip == '127.0.0.1' or ip == '0.0.0.x' or ip.startswith('192.168.'):
        return {'country': '', 'city': ''}

    # 1. ip2region（中国 IP 优先）
    result = _ip2region_lookup(ip)
    if result.get('city'):
        return result
    if result.get('country') and not _geoip_reader:
        return result

    # 2. 本地 MaxMind
    if _geoip_reader:
        try:
            response = _geoip_reader.city(ip)
            mm_city = response.city.name or ''
            mm_country = response.country.iso_code or ''
            # 如果 ip2region 给了 country 但没 city，MaxMind 补 city
            # ⚠️ 必须验证 country 一致性：ip2region 的 CN + MaxMind 的 Frankfurt = 错误
            if result.get('country') and not result.get('city') and mm_city:
                # 若 MaxMind country 与 ip2region 一致，用 ip2region country
                if mm_country and mm_country == result.get('country'):
                    return {'country': result.get('country'), 'city': mm_city}
                # 若不一致（如 CN + Frankfurt），以 MaxMind 为准
                if mm_country:
                    return {'country': mm_country, 'city': mm_city}
                # MaxMind 无 country 时才回退 ip2region country（罕见）
                return {'country': result.get('country'), 'city': mm_city}
            if mm_country:
                return {'country': mm_country, 'city': mm_city}
        except:
            pass

    # ip2region 至少给了 country（即使没 city）
    if result.get('country'):
        return result

    # 3. 回退到 ip-api
    return _ipapi_lookup(ip)


def _ipapi_lookup(ip: str) -> dict:
    """通过 ip-api.com 在线查询（带缓存）"""
    now = time.time()
    
    # 清理过期缓存
    global IPAPI_CACHE
    expired = [k for k, v in IPAPI_CACHE.items() if now - v['ts'] > IPAPI_CACHE_TTL]
    for k in expired:
        del IPAPI_CACHE[k]

    # 缓存命中
    if ip in IPAPI_CACHE:
        return IPAPI_CACHE[ip]['data']

    try:
        url = f'http://ip-api.com/json/{ip}?fields=countryCode,city'
        resp = urlopen(url, timeout=3)
        data = json.loads(resp.read().decode())
        if data.get('status') == 'success':
            result = {
                'country': data.get('countryCode', ''),
                'city': data.get('city', ''),
            }
            IPAPI_CACHE[ip] = {'ts': now, 'data': result}
            return result
    except Exception as e:
        pass

    return {'country': '', 'city': ''}


# ─── 维护工具 ──────────────────────────────────────────────────────────────────

def download_geolite2(output_path: str = None):
    """
    下载最新 GeoLite2 City 数据库
    需要 MaxMind 许可证密钥（免费注册: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data）
    用法: python3 -c "from analytics.geoip import download_geolite2; download_geolite2()"
    """
    import sys
    print("=" * 60)
    print(" GeoLite2 City 数据库下载")
    print("=" * 60)
    print()
    print("1. 注册 MaxMind 账号: https://www.maxmind.com/en/geolite2/signup")
    print("2. 创建许可证密钥: https://www.maxmind.com/en/accounts/current/license")
    print("3. 下载后放入以下任一路径:")
    for p in GEOIP_DB_CANDIDATES:
        print(f"   • {p}")
    print()
    print("或运行:")
    print("  wget 'https://download.maxmind.com/app/geoip_download?" +
          "edition_id=GeoLite2-City&license_key=YOUR_KEY&suffix=tar.gz'")
    print("  tar -xzf GeoLite2-City_*.tar.gz")
    print("  mv GeoLite2-City_*/GeoLite2-City.mmdb /path/to/")
    print()
