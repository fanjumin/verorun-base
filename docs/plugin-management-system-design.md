# 插件管理模块 — 完整设计方案（含付费生态）

生成日期：2026-07-07
基于对 WordPress、Jenkins、VS Code、Flask、Drupal 等主流系统的深度调研

---

## 一、主流系统插件架构横向对比

### 1.1 核心机制对比

| 维度 | WordPress | Jenkins | VS Code | Flask/Drupal | 本方案 |
|------|-----------|---------|---------|--------------|--------|
| **发现机制** | 文件扫描（plugins 目录） | 安装目录扫描 + Update Center | `package.json` 声明 `activationEvents` | Blueprint 显式注册 / Annotation 扫描 | **info.json 声明 + 目录扫描** |
| **生命周期** | activate → deactivate → uninstall | install → load → start → stop | lazy activation（事件触发） | init_app → 注册 Blueprint | **5 状态：INSTALLED→DISABLED→ENABLED→ACTIVE→UNINSTALLED** |
| **钩子系统** | Actions + Filters（双钩子） | Extension Point（@Extension 注解） | 贡献点（contributes）+ API | 事件系统（signal） | **Action + Filter 双钩子 + 事件总线** |
| **隔离性** | 函数命名空间（弱） | ClassLoader 隔离（强） | Extension Host 进程隔离（最强） | Python 模块隔离（中） | **Python 模块级隔离 + 独立数据库** |
| **依赖管理** | 无原生支持 | `Plugin-Dependencies` 声明式 | `extensionDependencies` | 无 | **声明式依赖 + 版本范围 + 循环检测** |
| **配置UI** | 设置页面 + Settings API | 系统配置页面 | settings.json / 配置界面 | app.config | **统一配置面板 + JSON Schema** |
| **热加载** | 插件激活需刷新 | 需重启 Jenkins | 需要重新加载窗口 | 开发模式支持 reload | **开发模式热加载，生产环境需重启** |
| **权限模型** | 角色权限（Capabilities） | 全局权限系统 | 无独立权限 | 无 | **插件权限声明 + 管理员审核** |
| **付费生态** | 无原生付费（靠第三方市场） | 免费生态 | Marketplace 购买 + IAP | 免费 | **统一 License 引擎 + 订阅管理 + 插件商店** |

### 1.2 各系统核心设计借鉴

| 系统 | 可借鉴的点 |
|------|-----------|
| **WordPress** | Hook 系统（Action/Filter）是扩展性最强的设计，插件头声明元信息简单有效 |
| **Jenkins** | ClassLoader 隔离 + 声明式依赖管理 + Update Center 是最完整的企业级方案 |
| **VS Code** | Lazy Activation（按需激活）+ 贡献点声明 + 进程隔离是性能最佳实践 |
| **Flask** | Blueprint 路由分组 + `init_app` 工厂模式 + `current_app` 上下文访问 |
| **Drupal** | Plugin Manager + 4 种发现机制（Annotation/YAML/Hook/Static）+ Plugin Interface |
| **Flask-Plugins** | `info.json` 元信息 + `__plugin__` 变量 + DISABLED 文件标记禁用 |

---

## 二、整体架构设计

### 2.1 架构分层

```
┌─────────────────────────────────────────────────┐
│                  应用层 (App)                      │
│  ┌─────────────┐ ┌──────────┐ ┌──────────────┐  │
│  │  PluginManager │ │  EventBus  │ │  HookRegistry  │  │
│  │  (核心引擎)    │ │  (事件总线) │ │  (钩子注册表)   │  │
│  └──────┬──────┘ └────┬─────┘ └──────┬───────┘  │
├─────────┼──────────────┼──────────────┼─────────────┤
│         ▼              ▼              ▼              │
│  ┌────────────────────────────────────────────┐     │
│  │          插件运行时 (Plugin Runtime)          │     │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────────┐  │     │
│  │  │ ali_api  │ │ coupons │ │ reviews       │  │     │
│  │  │ plugin   │ │ plugin  │ │ plugin        │  │     │
│  │  └─────────┘ └─────────┘ └──────────────┘  │     │
│  └────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────┤
│                  数据层 (Data)                        │
│  ┌──────────────┐ ┌──────────────────────────┐      │
│  │ plugin_registry│ │ 各插件独立数据库             │      │
│  │ (主库元数据表)   │ │ (plugins/*/*.db)           │      │
│  └──────────────┘ └──────────────────────────┘      │
└─────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

```
用户操作                         系统事件
   │                                │
   ▼                                ▼
┌─────────────┐           ┌──────────────────┐
│ 管理 API     │           │ EventBus 事件分发   │
│ (routes.py)  │           │ (钩子系统)         │
└──────┬──────┘           └────────┬─────────┘
       │                           │
       ▼                           ▼
┌──────────────────────────────────────────┐
│            PluginManager                   │
│  ┌─────────┐ ┌────────┐ ┌─────────────┐  │
│  │ 发现扫描  │ │ 生命周期 │ │ 依赖解析      │  │
│  └─────────┘ └────────┘ └─────────────┘  │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  plugin_registry (持久化状态)               │
└──────────────────────────────────────────┘
```

### 2.3 插件生命周期状态机

```
         ┌─────────┐
         │ UNKNOWN │  (磁盘发现但未注册)
         └────┬────┘
              │ discover()
              ▼
         ┌──────────┐
         │ INSTALLED │  (首次发现，写入 registry)
         └─────┬────┘
               │ enable()
          ┌────┴────┐
          │         │
          ▼         ▼
    ┌────────┐ ┌─────────┐
    │ ENABLED │ │ DISABLED│  (用户手动禁用)
    └───┬────┘ └─────────┘
        │                 ▲
        │ activate()      │ disable()
        ▼                 │
    ┌────────┐            │
    │ ACTIVE │────────────┘
    └───┬────┘  (运行中禁用的请)
        │
        │ uninstall()
        ▼
    ┌───────────┐
    │ UNINSTALLED│  (清理数据库 + 文件标记)
    └───────────┘
