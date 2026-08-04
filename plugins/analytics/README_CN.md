# Analytics (analytics)

## 概述

Analytics 是 VeroRun 的服务端无 Cookie 分析中间件插件，提供完整的网站访问数据采集、存储、聚合与可视化能力。插件通过无 Cookie 的轻量级追踪方式，在不依赖客户端 Cookie 的前提下实现 PV/UV 统计、访问者会话识别、页面级行为分析、地理位置解析以及趋势分析等功能。

版本：**1.2.0**

## 功能特性

- **无 Cookie 追踪**：基于服务端指纹（IP + User-Agent 组合哈希）实现访问者识别，无需依赖客户端 Cookie，符合隐私合规要求
- **PV/UV 统计**：精确记录页面浏览量（Page View）和独立访客数（Unique Visitor）
- **访问者会话管理**：基于时间窗口自动识别和合并访问者会话
- **页面级统计**：按页面路径、来源、设备类型等维度进行细粒度统计分析
- **地理位置解析**：集成 ip2region 库，通过 IP 地址解析访问者地理位置（国家/省份/城市）
- **用户代理解析**：内置 UA 解析器，识别浏览器、操作系统、设备类型
- **趋势分析**：提供按时间维度（小时/天/周/月）的访问趋势数据
- **实时仪表盘**：通过后台管理面板嵌入展示实时和历史的分析数据
- **后台聚合**：独立的聚合线程每 60 秒自动运行，将原始追踪数据聚合为统计指标
- **Workflow 集成**：通过 workflow_nodes 模块支持在工作流中调用分析数据

## 架构设计

### 数据库策略

插件使用**独立数据库**，实际部署中使用 PostgreSQL 的 `analytics` schema 进行数据存储。本地开发环境使用 SQLite 文件 `data/analytics.db`。

### 模块结构

```
┌─────────────────────────────────────────────────┐
│                  middleware.py                    │
│           (请求拦截与原始数据采集)                  │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                   tracker.py                     │
│              (行为追踪与事件记录)                   │
└─────────────────────┬───────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  ua_parser   │ │  geoip   │ │  models.py   │
│  (UA 解析)    │ │ (IP 定位) │ │  (11张分析表) │
└──────────────┘ └──────────┘ └──────┬───────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────┐
│                 processor.py                     │
│            (后台聚合线程 / 每60秒运行)              │
└─────────────────────┬───────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  dashboard   │ │   cli    │ │ workflow_    │
│  (仪表盘注入) │ │ (命令行)  │ │ nodes (工作流) │
└──────────────┘ └──────────┘ └──────────────┘
```

### 11 张分析表

插件在 PostgreSQL `analytics` schema 中维护以下数据表：

| 表名 | 用途 |
|------|------|
| `analytics_pageviews` | 原始页面浏览记录 |
| `analytics_visitors` | 访问者标识与会话信息 |
| `analytics_sessions` | 访问者会话聚合 |
| `analytics_pages` | 页面维度统计 |
| `analytics_referrers` | 来源统计 |
| `analytics_devices` | 设备类型统计 |
| `analytics_browsers` | 浏览器类型统计 |
| `analytics_os` | 操作系统统计 |
| `analytics_locations` | 地理位置统计 |
| `analytics_hourly` | 按小时聚合趋势 |
| `analytics_daily` | 按天聚合趋势 |

## 目录结构

