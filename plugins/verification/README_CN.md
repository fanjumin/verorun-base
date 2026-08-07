# Identity Verification (verification)

## 概述

Identity Verification（实名认证）是 VeroRun 平台的用户身份认证插件，基于支付宝实人认证服务提供用户实名身份验证能力。插件使用独立的 PostgreSQL schema `verification`，存储认证请求记录，核心认证逻辑委托给 auth-center 的 `verification_service` 处理。

插件的设计遵循"数据独立、逻辑复用"原则：认证路由保留在 auth-center 中，插件仅提供管理 UI 和认证请求记录的独立存储，认证发起和回调处理均委托给已有的认证服务层。

## 功能特性

- **支付宝实人认证**：集成支付宝身份验证服务，提供可靠的实名认证能力
- **认证请求管理**：独立存储认证请求记录，支持状态追踪（pending/completed）
- **请求记录查询**：支持按用户 ID 和请求 ID 索引查询认证历史
- **逻辑复用**：核心认证逻辑委托给 auth-center 的 `verification_service`，避免重复实现
- **独立数据库**：使用 PostgreSQL schema `verification`，包含 `verification_requests` 表
- **数据迁移**：首次启动自动从主库幂等迁移已有认证请求记录
- **管理 UI**：提供管理后台界面，展示认证请求状态

## 架构设计

```
+--------------------------------------------------------------+
|                    前端（用户提交 + 管理查看）                   |
+--------------------------------------------------------------+
         |                              |
         v                              v
+------------------------+    +---------------------------+
|  auth-center 路由       |    |  插件管理 UI              |
|  (认证发起 + 回调)       |    |  (templates/)            |
|                        |    |  认证请求状态查看          |
+------------------------+    +---------------------------+
         |                              |
         v                              v
+--------------------------------------------------------------+
|                      服务层 (services.py)                      |
|  +-- initiate_verification()                                   |
|  |   委托给 auth-center.services.verification_service          |
|  +-- verify_callback()                                         |
|      委托给 auth-center.services.verification_service          |
+--------------------------------------------------------------+
         |
         v
+--------------------------------------------------------------+
|                      数据层 (models.py)                        |
|  PG Schema: verification                                      |
|  +-- verification_requests   认证请求记录表                    |
|      (user_id, request_id, provider, return_url, status,      |
|       created_at, completed_at)                                |
+--------------------------------------------------------------+
         |
         v
+--------------------------------------------------------------+
|                    auth-center 服务层                          |
|  +-- services/verification_service.py                         |
|      +-- initiate_verification()  支付宝认证发起              |
|      +-- verify_callback()        支付宝回调处理              |
+--------------------------------------------------------------+
```

**设计原则**：

- **数据独立**：认证请求记录存储在插件独立库中，不污染主库
- **逻辑复用**：核心认证逻辑（发起认证、回调处理）委托给 auth-center 已有的 `verification_service`，避免代码重复
- **路由保留**：认证回调路由保留在 auth-center 中，插件仅补充管理 UI
- **兼容旧接口**：插件服务层惰性导入 auth-center 的 `verification_service`（admin 进程已包含 auth-center 于 sys.path，无需修改 sys.path）

## 目录结构

```
verification/
+-- README.md                    # 插件文档
+-- plugin.json                  # 插件元数据配置
+-- __init__.py                  # 插件入口，注册蓝图和 Hook
+-- models.py                    # 数据模型（独立 schema 连接、表创建、索引、主库迁移）
+-- services.py                  # 核心服务（委托给 auth-center verification_service）
+-- i18n/
|   +-- en.yml                   # 英文国际化
|   +-- zh-CN.yml                # 中文国际化
+-- templates/
    +-- admin_verification.html  # 管理后台页面模板
```

## 安装与启用

### 前提条件

- VeroRun 平台版本 >= 0.10.0
- 支付宝开放平台应用（已配置实人认证产品）
- auth-center 的 `verification_service` 已正确配置支付宝参数
- PostgreSQL 数据库

### 安装步骤

1. 将 `verification` 目录放置于 `plugins/` 下
2. 确保 `plugin.json` 中 `enabled` 为 `true`
3. 重启应用，插件将自动：
   - 创建 PostgreSQL schema `verification`
   - 初始化 `verification_requests` 表
   - 从主库幂等迁移已有认证请求记录
4. 在管理后台 "Security & Compliance" > "ID Verification" 中查看认证请求

### 注意事项

- 认证发起和回调的路由保留在 auth-center 中，不受此插件影响
- 插件仅提供管理 UI 和独立数据存储，不改变认证流程
- 确保 auth-center 的支付宝配置正确（app_id、私钥、公钥等）

## 配置说明

本插件无额外配置项，依赖 auth-center 的支付宝配置。认证流程由 auth-center 的 `verification_service` 完全控制。

## API 端点

认证相关的 API 路由保留在 auth-center 中，插件不提供独立的 API 端点。插件仅提供以下能力：

### 提供的 Hook

| Hook 标识符 | 说明 |
|-------------|------|
| `verification/initiate` | 发起实名认证流程（委托给 auth-center） |
| `verification/verify_callback` | 处理支付宝认证回调（委托给 auth-center） |

## 数据库表结构

### verification_requests

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT (PK) | 自增主键 |
| `user_id` | BIGINT | 认证用户 ID |
| `request_id` | TEXT (UNIQUE) | 认证请求唯一标识 |
| `provider` | TEXT | 认证服务商（如 alipay） |
| `return_url` | TEXT | 认证完成后的回调 URL |
| `status` | TEXT | 认证状态：pending / completed |
| `created_at` | TEXT | 请求创建时间 |
| `completed_at` | TEXT | 认证完成时间 |

## 依赖关系

### 内部依赖

| 依赖项 | 用途 |
|--------|------|
| `plugins._base.db` | 插件基础数据库连接模块 |
| `auth-center.models` | 主库读取（verification_requests 迁移源） |
| `auth-center.services.verification_service` | 核心认证逻辑（`initiate_verification`、`verify_callback`） |

### 外部依赖

| 依赖项 | 用途 |
|--------|------|
| 支付宝开放平台 API | 实人认证服务 |

## 菜单组

- **Security & Compliance** - ID Verification

## 许可证

本插件为 VeroRun 平台的一部分，遵循平台统一的许可证协议。