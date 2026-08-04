# 商品评价系统 (reviews)

## 概述

商品评价系统（reviews）是 VeroRun 的商品用户评价插件，允许已购买用户对商品进行打分、写评价和晒图。插件使用独立数据库 `reviews.db`，路由在 `__init__.py` 中以内联 Blueprint 方式定义，无管理菜单。

## 功能特性

- **商品打分**：支持 1-5 星评分，自动统计好评率、中评率、差评率
- **文字评价**：用户可撰写详细评价内容，支持多语言
- **图片晒单**：支持上传商品实拍图片，图片统计独立展示
- **匿名评价**：用户可选择匿名发表评价，保护隐私
- **购买验证**：评价前验证用户是否已购买该商品，防止虚假评价
- **评价管理**：用户可删除自己的评价（软删除，设置 `is_active=0`）
- **管理审核**：提供管理端评价审核和回复功能
- **评价统计**：自动统计商品评分分布、平均分、晒图数等

## 架构设计

### 数据库策略

使用**独立数据库** `reviews.db`（SQLite），存储评价数据。同时**跨库读取**主库中的 `users`（用户信息）、`products`（商品信息）、`order_items`（购买验证）等表。

### 模块结构

```
reviews/
├── __init__.py          # 插件入口 + 路由定义，ReviewsPlugin 类 + Blueprint
├── models.py            # 数据模型，数据库初始化
├── reviews.db           # 独立 SQLite 数据库
└── i18n/
    ├── en.yml
    └── zh-CN.yml
```

## 目录结构

| 文件/目录 | 说明 |
|-----------|------|
| `__init__.py` | 插件入口 + 路由定义，`ReviewsPlugin` 类定义，`register_routes()` 内联定义 Blueprint 和所有 API 端点 |
| `models.py` | 数据模型层，提供 `get_db()`（独立库）、`get_main_db()`（主库）、`init_db()` 初始化数据库 |
| `reviews.db` | 独立 SQLite 数据库文件 |
| `i18n/en.yml` | 英文翻译 |
| `i18n/zh-CN.yml` | 中文翻译 |

## 安装与启用

### 安装

插件已内置在 `plugins/reviews/` 目录下。VeroRun 启动时会自动扫描并注册。

### 启用

插件默认启用（`enabled: true`）。启用时执行：

1. 调用 `init_db()` 初始化独立数据库 `reviews.db`
2. 注册 `ORDER_PAID` 事件监听器，支付成功后记录可评价状态
3. 注册 Flask 蓝图路由（路由前缀：`/plugin/reviews`）

## 配置说明

`plugin.json` 中无额外配置项（`config: {}`），所有配置使用默认行为。

权限配置：

| 权限标识 | 说明 |
|----------|------|
| `shop.product.read` | 读取商品数据（用于评价关联） |
| `user.read` | 读取用户数据（用于评价展示） |

## API 端点

### 提供的 Hook 接口

| Hook 名称 | 功能描述 |
|-----------|----------|
| `review/validate` | 验证评价的有效性（是否已购买、是否重复评价等） |

### 用户端 API

通过 Blueprint（路由前缀 `/plugin/reviews`）提供以下端点：

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/<product_id>` | GET | 获取商品评价列表（支持分页、评分筛选、晒图筛选） |
| `/api/<product_id>/create` | POST | 提交商品评价（需登录，需已购买） |
| `/api/<review_id>` | DELETE | 删除自己的评价（软删除） |
| `/api/user/reviews` | GET | 获取当前用户的评价列表 |

### 管理端 API

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/reviews` | GET | 管理端评价审核列表（需管理员权限） |
| `/admin/reviews/<rid>/reply` | POST | 管理端回复评价（需管理员权限） |

## 依赖关系

### 事件监听

| 事件名称 | 处理逻辑 |
|----------|----------|
| `order/completed` | 订单完成后，记录订单可评价状态，用户可在订单页写评价 |

### 事件提供

本插件向事件总线提供 `review/validate` Hook，供其他插件验证评价有效性。

### 外部依赖

- 依赖 VeroRun 核心框架的 `BasePlugin`、事件总线（`EventName.ORDER_PAID`）、JWT 服务（`validate_token`）、i18n 模块
- 无外部第三方服务依赖

### 菜单集成

本插件**无管理菜单**，所有功能通过 API 和前端页面集成。

## 许可证

作为 VeroRun 项目的一部分，遵循项目统一许可证。