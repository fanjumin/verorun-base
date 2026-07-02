# 认证中心（Auth Center）

> **易站智能建站系统** 核心认证模块，以 Flask Blueprint 形式嵌入 **Platform（:8083）** 和 **Admin（:8084）** 两个服务，提供统一的用户认证、授权和账户管理体系。

---

## 目录

1. [架构总览](#1-架构总览)
2. [JWT 单点登录（SSO）](#2-jwt-单点登录sso)
3. [登录方式](#3-登录方式)
4. [用户体系](#4-用户体系)
5. [Blueprint 架构](#5-blueprint-架构)
6. [路由清单](#6-路由清单)
7. [配置中心](#7-配置中心)
8. [会话管理](#8-会话管理)
9. [相关文件](#9-相关文件)

---

## 1. 架构总览

`auth-center` 并非独立服务，而是一个可复用的 Python 包，通过 `register_auth()` 函数将约 18 个 Blueprint 批量挂载到宿主 Flask 应用上：

```
Platform App (:8083)          Admin App (:8084)
      │                             │
      ├─ register_auth(app)         ├─ register_auth(app)
      │                             │
      ▼                             ▼
┌─────────────────────────────────────────┐
│           auth-center 共享层              │
│  ┌─────────┐  ┌────────┐  ┌─────────┐  │
│  │ auth_bp │  │user_bp │  │admin_bp │  │
│  ├─────────┤  ├────────┤  ├─────────┤  │
│  │session  │  │payment │  │cms_admin│  │
│  │  _bp    │  │  _bp   │  │  _bp    │  │
│  ├─────────┤  ├────────┤  ├─────────┤  │
│  │ agent   │  │sub_bp  │  │ ...更多  │  │
│  │  _bp    │  │        │  │         │  │
│  └─────────┘  └────────┘  └─────────┘  │
│  ┌─────────────────────────────────┐    │
│  │  services/                      │    │
│  │  jwt_service  sms_service       │    │
│  │  oauth_service  captcha_service │    │
│  │  wechat_service  douyin_service │    │
│  │  brand_service  mail_service    │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**文件**: `auth-center/auth_blueprint.py` — `register_auth()` 入口，支持 `exclude_blueprints` 参数控制按需排除。

---

## 2. JWT 单点登录（SSO）

使用 **HS256 JWT** 实现跨子域单点登录，覆盖以下域名：

| 域名 | 用途 |
|---|---|
| `easykai.cn` | 主站（官网 / 用户端） |
| `platform.easykai.cn` | 平台端（用户工作台） |
| `admin.easykai.cn` | 管理后台 |
| `agent.easykai.cn` | 智能体（Agent） |

### SSO 流程

```
用户浏览器                          Platform/Admin                    auth-center
   │                                   │                               │
   │  1. POST /auth/password/login      │                               │
   │  ───────────────────────────────►  │                               │
   │                                   │  2. verify credentials         │
   │                                   │  ──────────────────────────►   │
   │                                   │  3. return JWT (jti, user_id, │
   │                                   │      phone, is_admin, exp)     │
   │                                   │  ◄──────────────────────────   │
   │  4. Set-Cookie: sso_token=<JWT>   │                               │
   │     Domain=.easykai.cn            │                               │
   │     Path=/   HttpOnly  Secure     │                               │
   │  ◄─────────────────────────────── │                               │
   │                                   │                               │
   │  5. GET /user/profile (另一个子域)  │                               │
   │     Cookie: sso_token=<JWT>       │                               │
   │  ───────────────────────────────► │                               │
   │                                   │  6. validate_token()          │
   │                                   │     - decode JWT HMAC         │
   │                                   │     - check jti blacklist     │
   │                                   │     - check user-level revoke │
   │                                   │  ──────────────────────────►   │
   │                                   │  7. 200 OK                    │
   │  ◄─────────────────────────────── │                               │
```

**关键实现**:

- **`jwt_service.create_token()`** — 生成携带 `jti`（唯一标识）、`user_id`、`phone`、`is_admin`、`app_name` 的 JWT，有效期 7 天（refresh token 30 天）。
- **`jwt_service.validate_token()`** — 验证 HMAC 签名 + 检查 `jti` 黑名单 + 检查用户级撤销时间戳。
- **`jwt_service.revoke_token()`** / **`revoke_all_user_tokens()`** — 单令牌撤销 + 全局强制下线。
- **Cookie 共享** — 通过 `.easykai.cn` 的 domain 实现跨子域 cookie 传递，同时在 URL query 带 `?token=` 做双保险（见 OAuth 回调）。
- **`_get_cookie_domain()`** — 动态从 `brand_settings.site_domain` 或请求 Host 推导跨子域 cookie domain。

**文件**: `auth-center/services/jwt_service.py`

---

## 3. 登录方式

认证中心支持以下 **4 种登录方式**：

### 3.1 密码登录（`/user/password/login`）

- 支持 `phone` / `username` / `email` 三种账号输入
- 密码哈希：`pbkdf2:sha256:100000:{salt}:{hash}`，兼容 werkzeug 旧格式
- 暴力防护：同一 IP 15 分钟内失败 3 次触发滑块验证码，10 次锁定
- 登录成功记录 `user_sessions` 会话

### 3.2 短信登录（`/auth/sms/login`）

- 验证码 6 位数字，有效期 10 分钟，5 次尝试上限
- 阿里云短信模板分场景：`register` / `login` / `change_phone` / `reset_password` / `modify_password`
- Stub 模式（默认）：无短信凭据时控制台打印验证码，方便开发测试
- 新手机号自动注册 + 创建免费套餐授权

**文件**: `auth-center/services/sms_service.py`

### 3.3 OAuth 第三方登录

| 平台 | 实现方式 | 凭据来源 | 特点 |
|---|---|---|---|
| **支付宝** (`/auth/oauth/alipay/login`) | 自定义 RSA 签名 | `system_config` | 非标准 OAuth，需手动验签 |
| **微信** (`/auth/oauth/wechat/login`) | authlib 集成 | 环境变量 | 单租户，全局统一凭据 |
| **抖音** (`/auth/oauth/douyin/login`) | 动态凭据查询 | 按域名查 DB（多租户） | 每次请求独立查询，无竞态 |

- OAuth 登录后自动创建用户，绑定第三方 open_id
- 统一回调到主域名 `https://easykai.cn/?token=<JWT>` 实现跨子域登录
- stun mode：模拟返回假数据，无需真实凭据

**文件**: `auth-center/services/oauth_service.py`

### 3.4 流程图：OAuth 回调

```
第三方 OAuth 页面           auth-center                 主站 (easykai.cn)
      │                        │                           │
      │ 1. 用户授权              │                           │
      │ ◄─────────────────────  │                           │
      │ 2. 回调 code            │                           │
      │ ──────────────────────► │                           │
      │                        │ 3. 换 token + 查用户       │
      │                        │ 4. 创建/查找用户           │
      │                        │ 5. 签发 JWT               │
      │                        │ 6. Set-Cookie: sso_token   │
      │                        │ 7. redirect /?token=<JWT> │
      │                        │ ────────────────────────►  │
      │                        │       (双保险登录成功)      │
```

---

## 4. 用户体系

### 4.1 账号模型

| 字段 | 说明 |
|---|---|
| `id` | 自增主键 |
| `username` | 登录名，3-20 字符，字母开头，唯一，30 天可改一次 |
| `display_name` | 显示名，可修改，与 `username` 分离 |
| `phone` | 手机号（电话登录/短信验证） |
| `email` | 邮箱（邮件验证） |
| `password_hash` | pbkdf2 哈希 |
| `is_admin` | 管理员标志（0/1） |
| `wechat_openid` / `douyin_open_id` / `alipay_user_id` | 第三方绑定 |
| `totp_secret` / `totp_enabled` | TOTP 二步验证 |
| `avatar_url` | 头像路径 |
| `is_real_name_verified` | 实人认证状态 |

### 4.2 角色与授权

- **角色**：`admin`（管理员） / `user`（普通用户）
- **应用授权**（`app_authorizations` 表）：用户对每个应用（如 `trademind`）有一个套餐级别（`free` / `pro` / `enterprise`）
- **API 密钥**（`api_keys` 表）：每个密钥绑定用户 + 应用，支持创建/吊销/重命名
- **套餐层级**（`TIERS`）：定义 daily_limit、price_month/year、features 等

### 4.3 扩展资料

- **`user_profiles`** — 性别、生日、年龄组、行业、职业、兴趣标签、个人简介
- **`user_addresses`** — 收货地址（省/市/区/街道四级联动）
- **`notification_preferences`** — 通知偏好（站内信/邮件）
- **`user_tickets`** — 工单系统（售前/售后/投诉/建议）

**文件**: `auth-center/routes/user.py`

---

## 5. Blueprint 架构

`register_auth()` 默认注册以下 **8 个核心 Blueprint**，可通过 `exclude_blueprints` 参数排除特定 Blueprint（例如 Admin 服务可以排除 `admin_bp` 以外的管理端 Blueprint，Platform 可以排除 `payment_bp` 等敏感 Blueprint）。

完整路由文件清单（`auth-center/routes/`）：

| # | 文件 | Blueprint 名 | 前缀 | 用途 |
|---|---|---|---|---|
| 1 | `auth.py` | `auth_bp` | `/auth` | 验证码、微信/抖音扫码、OAuth、退出 |
| 2 | `user.py` | `user_bp` | `/user` | 用户资料、API密钥、配置、地址、TOTP |
| 3 | `payment.py` | `payment_bp` | `/payment` | 订单创建、微信/支付宝支付 |
| 4 | `admin.py` | `admin_bp` | `/admin` | 管理面板仪表盘、站点配置 |
| 5 | `cms_admin.py` | `cms_admin_bp` | `/admin/cms` | CMS 内容管理 |
| 6 | `subscription.py` | `sub_bp` | `/subscription` | 套餐订阅管理 |
| 7 | `agents.py` | `agent_bp` | `/agent` | 用户智能体管理 |
| 8 | `sessions.py` | `session_bp` | `/session` | 登录会话列表/下线 |
| 9 | `header_admin.py` | — | — | 网站头部管理 |
| 10 | `footer_admin.py` | — | — | 网站底部管理 |
| 11 | `theme_admin.py` | — | — | 主题样式管理 |
| 12 | `shop_admin.py` | — | — | 商城管理 |
| 13 | `social_push.py` | — | — | 社交媒体推送 |
| 14 | `social_media.py` | — | — | 社媒内容发布 |
| 15 | `douyin_miniprogram.py` | — | — | 抖音小程序对接 |
| 16 | `comments.py` | — | — | 评论管理 |
| 17 | `content_factory.py` | — | — | 内容工厂 |
| 18 | `cleaner_agent.py` | — | — | 数据清理 Agent |

**注册入口**: `auth-center/auth_blueprint.py`

---

## 6. 路由清单

### `auth_bp` — 认证路由

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/auth/captcha/gen` | 生成滑块验证码挑战 |
| POST | `/auth/captcha/verify` | 验证滑块（行为检测） |
| POST | `/auth/sms/send` | 发送短信验证码 |
| POST | `/auth/sms/register` | 短信注册（设密码+用户名） |
| POST | `/auth/sms/login` | 短信验证码登录 |
| POST | `/auth/username/check` | 检查用户名可用性 |
| POST | `/auth/wechat/login` | 微信授权码登录 |
| GET | `/auth/wechat/qr` | 微信扫码登录页 |
| GET | `/auth/wechat/callback` | 微信回调 |
| GET | `/auth/douyin/qr` | 抖音扫码登录页 |
| GET | `/auth/douyin/callback` | 抖音回调 |
| GET | `/auth/oauth/<provider>/login` | 统一 OAuth 登录入口 |
| GET | `/auth/oauth/<provider>/callback` | 统一 OAuth 回调 |
| POST | `/auth/refresh` | 刷新 JWT Token |
| POST | `/auth/email/send` | 发送邮箱验证码 |
| POST | `/auth/email/verify` | 验证邮箱 |
| POST | `/auth/logout` | 退出登录（清 cookie + 下线 session） |

### `user_bp` — 用户路由

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/user/profile` | 获取用户资料 |
| PUT | `/user/profile` | 更新显示名 |
| PUT | `/user/username` | 修改用户名（30天限制） |
| POST | `/user/avatar` | 上传头像 |
| GET | `/user/keys` | API 密钥列表 |
| POST | `/user/keys/generate` | 生成新密钥 |
| PUT | `/user/keys/<id>` | 修改密钥名 |
| DELETE | `/user/keys/<id>` | 吊销密钥 |
| GET | `/user/keys/<id>/stats` | 密钥使用统计 |
| GET | `/user/tiers` | 套餐列表 |
| POST | `/user/password/set` | 设置/修改密码 |
| POST | `/user/password/login` | 密码登录 |
| POST | `/user/phone/change` | 更换绑定手机 |
| GET | `/user/config` | 系统配置列表（管理） |
| PUT | `/user/config` | 更新系统配置（管理） |
| POST | `/user/config/upload` | CSV 导入 AccessKey |
| POST | `/user/config/seed` | 初始化默认配置 |
| GET | `/user/usage-history` | 使用量历史 |
| GET | `/user/notifications` | 通知列表 |
| POST | `/user/notifications/read` | 标记已读 |
| POST | `/user/notifications/read-all` | 全部已读 |
| DELETE | `/user/notifications/<id>` | 删除通知 |
| GET/POST | `/user/tickets` | 工单列表/创建 |
| GET | `/user/activity` | 活动日志 |
| GET | `/user/profile/detail` | 扩展资料读取 |
| PUT | `/user/profile/detail` | 扩展资料更新 |
| GET | `/user/profile/completion` | 资料完成度 |
| GET/PUT | `/user/interests` | 兴趣标签 |
| GET | `/user/industries` | 行业列表 |
| GET | `/user/career-options` | 职业选项 |
| GET | `/user/regions` | 行政区划级联 |
| GET/POST/PUT/DELETE | `/user/addresses` | 收货地址 CRUD |
| POST | `/user/totp/setup` | 生成 TOTP 密钥+二维码 |
| POST | `/user/totp/verify` | 验证 TOTP 开启 2FA |
| POST | `/user/totp/disable` | 关闭 2FA |
| POST | `/user/oauth/unbind` | 解绑第三方账号 |
| GET/PUT | `/user/notification-preferences` | 通知偏好 |
| GET | `/user/verification` | 实名状态查询 |
| POST | `/user/verification/apply` | 发起实名认证 |
| GET/POST | `/user/verification/callback` | 认证回调 |
| GET | `/user/coupons` | 优惠券列表 |

### `session_bp` — 会话路由

| 方法 | 路径 | 功能 |
|---|---|---|
| GET | `/session/list` | 活跃会话列表 |
| GET | `/session/current` | 当前会话详情 |
| DELETE | `/session/<id>` | 终止指定会话 |

### `admin_bp` — 管理路由

| 方法 | 路径 | 功能 |
|---|---|---|
| POST | `/admin/logout` | 管理员退出 |
| GET | `/admin/dashboard` | 控制台概览 |

---

## 7. 配置中心

**`DeployConfig`** 类提供全局部署配置的统一入口：

```python
from services.deployment_config import deploy

deploy.DOMAIN           # 'easykai.cn'
deploy.url('platform')  # 'https://platform.easykai.cn'
deploy.email('support') # 'support@easykai.cn'
deploy.server_name()    # 'easykai.cn'
```

**优先级**: 环境变量 > `DEFAULT` 硬编码

支持的子域名映射（`to_dict()` 注入模板用）：

- `tm` → `tm.easykai.cn`
- `platform` → `platform.easykai.cn`
- `agent` → `agent.easykai.cn`
- `bot` → `bot.easykai.cn`
- `community` → `community.easykai.cn`

邮箱别名：`support@`、`postmaster@`、`hi@`

**文件**: `auth-center/services/deployment_config.py`

### 系统配置管理（`/user/config`）

通过 `system_config` 表动态存储 60+ 配置项，按类别分组：

| 类别 | 配置项示例 |
|---|---|
| `email` | SMTP 服务器/端口/账号/密码、IMAP |
| `sms` | 阿里云 AccessKey/SignName |
| `social` | 微信 Token、微博 AppKey/Secret |
| `miniapp_ai` | AI 供应商/模型/API Key |
| `payment` | 支付宝/微信支付凭据 |
| `verification` | 实人认证 AppID/私钥 |
| `alibaba` | 1688 开放平台凭据 |

---

## 8. 会话管理

**`user_sessions`** 表记录每次登录的详细信息：

- `token_hash` — JWT 的 SHA256 哈希，用于关联和吊销
- `device_name` / `device_type` — 设备标识（mobile/desktop）
- `ip_address` / `location` — 登录 IP 和地理位置
- `is_current` — 是否当前活跃会话
- `expired_at` — 过期时间（terminate 时设置）

用户可在「账户安全」页面查看所有活跃会话，并可远程下线其他设备。

**密码修改时的安全策略**（IAM v2）：修改密码后自动删除除当前会话外的所有 `user_sessions` 记录，实现"其他设备强制下线"。

**文件**: `auth-center/routes/sessions.py`

---

## 9. 相关文件

### 核心注册入口
- [`auth-center/auth_blueprint.py`](/auth-center/auth_blueprint.py)

### 路由
- [`auth-center/routes/auth.py`](/auth-center/routes/auth.py)
- [`auth-center/routes/user.py`](/auth-center/routes/user.py)
- [`auth-center/routes/sessions.py`](/auth-center/routes/sessions.py)
- [`auth-center/routes/admin.py`](/auth-center/routes/admin.py)
- [`auth-center/routes/payment.py`](/auth-center/routes/payment.py)
- [`auth-center/routes/agents.py`](/auth-center/routes/agents.py)

### 服务层
- [`auth-center/services/jwt_service.py`](/auth-center/services/jwt_service.py)
- [`auth-center/services/sms_service.py`](/auth-center/services/sms_service.py)
- [`auth-center/services/oauth_service.py`](/auth-center/services/oauth_service.py)
- [`auth-center/services/deployment_config.py`](/auth-center/services/deployment_config.py)
- [`auth-center/services/captcha_service.py`](/auth-center/services/captcha_service.py)
- [`auth-center/services/wechat_service.py`](/auth-center/services/wechat_service.py)
- [`auth-center/services/douyin_service.py`](/auth-center/services/douyin_service.py)
- [`auth-center/services/brand_service.py`](/auth-center/services/brand_service.py)
- [`auth-center/services/mail_service.py`](/auth-center/services/mail_service.py)
- [`auth-center/services/name_validator.py`](/auth-center/services/name_validator.py)
- [`auth-center/services/password_validator.py`](/auth-center/services/password_validator.py)

---

> **设计原则**：一次认证，全域通行。所有子域共享同一 JWT 秘钥、同一用户数据库，通过 `sso_token` cookie 实现无缝跳转，无需重复登录。
