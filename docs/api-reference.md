# VeroRon 维洛智能 — API 接口参考文档

> 版本: v1.0  
> 最后更新: 2026-07-01  
> 基础 URL: `https://<your-domain>`  
> 数据格式: 全部请求/响应均为 JSON

---

## 目录

1. [概述](#1-概述)
2. [认证 API](#2-认证-api)
3. [用户 API](#3-用户-api)
4. [管理后台 API](#4-管理后台-api)
5. [商城 API](#5-商城-api)
6. [订阅与支付 API](#6-订阅与支付-api)
7. [内容管理 API](#7-内容管理-api)
8. [AI 矩阵 API](#8-ai-矩阵-api)
9. [工作流引擎 API](#9-工作流引擎-api)
10. [平台公开 API](#10-平台公开-api)
11. [内容工厂 API](#11-内容工厂-api)
12. [1688 集成 API](#12-1688-集成-api)
13. [云服务开通 API](#13-云服务开通-api)
14. [分析统计 API](#14-分析统计-api)
15. [健康检查 API](#15-健康检查-api)
16. [验证码服务 API](#16-验证码服务-api)

---

## 1. 概述

### 1.1 通用约定

| 项目 | 说明 |
|------|------|
| 基础 URL | `https://platform.easykai.cn`（平台门户）、`https://admin.easykai.cn`（管理后台） |
| 响应格式 | 统一 `{"success": bool, "data": ..., "error": "..."}` |
| HTTP 方法 | GET（查询）、POST（创建）、PUT（更新）、DELETE（删除） |
| 成功状态码 | 200 |
| 失败状态码 | 400（请求错误）、401（未认证）、403（无权限）、404（不存在）、429（限流）、500（服务器错误） |

### 1.2 认证方式

**JWT Bearer Token**（所有需要登录的接口）：

```
Authorization: Bearer <your-jwt-token>
```

Token 可通过以下方式获取：
- 密码登录 `POST /user/password/login`
- 短信登录 `POST /auth/sms/login`
- 注册 `POST /auth/sms/register`
- OAuth 第三方登录回调

Cookie 方式（SSO 场景）：`sso_token=<jwt>` 或 `tm_token=<jwt>`

### 1.3 通用响应示例

```json
// 成功
{"success": true, "data": {...}}

// 失败
{"success": false, "error": "错误描述信息"}
```

### 1.4 通用错误码

| HTTP 状态码 | 说明 |
|-------------|------|
| 400 | 参数错误、缺少必填字段 |
| 401 | 未登录或 Token 已过期 |
| 403 | 无操作权限 |
| 404 | 请求的资源不存在 |
| 429 | 请求过于频繁（IP 限流） |
| 500 | 服务器内部错误 |

---

## 2. 认证 API

前缀: `/auth`  
认证: 部分无需认证，已标注

### 2.1 滑块验证码

#### `GET /auth/captcha/gen` — 生成滑块验证码挑战

无需认证。

**响应**:
```json
{
  "success": true,
  "data": {
    "captcha_id": "uuid",
    "bg_image": "base64...",
    "piece_image": "base64...",
    "piece_x": 120
    // 前端根据 piece_x 验证用户拖动位置
  }
}
```

#### `POST /auth/captcha/verify` — 验证滑块位置

**请求体**:
```json
{
  "captcha_id": "uuid",
  "user_x": 118,
  "trajectory": [{"x": 0, "y": 0, "t": 0}, {"x": 50, "y": 2, "t": 100}]
}
```

**响应**:
```json
{
  "success": true,
  "data": {"valid": true, "mode": "behavioral", "combined_score": 0.95}
}
```

### 2.2 短信验证码

#### `POST /auth/sms/send` — 发送短信验证码

**请求体**:
```json
{
  "phone": "13800138000",
  "purpose": "login",
  "country_code": "+86",
  "captcha_id": "uuid"
}
```

`purpose` 可选值: `login`, `register`, `modify_password`, `change_phone`, `email_verify`

**响应**:
```json
{"success": true, "data": {"sent": true, "provider": "stub", "code": "123456"}}
```

> 注意: stub 模式下会返回 `code` 用于测试；生产环境不返回。

### 2.3 用户名检查

#### `POST /auth/username/check` — 检查用户名是否可用

**请求体**: `{"username": "testuser"}`

**响应**: `{"success": true, "data": {"available": true}}`

### 2.4 注册

#### `POST /auth/sms/register` — 短信验证码注册

**请求体**:
```json
{
  "phone": "13800138000",
  "code": "123456",
  "password": "mypassword123",
  "username": "testuser",
  "display_name": "测试用户"
}
```

`display_name` 可选。

**响应**:
```json
{
  "success": true,
  "data": {
    "token": "jwt-token-string",
    "user": {"id": 1, "phone": "13800138000", "username": "testuser", "display_name": "测试用户"}
  }
}
```

### 2.5 登录

#### `POST /auth/sms/login` — 短信验证码登录

**请求体**: `{"phone": "13800138000", "code": "123456"}`

**响应**: 同注册响应。

#### `POST /user/password/login` — 密码登录

**请求体**:
```json
{
  "phone": "13800138000",
  "password": "mypassword",
  "captcha_id": "uuid"
}
```

`username` 可替代 `phone`。`captcha_id` 在连续 3 次失败后必填。

**响应**: 同注册响应。

### 2.6 微信登录

#### `POST /auth/wechat/login` — 微信静默登录

**请求体**: `{"code": "wechat-code"}`

**响应**: `{"success": true, "data": {"token": "...", "user": {"id": 1}}}`

#### `GET /auth/wechat/qr` — 微信扫码登录页面

返回微信登录页面（生产环境重定向到微信 OAuth）。

#### `GET /auth/wechat/callback` — 微信 OAuth 回调

处理微信授权回调，登录成功后重定向到主站首页并携带 token。

### 2.7 抖音登录

#### `GET /auth/douyin/qr` — 抖音扫码登录页

#### `GET /auth/douyin/callback` — 抖音 OAuth 回调

### 2.8 OAuth 统一登录

#### `GET /auth/oauth/<provider>/login` — 发起第三方 OAuth 登录

`provider` 可选: `alipay`, `douyin`, `google`, `github`, `facebook` 等。

#### `GET /auth/oauth/<provider>/callback` — OAuth 回调处理

### 2.9 Token 相关

#### `POST /auth/refresh` — 刷新 Token

**请求体**: `{"token": "old-jwt-token"}`

**响应**: `{"success": true, "data": {"token": "new-jwt-token"}}`

#### `POST /auth/logout` — 退出登录

清除 cookie 并标记当前 session 下线。

**响应**: `{"success": true}`

### 2.10 邮箱验证

#### `POST /auth/email/send` — 发送邮箱验证码

需 JWT 认证。

**请求体**: `{"email": "user@example.com"}`

**响应**: `{"success": true, "data": {"sent": true}}`

#### `POST /auth/email/verify` — 验证邮箱

**请求体**: `{"email": "user@example.com", "code": "123456"}`

**响应**: `{"success": true, "data": {"email": "user@example.com", "email_verified": true}}`

---

## 3. 用户 API

前缀: `/user`  
认证: 全部需要 JWT（已标注的除外）

### 3.1 个人资料

#### `GET /user/profile` — 获取当前用户资料

**响应** (节选):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "phone": "138****8000",
    "username": "testuser",
    "display_name": "测试用户",
    "avatar": "/static/avatars/xxx.png",
    "email": "user@example.com",
    "email_verified": true,
    "is_admin": false,
    "tier": "professional",
    "tier_name": "专业版",
    "calls_today": 5,
    "daily_limit": 100,
    "calls_remaining": 95,
    "totp_enabled": false,
    "password_set": true,
    "is_real_name_verified": false
  }
}
```

#### `PUT /user/profile` — 更新用户昵称

**请求体**: `{"nickname": "新昵称"}` 或 `{"display_name": "新显示名"}`

**响应**: `{"success": true, "data": {"nickname": "新昵称", "display_name": "新显示名"}}`

> 注意: 已实名认证用户不可修改显示名。

#### `PUT /user/username` — 修改用户名（30 天一次）

**请求体**: `{"username": "newusername"}`

**响应**: `{"success": true, "data": {"username": "newusername", "next_change_after": "30 days later"}}`

### 3.2 头像

#### `POST /user/avatar` — 上传头像

multipart/form-data: `avatar` 字段（支持 png/jpg/gif/webp，最大 2MB）

**响应**: `{"success": true, "data": {"avatar_url": "/static/avatars/xxx.png"}}`

### 3.3 API Key 管理

#### `GET /user/keys` — 列出 API Key 列表

**响应**:
```json
{
  "success": true,
  "data": [
    {"id": 1, "key_prefix": "tm-abc123...def0", "name": "我的Key", "calls_today": 10, "calls_total": 500, "created_at": "...", "active": true}
  ]
}
```

#### `POST /user/keys/generate` — 生成新的 API Key

**请求体**: `{"name": "我的Key"}`

**响应**:
```json
{
  "success": true,
  "data": {
    "key": "tm-abc123def456...",
    "key_prefix": "tm-abc123...456",
    "name": "我的Key",
    "tier": "professional",
    "warning": "Save this key now! It will not be shown again."
  }
}
```

> ⚠️ 完整 key 仅在创建时返回一次。

#### `DELETE /user/keys/<key_id>` — 撤销 API Key

**响应**: `{"success": true}`

#### `PUT /user/keys/<key_id>` — 更新 API Key 名称

**请求体**: `{"name": "新名称"}`

**响应**: `{"success": true}`

#### `GET /user/keys/<key_id>/stats` — 查询单个 Key 统计

**响应**: `{"success": true, "data": {"id": 1, "name": "...", "key_prefix": "...", "calls_today": 10, "calls_total": 500}}`

### 3.4 用户套餐

#### `GET /user/tiers` — 列出可用套餐

**响应**:
```json
{
  "success": true,
  "data": [
    {"id": "free", "name": "免费版", "desc": "...", "daily_limit": 20, "price_month": 0, "features": [...]}
  ]
}
```

### 3.5 使用统计

#### `GET /user/usage-history` — 使用历史

**响应**: `{"success": true, "data": {"total_keys": 3, "active_keys": 2, "total_calls": 1500, "today_calls": 10, "keys": [...]}}`

### 3.6 密码管理

#### `POST /user/password/set` — 设置/修改密码

**请求体**: `{"phone": "13800138000", "code": "123456", "password": "newpassword"}`

需短信验证（purpose=modify_password）。

**响应**: `{"success": true, "message": "Password changed, other devices logged out"}`

#### `POST /user/phone/change` — 更换绑定手机号

**请求体**: `{"old_phone": "138...", "old_code": "123456", "new_phone": "139...", "new_code": "654321"}`

### 3.7 系统配置（管理员）

#### `GET /user/config` — 获取系统配置

**响应**:
```json
{
  "success": true,
  "data": [{"key": "smtp_host", "value": "...", "sensitive": false, "category": "email", "label": "SMTP 服务器"}],
  "categories": [{"id": "email", "title": "邮箱配置"}],
  "schema": {"smtp_host": {"label": "SMTP 服务器", "category": "email", "sensitive": false}}
}
```

#### `PUT /user/config` — 更新系统配置

**请求体**: `{"key": "smtp_host", "value": "smtp.example.com"}`

#### `POST /user/config/upload` — 上传 CSV 导入 AccessKey

multipart/form-data: `file` 字段（CSV 格式，需包含 AccessKey ID / AccessKey Secret 列）。

#### `POST /user/config/seed` — 初始化默认配置项

### 3.8 通知

#### `GET /user/notifications` — 获取通知列表

**参数**: `?page=1&pageSize=20`

**响应**: `{"success": true, "data": [...], "total": 50, "unread": 3, "page": 1, "pageSize": 20}`

#### `GET /user/notifications/unread-count` — 未读通知数

#### `POST /user/notifications/read` — 标记已读

**请求体**: `{"id": 123}`（不传 id 则全部已读）

#### `POST /user/notifications/read-all` — 全部标记已读

#### `DELETE /user/notifications/<nid>` — 删除通知

### 3.9 工单

#### `GET /user/tickets` — 获取工单列表

**参数**: `?type=aftersale`（可选过滤: presale/aftersale/complaint/suggestion）

#### `POST /user/tickets` — 创建工单

**请求体**:
```json
{
  "title": "订单问题",
  "content": "我的订单还没发货",
  "type": "aftersale",
  "category": "物流",
  "contact": "13800138000"
}
```

### 3.10 活动日志

#### `GET /user/activity` — 获取最近活动

**参数**: `?limit=10` 或 `?page=1&page_size=20`

### 3.11 Agent 统计

#### `GET /user/agent/stats` — Agent 概览统计

#### `GET /user/posts` — 用户社区内容列表

### 3.12 用户资料详情

#### `GET /user/profile/detail` — 获取扩展资料

#### `PUT /user/profile/detail` — 更新扩展资料

#### `GET /user/profile/completion` — 资料完成度

### 3.13 兴趣标签

#### `GET /user/interests` — 获取用户兴趣

#### `PUT /user/interests` — 更新用户兴趣

**请求体**: `{"interest_ids": [1, 2, 3], "custom_tags": ["AI", "编程"]}`

### 3.14 数据字典

#### `GET /user/industries` — 行业列表

#### `GET /user/career-options` — 职业选项

**参数**: `?parent_id=1`（可选）

#### `GET /user/regions` — 行政区划

**参数**: `?parent_code=320000`（可选）

### 3.15 收货地址

#### `GET /user/addresses` — 地址列表

#### `POST /user/addresses` — 创建地址

#### `PUT /user/addresses/<addr_id>` — 更新地址

#### `DELETE /user/addresses/<addr_id>` — 删除地址

#### `PUT /user/addresses/<addr_id>/default` — 设为默认

### 3.16 双因素认证 (TOTP)

#### `POST /user/totp/setup` — 生成 TOTP 密钥及二维码

#### `POST /user/totp/verify` — 验证并启用 2FA

**请求体**: `{"token": "123456"}`

#### `POST /user/totp/disable` — 关闭 2FA

### 3.17 第三方账号

#### `POST /user/oauth/unbind` — 解绑第三方账号

**请求体**: `{"provider": "wechat"}`（支持 wechat/douyin）

### 3.18 通知偏好

#### `GET /user/notification-preferences` — 获取通知偏好

#### `PUT /user/notification-preferences` — 更新通知偏好

### 3.19 实名认证

#### `GET /user/verification` — 查询实名认证状态

#### `POST /user/verification/apply` — 发起实名认证

**请求体**: `{"return_url": "https://...", "cert_name": "张三", "cert_no": "身份证号"}`

#### `GET/POST /user/verification/callback` — 认证回调

#### `GET /user/coupons` — 用户优惠券列表

### 3.20 企业认证

#### `POST /user/enterprise/verify/ocr` — OCR 识别营业执照

**请求体**: `{"image": "base64-encoded-image"}`

#### `POST /user/enterprise/verify/submit` — 提交企业认证

#### `GET /user/enterprise/verify/status` — 查询企业认证状态

---

## 4. 管理后台 API

前缀: `/admin`  
认证: 需要管理员 JWT

### 4.1 仪表盘

#### `GET /admin/dashboard` — 仪表盘数据

#### `GET /admin/revenue/dashboard` — 收入仪表盘

### 4.2 用户管理

#### `GET /admin/users` — 用户列表

**参数**: `?page=1&pageSize=20&keyword=xxx&tier=free`

#### `GET /admin/users/<uid>` — 用户详情

#### `PUT /admin/users/<uid>/status` — 修改用户状态

#### `PUT /admin/users/<uid>/verify` — 审核用户

#### `GET /admin/users/<uid>/profile` — 用户扩展资料

#### `GET /admin/users/export` — 导出用户

### 4.3 Agent 管理

#### `GET /admin/agents` — Agent 列表

#### `GET /admin/posts` — 社区内容列表

#### `PUT /admin/posts/<pid>/review` — 审核社区内容

### 4.4 联系与 API Key

#### `GET /admin/contacts` — 联系列表

#### `GET /admin/api-keys` — API Key 列表

#### `DELETE /admin/api-keys/<kid>` — 删除 API Key

### 4.5 操作日志

#### `GET /admin/logs` — 操作日志

### 4.6 Agent 矩阵管理

#### `GET /admin/agent-matrix` — Agent 列表

#### `POST /admin/agent-matrix` — 创建 Agent

#### `PUT /admin/agent-matrix/<aid>` — 更新 Agent

#### `DELETE /admin/agent-matrix/<aid>` — 删除 Agent

#### `POST /admin/agent-matrix/<aid>/test` — 测试 Agent

### 4.7 邮件管理

#### `GET /admin/email/inbox` — 收件箱

#### `GET /admin/email/read/<uid>` — 读取邮件

#### `POST /admin/email/send` — 发送邮件

#### `GET /admin/email/sent` — 已发送

#### `GET /admin/email/contacts` — 邮件联系人

### 4.8 短信模板

#### `GET /admin/sms/templates` — 短信模板列表

#### `POST /admin/sms/templates` — 创建模板

#### `PUT /admin/sms/templates/<tid>` — 更新模板

#### `DELETE /admin/sms/templates/<tid>` — 删除模板

### 4.9 管理员管理

#### `GET /admin/admins` — 管理员列表

#### `GET /admin/admins/me` — 当前管理员信息

#### `PUT /admin/admins/me` — 更新个人信息

#### `POST /admin/admins` — 创建管理员

#### `PUT /admin/admins/<uid>` — 更新管理员

#### `DELETE /admin/admins/<uid>` — 删除管理员

### 4.10 头像管理

#### `POST /admin/users/<uid>/avatar` — 设置用户头像

#### `GET /admin/avatars/defaults` — 默认头像列表

### 4.11 品牌设置

#### `GET /admin/brand-settings` — 获取品牌设置

#### `PUT /admin/brand-settings` — 更新品牌设置

#### `POST /admin/brand-settings/logo` — 上传 Logo

### 4.12 通知模板

#### `GET /admin/notifications/templates` — 通知模板列表

#### `POST /admin/notifications/templates` — 创建模板

#### `POST /admin/notifications/send` — 发送通知

### 4.13 工单管理

#### `GET /admin/tickets` — 工单列表

#### `PUT /admin/tickets/<tid>` — 回复工单

### 4.14 奖励规则

#### `GET /admin/reward-rules` — 奖励规则列表

#### `POST /admin/reward-rules` — 创建规则

#### `PUT /admin/reward-rules/<rid>` — 更新规则

#### `DELETE /admin/reward-rules/<rid>` — 删除规则

#### `GET /admin/reward-claims` — 奖励领取记录

### 4.15 兴趣管理

#### `GET /admin/interests` — 兴趣标签列表

#### `POST /admin/interests` — 创建标签

#### `PUT /admin/interests/<iid>` — 更新标签

#### `DELETE /admin/interests/<iid>` — 删除标签

#### `GET /admin/interests/public` — 公开兴趣列表

### 4.16 社媒链接

#### `GET /admin/social-links` — 社媒链接列表

#### `POST /admin/social-links` — 创建链接

#### `PUT /admin/social-links/<lid>` — 更新链接

#### `DELETE /admin/social-links/<lid>` — 删除链接

#### `PUT /admin/social-links/reorder` — 排序

### 4.17 渠道配置

#### `GET /admin/channels` — 渠道列表

#### `GET /admin/channels/<channel>` — 渠道详情

#### `PUT /admin/channels/<channel>` — 更新渠道

#### `POST /admin/channels/<channel>/test` — 测试渠道

### 4.18 集群服务

#### `GET /admin/cluster/services` — 服务列表

#### `POST /admin/cluster/services` — 注册服务

#### `PUT /admin/cluster/services/<sid>` — 更新服务

#### `DELETE /admin/cluster/services/<sid>` — 删除服务

#### `POST /admin/cluster/services/<sid>/start` — 启动服务

#### `POST /admin/cluster/services/<sid>/stop` — 停止服务

#### `POST /admin/cluster/services/<sid>/restart` — 重启服务

#### `GET /admin/cluster/services/<sid>/logs` — 服务日志

#### `GET /admin/cluster/services/<sid>/health` — 服务健康检查

### 4.19 头部导航管理

**Blueprints: header_bp / footer_bp**

#### `GET /header-nav` — 获取导航

#### `POST /header-nav` — 添加导航项

#### `PUT /header-nav/<item_id>` — 更新导航项

#### `DELETE /header-nav/<item_id>` — 删除导航项

#### `POST /header-nav/reorder` — 排序导航

#### `GET /footer-links` — 底部链接

#### `POST /footer-links` — 添加底部链接

---

## 5. 商城 API

### 5.1 商城管理（后台）

前缀: `/shop`  
认证: 需要管理员 JWT

#### `POST /shop/products/upload-image` — 上传商品图片

#### `GET /shop/products` — 商品列表

#### `POST /shop/products` — 创建商品

#### `GET /shop/products/<pid>` — 商品详情

#### `PUT /shop/products/<pid>` — 更新商品

#### `DELETE /shop/products/<pid>` — 删除商品

#### `GET /shop/products/<pid>/specs` — 商品规格

#### `POST /shop/products/<pid>/specs` — 添加规格

#### `GET /shop/products/<pid>/skus` — SKU 列表

#### `POST /shop/products/<pid>/skus/generate` — 生成 SKU

#### `GET /shop/categories` — 分类列表

#### `POST /shop/categories` — 创建分类

#### `PUT /shop/categories/<cid>` — 更新分类

#### `DELETE /shop/categories/<cid>` — 删除分类

#### `GET /shop/orders` — 订单列表

#### `GET /shop/orders/<oid>/detail` — 订单详情

#### `POST /shop/orders/<pid>/confirm` — 确认订单

#### `POST /shop/orders/<oid>/refund` — 退款处理

#### `POST /shop/orders/<oid>/complete` — 完成订单

#### `GET /shop/express-companies` — 快递公司列表

#### `POST /shop/orders/<oid>/ship` — 发货

#### `GET /shop/orders/<oid>/track` — 物流追踪

#### `GET /shop/coupons` — 优惠券列表

#### `POST /shop/coupons` — 创建优惠券

#### `PUT /shop/coupons/<cid>` — 更新优惠券

#### `DELETE /shop/coupons/<cid>` — 删除优惠券

#### `POST /shop/coupons/distribute` — 分发优惠券

#### `POST /shop/products/<pid>/ai-optimize` — AI 优化商品

#### `POST /shop/products/ai-batch` — AI 批量优化

### 5.2 商城前端（用户端）

前缀: `/shop/api`  
认证: 需要用户 JWT

#### `GET /shop/api/products` — 前端商品列表

#### `GET /shop/api/products/<pid>` — 商品详情

#### `GET /shop/api/products/<pid>/skus` — 商品 SKU

#### `GET /shop/api/cart` — 购物车

#### `POST /shop/api/cart/add` — 加入购物车

#### `POST /shop/api/cart/update` — 更新购物车

#### `POST /shop/api/cart/remove` — 移除购物车

#### `POST /shop/api/checkout` — 结算下单

#### `GET /shop/api/orders` — 订单列表

#### `POST /shop/api/orders/<oid>/cancel` — 取消订单

#### `POST /shop/api/orders/<oid>/delete` — 删除订单

#### `POST /shop/api/orders/<oid>/confirm-receipt` — 确认收货

#### `POST /shop/api/orders/<oid>/request-refund` — 申请退款

#### `POST /shop/api/pay/<oid>` — 支付

#### `GET /shop/api/pay/status/<oid>` — 支付状态

#### `POST /shop/api/coupon/validate` — 优惠券验证

#### `GET /shop/api/user/info` — 用户信息

---

## 6. 订阅与支付 API

### 6.1 订阅管理（用户端）

前缀: `/subscription`

#### `GET /subscription/plans` — 套餐列表

#### `GET /subscription/plans/features` — 套餐功能对比

#### `GET /subscription/my` — 我的订阅

#### `GET /subscription/my/invoices` — 发票列表

#### `POST /subscription/create` — 创建订阅订单

#### `POST /subscription/notify/<channel>` — 支付通知回调

#### `POST /subscription/cancel` — 取消订阅

#### `POST /subscription/reactivate` — 重新激活订阅

#### `GET /subscription/orders` — 订单列表

#### `POST /subscription/retry-payment` — 重试支付

### 6.2 订阅管理（管理员）

#### `GET /subscription/admin/plans` — 套餐管理列表

#### `POST /subscription/admin/plans` — 创建套餐

#### `PUT /subscription/admin/plans/<pid>` — 更新套餐

#### `DELETE /subscription/admin/plans/<pid>` — 删除套餐

#### `GET /subscription/admin/subscriptions` — 所有订阅

#### `POST /subscription/admin/subscriptions/<sid>/manual-renew` — 手动续费

#### `GET /subscription/admin/orders` — 所有订单

#### `GET /subscription/admin/stats` — 订阅统计

#### `GET /subscription/admin/coupons` — 优惠券管理

#### `GET /subscription/admin/events` — 订阅事件

#### `GET /subscription/admin/audit-log` — 审计日志

### 6.3 部署订阅 API

前缀: `/api/subscription`

#### `GET /api/subscription/admin/codes` — 部署码列表（管理员）

#### `POST /api/subscription/admin/codes/generate` — 生成部署码（管理员）

**请求体**: `{"user_id": 1, "plan_key": "deploy_basic", "duration_days": 365}`

#### `POST /api/subscription/admin/codes/<code_id>/revoke` — 作废部署码

#### `POST /api/subscription/heartbeat` — 客户端心跳验证

**请求体**: `{"code": "DC-20260701-XXXXXX", "hostname": "server1", "version": "1.0.0"}`

**响应**:
```json
{
  "success": true,
  "data": {
    "valid": true,
    "days_remaining": 360,
    "status": "active",
    "message": "订阅有效",
    "plan_key": "deploy_basic"
  }
}
```

#### `GET /api/subscription/check` — 公共查询订阅状态

**参数**: `?code=DC-20260701-XXXXXX`

---

## 7. 内容管理 API

前缀: `/admin/cms`  
认证: 需要管理员 JWT

### 7.1 页面块管理

#### `GET /admin/cms/blocks/<page>` — 获取指定页面内容块

#### `GET /admin/cms/blocks/<page>/all` — 获取所有块

#### `POST /admin/cms/blocks` — 创建内容块

**请求体**: `{"page": "home", "block_type": "hero", "title": "...", "content": "...", "sort_order": 1}`

#### `PUT /admin/cms/blocks/<block_id>` — 更新内容块

#### `DELETE /admin/cms/blocks/<block_id>` — 删除内容块

#### `POST /admin/cms/blocks/<page>/reorder` — 排序内容块

### 7.2 文章管理

#### `GET /admin/cms/posts` — 文章列表

#### `POST /admin/cms/posts` — 创建文章

#### `PUT /admin/cms/posts/<post_id>` — 更新文章

#### `DELETE /admin/cms/posts/<post_id>` — 删除文章

#### `POST /admin/cms/posts/<post_id>/publish` — 发布/下架文章

### 7.3 分类管理

#### `GET /admin/cms/categories` — 分类列表

#### `POST /admin/cms/categories` — 创建分类

#### `PUT /admin/cms/categories/<cat_id>` — 更新分类

#### `DELETE /admin/cms/categories/<cat_id>` — 删除分类

#### `POST /admin/cms/categories/reorder` — 排序分类

### 7.4 设置

#### `GET /admin/cms/settings` — CMS 设置

#### `PUT /admin/cms/settings` — 更新设置

---

## 8. AI 矩阵 API

前缀: `/admin/agent-matrix`  
认证: 需要管理员 JWT

### 8.1 Agent 管理

#### `GET /admin/agent-matrix/agents` — Agent 列表

**参数**: `?role=sub&domain=shop&active_only=1`

#### `POST /admin/agent-matrix/agents` — 创建 Agent

#### `GET /admin/agent-matrix/agents/<aid>` — Agent 详情

#### `PUT /admin/agent-matrix/agents/<aid>` — 更新 Agent

#### `DELETE /admin/agent-matrix/agents/<aid>` — 删除 Agent

#### `POST /admin/agent-matrix/agents/<aid>/toggle` — 启用/禁用

#### `POST /admin/agent-matrix/agents/<aid>/test` — 测试 Agent

#### `GET /admin/agent-matrix/agents/<aid>/capabilities` — Agent 能力

### 8.2 任务管理

#### `GET /admin/agent-matrix/tasks` — 任务列表

**参数**: `?status=running&module=shop&agent_id=1`

#### `GET /admin/agent-matrix/tasks/<task_id>` — 任务详情

#### `POST /admin/agent-matrix/tasks/<task_id>/cancel` — 取消任务

#### `POST /admin/agent-matrix/tasks/<task_id>/retry` — 重试任务

#### `GET /admin/agent-matrix/tasks/<task_id>/logs` — 任务日志

#### `GET /admin/agent-matrix/tasks/recent` — 最近 20 条任务

### 8.3 对话（核心 AI 入口）

#### `POST /admin/agent-matrix/chat` — 向 Master Agent 发送指令

**请求体**:
```json
{
  "messages": [{"role": "user", "content": "帮我写一篇关于AI的文章"}],
  "session_id": "optional-session-id"
}
```

**响应**:
```json
{
  "success": true,
  "data": {"reply": "...", "session_id": "...", "tasks": [...]}
}
```

#### `POST /admin/agent-matrix/chat/tool` — 工具调用模式

#### `POST /admin/agent-matrix/chat/stream` — SSE 流式聊天

**请求体**: 同上，响应为 SSE 流 `text/event-stream`。

SSE 事件格式：
```
data: {"type": "token", "content": "回复片段"}
data: {"type": "done", "reply": "完整回复", "retrievedKnowledge": [...]}
data: {"type": "error", "content": "错误信息"}
```

#### `GET /admin/agent-matrix/chat/history` — 会话历史列表

#### `GET /admin/agent-matrix/chat/<session_id>` — 会话详情

#### `POST /admin/agent-matrix/chat/<session_id>/clear` — 清除会话

#### `GET /admin/agent-matrix/chat/search` — 搜索会话

**参数**: `?q=关键词`

### 8.4 任务调度

#### `POST /admin/agent-matrix/dispatch` — 直接下发任务给 Sub Agent

**请求体**: `{"agent_id": 1, "task_type": "content_generation", "params": {...}}`

### 8.5 提示词管理

#### `GET /admin/agent-matrix/providers` — 可用 LLM 提供商列表

#### `GET /admin/agent-matrix/prompts` — Prompt 模板列表

#### `GET /admin/agent-matrix/prompts/load` — 加载 Prompt 文件

### 8.6 统计监控

#### `GET /admin/agent-matrix/stats` — Agent 统计

#### `GET /admin/agent-matrix/dashboard` — 仪表盘

#### `GET /admin/agent-matrix/health` — 健康检查

#### `GET /admin/agent-matrix/token-stats` — Token 消耗统计

**参数**: `?period=7d&dimension=agent&agent_id=1`

#### `GET /admin/agent-matrix/token-logs` — Token 日志明细

### 8.7 图片生成

#### `POST /admin/agent-matrix/generate-image` — 生成图片

#### `POST /admin/agent-matrix/upload` — 上传文件

#### `GET /admin/agent-matrix/download/<filename>` — 下载文件

---

## 9. 工作流引擎 API

前缀: `/admin/automation`  
认证: 需要管理员 JWT

### 9.1 统计

#### `GET /admin/automation/stats` — 工作流统计

### 9.2 定时作业

#### `GET /admin/automation/jobs` — 作业列表

#### `POST /admin/automation/jobs` — 创建作业

#### `GET /admin/automation/jobs/<job_id>` — 作业详情

#### `PUT /admin/automation/jobs/<job_id>` — 更新作业

#### `DELETE /admin/automation/jobs/<job_id>` — 删除作业

#### `POST /admin/automation/jobs/<job_id>/toggle` — 启用/禁用

#### `POST /admin/automation/jobs/<job_id>/run` — 立即执行

### 9.3 DAG 工作流

#### `GET /admin/automation/workflows` — 工作流列表

#### `POST /admin/automation/workflows` — 创建工作流

#### `GET /admin/automation/workflows/<wf_id>` — 工作流详情

#### `PUT /admin/automation/workflows/<wf_id>` — 更新工作流

#### `DELETE /admin/automation/workflows/<wf_id>` — 删除工作流

#### `POST /admin/automation/workflows/<wf_id>/run` — 运行工作流

### 9.4 运行实例

#### `GET /admin/automation/instances` — 实例列表

#### `GET /admin/automation/instances/<inst_id>` — 实例详情

#### `POST /admin/automation/instances/<inst_id>/pause` — 暂停

#### `POST /admin/automation/instances/<inst_id>/resume` — 恢复

#### `POST /admin/automation/instances/<inst_id>/cancel` — 取消

### 9.5 系统

#### `GET /admin/automation/logs` — 执行日志

#### `GET /admin/automation/scheduler/status` — 调度器状态

#### `POST /admin/automation/scheduler/pause` — 暂停调度器

#### `POST /admin/automation/scheduler/resume` — 恢复调度器

#### `GET /admin/automation/health` — 健康检查

---

## 10. 平台公开 API

前缀: `/api/v1`  
认证: 部分无需认证

### 10.1 聊天（免登录）

#### `POST /api/v1/chat/save` — 保存会话消息

**请求体**: `{"openid": "xxx", "messages": [{"role": "user", "content": "你好"}]}`

#### `POST /api/v1/chat/history` — 获取会话历史

**请求体**: `{"openid": "xxx"}`

#### `POST /api/v1/chat/public` — 公开 AI 对话（官网商务机器人）

**请求体**: `{"messages": [...], "source": "website", "temperature": 0.7}`

IP 限流: 每 IP 每分钟 10 次。

#### `POST /api/v1/chat` — 流式 AI 对话（SSE）

**请求体**:
```json
{
  "messages": [{"role": "user", "content": "你们有什么产品？"}],
  "profile": {"name": "张三"},
  "visitCount": 3,
  "threeAskState": 0
}
```

响应为 SSE 流（`text/event-stream`）。

### 10.2 AI 对话（需登录）

#### `POST /api/v1/chat/request` — 非流式 AI 对话

**请求体**:
```json
{
  "messages": [{"role": "user", "content": "什么是RAG？"}],
  "temperature": 0.7,
  "max_tokens": 2048,
  "skip_rag": false
}
```

**响应**:
```json
{"success": true, "data": {"content": "RAG是...", "rag": true}}
```

### 10.3 用户画像

#### `POST /api/v1/profile/save` — 保存用户画像

**请求体**: `{"openid": "xxx", "profile": {"name": "张三", "age": 25}}`

#### `POST /api/v1/profile/get` — 获取用户画像

#### `POST /api/v1/profile/summary` — 保存会话摘要

### 10.4 知识库

需 JWT 认证。

#### `POST /api/v1/knowledge/list` — 知识库列表（分页）

**请求体**:
```json
{"keyword": "AI", "category": "tech", "page": 1, "pageSize": 10}
```

#### `POST /api/v1/knowledge/save` — 新增/更新知识块

**请求体**:
```json
{"id": "kb_001", "title": "什么是AI", "content": "AI是...", "keywords": ["AI","人工智能"], "category": "tech", "priority": 1}
```

#### `POST /api/v1/knowledge/delete` — 删除知识块

**请求体**: `{"id": "kb_001"}`

### 10.5 RAG 检索

#### `POST /api/v1/rag/search` — 混合语义检索

**请求体**:
```json
{"query": "什么是人工智能", "topK": 5, "category": "tech"}
```

**响应**:
```json
{
  "success": true,
  "data": [
    {"block": {"id": "...", "title": "...", "content": "...", "category": "tech"}, "score": 0.85}
  ]
}
```

### 10.6 其他

#### `POST /api/v1/notify/feishu` — 飞书通知代理

需 JWT 认证。

**请求体**: `{"cardData": {...}, "webhookUrl": "https://open.feishu.cn/..."}`

#### `POST /api/v1/feedback/save` — 保存用户反馈

**请求体**:
```json
{
  "openid": "xxx",
  "messageId": "msg_001",
  "feedback": "positive",
  "content": "回答得很好",
  "query": "你们有什么产品",
  "aiReply": "我们有..."
}
```

#### `POST /api/v1/visit/increment` — 递增访问计数

**请求体**: `{"openid": "xxx"}`

---

## 11. 内容工厂 API

前缀: `/admin/content-factory`  
认证: 需要管理员 JWT

### 11.1 数据源管理

#### `GET /admin/content-factory/sources` — 数据源列表

#### `POST /admin/content-factory/sources` — 添加数据源

#### `PUT /admin/content-factory/sources/<sid>` — 更新数据源

#### `DELETE /admin/content-factory/sources/<sid>` — 删除数据源

### 11.2 内容采集

#### `POST /admin/content-factory/crawl` — 执行采集

#### `GET /admin/content-factory/contents` — 采集内容列表

#### `DELETE /admin/content-factory/contents/<rid>` — 删除采集内容

### 11.3 AI 加工

#### `POST /admin/content-factory/process` — AI 加工内容

#### `POST /admin/content-factory/ai-format` — AI 格式化

#### `POST /admin/content-factory/ai-cover` — AI 生成封面

### 11.4 审核发布

#### `POST /admin/content-factory/review` — 审核

#### `POST /admin/content-factory/publish` — 发布

### 11.5 技能推送

#### `POST /admin/content-factory/push-skill` — 推送技能

#### `GET /admin/content-factory/pushed-skills` — 已推送技能

#### `DELETE /admin/content-factory/pushed-skills/<push_id>` — 删除推送

### 11.6 其他

#### `GET /admin/content-factory/tasks` — 任务列表

#### `GET /admin/content-factory/stats` — 统计

#### `POST /admin/content-factory/generate-static` — 生成静态页面

#### `POST /admin/content-factory/push-to-knowledge` — 推送到知识库

---

## 12. 1688 集成 API

前缀: `/admin/ali-api`  
认证: 需要管理员 JWT

### 12.1 OAuth 认证

#### `GET /admin/ali-api/oauth/url` — 获取授权 URL

#### `GET/POST /admin/ali-api/oauth/callback` — 授权回调

#### `GET /admin/ali-api/oauth/status` — OAuth 状态

#### `POST /admin/ali-api/oauth/refresh` — 刷新 Token

#### `POST /admin/ali-api/oauth/disconnect` — 断开连接

### 12.2 商品管理

#### `GET /admin/ali-api/items` — 商品列表

#### `GET /admin/ali-api/items/<item_id>` — 商品详情

#### `POST /admin/ali-api/items/collect` — 采集商品

#### `POST /admin/ali-api/items/search` — 搜索商品

#### `POST /admin/ali-api/items/<item_id>/ai-optimize` — AI 优化

#### `POST /admin/ali-api/items/<item_id>/publish` — 发布商品

#### `POST /admin/ali-api/items/<item_id>/unpublish` — 下架

### 12.3 图片管理

#### `POST /admin/ali-api/items/<item_id>/images/upload` — 上传图片

#### `DELETE /admin/ali-api/items/<item_id>/images/<idx>` — 删除图片

#### `POST /admin/ali-api/items/<item_id>/images/reorder` — 排序图片

### 12.4 系统

#### `GET /admin/ali-api/config` — 获取配置

#### `GET /admin/ali-api/cache/stats` — 缓存统计

#### `POST /admin/ali-api/cache/clear` — 清除缓存

#### `GET /admin/ali-api/logs` — 操作日志

---

## 13. 云服务开通 API

前缀: `/cloud`  
认证: 需要用户 JWT

#### `GET /cloud/products` — 云产品列表

#### `GET /cloud/instances` — 实例列表

#### `GET /cloud/instances/<iid>` — 实例详情

#### `POST /cloud/instances/provision` — 开通实例

#### `GET /cloud/instances/<iid>/status` — 实例状态

#### `POST /cloud/instances/<iid>/terminate` — 终止实例

---

## 14. 分析统计 API

前缀: `/admin/analytics`  
认证: 需要管理员 JWT

#### `POST /admin/analytics/api/v1/log` — 记录日志

#### `POST /admin/analytics/api/v1/event` — 记录事件

#### `GET /admin/analytics/api/v1/realtime` — 实时数据

#### `GET /admin/analytics/api/v1/trend` — 趋势数据

#### `GET /admin/analytics/api/v1/pages` — 页面统计

#### `GET /admin/analytics/api/v1/sources` — 来源统计

#### `GET /admin/analytics/api/v1/geo` — 地理位置

#### `GET /admin/analytics/api/v1/devices` — 设备统计

#### `GET /admin/analytics/api/v1/overview` — 概览

#### `GET /admin/analytics/api/v1/export` — 导出数据

---

## 15. 健康检查 API

前缀: `/health`

#### `GET /health/` — 健康检查仪表盘

#### `GET /health/api/status` — 系统状态概览

#### `POST /health/api/run` — 执行健康检查

#### `GET /health/api/history` — 检查历史

#### `GET /health/api/checks` — 检查项列表

#### `PUT /health/api/checks/<check_id>` — 更新检查项

#### `DELETE /health/api/checks/<check_id>` — 删除检查项

#### `GET /health/api/trend` — 检查趋势

#### `GET /health/api/alerts` — 告警列表

---

## 16. 验证码服务 API

前缀: `http://127.0.0.1:8090`（内部服务）

#### `GET /api/captcha/generate` — 生成滑块验证码

#### `POST /api/captcha/verify` — 验证滑块

**请求体**: `{"token": "uuid", "drag_distance": 120, "drag_trace": [...]}`

#### `POST /api/captcha/consume` — 消费验证码（一次性使用）

---

## 附录：用户 Agent API

前缀: `/agent`  
认证: 需要用户 JWT

#### `GET /agent/list` — 用户 Agent 列表

#### `POST /agent/create` — 创建 Agent

**请求体**: `{"agent_name": "我的助手", "agent_type": "personal", "default_scopes": ["stock:read", "market:alert"]}`

#### `GET /agent/<aid>` — Agent 详情（含 API Keys）

#### `PUT /agent/<aid>` — 更新 Agent

#### `DELETE /agent/<aid>` — 删除 Agent

#### `GET /agent/<aid>/keys` — API Key 列表

#### `POST /agent/<aid>/keys/create` — 生成 API Key

**请求体**: `{"name": "我的Key", "scopes": [...], "expire_days": 365}`

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "key": "ek-abc123...",
    "key_prefix": "ek-abc123...def0",
    "name": "我的Key",
    "expire_days": 365,
    "warning": "⚠️ 密钥只显示一次！"
  }
}
```

#### `DELETE /agent/<aid>/keys/<kid>` — 撤销 Key

#### `POST /agent/<aid>/keys/<kid>/rotate` — 轮换 Key

#### `GET /agent/<aid>/stats` — Agent 使用统计

---

## 附录：抖音小程序 API

前缀: `/douyin_mp`

#### `POST /douyin_mp/login/code` — 抖音小程序登录

#### `GET /douyin_mp/user/info` — 获取用户信息

#### `POST /douyin_mp/user/unbind_douyin` — 解绑抖音

#### `GET /douyin_mp/user/bind_status` — 绑定状态

---

## 附录：评论 API

#### `POST /api/v1/comments` — 提交评论

#### `GET /api/v1/comments/<post_id>` — 获取评论列表

#### `GET /admin/comments` — 管理员评论列表

#### `PUT /admin/comments/<cid>/review` — 审核评论

---

## 7. Social Media Mini-Program API

> New in v2026.07 — Endpoints used by platform-specific mini-programs (Douyin, WeChat, Telegram, LINE).

前缀: `/api/v1/mini-program/`

### 7.1 认证

#### `POST /api/v1/mini-program/auth/login` — 小程序登录

平台通过 `code` / `initData` / `accessToken` 换系统 JWT。

**请求体示例**（微信/抖音）:
```json
{
  "platform": "wechat",
  "code": "wx_code_from_login"
}
```

**请求体示例**（Telegram）:
```json
{
  "platform": "telegram",
  "initData": "tg_init_data_string"
}
```

**请求体示例**（LINE）:
```json
{
  "platform": "line",
  "accessToken": "line_access_token",
  "userId": "line_user_id",
  "displayName": "User Name"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "token": "jwt_token_string",
    "user": { "id": 1, "username": "wx_xxx", "display_name": "User" }
  }
}
```

#### `POST /api/v1/mini-program/auth/validate` — 验证 JWT 有效性

**请求体**:
```json
{ "token": "jwt_token_string" }
```

**响应**:
```json
{ "success": true, "data": { "valid": true, "user": { ... } } }
```

### 7.2 聊天

#### `POST /api/v1/mini-program/chat/send` — 非流式 AI 对话

**请求体**:
```json
{
  "message": "你好",
  "history": [],
  "platform": "telegram"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "reply": "你好！有什么可以帮助你的？",
    "retrievedKnowledge": []
  }
}
```

#### `POST /api/v1/mini-program/chat/stream` — 流式 AI 对话（SSE）

**请求体**: 同上 `send`。

**响应**: SSE 流，事件类型：
- `data: {"type":"token","content":"你好"}`
- `data: {"type":"done","reply":"完整回复","retrievedKnowledge":[]}`
- `data: {"type":"error","error":"错误信息"}`

#### `GET /api/v1/mini-program/chat/history` — 获取聊天历史

**响应**:
```json
{ "success": true, "data": { "messages": [{"role":"user","content":"你好"}, ...] } }
```

### 7.3 知识库

#### `GET /api/v1/mini-program/knowledge/search` — 搜索知识库

**参数**: `q` (查询关键词), `topK` (返回条数, 默认 5), `category` (可选分类过滤)

**响应**:
```json
{ "success": true, "data": [{"id":"1","title":"退货政策","content":"...","score":0.95,"category":"policy"}] }
```

### 7.4 用户

#### `GET /api/v1/mini-program/user/profile` — 获取用户资料

**响应**:
```json
{ "success": true, "data": { "id":1, "username":"tg_xxx", "display_name":"用户" } }
```

### 7.5 站点信息

#### `GET /api/v1/mini-program/site/info` — 获取站点品牌信息

**响应**:
```json
{ "success": true, "data": { "site_name":"VeroRun","primary_color":"#4F46E5","logo_url":"..." } }
```

#### `GET /api/v1/mini-program/site/pages` — 获取已发布页面列表

#### `GET /api/v1/mini-program/site/page/<slug>` — 获取指定页面内容

---

## 附录：会话管理 API

前缀: `/session`

#### `GET /session/list` — 当前用户会话列表

#### `GET /session/current` — 当前会话详情

#### `DELETE /session/<sid>` — 删除会话

---

> **文档维护说明**  
> 本文档基于 v2026.07 代码生成。由于系统包含约 380+ API 端点，本文档覆盖了所有主要路由分组。  
> 如需某个具体端点的详细请求/响应示例，请查阅对应模块的路由文件。
