# 支付与订阅系统（Payment & Subscription）

## 概述

本模块提供 **支付网关集成**（Payment Gateway Integration）和 **订阅计费**（Subscription Billing）两大核心能力，支持支付宝/微信支付、套餐订阅、自动续费、优惠券及电子发票等完整商业闭环。

模块架构：

```
┌──────────────────────────────────────────────────┐
│                  Frontend                        │
│  (subscribe_portal.html / 用户购买页)              │
└──────────────┬───────────────────────────────────┘
               │ HTTP/REST
┌──────────────▼───────────────────────────────────┐
│          Subscription Blueprint                  │
│    auth-center/routes/subscription/__init__.py   │
│   ┌─────────┬──────────┬──────────┬──────────┐  │
│   │  Plans  │  Orders  │  Coupon  │  Invoices│  │
│   └────┬────┴────┬─────┴────┬─────┴────┬─────┘  │
└────────┼────────┼──────────┼──────────┼─────────┘
         │        │          │          │
┌────────▼──┐ ┌──▼────────┐ │ ┌────────▼────────┐
│  Alipay   │ │ WeChat Pay│ │ │  Invoice Service │
│  Gateway  │ │  Gateway  │ │ │  generate_pdf()  │
└─────┬─────┘ └─────┬─────┘ │ └─────────────────┘
      │             │        │
┌─────▼─────────────▼────────▼───────────────────┐
│             Payment Gateway Stub                │
│   (未配置密钥时自动降级为开发桩模式)                  │
└────────────────────────────────────────────────┘
```

---

## 支付网关（Payment Gateways）

### 支付宝（Alipay）

**文件：** [`auth-center/routes/subscription/gateway/alipay.py`](../auth-center/routes/subscription/gateway/alipay.py)

支持两种支付模式：

| 模式 | 方法 | 适用场景 |
|------|------|----------|
| 一次性支付（即时到账） | `call_alipay_page_pay()` | 首次购买套餐 |
| 周期扣款（签约 + 自动扣款） | `create_cycle_sign_request()` / `execute_charge()` | 自动续费订阅 |

- **API 方法：** `alipay.trade.page.pay`（电脑网站支付）、`alipay.trade.pay`（协议扣款）
- **签名算法：** RSA2（SHA256withRSA）
- **通知机制：** 异步 POST 回调 `POST /subscription/notify/alipay`
- **配置项：** `alipay_app_id`（system_config → 环境变量）、商户私钥文件 `certs/alipay_private_key.pem`
- **桩模式（Stub）：** 未配置 `alipay_app_id` 时自动降级，返回 `stub: true` 便于开发调试

### 微信支付（WeChat Pay）

**文件：** [`auth-center/routes/subscription/gateway/wechat.py`](../auth-center/routes/subscription/gateway/wechat.py)

| 模式 | 方法 | 适用场景 |
|------|------|----------|
| Native 扫码支付（一次性） | `call_native_pay()` | 首次购买套餐 |
| 委托扣款（签约 + 自动扣款） | `execute_contract_charge()` | 自动续费 |

- **API 协议：** 微信支付 V3 API
- **认证方式：** 商户证书 RSA 签名 + 平台证书 V3 密钥
- **加密算法：** AES-256-GCM（回调 resource 解密）
- **通知机制：** 异步 POST 回调 `POST /subscription/notify/wechat`
- **配置项：** `wechat_app_id`、`wechat_mchid`、`wechat_api_v3_key`、`wechat_cert_serial`、`wechat_plan_id`
- **桩模式：** 未配置 `WECHAT_APPID` 时自动降级

### 支付回调统一入口

**文件：** [`auth-center/routes/subscription/__init__.py`](../auth-center/routes/subscription/__init__.py) → `payment_notify()`（第 440 行）

```python
POST /subscription/notify/<channel>  # channel = wechat | alipay
```

所有支付渠道的回调均汇聚至此，由 `_fulfill_order()`（第 458 行）执行订单履约逻辑。

---

## 数据库表结构（Database Tables）

### `subscription_plans` — 套餐定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `plan_key` | TEXT UNIQUE | 套餐标识（如 `free` / `standard` / `pro` / `site_basic`） |
| `name` | TEXT | 套餐名称 |
| `price_month` / `price_year` | INTEGER | 月付 / 年付价格（**单位：分**） |
| `trial_days` | INTEGER | 试用天数 |
| `tier` | TEXT | 等级（`free` / `premium` / `pro` / `enterprise`） |
| `features_json` | TEXT | 特性列表 JSON 数组 |
| `is_active` | INTEGER | 是否启用 |
| `sort_order` | INTEGER | 排序权重 |

内置默认套餐：`free`（免费）、`standard`（标准）、`pro`（专业）。

