# 插件标准 v1.5 — 完整规范

> 生成日期：2026-07-09（§9-11 于 07-09 追加）
> 更新日期：2026-07-31（§9、§10.3、§11.2 — 适配 PostgreSQL schema 架构）
> 更新日期：2026-08-05（v1.2 → v1.3 — 追加 §13 版本发现与升级规范）
> 更新日期：2026-08-05（v1.3 → v1.4 — 追加 §14 商店展示规范 + plugin.json 展示字段）
> 更新日期：2026-08-07（v1.4 → v1.5 — 追加 §15 前端框架插件指南、§16 插件审核规范；§9.2 补框架插件目录约定；§11.3 补审核交叉引用；§12.11 补 iframe 例外条款）
> 前置阅读：本规范假定已了解项目最高宪法 [AGENTS.md](../AGENTS.md) 和 `project_rules.md`。

---

## 0. 设计原则

| 原则 | 解释 |
|------|------|
| **AI 引擎是内核** | 插件不直接操作 LLM。所有 Agent 注册、模型选择、API Key 管理均由 AI 引擎内核统一裁决。 |
| **声明意图，不绑定实现** | 插件声明"我需要什么能力的模型"，不绑定具体 provider/model。用户/管理员控制成本。 |
| **卸载零残留** | Agent 注册随插件走。卸载时 `WHERE source_plugin='xxx'` 一并注销，数据和 prompt 归零。 |
| **向后兼容** | 所有 v1.1 新增字段均为可选。旧 `plugin.json` 不加新字段，解析和安装照常工作。 |
| **复用不重造** | Agent 注册复用现有 `agent_matrix` 的 `agents` 表（加列）；统计复用 PluginManager 现有 `BasePlugin` 可选方法机制。 |

---

## 1. plugin.json 完整 Schema

### 1.1 全部字段一览（`★` = v1.1 新增）

```
plugin.json
├── 标识
│   ├── identifier         string   ★必填   唯一标识，如 "ali_api"
│   ├── name               string   ★必填   显示名称（英文规范值，如 "1688 Supply Chain"）
│   ├── name_i18n_key      string   ★v1.5   插件名 i18n 查找键（如 "plugin.name"，见 §10.5）
│   ├── version            string   ★必填   语义化版本号
│   ├── description        string           描述
│   ├── author             string           作者
│   └── min_app_version    string           最低系统版本
│
├── ★ 分类与展示（v1.1 新增）
│   ├── category           string           插件分类
│   ├── icon               string           图标名（复用 icons.html 体系）
│   ├── icon_url           string           ★v1.4 商店卡片缩略图 URL（280x120px 推荐）
│   ├── tags               string[]         标签数组
│   ├── screenshots        string[]         ★v1.4 详情页截图 URL 数组
│   └── readme_url         string           ★v1.4 README 文件 URL（Markdown 格式，详情页展示）
│
├── 依赖与配置
│   ├── dependencies         object           {identifier: version_spec}
│   ├── config             object           默认配置
│   ├── settings_schema    object           JSON Schema Draft-07（配置表单校验）
│   ├── permissions        string[]         权限声明
│   └── hooks              object           {provides: [], listens: []}
│
├── ★ Agent 声明（v1.1 新增）
│   └── agents             object[]         插件希望注册到 Agent 矩阵的角色
│       ├── name                            显示名称
│       ├── identifier                      Agent 唯一标识
│       ├── role_type                       master | sub
│       ├── domain                         领域标签（用于关键词模板 fallback）
│       ├── prompt_file                     相对插件目录的 prompt 路径
│       ├── model_policy  object            模型选择策略（见 §3）
│       ├── capabilities   string[]         能力标签
│       └── enabled_by_default bool         启用时是否默认激活
│
└── ★ Dashboard 统计（v1.1 新增）
    └── dashboard          object
        └── stats           object[]         统计指标列表
            ├── key                         指标键
            ├── title                       卡片标题
            └── type                        counter | gauge
```

### 1.2 完整示例（1688 插件改造后）

```json
{
  "name": "1688 Supply Chain",
  "name_i18n_key": "plugin.name",
  "identifier": "ali_api",
  "version": "0.3.0",
  "description": "1688 供应链采集 — 商品搜索、AI 优化、本地商城发布",
  "author": "VeroRun",
  "min_app_version": "0.10.0",

  "category": "supply_chain",
  "icon": "package",
  "icon_url": "https://cdn.verorun.com/plugins/ali_api/icon.png",
  "tags": ["电商", "采集", "AI"],
  "screenshots": [
    "https://cdn.verorun.com/plugins/ali_api/screenshot1.png",
    "https://cdn.verorun.com/plugins/ali_api/screenshot2.png"
  ],
  "readme_url": "https://cdn.verorun.com/plugins/ali_api/README.md",

  "dependencies": {},

  "config": {
    "api_gateway": "https://gw.open.1688.com/openapi"
  },

  "permissions": [
    "network.request",
    "shop.product.write"
  ],

  "hooks": {
    "provides": [],
    "listens": []
  },

  "agents": [
    {
      "name": "Supply Chain Agent",
      "identifier": "supply_chain",
      "role_type": "sub",
      "domain": "supply_chain",
      "prompt_file": "agents/supply_chain_prompt.md",
      "model_policy": {
        "strategy": "tier",
        "tier": "standard",
        "allow_user_override": true,
        "fallback": "inherit"
      },
      "capabilities": ["product.search", "product.rewrite", "product.publish"],
      "enabled_by_default": true
    }
  ],

  "dashboard": {
    "stats": [
      { "key": "total_items",       "title": "已采集商品", "type": "counter" },
      { "key": "published_today",   "title": "今日发布",   "type": "counter" },
      { "key": "api_calls_24h",     "title": "24h API调用","type": "gauge"   }
    ]
  },

  "settings_schema": {
    "type": "object",
    "properties": {
      "api_gateway": {
        "title": "API 网关地址",
        "type": "string",
        "description": "1688 Open API 网关地址"
      }
    }
  }
}
```

---

## 2. 新增字段规范

