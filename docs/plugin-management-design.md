# 插件管理系统设计方案

## 一、主流系统插件管理调研

### 1. Jenkins（Java/CI 平台）
| 特性 | 实现方式 |
|------|----------|
| **扩展点** | Extension Points（接口定义）→ Extensions（插件实现），自动发现装配 |
| **生命周期** | 安装 → 加载 → 初始化 → 运行 → 卸载 |
| **隔离** | 每个插件独立 ClassLoader，插件间可声明依赖 |
| **配置** | `META-INF/MANIFEST.MF` 声明元信息（ID、版本、依赖） |
| **管理 UI** | Web 界面：查看/安装/启用/禁用/卸载，有 Update Center |
| **依赖** | 插件间可声明依赖性，Maven 管理构建 |
| **分发** | Update Center 自动检测发布，HPI 包格式 |

### 2. WordPress（PHP/CMS）
| 特性 | 实现方式 |
|------|----------|
| **扩展机制** | **Hook 系统**：Actions（事件触发）+ Filters（数据过滤） |
| **生命周期** | 激活 → 运行 → 停用 → 卸载 |
| **目录结构** | `wp-content/plugins/<plugin-name>/`，主文件头信息声明元数据 |
| **数据库** | 插件自主管理（CREATE TABLE 在激活时执行） |
| **管理 UI** | 后台「插件」页面：搜索/安装/激活/停用/删除 |
| **生态** | WordPress.org Plugin Directory，自动更新检查 |
| **钩子优先级** | 每个钩子可设置优先级（默认 10），控制执行顺序 |

### 3. VS Code（TypeScript/编辑器）
| 特性 | 实现方式 |
|------|----------|
| **隔离** | **独立 Extension Host 进程**，插件崩溃不影响主进程 |
| **懒加载** | `activationEvents` 声明触发条件，条件满足才加载 |
| **元信息** | `package.json` 扩展字段：contributes、activationEvents |
| **生命周期** | `activate()` → 运行时 → `deactivate()` |
| **管理 UI** | 内置 Extensions 面板：搜索/安装/禁用/卸载 |
| **分发** | VSIX 包，Marketplace 发布 |

### 4. Drupal（PHP/CMS）
| 特性 | 实现方式 |
|------|----------|
| **双层机制** | **Plugin System**（功能组件）+ **Hook System**（事件通信） |
| **插件发现** | Annotation（注解）+ YAML + Hook，Plugin Manager 统一管理 |
| **插件类型** | Block、Field、Views Style 等，每种类型独立接口+管理器 |
| **服务容器** | 插件通过 Symfony DI 容器注入依赖 |
| **生命周期** | 安装 → 启用 → 运行 → 禁用 → 卸载 |
| **管理 UI** | 后台「扩展」页面：浏览/安装/启用/禁用/卸载 |

### 5. Flask（Python/Web）
| 特性 | 实现方式 |
|------|----------|
| **Blueprint** | 路由分组，注册到 APP，不支持卸载 |
| **Extension 模式** | Class + `init_app()` 双阶段初始化，支持工厂模式 |
| **配置** | `app.config` 统一管理 |
| **无内置管理** | Flask 不提供插件管理 UI，需自行实现 |

---

## 二、共性规律总结

```
┌─────────────────────────────────────────────────────┐
│                    插件管理系统                        │
├─────────────┬─────────────┬─────────────┬────────────┤
│  元信息管理  │  生命周期    │   资源隔离   │   管理接口  │
├─────────────┼─────────────┼─────────────┼────────────┤
│ • 名称/版本  │ • 安装      │ • 独立数据库  │ • 列表查看  │
│ • 作者/描述  │ • 启用/禁用  │ • 独立路由   │ • 安装/卸载  │
│ • 依赖声明   │ • 运行      │ • 进程隔离   │ • 启用/禁用  │
│ • 兼容版本   │ • 卸载      │ • 依赖管理   │ • 配置管理   │
└─────────────┴─────────────┴─────────────┴────────────┘
```

---

## 三、本项目方案

### 3.1 整体架构

