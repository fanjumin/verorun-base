# 系统健康巡检中心 — 添加新检查项开发指南

## 架构概览

```
checkers.py                    routes.py                    admin/templates/health.html
┌──────────────────┐           ┌──────────────────┐         ┌──────────────────────┐
│  BaseHealthCheck │           │  GET /api/status  │         │  ⚙️ 管理检查项 tab     │
│  (抽象基类)      │           │  POST /api/run    │ ◄────── │  📦 注册表显示       │
│         ↑        │           │  GET /api/checks  │         │  ＋一键添加          │
│  继承实现        │           │  GET /api/checkers/registry│  🗑 删除/排序/配置   │
│  @register 注册  │           │  POST /api/checkers/register│                    │
│         ↑        │           └──────────────────┘         └──────────────────────┘
│  CheckerRegistry │
│  (全局注册表)    │
└──────────────────┘
```

**核心概念：**
- **BaseHealthCheck** — 所有检查器的抽象基类
- **@register(check_key)** — 将检查器类注册到全局注册表
- **CheckerRegistry** — 管理所有注册的检查器，支持 list / get / unregister
- **health_checks 表** — 存储检查项的启用/禁用、配置、排序等状态
- **健康巡检运行引擎** — 遍历 health_checks 表中启用的项，逐一执行检查

---

## 方式一：代码注册（推荐）

### 步骤 1：在 checkers.py 中编写检查器类

```python
from easykai_health.checkers import BaseHealthCheck, CheckResult, register

@register('my_business_api')          # ← 唯一键，与 DB 中 check_key 对应
class MyBusinessAPIHealthCheck(BaseHealthCheck):
    # ── 元数据（必填） ──
    check_key = 'my_business_api'
    name = '业务 API 检查'              # 管理后台显示的名称
    category = 'external'              # 分类: system/external/workflow/agent/cms/community/ssl/error
    severity = 'warning'               # 告警级别: info/warning/critical
    description = '检查特定业务 API 的可用性和响应时间'
    sort_order = 55                    # 排序值（越小越靠前）

    # ── 配置默认值（可选） ──
    config_defaults = {
        'timeout': 5,
        'base_url': 'https://api.example.com',
    }

    # ── 配置 JSON Schema（可选，管理后台可视化编辑） ──
    config_schema = {
        'type': 'object',
        'properties': {
            'timeout': {'type': 'integer', 'default': 5, 'description': '超时(秒)'},
            'base_url': {'type': 'string', 'default': 'https://api.example.com', 'description': 'API 基础 URL'},
        }
    }

    def check(self) -> CheckResult:
        """
        核心检查逻辑。
        返回 CheckResult(status, response_time_ms, message, detail)
        其中 status: 'passed' | 'warning' | 'error'
        """
        start = time.time()
        try:
            url = self.config.get('base_url') + '/health'
            code, elapsed, body = self._http_get(url, self.config.get('timeout', 5))

            if code == 200:
                return CheckResult('passed', elapsed, f'API 正常 (HTTP {code})')
            else:
                return CheckResult('error', elapsed, f'API 返回 {code}')
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('error', elapsed, str(e))
```

### 步骤 2：在管理后台启用

1. 部署代码后，打开「健康巡检」→「⚙️ 检查项配置」
2. 在「📦 可添加的检查器」区域找到你的新检查项
3. 点击「＋添加」按钮
4. 新检查项会自动出现在已配置列表中，默认启用

---

## 方式二：仅 DB 记录（无需写 Python 代码）

适用于临时性的 HTTP 端点检查或不需要复杂逻辑的场景。

### 在管理后台操作

1. 打开「健康巡检」→「⚙️ 检查项配置」
2. 在「➕ 手动添加检查项」区域填入：
   - Key: `check_my_service`
   - 名称: `我的服务检查`
   - 分类: `external`
   - 级别: `warning`
3. 点击「添加」
4. 该检查项将出现在列表中，执行时状态为 `warning`（无对应的 Python 检查器实现）

---

## 方式三：单独文件注册（模块化）

对于复杂的检查器，可以放在单独的文件中：

```python
# easykai_health/checkers/my_custom_checker.py
from ..checkers import BaseHealthCheck, CheckResult, register

@register('custom_check')
class CustomCheck(BaseHealthCheck):
    check_key = 'custom_check'
    name = '自定义检查'
    category = 'system'
    severity = 'warning'

    def check(self) -> CheckResult:
        # ... 实现
        pass
```

