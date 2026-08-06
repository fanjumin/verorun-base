# Developer Accounts (dev_accounts)

## 概述

Developer Accounts 是 VeroRun 的社交媒体平台开发者账号管理插件，用于集中管理多个第三方平台的开发者账号信息（如 App ID、App Secret、Bot Token、Access Token 等敏感凭证）。插件提供加密存储能力，确保凭证数据安全。

## 功能特性

- **多平台管理**：支持抖音、头条、微信、Telegram、LINE 等主流社交媒体平台的开发者账号管理
- **凭证加密存储**：App Secret、Bot Token、Access Token 等敏感信息经 Fernet 加密后存储于数据库
- **CRUD 操作**：提供完整的创建、查看、编辑、删除开发者账号的功能
- **连接测试**：Telegram / LINE 支持调用平台 API 验证凭证有效性
- **统一凭证管理**：为其他模块（小程序登录、站点构建等）提供统一的开发者凭证读取接口

## 架构设计

### 数据库策略

插件**无独立数据库 / 独立 schema**，使用 VeroRun 主库 `public` schema 存储数据。

**逻辑解耦决策（标准 §12.10）**：`dev_accounts` 表被以下模块跨组件共享读取，因此保留在主库，未迁移到独立 schema：

- `main_site/routes/mini_program.py`：直接 SQL 读取 `bot_token` 用于 Telegram 登录签名校验
- `site_builder/routes.py`：经 `models` 读取凭证用于小程序部署配置

迁移到独立 schema 会破坏上述核心链路。数据访问统一通过 `plugins/_base/db.py` 的 PostgreSQL 连接（`get_raw_connection()` + `PgConnection`，`SET search_path TO public`）。

### 数据表结构

#### dev_accounts

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Serial | 主键 |
| `platform` | Text | 平台类型（douyin / toutiao / wechat / telegram / line） |
| `account_name` | Text | 账号名称（用于标识） |
| `app_id` | Text | 应用 ID |
| `app_secret` | Text (加密) | 应用密钥（Fernet 加密存储） |
| `bot_token` | Text (加密) | 机器人 Token（Fernet 加密存储） |
| `channel_id` | Text | 频道 ID |
| `channel_secret` | Text (加密) | 频道密钥（Fernet 加密存储） |
| `access_token` | Text (加密) | 访问令牌（Fernet 加密存储） |
| `extra_config` | Text | 附加配置（JSON 字符串） |
| `is_active` | Integer | 是否启用（1 / 0） |
| `created_at` | Text | 创建时间 |
| `updated_at` | Text | 更新时间 |

### 加密说明

敏感字段使用 `cryptography.fernet`（**AES-128-CBC + HMAC-SHA256**，非 AES-256-GCM）加密。密钥来源于环境变量 `DEV_ACCOUNTS_ENCRYPTION_KEY`，经 SHA-256 派生为 Fernet 兼容密钥格式。密钥在首次 `encrypt` / `decrypt` 调用时懒加载。

### 模块结构

```
dev_accounts/
├── __init__.py          # 插件入口，注册路由、生命周期钩子、Dashboard 统计
├── models.py            # 数据访问层（PG 连接、CRUD、连接测试）
├── routes.py            # 管理后台 API 路由（CRUD、连接测试）
├── crypto.py            # Fernet 加密/解密工具模块
├── i18n/                # 多语言翻译（zh-CN.yml / en.yml）
│   ├── zh-CN.yml
│   └── en.yml
├── migrations/          # 版本迁移 SQL
│   └── v1.0.0.sql
└── plugin.json          # 插件元数据配置
```

## 安装与启用

### 安装

插件已包含在 VeroRun 的默认插件目录中，无需额外安装步骤。

### 环境变量

首次启用前需设置加密密钥（不设置时仅 `encrypt`/`decrypt` 调用会报错，插件可正常加载）：

```bash
export DEV_ACCOUNTS_ENCRYPTION_KEY='<Fernet 密钥>'
# 生成方式：
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 启用

1. 在 VeroRun 管理后台 "插件管理" 页面中启用 Developer Accounts 插件
2. 插件启用后将自动在主库中创建 `dev_accounts` 表（如不存在）
3. 管理后台将出现 "Developer Accounts" 菜单项（`/admin/dev-accounts`）

## 配置说明

插件**无插件级配置项**（`plugin.json` 的 `config` 为空对象）。所需外部配置仅有环境变量 `DEV_ACCOUNTS_ENCRYPTION_KEY`（见上文）。

## API 端点

### 管理后台 API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/admin/dev-accounts/` | 列出所有开发者账号（可带 `?platform=` 筛选） |
| `POST` | `/admin/dev-accounts/` | 创建新的开发者账号 |
| `GET` | `/admin/dev-accounts/<id>` | 查看开发者账号详情 |
| `PUT` | `/admin/dev-accounts/<id>` | 编辑开发者账号 |
| `DELETE` | `/admin/dev-accounts/<id>` | 删除开发者账号 |
| `POST` | `/admin/dev-accounts/<id>/test` | 测试开发者账号连接 |

所有端点均需管理员权限（JWT `is_admin`）。

### 内部接口

| 方法 | 说明 |
|------|------|
| `models.get_all(platform)` | 获取账号列表（敏感字段已脱敏） |
| `models.get_by_id(id)` | 获取单个账号（敏感字段已脱敏） |
| `models.get_by_platform(platform)` | 获取指定平台账号（敏感字段已脱敏） |
| `models.test_connection(id)` | 测试平台连接 |

### 管理后台

| 菜单项 | 说明 |
|--------|------|
| `Developer Accounts` | 开发者账号管理页面（由 admin SPA 承载，路径 `/admin/dev-accounts`） |

## 依赖关系

### 内部依赖

- VeroRun 核心框架：插件管理器、路由注册
- `plugins/_base/db.py`：PostgreSQL 连接（`get_raw_connection()` + `PgConnection`）
- `cryptography`：Fernet 加密
- 环境变量 `DEV_ACCOUNTS_ENCRYPTION_KEY`

### 外部依赖

- `cryptography`（Python 包）

### 被依赖

- **main_site**（`routes/mini_program.py`）：直接 SQL 读取 `bot_token` 校验 Telegram 登录
- **site_builder**（`routes.py`）：经 `models.get_all/update` 读取开发者凭证进行小程序部署

## 许可证

本插件为 VeroRun 项目的一部分，遵循 VeroRun 项目的整体许可证协议。