### 2.1 分类与展示

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `category` | string | 否 | `"other"` | Dashboard 按此分组。建议枚举：`content`、`shop`、`supply_chain`、`ai_agent`、`system`、`knowledge`、`social`、`other` |
| `icon` | string | 否 | `"plugin"` | 图标名，复用现有 [icons.html](../admin/templates/partials/icons.html) 体系的 SVG ID |
| `tags` | string[] | 否 | `[]` | 用于搜索和筛选 |

### 2.2 Agent 声明 (`agents`)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | 是 | — | Agent 显示名称 |
| `identifier` | string | 是 | — | 唯一标识，不可与已有 Agent 冲突。建议格式：`插件identifier_角色` |
| `role_type` | string | 是 | — | `master` 或 `sub`（对齐 agents 表 CHECK 约束） |
| `domain` | string | 是 | — | 领域标签，用于 `_template_decompose` 关键词 fallback |
| `prompt_file` | string | 是 | — | **相对插件目录**的路径。启用时从文件读取内容写入 agents 表。卸载时注销数据库行，文件随目录删除。 |
| `model_policy` | object | 否 | `{"strategy":"inherit"}` | 模型选择策略，详见 §3 |
| `capabilities` | string[] | 否 | `[]` | 能力标签，如 `["product.search","product.publish"]` |
| `enabled_by_default` | bool | 否 | `true` | 插件启用时该 Agent 是否默认激活 |

### 2.3 Dashboard 统计 (`dashboard`)

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `dashboard` | object | 否 | `{}` | Dashboard 统计声明 |
| `dashboard.stats` | object[] | 否 | `[]` | 统计指标列表 |
| `stats[].key` | string | 是 | — | 指标标识符，`get_dashboard_stats()` 返回 dict 中的 key |
| `stats[].title` | string | 是 | — | 卡片上显示的中文标题 |
| `stats[].type` | string | 是 | — | `counter`（累计值）或 `gauge`（瞬时/周期值） |

统计获取：调用 `BasePlugin.get_dashboard_stats()` → 返回 `{key: value}` → Dashboard 按 `stats` 声明渲染卡片。**数据源由插件自行从独立库取数。**

---

## 3. 模型选择策略 (`model_policy`)

### 3.1 概述

插件**不直接绑定模型**。插件通过 `model_policy` 声明"我需要什么档次的推理能力"，最终由 AI 引擎内核根据用户配置的 **tier 映射** 选择具体 provider/model。

用户换一次全局模型，所有使用 `inherit`/`tier` 策略的插件 Agent 跟着换——成本和管理权在用户手里。

### 3.2 字段定义

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `strategy` | string | 否 | `"inherit"` | `inherit` \| `tier` \| `explicit` |
| `tier` | string | 条件必填 | `"standard"` | `high` \| `standard` \| `cheap` \| `local`。仅 `strategy=tier` 时生效 |
| `provider` | string | 条件必填 | `""` | 如 `"deepseek"`。仅 `strategy=explicit` 时生效 |
| `model` | string | 条件必填 | `""` | 如 `"deepseek-chat"`。仅 `strategy=explicit` 时生效 |
| `allow_user_override` | bool | 否 | `true` | 用户能否在后台手动为此 Agent 换模型 |
| `fallback` | string | 否 | `"inherit"` | 首选不可用时的降级：`"inherit"`（降级到全局默认）\| `"none"`（不降级，报错） |

### 3.3 三种策略

#### `inherit`（继承全局，默认）
```json
{ "model_policy": { "strategy": "inherit" } }
```
插件不关心用什么模型。使用系统全局默认模型。**适用**：绝大多数普通插件 Agent。

#### `tier`（能力档位，推荐主推）
```json
{ "model_policy": { "strategy": "tier", "tier": "high" } }
```

| tier | 适用场景 | 默认映射（可后台改） |
|------|----------|------|
| `high` | 任务拆解、自检、复杂推理（Master Agent） | gpt-4o |
| `standard` | 通用执行（内容改写、信息提取） | deepseek-chat |
| `cheap` | 大批量低要求（清洗、摘要、分类） | qwen-turbo |
| `local` | 隐私/离线（内部数据不传外网） | ollama llama3 |

tier → 具体模型的映射存在 `system_config` 表，后台 AI 设置页可配。默认值由 `PROVIDER_CONFIGS` 提供。

#### `explicit`（显式指定）
```json
{ "model_policy": { "strategy": "explicit", "provider": "deepseek", "model": "deepseek-chat" } }
```
插件明确要求某个模型。系统校验 Key 可用后使用，不可用则按 fallback 降级。**适用**：插件做了特定模型的 prompt 微调。

### 3.4 解析优先级（由 AI 引擎内核统一执行）

```
1. 用户后台对该 Agent 的手动覆盖（需 allow_user_override=true）
2. model_policy.strategy 解析
   └─ inherit   → 全局默认 Agent 模型
   └─ tier      → system_config 查 model_tier_{high|standard|cheap|local} → provider_model_id
   └─ explicit  → provider + model（校验 Key 可用）
3. model_policy.fallback
4. PROVIDER_CONFIGS 硬编码兜底
```

### 3.5 卸载时 tier 配置是否删除？

**不删除。** tier 映射存在 `system_config` 表，属于系统级配置，不属于任何插件。卸载插件只注销 `agents` 表中 `source_plugin` 对应的行，不动 `system_config`。

---

## 4. Agent 注册/注销生命周期

### 4.1 启用流程

```
enable(plugin)
  │
  ├─ 1. setup()
  │     └─ 插件初始化独立库、创建表、注册路由
  │
  ├─ 2. register_agents()                        ★新增
  │     ├─ 读 self.plugin_info.metadata['agents']
  │     ├─ 遍历每个 agent 声明:
  │     │   ├─ 从 prompt_file 读取完整 system_prompt
  │     │   ├─ 调用 agent_matrix.register_plugin_agent(
  │     │   │     identifier, name, role_type, domain,
  │     │   │     provider, model, system_prompt,
  │     │   │     model_policy_json,
  │     │   │     source_plugin=plugin_identifier,
  │     │   │     enabled=enabled_by_default
  │     │   │   )
  │     │   └─ INSERT OR REPLACE INTO agents
  │     └─ 打印 "[AliApi] Agent registered: supply_chain"
  │
  └─ 3. activate()
        └─ 激活运行时资源
```

### 4.2 卸载/禁用流程

