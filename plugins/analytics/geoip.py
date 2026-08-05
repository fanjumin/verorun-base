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
import base64
from urllib.request import urlopen, Request, HTTPError
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
    判断服务器是否在境外。
    优先级: DEPLOY_MARKET 环境变量 > ip-api.com 自动检测（仅启动时一次）
    首次调用后缓存结果。
    """
    global _IS_INTL
    if _IS_INTL is not None:
        return _IS_INTL

    # 1. 优先读取环境变量（部署时常量，零延迟，可靠）
    market_env = os.environ.get('DEPLOY_MARKET', '').lower()
    if market_env in ('intl', 'international', 'global'):
        _IS_INTL = True
        print(f'[Analytics] Market set via DEPLOY_MARKET={market_env} → intl')
        return _IS_INTL
    if market_env in ('cn', 'china'):
        _IS_INTL = False
        print(f'[Analytics] Market set via DEPLOY_MARKET={market_env} → cn')
        return _IS_INTL

    # 2. 回退到 ip-api 自动检测（仅启动时一次）
    try:
        import json
        from urllib.request import urlopen
        resp = urlopen('https://ip-api.com/json/?fields=countryCode', timeout=5)
        data = json.loads(resp.read().decode())
        cc = (data.get('countryCode') or '').upper()
        _IS_INTL = (cc != 'CN')
        print(f'[Analytics] Market auto-detected via ip-api: {"intl" if _IS_INTL else "cn"}')
    except Exception:
        _IS_INTL = False  # 默认国内
        print('[Analytics] Market detection failed, defaulting to cn')
    return _IS_INTL


def is_server_international() -> bool:
    """对外公开：判断服务器是否在境外"""
    return _detect_server_location()


def get_market() -> str:
    """对外公开：返回 'intl' 或 'cn'"""
    return 'intl' if _detect_server_location() else 'cn'


def detect_client_market(ip: str) -> str:
    """
    根据客户端 IP 判断市场：'cn' 或 'intl'
    用于前端根据访客 IP 动态切换中国/国际视图。
    """
    if not ip or ip.startswith('127.') or ip.startswith('192.168.') or ip.startswith('10.'):
        return get_market()  # 内网 IP 回退到服务器市场

    # 优先用 ip2region（本地，零延迟）
    result = _ip2region_lookup(ip)
    if result.get('country'):
        return 'cn' if result['country'] == 'CN' else 'intl'

    # 回退到 ip-api
    try:
        api_result = _ipapi_lookup(ip)
        if api_result.get('country'):
            return 'cn' if api_result['country'] == 'CN' else 'intl'
    except Exception:
        pass

    return get_market()  # 最终回退到服务器市场


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
        # 只有合法的 ISO 3166-1 alpha-2 国家码才视为有效
        if cc and len(cc) == 2 and cc.isalpha() and cc.isupper():
            return {'country': cc, 'city': city}
        return {}
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
        url = f'https://ip-api.com/json/{ip}?fields=countryCode,city'
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

def download_geolite2_auto(license_key: str, account_id: str = '', edition: str = 'GeoLite2-City') -> dict:
    """
    自动从 MaxMind 下载数据库到 analytics/data/ 目录。
    2024+ 新版 API 要求 Basic Auth（account_id:license_key）。

    参数:
      license_key — MaxMind License Key
      account_id  — MaxMind Account ID（新版必须）
      edition     — 'GeoLite2-City'（免费，默认）或 'GeoIP2-City'（付费）

    返回: {'success': True, 'path': '...', 'size_mb': 12.3}
         或 {'success': False, 'error': '...'}
    """
    import tarfile
    import tempfile
    import shutil

    target_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(target_dir, exist_ok=True)
    mmdb_name = edition + '.mmdb'
    target_path = os.path.join(target_dir, mmdb_name)

    # 新版 URL（2024+）
    url = (
        'https://download.maxmind.com/geoip/databases'
        f'/{edition}/download?suffix=tar.gz'
    )

    try:
        req = Request(url)

        # Basic Auth: account_id:license_key
        if account_id:
            credentials = base64.b64encode(f'{account_id}:{license_key}'.encode()).decode()
            req.add_header('Authorization', f'Basic {credentials}')
        elif license_key:
            # 兼容旧版：仅有 license_key 时用 query param（部分版本仍支持）
            url_with_key = url + f'&license_key={license_key}'
            req = Request(url_with_key)

        resp = urlopen(req, timeout=120)

        # 写入临时文件
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
            tmp.write(resp.read())
            tmp_path = tmp.name

        try:
            with tarfile.open(tmp_path, 'r:gz') as tar:
                mmdb_member = None
                for member in tar.getmembers():
                    if member.name.endswith('.mmdb'):
                        mmdb_member = member
                        break
                if not mmdb_member:
                    return {
                        'success': False,
                        'error': f'{edition}.mmdb not found in downloaded archive',
                    }

                extracted = tar.extractfile(mmdb_member)
                if extracted:
                    with open(target_path, 'wb') as f:
                        shutil.copyfileobj(extracted, f)
        finally:
            os.unlink(tmp_path)

        size_mb = round(os.path.getsize(target_path) / (1024 * 1024), 1)

        # 重置 reader，下次 geoip_lookup 自动重新加载
        global _geoip_reader
        _geoip_reader = None

        # 确保路径在探测列表中
        if target_path not in GEOIP_DB_CANDIDATES:
            GEOIP_DB_CANDIDATES.insert(0, target_path)

        print(f'[Analytics] ✅ {mmdb_name} downloaded ({size_mb} MB) → {target_path}')
        return {'success': True, 'path': target_path, 'size_mb': size_mb}

    except HTTPError as e:
        if e.code == 451:
            return {
                'success': False,
                'error': (
                    f'HTTP 451: MaxMind requires signing the Data Processing Agreement (DPA). '
                    f'Please log in to maxmind.com → Account → Data Processing Agreements → sign the DPA. '
                    f'Alternatively, download {mmdb_name} manually from your MaxMind account and upload it below.'
                ),
            }
        if e.code == 401:
            return {
                'success': False,
                'error': (
                    f'HTTP 401: Authentication failed. '
                    f'Verify your Account ID and License Key. '
                    f'Note: MaxMind now requires both Account ID and License Key with Basic Auth.'
                ),
            }
        return {'success': False, 'error': f'HTTP {e.code}: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def install_geolite2_file(source_path: str) -> dict:
    """
    手动安装 .mmdb 文件到 analytics/data/ 目录。
    用户在 MaxMind 官网下载后通过后台手动上传。

    返回: {'success': True, 'path': '...', 'size_mb': 12.3}
         或 {'success': False, 'error': '...'}
    """
    import shutil

    if not os.path.exists(source_path):
        return {'success': False, 'error': f'File not found: {source_path}'}

    if not source_path.endswith('.mmdb'):
        return {'success': False, 'error': 'Only .mmdb files are supported'}

    target_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(target_dir, exist_ok=True)
    basename = os.path.basename(source_path)
    target_path = os.path.join(target_dir, basename)

    try:
        shutil.copy2(source_path, target_path)
        size_mb = round(os.path.getsize(target_path) / (1024 * 1024), 1)

        # 重置 reader
        global _geoip_reader
        _geoip_reader = None

        # 确保路径在探测列表中
        if target_path not in GEOIP_DB_CANDIDATES:
            GEOIP_DB_CANDIDATES.insert(0, target_path)

        print(f'[Analytics] ✅ {basename} installed ({size_mb} MB) → {target_path}')
        return {'success': True, 'path': target_path, 'size_mb': size_mb}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_geoip_status() -> dict:
    """返回 GeoIP 数据库安装状态（ip2region + MaxMind）"""
    result = {}

    # ip2region
    if os.path.exists(IP2REGION_DB):
        stat = os.stat(IP2REGION_DB)
        result['ip2region'] = {
            'installed': True,
            'path': IP2REGION_DB,
            'size_mb': round(stat.st_size / (1024 * 1024), 1),
            'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime)),
        }
    else:
        result['ip2region'] = {'installed': False, 'path': None}

    # MaxMind GeoLite2
    mmdb_path = _find_db()
    if mmdb_path:
        stat = os.stat(mmdb_path)
        result['geolite2'] = {
            'installed': True,
            'path': mmdb_path,
            'size_mb': round(stat.st_size / (1024 * 1024), 1),
            'mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime)),
        }
    else:
        result['geolite2'] = {'installed': False, 'path': None}

    return result


def download_ip2region_auto() -> dict:
    """
    从 GitHub 下载 ip2region_v4.xdb 到 analytics/data/ 目录。
    开源免费，无需注册。

    返回: {'success': True, 'path': '...', 'size_mb': 11.2}
         或 {'success': False, 'error': '...'}
    """
    import shutil

    target_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, 'ip2region_v4.xdb')

    # GitHub / Gitee 镜像（国内优先 Gitee，境外优先 GitHub）
    urls = [
        'https://raw.githubusercontent.com/lionsoul2014/ip2region/master/data/ip2region.xdb',
        'https://gitee.com/mirrors/ip2region/raw/master/data/ip2region.xdb',
        'https://ghproxy.com/https://raw.githubusercontent.com/lionsoul2014/ip2region/master/data/ip2region.xdb',
    ]

    last_error = ''
    for url in urls:
        try:
            resp = urlopen(url, timeout=120)
            if resp.status == 200:
                with open(target_path, 'wb') as f:
                    shutil.copyfileobj(resp, f)

                size_mb = round(os.path.getsize(target_path) / (1024 * 1024), 1)

                # 重置 searcher，下次 geoip_lookup 自动重新加载
                global _ip2region_searcher
                _ip2region_searcher = None

                print(f'[Analytics] ✅ ip2region.xdb downloaded ({size_mb} MB) → {target_path}')
                return {'success': True, 'path': target_path, 'size_mb': size_mb}
            else:
                last_error = f'HTTP {resp.status} from {url}'
        except Exception as e:
            last_error = f'{url}: {e}'

    return {'success': False, 'error': f'All mirrors failed: {last_error}'}
