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

from i18n import _
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
    '/usr/share/GeoIP/GeoLite2-City.mmdb',
    './data/GeoLite2-City.mmdb',
    '../data/GeoLite2-City.mmdb',
]

# ip-api 缓存（避免限流）
IPAPI_CACHE = {}
IPAPI_CACHE_TTL = 3600  # 1 小时缓存

_geoip_reader = None
_ip2region_searcher = None

# 自动检测：启动时查服务器公网 IP，判断是否境外
# 不再依赖 DEPLOY_MARKET 环境变量
_IS_INTL = None  # None = 尚未检测，False = 境内，True = 境外


def _detect_server_location() -> bool:
    """
    通过 ip-api.com 查询服务器自己的公网 IP，判断是否在境外。
    首次调用后缓存结果。
    """
    global _IS_INTL
    if _IS_INTL is not None:
        return _IS_INTL
    try:
        import json
        from urllib.request import urlopen
        resp = urlopen('http://ip-api.com/json/?fields=countryCode', timeout=5)
        data = json.loads(resp.read().decode())
        cc = (data.get('countryCode') or '').upper()
        _IS_INTL = (cc != 'CN')
    except Exception:
        # 检测失败时回退到 DEPLOY_MARKET
        _IS_INTL = os.environ.get('DEPLOY_MARKET', 'cn').lower() not in ('cn', 'china', '')
    return _IS_INTL


def is_server_international() -> bool:
    """对外公开：判断服务器是否在境外"""
    return _detect_server_location()


def get_market() -> str:
    """对外公开：返回 'intl' 或 'cn'"""
    return 'intl' if _detect_server_location() else 'cn'


# ─── ip2region ───────────────────────────────────────────────────────────────────

def _init_ip2region() -> bool:
    """初始化 ip2region（优先于 MaxMind）"""
    global _ip2region_searcher
    if not os.path.exists(IP2REGION_DB):
        print(f'[Analytics] ℹ️ ip2region database not found: {IP2REGION_DB}')
        return False
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ip2region import util
        from ip2region.searcher import new_with_buffer
        with open(IP2REGION_DB, 'rb') as f:
            _ip2region_searcher = new_with_buffer(util.IPv4, f.read())
        print(f'[Analytics] ✅ ip2region loaded: {IP2REGION_DB}')
        return True
    except Exception as e:
        print(f'[Analytics] ⚠️ ip2region loading failed: {e}')
        return False


def _ip2region_lookup(ip: str) -> dict:
    """
    ip2region 查询，解析 _("Country|Region|Province|City|ISP") 格式
    返回: {'country': _('China'), 'city': _('Nanjing')}
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
    _('China'): 'CN', 'China': 'CN',
    _('United States'): 'US', 'United States': 'US',
    _('Japan'): 'JP', 'Japan': 'JP',
    _('South Korea'): 'KR', 'South Korea': 'KR', 'Korea': 'KR',
    _('United Kingdom'): 'GB', 'United Kingdom': 'GB',
    _('Germany'): 'DE', 'Germany': 'DE',
    _('France'): 'FR', 'France': 'FR',
    _('Russia'): 'RU', 'Russia': 'RU',
    _('India'): 'IN', 'India': 'IN',
    _('Brazil'): 'BR', 'Brazil': 'BR',
    _('Canada'): 'CA', 'Canada': 'CA',
    _('Australia'): 'AU', 'Australia': 'AU',
    _('Singapore'): 'SG', 'Singapore': 'SG',
    _('Malaysia'): 'MY', 'Malaysia': 'MY',
    _('Thailand'): 'TH', 'Thailand': 'TH',
    _('Vietnam'): 'VN', 'Vietnam': 'VN',
    _('Indonesia'): 'ID', 'Indonesia': 'ID',
    _('Philippines'): 'PH', 'Philippines': 'PH',
    _('Netherlands'): 'NL', 'Netherlands': 'NL',
    _('Italy'): 'IT', 'Italy': 'IT',
    _('Spain'): 'ES', 'Spain': 'ES',
    _('Sweden'): 'SE', 'Sweden': 'SE',
    _('Switzerland'): 'CH', 'Switzerland': 'CH',
    _('Hong Kong'): 'HK', 'Hong Kong': 'HK',
    _('Taiwan'): 'TW', 'Taiwan': 'TW',
    _('Macau'): 'MO', 'Macau': 'MO',
    _('United Arab Emirates'): 'AE', 'United Arab Emirates': 'AE',
    _('Saudi Arabia'): 'SA', 'Saudi Arabia': 'SA',
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
            print(f'[Analytics] ℹ️ GeoIP databases not found, using ip-api as fallback')
        else:
            print(f'[Analytics] ℹ️ GeoLite2 database not found, ip2region + ip-api available')
        return _ip2region_searcher is not None
    try:
        import geoip2.database
        _geoip_reader = geoip2.database.Reader(db_path)
        print(f'[Analytics] ✅ GeoIP loaded: {db_path}')
        return True
    except Exception as e:
        print(f'[Analytics] ⚠️ GeoIP loading failed: {e}')
        return _ip2region_searcher is not None


def geoip_lookup(ip: str) -> dict:
    """
    IP 地理查询（ip2region → MaxMind → ip-api）
    返回: {'country': 'CN', 'city': _('Nanjing')}
    失败返回空 dict
    """
    global _geoip_reader, _ip2region_searcher
    if not ip or ip == '127.0.0.1' or ip == '0.0.0.x' or ip.startswith('192.168.'):
        return {'country': '', 'city': ''}

    # 1. 国际部署优先使用 MaxMind，国内部署优先 ip2region
    if _detect_server_location():
        # 国际：MaxMind（国际 IP 精准）→ ip2region → ip-api
        if _geoip_reader:
            try:
                response = _geoip_reader.city(ip)
                mm_city = response.city.name or ''
                mm_country = response.country.iso_code or ''
                if mm_country:
                    return {'country': mm_country, 'city': mm_city}
            except:
                pass
        result = _ip2region_lookup(ip)
        if result.get('country'):
            return result
    else:
        # 国内：ip2region（中国 IP 精准）→ MaxMind → ip-api
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
    print(_("3. After Downloading, Place in Any of the Following Paths:"))
    for p in GEOIP_DB_CANDIDATES:
        print(f"   • {p}")
    print()
    print(_("Or run:"))
    print("  wget 'https://download.maxmind.com/app/geoip_download?" +
          "edition_id=GeoLite2-City&license_key=YOUR_KEY&suffix=tar.gz'")
    print("  tar -xzf GeoLite2-City_*.tar.gz")
    print("  mv GeoLite2-City_*/GeoLite2-City.mmdb /path/to/")
    print()