```
disable / uninstall(plugin)
  │
  ├─ deactivate() / on_uninstall()
  │    └─ 清理运行时资源
  │
  └─ 注销所有 Agent:                               ★新增
       DELETE FROM agents WHERE source='plugin' AND source_plugin=?
       打印 "[AliApi] Agents unregistered: 1"
```

---

## 5. 数据库变动

### 5.1 主库 `plugin_registry` 表

```sql
ALTER TABLE plugin_registry ADD COLUMN category        TEXT DEFAULT 'other';
ALTER TABLE plugin_registry ADD COLUMN icon            TEXT DEFAULT 'plugin';
ALTER TABLE plugin_registry ADD COLUMN tags            TEXT DEFAULT '[]';
ALTER TABLE plugin_registry ADD COLUMN dashboard_meta  TEXT DEFAULT '{}';
```

每条 `ALTER TABLE` 需 try/except 幂等处理（列已存在则忽略）。

### 5.2 主库 `agents` 表

```sql
ALTER TABLE agents ADD COLUMN source         TEXT DEFAULT 'builtin';
ALTER TABLE agents ADD COLUMN source_plugin  TEXT DEFAULT '';
ALTER TABLE agents ADD COLUMN model_policy   TEXT DEFAULT '{"strategy":"inherit"}';
ALTER TABLE agents ADD COLUMN prompt_source  TEXT DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_agents_source_plugin ON agents(source_plugin);
```

- `source='builtin'`：9 个默认 Agent（Athena、CMS Agent 等）
- `source='plugin'`：插件注册的。`source_plugin` 存插件 identifier
- `prompt_source`：空串 = 硬编码；`"plugin:ali_api"` = 来自插件目录

### 5.3 系统初始化

`seed_default_agents()` 写入种子 Agent 时补 `source='builtin'`。

### 5.4 关键约束

1. **以上 SQL 全部 ALTER TABLE 操作主库结构，属于破坏性操作**，执行前须用户单独批准。
2. **全部幂等**：每条 ALTER 用 try/except 包住，列已存在则跳过。

---

## 6. PluginManager + BasePlugin 代码变动

### 6.1 PluginInfo dataclass

新增 4 个字段：

```python
@dataclass
class PluginInfo:
    # ... 现有字段保持不变 ...
    category: str = 'other'
    icon: str = 'plugin'
    tags: list = field(default_factory=list)
    dashboard_meta: dict = field(default_factory=dict)
```

### 6.2 PluginDiscovery

`_parse_plugin_json()` 新增解析上述字段，缺省则用默认值。

### 6.3 BasePlugin 新增可选方法

```python
def register_agents(self) -> list:
    """返回需注册到 Agent 矩阵的角色列表。默认从 plugin.json 读取。"""

def get_dashboard_stats(self) -> dict:
    """返回 Dashboard 统计指标。插件覆写，从自有独立库取数。"""
```

### 6.4 manager.py 生命周期

| 事件 | 新增动作 |
|------|----------|
| `enable()` | setup 之后调 `register_agents()` |
| `disable()` | 注销 `source_plugin` 对应的所有 Agent |
| `uninstall()` | 同上，且清理 `plugin_registry` 行 |
| `get_all_stats()` | 遍历 active 插件，逐个调 `get_dashboard_stats()` 聚合 |

---

## 7. 执行清单

| 阶段 | 序号 | 文件/操作 | 风险 |
|------|------|----------|------|
| **Phase B** | 1 | `agent_matrix/models.py` — 新增 `register_plugin_agent()` / `unregister_plugin_agents()` | 低 |
| | 2 | `agent_matrix/models.py` — `ALTER TABLE agents` 加 4 列 + 索引 | **高（动主库）** |
| | 3 | `agent_matrix/models.py` — `seed_default_agents()` 补 `source='builtin'` | 低 |
| | 4 | `agent_matrix/engine.py` — model_policy 解析层前置 | 中 |
| | 5 | `plugin_manager/models.py` — PluginInfo 加字段 + `ALTER TABLE plugin_registry` 加 4 列 | 中 |
| | 6 | `plugin_manager/discovery.py` — 解析新字段 | 低 |
| | 7 | `plugin_manager/base.py` — 新增 `register_agents()` / `get_dashboard_stats()` | 低 |
| | 8 | `plugin_manager/manager.py` — enable/disable/uninstall 插入 Agent 注册/注销 | 中 |
| **Phase C** | 9 | Dashboard 模板 — 插件分类表 + 统计卡片聚合 | 中 |
| **Phase D** | 10 | 各现有插件 `plugin.json` 补新字段 | 低 |
| | 11 | 新增 `agent_matrix/services/model_resolver.py`（tier → model 翻译器） | 中 |

---

## 8. 向后兼容

- 旧 `plugin.json` 不加新字段 → PluginInfo 自动给默认值，安装不中断
- 旧 PluginInfo 序列化/反序列化 → `from_json`/`to_dict` 自动适配新字段（dataclass 默认值）
- `seed_default_agents()` 的 9 个内置 Agent 补 `source='builtin'` → 现有行为不变
- `model_policy` 不填 → 默认 `strategy=inherit`，等价于直接用全局默认模型，和现在完全一样

---

## 9. 目录结构与部署映射

### 9.1 单库多 Schema 架构

当前系统使用单一 PostgreSQL 实例（`verorun`），插件通过独立 **schema** 实现数据隔离，不再使用 SQLite。

| 层 | Schema | 说明 |
|----|--------|------|
| 主系统 | `public` | 用户、Agent、系统配置、订阅订单等核心表 |
| 插件 | `analytics`、`health`、`content_factory` 等 | 每个插件独立 schema，表结构自包含 |
| 管理后台 | Admin 服务 (`:8084`) | 通过 `plugins/_base/db.py` 的 `get_raw_connection()` 统一连接 PG |

**插件接入 PG 方式**：

```python
from plugins._base.db import get_raw_connection

conn = get_raw_connection()  # 连接到 verorun 数据库
cur = conn.cursor()
cur.execute("SET search_path TO my_plugin, public")  # 设置 schema 搜索路径
cur.execute("CREATE TABLE IF NOT EXISTS my_data (...)")
```

