#!/usr/bin/env python3
"""
Health Check — Checkers
=========================
All checkers inherit from BaseHealthCheck and auto-register via the @register
decorator.

Adding a new checker takes 3 steps:
  1. Inherit BaseHealthCheck in this file (or create a new checker_xxx.py)
  2. Decorate with @register
  3. Add a record to the health_checks table (ORM / API)

See DEVELOPER.md for detailed tutorial.
"""

import os, sys, json, time, socket, ssl, subprocess
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, Tuple
from services.deployment_config import deploy
from i18n import _

import urllib.request
import urllib.error

# Add project path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))


# ═══════════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════════

class CheckerRegistry:
    """
    Global checker registry.
    Register via @register(check_key) decorator or directly call register().
    """

    _checkers: Dict[str, Type['BaseHealthCheck']] = {}

    @classmethod
    def register(cls, check_key: str, checker_cls: Type['BaseHealthCheck'] = None):
        """
        Register a checker — can be used as decorator or direct call.

        Usage:
            @register('my_check')
            class MyCheck(BaseHealthCheck): ...
        """
        if checker_cls is not None:
            cls._checkers[check_key] = checker_cls
            return checker_cls

        def decorator(klass):
            cls._checkers[check_key] = klass
            # Set check_key on class if not explicitly defined
            if not hasattr(klass, 'check_key') or not klass.check_key:
                klass.check_key = check_key
            return klass
        return decorator

    @classmethod
    def get(cls, check_key: str) -> Optional[Type['BaseHealthCheck']]:
        """Get checker class by key."""
        return cls._checkers.get(check_key)

    @classmethod
    def get_instance(cls, check_key: str, config: dict = None) -> Optional['BaseHealthCheck']:
        """Get checker instance."""
        klass = cls.get(check_key)
        if not klass:
            return None
        return klass(config or {})

    @classmethod
    def list_registered(cls) -> List[Dict]:
        """List metadata for all registered checkers (used by admin UI)."""
        result = []
        for key, klass in sorted(cls._checkers.items()):
            # Instantiate to get metadata (may depend on config, use empty dict)
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
        """Unregister a checker."""
        cls._checkers.pop(check_key, None)

    @classmethod
    def size(cls) -> int:
        return len(cls._checkers)


# Convenience alias
register = CheckerRegistry.register


# ═══════════════════════════════════════════════════════════════════════════
# Check Result
# ═══════════════════════════════════════════════════════════════════════════

class CheckResult:
    """Result of a single check."""
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
# Abstract Base HealthCheck
# ═══════════════════════════════════════════════════════════════════════════

class BaseHealthCheck(ABC):
    """
    Abstract base class for health checkers.
    All custom checkers must inherit from this class and implement check().

    Class attributes (overridable):
        check_key: str              — Unique key (defaults to registry key)
        name: str                   — Display name
        category: str               — Category (system/external/workflow/agent/cms/community/ssl/error)
        severity: str               — Severity (info/warning/critical)
        description: str            — Description
        sort_order: int             — Sort weight
        config_schema: dict         — JSON Schema for config
        config_defaults: dict       — Default config values

    Subclasses must implement:
        check(self) -> CheckResult  — Run the check
    """

    # ── Metadata (override in subclasses) ──
    check_key: str = ''
    name: str = 'Unnamed Check'
    category: str = 'system'
    severity: str = 'warning'
    description: str = ''
    sort_order: int = 50
    config_schema: dict = {}
    config_defaults: dict = {}

    def __init__(self, config: dict):
        """Initialize checker; config is read from health_checks.config JSON."""
        self.config = {**self.config_defaults, **config}

    # ── Metadata accessors (overridable) ──

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
        """Return JSON Schema for config (used by admin page config editor)."""
        return self.config_schema

    def get_config_defaults(self) -> dict:
        return self.config_defaults

    # ── Check entry point ──

    @abstractmethod
    def check(self) -> CheckResult:
        """
        The sole entry point for running a check.
        Subclasses must implement this and return a CheckResult.
        """
        pass

    # ── Legacy compatibility (called by routes.py) ──
    def run(self) -> CheckResult:
        """Legacy compatibility: delegates to check() by default."""
        return self.check()

    # ── Utility methods ──

    def _http_get(self, url: str, timeout: int = 5) -> Tuple[int, int, str]:
        """HTTP GET request, returns (status_code, elapsed_ms, body)."""
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
        """Execute a shell command, returns (returncode, stdout, stderr)."""
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
# Concrete Checker Implementations
# ═══════════════════════════════════════════════════════════════════════════
#
# Each checker class below inherits BaseHealthCheck and is registered
# with @register. They are built-in system checkers.
#
# To add a new checker, scroll to the bottom and use the template.
# ═══════════════════════════════════════════════════════════════════════════