```

---

## 三、模块详细设计

### 3.1 目录结构

```
plugin_manager/                     # 新增核心模块
├── __init__.py                     # PluginManager 类
├── models.py                       # PluginRegistry 模型
├── routes.py                       # 管理 API
├── hooks.py                        # 钩子系统 (HookRegistry)
├── events.py                       # 事件总线 (EventBus)
├── exceptions.py                   # 自定义异常
└── templates/                      # 后台管理 UI
    ├── plugin_list.html
    ├── plugin_detail.html
    ├── plugin_settings.html
    └── plugin_market.html

plugins/<name>/                     # 每个插件标准化
├── plugin.json                     # 元信息声明（必需）
├── __init__.py                     # 插件入口（必需）
├── __plugin__.py                   # Plugin 子类（可选，自动发现）
├── models.py                       # 数据库模型
├── routes.py / views.py            # 路由/视图
├── hooks.py                        # 钩子注册
├── static/                         # 静态资源
└── templates/                      # 模板
```

### 3.2 plugin.json 元信息规范

```json
{
  "identifier": "coupons",
  "name": "优惠券管理",
  "version": "1.0.0",
  "min_app_version": "1.0.0",
  "author": "EasyKai",
  "license": "MIT",
  "description": "优惠券生成、分发和核销功能",
  "homepage": "https://easykai.cn/plugins/coupons",

  "dependencies": {
    "ali_api": ">=1.0.0"
  },

  "hooks": {
    "provides": [
      "coupons.validate",
      "coupons.redeem"
    ],
    "listens": [
      "order.paid",
      "user.registered"
    ]
  },

  "permissions": [
    "db:read:coupons",
    "db:write:coupons",
    "api:admin:coupons"
  ],

  "settings_schema": {
    "type": "object",
    "properties": {
      "default_discount": {
        "type": "number",
        "title": "默认折扣率",
        "default": 0.9
      },
      "max_per_user": {
        "type": "integer",
        "title": "每人最大领取数",
        "default": 3
      }
    }
  }
}
```

### 3.3 核心类设计

#### PluginManager（核心引擎）

```python
class PluginManager:
    """
    插件管理器的核心类，职责：
    - 扫描 plugins/ 目录发现插件
    - 管理插件生命周期（install/enable/disable/uninstall）
    - 解析依赖并检测循环依赖
    - 维护 plugin_registry 持久化状态
    - 提供插件实例缓存
    """

    def __init__(self, app=None):
        self.app = app
        self.plugins_dir = None        # plugins/ 目录路径
        self._registry = {}            # {identifier: PluginInfo}
        self._instances = {}           # {identifier: PluginInstance}
        self._hook_registry = HookRegistry()
        self._event_bus = EventBus()
        self._discovery = PluginDiscovery()

    def init_app(self, app):
        """工厂模式初始化，绑定到 Flask 应用"""
        self.plugins_dir = os.path.join(app.root_path, 'plugins')
        # 注册内置管理路由
        from . import routes
        app.register_blueprint(routes.bp, url_prefix='/admin/plugins')
        # 扫描已启用插件
        self._load_registry()
        self._activate_enabled()

    # --- 生命周期方法 ---

    def discover(self) -> list[PluginInfo]:
        """扫描 plugins/ 目录，返回未注册的新插件列表"""

    def install(self, identifier: str) -> PluginInfo:
        """安装：写入 registry，状态 → INSTALLED"""

    def enable(self, identifier: str) -> PluginInfo:
        """启用：解析依赖，执行 setup()，状态 → ENABLED"""

    def activate(self, identifier: str) -> PluginInfo:
        """激活：加载插件模块，注册路由/钩子，状态 → ACTIVE"""

    def disable(self, identifier: str) -> PluginInfo:
        """禁用：反注册路由/钩子，状态 → DISABLED"""

    def uninstall(self, identifier: str) -> None:
        """卸载：清理数据库表，删除 registry 记录"""

    # --- 查询方法 ---

    def get_plugin(self, identifier: str) -> PluginInfo:
    def list_plugins(self, status=None) -> list[PluginInfo]:
    def is_enabled(self, identifier: str) -> bool:
    def is_active(self, identifier: str) -> bool:

    # --- 钩子/事件方法 ---

    def register_hook(self, identifier: str, hook_name: str, callback):
    def trigger_action(self, hook_name: str, **kwargs):
    def apply_filter(self, hook_name: str, value, **kwargs):

    # --- 内部方法 ---

    def _resolve_dependencies(self, identifier: str) -> list[str]:
        """拓扑排序解析依赖，检测循环依赖"""

    def _load_plugin_module(self, identifier: str):
        """动态 import 插件模块"""

    def _unload_plugin_module(self, identifier: str):
        """从 sys.modules 中移除"""