**关键规则**：
- 插件写操作限定在自己的 schema 内
- 读主库 public schema 数据需显式指定 `public.table_name`
- `plugins/_base/db.py` 提供统一的 `get_raw_connection()` 工厂，替代各插件内联 `psycopg2.connect()`

### 9.2 框架插件目录约定（v1.5 追加）

使用 React/Vue 等前端框架的插件，在标准目录基础上增加：

```
plugins/<id>/
├── static/
│   ├── lib/                # 本地化的框架 UMD 库（禁止外网 CDN，见 §15）
│   └── js/                 # 自身脚本（手写或构建产物）
├── src/                    # （可选）框架源码（组件/样式），审核要求见 §16
│   ├── components/
│   └── build/              # （可选）可复现构建配置（esbuild/vite 等）
├── templates/
│   └── <page>.html         # iframe 独立页面（menu.embed_url 指向）
└── plugin.json             # menu.embed_url 必须声明 iframe 页面路由
```

约束：
- 框架库只允许**本地静态文件**，禁止在页面中引用外网 CDN（unpkg/jsdelivr/cdnjs）
- `templates/` 框架页面为独立完整 HTML，允许 `<script>`（§12.11 例外条款）
- 若提交打包产物，必须同时提供 `src/` 源码 + 构建命令，保证**可复现构建**（§16 审核要求）

---

## 10. 功能扩展规范

### 10.1 事件/钩子系统（Actions + Filters）

扩展现有的 `plugin_manager/event_bus.py`，增加双钩子机制。

#### Action（通知型）

事件触发后执行回调，无返回值。已支持的 `EventName`：

```python
class EventName(Enum):
    PLUGIN_ENABLED = 'plugin_enabled'
    PLUGIN_DISABLED = 'plugin_disabled'
    PLUGIN_INSTALLED = 'plugin_installed'
    PLUGIN_UNINSTALLED = 'plugin_uninstalled'
    ORDER_PAID = 'order_paid'
    USER_REGISTERED = 'user_registered'
    USER_LOGIN = 'user_login'
    PRODUCT_CREATED = 'product_created'
    PRODUCT_UPDATED = 'product_updated'
    CONTENT_PUBLISHED = 'content_published'
```

注册方式：

```python
class MyPlugin(BasePlugin):
    def on_enable(self, registry):
        bus = get_event_bus()
        bus.on(EventName.ORDER_PAID, self._on_order_paid)

    def _on_order_paid(self, **kwargs):
        logger.info(f"订单 {kwargs.get('order_id')} 已支付")
```

#### Filter（过滤型 — 新增）

允许插件修改数据后再返回，支持链式调用：

```python
class FilterBus:
    def __init__(self):
        self._filters = defaultdict(list)

    def add_filter(self, name: str, handler, priority: int = 10):
        self._filters[name].append((priority, handler))
        self._filters[name].sort(key=lambda x: x[0])

    def apply(self, name: str, value, **kwargs):
        for _, handler in self._filters.get(name, []):
            value = handler(value, **kwargs)
        return value
```

**适用场景**：
- `page_head` → 插件注入自定义 CSS/JS
- `product_detail` → 插件扩展商品详情字段
- `user_profile` → 插件添加用户自定义字段

### 10.2 权限模型

插件通过 `plugin.json` 的 `permissions` 字段声明所需权限范围：

```json
{
  "permissions": [
    "api:read",
    "api:write",
    "user:profile"
  ],
  "admin_permissions": ["admin:access"]
}
```

| 权限 | 说明 |
|------|------|
| `api:read` | 可读取业务数据（订单、商品、用户信息） |
| `api:write` | 可写入业务数据（创建订单、发布商品） |
| `user:profile` | 可读取用户基本信息（但不含密码/密钥） |
| `admin:access` | 可访问管理后台接口 |
| `network:request` | 可发起外部网络请求 |
| `filesystem:read` | 可读取插件目录外的文件 |
| `filesystem:write` | 可在插件目录外写入文件 |

**实施规则**：
- 路由自动注册到统一前缀 `/plugin/<name>/`，`plugin_manager/routes.py` 检查权限
- 超过声明范围的调用返回 403
- `admin_permissions` 中声明的权限需要管理员角色才能放行

### 10.3 配置 UI

每个插件通过 `settings_schema`（JSON Schema Draft-07）声明配置表单，自动渲染为管理后台设置页面。

**存储**：`plugin_registry` 表的 `config` 字段（JSON 类型，PG 主库）：

```sql
-- 配置存储在 plugin_registry.config 中，不需要独立表
SELECT config FROM plugin_registry WHERE identifier = 'my_plugin';
```

**默认值**在 `plugin.json` 的 `config` 中声明（同旧版，无变化）。PluginManager 在安装时将默认值写入 `plugin_registry.config`，后续修改通过 BasePlugin 的 `get_config_value()` / `set_config_value()` 方法读写。

```json
{
  "config": {
    "api_key": "",
    "max_items": 20,
    "enable_notify": true
  },
  "settings_schema": {
    "type": "object",
    "properties": {
      "api_key": {
        "title": "API Key",
        "type": "string",
        "description": "第三方服务 API 密钥"
      },
      "max_items": {
        "title": "最大条目数",
        "type": "integer",
        "default": 20,
        "minimum": 1
      },
      "enable_notify": {
        "title": "启用通知",
        "type": "boolean",
        "default": true
      }
    }
  }
}
```

**管理端入口**：插件通过 `plugin.json` 的 `admin_url` 字段声明管理页面入口。插件管理列表（`plugins_admin.html`）据此显示 🔗 Manage 链接跳转到插件自有管理页或 admin SPA。插件配置不再通过 PluginManager 内联加载，由插件自有页面独立承载。

**管理菜单（`menu` 扩展字段）**：`PluginManager` 消费 `plugin.json` 顶层 `menu` 对象，向 admin SPA 注入插件管理菜单项（`PluginManager.get_plugin_menus()` 读取 `metadata['menu']`）。该字段为系统实际使用但未写入早期规范的扩展字段，结构如下：

```json
"menu": {
  "group": "System",
  "key": "dev_accounts",
  "icon": "key",
  "label": "Developer Accounts"
}
```