# ─── 1. Core API Check ──────────────────────────────────────────────────

@register('core_api')
class CoreAPIHealthCheck(BaseHealthCheck):
    check_key = 'core_api'
    name = 'Core API Check'
    category = 'system'
    severity = 'warning'
    description = 'Health endpoint check for all subsites (Site/Platform/Admin)'
    sort_order = 10
    config_defaults = {'timeout': 5, 'endpoints': ['/health']}
    config_schema = {
        'type': 'object',
        'properties': {
            'timeout': {'type': 'integer', 'default': 5, 'description': 'Timeout (seconds)'},
        }
    }

    def check(self) -> CheckResult:
        endpoints = self.config.get('endpoints', ['/health'])
        subdomains = {
            'Main Site': ('http://127.0.0.1:8081', 8081),
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
            return CheckResult('passed', max_time, f'All {len(subdomains)} subsite APIs OK', detail)
        failed = [k for k, v in results.items() if not v['ok']]
        status = 'warning' if len(failed) <= 2 else 'error'
        return CheckResult(status, max_time,
                           f'{len(failed)}/{len(subdomains)} subsites abnormal: {", ".join(failed)}', detail)


# ─── 2. Database Connection Check ───────────────────────────────────────

@register('database')
class DatabaseHealthCheck(BaseHealthCheck):
    check_key = 'database'
    name = 'Database Connection'
    category = 'system'
    severity = 'critical'
    description = 'SQLite database connection status, table count, and file size'
    sort_order = 20
    config_defaults = {'timeout': 3}
    config_schema = {
        'type': 'object',
        'properties': {
            'timeout': {'type': 'integer', 'default': 3, 'description': 'Timeout (seconds)'},
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
                               f'Database OK ({tables} tables, {size_str})',
                               {'tables': tables, 'db_size_bytes': db_size, 'type': 'SQLite'})
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('error', elapsed, f'Database connection failed: {e}', {'error': str(e)})


# ─── 3. Redis Cache Check ───────────────────────────────────────────────

@register('redis')
class RedisHealthCheck(BaseHealthCheck):
    check_key = 'redis'
    name = 'Redis Cache'
    category = 'system'
    severity = 'warning'
    description = 'Redis cache service connection status'
    sort_order = 25
    config_defaults = {'host': '127.0.0.1', 'port': 6379, 'timeout': 3}
    config_schema = {
        'type': 'object',
        'properties': {
            'host': {'type': 'string', 'default': '127.0.0.1', 'description': 'Redis host'},
            'port': {'type': 'integer', 'default': 6379, 'description': 'Port'},
            'timeout': {'type': 'integer', 'default': 3, 'description': 'Timeout (seconds)'},
        }
    }

    def check(self) -> CheckResult:
        try:
            import redis as redis_client
        except ImportError:
            return CheckResult('warning', 0, 'Redis client not available (pip install redis)')

        host = self.config.get('host', '127.0.0.1')
        port = self.config.get('port', 6379)
        start = time.time()
        try:
            r = redis_client.Redis(host=host, port=port, socket_timeout=3)
            r.ping()
            elapsed = int((time.time() - start) * 1000)
            # Extra: check connection pool info
            info = r.info()
            pool_info = {
                'connected_clients': info.get('connected_clients', 'N/A'),
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'uptime_in_days': info.get('uptime_in_days', 'N/A'),
            }
            return CheckResult('passed', elapsed,
                               f'Redis OK ({host}:{port}, connections:{pool_info["connected_clients"]})',
                               pool_info)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('warning', elapsed, f'Redis check failed: {e}')


# ─── 4. Server Resources Check ─────────────────────────────────────────

@register('server_resources')
class ServerHealthCheck(BaseHealthCheck):
    check_key = 'server_resources'
    name = 'Server Resources'
    category = 'system'
    severity = 'warning'
    description = 'CPU / Memory / Disk usage monitoring'
    sort_order = 30
    config_defaults = {'cpu_threshold': 90, 'mem_threshold': 85, 'disk_threshold': 85}
    config_schema = {
        'type': 'object',
        'properties': {
            'cpu_threshold': {'type': 'integer', 'default': 90, 'description': 'CPU alert threshold (%)'},
            'mem_threshold': {'type': 'integer', 'default': 85, 'description': 'Memory alert threshold (%)'},
            'disk_threshold': {'type': 'integer', 'default': 85, 'description': 'Disk alert threshold (%)'},
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
                warnings.append(f'CPU {cpu_usage}% > threshold')
        except Exception as e:
            cpu_usage = -1
            detail['cpu_error'] = str(e)

        # Memory
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
                warnings.append(f'Memory {mem_usage}% > threshold')
        except Exception as e:
            mem_usage = -1
            detail['mem_error'] = str(e)

        # Disk
        try:
            s = os.statvfs('/')
            du = round(100 - s.f_bfree * 100 / s.f_blocks, 1)
            detail['disk_usage_pct'] = du
            if du > self.config.get('disk_threshold', 85):
                warnings.append(f'Disk {du}% > threshold')
        except Exception as e:
            du = -1
            detail['disk_error'] = str(e)

        elapsed = int((time.time() - start) * 1000)
        detail['elapsed_ms'] = elapsed
        if not warnings:
            return CheckResult('passed', elapsed,
                               f'CPU {cpu_usage}% | Memory {mem_usage}% | Disk {du}%', detail)
        return CheckResult('warning', elapsed, '; '.join(warnings), detail)


# ─── 5. SSL Certificate Check ──────────────────────────────────────────

@register('ssl_cert')
class SSLHealthCheck(BaseHealthCheck):
    check_key = 'ssl_cert'
    name = 'SSL Certificate'
    category = 'ssl'
    severity = 'warning'
    description = 'SSL certificate expiry check for all subdomains'
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
                        'description': 'Domains to check'},
            'expire_warn_days': {'type': 'integer', 'default': 30,
                                 'description': 'Days before expiry to start warning'},
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
            start = time.time()
            try:
                ctx = ssl.create_default_context()
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        elapsed = int((time.time() - start) * 1000)
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
                        max_time = max(max_time, elapsed)
            except Exception as e:
                results[domain] = {'status': 'error', 'error': str(e)[:50]}

        elapsed = int((time.time() - start) * 1000) if 'start' in dir() else 0
        ok_count = sum(1 for r in results.values() if r.get('status') == 'ok')
        detail = {'domains': results}

        if all_ok and not any_warning:
            return CheckResult('passed', max_time,
                               f'{ok_count}/{len(domains)} SSL certificates valid', detail)
        elif all_ok:
            expiring = [d for d, r in results.items() if r.get('status') == 'expiring_soon']
            return CheckResult('warning', max_time,
                               f'{len(expiring)} domain(s) expiring soon', detail)
        else:
            return CheckResult('error', max_time, 'Some SSL certificates abnormal', detail)


# ─── 6. External Dependencies Check ────────────────────────────────────

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
            return CheckResult('passed', 0, 'No external API endpoints configured (can configure in admin)')

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
                               f'All {len(endpoints)} external APIs OK')
        return CheckResult('warning', max_time,
                           f'{len(failed)}/{len(endpoints)} abnormal: {", ".join(failed)}',
                           {'endpoints': results})


# ─── 7. Workflow Engine Check ─────────────────────────────────────────

@register('workflow_engine')
class WorkflowHealthCheck(BaseHealthCheck):
    check_key = 'workflow_engine'
    name = 'Workflow Engine'
    category = 'workflow'
    severity = 'warning'
    description = 'Cron / Workflow scheduler running status and recent execution records'
    sort_order = 60
    config_defaults = {'timeout': 5}

    def check(self) -> CheckResult:
        start = time.time()
        try:
            from orchestrator import models as om
        except ImportError:
            return CheckResult('warning', 0, 'Orchestrator module not available')

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
                warnings.append(f'{recent_failed} workflow failures in 24h')
            status = 'passed' if not warnings else 'warning'
            msg = f'{cron_active}/{cron_total} Cron active | {wf_total} workflows'
            if warnings:
                msg += ' | ' + '; '.join(warnings)
            return CheckResult(status, elapsed, msg, detail)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('warning', elapsed, f'Check failed: {e}')


# ─── 8. Agent Matrix Check ────────────────────────────────────────────

@register('agent_matrix')
class AgentMatrixHealthCheck(BaseHealthCheck):
    check_key = 'agent_matrix'
    name = 'Agent Matrix'
    category = 'agent'
    severity = 'warning'
    description = 'Agent matrix (main config + system agents + user agents + running tasks) status'
    sort_order = 70
    config_defaults = {'timeout': 10}

    def check(self) -> CheckResult:
        start = time.time()
        try:
            from agent_matrix.models import get_db as am_get_db
        except ImportError:
            return CheckResult('warning', 0, 'Agent Matrix module not available')

        try:
            with am_get_db() as conn:
                tables = [t['name'] for t in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
                detail = {'tables_found': [t for t in tables if 'agent' in t.lower()]}

                am_count = conn.execute('SELECT COUNT(*) as c FROM agent_matrix').fetchone()['c'] if 'agent_matrix' in tables else 0
                sa_count = conn.execute('SELECT COUNT(*) as c FROM system_agents WHERE is_active=1').fetchone()['c'] if 'system_agents' in tables else 0
                ap_count = conn.execute('SELECT COUNT(*) as c FROM agent_profiles').fetchone()['c'] if 'agent_profiles' in tables else 0
                task_count = conn.execute("SELECT COUNT(*) as c FROM agent_tasks WHERE status='running'").fetchone()['c'] if 'agent_tasks' in tables else 0

                detail.update({'agent_matrix': am_count, 'system_agents_active': sa_count,
                               'agent_profiles': ap_count, 'running_tasks': task_count})

            elapsed = int((time.time() - start) * 1000)
            return CheckResult('passed', elapsed,
                               f'{am_count} matrix configs | {sa_count} system agents | {ap_count} user agents | {task_count} running',
                               detail)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('warning', elapsed, f'Check failed: {e}')


# ─── 9. Content Factory Check ─────────────────────────────────────────

@register('content_factory')
class ContentFactoryHealthCheck(BaseHealthCheck):
    check_key = 'content_factory'
    name = 'Content Factory'
    category = 'cms'
    severity = 'warning'
    description = 'Content factory collection channel status, processing queue, pending review'
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
                               f'{channels} channels | {processing} processing | {pending} pending review', detail)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('warning', elapsed, f'Check failed: {e}')


# ─── 10. SSE / WebSocket Connection Check ─────────────────────────────

@register('sse_ws')
class SSEWebSocketHealthCheck(BaseHealthCheck):
    check_key = 'sse_ws'
    name = 'SSE/WebSocket'
    category = 'system'
    severity = 'warning'
    description = 'SSE push / WebSocket connection status'
    sort_order = 95
    config_defaults = {'timeout': 5}
    config_schema = {
        'type': 'object',
        'properties': {
            'endpoints': {'type': 'array', 'items': {'type': 'string'},
                          'description': 'SSE endpoint list'},
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
                    detail[url] = f'HTTP {code} (service running)'
                else:
                    warnings.append(f'{url} returned {code}')
                    detail[url] = f'Abnormal: {code}'
            except Exception as e:
                warnings.append(f'{url} unreachable')
                detail[f'{url}_error'] = str(e)[:50]

        elapsed = int((time.time() - start) * 1000)
        if not warnings:
            return CheckResult('passed', elapsed, 'SSE/WS connections OK', detail)
        return CheckResult('warning', elapsed, '; '.join(warnings), detail)


# ─── 11. Error Log Stats ──────────────────────────────────────────────

@register('error_logs')
class ErrorLogHealthCheck(BaseHealthCheck):
    check_key = 'error_logs'
    name = 'Error Logs'
    category = 'error'
    severity = 'warning'
    description = 'Error log count in the last 24 hours'
    sort_order = 100
    config_defaults = {'hours': 24, 'threshold': 50}
    config_schema = {
        'type': 'object',
        'properties': {
            'hours': {'type': 'integer', 'default': 24, 'description': 'Statistics window (hours)'},
            'threshold': {'type': 'integer', 'default': 50, 'description': 'Alert threshold (error count)'},
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
                                   f'{errors} errors in last {hours}h (threshold: {threshold})', detail)
            return CheckResult('passed', elapsed, f'{errors} error logs in last {hours}h', detail)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('passed', elapsed, f'Check skipped: {e}')


# ═══════════════════════════════════════════════════════════════════════════
# Fix Suggestions
# ═══════════════════════════════════════════════════════════════════════════
# Checkers can attach fix_suggestions to their CheckResult.detail,
# so that administrators or auto-repair workflows can execute fixes.
# ═══════════════════════════════════════════════════════════════════════════

class FixSuggestion:
    """
    A single fix suggestion describing an executable repair operation.

    record_type:  Type identifier (e.g. 'media_file', 'avatar', 'brand_logo')
    table:        Database table name
    record_id:    Record ID
    field:        Field name (which field references the missing file)
    missing_path: File path missing on disk
    action:       Suggested action: 'mark_deleted' / 'delete_record' / 'clear_field'
    reason:       Reason for the fix
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
        """Apply a fix using an existing DB connection. Returns True on success."""
        if suggestion.action == 'mark_deleted':
            if hasattr(conn, 'execute'):
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
# Media Integrity Checker
# ═══════════════════════════════════════════════════════════════════════════
# Scans media files/avatars referenced in the database and verifies
# they exist on disk. Reports warnings with fix suggestions for missing files.
# ═══════════════════════════════════════════════════════════════════════════

# Project root for resolving media file disk paths
PROJECT_ROOT = os.path.normpath(os.path.join(BASE_DIR, '..'))

# URL path → disk path mapping rules (highest priority first)
_PATH_MAP = [
    ('/static/media/',     os.path.join(PROJECT_ROOT, 'admin', 'static', 'media')),
    ('/static/avatars/',   os.path.join(PROJECT_ROOT, 'admin', 'static', 'avatars')),
    ('/admin/static/media/', os.path.join(PROJECT_ROOT, 'admin', 'static', 'media')),
    ('/admin/static/avatars/', os.path.join(PROJECT_ROOT, 'admin', 'static', 'avatars')),
]


def _url_to_fs_path(url_path: str) -> str:
    """Convert a URL path (e.g. /static/media/xxx.jpg) to a local filesystem path."""
    for url_prefix, fs_dir in _PATH_MAP:
        if url_path.startswith(url_prefix):
            rel = url_path[len(url_prefix):]
            # Strip extraneous static/ prefix
            if rel.startswith('static/'):
                rel = rel[7:]
            return os.path.normpath(os.path.join(fs_dir, rel)).replace('\\', '/')
    # Fallback: try direct join
    fname = os.path.basename(url_path)
    return os.path.join(PROJECT_ROOT, 'admin', 'static', 'media', fname).replace('\\', '/')


@register('media_integrity')
class MediaIntegrityChecker(BaseHealthCheck):
    check_key = 'media_integrity'
    name = 'Media Integrity'
    category = 'cms'
    severity = 'warning'
    description = 'Scan media files/avatars referenced in DB and verify disk existence'
    sort_order = 85
    config_defaults = {
        'dry_run': True,           # Report only, no fixes by default
        'max_fixes_per_run': 20,   # Max fixes per run
    }
    config_schema = {
        'type': 'object',
        'properties': {
            'dry_run': {'type': 'boolean', 'default': True,
                        'description': 'Dry-run mode: report only, do not execute fixes'},
            'max_fixes_per_run': {'type': 'integer', 'default': 20,
                                  'description': 'Max records to fix per run'},
        }
    }

    def _check_paths(self, records: list, path_field: str, record_type: str,
                     table: str) -> list:
        """Check if files for a batch of records exist on disk. Returns list of missing items."""
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
        """Generate fix suggestions from missing file records."""
        suggestions = []
        for item in missing_items:
            rec = item['record']
            action = 'clear_field'
            reason = f'File not found: {item["raw_path"]}'
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
            return CheckResult('warning', 0, 'Main DB models not available, skipping media check')

        with main_db() as conn:
            tables_found = [t['name'] for t in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]

            # ── 1. media_files table ──
            if 'media_files' in tables_found:
                rows = conn.execute(
                    "SELECT id, file_path, thumb_path, original_name FROM media_files "
                    "WHERE status IS NULL OR status!='deleted'"
                ).fetchall()
                for field in ('file_path', 'thumb_path'):
                    missing_all.extend(self._check_paths(
                        [dict(r) for r in rows], field, 'media_file', 'media_files'
                    ))

            # ── 2. users table: avatars ──
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

            # ── 4. social_links: icons ──
            if 'social_links' in tables_found:
                rows = conn.execute(
                    "SELECT id, icon_url, name FROM social_links "
                    "WHERE icon_url IS NOT NULL AND icon_url != ''"
                ).fetchall()
                missing_all.extend(self._check_paths(
                    [dict(r) for r in rows], 'icon_url', 'social_icon', 'social_links'
                ))

        # Deduplicate by file path + record ID + field
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
            return CheckResult('passed', elapsed, 'All media files exist', detail)

        msg = f'Found {total_missing} missing files'
        if limited:
            msg += f' (showing first {max_fixes})'
        if dry_run:
            msg += ' (Dry-run, no fixes applied)'
        return CheckResult('warning', elapsed, msg, detail)


# ═══════════════════════════════════════════════════════════════════════════
# Template for Adding New Checkers
# ═══════════════════════════════════════════════════════════════════════════
#
# Usage:
#   1. Add a record to the health_checks table (check_key must match the
#      registration key)
#   2. Restart the admin service for it to take effect
#
# No other code changes required.
#
# ─── Template Start ────────────────────────────────────────────────────
#
# @register('your_check_key')           # ← Unique key, matches health_checks.check_key
# class YourCheck(BaseHealthCheck):
#     check_key = 'your_check_key'
#     name = 'Your Check Name'            # ← Display name in admin UI
#     category = 'system'                 # ← Category: system/external/workflow/agent/cms/community/ssl/error
#     severity = 'warning'                # ← Severity: info/warning/critical
#     description = 'Describe what this check does'
#     sort_order = 55                     # ← Sort order (lower = higher priority)
#
#     # Config defaults (optional)
#     config_defaults = {
#         'timeout': 5,
#         'some_option': 'default_value',
#     }
#
#     # Config JSON Schema (optional, for admin page visual editing)
#     config_schema = {
#         'type': 'object',
#         'properties': {
#             'timeout': {'type': 'integer', 'default': 5, 'description': 'Timeout (seconds)'},
#             'some_option': {'type': 'string', 'default': 'default_value', 'description': 'Option description'},
#         }
#     }
#
#     def check(self) -> CheckResult:
#         """Implement check logic, return CheckResult."""
#         start = time.time()
#         try:
#             # ... your check logic ...
#             elapsed = int((time.time() - start) * 1000)
#             return CheckResult('passed', elapsed, 'Everything OK', {'key': 'value'})
#         except Exception as e:
#             elapsed = int((time.time() - start) * 1000)
#             return CheckResult('error', elapsed, f'Error: {e}')
#
# ─── Template End ──────────────────────────────────────────────────────
