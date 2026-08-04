# Subscription (subscription)

## 概述

Subscription（统一按需订阅管理）是 VeroRun 的核心订阅计费插件，采用按 Feature/SKU 独立订阅模式，废弃传统套餐制。支持双环境支付路由（CN 环境使用支付宝/微信支付，INTL 环境使用 Stripe/PayPal），实现按需付费的灵活计费体系。

## 功能特性

- **按 Feature/SKU 独立订阅**：每个功能或 SKU 独立计费，用户可按需订阅，无需购买固定套餐
- **双环境支付路由**：自动根据站点域名判断市场环境（verorun.cn 或 verorun.com），路由到对应支付渠道
- **试用期支持**：可配置免费试用天数，新用户自动获得试用资格
- **宽限期管理**：订阅到期后有可配置的宽限期，避免服务立即中断
- **自动续费**：支持默认开启自动续费，减少用户手动续费操作
- **订阅全生命周期管理**：提供 `subscribe`、`cancel`、`renew` 全流程 Hook
- **定时任务**：`scheduler.py` 定期检查订阅状态，处理到期提醒和自动续费
- **种子数据**：内置默认 SKU 目录，安装时自动填充

## 架构设计

### 数据库策略

使用**独立数据库**（通过 `models.py` 中的 `init_tables()` 初始化），存储订阅记录、SKU 目录、支付记录等核心数据。订阅状态查询时可跨库读取主库用户信息。

### 模块结构

```
subscription/
├── __init__.py                # 插件入口，SubscriptionPlugin 类定义
├── models.py                  # 数据模型，数据库初始化，种子数据
├── routes.py                  # Flask 蓝图路由，订阅页面与 API
├── services.py                # 核心服务层，订阅逻辑处理
├── scheduler.py               # 定时调度器，到期检查与提醒
├── gateways/
│   ├── __init__.py
│   ├── alipay.py              # 支付宝支付网关
│   ├── wechat.py              # 微信支付网关
│   ├── stripe.py              # Stripe 支付网关
│   └── paypal.py              # PayPal 支付网关
├── templates/
│   ├── subscribe.html         # 用户订阅页面
│   └── subscribe_admin.html   # 管理后台页面
└── i18n/
    ├── en.yml
    └── zh-CN.yml
```

## 目录结构

| 文件/目录 | 说明 |
|-----------|------|
| `__init__.py` | 插件入口，定义 `SubscriptionPlugin` 类，处理生命周期 |
| `models.py` | 数据模型层，提供 `init_tables()` 初始化数据库，`seed_default_items()` 填充种子数据 |
| `routes.py` | 路由层，提供订阅页面和 API 端点 |
| `services.py` | 核心服务层，`SubscriptionService` 实现订阅的创建、查询、取消、续费等逻辑 |
| `scheduler.py` | 定时调度器，定期检查订阅到期状态，触发提醒和自动续费 |
| `gateways/alipay.py` | 支付宝支付网关实现 |
| `gateways/wechat.py` | 微信支付网关实现 |
| `gateways/stripe.py` | Stripe 支付网关实现 |
| `gateways/paypal.py` | PayPal 支付网关实现 |
| `templates/subscribe.html` | 用户订阅页面模板 |
| `templates/subscribe_admin.html` | 管理后台页面模板 |
| `i18n/en.yml` | 英文翻译 |
| `i18n/zh-CN.yml` | 中文翻译 |

## 安装与启用

### 安装

插件已内置在 `plugins/subscription/` 目录下。VeroRun 启动时会自动扫描并注册。

### 启用

插件默认启用（`enabled: true`）。启用时执行：

1. 调用 `init_tables()` 创建独立数据库表
2. 调用 `seed_default_items()` 填充默认 SKU 目录
3. 初始化 i18n 翻译函数（注入到 routes 和 services 模块）
4. 注册定时任务（到期检查、自动续费）
5. 注册 Flask 蓝图路由

## 配置说明

`plugin.json` 中的配置项：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `trial_days` | integer | 0 | 免费试用天数（0 = 无试用期） |
| `grace_days` | integer | 3 | 到期后宽限期天数（宽限期内不禁用服务） |
| `auto_renew_default` | boolean | true | 新订阅默认是否开启自动续费 |

权限配置：

| 权限标识 | 说明 |
|----------|------|
| `subscription.read` | 读取订阅状态和 SKU 信息 |
| `subscription.write` | 创建/修改/取消订阅 |
| `subscription.admin` | 管理 SKU 目录和订阅配置 |

## API 端点

### 提供的 Hook 接口

| Hook 名称 | 功能描述 |
|-----------|----------|
| `subscription/has` | 检查用户是否拥有指定 Feature/SKU 的有效订阅 |
| `subscription/list` | 获取用户的所有订阅列表 |
| `subscription/subscribe` | 为用户创建新的订阅 |
| `subscription/cancel` | 取消用户的订阅 |
| `subscription/renew` | 续费用户的订阅 |

### 管理后台路由

通过 Flask 蓝图注册，提供：
- SKU 目录管理
- 订阅记录管理
- 用户订阅状态查询

## 依赖关系

### 事件监听

| 事件名称 | 处理逻辑 |
|----------|----------|
| `user/registered` | 新用户注册后，自动为其创建试用期订阅（如果 `trial_days > 0`） |

### 事件提供

本插件向事件总线提供 5 个 Hook，覆盖订阅全生命周期。其他插件可通过 `subscription/has` 检查用户是否拥有特定功能权限。

### 外部依赖

- **支付宝**：CN 环境支付网关，依赖支付宝开放平台 API
- **微信支付**：CN 环境支付网关，依赖微信支付 API V3
- **Stripe**：INTL 环境支付网关，依赖 Stripe API
- **PayPal**：INTL 环境支付网关，依赖 PayPal REST API
- 依赖 VeroRun 核心框架的 `BasePlugin`、事件总线、i18n 模块

### 菜单集成

- **菜单组**：Core（无分组）
- 注意：此插件属于核心模块，菜单项不显示在常规分组中

## 许可证

作为 VeroRun 项目的一部分，遵循项目统一许可证。