- `group` — 菜单分组名（如 `System`、`Security & Compliance`）
- `key` — 唯一标识，admin SPA 通过 `window["l_" + key]()` 调用插件页面渲染函数
- `icon` — 菜单图标名称
- `label` — 菜单显示名（可配合 i18n 翻译）

约定：`menu.key` 必须与插件模板中定义的 `window.l_<key>` 渲染函数一致，否则点击菜单无页面响应。可选 `url` 字段仅作展示用途，不参与导航（导航由 admin SPA 的 `goPlugin()` 依据 `embed_url` 决定；无 `embed_url` 时走内联 `l_<key>()` 渲染）。

### 10.4 依赖管理

#### 声明方式

```json
{
  "dependencies": {
    "reviews": ">=1.0.0",
    "order_notify": "*"
  },
  "conflicts": ["legacy_reviews"]
}
```

`dependencies` 值使用语义化版本范围：
- `"*"` — 任意版本
- `">=1.0.0"` — 大于等于 1.0.0
- `"1.0.0"` — 精确匹配
- `"~1.0.0"` — 兼容版本（>=1.0.0 且 <1.1.0）

#### 加载规则

1. `PluginManager.enable()` 时解析所有依赖
2. **拓扑排序**确定加载顺序，确保依赖先加载
3. **循环依赖检测** — 发现环则报错，阻止 enable
4. **依赖缺失** — 如果依赖插件不存在，允许 keep disabled，enable 时报错提示

**核心逻辑**（增强 `plugin_manager/deps.py`）：

```python
def resolve_load_order(plugins: Dict[str, PluginMeta]) -> List[str]:
    """拓扑排序，按依赖顺序返回插件名列表"""
    graph = {}
    for name, meta in plugins.items():
        graph[name] = set(meta.metadata.get('dependencies', {}).keys())
    # Kahn 算法检测循环依赖
    # 返回排序后的列表
```

### 10.5 日志与监控

#### 独立日志通道

每个插件自动获得隔离的日志文件：

```python
from plugin_manager.logger import get_plugin_logger

logger = get_plugin_logger('my_plugin')
logger.info("操作成功")       # → logs/plugins/my_plugin.log
logger.error("操作失败")      # → logs/plugins/my_plugin.log
```

日志文件位置：`data/logs/plugins/<plugin_name>.log`

#### 监控指标

通过 `BasePlugin.get_dashboard_stats()` 暴露：

```python
class MyPlugin(BasePlugin):
    def get_dashboard_stats(self) -> dict:
        with get_db() as conn:
            return {
                'total_items': conn.execute('SELECT COUNT(*) FROM my_items').fetchone()[0],
                'api_calls_24h': conn.execute(
                    "SELECT COUNT(*) FROM api_logs WHERE created_at > datetime('now', '-1 day')"
                ).fetchone()[0],
            }
```

**指标规范**：
- 全部暴露为 `/admin/plugins/metrics` 端点
- 错误率超过阈值（如 5%）触发管理告警
- 每个插件最多上报 10 个指标

### 10.6 版本与 Schema 迁移

#### 版本声明

```json
{
  "version": "1.0.0"
}
```

语义化版本约定：
- **主版本**：Schema 破坏性变更（删表、改列）
- **次版本**：新增功能、新增表、新增列（向后兼容）
- **补丁**：Bug 修复、性能优化

#### 迁移机制

`BasePlugin` 提供可选迁移方法：

```python
class BasePlugin:
    def get_schema_version(self) -> str:
        """从插件独立库读取当前 schema 版本"""

    def migrate(self, from_version: str, to_version: str) -> bool:
        """版本升级逻辑，子类覆写"""
        return True
```

**约定目录结构**：

```
plugins/<name>/
├── migrations/
│   ├── v1.0.0_to_v1.1.0.sql
│   └── v1.1.0_to_v2.0.0.sql
└── plugin.json
```

**执行流程**：
1. 插件 enable 时检查 `get_schema_version()` vs `plugin.json` 中的 `version`
2. 如果落后，顺序执行 `migrations/` 下的 SQL 文件
3. 每个 SQL 文件用事务包裹，失败自动回滚
4. 迁移完成后更新存储的 schema 版本号

---

## 11. 安全与合规

### 11.1 最小权限原则

- 插件只能访问其 `permissions` 中声明的资源
- 默认无权限，需要显式声明
- 敏感权限（`admin:access`、`filesystem:write`、`network:request`）需要管理员在安装时手动确认

### 11.2 数据隔离

- 插件通过独立 PostgreSQL **schema** 实现数据隔离（非 SQLite `.db` 文件）
- 插件通过 `plugins/_base/db.py` 的 `get_raw_connection()` 获取 PG 连接
- 需读主库 public schema 数据时显式指定 `public.table_name`
- 不得直接修改其他插件的 schema 或 public schema 表结构

### 11.3 网络隔离

- `network:request` 权限默认关闭，开启需管理员确认
- 插件发起的 HTTP 请求默认超时 10 秒
- 禁止访问内网 IP 段（127.0.0.0/8、10.0.0.0/8、172.16.0.0/12、192.168.0.0/16）
- **前端侧**（浏览器环境）安全规则（外网 CDN、token/Cookie 外泄、XSS）见 §16「插件审核规范」

---

## 12. 模块解耦标准操作手册（2026-07 追加）

> 本章沉淀自"系统模块 → 插件"解耦实践（IM Gateway 试点），作为后续模块解耦的统一模板。

### 12.1 i18n 前置铁律

插件翻译文件必须放在 `plugins/<id>/i18n/{zh-CN,en}.yml`（**不是 `locale/`**）。
PluginManager 在 `init_app` 时调用 `seed_plugin_translations()` 将其写入主库 `i18n_strings` 表，
使全局 `{{ _() }}` 能查到。模板统一用 `{{ _('English Source') }}`，源串为英文，
`zh-CN.yml` 提供中文映射，`en.yml` 为同一映射（identity）。

### 12.2 标准目录结构

