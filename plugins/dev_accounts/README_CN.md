# Developer Accounts (dev_accounts)

## 概述

Developer Accounts 是 VeroRun 的社交媒体平台开发者账号管理插件，用于集中管理多个第三方平台的开发者账号信息（如 App ID、App Secret、Bot Token、Access Token 等敏感凭证）。插件提供加密存储能力，确保凭证数据安全。

## 功能特性

- **多平台管理**：支持抖音、微信、Telegram、LINE 等主流社交媒体平台的开发者账号管理
- **凭证加密存储**：App Secret、Bot Token、Access Token 等敏感信息经过加密后存储于数据库，保障数据安全
- **CRUD 操作**：提供完整的创建、查看、编辑、删除开发者账号的功能
- **平台枚举**：内置平台类型枚举，支持按平台筛选和查询
- **统一凭证管理**：为其他插件（如 OAuth 登录、IM 网关、社交推送等）提供统一的开发者凭证读取接口

## 架构设计

### 数据库策略

插件**无独立数据库**，使用 VeroRun 主库存储数据。

### 数据表结构

#### dev_accounts

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 主键 |
| `platform` | String(50) | 平台类型（douyin / wechat / telegram / line） |
| `account_name` | String(100) | 账号名称（用于标识） |
| `app_id` | String(200) | 应用 ID |
| `app_secret` | Text (加密) | 应用密钥（AES 加密存储） |
| `bot_token` | Text (加密) | 机器人 Token（AES 加密存储） |
| `access_token` | Text (加密) | 访问令牌（AES 加密存储） |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

### 模块结构

```
┌─────────────────────────────────────────────────┐
│                   routes.py                      │
│           (CRUD 路由 / 管理后台接口)               │
└─────────────────────┬───────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  models.py   │ │crypto.py │ │ VeroRun 核心  │
│ (ORM 模型)    │ │(加密工具) │ │ (Hook 系统)   │
└──────────────┘ └──────────┘ └──────────────┘
```

## 目录结构

```
dev_accounts/
├── __init__.py          # 插件入口，注册路由与菜单
├── models.py            # 数据模型定义（dev_accounts 表）
├── routes.py            # 管理后台 API 路由（CRUD）
├── crypto.py            # 加密/解密工具模块
└── plugin.json          # 插件元数据配置
```

## 安装与启用

### 安装

插件已包含在 VeroRun 的默认插件目录中，无需额外安装步骤。

### 启用

1. 在 VeroRun 管理后台 "插件管理" 页面中启用 Developer Accounts 插件
2. 插件启用后将自动在主库中创建 `dev_accounts` 表（如不存在）
3. 管理后台将出现 "Developer Accounts" 菜单项

## 配置说明

在 `plugin.json` 中配置以下参数：

```json
{
  "name": "dev_accounts",
  "database": {
    "use_main_db": true
  },
  "encryption": {
    "algorithm": "AES-256-GCM",
    "key_source": "app_secret_key"
  },
  "platforms": [
    "douyin",
    "wechat",
    "telegram",
    "line"
  ]
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `database.use_main_db` | 是否使用主库 | `true` |
| `encryption.algorithm` | 加密算法 | `AES-256-GCM` |
| `encryption.key_source` | 加密密钥来源（应用配置） | `app_secret_key` |
| `platforms` | 支持的平台列表 | `douyin, wechat, telegram, line` |

## API 端点

### 管理后台 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/dev_accounts/` | 列出所有开发者账号 |
| `POST` | `/admin/dev_accounts/` | 创建新的开发者账号 |
| `GET` | `/admin/dev_accounts/<id>` | 查看开发者账号详情 |
| `PUT` | `/admin/dev_accounts/<id>` | 编辑开发者账号 |
| `DELETE` | `/admin/dev_accounts/<id>` | 删除开发者账号 |

### 内部接口

| 方法 | 说明 |
|------|------|
| `get_credentials(platform)` | 根据平台类型获取解密后的凭证信息 |
| `get_app_config(platform)` | 获取指定平台的 App ID 和 App Secret |

### 管理后台

| 菜单项 | 说明 |
|--------|------|
| `Developer Accounts` | 开发者账号管理页面 |

## 依赖关系

### 内部依赖

- VeroRun 核心框架：主库 ORM、路由注册、Hook 系统
- 管理后台（auth-center）：菜单渲染
- `crypto.py` 依赖应用级加密密钥

### 外部依赖

无外部第三方依赖。

### 被依赖

- **oauth_config** 插件：读取开发者账号凭证进行 OAuth 登录
- **im_gateway** 插件：读取 Telegram/LINE 等平台的 Bot Token
- **social_push** 插件：读取社交媒体平台的开发者凭证

## 许可证

本插件为 VeroRun 项目的一部分，遵循 VeroRun 项目的整体许可证协议。