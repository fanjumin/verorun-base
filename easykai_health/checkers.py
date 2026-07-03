#!/usr/bin/env python3
"""
Health Monitor — 健康检查器
=============================
所有检查器继承 BaseHealthCheck 基类，通过 @register 装饰器自动注册。

添加新检查项只需三步：
  1. 在 checkers.py (或新建 checker_xxx.py) 中继承 BaseHealthCheck
  2. 用 @register 装饰器注册
  3. 在 health_checks 表添加一条记录（ORM / API 均可）

参见 DEVELOPER.md 获取详细教程。
"""

import os, sys, json, time, socket, ssl, subprocess
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, Tuple
from services.deployment_config import deploy
from i18n import _

import urllib.request
import urllib.error

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))


# ═══════════════════════════════════════════════════════════════════════════
# 注册表 (Registry)
# ═══════════════════════════════════════════════════════════════════════════

class CheckerRegistry:
    """
    全局检查器注册表。
    通过 @register(check_key) 装饰器注册，或在代码中直接调用 register()。
    """

    _checkers: Dict[str, Type['BaseHealthCheck']] = {}

    @classmethod
    def register(cls, check_key: str, checker_cls: Type['BaseHealthCheck'] = None):
        """
        注册检查器 — 可用作装饰器或直接调用。
        用法:
            @register('my_check')
            class MyCheck(BaseHealthCheck): ...
        """
        if checker_cls is not None:
            cls._checkers[check_key] = checker_cls
            return checker_cls

        def decorator(klass):
            cls._checkers[check_key] = klass
            # 如果类没有明确定义 check_key，则写入类属性
            if not hasattr(klass, 'check_key') or not klass.check_key:
                klass.check_key = check_key
            return klass
        return decorator

    @classmethod
    def get(cls, check_key: str) -> Optional[Type['BaseHealthCheck']]:
        """按 key 获取检查器类"""
        return cls._checkers.get(check_key)

    @classmethod
    def get_instance(cls, check_key: str, config: dict = None) -> Optional['BaseHealthCheck']:
        """获取检查器实例"""
        klass = cls.get(check_key)
        if not klass:
            return None
        return klass(config or {})

    @classmethod
    def list_registered(cls) -> List[Dict]:
        """列出所有已注册检查器的元数据（用于管理界面）"""
        result = []
        for key, klass in sorted(cls._checkers.items()):
            # 实例化获取元数据（可能依赖 config，用空 dict 即可）
            try:
                inst = klass({})
                meta = {
                    'check_key': key,
                    'name': inst.get_name(),
                    'category': inst.get_category(),
                    'severity': inst.get_severity(),
                    'description': inst.get_description(),
                    'default_sort_order': inst.get_sort_order(),
                    'config_schema': inst.get_config_schema(),
                    'config_defaults': inst.get_config_defaults(),
                }
            except Exception as e:
                meta = {
                    'check_key': key,
                    'name': getattr(klass, 'check_key', key),
                    'error': str(e),
                }
            result.append(meta)
        return result

    @classmethod
    def unregister(cls, check_key: str):
        """注销检查器"""
        cls._checkers.pop(check_key, None)

    @classmethod
    def size(cls) -> int:
        return len(cls._checkers)


# 便捷别名
register = CheckerRegistry.register


# ═══════════════════════════════════════════════════════════════════════════
# 检查结果类
# ═══════════════════════════════════════════════════════════════════════════

class CheckResult:
    """单个检查项的结果"""
    def __init__(self, status: str = 'passed', response_time_ms: int = 0,
                 message: str = '', detail: dict = None):
        assert status in ('passed', 'warning', 'error'), f"Invalid status: {status}"
        self.status = status
        self.response_time_ms = response_time_ms
        self.message = message
        self.detail = detail or {}

    def to_dict(self) -> dict:
        return {
            'status': self.status,
            'response_time_ms': self.response_time_ms,
            'message': self.message,
            'detail': json.dumps(self.detail, ensure_ascii=False),
        }

    def to_emoji(self) -> str:
        return '✅' if self.status == 'passed' else ('⚠️' if self.status == 'warning' else '❌')


# ═══════════════════════════════════════════════════════════════════════════
# 抽象基类 (Abstract Base HealthCheck)
# ═══════════════════════════════════════════════════════════════════════════