```
analytics/
├── __init__.py              # 插件入口，注册 Hook 与中间件
├── models.py                # 11 张分析数据表的 ORM 模型定义
├── middleware.py             # 服务端无 Cookie 分析中间件
├── processor.py             # 后台聚合处理线程（每 60 秒运行）
├── tracker.py               # 事件追踪器，记录原始行为数据
├── geoip.py                 # IP 地理位置解析（基于 ip2region）
├── ua_parser.py             # User-Agent 解析器
├── dashboard.py             # 仪表盘数据注入（dashboard.data filter）
├── cli.py                   # 命令行工具（CLI 命令）
├── workflow_nodes.py        # Workflow 引擎集成节点
├── migrate_analytics.py     # 数据库迁移脚本
├── plugin.json              # 插件元数据配置
├── data/
│   ├── analytics.db         # 本地开发 SQLite 数据库
│   └── ip2region_v4.xdb     # ip2region IP 地理位置数据库
├── ip2region/
│   ├── __init__.py
│   ├── searcher.py          # ip2region 查询引擎
│   └── util.py              # ip2region 工具函数
├── i18n/
│   ├── en.yml               # 英文国际化
│   └── zh-CN.yml            # 中文国际化
├── static/
│   ├── china.json           # 中国地图数据
│   └── world.json           # 世界地图数据
└── templates/
    └── analytics.html       # 管理后台仪表盘模板
```

## 安装与启用

### 安装

插件已包含在 VeroRun 的默认插件目录中，无需额外安装步骤。

### 启用

1. 确保 PostgreSQL 数据库中存在 `analytics` schema
2. 运行数据库迁移脚本：

```bash
python -m plugins.analytics.migrate_analytics
```

3. 在 VeroRun 管理后台 "插件管理" 页面中启用 Analytics 插件
4. 中间件将在启用后自动开始拦截请求并采集数据

### 本地开发

本地开发时，插件会自动使用 SQLite 数据库 `data/analytics.db`。无需额外配置即可运行。

## 配置说明

在 `plugin.json` 中配置以下参数：

```json
{
  "name": "analytics",
  "version": "1.2.0",
  "database": {
    "type": "postgresql",
    "schema": "analytics"
  },
  "aggregation": {
    "interval_seconds": 60
  },
  "middleware": {
    "enabled": true,
    "exclude_paths": ["/admin/*", "/static/*", "/api/health"]
  },
  "ip2region": {
    "db_path": "data/ip2region_v4.xdb"
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `database.schema` | PostgreSQL schema 名称 | `analytics` |
| `aggregation.interval_seconds` | 聚合线程运行间隔（秒） | `60` |
| `middleware.enabled` | 是否启用中间件 | `true` |
| `middleware.exclude_paths` | 排除的路径模式列表 | 管理后台与静态资源 |
| `ip2region.db_path` | ip2region 数据库文件路径 | `data/ip2region_v4.xdb` |

## API 端点

### Hook 提供

| Hook 标识符 | 类型 | 说明 |
|-------------|------|------|
| `analytics/track_event` | Hook | 手动记录自定义分析事件 |
| `analytics/get_realtime` | Hook | 获取实时分析数据（当前在线人数、今日 PV/UV） |
| `analytics/get_trend` | Hook | 获取指定时间范围的分析趋势数据 |

### 管理后台

| 路径 | 说明 |
|------|------|
| `/admin/analytics/` | 分析仪表盘（嵌入页面） |

### Filter 注册

| Filter 标识符 | 说明 |
|---------------|------|
| `dashboard.data` | 模块级注册，向管理后台仪表盘注入分析数据摘要 |

## 依赖关系

### 内部依赖

- VeroRun 核心框架：中间件注册、Hook 系统、事件总线
- 管理后台（auth-center）：仪表盘嵌入与菜单渲染

### 外部依赖

- **ip2region**：IP 地理位置解析库，使用 `data/ip2region_v4.xdb` 离线数据库
- **PostgreSQL**：生产环境数据存储（`analytics` schema）

### 被依赖

- **health_check** 插件：可通过 `analytics/get_trend` Hook 获取访问趋势进行健康分析
- **Workflow 引擎**：通过 `workflow_nodes.py` 在工作流中调用分析数据

### 菜单

- **菜单组**：`Monitoring & Data`
- **嵌入 URL**：`/admin/analytics/`

## 许可证

本插件为 VeroRun 项目的一部分，遵循 VeroRun 项目的整体许可证协议。