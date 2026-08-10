#!/usr/bin/env python3
"""
VeroRun 维洛智能 — 本地授权验证服务（运行在客户部署的实例上）
验证订阅状态，管理本地缓存

使用方式：
    from services.license_service import LicenseService
    svc = LicenseService()
    status = svc.get_status()  # 返回 {valid, days_remaining, status}
    svc.refresh()              # 主动刷新（调用心跳API）
"""
import os, json, time, requests, platform
from datetime import datetime, timedelta
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
from i18n import _

# PostgreSQL 连接配置（复用环境变量）
_PG_CONFIG = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': int(os.environ.get('PG_PORT', 5432)),
    'dbname': os.environ.get('PG_DB', 'appdb'),
    'user': os.environ.get('PG_USER', 'app'),
    'password': os.environ.get('PG_PASSWORD', ''),
}


class _DbWrapper:
    """psycopg2 connection wrapper that exposes sqlite3-style execute/commit."""
    def __init__(self, conn):
        self._conn = conn
        self._cur = conn.cursor(cursor_factory=RealDictCursor)
    def execute(self, sql, params=None):
        if params is not None:
            self._cur.execute(sql, params)
        else:
            self._cur.execute(sql)
        return self
    def executemany(self, sql, params):
        return self._cur.executemany(sql, params)
    def fetchone(self):
        return self._cur.fetchone()
    def fetchall(self):
        return self._cur.fetchall()
    def commit(self):
        self._conn.commit()
    def rollback(self):
        self._conn.rollback()
    def cursor(self):
        return self._conn.cursor()
    def close(self):
        self._cur.close()
    def executescript(self, sql):
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        old_level = self._conn.isolation_level
        self._conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = self._conn.cursor()
        cur.execute(sql)
        cur.close()
        self._conn.set_isolation_level(old_level)
    def __getattr__(self, name):
        return getattr(self._cur, name)


class LicenseService:
    """本地授权验证服务"""

    HEARTBEAT_INTERVAL = 86400  # 24小时
    HEARTBEAT_URL_ENV = 'APP_HEARTBEAT_URL'

    @staticmethod
    def _get_heartbeat_url() -> str:
        """获取心跳 URL（区域感知）。
        环境变量 APP_HEARTBEAT_URL 覆盖优先（向后兼容）。
        容错：独立部署时 plugin_manager 可能不在路径中。
        """
        override = os.environ.get('APP_HEARTBEAT_URL', '')
        if override:
            return override
        try:
            import sys
            _verorun_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if _verorun_root not in sys.path:
                sys.path.insert(0, _verorun_root)
            from plugin_manager.region import get_license_service_url
            return get_license_service_url()
        except ImportError:
            region = os.environ.get('APP_REGION', 'global')
            if region == 'cn':
                return 'https://api.verorun.cn/api/subscription/heartbeat'
            return 'https://api.verorun.com/api/subscription/heartbeat'

    DEFAULT_HEARTBEAT_URL = 'https://localhost/api/subscription/heartbeat'

    def __init__(self, db_path=None):
        self._pg_config = dict(_PG_CONFIG)
        if db_path:
            self._pg_config['dbname'] = db_path
        self._cache = {'result': None, 'timestamp': 0}
        self._ensure_config_table()

    def _get_conn(self):
        conn = psycopg2.connect(**self._pg_config, cursor_factory=psycopg2.extras.RealDictCursor)
        return _DbWrapper(conn)

    def _ensure_config_table(self):
        """确保 system_config 表存在（存储本地授权缓存）"""
        conn = self._get_conn()
        conn.execute('''CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        conn.commit()
        conn.close()

    def _get_config(self, key, default=None):
        conn = self._get_conn()
        row = conn.execute('SELECT value FROM system_config WHERE key=%s', (key,)).fetchone()
        conn.close()
        if row:
            return row['value']
        return default

    def _set_config(self, key, value):
        conn = self._get_conn()
        conn.execute(
            'INSERT INTO system_config (key, value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value',
            (key, str(value)))
        conn.commit()
        conn.close()

    def get_status(self):
        """
        获取本地缓存的授权状态

        返回:
            {
                'valid': bool,          # 是否有效
                'days_remaining': int,   # 剩余天数
                'status': str,           # active/expired/unknown
                'cached_at': str,        # 上次缓存时间
                'message': str,          # 提示信息
                'needs_refresh': bool,   # 是否需要重新验证
            }
        """
        cached = self._get_config('license_status', '{}')
        deployment_code = self._get_config('deployment_code', '')

        try:
            status = json.loads(cached)
        except (json.JSONDecodeError, TypeError):
            status = {}

        now = time.time()
        cached_at = status.get('cached_at', 0)
        needs_refresh = (now - cached_at) > self.HEARTBEAT_INTERVAL

        if not deployment_code:
            return {
                'valid': False,
                'days_remaining': 0,
                'status': 'unknown',
                'cached_at': datetime.fromtimestamp(cached_at).isoformat() if cached_at else '',
                'message': _('未配置部署码，请联系管理员'),
                'needs_refresh': False,
            }

        return {
            'valid': status.get('valid', False),
            'days_remaining': status.get('days_remaining', 0),
            'status': status.get('status', 'unknown'),
            'cached_at': datetime.fromtimestamp(cached_at).isoformat() if cached_at else '',
            'message': status.get('message', ''),
            'needs_refresh': needs_refresh,
        }

    def refresh(self, deployment_code=None):
        """
        主动刷新授权状态（调用主服务器心跳API）

        参数:
            deployment_code: str — 部署码（可选，默认从本地配置读取）

        返回:
            同 get_status()
        """
        if not deployment_code:
            deployment_code = self._get_config('deployment_code', '')

        if not deployment_code:
            return self.get_status()

        heartbeat_url = self._get_heartbeat_url()

        try:
            resp = requests.post(
                heartbeat_url,
                json={'code': deployment_code, 'hostname': platform.node(), 'version': '1.0.0'},
                timeout=10
            )
            data = resp.json().get('data', {}) if resp.ok else {}
            valid = data.get('valid', False)
        except Exception:
            # 网络不通时，保留上次有效缓存，不因网络抖动锁定用户
            status = self.get_status()
            if status.get('valid'):
                # 延长有效缓存时间，避免因短暂网络问题导致 needs_refresh 超时
                status['needs_refresh'] = False
            return status

        cache_entry = {
            'valid': valid,
            'days_remaining': data.get('days_remaining', 0),
            'status': 'active' if valid else 'expired',
            'message': data.get('message', ''),
            'cached_at': time.time(),
        }

        self._set_config('license_status', json.dumps(cache_entry))

        return self.get_status()

    def check_admin_access(self):
        """
        检查管理后台是否可访问
        返回 True = 允许访问，False = 需要跳转续费页
        """
        # 60秒内存缓存，避免每次请求开数据库连接
        now = time.time()
        if now - self._cache['timestamp'] < 60:
            return self._cache['result']

        status = self.get_status()
        result = True if status['status'] == 'unknown' else status['valid']
        self._cache = {'result': result, 'timestamp': now}
        return result

    def check_ai_access(self):
        """
        检查 AI 功能是否可用
        返回 True = 可用，False = 已过期不可用
        """
        status = self.get_status()
        if status['status'] == 'unknown':
            return True
        return status['valid']