```
plugins/<id>/
├── plugin.json          # 标识/菜单/settings_schema（menu.key 复用旧前端函数名以兼容侧边栏）
├── __init__.py          # <Name>Plugin(BasePlugin)：on_install 建表+迁移、register_routes、对外接口
├── models.py            # 独立库 <id>.db：get_<id>_db() / init_<id>_db() / migrate_from_main_db()
├── routes.py            # Blueprint，url_prefix 保持与迁出前一致（如 /admin/channels）
├── adapters/            # （可选）多实现抽象：base.py 基类 + 各实现子类 + __init__.py 工厂
├── templates/           # 前端 partial（从 admin/templates/partials/ 迁入）
└── i18n/                # zh-CN.yml / en.yml
```

> 使用前端框架（React/Vue）的插件目录约定另见 §9.2。

### 12.3 独立库 + 主库只读契约

- 插件自有数据写独立库 `plugins/<id>/<id>.db`（`get_<id>_db()`）。
- 需读主库时用 `from models import get_db`（只读），严禁跨库 JOIN / 写主库结构。
- `migrate_from_main_db()`：从主库同名表幂等迁移历史数据，仅在本地为空时覆盖，避免回退用户新配置。

### 12.4 主系统改造清单（迁出四件事）

1. **路由**：删除 admin.py 中迁出的路由，留一行迁移注释。
2. **模板 include**：admin.html 的 `{% include 'partials/x.html' %}` 改为
   `{% include 'plugins/<id>/templates/xxx.html' ignore missing %}`。
3. **前端 JS**：从 partials 中删除迁出的函数块，迁入插件模板。
4. **跨模块调用**：主系统若需调插件能力（如媒体库推送），通过
   `app.extensions['plugin_manager'].get_instance('<id>')` 获取实例调用，
   插件禁用时实例为 None，主系统据此降级提示。

### 12.5 双写过渡与卸载零残留

- 迁移后**保留主库旧表**一个过渡期（删表是破坏性操作，需单独批准）。
  部署验证插件读写正常后，再单独批准删主库表。
- `on_uninstall` 需清理插件独立库与注册的 Agent（`WHERE source_plugin='<id>'`）。

### 12.6 验证步骤

1. `python -m py_compile` 全部新增/修改的 .py 文件。
2. 隔离脚本验证：插件导入、`init_db`、adapter 工厂、对外接口可调用。
3. `GetDiagnostics` 无报错。
4. 部署到服务器后，验证真实数据迁移 + 页面功能 + i18n 显示。

### 12.7 跨模块依赖处理（Social Push 案例）

当被解耦模块的函数/常量被其他模块 import 时（如 `social_push._publish_to_platform`、
`PLATFORM_INFO` 被 content_factory、cms_admin 引用），处理模式：

1. 插件 `__init__.py` 将这些能力暴露为**实例方法/属性**
   （如 `publish_to_platform()`、`PLATFORM_INFO` property）。
2. 调用方改为经 PluginManager 获取实例：
   ```python
   import flask as _flask
   _pm = _flask.current_app.extensions.get('plugin_manager')
   _sp = _pm.get_instance('social_push') if (_pm and _pm.is_enabled('social_push')) else None
   if _sp is None:
       # 降级：插件未启用
       ...
   _sp.publish_to_platform(...)
   ```
3. 插件禁用时实例为 None，调用方降级（返回提示 / 视为无该能力）。

### 12.8 前端拆分边界（Social Push 案例）

原 partial 若混入无关功能（如 social.html 尾部混入 PPT / 数字人视频），
**只迁移属于本模块的函数**，无关代码留在原 partial 原地，避免越界改动。
被迁移函数依赖的全局工具（T / esc / showToast / go）在插件模板中仍可用
（插件模板同样 include 进 admin.html 全局作用域）。

### 12.9 LLM 归属与概念分离（Social Push 缺陷改造）

**决策**：`services.ai_content_generator`（通义千问文案 + 通义万相配图）是
**全站公共 LLM 底层服务**，agent_matrix 内核自身亦依赖它。故：
- ❌ 不下沉到 agent_matrix（会造成循环依赖，且 agent_matrix 无图像生成能力）
- ❌ 不搬进插件私有（多方共享）
- ✅ 保持公共服务原地，插件通过 `from services.ai_content_generator import ...` 复用

**缺陷修复（UI/概念层）**：原 `check-config` 把 AI 文案/配图与社媒平台混在
同一 `platforms` 数组，造成"社媒号与 LLM 混放"。改造为两个字段：
- `platforms`：仅【发布渠道】（真实社媒号）
- `ai_capabilities`：【创作工具】（AI 文案/配图，非发布目标）

前端据此分区渲染：发布勾选框只含社媒平台，AI 能力单列信息区。

**死代码清理**：`_publish_douyin_video` 调用不存在的 `douyin_service.publish_video`
（必然 ImportError），连同 `PLATFORM_INFO` 的 `douyin_video` 一并删除。

### 12.10 逻辑解耦 vs 数据解耦（OAuth Config 案例）

并非所有解耦都用独立库。当迁出模块的**数据表被其他核心链路共享读取**时，
必须只做"逻辑解耦"（路由/UI 进插件），**数据表留主库**：

- **案例**：OAuth 配置管理（Phase 4A）迁入 `plugins/oauth_config/`，但
  `oauth_providers` 表被登录回调链路（auth-center 的 douyin/alipay/wechat
  `_service._get_config`）读取。若插件用独立库，配置写入插件库、登录读主库
  → 凭据读不到 → **切断登录**。
- **正确做法**：插件 `routes.py` 通过 `get_main_db()` 直接读写主库 `oauth_providers`，
  不建独立库、不写 migrate。插件只是"把路由和 UI 搬进来"。
- **判据**：迁出的表是否被 admin 之外的服务（auth-center :8083 等）读取？
  是 → 留主库（逻辑解耦）；否 → 可独立库（数据解耦，如 im_gateway/social_push）。

### 12.11 前端模板铁律：禁止 `<script>` 标签（重要）

admin 所有 partial（含插件模板）是**裸 JS**，由 core.html 开启外层大 `<script>`、
tail.html 统一闭合。插件模板**绝不能自带 `<script>...</script>`**，否则中间的
闭合标签会提前截断外层 script，导致其后所有 partial 的 JS 变成裸 HTML
（表现为满屏 `Unexpected token '<'`、`xxx is not defined`、URL 片段被当资源 404）。
插件前端模板首行应直接是 JS 或 `//` 注释，不加任何 HTML script 标签。