```

#### PluginInfo（插件元信息）

```python
@dataclass
class PluginInfo:
    identifier: str           # 唯一标识（如 "coupons"）
    name: str                 # 显示名称
    version: str              # 版本号（semver）
    min_app_version: str      # 最低应用版本
    author: str
    description: str
    path: str                 # 插件目录绝对路径
    status: PluginStatus      # 当前状态枚举
    dependencies: dict        # {identifier: version_spec}
    provides_hooks: list      # 本插件提供的钩子列表
    listens_hooks: list       # 本插件监听的钩子列表
    permissions: list         # 权限声明
    settings_schema: dict     # 配置项 JSON Schema
    installed_at: datetime    # 安装时间
    updated_at: datetime      # 最后更新时间
    config: dict              # 运行时配置（持久化）
```

#### BasePlugin（插件基类）

```python
class BasePlugin:
    """
    所有插件应继承的基类，提供标准生命周期方法。
    插件不必须继承此类（鸭子类型），但建议继承以利用默认实现。
    """

    # 插件引用（由 PluginManager 注入）
    plugin_info: PluginInfo = None
    manager: 'PluginManager' = None

    def setup(self):
        """
        [ENABLED 阶段调用] 插件初始化
        - 创建数据库表
        - 注册钩子
        - 初始化配置
        """
        pass

    def activate(self):
        """
        [ACTIVE 阶段调用] 插件激活
        - 注册路由（Blueprint）
        - 注册事件监听
        - 启动后台任务（APScheduler）
        """
        pass

    def deactivate(self):
        """
        [DISABLED 阶段调用] 插件停用
        - 移除路由
        - 取消事件监听
        - 停止后台任务
        """
        pass

    def get_config(self, key=None, default=None):
        """读取插件配置"""

    def set_config(self, key, value):
        """保存插件配置（持久化到 registry.config）"""
```

### 3.4 钩子系统设计（Action + Filter）

借鉴 WordPress 的双钩子模式，同时支持 Action（执行操作）和 Filter（修改数据）：

```python
class HookRegistry:
    """
    钩子注册表，管理所有插件的 Action 和 Filter 注册。
    """

    def add_action(self, hook_name: str, callback, priority: int = 10):
        """注册一个 Action 钩子"""

    def remove_action(self, hook_name: str, callback, priority: int = 10):
        """移除 Action 钩子"""

    def do_action(self, hook_name: str, *args, **kwargs):
        """触发 Action 钩子，按 priority 顺序执行所有回调"""

    def add_filter(self, hook_name: str, callback, priority: int = 10):
        """注册一个 Filter 钩子"""

    def remove_filter(self, hook_name: str, callback, priority: int = 10):
        """移除 Filter 钩子"""

    def apply_filters(self, hook_name: str, value, *args, **kwargs):
        """触发 Filter 钩子，每个回调返回值作为下一个的输入"""
```

**预定义的系统钩子点**：

| 钩子名称 | 类型 | 触发时机 | 参数 |
|---------|------|---------|------|
| `app.before_request` | Action | 每个请求前 | `request` |
| `app.after_request` | Filter | 每个请求后 | `response` |
| `app.template_context` | Filter | 模板渲染前 | `context` dict |
| `plugin.installed` | Action | 插件安装后 | `plugin_id` |
| `plugin.enabled` | Action | 插件启用后 | `plugin_id` |
| `plugin.disabled` | Action | 插件禁用后 | `plugin_id` |
| `plugin.uninstalled` | Action | 插件卸载后 | `plugin_id` |
| `order.created` | Action | 订单创建 | `order` |
| `order.paid` | Action | 订单支付 | `order` |
| `user.registered` | Action | 用户注册 | `user` |
| `page.render` | Filter | 页面渲染前 | `html` |

### 3.5 事件总线设计（补充钩子系统）

钩子系统是同步的，事件总线支持异步/延迟处理：

```python
class EventBus:
    """
    事件总线，用于插件间通信。
    与钩子的区别：事件是"发布-订阅"模式，可以有多个订阅者，
    但不修改数据，也不保证执行顺序。
    """

    def publish(self, event_name: str, data: dict = None):
        """发布事件（异步，入队列）"""

    def subscribe(self, event_name: str, callback):
        """订阅事件"""

    def unsubscribe(self, event_name: str, callback):
        """取消订阅"""

    def on(self, event_name: str):
        """装饰器语法糖"""
```

### 3.6 数据库模型

```python
class PluginRegistry(Model):
    """主库中的插件注册表"""

    __tablename__ = 'plugin_registry'

    id = Column(Integer, primary_key=True)
    identifier = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    version = Column(String(32), nullable=False)

    # JSON 字段：存储完整的 plugin.json 内容
    metadata = Column(Text, nullable=False)

    # 当前状态
    status = Column(String(16), nullable=False, default='installed')
    # installed | enabled | active | disabled | uninstalled

    # 配置（持久化的插件设置）
    config = Column(Text, nullable=True)

    # 时间戳
    installed_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # 错误信息（最后一次失败的详情）
    last_error = Column(String(512), nullable=True)