### `subscriptions` — 用户订阅

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | INTEGER UNIQUE | 用户（**一人一订阅**） |
| `plan_key` | TEXT | 当前套餐 |
| `period` | TEXT | `month` / `year` |
| `status` | TEXT | `active` / `trialing` / `past_due` / `canceled` / `expired` |
| `current_period_start` / `current_period_end` | TEXT | 当前周期起止（ISO 时间） |
| `auto_renew` | INTEGER | 是否自动续费 |
| `payment_method` | TEXT | `wechat` / `alipay` |
| `alipay_agreement_id` / `wechat_contract_id` | TEXT | 支付网关签约 ID |
| `pending_plan_key` / `pending_period` / `pending_at` | TEXT | 降级待生效套餐 |

### `subscription_orders` — 订阅订单

| 字段 | 类型 | 说明 |
|------|------|------|
| `order_no` | TEXT UNIQUE | 订单号（`SUB` + 时间 + 随机） |
| `amount_fen` | INTEGER | 金额（分） |
| `item_type` | TEXT | `new` / `renew` / `upgrade` / `downgrade` |
| `status` | TEXT | `pending` → `paid` / `failed` / `cancelled` |
| `payment_method` | TEXT | 支付方式 |
| `channel_order_id` | TEXT | 网关交易号 |
| `user_deleted` | INTEGER | 用户软删标记 |

### `coupons` — 优惠券

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | TEXT UNIQUE | 优惠码 |
| `type` / `coupon_type` | TEXT | `fixed`（固定减）/ `percent`（百分比）/ `first_month_percent`（首月折扣） |
| `value` | INTEGER | 折扣值（固定金额为分，百分比为 0-100 整数） |
| `max_uses` / `used_count` | INTEGER | 总使用次数限制 / 已用次数 |
| `max_per_user` / `per_user_limit` | INTEGER | 每人使用上限 |
| `min_amount_fen` | INTEGER | 最低消费门槛（分） |
| `applicable_plans` | TEXT | 适用套餐列表（逗号分隔，空为全部） |
| `first_month_only` | INTEGER | 是否仅限首月 |
| `stackable` | INTEGER | 是否可叠加 |
| `active_from` / `active_to` | TEXT | 限时窗口 |
| `expires_at` | TEXT | 过期时间 |
| `is_active` | INTEGER | 是否启用 |

### `coupon_redemptions` — 优惠券核销记录

| 字段 | 说明 |
|------|------|
| `coupon_id` | 关联优惠券 |
| `user_id` | 使用用户 |
| `order_no` | 关联订单 |
| `discount_fen` | 折扣金额（分） |

### `invoices` — 电子发票

| 字段 | 说明 |
|------|------|
| `invoice_no` | 发票号（`INV` + 日期 + 4 位随机） |
| `order_no` | 关联订单 |
| `amount_fen` / `amount_yuan` | 金额 |
| `plan_name` / `period_text` | 套餐名称 / 周期描述 |
| `pdf_path` | PDF 文件路径 |
| `status` | `issued` / `cancelled` |

### `payment_events` — 支付事件日志

记录每笔扣款（含自动续费）的成功/失败明细，用于排查和对账。

### `subscription_audit_log` — 审计日志

记录所有关键操作（创建套餐、取消订阅、手动续费等），含操作人 IP 和管理员 ID。

---

## 套餐管理（Plan Management）

**文件：** [`auth-center/routes/subscription/__init__.py`](../auth-center/routes/subscription/__init__.py) → 第 76-88 行

- **多层级套餐：** 按 `tier` 等级（`free` < `premium` < `pro` < `enterprise`）排序
- **双周期定价：** 每个套餐有 `price_month`（月付）和 `price_year`（年付）两个价格，**均以分为单位**
- **特性 JSON：** `features_json` 字段存储套餐特性列表，前端通过 `/plans/features` 端点获取特性对比矩阵（第 120 行）
- **站点级套餐：** 建站业务线使用 `site_basic` / `site_standard` / `site_pro` 系列（数据库 migration 第 1995 行）

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/subscription/plans` | 用户端：获取所有活跃套餐及特性 |
| GET | `/subscription/plans/features` | 特性对比矩阵 |
| GET | `/subscription/admin/plans` | 管理员：全部套餐列表 |
| POST | `/subscription/admin/plans` | 管理员：创建套餐 |
| PUT | `/subscription/admin/plans/<id>` | 管理员：更新套餐 |
| DELETE | `/subscription/admin/plans/<id>` | 管理员：删除套餐 |

---

## 订单流程（Order Flow）

```
┌─────────┐   ┌──────────┐   ┌────────────┐   ┌──────────┐
│ 用户选择  │ → │ 创建订单   │ → │ 跳转支付网关 │ → │ 支付完成   │
│ 套餐+周期  │   │ POST     │   │ (支付宝/微信)│   │ (异步回调) │
└─────────┘   │ /create  │   └────────────┘   └────┬─────┘
              └──────────┘                         │
                                                   ▼
              ┌──────────┐   ┌────────────┐   ┌──────────┐
              │ 订阅激活   │ ← │ 订单履约    │ ← │ 回调验证   │
              │ (active)  │   │ _fulfill   │   │ 签名       │
              └──────────┘   │ _order()    │   └──────────┘
                             └────────────┘