> **iframe 例外条款（v1.5）**：本铁律仅约束**内联 partial**（`window.l_<key>()` 裸 JS 渲染路径，
> 运行在共享 admin 页面）。走 **iframe 加载（`menu.embed_url`）的框架插件页面是独立完整 HTML 文档**，
> 允许使用 `<script>` 标签引入本地框架库与自身脚本，但必须遵守 §15「前端框架插件指南」：
> 仅限本地静态库、禁止外网 CDN、token 按 §15 传递。
> 内联路径（`l_<key>()`）**永远禁止**引入任何前端框架（全局作用域污染、版本冲突）。

---

## 13. 版本发现与升级规范（2026-08 追加）

> 本章定义插件"本地版本 vs 商店版本"的发现契约，配合
> `plugin_manager/store.py::check_updates()` 与商店目录 `store_catalog.json` 使用。
> 发布侧自动化（tag + CI）见 13.3（Phase C 预留）。

### 13.1 版本号铁律

- 插件版本号一律使用 **semver `X.Y.Z`**（如 `1.2.0`），允许 `X.Y.Z-prerelease` 预发布后缀。
- 版本唯一真源为插件目录下 `plugin.json` 的 `version` 字段；商店目录 `store_catalog.json`
  的 `version` 必须与插件包内 `plugin.json` 一致（Phase C 发布流水线强制校验，不一致拒绝发布）。
- 禁止日期型/自增型非 semver 版本号；解析失败时版本对比**退化为字符串比较**
  （`latest != installed` 即视为可更新），并打印告警日志。

### 13.2 版本对比逻辑契约（check_updates）

`StoreAPIClient.check_updates(local_versions)` 输入为 `{identifier: installed_version}`，
输出为 `{identifier: {installed, latest, has_update, min_app_version}}`，规则：

1. **只对比"本地已安装 且 商店上架（enabled=1）"的插件**；本地未安装或商店未上架不参与。
2. `has_update = parse_version(latest) > parse_version(installed)`（semver 逐段比较）。
3. 任一版本号解析失败 → 退化为 `latest != installed` 字符串比较，并输出 `⚠️` 告警日志。
4. 每次调用输出明细日志：入参数量、商店目录条数、逐插件对比结果、最终统计
   （匹配/跳过/可更新数），日志前缀统一 `[StoreAPIClient] check_updates:`。
5. **幂等**：纯查询无副作用，不写库、不触发下载；可随时重复调用。

### 13.3 发布侧：tag 命名（Phase C 预留）

- 插件发布 tag 命名：`<identifier>-v<X.Y.Z>`（如 `ads-v1.1.0`）。
- 触发 `plugin-release.yml` 流水线：打包 `plugins/<id>/` → `<id>-vX.Y.Z.zip` + SHA256 →
- 上传 verorun-store Release → 更新 `store_catalog.json` 对应条目。
- ★v1.4：从 `plugin.json` 提取 `icon_url`、`screenshots`、`readme_url` 并写入
  `store_catalog.json` 对应条目（无需 Store Admin 手动录入）。
- 主系统版本 tag `vX.Y.Z` 与插件 tag 互不影响，两者可独立发布。

### 13.4 升级侧契约（Phase B 预留）

- 前端仅在 `has_update=true` 时显示升级入口（当前为徽标展示，升级按钮随 Phase B 落地）。
- 升级前必须：备份旧版本目录 → 校验 `min_app_version` 与系统版本 → SHA256 校验下载包。
- 升级后以"重启生效"为准；升级失败自动回滚备份。

### 13.5 验证步骤

1. Store Admin 造一条 version 高于本地插件的记录。
2. 访问 `/admin/plugins/unified`：本地列表对应插件 `has_update=true`、`latest_version` 正确。
3. 访问 `/admin/plugins/store/browse`：卡片显示 `🔄 vX.Y.Z Upgrade available` 徽标，
   已安装插件显示 `Installed` 徽标。
4. 检查服务日志中 `[StoreAPIClient] check_updates:` 明细输出。

---

## 14. 商店展示规范（2026-08 追加，v1.4）

> 本章定义插件在商店中的展示契约，配合 `admin/templates/partials/plugins_store.html`
> 的卡片 + 详情弹窗渲染使用。

### 14.1 卡片层展示

商店卡片仅展示摘要信息，不提供直接安装入口。

| 展示项 | 数据来源 | 说明 |
|--------|----------|------|
| 缩略图 | `store_plugins.icon_url` | 推荐 280x120px。为空时显示分类占位符 |
| 名称 | `store_plugins.name` | — |
| 版本号 | `store_plugins.version` | 显示为 `vX.Y.Z` |
| 简介 | `store_plugins.description` | 最多 2 行，超出截断 |
| 评分 | `plugin_reviews` 聚合 | 星级 + 评价数 |
| 价格 | `store_plugins.price_type` | Free / ¥金额 / $金额 |
| 已安装状态 | `plugin_registry` 比对 | Installed 徽标 |
| 可升级徽标 | `check_updates()` | 🔄 vX.Y.Z Upgrade available |
| 操作按钮 | — | 统一为「详情」按钮，无安装入口 |

### 14.2 详情弹窗展示

详情弹窗承载完整决策信息与唯一安装入口。

| 标签页 | 内容 | 数据来源 |
|--------|------|----------|
| 描述 | 完整描述 + 截图 | `store_plugins.description` + `screenshots` |
| README | README 全文（Markdown 渲染） | `store_plugins.readme_url` |
| 评价 | 评价列表 + 评价表单 | `plugin_reviews` 表 |

### 14.3 安装入口

安装/购买按钮**仅在详情弹窗底部**出现，卡片层不提供安装入口。

| 插件状态 | 按钮文字 | 行为 |
|----------|----------|------|
| 已安装 | Installed 徽标 | 无操作 |
| 未安装 + 免费 | Install | `storeInstallPlugin()` |
| 未安装 + 付费 | Purchase | `showPurchaseDialog()` |
| 已安装 + 有更新 | Upgrade | `storeInstallPlugin()`（Phase B 后 `upgrade()`） |

### 14.4 资源托管要求