```

### 3.7 管理 API 设计

| 端点 | 方法 | 用途 | 权限 |
|------|------|------|------|
| `/admin/plugins` | GET | 列出所有插件 | admin |
| `/admin/plugins/discover` | POST | 扫描发现新插件 | admin |
| `/admin/plugins/<id>/install` | POST | 安装插件 | admin |
| `/admin/plugins/<id>/enable` | POST | 启用插件 | admin |
| `/admin/plugins/<id>/disable` | POST | 禁用插件 | admin |
| `/admin/plugins/<id>/uninstall` | POST | 卸载插件（需确认） | admin |
| `/admin/plugins/<id>/config` | GET/POST | 插件配置读写 | admin |
| `/admin/plugins/<id>/hooks` | GET | 查看插件钩子列表 | admin |
| `/admin/plugins/<id>/status` | GET | 插件健康状态 | admin |

---

## 四、付费插件生态设计

### 4.1 整体商业模型

```
┌────────────────────────────────────────────────────────────────┐
│                    插件生态参与者                                 │
│                                                                  │
│  平台方 (EasyKai)         开发者 (内部/第三方)     终端用户        │
│  ┌──────────────────┐    ┌─────────────────┐   ┌────────────┐   │
│  │ • 提供插件系统     │    │ • 开发插件        │   │ • 购买/订阅  │   │
│  │ • 运营插件商店     │◄──►│ • 提交到商店      │◄──►│ • 下载安装  │   │
│  │ • License 验证服务 │    │ • 定价/版本管理    │   │ • 管理授权  │   │
│  │ • 资金结算         │    │ • 获取收益        │   │ • 续费/升级 │   │
│  └──────────────────┘    └─────────────────┘   └────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

**核心原则**：
- 插件系统本身是平台能力，不对基础功能收费
- 插件开发者（包括内部团队）可以在商店发布付费插件
- 平台抽取一定比例（如 20%）作为服务费
- 支持买断、订阅、订阅含试用三种模式

### 4.2 插件售卖模式

| 模式 | 说明 | 适用场景 | 定价示例 |
|------|------|---------|---------|
| **免费 (free)** | 无需授权，所有人可用 | 基础功能、社区贡献 | ¥0 |
| **买断 (one-time)** | 一次性付费，永久使用，含 N 个月更新 | 功能完整、迭代不频繁的插件 | ¥99/永久 |
| **订阅 (subscription)** | 按周期付费，持续获得更新和支持 | 需要持续维护的行业插件 | ¥29/月、¥299/年 |
| **订阅含试用 (trial)** | 免费试用 X 天，到期后自动转为付费订阅 | 需要体验的高价值插件 | 试用7天 → ¥29/月 |
| **按需 (usage-based)** | 按调用量/数据量付费（需插件内统计上报） | API 类、数据处理类插件 | 按次/按条计费 |

### 4.3 生命周期 — License 化扩展

在原有 5 状态生命周期中，License 校验在 `enable()` 和 `activate()` 之间插入：

```
          ┌──────────┐
          │ INSTALLED │  (文件就绪，记录入库)
          └─────┬────┘
                │ enable()
                ▼
          ┌──────────┐
          │ ENABLED   │
          └─────┬────┘
                │ license_check() ←── 新增校验点
           ┌────┴────┐
           │         │
           ▼         ▼
     ┌─────────┐ ┌───────────┐
     │ ACTIVE  │ │ LICENSE    │ (未授权 / 过期)
     │ (正常使用) │ │ _EXPIRED   │
     └─────────┘ └───────────┘
```

- **免费插件**：跳过 License 校验，直接进入 ACTIVE
- **付费插件**：在校验点执行 `LicenseManager.validate(plugin_id)`
  - 校验通过 → ACTIVE
  - 未购买/过期 → LICENSE_EXPIRED（功能受限或完全禁用，由配置决定）

新增 2 个状态：

| 状态 | 说明 |
|------|------|
| `LICENSE_PENDING` | 已安装但 License 待激活（需付费/输入激活码） |
| `LICENSE_EXPIRED` | License 已过期（订阅到期或买断更新期结束） |

### 4.4 插件商店架构

#### 整体交互流程

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│  终端用户       │     │  平台端 (本系统)    │     │  License 服务端  │
│  (浏览器)       │     │                  │     │  (独立服务)      │
│              │     │ ┌──────────────┐  │     │              │
│ 浏览商店 ──────►  │ │ PluginStore   │──┼────► │ 验证 License   │
│              │     │ │ (商店模块)     │  │     │              │
│ 购买插件 ──────►  │ ├──────────────┤  │     │ 生成 License   │
│              │     │ │ Payment      │──┼────► │              │
│ 激活License ──►  │ │ (支付对接)    │  │     │ 记录订阅状态    │
│              │     │ └──────────────┘  │     │              │
│ 下载安装 ──────►  │ ┌──────────────┐  │     │              │
│              │     │ │ LicenseVerif │──┼────► │ 在线验证       │
│              │     │ │ (运行校检)    │◄─┼─────┤              │
│              │     │ └──────────────┘  │     │              │
└──────────────┘     └──────────────────┘     └──────────────┘
```

#### 目录结构扩展

```
plugin_manager/
├── ... (原有文件)
├── store.py                    # 商店模块 (浏览/购买/下载)
├── license.py                  # License 引擎 (验证/解密/离线激活)
├── payment.py                  # 支付对接 (支付宝/微信)
├── subscription.py             # 订阅管理 (周期/续费/取消)
├── publisher.py                # 开发者/发布者管理
├── models_store.py             # 商店相关模型
│
├── templates/
│   ├── ... (原有模板)
│   └── plugin_store.html       # 插件商店页面
│   └── plugin_purchase.html    # 购买/订阅页面
│   └── plugin_licenses.html    # 我的授权页
│   └── plugin_publisher.html   # 开发者中心
│
├── store_api/                  # 与远程商店服务通信的客户端
│   ├── __init__.py
│   ├── catalog.py              # 插件目录 API
│   ├── purchase.py             # 下单/支付 API
│   └── license_remote.py       # 远程 License 验证 API
```

### 4.5 数据库模型扩展

#### License 记录表（主库）

```python
class LicenseRecord(Model):
    """付费插件的授权记录"""
    __tablename__ = 'plugin_licenses'

    id = Column(Integer, primary_key=True)
    plugin_id = Column(String(64), nullable=False)      # 插件标识
    site_id = Column(String(128), nullable=False)       # 站点唯一标识（机器码）

    license_key = Column(String(128), nullable=False)   # License Key
    license_type = Column(String(16), nullable=False)   # free | one-time | subscription | trial
    license_status = Column(String(16), nullable=False) # active | expired | suspended | revoked

    # 有效期
    activated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)        # 买断 = 永久+更新期止
    trial_ends_at = Column(DateTime, nullable=True)     # 试用截止

    # 订阅
    subscription_id = Column(String(64), nullable=True) # 支付平台订阅ID
    next_billing_at = Column(DateTime, nullable=True)   # 下次扣款日
    auto_renew = Column(Boolean, default=True)

    # 元数据
    order_id = Column(String(64), nullable=True)        # 订单号
    customer_email = Column(String(128), nullable=True)  # 购买者邮箱
    max_sites = Column(Integer, default=1)              # 允许绑定站点数

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

