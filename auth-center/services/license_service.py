#!/usr/bin/env python3
"""
VeroRon 维洛智能 — 本地授权验证服务（运行在客户部署的实例上）
验证订阅状态，管理本地缓存

使用方式：
    from services.license_service import LicenseService
    svc = LicenseService()
    status = svc.get_status()  # 返回 {valid, days_remaining, status}
    svc.refresh()              # 主动刷新（调用心跳API）
"""
import os, json, time, sqlite3, requests
from datetime import datetime, timedelta


class LicenseService:
    """本地授权验证服务"""

    HEARTBEAT_INTERVAL = 86400  # 24小时
    HEARTBEAT_URL_ENV = 'EASYKAI_HEARTBEAT_URL'
    DEFAULT_HEARTBEAT_URL = 'https://localhost/api/subscription/heartbeat'

    def __init__(self, db_path=None):
        self.db_path = db_path or os.environ.get(
            'DB_PATH',
            os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'x7k2m9a4.db')
        )
        self._ensure_config_table()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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
        row = conn.execute('SELECT value FROM system_config WHERE key=?', (key,)).fetchone()
        conn.close()
        if row:
            return row['value']
        return default

    def _set_config(self, key, value):
        conn = self._get_conn()
        conn.execute('INSERT OR REPLACE INTO system_config (key, value) VALUES (?,?)', (key, str(value)))
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
                'message': '未配置部署码，请联系管理员',
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

        heartbeat_url = os.environ.get(self.HEARTBEAT_URL_ENV, self.DEFAULT_HEARTBEAT_URL)

        try:
            resp = requests.post(
                heartbeat_url,
                json={'code': deployment_code, 'hostname': os.uname().nodename, 'version': '1.0.0'},
                timeout=10
            )
            data = resp.json().get('data', {}) if resp.ok else {}
            valid = data.get('valid', False)
        except Exception:
            # 网络不通时，保留上次缓存状态
            status = self.get_status()
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
        status = self.get_status()
        if status['status'] == 'unknown':
            # 首次使用，从未验证过 — 允许访问
            return True
        return status['valid']

    def check_ai_access(self):
        """
        检查 AI 功能是否可用
        返回 True = 可用，False = 已过期不可用
        """
        status = self.get_status()
        if status['status'] == 'unknown':
            return True
        return status['valid']
