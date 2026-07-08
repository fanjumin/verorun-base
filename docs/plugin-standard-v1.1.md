# 插件标准 v1.1 — 完整规范

> 生成日期：2026-07-08
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
│   ├── name               string   ★必填   显示名称，如 "1688 供应链采集"
│   ├── version            string   ★必填   语义化版本号
│   ├── description        string           描述
│   ├── author             string           作者
│   └── min_app_version    string           最低系统版本
│
├── ★ 分类与展示（v1.1 新增）
│   ├── category           string           插件分类
│   ├── icon               string           图标名（复用 icons.html 体系）
│   └── tags               string[]         标签数组
│
├── 依赖与配置
│   ├── depends_on         object           {identifier: version_spec}
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
  "name": "1688 供应链采集",
  "identifier": "ali_api",
  "version": "0.3.0",
  "description": "1688 供应链采集 — 商品搜索、AI 优化、本地商城发布",
  "author": "VeroRun",
  "min_app_version": "0.10.0",

  "category": "supply_chain",
  "icon": "package",
  "tags": ["电商", "采集", "AI"],

  "depends_on": {},

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