class BaseHealthCheck(ABC):
    """
    健康检查器抽象基类。
    所有自定义检查器必须继承此类并实现 check() 方法。

    类属性（可覆盖）:
        check_key: str              — 唯一键 (默认从注册表获取)
        name: str                   — 显示名称
        category: str               — 分类 (system/external/workflow/agent/cms/community/ssl/error)
        severity: str               — 告警级别 (info/warning/critical)
        description: str            — 描述
        sort_order: int             — 排序权重
        config_schema: dict         — JSON Schema 描述配置项
        config_defaults: dict       — 默认配置

    子类必须实现:
        check(self) -> CheckResult  — 执行检查
    """

    # ── 元数据（子类覆盖这些值） ──
    check_key: str = ''
    name: str = '未命名检查项'
    category: str = 'system'
    severity: str = 'warning'
    description: str = ''
    sort_order: int = 50
    config_schema: dict = {}
    config_defaults: dict = {}

    def __init__(self, config: dict):
        """初始化检查器，config 从 health_checks.config JSON 读取"""
        self.config = {**self.config_defaults, **config}

    # ── 元数据访问方法（可被子类覆盖） ──

    def get_name(self) -> str:
        return _(self.name)

    def get_category(self) -> str:
        return self.category

    def get_severity(self) -> str:
        return self.severity

    def get_description(self) -> str:
        return _(self.description)

    def get_sort_order(self) -> int:
        return self.sort_order

    def get_config_schema(self) -> dict:
        """返回配置项的 JSON Schema，用于管理页面的配置编辑器"""
        return self.config_schema

    def get_config_defaults(self) -> dict:
        return self.config_defaults

    # ── 检查入口 ──

    @abstractmethod
    def check(self) -> CheckResult:
        """
        执行检查的唯一入口。
        子类必须实现此方法，返回 CheckResult。
        """
        pass

    # ── 兼容旧版 (routes.py 中调用 run()) ──
    def run(self) -> CheckResult:
        """旧版兼容：默认委托给 check()"""
        return self.check()

    # ── 工具方法 ──

    def _http_get(self, url: str, timeout: int = 5) -> Tuple[int, int, str]:
        """HTTP GET 请求，返回 (status_code, elapsed_ms, body)"""
        start = time.time()
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed = int((time.time() - start) * 1000)
                body = resp.read().decode('utf-8', errors='replace')[:500]
                return resp.status, elapsed, body
        except urllib.error.HTTPError as e:
            elapsed = int((time.time() - start) * 1000)
            return e.code, elapsed, str(e)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return 0, elapsed, str(e)

    def _exec(self, cmd: str, timeout: int = 10) -> Tuple[int, str, str]:
        """执行 shell 命令，返回 (returncode, stdout, stderr)"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, '', 'timeout'
        except Exception as e:
            return -1, '', str(e)


# ═══════════════════════════════════════════════════════════════════════════
# 具体检查器实现
# ═══════════════════════════════════════════════════════════════════════════
#
# 以下每个检查器类都继承 BaseHealthCheck，用 @register 注册。
# 它们是现成的参考示例，也是系统自带的默认检查项。
#
# 如需添加新检查项，滚动到文件底部查看「添加新检查项的模板」。
# ═══════════════════════════════════════════════════════════════════════════

# ─── 1. 核心 API 检查 ─────────────────────────────────────────────────────

@register('core_api')
class CoreAPIHealthCheck(BaseHealthCheck):
    check_key = 'core_api'
    name = '核心API检查'
    category = 'system'
    severity = 'warning'
    description = '所有子站（主站 Site / Platform / Admin）的健康端点检查'
    sort_order = 10
    config_defaults = {'timeout': 5, 'endpoints': ['/health']}
    config_schema = {
        'type': 'object',
        'properties': {
            'timeout': {'type': 'integer', 'default': 5, 'description': '超时时间(秒)'},
        }
    }

    def check(self) -> CheckResult:
        endpoints = self.config.get('endpoints', ['/health'])
        subdomains = {
            _('Main Site'): ('http://127.0.0.1:8081', 8081),
            deploy.server_name('platform'): ('http://127.0.0.1:8083', 8083),
            f'{deploy.server_name("agent")} (admin)': ('http://127.0.0.1:8084', 8084),
        }
        results = {}
        all_ok = True
        max_time = 0

        for domain, (base, port) in subdomains.items():
            url = f'{base}{endpoints[0]}'
            code, elapsed, body = self._http_get(url, self.config.get('timeout', 5))
            max_time = max(max_time, elapsed)
            ok = code == 200
            results[domain] = {'code': code, 'ms': elapsed, 'ok': ok}
            if not ok:
                all_ok = False

        detail = {'endpoints': results}
        if all_ok:
            return CheckResult('passed', max_time, f'所有 {len(subdomains)} 个子站 API 正常', detail)
        failed = [k for k, v in results.items() if not v['ok']]
        status = 'warning' if len(failed) <= 2 else 'error'
        return CheckResult(status, max_time,
                           f'{len(failed)}/{len(subdomains)} 子站异常: {", ".join(failed)}', detail)


# ─── 2. 数据库连接检查 ─────────────────────────────────────────────────────

@register('database')
class DatabaseHealthCheck(BaseHealthCheck):
    check_key = 'database'
    name = '数据库连接检查'
    category = 'system'
    severity = 'critical'
    description = 'SQLite 数据库连接状态、表数量、文件大小'
    sort_order = 20
    config_defaults = {'timeout': 3}
    config_schema = {
        'type': 'object',
        'properties': {
            'timeout': {'type': 'integer', 'default': 3, 'description': '超时(秒)'},
        }
    }

    def check(self) -> CheckResult:
        from models import get_db as main_db
        start = time.time()
        try:
            with main_db() as conn:
                conn.execute('SELECT 1')
                elapsed = int((time.time() - start) * 1000)
                tables = conn.execute(
                    "SELECT COUNT(*) as c FROM sqlite_master WHERE type='table'"
                ).fetchone()['c']
                db_path = os.environ.get('DB_PATH', os.path.join(BASE_DIR, '..', 'data', 'x7k2m9a4.db'))
                db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            size_str = f'{db_size/1024/1024:.1f}MB' if db_size > 1024*1024 else f'{db_size/1024:.0f}KB'
            return CheckResult('passed', elapsed,
                               f'数据库正常 ({tables} 张表, {size_str})',
                               {'tables': tables, 'db_size_bytes': db_size, 'type': 'SQLite'})
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('error', elapsed, f'数据库连接失败: {e}', {'error': str(e)})


# ─── 3. Redis 缓存检查 ──────────────────────────────────────────────────────

@register('redis')
class RedisHealthCheck(BaseHealthCheck):
    check_key = 'redis'
    name = 'Redis缓存检查'
    category = 'system'
    severity = 'warning'
    description = 'Redis 缓存服务连接状态'
    sort_order = 25
    config_defaults = {'host': '127.0.0.1', 'port': 6379, 'timeout': 3}
    config_schema = {
        'type': 'object',
        'properties': {
            'host': {'type': 'string', 'default': '127.0.0.1', 'description': 'Redis 主机'},
            'port': {'type': 'integer', 'default': 6379, 'description': '端口'},
            'timeout': {'type': 'integer', 'default': 3, 'description': '超时(秒)'},
        }
    }

    def check(self) -> CheckResult:
        try:
            import redis as redis_client
        except ImportError:
            return CheckResult('warning', 0, 'Redis 客户端未安装 (pip install redis)')

        host = self.config.get('host', '127.0.0.1')
        port = self.config.get('port', 6379)
        start = time.time()
        try:
            r = redis_client.Redis(host=host, port=port, socket_timeout=3)
            r.ping()
            elapsed = int((time.time() - start) * 1000)
            # 额外：检查连接池信息
            info = r.info()
            pool_info = {
                'connected_clients': info.get('connected_clients', 'N/A'),
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'uptime_in_days': info.get('uptime_in_days', 'N/A'),
            }
            return CheckResult('passed', elapsed,
                               f'Redis 正常 ({host}:{port}, 连接数:{pool_info["connected_clients"]})',
                               pool_info)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('warning', elapsed, f'Redis 检查失败: {e}')


# ─── 4. 服务器资源检查 ─────────────────────────────────────────────────────

@register('server_resources')
class ServerHealthCheck(BaseHealthCheck):
    check_key = 'server_resources'
    name = '服务器资源检查'
    category = 'system'
    severity = 'warning'
    description = 'CPU / 内存 / 磁盘使用率监控'
    sort_order = 30
    config_defaults = {'cpu_threshold': 90, 'mem_threshold': 85, 'disk_threshold': 85}
    config_schema = {
        'type': 'object',
        'properties': {
            'cpu_threshold': {'type': 'integer', 'default': 90, 'description': 'CPU 告警阈值(%)'},
            'mem_threshold': {'type': 'integer', 'default': 85, 'description': '内存告警阈值(%)'},
            'disk_threshold': {'type': 'integer', 'default': 85, 'description': '磁盘告警阈值(%)'},
        }
    }

    def check(self) -> CheckResult:
        start = time.time()
        detail = {}
        warnings = []

        # CPU
        try:
            with open('/proc/stat') as f:
                parts = list(map(int, f.readline().split()[1:]))
            total, idle = sum(parts), parts[3]
            time.sleep(0.1)
            with open('/proc/stat') as f:
                parts2 = list(map(int, f.readline().split()[1:]))
            total2, idle2 = sum(parts2), parts2[3]
            diff_total = total2 - total
            cpu_usage = round(100 - (idle2 - idle) * 100 / diff_total, 1) if diff_total > 0 else 0
            detail['cpu_usage_pct'] = cpu_usage
            if cpu_usage > self.config.get('cpu_threshold', 90):
                warnings.append(f'CPU {cpu_usage}% > 阈值')
        except Exception as e:
            cpu_usage = -1
            detail['cpu_error'] = str(e)

        # 内存
        try:
            with open('/proc/meminfo') as f:
                mem = {}
                for line in f:
                    p = line.split(':')
                    if len(p) == 2:
                        try: mem[p[0].strip()] = int(p[1].strip().replace(' kB', ''))
                        except: pass
            mt, ma = mem.get('MemTotal', 0), mem.get('MemAvailable', 0)
            mem_usage = round(100 - ma * 100 / mt, 1) if mt > 0 else 0
            detail['mem_usage_pct'] = mem_usage
            if mem_usage > self.config.get('mem_threshold', 85):
                warnings.append(f'内存 {mem_usage}% > 阈值')
        except Exception as e:
            mem_usage = -1
            detail['mem_error'] = str(e)

        # 磁盘
        try:
            s = os.statvfs('/')
            du = round(100 - s.f_bfree * 100 / s.f_blocks, 1)
            detail['disk_usage_pct'] = du
            if du > self.config.get('disk_threshold', 85):
                warnings.append(f'磁盘 {du}% > 阈值')
        except Exception as e:
            du = -1
            detail['disk_error'] = str(e)

        elapsed = int((time.time() - start) * 1000)
        detail['elapsed_ms'] = elapsed
        if not warnings:
            return CheckResult('passed', elapsed,
                               f'CPU {cpu_usage}% | 内存 {mem_usage}% | 磁盘 {du}%', detail)
        return CheckResult('warning', elapsed, '; '.join(warnings), detail)


# ─── 5. SSL 证书检查 ───────────────────────────────────────────────────────

@register('ssl_cert')
class SSLHealthCheck(BaseHealthCheck):
    check_key = 'ssl_cert'
    name = 'SSL证书检查'
    category = 'ssl'
    severity = 'warning'
    description = '各子域名 SSL 证书到期时间检查'
    sort_order = 50
    config_defaults = {
        'domains': [deploy.server_name(),
                     deploy.server_name('platform'), deploy.server_name('agent')],
        'expire_warn_days': 30,
    }
    config_schema = {
        'type': 'object',
        'properties': {
            'domains': {'type': 'array', 'items': {'type': 'string'},
                        'description': '要检查的域名列表'},
            'expire_warn_days': {'type': 'integer', 'default': 30,
                                 'description': '到期前 N 天开始警告'},
        }
    }

    def check(self) -> CheckResult:
        domains = self.config.get('domains', [])
        warn_days = self.config.get('expire_warn_days', 30)
        results = {}
        all_ok = True
        any_warning = False
        max_time = 0

        for domain in domains:
            try:
                ctx = ssl.create_default_context()
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        elapsed = int((time.time() - start) * 1000) if 'start' in locals() else 0
                        expire = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                        days = (expire - datetime.now()).days
                        results[domain] = {'days_left': days, 'expire': cert['notAfter']}
                        if days <= 0:
                            all_ok = False
                            results[domain]['status'] = 'expired'
                        elif days <= warn_days:
                            any_warning = True
                            results[domain]['status'] = 'expiring_soon'
                        else:
                            results[domain]['status'] = 'ok'
            except Exception as e:
                results[domain] = {'status': 'error', 'error': str(e)[:50]}

        elapsed = int((time.time() - start) * 1000) if 'start' in dir() else 0
        ok_count = sum(1 for r in results.values() if r.get('status') == 'ok')
        detail = {'domains': results}

        if all_ok and not any_warning:
            return CheckResult('passed', max_time,
                               f'{ok_count}/{len(domains)} 域名 SSL 有效', detail)
        elif all_ok:
            expiring = [d for d, r in results.items() if r.get('status') == 'expiring_soon']
            return CheckResult('warning', max_time,
                               f'{len(expiring)} 个域名证书即将到期', detail)
        else:
            return CheckResult('error', max_time, '部分 SSL 证书异常', detail)


# ─── 6. 外部依赖 API 检查 ──────────────────────────────────────────────────

@register('external_apis')
class ExternalAPIHealthCheck(BaseHealthCheck):
    check_key = 'external_apis'
    name = 'External Dependencies Check'
    category = 'external'
    severity = 'warning'
    description = 'Stock/AI/Payment dependencies'
    sort_order = 40
    config_defaults = {'timeout': 10, 'endpoints': []}
    config_schema = {
        'type': 'object',
        'properties': {
            'endpoints': {
                'type': 'array',
                'items': {'type': 'string'},
                'description': 'External API URLs to check'
            },
            'timeout': {'type': 'integer', 'default': 10, 'description': 'Timeout (seconds)'},
        }
    }

    def check(self) -> CheckResult:
        start = time.time()
        endpoints = self.config.get('endpoints', [])
        if not endpoints:
            return CheckResult('passed', 0, '未配置外部 API 端点（可在管理页面配置）')

        results = {}
        max_time = 0
        timeout = self.config.get('timeout', 10)

        for url in endpoints:
            code, elapsed, body = self._http_get(url, timeout)
            max_time = max(max_time, elapsed)
            host = url.split('/')[2] if '//' in url else url
            ok = (code == 200)
            results[host] = {'code': code, 'ms': elapsed, 'status': 'ok' if ok else 'fail'}

        elapsed = int((time.time() - start) * 1000)
        failed = [f'{k}({v["code"]})' for k, v in results.items() if v['status'] == 'fail']
        if not failed:
            return CheckResult('passed', max_time,
                               f'所有 {len(endpoints)} 个外部 API 正常')
        return CheckResult('warning', max_time,
                           f'{len(failed)}/{len(endpoints)} 个异常: {", ".join(failed)}',
                           {'endpoints': results})


# ─── 7. Workflow 引擎检查 ─────────────────────────────────────────────────

@register('workflow_engine')
class WorkflowHealthCheck(BaseHealthCheck):
    check_key = 'workflow_engine'
    name = '工作流引擎检查'
    category = 'workflow'
    severity = 'warning'
    description = 'Cron / Workflow 调度器运行状态、最近执行记录'
    sort_order = 60
    config_defaults = {'timeout': 5}

    def check(self) -> CheckResult:
        start = time.time()
        try:
            from orchestrator import models as om
        except ImportError:
            return CheckResult('warning', 0, 'Orchestrator 模块未安装')

        try:
            with om.get_db() as conn:
                cron_total = conn.execute('SELECT COUNT(*) as c FROM cron_jobs').fetchone()['c']
                cron_active = conn.execute('SELECT COUNT(*) as c FROM cron_jobs WHERE is_active=1').fetchone()['c']
                wf_total = conn.execute('SELECT COUNT(*) as c FROM workflow_definitions').fetchone()['c']
                recent_failed = conn.execute(
                    "SELECT COUNT(*) as c FROM workflow_instances "
                    "WHERE status='failed' AND created_at>=datetime('now', '-1 day')"
                ).fetchone()['c']
            elapsed = int((time.time() - start) * 1000)
            detail = {'cron_total': cron_total, 'cron_active': cron_active,
                      'workflows': wf_total, 'recent_failures_24h': recent_failed}
            warnings = []
            if recent_failed > 5:
                warnings.append(f'24h 内 {recent_failed} 个工作流失败')
            status = 'passed' if not warnings else 'warning'
            msg = f'{cron_active}/{cron_total} Cron 活跃 | {wf_total} 工作流'
            if warnings:
                msg += ' | ' + '; '.join(warnings)
            return CheckResult(status, elapsed, msg, detail)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('warning', elapsed, f'检查失败: {e}')


# ─── 8. Agent 矩阵检查 ────────────────────────────────────────────────────

@register('agent_matrix')
class AgentMatrixHealthCheck(BaseHealthCheck):
    check_key = 'agent_matrix'
    name = 'Agent矩阵检查'
    category = 'agent'
    severity = 'warning'
    description = 'Agent 矩阵（主配置 + 系统Agent + 用户Agent + 运行中任务）状态'
    sort_order = 70
    config_defaults = {'timeout': 10}

    def check(self) -> CheckResult:
        start = time.time()
        try:
            from agent_matrix.models import get_db as am_get_db
        except ImportError:
            return CheckResult('warning', 0, 'Agent Matrix 模块未安装')

        try:
            with am_get_db() as conn:
                tables = [t['name'] for t in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
                detail = {'tables_found': [t for t in tables if 'agent' in t.lower()]}

                # agent_matrix
                am_count = conn.execute('SELECT COUNT(*) as c FROM agent_matrix').fetchone()['c'] if 'agent_matrix' in tables else 0
                # system_agents
                sa_count = conn.execute('SELECT COUNT(*) as c FROM system_agents WHERE is_active=1').fetchone()['c'] if 'system_agents' in tables else 0
                # agent_profiles
                ap_count = conn.execute('SELECT COUNT(*) as c FROM agent_profiles').fetchone()['c'] if 'agent_profiles' in tables else 0
                # running tasks
                task_count = conn.execute("SELECT COUNT(*) as c FROM agent_tasks WHERE status='running'").fetchone()['c'] if 'agent_tasks' in tables else 0

                detail.update({'agent_matrix': am_count, 'system_agents_active': sa_count,
                               'agent_profiles': ap_count, 'running_tasks': task_count})

            elapsed = int((time.time() - start) * 1000)
            return CheckResult('passed', elapsed,
                               f'{am_count} 矩阵配置 | {sa_count} 系统Agent | {ap_count} 用户Agent | {task_count} 运行中',
                               detail)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('warning', elapsed, f'检查失败: {e}')


# ─── 9. 内容工厂检查 ──────────────────────────────────────────────────────

@register('content_factory')
class ContentFactoryHealthCheck(BaseHealthCheck):
    check_key = 'content_factory'
    name = '内容工厂检查'
    category = 'cms'
    severity = 'warning'
    description = '内容工厂采集通道状态、加工队列、待审核内容'
    sort_order = 80
    config_defaults = {'timeout': 5}

    def check(self) -> CheckResult:
        start = time.time()
        try:
            from models import get_db as main_db
            with main_db() as conn:
                tables = [t['name'] for t in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
                detail = {}
                channels = conn.execute('SELECT COUNT(*) as c FROM collection_channels WHERE is_active=1').fetchone()['c'] if 'collection_channels' in tables else 0
                processing = conn.execute("SELECT COUNT(*) as c FROM content_items WHERE status='processing'").fetchone()['c'] if 'content_items' in tables else 0
                pending = conn.execute("SELECT COUNT(*) as c FROM content_items WHERE status='pending_review'").fetchone()['c'] if 'content_items' in tables else 0
                detail.update({'active_channels': channels, 'processing': processing, 'pending_review': pending})

            elapsed = int((time.time() - start) * 1000)
            return CheckResult('passed', elapsed,
                               f'{channels} 通道 | {processing} 加工中 | {pending} 待审核', detail)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('warning', elapsed, f'检查失败: {e}')


# ─── 11. SSE / WS 连接检查 ────────────────────────────────────────────────

@register('sse_ws')
class SSEWebSocketHealthCheck(BaseHealthCheck):
    check_key = 'sse_ws'
    name = 'SSE/WS连接检查'
    category = 'system'
    severity = 'warning'
    description = 'SSE 推送 / WebSocket 连接状态'
    sort_order = 95
    config_defaults = {'timeout': 5}
    config_schema = {
        'type': 'object',
        'properties': {
            'endpoints': {'type': 'array', 'items': {'type': 'string'},
                          'description': 'SSE 端点列表'},
        }
    }

    def check(self) -> CheckResult:
        start = time.time()
        endpoints = self.config.get('endpoints', [])
        detail = {}
        warnings = []

        for url in endpoints:
            try:
                code, elapsed, body = self._http_get(url, timeout=5)
                if code in (200, 404, 405):
                    detail[url] = f'HTTP {code} (服务运行中)'
                else:
                    warnings.append(f'{url} 返回 {code}')
                    detail[url] = f'异常: {code}'
            except Exception as e:
                warnings.append(f'{url} 不可达')
                detail[f'{url}_error'] = str(e)[:50]

        elapsed = int((time.time() - start) * 1000)
        if not warnings:
            return CheckResult('passed', elapsed, 'SSE/WS 连接正常', detail)
        return CheckResult('warning', elapsed, '; '.join(warnings), detail)


# ─── 12. 错误日志统计 ──────────────────────────────────────────────────────

@register('error_logs')
class ErrorLogHealthCheck(BaseHealthCheck):
    check_key = 'error_logs'
    name = '错误日志统计'
    category = 'error'
    severity = 'warning'
    description = '最近 24 小时错误日志统计'
    sort_order = 100
    config_defaults = {'hours': 24, 'threshold': 50}
    config_schema = {
        'type': 'object',
        'properties': {
            'hours': {'type': 'integer', 'default': 24, 'description': '统计时间范围(小时)'},
            'threshold': {'type': 'integer', 'default': 50, 'description': '告警阈值(错误数)'},
        }
    }

    def check(self) -> CheckResult:
        start = time.time()
        hours = self.config.get('hours', 24)
        threshold = self.config.get('threshold', 50)

        try:
            from models import get_db as main_db
            with main_db() as conn:
                if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_logs'").fetchone():
                    errors = conn.execute(
                        "SELECT COUNT(*) as c FROM admin_logs WHERE (action LIKE '%error%' OR action LIKE '%fail%') "
                        "AND created_at>=datetime('now', '-{} hours')".format(hours)
                    ).fetchone()['c']
                else:
                    errors = 0
            elapsed = int((time.time() - start) * 1000)
            detail = {'recent_errors_24h': errors, 'threshold': threshold}
            if errors > threshold:
                return CheckResult('warning', elapsed,
                                   f'最近{hours}h 内 {errors} 个错误（阈值 {threshold}）', detail)
            return CheckResult('passed', elapsed, f'最近{hours}h 内 {errors} 个错误日志', detail)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('passed', elapsed, f'检查跳过: {e}')


# ═══════════════════════════════════════════════════════════════════════════
# 自动修复建议 (FixSuggestion)
# ═══════════════════════════════════════════════════════════════════════════
# 检查器可在 CheckResult.detail 中附带 fix_suggestions 数组，
# 系统管理员或自动修复程序可根据建议执行修复操作。
# ═══════════════════════════════════════════════════════════════════════════

class FixSuggestion:
    """
    修复建议 — 描述一条可执行的修复操作。

    record_type:  记录类型标识（如 'media_file', 'avatar', 'brand_logo'）
    table:        数据库表名
    record_id:    记录 ID
    field:        字段名（哪个字段引用了不存在的文件）
    missing_path: 磁盘上丢失的文件路径
    action:       建议操作: 'mark_deleted' / 'delete_record' / 'clear_field'
    reason:       修复原因说明
    """
    def __init__(self, record_type: str, table: str, record_id: int,
                 field: str, missing_path: str, action: str = 'mark_deleted',
                 reason: str = ''):
        self.record_type = record_type
        self.table = table
        self.record_id = record_id
        self.field = field
        self.missing_path = missing_path
        self.action = action
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            'record_type': self.record_type,
            'table': self.table,
            'record_id': self.record_id,
            'field': self.field,
            'missing_path': self.missing_path,
            'action': self.action,
            'reason': self.reason,
        }

    @staticmethod
    def apply_fix(conn, suggestion: 'FixSuggestion') -> bool:
        """在已有数据库连接上执行修复操作。返回 True 表示成功。"""
        if suggestion.action == 'mark_deleted':
            if hasattr(conn, 'execute'):
                # SQLite
                conn.execute(
                    f"UPDATE {suggestion.table} SET status='deleted' WHERE id=?",
                    (suggestion.record_id,)
                )
                return True
        elif suggestion.action == 'clear_field':
            if hasattr(conn, 'execute'):
                conn.execute(
                    f"UPDATE {suggestion.table} SET {suggestion.field}=? WHERE id=?",
                    ('', suggestion.record_id)
                )
                return True
        elif suggestion.action == 'delete_record':
            if hasattr(conn, 'execute'):
                conn.execute(
                    f"DELETE FROM {suggestion.table} WHERE id=?",
                    (suggestion.record_id,)
                )
                return True
        return False


# ═══════════════════════════════════════════════════════════════════════════
# 媒体完整性检查器 (MediaIntegrityChecker)
# ═══════════════════════════════════════════════════════════════════════════
# 扫描数据库中引用的媒体/头像文件，检查磁盘上是否真实存在。
# 发现丢失文件时报告 warning + 附带修复建议。
# ═══════════════════════════════════════════════════════════════════════════

# 项目根目录（用于定位媒体文件磁盘路径）
PROJECT_ROOT = os.path.normpath(os.path.join(BASE_DIR, '..'))

# URL 路径 → 磁盘路径的映射规则（按优先级排序）
_PATH_MAP = [
    ('/static/media/',     os.path.join(PROJECT_ROOT, 'admin', 'static', 'media')),
    ('/static/avatars/',   os.path.join(PROJECT_ROOT, 'admin', 'static', 'avatars')),
    ('/admin/static/media/', os.path.join(PROJECT_ROOT, 'admin', 'static', 'media')),
    ('/admin/static/avatars/', os.path.join(PROJECT_ROOT, 'admin', 'static', 'avatars')),
]


def _url_to_fs_path(url_path: str) -> str:
    """将 URL 路径（如 /static/media/xxx.jpg）转为本地文件系统路径。"""
    for url_prefix, fs_dir in _PATH_MAP:
        if url_path.startswith(url_prefix):
            rel = url_path[len(url_prefix):]
            # 去掉多余的 static/ 前缀（如 static/static/media/xxx → media/xxx）
            if rel.startswith('static/'):
                rel = rel[7:]
            return os.path.normpath(os.path.join(fs_dir, rel)).replace('\\', '/')
    # fallback: 尝试直接拼接
    fname = os.path.basename(url_path)
    return os.path.join(PROJECT_ROOT, 'admin', 'static', 'media', fname).replace('\\', '/')


@register('media_integrity')
class MediaIntegrityChecker(BaseHealthCheck):
    check_key = 'media_integrity'
    name = '媒体完整性检查'
    category = 'cms'
    severity = 'warning'
    description = '扫描数据库中引用的媒体文件/头像，检测磁盘上是否真实存在'
    sort_order = 85
    config_defaults = {
        'dry_run': True,           # 默认只报告不修复
        'max_fixes_per_run': 20,   # 单次最多修复数
    }
    config_schema = {
        'type': 'object',
        'properties': {
            'dry_run': {'type': 'boolean', 'default': True,
                        'description': 'Dry-run 模式：只报告不执行修复'},
            'max_fixes_per_run': {'type': 'integer', 'default': 20,
                                  'description': '单次巡检最多修复的记录数'},
        }
    }

    def _check_paths(self, records: list, path_field: str, record_type: str,
                     table: str) -> list:
        """检查一批记录的文件是否存在。返回缺失记录列表。"""
        missing = []
        for rec in records:
            raw_path = rec.get(path_field, '')
            if not raw_path:
                continue
            fs_path = _url_to_fs_path(raw_path)
            if not os.path.exists(fs_path):
                missing.append({
                    'record': rec,
                    'fs_path': fs_path,
                    'raw_path': raw_path,
                    'record_type': record_type,
                    'table': table,
                })
        return missing

    def _build_fix_suggestions(self, missing_items: list) -> list:
        """为丢失记录生成修复建议。"""
        suggestions = []
        for item in missing_items:
            rec = item['record']
            action = 'clear_field'
            reason = f'文件不存在: {item["raw_path"]}'
            # media_files 记录可以软删除
            if item['table'] == 'media_files':
                action = 'mark_deleted'
            suggestions.append(FixSuggestion(
                record_type=item['record_type'],
                table=item['table'],
                record_id=rec['id'],
                field=item.get('field', ''),
                missing_path=item['fs_path'],
                action=action,
                reason=reason,
            ))
        return suggestions

    def check(self) -> CheckResult:
        start = time.time()
        missing_all = []
        dry_run = self.config.get('dry_run', True)
        max_fixes = self.config.get('max_fixes_per_run', 20)

        try:
            from models import get_db as main_db
        except ImportError:
            return CheckResult('warning', 0, '主库 models 模块未安装，跳过媒体检查')

        with main_db() as conn:
            tables_found = [t['name'] for t in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]

            # ── 1. media_files 表：主媒体库 ──
            if 'media_files' in tables_found:
                rows = conn.execute(
                    "SELECT id, file_path, thumb_path, original_name FROM media_files "
                    "WHERE status IS NULL OR status!='deleted'"
                ).fetchall()
                for field in ('file_path', 'thumb_path'):
                    missing_all.extend(self._check_paths(
                        [dict(r) for r in rows], field, 'media_file', 'media_files'
                    ))

            # ── 2. users 表：头像 ──
            if 'users' in tables_found:
                rows = conn.execute(
                    "SELECT id, avatar_url FROM users "
                    "WHERE avatar_url IS NOT NULL AND avatar_url != ''"
                ).fetchall()
                missing_all.extend(self._check_paths(
                    [dict(r) for r in rows], 'avatar_url', 'avatar', 'users'
                ))

            # ── 3. brand_settings: logo + favicon ──
            if 'brand_settings' in tables_found:
                row = conn.execute(
                    "SELECT id, logo_url, favicon_url FROM brand_settings WHERE id=1"
                ).fetchone()
                if row:
                    r = dict(row)
                    missing_all.extend(self._check_paths(
                        [r], 'logo_url', 'brand_logo', 'brand_settings'
                    ))
                    missing_all.extend(self._check_paths(
                        [r], 'favicon_url', 'brand_favicon', 'brand_settings'
                    ))

            # ── 4. social_links: 图标 ──
            if 'social_links' in tables_found:
                rows = conn.execute(
                    "SELECT id, icon_url, name FROM social_links "
                    "WHERE icon_url IS NOT NULL AND icon_url != ''"
                ).fetchall()
                missing_all.extend(self._check_paths(
                    [dict(r) for r in rows], 'icon_url', 'social_icon', 'social_links'
                ))

        # 去重：同一个文件路径被多条记录引用
        seen_paths = set()
        unique_missing = []
        for item in missing_all:
            key = (item['fs_path'], item['record']['id'], item.get('field', ''))
            if key not in seen_paths:
                seen_paths.add(key)
                unique_missing.append(item)

        fix_suggestions = self._build_fix_suggestions(unique_missing[:max_fixes])
        total_missing = len(unique_missing)
        limited = total_missing > max_fixes

        elapsed = int((time.time() - start) * 1000)
        detail = {
            'total_missing': total_missing,
            'max_fixes': max_fixes,
            'limited': limited,
            'dry_run': dry_run,
            'items': [{
                'record_type': item['record_type'],
                'table': item['table'],
                'id': item['record']['id'],
                'field': item.get('field', ''),
                'raw_path': item['raw_path'],
                'fs_path': item['fs_path'],
                'original_name': item['record'].get('original_name', ''),
            } for item in unique_missing[:max_fixes]],
            'fix_suggestions': [s.to_dict() for s in fix_suggestions],
        }

        if total_missing == 0:
            return CheckResult('passed', elapsed, '所有媒体文件均存在', detail)

        msg = f'发现 {total_missing} 个丢失文件'
        if limited:
            msg += f'（仅展示前 {max_fixes} 个）'
        if dry_run:
            msg += '（Dry-run 模式，未执行修复）'
        return CheckResult('warning', elapsed, msg, detail)


# ═══════════════════════════════════════════════════════════════════════════
# 添加新检查项的模板（复制此段即可）
# ═══════════════════════════════════════════════════════════════════════════
#
# 使用方法:
#   1. 在 health_checks 表中添加记录（check_key 需与注册 key 一致）
#   2. 如果要立即生效，重启 admin 服务即可
#
# 无需修改任何其他代码。
#
# ─── 模板开始 ────────────────────────────────────────────────────────────
#
# @register('your_check_key')           # ← 唯一键，与 health_checks.check_key 对应
# class YourCheck(BaseHealthCheck):
#     check_key = 'your_check_key'
#     name = '你的检查项名称'              # ← 管理后台显示的名称
#     category = 'system'                 # ← 分类: system/external/workflow/agent/cms/community/ssl/error
#     severity = 'warning'                # ← 告警级别: info/warning/critical
#     description = '描述这个检查项做什么'  # ← 描述
#     sort_order = 55                     # ← 排序值（越小越靠前）
#
#     # 配置默认值（可选）
#     config_defaults = {
#         'timeout': 5,
#         'some_option': 'default_value',
#     }
#
#     # 配置 JSON Schema（可选，用于管理后台可视化编辑）
#     config_schema = {
#         'type': 'object',
#         'properties': {
#             'timeout': {'type': 'integer', 'default': 5, 'description': '超时时间(秒)'},
#             'some_option': {'type': 'string', 'default': 'default_value', 'description': '选项说明'},
#         }
#     }
#
#     def check(self) -> CheckResult:
#         """实现检查逻辑，返回 CheckResult"""
#         start = time.time()
#         try:
#             # ... 你的检查逻辑 ...
#             elapsed = int((time.time() - start) * 1000)
#             return CheckResult('passed', elapsed, '一切正常', {'key': 'value'})
#         except Exception as e:
#             elapsed = int((time.time() - start) * 1000)
#             return CheckResult('error', elapsed, f'出错: {e}')
#
# ─── 模板结束 ────────────────────────────────────────────────────────────