```
app/
├── core/                           # 核心（不可卸载）
│   ├── models.py                   # 主库 126 张表
│   ├── routes/                     # 核心路由
│   └── services/                   # JWT、事件总线等
│
├── plugin_manager/                 # ★ 新增：插件管理器
│   ├── __init__.py                 # PluginManager 类
│   ├── models.py                   # plugin_registry 表
│   ├── routes.py                   # 管理 API
│   └── templates/                  # 管理界面
│
└── plugins/                        # 插件目录（每个独立）
    ├── ali_api/
    │   ├── plugin.json             # ★ 新增：插件元信息
    │   ├── models.py
    │   └── ...
    ├── coupons/
    │   ├── plugin.json             # ★ 新增
    │   ├── models.py               # ✅ 已有
    │   └── ...
    ├── reviews/
    │   ├── plugin.json             # ★ 新增
    │   ├── models.py               # ✅ 已有
    │   └── ...
    ├── wishlist/
    │   ├── plugin.json             # ★ 新增
    │   ├── models.py               # ✅ 已有
    │   └── ...
    └── order_notify/
        ├── plugin.json             # ★ 新增
        └── ...
```

### 3.2 插件元信息（plugin.json）

```json
{
  "name": "coupons",
  "version": "0.1.0",
  "title": "智能优惠券引擎",
  "description": "场景券 / AI 推荐 / 订阅联动",
  "author": "VeroRun",
  "license": "MIT",
  "min_app_version": "1.0.0",
  "dependencies": [],
  "has_db": true,
  "db_tables": ["coupons", "coupon_redemptions"],
  "routes_prefix": "/plugin/coupons"
}
```

### 3.3 生命周期

```
安装 → 启用 → 运行 → 禁用 → 卸载
 ↓       ↓              ↓
创建DB  注册路由        删除DB
写入注册表              清注册表
```

| 阶段 | 操作 | 实现状态 |
|------|------|----------|
| **安装** | 创建独立库 + 写 plugin_registry | `on_install()` ✅ |
| **启用** | 注册蓝图到 Flask app | `on_enable()` + `register_routes()` ✅ |
| **禁用** | 摘除路由（Flask 不支持，需重启） | 需扩展 |
| **卸载** | 删除独立库 + 删注册记录 | 未实现 |

### 3.4 插件注册表（主库）

```sql
CREATE TABLE plugin_registry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT UNIQUE NOT NULL,
    version         TEXT NOT NULL,
    title           TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    author          TEXT DEFAULT '',
    is_active       INTEGER DEFAULT 0,
    is_installed    INTEGER DEFAULT 0,
    has_db          INTEGER DEFAULT 0,
    installed_at    TEXT,
    updated_at      TEXT,
    config_json     TEXT DEFAULT '{}'
);
```

### 3.5 管理 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/plugin-manager/list` | GET | 列出所有插件（含状态） |
| `/plugin-manager/install/<name>` | POST | 安装插件 |
| `/plugin-manager/uninstall/<name>` | POST | 卸载插件 |
| `/plugin-manager/enable/<name>` | POST | 启用插件（需重启） |
| `/plugin-manager/disable/<name>` | POST | 禁用插件 |
| `/plugin-manager/config/<name>` | GET/POST | 插件配置 |

### 3.6 与现有代码的关系

| 现有组件 | 改动 |
|----------|------|
| `plugins/base.py` | 扩展 BasePlugin：增加 `on_uninstall()`、`get_manifest()` |
| 各插件 `__init__.py` | 新增 `plugin.json`，其余不动 |
| `sync_schema.py` | 无需改动（已排除插件表） |

---

## 四、实施计划

### 阶段一：基础框架（P0）
- 创建 `plugin_manager/` 模块（model + route + manager）
- plugin_registry 表（放入主库）
- 扩展 BasePlugin：`on_uninstall()`、`get_manifest()`
- 扫描 plugins/ 目录发现所有插件

### 阶段二：管理 API（P0）
- 安装/卸载/启用/禁用 API
- 插件列表/状态查询 API
- 管理后台前端页面

### 阶段三：插件标准化（P1）
- 5 个插件各创建 plugin.json
- 统一生命周期回调
- install.py 集成插件管理器

### 阶段四：高级功能（P2）
- 插件配置持久化
- 依赖检查
- 更新机制
