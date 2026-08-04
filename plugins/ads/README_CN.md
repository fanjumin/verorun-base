# Ad Management (ads)

## 概述

Ad Management（广告管理）是 VeroRun 的广告投放管理插件，负责广告位管理、广告展示/点击统计，并提供 AI-Ready 的 API 接口。插件使用独立数据库 `ads.db`，不依赖主库。

## 功能特性

- **广告位管理**：支持创建、编辑、删除广告位，按区域（zones）分类管理
- **展示/点击统计**：自动记录广告展示次数（impression）和点击次数（click），支持数据聚合与分析
- **AI-Ready API**：提供标准化的 Hook 接口，供 AI 代理和外部系统调用，实现智能广告投放
- **多站点支持**：广告位可绑定到不同站点，支持跨站点广告管理
- **管理后台**：内置管理界面 `admin_ads.html`，支持可视化配置广告位
- **前端渲染组件**：提供 `render_ads.html` 模板和 `ads.js` 前端脚本，支持广告的客户端渲染

## 架构设计

### 数据库策略

使用**独立数据库** `ads.db`（SQLite），完全与主库解耦。数据库文件位于插件目录下，包含以下表：

- `ad_placements`：广告位定义（名称、区域、尺寸、状态等）
- `ad_impressions`：广告展示记录（广告位 ID、时间戳、用户标识等）
- `ad_clicks`：广告点击记录（广告位 ID、时间戳、用户标识、来源 URL 等）

### 模块结构

```
ads/
├── __init__.py          # 插件入口，AdsPlugin 类定义，生命周期管理
├── models.py            # 数据模型，数据库初始化与 CRUD 操作
├── routes.py            # Flask 蓝图路由，管理后台 API 端点
├── ai_tools.py          # AI 工具函数，暴露给 AI 代理的标准接口
├── templates/
│   ├── admin_ads.html   # 管理后台界面模板
│   └── render_ads.html  # 前端广告渲染模板
├── static/
│   └── ads.js           # 前端广告渲染脚本
└── i18n/
    ├── en.yml           # 英文翻译
    └── zh-CN.yml        # 中文翻译
```

## 目录结构

| 文件/目录 | 说明 |
|-----------|------|
| `__init__.py` | 插件入口，定义 `AdsPlugin` 类，处理安装/启用/禁用生命周期 |
| `models.py` | 数据模型层，提供 `init_ad_db()` 初始化数据库，定义表结构 |
| `routes.py` | 路由层，提供 `ads_bp` 蓝图，暴露管理后台 API |
| `ai_tools.py` | AI 工具层，封装 `get_placements`、`record_impression` 等 AI 可调用函数 |
| `plugin.json` | 插件元数据配置，定义菜单、权限、Hook、设定项 |
| `templates/admin_ads.html` | 管理后台页面 |
| `templates/render_ads.html` | 前端广告渲染模板 |
| `static/ads.js` | 前端广告渲染与统计脚本 |
| `i18n/en.yml` | 英文国际化翻译 |
| `i18n/zh-CN.yml` | 中文国际化翻译 |
| `ads.db` | 独立 SQLite 数据库文件 |

## 安装与启用

### 安装

插件已内置在 `plugins/ads/` 目录下。VeroRun 启动时会自动扫描并注册插件。

### 启用

插件默认启用（`enabled: true`）。启用时执行以下步骤：

1. 调用 `init_ad_db()` 初始化独立数据库 `ads.db`（幂等操作）
2. 注入 i18n 翻译函数
3. 注册 Flask 蓝图路由

### 手动控制

在管理后台的插件管理页面，可以手动启用/禁用此插件。禁用后广告位将不再渲染，但数据库和数据保留。

## 配置说明

`plugin.json` 中的配置项：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `default_width` | integer | 320 | 默认广告宽度（像素） |
| `default_height` | integer | 0 | 默认广告高度（0 = 自适应） |
| `max_placements` | integer | 50 | 最大广告位数量限制 |

权限配置：

| 权限标识 | 说明 |
|----------|------|
| `ads.read` | 读取广告位和统计数据 |
| `ads.write` | 创建/修改/删除广告位 |

## API 端点

### 提供的 Hook 接口

| Hook 名称 | 功能描述 |
|-----------|----------|
| `ads/get_placements` | 获取所有或指定区域的广告位列表 |
| `ads/render_ad` | 渲染指定广告位的 HTML 内容 |
| `ads/get_stats` | 获取广告位的展示/点击统计数据 |
| `ads/record_impression` | 记录一次广告展示事件 |
| `ads/record_click` | 记录一次广告点击事件 |

### 管理后台路由

通过 `ads_bp` 蓝图注册，提供 RESTful API 用于广告位 CRUD 操作和统计查询。

## 依赖关系

### 事件监听

本插件不监听任何系统事件。

### 事件提供

本插件向事件总线提供以上 5 个 Hook 接口，供其他插件和 AI 代理调用。

### 外部依赖

- 无外部服务依赖
- 依赖 VeroRun 核心框架的 `BasePlugin`、事件总线、i18n 模块

### 菜单集成

- **菜单组**：AI & Content
- **菜单项**：Ad Management（图标：ads）

## 许可证

作为 VeroRun 项目的一部分，遵循项目统一许可证。