- `icon_url`：同源 CDN 或公开可访问 URL，推荐 280x120px PNG/JPG
- `screenshots`：同源 CDN，推荐 1024x576px，最多 5 张
- `readme_url`：同源 CDN 或 GitHub Raw URL，Markdown 格式
- 资源加载失败时前端应有降级展示（占位符 / 新窗口打开链接）

### 14.5 与 CI 发布流水线的关系（Phase C 预留）

Phase C 落地后，`plugin.json` 中声明的 `icon_url`、`screenshots`、`readme_url`
将被 CI 自动提取并写入 `store_catalog.json` 对应条目，无需 Store Admin 手动录入。
当前阶段这些字段通过 Store Admin 手动维护。

### 14.6 向后兼容性

`icon_url`、`screenshots`、`readme_url` 三个字段均为可选。
旧 `plugin.json` 不加这些字段，`PluginInfo` 自动给默认值（空字符串/空数组），
安装和展示照常工作。卡片和详情弹窗对空值有降级处理（占位符 / 隐藏标签页）。

---

## 15. 前端框架插件指南（2026-08 追加，v1.5）

> 本指南面向习惯使用 React/Vue 的插件开发者。框架支持是**可选便利层**，
> 不是迁移要求——存量原生 JS 插件零影响。

### 15.1 支持范围与硬边界

| 项 | 规则 |
|----|------|
| 加载路径 | **强制 iframe**（`menu.embed_url` 声明独立页面路由）；内联 `l_<key>()` 路径**永远禁止**框架 |
| 受支持框架 | React 18.3.x（UMD）、Vue 3.4.x（UMD） |
| 框架库来源 | 仅限系统本地静态库，**禁止外网 CDN** |
| 存量插件 | 零迁移，本指南仅适用于新框架插件 |

### 15.2 本地框架库

系统提供（vendored 静态文件，随代码分发）：

| 库 | 路径 | 版本 |
|----|------|------|
| React | `admin/static/lib/workflow/react.production.min.js` | 18.3.1 |
| ReactDOM | `admin/static/lib/workflow/react-dom.production.min.js` | 18.3.1 |
| Vue | `admin/static/lib/plugin-frameworks/vue.global.prod.js` | 3.4.38 |

> iframe 页面经 Admin 蓝图静态路由可访问（`/static/lib/...`）。
> **禁止**自行引用 unpkg / jsdelivr / cdnjs 等外网 CDN（§16 审核必查）。
>
> Vue 3.4.38 SHA256（锁定）：`B50EEEFE35D41636BB96C92B40F1DF0B4FB7914E07B3C625B1EC15E9748767B9`

### 15.3 iframe 页面模板（最小骨架）

```html
<!DOCTYPE html>
<html lang="{{ g.lang_code or 'zh-CN' }}">
<head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="/static/css/design-system.css"/>
<script src="/static/lib/plugin-frameworks/vue.global.prod.js"></script>
<script>window.__SSO_TOKEN = {{ sso_token|tojson }};</script>
</head>
<body>
<div id="app"></div>
<script src="/plugin/<id>/static/js/app.js"></script>
</body>
</html>
```

### 15.4 SSO 鉴权（token）

- iframe 加载时 `goPlugin()` 通过 URL 参数注入 token：`embed_url?token=...`
- 插件页面后端路由校验 `?token=`（与现 ali_api / analytics 同模式）
- **禁止**将 token 发送到任何第三方域名；页面内请求仅允许同域 API

### 15.5 i18n 注入（window.__t）

`_()` 为服务端 Jinja2 函数，框架组件无法直接调用。服务端渲染 iframe 页面时将翻译字典注入：

```html
<script>
window.__t = {{ translations|tojson }};
window.__locale = '{{ g.lang_code or "zh-CN" }}';
</script>
```

组件内通过 `window.__t['key']` 读取，缺失键回退英文源串。插件 i18n 文件仍放 `plugins/<id>/i18n/{zh-CN,en}.yml`。

### 15.6 样式约定

- 引用 `design-system.css`（仅变量），使用系统标准变量名（`--bg-card`、`--text`、`--border` 等）
- 禁止硬编码色值，与主站/Admin 视觉保持一致

### 15.7 安全红线（审核必查，见 §16）

1. 禁止外网 CDN 脚本
2. 禁止 token / Cookie 外泄到第三方域
3. 禁止 `eval(` / `new Function(` / `innerHTML` 拼接不可信数据
4. 提交打包产物必须附 `src/` 源码 + 可复现构建命令

---

## 16. 插件审核规范（2026-08 追加，v1.5）

> 审核针对**所有提交商店/发布的插件**，后端 Python 与前端 JS/HTML **同等覆盖**。
> React/Vue 框架插件因打包混淆，额外要求源码包与可复现构建。

### 16.1 审核范围

| 维度 | 覆盖 |
|------|------|
| 后端 Python | 危险执行（subprocess / eval / os.system）、SQL 拼接、pickle 反序列化、硬编码凭据 |
| 前端 JS/HTML | 外网 CDN、token / Cookie 外泄、XSS（eval / new Function / innerHTML）、document.write |
| 框架插件（React/Vue） | 依赖清单（package.json / lock）、源码 + 可复现构建、打包产物与源码一致性 |

### 16.2 审核方式（AI 辅助 + 人工审批）

- 审核由 **VeroRun AI Agent** 依据本规范及设计文档执行（提示词规则另行维护）
- Agent 输出**结构化审核报告**（findings / severity / verdict），供人工快速复核
- **人工审批兜底**：verdict 仅作建议，最终放行由管理员决定（approval 节点）

### 16.3 审核流程（工作流）

```
触发（提交商店 / 发布前）
  → 采集插件源码 + 设计文档
  → AI Agent 对照规范审查 → 结构化报告
  → 人工审批（approval）
  → 通知结果 + 记录审核日志
```

### 16.4 审核挂点

| 阶段 | 动作 |
|------|------|
| 发布前（publish） | 门禁：AI 审核 + 人工审批通过后方可发布 |
| 商店提交（submit_plugin） | 接入同一审核流程 |
| 人工复核 | 支持随时对已安装插件发起复审 |

### 16.5 提示词规则

> ⏳ 维护中：具体提示词模板与工作流配置在后续批次补充（见方案文档
> `文档/plugin-react-vue-support-plan.md`）。审核判定标准以 §16.1 范围为准。