然后在 `routes.py` 或 `__init__.py` 中 import 这个文件：

```python
# 在 checkers.py 末尾或 routes.py 开头
from .checkers.my_custom_checker import CustomCheck  # 触发 @register
```

---

## 检查器 API 参考

### BaseHealthCheck 类

| 方法/属性 | 类型 | 说明 |
|-----------|------|------|
| `check_key` | `str` (类属性) | 唯一标识键 |
| `name` | `str` (类属性) | 显示名称 |
| `category` | `str` (类属性) | 分类标签 |
| `severity` | `str` (类属性) | 告警级别 |
| `description` | `str` (类属性) | 描述 |
| `sort_order` | `int` (类属性) | 排序权重 |
| `config_defaults` | `dict` (类属性) | 默认配置 |
| `config_schema` | `dict` (类属性) | JSON Schema |
| `check()` | 方法 (必须实现) | 执行检查 → CheckResult |
| `_http_get(url, timeout)` | 方法 | HTTP GET 请求 → (status, ms, body) |
| `_exec(cmd, timeout)` | 方法 | Shell 命令 → (rc, stdout, stderr) |

### CheckResult 类

```python
CheckResult(
    status='passed',         # 'passed' | 'warning' | 'error'
    response_time_ms=0,      # 响应时间(毫秒)
    message='一切正常',       # 显示消息
    detail={'key': 'value'}  # JSON 详情（自动序列化）
)
```

### 工具方法

- `self._http_get(url, timeout=5)` → `(status_code, elapsed_ms, body)`
- `self._exec(cmd, timeout=10)` → `(returncode, stdout, stderr)`

---

## 常见示例模板

### 检查特定业务 API（如社区版块接口）

```python
@register('community_api')
class CommunityAPIHealthCheck(BaseHealthCheck):
    check_key = 'community_api'
    name = '社区 API 检查'
    category = 'community'
    severity = 'warning'
    description = '检查社区 7 大版块的关键接口'
    config_defaults = {'timeout': 10}

    def check(self) -> CheckResult:
        start = time.time()
        sections = ['plaza', 'guilds', 'debates', 'alerts', 'ranking', 'arena', 'follows']
        base = 'https://community.your-site.com'
        results = {}
        errors = 0

        for section in sections:
            url = f'{base}/{section}'
            code, elapsed, _ = self._http_get(url, self.config.get('timeout', 5))
            ok = code in (200, 302)
            results[section] = {'code': code, 'ms': elapsed, 'ok': ok}
            if not ok:
                errors += 1

        elapsed = int((time.time() - start) * 1000)
        if errors == 0:
            return CheckResult('passed', elapsed, f'所有 {len(sections)} 个版块正常')
        return CheckResult('warning', elapsed, f'{errors}/{len(sections)} 个异常', {'sections': results})
```

### 检查 Agent 矩阵主/子 Agent

```python
@register('agent_status')
class AgentStatusHealthCheck(BaseHealthCheck):
    check_key = 'agent_status'
    name = 'Agent 在线状态'
    category = 'agent'
    severity = 'critical'
    description = '主 Agent 和所有子 Agent 的健康状态'

    def check(self) -> CheckResult:
        start = time.time()
        try:
            from agent_matrix.models import get_db
            with get_db() as conn:
                agents = conn.execute(
                    'SELECT id, name, status, last_heartbeat FROM agent_matrix'
                ).fetchall()
            elapsed = int((time.time() - start) * 1000)
            online = sum(1 for a in agents if a.get('status') == 'online')
            total = len(agents)
            if online == total:
                return CheckResult('passed', elapsed, f'{online}/{total} Agent 在线')
            return CheckResult('warning', elapsed, f'{online}/{total} Agent 在线（{total-online} 离线）',
                               {'agents': [dict(a) for a in agents]})
        except Exception as e:
            return CheckResult('error', 0, str(e))
```

### 检查内容工厂采集通道

```python
@register('content_pipeline')
class ContentPipelineCheck(BaseHealthCheck):
    check_key = 'content_pipeline'
    name = '内容流水线检查'
    category = 'cms'
    severity = 'warning'
    description = '内容工厂采集通道状态、加工队列深度'

    def check(self) -> CheckResult:
        start = time.time()
        try:
            from models import get_db
            with get_db() as conn:
                channels = conn.execute(
                    'SELECT name, status, last_run_at FROM collection_channels WHERE is_active=1'
                ).fetchall()
                queue_depth = conn.execute(
                    "SELECT COUNT(*) as c FROM content_items WHERE status='pending'"
                ).fetchone()['c']
            elapsed = int((time.time() - start) * 1000)
            return CheckResult('passed', elapsed,
                               f'{len(channels)} 通道 | 队列深度 {queue_depth}',
                               {'channels': [dict(c) for c in channels], 'queue_depth': queue_depth})
        except Exception as e:
            return CheckResult('error', 0, str(e))
```