#### 插件商店目录模型（从远程商店同步到本地缓存）

```python
class StorePlugin(Model):
    """商店中的插件信息（本地缓存远程商店目录）"""
    __tablename__ = 'store_plugins'

    id = Column(Integer, primary_key=True)
    identifier = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(32), nullable=False)
    author = Column(String(128), nullable=False)
    author_url = Column(String(256), nullable=True)

    # 定价
    price_type = Column(String(16), nullable=False)     # free / one-time / subscription / trial
    price_amount = Column(Integer, nullable=True)       # 价格（单位：分，¥9900 = ¥99）
    price_interval = Column(String(8), nullable=True)   # month / year
    trial_days = Column(Integer, nullable=True)         # 试用天数

    # 文件
    download_url = Column(String(512), nullable=True)   # 下载地址
    package_hash = Column(String(64), nullable=True)    # 文件校验
    file_size = Column(Integer, nullable=True)          # 文件大小（KB）

    # 分类/标签
    category = Column(String(32), nullable=True)
    tags = Column(String(256), nullable=True)

    # 统计
    downloads = Column(Integer, default=0)
    rating = Column(String(8), nullable=True)

    updated_at = Column(DateTime, nullable=False)
```

### 4.6 plugin.json 补充 — 定价字段

```json
{
  "identifier": "ali_api",
  "name": "阿里API集成",
  "version": "1.0.0",
  "author": "EasyKai",
  "description": "阿里巴巴商品API、用户API和OAuth集成",
  "dependencies": {},
  "hooks": { ... },

  "pricing": {
    "type": "subscription",
    "amount": 29900,
    "currency": "CNY",
    "interval": "year",
    "trial_days": 7,
    "max_sites": 1
  }
}
```

`pricing.type` 枚举：

| type | amount | interval | trial_days | 有效行为 |
|------|--------|----------|-----------|---------|
| `free` | 忽略 | 忽略 | 忽略 | 免费使用 |
| `one-time` | ¥9999 | 忽略 | 可选 | 一次性付款，永久有效 |
| `subscription` | ¥29900 | `month`/`year` | 可选 | 按周期扣款 |
| `trial` | 同 subscription | 同 subscription | 7/14/30 | 试用后自动转订阅 |

### 4.7 License 引擎设计

#### 在线验证流程

```
用户端 (本系统)                     License 服务端
     │                                  │
     │  POST /license/verify             │
     │  { plugin_id, license_key,        │
     │    site_id, version }             │
     │ ──────────────────────────────►   │
     │                                  │
     │  ← 200 { valid: true,            │
     │    expires_at,                    │
     │    features: [...] }              │
     │  ← 403 { valid: false,            │
     │    reason: "expired/pending/       │
     │           invalid_site/revoked" } │
     │                                  │
```

#### 离线验证（备选方案）

当 License 服务端不可达时的降级策略：

```python
class OfflineLicense:
    """
    离线 License 验证：
    1. 首激活时，服务端返回加密 token（含插件ID+站点ID+有效期）
    2. 后续验证仅本地解密 + 校验证书有效期和站点匹配
    3. 允许离线使用 N 天（config 可配），超期后必须在线验证一次
    """

    @staticmethod
    def generate_token(plugin_id: str, site_id: str,
                       expires_at: str, secret: str) -> str:
        """服务端：生成加密 token"""
        payload = f"{plugin_id}:{site_id}:{expires_at}"
        return encrypt(payload, secret)

    @staticmethod
    def validate_token(token: str, plugin_id: str,
                       site_id: str, secret: str) -> bool:
        """客户端：本地解密 + 校验"""
        try:
            payload = decrypt(token, secret)
            pid, sid, expires = payload.split(":")
            if pid != plugin_id or sid != site_id:
                return False
            if datetime.fromisoformat(expires) < datetime.now():
                return False
            return True
        except Exception:
            return False
```

#### LicenseManager 核心类

