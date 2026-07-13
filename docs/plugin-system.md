# 插件系统开发指南（Plugin System API Reference）

> VeroRun 维洛智能建站系统通用插件框架  
> 版本：v1.0 | 更新日期：2026-07-07

---

## 目录

1. [概述](#1-概述)
2. [快速开始](#2-快速开始)
3. [插件基类 API](#3-插件基类-api)
4. [事件钩子系统](#4-事件钩子系统)
5. [插件注册表](#5-插件注册表)
6. [插件元数据](#6-插件元数据)
7. [集成示例](#7-集成示例)
8. [最佳实践](#8-最佳实践)

---

## 1. 概述

### 1.1 设计理念

插件系统遵循 **声明式注册 + 生命周期管理** 的设计模式：

- **零侵入**：不修改现有模块代码即可扩展功能
- **失败隔离**：单个插件崩溃不影响主系统和其它插件
- **依赖管理**：支持插件间依赖声明和递归加载
- **i18n 原生**：所有用户可见字符串使用 `_()` 包裹

### 1.2 插件能力矩阵

| 能力 | 实现方法 | 说明 |
|------|---------|------|
| **路由/API** | `register_routes()` | 返回 Flask Blueprint 列表 |
| **定时任务** | `register_jobs()` | 返回 APScheduler job 配置 |
| **DAG 工作流节点** | `register_dag_nodes()` | 注册到 WorkflowEngine |
| **健康检查** | `register_health_checks()` | 注册到 health_check |
| **事件响应** | `get_event_handlers()` | 订阅系统事件 |
| **数据库** | 直接使用 `get_db()` | 复用 auth-center SQLite |
| **认证** | 复用 `jwt_service` | JWT SSO 跨子域 |

### 1.3 目录结构

```
plugins/
├── __init__.py         # 入口：load_plugins()
├── base.py             # BasePlugin 基类
├── registry.py         # PluginRegistry 注册表
├── hooks.py            # EventBus 事件总线
└── your_plugin/        # 你的插件目录
    ├── __init__.py     # 插件 Python 包（必须包含 Plugin 类）
    ├── plugin.json     # 插件元数据声明
    ├── routes.py       # 可选：路由定义
    └── tasks.py        # 可选：定时任务
```

---

## 2. 快速开始

### 2.1 创建插件

**步骤 1**：在 `plugins/` 下创建插件目录 `demo_hello/`

**步骤 2**：创建 `plugins/demo_hello/__init__.py`：

```python
from flask import Blueprint, jsonify
from plugins.base import BasePlugin
from plugins.hooks import EventName
from i18n import _

bp = Blueprint('demo_hello', __name__)

@bp.route('/')
def hello():
    return jsonify({'message': _('你好，这是示例插件！')})

class DemoHelloPlugin(BasePlugin):
    name = 'demo_hello'
    version = '0.1.0'
    description = '示例演示插件'
    author = 'EasyKai'

    def register_routes(self):
        return [bp]

    def get_event_handlers(self):
        def on_user_login(**kwargs):
            self.log(f"用户登录: {kwargs.get('username', '?')}")
        return {EventName.USER_LOGIN: on_user_login}
```

**步骤 3**：创建 `plugins/demo_hello/plugin.json`：

```json
{
    "name": "demo_hello",
    "version": "0.1.0",
    "description": "示例演示插件",
    "author": "EasyKai",
    "depends_on": [],
    "enabled": true,
    "config": {
        "greeting": "Hello World"
    }
}
```

**步骤 4**：重启服务，插件自动加载。访问 `/plugin/demo_hello/` 测试。

### 2.2 系统启动流程

```
Platform/Admin 启动
    └── register_auth(app)         # auth_blueprint.py
        └── load_plugins(app)       # plugins/__init__.py
            ├── PluginRegistry.load_all()
            │   ├── discover()          # 扫描 plugins/ 目录
            │   ├── load(plugin_name)   # 逐个加载
            │   │   ├── 读取 plugin.json
            │   │   ├── importlib 加载模块
            │   │   ├── 查找 BasePlugin 子类
            │   │   └── 实例化 + 校验
            │   └── enable(plugin_name) # 逐个启用
            │       ├── 检查依赖
            │       ├── on_enable()
            │       └── 注册事件钩子
            └── mount_all(app)         # 挂载 Blueprint
```

---

## 3. 插件基类 API

### 3.1 BasePlugin 类

`plugins/base.py` — 所有插件必须继承的抽象基类。

#### 3.1.1 必须设置的元数据

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | str | 插件唯一标识（与目录名一致） |
| `version` | str | 版本号，格式 `0.1.0` |
| `description` | str | 插件功能描述 |
| `author` | str | 插件作者 |
| `depends_on` | list[str] | 依赖的其他插件 name 列表 |
| `config_schema` | dict | 配置项定义（可选） |

#### 3.1.2 生命周期方法

| 方法 | 调用时机 | 返回值 |
|------|---------|--------|
| `on_install(registry)` | 插件首次加载 | `True` 成功 |
| `on_enable(registry)` | 插件启用时 | `True` 成功 |
| `on_disable(registry)` | 插件禁用时 | `True` 成功 |
| `on_uninstall(registry)` | 插件卸载时 | `True` 成功 |

#### 3.1.3 功能注册方法

| 方法 | 返回类型 | 说明 |
|------|---------|------|
| `register_routes()` | `List[Blueprint]` | Flask Blueprint 列表 |
| `register_jobs()` | `List[dict]` | APScheduler job 配置 |
| `register_dag_nodes()` | `Dict[str, Any]` | 节点类型 → 处理器 |
| `register_health_checks()` | `List[dict]` | 健康检查项 |
| `get_event_handlers()` | `Dict[str, Any]` | 事件名 → 处理器 |

#### 3.1.4 工具方法

| 方法 | 说明 |
|------|------|
| `get_config_value(key, default)` | 获取插件配置值 |
| `log(message, level)` | 统一日志输出 |
| `validate_config()` | 校验插件配置 |
| `t(text, locale=None)` | 插件独立 i18n 翻译（与系统 `_()` 隔离） |

---

### 3.2 register_jobs() 配置格式

每条 job 格式：

```python
{
    'job_id': 'my_job_id',           # 必填，全局唯一
    'func': my_task_function,        # 必填，任务函数
    'trigger': 'cron',               # 必填：cron | interval | date
    'kwargs': {                      # trigger 参数
        'hour': 2,                   # cron: hour, minute, day...
        'minute': 0,
        # interval: {'seconds': 3600}
        # date: {'run_date': datetime(2026, 7, 1)}
    },
    'priority': 'normal',            # critical | high | normal | low
    'max_retries': 2,                # 失败重试次数
}
```

### 3.3 register_health_checks() 配置格式

每条检查格式：

```python
{
    'check_id': 'my_check_id',       # 必填
    'name': '检查项名称',             # 必填（中文源文本，支持 i18n）
    'category': 'database',          # database | api | custom
    'func': check_function,          # 必填，返回 {'status': 'ok', 'msg': '...'}
    'severity': 'warning',           # warning | critical
    'interval_seconds': 300,         # 检查间隔
}
```

---

## 4. 事件钩子系统

### 4.1 预定义事件

`plugins/hooks.py` — EventName 类：

| 事件常量 | 触发时机 |
|---------|---------|
| `APP_READY` | 应用启动就绪 |
| `APP_SHUTDOWN` | 应用即将关闭 |
| `USER_REGISTERED` | 用户注册完成 |
| `USER_LOGIN` | 用户登录成功 |
| `USER_LOGOUT` | 用户退出登录 |
| `USER_UPDATED` | 用户信息更新 |
| `USER_DELETED` | 用户被删除 |
| `ORDER_CREATED` | 订单创建 |
| `ORDER_PAID` | 订单支付完成 |
| `ORDER_REFUNDED` | 订单退款完成 |
| `ORDER_CANCELLED` | 订单取消 |
| `ORDER_SHIPPED` | 订单发货 |
| `ORDER_COMPLETED` | 订单完成 |
| `SUB_CREATED` | 订阅创建 |
| `SUB_RENEWED` | 订阅续费 |
| `SUB_EXPIRED` | 订阅过期 |
| `SUB_CANCELLED` | 订阅取消 |
| `CMS_CONTENT_PUBLISHED` | CMS 内容发布 |
| `CMS_CONTENT_UPDATED` | CMS 内容更新 |
| `CMS_CONTENT_DELETED` | CMS 内容删除 |
| `SCHEDULER_JOB_STARTED` | 定时任务开始 |
| `SCHEDULER_JOB_COMPLETED` | 定时任务完成 |
| `SCHEDULER_JOB_FAILED` | 定时任务失败 |
| `HEALTH_CHECK_PASSED` | 健康检查通过 |
| `HEALTH_CHECK_WARNING` | 健康检查警告 |
| `HEALTH_CHECK_ERROR` | 健康检查错误 |
| `PLUGIN_INSTALLED` | 插件安装 |
| `PLUGIN_ENABLED` | 插件启用 |
| `PLUGIN_DISABLED` | 插件禁用 |
| `PLUGIN_UNINSTALLED` | 插件卸载 |

### 4.2 使用事件总线

```python
from plugins.hooks import EventName, get_event_bus

bus = get_event_bus()

# 订阅事件
def on_user_login(**kwargs):
    user_id = kwargs.get('user_id')
    print(f'User {user_id} logged in')

bus.on(EventName.USER_LOGIN, on_user_login)

# 触发事件
bus.emit(EventName.USER_LOGIN, user_id=123, username='demo')
```

### 4.3 在插件中注册事件

```python
class MyPlugin(BasePlugin):
    def get_event_handlers(self):
        return {
            EventName.ORDER_PAID: self.on_order_paid,
            EventName.USER_REGISTERED: self.on_user_registered,
        }
```

---

## 5. 插件注册表

### 5.1 PluginRegistry 主要方法

```python
from plugins import get_plugin_registry

registry = get_plugin_registry()

# 查询
registry.get('plugin_name')           # 获取插件实例
registry.is_enabled('plugin_name')    # 检查是否启用
registry.count()                       # 已加载数量
registry.count_enabled()               # 已启用数量
registry.list_all()                    # 列出所有插件信息
registry.get_info('plugin_name')      # 获取插件详细信息

# 管理
registry.load('plugin_name')           # 加载插件
registry.enable('plugin_name')         # 启用插件
registry.disable('plugin_name')        # 禁用插件
registry.install('plugin_name')        # 安装插件
registry.uninstall('plugin_name')      # 卸载插件

# 发现与挂载
registry.discover()                    # 扫描插件目录，发现可用插件
registry.mount_all(app)                # 挂载所有启用插件的 Blueprint 到 Flask app
```

### 5.2 统一入口函数

```python
from plugins import (
    load_plugins,          # 加载并挂载到 Flask app
    get_plugin_registry,   # 获取全局 PluginRegistry 单例
)
```

---

## 6. 插件元数据

### 6.1 plugin.json 字段说明

```json
{
    "name": "插件唯一标识",
    "version": "0.1.0",
    "description": "插件功能描述（支持 i18n）",
    "author": "作者",
    "depends_on": ["other_plugin"],
    "enabled": true,
    "config": {
        "key": "value"
    }
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 唯一标识，与目录名一致 |
| `version` | 是 | 语义化版本号 |
| `description` | 是 | 功能描述 |
| `author` | 是 | 插件作者 |
| `depends_on` | 否 | 依赖插件列表 |
| `enabled` | 否 | 是否启用，默认 `true` |
| `config` | 否 | 插件自定义配置 |

### 6.2 i18n 要求

所有 `plugin.json` 中面向用户的描述字段使用中文源文本：

```json
{
    "description": "示例演示插件 — 展示插件系统基本用法"
}
```

英文翻译在 `i18n/en.yml` 中维护。

---

## 7. 集成示例

### 7.1 带定时任务的插件

```python
from plugins.base import BasePlugin
from i18n import _

def daily_report():
    print(_('每日报告生成中...'))

class ReportPlugin(BasePlugin):
    name = 'report'
    version = '0.1.0'
    description = '每日报告自动生成'
    author = 'EasyKai'

    def register_jobs(self):
        return [{
            'job_id': 'report_daily',
            'func': daily_report,
            'trigger': 'cron',
            'kwargs': {'hour': 8, 'minute': 0},
            'priority': 'normal',
            'max_retries': 2,
        }]
```

### 7.2 带健康检查的插件

```python
from plugins.base import BasePlugin
from i18n import _

def check_external_api():
    try:
        # 检查外部 API 可用性
        return {'status': 'ok', 'msg': _('外部 API 连接正常')}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}

class MonitorPlugin(BasePlugin):
    name = 'monitor'
    version = '0.1.0'
    description = '外部服务监控'
    author = 'EasyKai'

    def register_health_checks(self):
        return [{
            'check_id': 'external_api_status',
            'name': '外部 API 连通性检查',
            'category': 'api',
            'func': check_external_api,
            'severity': 'critical',
            'interval_seconds': 120,
        }]
```

### 7.3 带 DAG 节点的插件

```python
from plugins.base import BasePlugin

def my_dag_handler(ctx):
    print(f"Processing DAG node with context: {ctx}")
    return {'status': 'completed'}

class WorkflowPlugin(BasePlugin):
    name = 'custom_workflow'
    version = '0.1.0'
    description = '自定义工作流节点'
    author = 'EasyKai'

    def register_dag_nodes(self):
        return {'my_custom_node': my_dag_handler}
```

---

## 8. 最佳实践

### 8.1 错误处理

```python
class MyPlugin(BasePlugin):
    def on_enable(self, registry):
        try:
            # 初始化操作
            init_something()
            return True
        except Exception as e:
            self.log(f'启用失败: {e}', 'error')
            return False
```

### 8.2 i18n 规范

插件使用 **自有翻译**，与系统 `_()` 完全隔离。

#### 翻译文件

放在插件目录的 `i18n/` 下，格式与系统 YAML 一致：

```
plugins/your_plugin/
└── i18n/
    ├── zh-CN.yml    # 中文翻译
    └── en.yml       # 英文翻译
```

#### 使用 `self.t()` 方法

```python
class MyPlugin(BasePlugin):
    def my_handler(self):
        # 使用 self.t() 翻译插件自己的文本
        msg = self.t('插件未找到')
        return jsonify({'error': msg})
```

`self.t()` 自动跟随系统 `DEPLOY_LANG`，无需手动传 locale。

#### 目录结构规范

```
plugins/your_plugin/
├── __init__.py       # BasePlugin 子类
├── plugin.json       # 元数据
├── i18n/             # 插件自有翻译（与系统 _() 隔离）
│   ├── zh-CN.yml
│   └── en.yml
├── README.zh-CN.md   # 中文文档
└── README.en.md      # 英文文档
```

### 8.3 安全规范

- 不要在 `plugin.json` 中硬编码密钥
- 使用环境变量存储敏感配置
- 插件路由使用 `/plugin/{name}/` 前缀，避免路由冲突

```python
# 正确的配置方式
def on_enable(self, registry):
    api_key = os.environ.get('MY_PLUGIN_API_KEY', '')
```

### 8.4 调试

```python
# 查看已加载插件
from plugins import get_plugin_registry
registry = get_plugin_registry()
for info in registry.list_all():
    print(f"  - {info['name']} v{info['version']} [{info['status']}]")
```

---

## 9. Social Media Mini-Program Plugin Standard

> New in v2026.07 — Standard for plugins that generate social media mini-programs.

### 9.1 Directory Structure

```
plugins/dev_accounts/
├── __init__.py       # DevAccountsPlugin(BasePlugin)
├── plugin.json       # Metadata
├── routes.py         # Admin CRUD endpoints
├── models.py         # Database operations
├── crypto.py         # AES-256 credential encryption
├── i18n/             # Internationalization
│   ├── zh-CN.yml
│   └── en.yml
└── README.md
```

### 9.2 plugin.json Fields

```json
{
    "name": "Developer Accounts",
    "identifier": "dev_accounts",
    "version": "1.0.0",
    "description": "Manage developer accounts for social media platforms",
    "author": "VeroRun",
    "category": "admin",
    "permissions": ["admin"],
    "admin": {
        "menu": {
            "title": "Developer Accounts",
            "icon": "key",
            "url": "/admin/dev-accounts"
        }
    }
}
```

### 9.3 Plugin Class

```python
from plugins.base import BasePlugin

class DevAccountsPlugin(BasePlugin):
    """Developer accounts management plugin."""

    def on_install(self, registry):
        """Create dev_accounts table on first install."""
        self._create_table()

    def on_enable(self, registry):
        """Register admin routes."""
        from .routes import dev_accounts_bp
        registry.app.register_blueprint(dev_accounts_bp)

    def _create_table(self):
        """Create the encrypted credentials table."""
        with self._get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dev_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    app_id TEXT DEFAULT '',
                    app_secret TEXT DEFAULT '',
                    bot_token TEXT DEFAULT '',
                    channel_id TEXT DEFAULT '',
                    channel_secret TEXT DEFAULT '',
                    access_token TEXT DEFAULT '',
                    extra_config TEXT DEFAULT '{}',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dev_accounts_platform
                ON dev_accounts(platform)
            """)
            conn.commit()
```

### 9.4 Security: Credential Encryption

```python
# plugins/dev_accounts/crypto.py
from cryptography.fernet import Fernet
import os

def _get_key():
    key = os.environ.get('DEV_ACCOUNTS_ENCRYPTION_KEY', '')
    if not key:
        raise RuntimeError('DEV_ACCOUNTS_ENCRYPTION_KEY not set')
    return key.encode() if isinstance(key, str) else key

def encrypt(value):
    if not value:
        return ''
    f = Fernet(_get_key())
    return f.encrypt(value.encode()).decode()

def decrypt(value):
    if not value:
        return ''
    f = Fernet(_get_key())
    return f.decrypt(value.encode()).decode()

def mask(value):
    """Show only last 4 characters for display."""
    if not value or len(value) <= 4:
        return '****'
    return '****' + value[-4:]
```

### 9.5 Mini-App Generator Plugin Interface

For plugins that generate mini-program code:

```python
class MiniAppGeneratorPlugin(BasePlugin):
    """Base class for mini-app generator plugins."""

    def register_mini_apps(self):
        """Return list of supported platforms."""
        return [
            {
                'platform': 'douyin',
                'name': 'Douyin / Toutiao',
                'type': 'native',
                'generator': 'site_builder.mini_app.generators.douyin.DouyinGenerator',
            },
        ]

    def on_enable(self, registry):
        """Register mini-app platforms with Site_builder."""
        platforms = self.register_mini_apps()
        for p in platforms:
            registry.register_mini_app_platform(p)
```

### 9.6 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DEV_ACCOUNTS_ENCRYPTION_KEY` | Yes | 32-byte Fernet key for credential encryption |
| `DEPLOY_DOMAIN` | Yes | System domain for API URLs |
| `DEPLOY_MARKET` | Yes | Market identifier (cn/international) |

Generate a key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```