### 检查特定 Workflow 最近执行状态

```python
@register('workflow_recent')
class WorkflowRecentCheck(BaseHealthCheck):
    check_key = 'workflow_recent'
    name = '最近工作流状态'
    category = 'workflow'
    severity = 'warning'
    description = '检查某个特定 Workflow 的最近执行状态'
    config_defaults = {'workflow_id': 1, 'max_failures': 3}

    def check(self) -> CheckResult:
        start = time.time()
        try:
            from orchestrator import models as om
            wf_id = self.config.get('workflow_id', 1)
            with om.get_db() as conn:
                recent = conn.execute(
                    "SELECT id, status, started_at, finished_at FROM workflow_instances "
                    "WHERE workflow_id=? ORDER BY started_at DESC LIMIT 10",
                    (wf_id,)
                ).fetchall()
                failures = sum(1 for r in recent if r['status'] == 'failed')
            elapsed = int((time.time() - start) * 1000)
            threshold = self.config.get('max_failures', 3)
            if failures > threshold:
                return CheckResult('warning', elapsed,
                                   f'最近 {len(recent)} 次执行中 {failures} 次失败（阈值 {threshold}）',
                                   {'instances': [dict(r) for r in recent]})
            return CheckResult('passed', elapsed,
                               f'最近 {len(recent)} 次执行正常')
        except Exception as e:
            return CheckResult('error', 0, str(e))
```

### 检查 Redis 连接池状态

```python
@register('redis_pool')
class RedisPoolHealthCheck(BaseHealthCheck):
    check_key = 'redis_pool'
    name = 'Redis 连接池状态'
    category = 'system'
    severity = 'warning'
    description = 'Redis 连接池使用情况、内存、命中率'
    config_defaults = {'host': '127.0.0.1', 'port': 6379, 'max_clients_warn': 100}

    def check(self) -> CheckResult:
        start = time.time()
        try:
            import redis
            r = redis.Redis(host=self.config['host'], port=self.config['port'],
                           socket_timeout=3, decode_responses=True)
            info = r.info()
            elapsed = int((time.time() - start) * 1000)
            detail = {
                'connected_clients': info.get('connected_clients'),
                'used_memory_human': info.get('used_memory_human'),
                'uptime_in_days': info.get('uptime_in_days'),
                'keyspace_hit_ratio': round(
                    info.get('keyspace_hits', 0) * 100 / max(
                        info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1), 1), 2
                ),
            }
            clients = detail['connected_clients']
            threshold = self.config.get('max_clients_warn', 100)
            if clients > threshold:
                return CheckResult('warning', elapsed,
                                   f'连接数 {clients} 超过阈值 {threshold}', detail)
            return CheckResult('passed', elapsed,
                               f'Redis 正常 | {clients} 连接 | {detail["used_memory_human"]}', detail)
        except Exception as e:
            return CheckResult('error', 0, str(e))
```

---

## 部署验证

```bash
# 1. 部署代码到服务器
cd ~/projects/VeroRun
scp -r easykai_health/ your-user@your-server:/path/to/deployment/

# 2. 重启 admin 服务
ssh your-user@your-server "cd /path/to/deployment && find easykai_health -name __pycache__ -exec rm -rf {} + && fuser -k 8084/tcp && sleep 1 && cd admin && python3 -B app.py 8084 &"

# 3. 验证新检查项可见
# 访问你的管理后台 → 健康巡检 → ⚙️ 检查项配置
# 在「📦 可添加的检查器」中点击「＋添加」
```

---

## 注意事项

1. **check_key 必须唯一** — 与 DB 中 health_checks.check_key 对应
2. **部署后需重启** — 新注册的检查器类在 admin 服务重启后才生效
3. **DB 中已有记录** — 如果 check_key 已存在于 health_checks 表，点击「＋添加」会提示已存在
4. **检查器不可用时** — 如果 @register 注册了但 Python 中无对应实现，执行时会标记为 warning
5. **异步执行** — 手动巡检是异步的，点击「⚡ 立即巡检」后需等待几秒刷新