```python
class LicenseManager:
    """
    License 管理器，职责：
    - 管理所有付费插件的授权状态
    - 在线/离线验证双通道
    - 自动检测订阅到期并标记
    """

    def __init__(self, store_api=None, offline_secret=None):
        self._store = store_api or StoreAPIClient()
        self._offline_secret = offline_secret
        self._cache = {}  # {plugin_id: LicenseRecord}

    def validate(self, plugin_id: str) -> LicenseResult:
        """
        校验插件 License。
        1. 免费插件 → 直接通过
        2. 查本地 LicenseRecord
        3. 在线验证（有网络）
        4. 离线验证（无网络 fallback）
        5. 未购买 → LICENSE_PENDING
        """

    def activate(self, plugin_id: str, license_key: str) -> LicenseResult:
        """首次激活：调用远程 API 验证 license_key → 写入本地 LicenseRecord"""

    def deactivate(self, plugin_id: str) -> bool:
        """反激活：调用远程 API 释放绑定 → 清理本地记录"""

    def check_expiry(self, plugin_id: str) -> bool:
        """检查订阅是否即将过期（提前 7 天预警）"""

    def refresh_all(self) -> dict[str, LicenseStatus]:
        """启动时/定期刷新所有已安装付费插件的授权状态"""
```

### 4.8 支付对接设计

```python
class PaymentProvider(ABC):
    """支付抽象接口，支持多支付网关"""

    @abstractmethod
    def create_order(self, plugin_id: str, price: int,
                     customer_email: str) -> OrderResult:
        """创建订单，返回支付链接"""

    @abstractmethod
    def verify_payment(self, order_id: str) -> PaymentResult:
        """验证支付结果"""

    @abstractmethod
    def create_subscription(self, plugin_id: str, plan: str,
                            customer_email: str) -> SubscriptionResult:
        """创建订阅"""

    @abstractmethod
    def cancel_subscription(self, subscription_id: str) -> bool:
        """取消订阅"""

    @abstractmethod
    def handle_webhook(self, payload: dict) -> WebhookResult:
        """处理支付回调（支付成功/订阅续费/取消等）"""


class AlipayProvider(PaymentProvider):
    """支付宝当面付/周期扣款实现"""

class WechatPayProvider(PaymentProvider):
    """微信支付实现"""
```

**支付事件 → 系统钩子映射**：

| 支付事件 | 触发的系统钩子 | 用途 |
|---------|--------------|------|
| 支付成功 | `license.activated` | 插件授权激活 |
| 订阅续费成功 | `license.renewed` | 延长有效期 |
| 订阅取消 | `license.cancelled` | 到期后不再续费 |
| 订阅过期 | `license.expired` | 功能降级/锁定 |
| 退款 | `license.revoked` | 吊销授权 |

### 4.9 开发者/发布者模型

```python
class Publisher(Model):
    """插件开发者/发布者"""
    __tablename__ = 'plugin_publishers'

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)           # 开发者名称
    email = Column(String(128), nullable=False)           # 联系邮箱
    website = Column(String(256), nullable=True)          # 开发者主页
    verified = Column(Boolean, default=False)             # 是否已认证
    revenue_share = Column(Integer, default=80)           # 分成比例（%）

    # 结算信息
    payout_email = Column(String(128), nullable=True)     # 收款账号
    total_earnings = Column(Integer, default=0)           # 总收益（分）
    pending_payout = Column(Integer, default=0)           # 待结算

    created_at = Column(DateTime, nullable=False)
```

**开发者流程**：

```
1. 注册开发者账号
2. 提交插件信息 + plugin.json + 插件包
3. 平台审核（代码安全扫描 + 功能验证）
4. 审核通过 → 上架商店
5. 用户购买 → 平台收款 → 定期结算给开发者
```

### 4.10 插件打包与分发

```
plugin_package_v1.0.0.zip
├── plugin.json                    # 元信息（含定价）
├── source/                        # 插件源码
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   └── hooks.py
├── static/                        # 静态资源
│   └── css/, js/
├── templates/                     # 模板
└── signature.sig                  # 数字签名（防篡改校验）
```

安装方式扩展：
1. **本地目录** → 直接放入 `plugins/`（开发/内部用）
2. **商店下载** → 从商店购买后自动下载到 `plugins/` + 验证签名
3. **手动上传** → 后台上传 zip 包 → 解压 → 校验 → 注册

### 4.11 新增管理 API

| 端点 | 方法 | 用途 | 权限 |
|------|------|------|------|
| `/admin/plugins/store` | GET | 浏览插件商店 | admin |
| `/admin/plugins/store/<id>/purchase` | POST | 购买/订阅插件 | admin |
| `/admin/plugins/store/<id>/download` | POST | 下载已购插件 | admin |
| `/admin/plugins/<id>/activate-license` | POST | 手动激活 License | admin |
| `/admin/plugins/<id>/deactivate-license` | POST | 反激活 License | admin |
| `/admin/plugins/licenses` | GET | 查看所有授权记录 | admin |
| `/admin/plugins/subscriptions` | GET | 查看所有订阅 | admin |
| `/admin/plugins/subscriptions/<id>/cancel` | POST | 取消订阅 | admin |
| `/admin/plugins/publisher` | GET | 开发者中心首页 | publisher |
| `/admin/plugins/publisher/submit` | POST | 提交新插件 | publisher |
| `/admin/plugins/publisher/earnings` | GET | 收益统计 | publisher |

### 4.12 License 校验性能保障

为保证启动和请求性能，License 校验设计如下：

```
每次请求校验  →  不可取（避免第三方高性能依赖）
     │
     ▼
启动时批量校验  →  验证所有已启用付费插件的 License → 缓存到内存
     │
     ▼
定期后台校验  →  APScheduler 定时任务（每 6 小时刷新一次）
     │
     ▼
离线宽容期  →  在线失败后允许继续运行 72 小时
```