```

**核心履约函数：** `_fulfill_order()`（第 458 行）

支付成功后自动执行：

1. 更新订单状态 `pending → paid`，记录支付网关交易号
2. 根据 `item_type` 执行不同逻辑：
   - `new` → 创建新订阅记录（`INSERT OR REPLACE`，幂等安全）
   - `upgrade` → 延长周期结束时间（取新旧结束时间最大值）
   - `renew` → 将 `current_period_end` 增加一个周期
3. 同步更新 `app_authorizations`（授权表）和 `skill_keys`（API 密钥）的等级
4. 自动生成电子发票（通过 `invoice_service.create_invoice_record()`）

### 升级/降级逻辑（第 346 行）

| 类型 | 条件 | 处理方式 |
|------|------|----------|
| 升级（Upgrade） | 新套餐 tier 更高 | 立即生效，按剩余天数折算差价，生成 `UPG` 订单 |
| 降级（Downgrade） | 新套餐 tier 更低 | 下个周期生效，记录 `pending_plan_key`，当前周期不变 |

---

## 发票系统（Invoice System）

**服务文件：** [`auth-center/services/invoice_service.py`](../auth-center/services/invoice_service.py)

- **自动生成：** 每笔支付成功后在 `_fulfill_order()` 中自动触发
- **PDF 生成：** 使用 `fpdf2` 库生成标准 A4 电子发票，含中文字体支持
- **公司信息：** 徐州易开网络科技有限公司（`SELLER_NAME` = 徐州易开网络科技有限公司）
- **存储路径：** `data/invoices/` 目录
- **下载端点：** `GET /subscription/my/invoices/<invoice_no>/download`（第 224 行）
- **兜底策略：** 如 `fpdf2` 未安装，返回 JSON 数据而非报错

---

## 管理员操作（Admin Operations）

**文件：** [`auth-center/routes/subscription/__init__.py`](../auth-center/routes/subscription/__init__.py) → 第 725-991 行

| 端点 | 说明 |
|------|------|
| `POST /subscription/admin/plans` | CRUD：创建/更新/删除套餐 |
| `GET /subscription/admin/subscriptions` | 订阅列表（支持分页+搜索+状态筛选） |
| `POST .../admin/subscriptions/<id>/manual-renew` | **手动续费**：延长一个周期 |
| `POST .../admin/subscriptions/<id>/force-cancel` | **强制取消**：立即到期并降级为免费版 |
| `GET /subscription/admin/orders` | 订单管理列表 |
| `GET /subscription/admin/coupons` | 优惠券管理（CRUD） |
| `GET /subscription/admin/stats` | **数据看板**：MRR、活跃订阅数、本月新增/取消、今日/本月收入、套餐分布 |
| `GET /subscription/admin/events` | 支付事件日志 |
| `GET /subscription/admin/audit-log` | 操作审计日志 |

### 数据看板（Admin Stats, 第 873 行）

- **MRR**（Monthly Recurring Revenue）：按月汇总活跃订阅的月均收入（年付除以 12）
- **活跃订阅数**：`status IN ('active','trialing')`
- **本月新增 / 取消数**
- **今日 / 本月收入**
- **套餐分布**：各套餐当前活跃用户数

---

## 优惠券系统（Coupon System）

**回调逻辑：** `_apply_coupon()` 函数（第 996 行）

### 折扣类型

| `coupon_type` | 说明 | 折扣计算 |
|---------------|------|----------|
| `fixed` | 固定金额减免 | `min(value, amount_fen)` |
| `percent` | 百分比折扣 | `amount_fen * value / 100` |
| `first_month_percent` | 首月特价百分比 | 同上，标记首月 |

### 验证规则（Validation）

应用优惠码时按顺序执行以下检查，任一不通过则返回 `discount_fen = 0`：

1. **存在性 & 活跃状态**：`is_active=1` 且 `expires_at` 未过期
2. **限时窗口**：`active_from` / `active_to` 在有效期内
3. **总使用次数**：`used_count < max_uses`
4. **每人使用次数**：该用户已使用次数 `<= max_per_user`
5. **适用套餐**：若 `applicable_plans` 非空，当前套餐必须在列表中
6. **最低消费**：`amount_fen >= min_amount_fen`
7. **叠加检查**：若 `stackable=0`，检查近期是否有其他不可叠加优惠券已使用

---

## 续费与挽留（Renewal & Dunning）

**服务文件：** [`auth-center/routes/subscription/renewal.py`](../auth-center/routes/subscription/renewal.py)

### 自动续费引擎

通过 **cron 定时任务** 每日自动执行：

```bash
# 每日扫描
python auth-center/routes/subscription/renewal.py
```

### 流程

```
                    ┌────────────────────────────┐
                    │  每日扫描: run_renewal_scan() │
                    │  查找 current_period_end     │
                    │  = today 的活跃订阅          │
                    └────────────┬───────────────┘
                                 ▼
                    ┌────────────────────────────┐
                    │  _process_renewal()         │
                    │  1. 创建 REN 续费订单        │
                    │  2. 调用 execute_charge()    │
                    │   (支付宝周期扣款 / 微信委托)  │
                    └────────────┬───────────────┘
                          ┌─────┴─────┐
                          ▼           ▼
                    ┌──────────┐ ┌──────────────┐
                    │ 扣款成功   │ │ 扣款失败      │
                    │ _fulfill  │ │ _mark_past   │
                    │ _order()  │ │ _due()       │
                    │ 续期+通知  │ │ status→past  │
                    └──────────┘ │ _due + 通知   │
                                └──────┬───────┘
                                       ▼
                          ┌────────────────────────┐
                          │ Dunning 重试计划         │
                          │ 第1/3/7天重试扣款        │
                          │ (run_dunning_scan())    │
                          └────────────────────────┘
                                       │
                          ┌────────────┘
                          ▼
                    ┌────────────────────────────┐
                    │ 宽限期 (GRACE_DAYS=7) 过后   │
                    │ status → expired           │
                    │ 降级为 free 套餐              │
                    │ 同步降级 app_authorizations  │
                    └────────────────────────────┘