核心策略：
- **不**在每个请求中校验 License
- 仅在校验点（enable → license_check → activate）和后台任务中触发
- 离线宽容期：避免因网络波动导致正常用户无法使用

### 4.13 预留给未来扩展的接口

```python
class LicenseVerifier(ABC):
    """License 验证器 SPI —— 允许未来替换验证策略"""
    @abstractmethod
    def verify(self, plugin_id: str, license_key: str,
               site_id: str) -> VerificationResult: ...

class PaymentRouter:
    """支付路由 —— 允许动态切换/新增支付渠道"""
    def charge(self, provider_name: str, amount: int,
               description: str) -> ChargeResult: ...

class StoreBackend(ABC):
    """插件商店后端 —— 允许对接不同商店平台"""
    @abstractmethod
    def search(self, query: str) -> list[StorePlugin]: ...
    @abstractmethod
    def purchase(self, plugin_id: str) -> PurchaseResult: ...
```

---

## 五、现有 5 个插件标准化方案

### 5.1 标准化清单

每个插件需要新增或修改：

| 文件 | 用途 | 状态 |
|------|------|------|
| `plugin.json` | 元信息声明（含定价） | 🔲 新增 |
| `__init__.py` | 确保存在 `__plugin__` 变量 | 🔲 检查 |
| `hooks.py` | 定义插件提供的/监听的钩子（可选） | 🔲 可选新增 |

### 5.2 各插件 plugin.json 示例

**ali_api**：
```json
{
  "identifier": "ali_api",
  "name": "阿里API集成",
  "version": "1.0.0",
  "author": "EasyKai",
  "description": "阿里巴巴商品API、用户API和OAuth集成",
  "dependencies": {},
  "pricing": { "type": "subscription", "amount": 29900, "interval": "year", "trial_days": 7 },
  "hooks": {
    "provides": ["ali_api.product_sync", "ali_api.order_import"],
    "listens": ["order.created", "product.updated"]
  },
  "permissions": ["db:*:ali_api_*", "api:external:alibaba"]
}
```

**coupons**：
```json
{
  "identifier": "coupons",
  "name": "优惠券管理",
  "version": "1.0.0",
  "author": "EasyKai",
  "description": "优惠券生成、分发和核销功能",
  "dependencies": {},
  "pricing": { "type": "one-time", "amount": 9900 },
  "hooks": {
    "provides": ["coupons.validate", "coupons.redeem"],
    "listens": ["order.created", "user.registered"]
  },
  "permissions": ["db:*:coupons"]
}
```

**reviews**：
```json
{
  "identifier": "reviews",
  "name": "商品评价",
  "version": "1.0.0",
  "author": "EasyKai",
  "description": "商品评价和评分功能",
  "dependencies": {},
  "pricing": { "type": "one-time", "amount": 4900 },
  "hooks": {
    "provides": ["reviews.after_submit", "reviews.rating_calc"],
    "listens": ["order.paid"]
  },
  "permissions": ["db:*:product_reviews"]
}
```

**wishlist**：
```json
{
  "identifier": "wishlist",
  "name": "收藏夹",
  "version": "1.0.0",
  "author": "EasyKai",
  "description": "用户商品收藏功能",
  "dependencies": {},
  "pricing": { "type": "free" },
  "hooks": {
    "listens": ["user.registered"]
  },
  "permissions": ["db:*:wishlist"]
}
```

**order_notify**：
```json
{
  "identifier": "order_notify",
  "name": "订单通知",
  "version": "1.0.0",
  "author": "EasyKai",
  "description": "订单状态变更通知（邮件/站内信）",
  "dependencies": {},
  "pricing": { "type": "free" },
  "hooks": {
    "listens": ["order.created", "order.paid", "order.shipped"]
  },
  "permissions": ["service:email"]
}
```

---

## 六、实施计划（7 阶段）

### 阶段一：核心引擎 + 数据库（P0）

**目标**：PluginManager 模块可运行，能扫描和持久化插件状态

| 任务 | 文件 | 预估 |
|------|------|------|
| 创建 plugin_manager/ 目录结构 | 新建目录 | - |
| 实现 `models.py` — PluginRegistry 模型 | `plugin_manager/models.py` | - |
| 实现 `PluginManager` 核心类（扫描 + 注册 + 状态机 5 状态） | `plugin_manager/__init__.py` | - |
| 实现 `BasePlugin` 基类 | `plugins/base.py`（扩展） | - |
| 实现 `exceptions.py` — 插件异常体系 | `plugin_manager/exceptions.py` | - |
| 更新 `sync_schema.py` 加入 plugin_registry 表 | `scripts/sync_schema.py`（修改） | - |
| 单元测试覆盖 | `tests/test_plugin_manager.py` | - |

### 阶段二：管理 API + 后台 UI（P0）

**目标**：管理员可通过后台管理插件

| 任务 | 文件 | 预估 |
|------|------|------|
| 实现 `routes.py` — 9 个 REST API | `plugin_manager/routes.py` | - |
| 实现插件列表页模板 | `plugin_manager/templates/plugin_list.html` | - |
| 实现插件详情页模板 | `plugin_manager/templates/plugin_detail.html` | - |
| 实现插件配置页模板（动态渲染 JSON Schema） | `plugin_manager/templates/plugin_settings.html` | - |
| 集成到现有管理后台导航 | 修改 admin 导航 | - |

### 阶段三：5 个插件标准化 + 钩子系统（P1）

**目标**：所有插件符合新规范，钩子系统可用

| 任务 | 文件 | 预估 |
|------|------|------|
| 实现 `hooks.py` — HookRegistry（Action + Filter） | `plugin_manager/hooks.py` | - |
| 实现 `events.py` — EventBus | `plugin_manager/events.py` | - |
| 在系统关键路径植入预定义钩子点 | - | - |
| 5 个插件各加 `plugin.json`（含定价字段） | - | - |
| 5 个插件适配 `BasePlugin` 接口 | - | - |
| 验证所有插件 `self.t()` 翻译方法作用域 | 修复已知问题 | - |

### 阶段四：高级功能（P2）

**目标**：依赖管理、配置验证、日志监控

| 任务 | 文件 | 预估 |
|------|------|------|
| 依赖解析器（拓扑排序 + 循环检测 + 版本匹配） | `plugin_manager/deps.py` | - |
| 插件配置 JSON Schema 校验 | `plugin_manager/validators.py` | - |
| 插件独立日志通道（`plugins/<name>/logs/`） | `plugin_manager/logging.py` | - |
| 插件健康检查 API（`/status`） | - | - |

### 阶段五：License + 本地商店（P1）

**目标**：安装免费/付费插件，支持 License 校验

| 任务 | 文件 | 预估 |
|------|------|------|
| 实现 `license.py` — License 引擎（在线 + 离线） | `plugin_manager/license.py` | - |
| 实现 `store.py` — 商店客户端（浏览/下载） | `plugin_manager/store.py` | - |
| 实现 `models_store.py` — 商店缓存模型 + LicenseRecord 表 | `plugin_manager/models_store.py` | - |
| 扩展 PluginRegistry 模型，加入 License 字段 | `plugin_manager/models.py`（扩展） | - |
| 实现 `/admin/plugins/store` 商店浏览 API | `plugin_manager/routes.py`（扩展） | - |
| 实现插件商店页面模板 | `plugin_manager/templates/plugin_store.html` | - |
| 更新 `sync_schema.py` 加入新增表 | `scripts/sync_schema.py`（修改） | - |

### 阶段六：支付 + 订阅（P2）

**目标**：在线购买、订阅管理、支付回调

| 任务 | 文件 | 预估 |
|------|------|------|
| 实现 `payment.py` — 支付宝/微信支付对接 | `plugin_manager/payment.py` | - |
| 实现 `subscription.py` — 订阅管理 | `plugin_manager/subscription.py` | - |
| 实现购买/订阅 API | `plugin_manager/routes.py`（扩展） | - |
| 实现购买/订阅页面模板 + 授权管理页面 | `plugin_manager/templates/` | - |
| License 服务端 API（单独部署或集成） | `license_server/` | - |

### 阶段七：开发者中心（P3）

**目标**：开放第三方插件提交流程

| 任务 | 文件 | 预估 |
|------|------|------|
| 实现 `publisher.py` — 开发者管理 | `plugin_manager/publisher.py` | - |
| 实现 `/admin/plugins/publisher` 系列 API | `plugin_manager/routes.py`（扩展） | - |
| 实现插件提交审核流程 | 新建审核模块 | - |
| 实现开发者页面 | `plugin_manager/templates/plugin_publisher.html` | - |
| 完善插件打包工具 | `scripts/package_plugin.py` | - |
| 编写开发者文档 | `docs/plugin-dev-guide.md` | - |

---

## 七、已知问题修复（配套进行）

| 问题 | 文件 | 修复方案 |
|------|------|---------|
| `ali_api` 在插件库创建 `product_skus` 表 | `plugins/ali_api/routes/admin.py:L772` | 移动到主库 models.py 或改为查询主表 |
| `self.t()` 作用域问题 | 各插件 `__init__.py` | 将 `t()` 改为模块级函数或注入到 `g` 对象 |

---

## 八、风险与注意事项

1. **依赖循环检测**：插件 A 依赖 B，B 依赖 A — 必须在 enable 阶段做拓扑排序检测
2. **数据库迁移**：插件升级时需处理 Schema 变更，建议初期约定"不向后不兼容，升级需手动"
3. **钩子性能**：大量插件注册同一个钩子时可能影响性能，考虑钩子执行超时机制
4. **安全边界**：插件拥有完整 Python 执行能力，需管理员审核后才可启用来源不明的插件
5. **主库残留**：阶段三完成后，可选择性删除主库中的 coupons、product_reviews、wishlist 等表
6. **License 防破解**：离线 token 使用非对称加密，私钥仅存服务端；建议定期轮换签名密钥
7. **支付安全**：支付回调必须验证签名和幂等性，防止重复激活

---

## 九、参考系统

- **WordPress Hooks**: Actions (`do_action`) + Filters (`apply_filters`)
- **Jenkins Plugin Architecture**: Extension Point + ClassLoader isolation + Update Center
- **VS Code Extensions**: `activationEvents` + `contributes` + Extension Host process + Marketplace
- **Flask Extensions**: `init_app()` factory pattern + Blueprint + `current_app`
- **Drupal Plugin API**: PluginManager + Discovery (Annotation/YAML) + PluginInterface
- **Flask-Plugins**: `info.json` + `__plugin__` variable + DISABLED file
- **Stripe/Lemon Squeezy**: Payment + Subscription + License key generation（商业模式参考）