```

### 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `GRACE_DAYS` | 7 | 宽限期天数，逾期后降级为免费版 |
| `DUNNING_DAYS` | [1, 3, 7] | 扣款失败后第 1/3/7 天重试 |
| `auto_renew` | 1 | 新订阅默认开启自动续费 |

### 用户自助

| 端点 | 说明 |
|------|------|
| `POST /subscription/cancel` | 取消订阅（到期不续），支持填写原因和反馈 |
| `POST /subscription/reactivate` | 重新激活已取消的订阅 |
| `POST /subscription/retry-payment` | 缴费挽回：`past_due` 用户手动补缴 |
| `PUT /subscription/my/payment-method` | 更换支付方式 |

---

## 多租户（Multi-tenant）— 按站点配置套餐

支持为不同站点（`site_key`）配置独立的套餐体系：

- **建站套餐**（Site Plans）：`site_basic`（基础版 ¥599/月）、`site_standard`（标准版 ¥1,599/月）、`site_pro`（专业版 ¥2,999/月）
- **API 套餐**（API Plans）：`free`、`standard`（¥88/月）、`pro`（¥188/月）
- **灵活筛选：** `plan_key` 命名规范（`site_*` 前缀），前端按场景过滤

### 备选订阅模块（Module-DB）

**文件：** [`auth-center/routes/subscription/__init__.py`](../auth-center/routes/subscription/__init__.py)

- 本模块使用独立的 SQLite 数据库连接（`DB_PATH`），与 `community.models` 解耦
- **Webhook（Trademind 集成）：** 订阅状态变更自动同步至 `app_authorizations` 和 `skill_keys` 表

---

## 文件索引（File Index）

| 路径 | 用途 |
|------|------|
| `auth-center/routes/subscription/__init__.py` | 核心蓝图：所有 API 端点 + 订单履约 + 优惠券逻辑 |
| `auth-center/routes/subscription/gateway/alipay.py` | 支付宝支付网关（一次性支付 + 周期扣款） |
| `auth-center/routes/subscription/gateway/wechat.py` | 微信支付网关（Native 扫码 + 委托扣款） |
| `auth-center/routes/subscription/renewal.py` | 自动续费引擎 + Dunning 重试 |
| `auth-center/services/invoice_service.py` | 电子发票 PDF 生成 |
| `auth-center/services/payment_service.py` | 商城订单支付宝支付封装（旧版） |
| `auth-center/routes/payment.py` | 旧版支付路由（桩模式，逐步迁移中） |
| `auth-center/services/alipay_service.py` | 支付宝 OAuth 登录服务 |
| `auth-center/services/renewal_reminder.py` | 续费通知服务（微信/邮件推送） |
| `auth-center/models/database.py` | 数据库表定义 + 数据迁移 |
