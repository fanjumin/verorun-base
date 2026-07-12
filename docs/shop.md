# 商城系统（Shop Module）

## 概述 Overview

易站智能建站系统的**商城模块**提供完整的电商能力（E-Commerce），涵盖商品管理、多规格 SKU、购物车、订单流转、支付网关集成与云服务自动开通。

| 维度 | 说明 |
|------|------|
| 定位 | 内置电商子系统，支持实物/虚拟/云服务商品 |
| 技术栈 | Flask + SQLite + Blueprint |
| 管理端 API | `auth-center/routes/shop_admin.py`（/shop/*） |
| 前端 API | `platform/routes/shop_public.py`（/shop/api/*） |
| 支付服务 | `auth-center/services/payment_service.py` |
| 前端页面 | `platform/templates/shop.html`、`shop_detail.html`、`cart.html` |

---

## 数据库表 Database Tables

### 商品体系

#### products — 商品主表

文件：`auth-center/models/database.py`（第 1620–1650 行附近）

```sql
CREATE TABLE products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    subtitle        TEXT DEFAULT '',
    product_type    TEXT NOT NULL DEFAULT 'service',
                    -- service / cloud_service
    category        TEXT DEFAULT '',
    category_id     INTEGER DEFAULT 0,
    price           REAL NOT NULL DEFAULT 0,
    original_price  REAL DEFAULT 0,
    stock           INTEGER DEFAULT 0,
    sales_count     INTEGER DEFAULT 0,
    thumbnail       TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    features        TEXT DEFAULT '[]',       -- JSON 数组
    images          TEXT DEFAULT '[]',       -- JSON 数组
    ai_config       TEXT DEFAULT '{}',       -- JSON 对象
    product_config  TEXT DEFAULT '{}',       -- cloud_service 专用配置
    sort_order      INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT,
    updated_at      TEXT
);
```

关键字段：
- **product_type**：`service`（普通服务/实物）或 `cloud_service`（云服务，支付后触发自动开通）
- **is_active**：`1` 上架 / `0` 下架
- **features** / **images**：JSON 格式存储的特性列表和多图 URL
- **ai_config**：AI 优化配置（如 AI 重写标题、描述）
- **product_config**：云服务商品专属配置（specs、service_type、provider 等）

#### categories — 商品分类

```sql
CREATE TABLE categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE,
    parent_id   INTEGER DEFAULT 0,
    level       INTEGER DEFAULT 0,
    icon        TEXT DEFAULT '',
    sort_order  INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT,
    updated_at  TEXT
);
```

支持多级分类（parent_id + level），通过 category_id 关联 products。

#### product_specs / product_spec_values / product_skus — 多规格 SKU

```sql
-- 规格名（如 "颜色"、"尺寸"）
CREATE TABLE product_specs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    spec_name   TEXT NOT NULL,
    sort_order  INTEGER DEFAULT 0
);

-- 规格值（如 "红色"、"XL"）
CREATE TABLE product_spec_values (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id     INTEGER NOT NULL REFERENCES product_specs(id),
    spec_value  TEXT NOT NULL,
    sort_order  INTEGER DEFAULT 0
);

-- SKU 库存
CREATE TABLE product_skus (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    sku_code    TEXT NOT NULL,           -- 如 "R-001-RED-XL"
    spec_path   TEXT NOT NULL DEFAULT '{}', -- JSON: {"颜色":"红色","尺寸":"XL"}
    price       REAL NOT NULL DEFAULT 0,
    stock       INTEGER DEFAULT 0,
    image       TEXT DEFAULT '',
    is_active   INTEGER DEFAULT 1,
    created_at  TEXT,
    updated_at  TEXT
);
```

每个 SKU 可以独立定价、管理库存，前端通过 `spec_path` 匹配用户选择的规格组合。

### 订单体系

#### order_items — 订单明细

文件：`auth-center/models/database.py`（第 1685–1710 行附近）

```sql
CREATE TABLE order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        TEXT NOT NULL,        -- 订单号（SP 开头）
    user_id         INTEGER NOT NULL REFERENCES users(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    product_title   TEXT NOT NULL DEFAULT '',
    quantity        INTEGER DEFAULT 1,
    unit_price      REAL NOT NULL DEFAULT 0,
    subtotal        REAL NOT NULL DEFAULT 0,
    coupon_id       INTEGER DEFAULT NULL,
    discount        REAL DEFAULT 0,
    status          TEXT DEFAULT 'pending',
                    -- pending / paid / shipped / completed / refunding / refunded / cancelled
    payment_method  TEXT DEFAULT '',      -- alipay / wechat / stub
    payment_trade_no TEXT DEFAULT '',
    tracking_company TEXT DEFAULT '',     -- 快递公司
    tracking_number TEXT DEFAULT '',      -- 快递单号
    shipping_status TEXT DEFAULT '',      -- pending / shipped
    refund_reason   TEXT DEFAULT '',
    refund_requested_at TEXT,
    refunded_at     TEXT,
    paid_at         TEXT,
    shipped_at      TEXT,
    completed_at    TEXT,
    created_at      TEXT
);
```

### 购物车

#### carts — 购物车

```sql
CREATE TABLE carts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    sku_id      INTEGER DEFAULT 0 REFERENCES product_skus(id),
    quantity    INTEGER DEFAULT 1,
    created_at  TEXT,
    UNIQUE(user_id, product_id)
);
```

支持 SKU 级别加入购物车（sku_id 字段，2026-06-19 迁移添加）。

### 优惠券

#### coupons — 优惠券

文件：`auth-center/models/database.py`（第 1670–1685 行附近）

```sql
CREATE TABLE coupons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL DEFAULT '',
    coupon_type     TEXT NOT NULL DEFAULT 'fixed',
                    -- fixed / percent / free_shipping
    value           REAL NOT NULL DEFAULT 0,
    min_amount      REAL DEFAULT 0,
    usage_limit     INTEGER DEFAULT 0,
    used_count      INTEGER DEFAULT 0,
    expire_at       TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT
);
```

额外字段（后续迁移添加）：`coupon_category`（general / new_user / threshold）、`applicable_products`、`per_user_limit`、`min_quantity`。使用记录存放于 `coupon_redemptions` 表。

### 购买记录

#### user_purchases — 用户购买记录

```sql
CREATE TABLE user_purchases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    product_id      INTEGER NOT NULL REFERENCES products(id),
    order_id        TEXT DEFAULT '',
    purchase_type   TEXT NOT NULL DEFAULT 'once',
                    -- once / subscription
    expire_at       TEXT,
    status          TEXT DEFAULT 'active',
                    -- active / expired / cancelled
    created_at      TEXT
);
```

---

## 商品管理 Product Management

### 管理端 API（/shop/*）

所有管理接口需 `Authorization: Bearer <admin_token>`。

| 端点 | 方法 | 功能 |
|------|------|------|
| `/shop/products` | GET | 商品列表（支持 search/category_id/is_active 筛选） |
| `/shop/products` | POST | 创建商品 |
| `/shop/products/<pid>` | GET | 获取商品详情 |
| `/shop/products/<pid>` | PUT | 更新商品 |
| `/shop/products/<pid>` | DELETE | 删除商品（级联清理 specs/SKUs） |
| `/shop/products/<pid>/preview` | GET | 管理员预览（绕过 is_active） |
| `/shop/products/<pid>/specs` | GET | 获取规格列表（含规格值） |
| `/shop/products/<pid>/specs` | POST | 添加规格名 |
| `/shop/products/<pid>/specs/<sid>` | PUT | 修改规格名 |
| `/shop/products/<pid>/specs/<sid>` | DELETE | 删除规格及值 |
| `/shop/products/<pid>/specs/<sid>/values` | POST | 添加规格值 |
| `/shop/products/<pid>/specs/<sid>/values/<vid>` | DELETE | 删除规格值 |
| `/shop/products/<pid>/skus` | GET | 获取 SKU 列表 |
| `/shop/products/<pid>/skus` | POST | 创建 SKU |
| `/shop/products/<pid>/skus/<skuid>` | PUT | 更新 SKU |
| `/shop/products/<pid>/skus/<skuid>` | DELETE | 删除 SKU |
| `/shop/products/<pid>/images` | GET | 获取图片列表 |
| `/shop/products/<pid>/images` | POST | 添加图片 |
| `/shop/products/<pid>/images/<idx>` | DELETE | 删除指定图片 |
| `/shop/products/<pid>/images/reorder` | POST | 重新排序图片 |
| `/shop/products/upload-image` | POST | 上传图片文件（返回 URL） |

### 分类管理

| 端点 | 方法 | 功能 |
|------|------|------|
| `/shop/categories` | GET | 分类列表（树形/平铺） |
| `/shop/categories` | POST | 创建分类 |
| `/shop/categories/<cid>` | PUT | 更新分类 |
| `/shop/categories/<cid>` | DELETE | 删除分类 |

---

## 购物车 Shopping Cart

所有购物车接口需要用户登录。

| 端点 | 方法 | 功能 |
|------|------|------|
| `/shop/api/cart` | GET | 获取购物车列表（含 SKU 价格、小计） |
| `/shop/api/cart/add` | POST | 加入购物车（支持 sku_id） |
| `/shop/api/cart/update` | POST | 修改数量 |
| `/shop/api/cart/remove` | POST | 移除商品 |

购物车数据存放在 `carts` 表，通过 `user_id` 关联用户，`sku_id` 关联 SKU（可选）。

---

## 订单流程 Order Flow

### 状态机

```
                    ┌─────────┐
                    │ pending │ ← 订单创建完成，待支付
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼────┐ 取消  │   申请退款
         │cancelled│    ┌──▼───┐        ┌──────────┐
         └─────────┘    │ paid │ ───→ │ refunding │
                        └──┬───┘        └────┬─────┘
                           │                  │
                     ┌─────▼──────┐     ┌─────▼──────┐
                     │  shipped   │     │  refunded  │
                     └─────┬──────┘     └────────────┘
                           │
                     ┌─────▼──────┐
                     │ completed  │
                     └────────────┘
```

### 完整流程

```
用户浏览商品 → 加入购物车
        ↓
   /shop/api/checkout（创建订单）
        ↓
   生成 order_items（status=pending）
   扣减库存，清空购物车
        ↓
   /shop/api/pay/<oid>（发起支付）
        ↓
   支付宝电脑网站支付 / 微信 Native 支付
        ↓
   支付回调 /shop/api/pay/notify（支付宝异步通知）
               /shop/api/pay/wechat-notify（微信异步通知）
        ↓
   confirm_shop_order() 更新 status=paid
   创建 user_purchases 记录
        ↓
   ┌─ 如果 product_type == 'cloud_service'
   │  → 异步触发云服务开通流程
   │  → Provider 创建资源（Docker 容器等）
   │  → 更新 cloud_instances 状态
   │
   └─ 管理员发货（tracking_company + tracking_number）
        ↓
   用户确认收货 → status=completed
```

### 用户端订单 API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/shop/api/checkout` | POST | 创建订单（支持购物车结算 / 直接购买 / 优惠券） |
| `/shop/api/orders` | GET | 我的订单列表 |
| `/shop/api/orders/<oid>/cancel` | POST | 取消订单（仅 pending） |
| `/shop/api/orders/<oid>/delete` | POST | 删除订单（软删） |
| `/shop/api/orders/<oid>/confirm-receipt` | POST | 确认收货 |
| `/shop/api/orders/<oid>/request-refund` | POST | 申请退款 |
| `/shop/api/orders/<oid>/track-user` | GET | 查询物流轨迹 |

### 管理端订单 API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/shop/orders` | GET | 订单列表（含用户/商品关联） |
| `/shop/orders/<oid>/detail` | GET | 订单详情（含支付事件、物流） |
| `/shop/orders/<oid>/confirm` | POST | 确认支付（自动触发云服务开通） |
| `/shop/orders/<oid>/ship` | POST | 订单发货（录入物流信息） |
| `/shop/orders/<oid>/complete` | POST | 标记已完成 |
| `/shop/orders/<oid>/refund` | POST | 退款（恢复库存+撤销购买记录） |

---

## 支付网关 Payment Gateway

### 支付宝 Alipay

文件：`auth-center/services/payment_service.py`

- 方法：`alipay.trade.page.pay`（电脑网站支付）
- 支付参数生成 → 前端跳转支付宝收银台
- 异步通知：`/shop/api/pay/notify`（POST form）
- 验签：支付宝公钥 RSA2 签名验证
- 桩模式：未配置时自动启用，`/shop/api/pay/<oid>/stub-confirm` 模拟支付

### 微信支付 WeChat Pay

文件：`auth-center/routes/subscription/gateway/wechat.py`

- 方法：Native 扫码支付（`call_native_pay`）
- 异步通知：`/shop/api/pay/wechat-notify`（POST JSON）
- 验签：微信平台证书 + `_verify_wechat_sign`

### 配置优先级

1. `system_config` 表（`alipay_app_id` / `alipay_private_key` / `alipay_public_key`）
2. 环境变量（`ALIPAY_APP_ID` / `NOTIFY_BASE` / `WECHAT_*`）
3. 桩模式（stub，开发测试用）

---

## 云服务商品 Cloud Service Product Type

当 `products.product_type = 'cloud_service'` 时，订单支付后将自动触发云服务开通（已移除）。

架构：

```
订单支付确认（confirm_order）
        │
        ▼
（已移除）
        │
   ┌────┼────┐
   │    │    │
   ▼    ▼    ▼
验证  创建   轮询
配置  资源   状态
        │
        ▼
   更新 cloud_instances
   返回连接信息（IP/端口/密码）
```

- **Provider 抽象**：已移至独立插件（已移除）
- **TemplateProvider**（当前默认）：在宿主机创建 Docker 容器
- **预留**：阿里云 / 腾讯云 / 百度云 Provider 适配器
- **数据表**：`cloud_instances` 存储实例状态（pending / provisioning / running / stopped / terminated / failed）

---

## 优惠券系统 Coupons

支持多种优惠类型：

| 类型 | 说明 |
|------|------|
| `fixed` | 固定金额减免 |
| `percent` | 百分比折扣 |
| `free_shipping` | 免运费 |
| `threshold` | 满减（coupon_category=threshold） |
| `new_user` | 新用户专享（coupon_category=new_user） |

校验逻辑涵盖：有效期、使用次数限制、最低消费、适用商品白名单、每人限用次数。使用记录存放于 `coupon_redemptions` 表。

---

## 订阅系统集成 Integration with Subscription

商城系统与订阅系统（`subscription_plans` / `subscription_orders`）共享支付网关但保持数据隔离：

- **商城订单**：`order_items` 表，`SP` 开头订单号
- **订阅订单**：`subscription_orders` 表，独立流水号
- **购买记录**：`user_purchases` 表记录用户对商品的购买状态
- **支付网关复用**：支付宝 / 微信支付的异步通知统一由 `payment_service.py` 的 `confirm_shop_order()` 处理

---

## AI 集成 AI Integration

商品模块通过 `agent_matrix` 的 **Shop Agent**（`shop` 域智能体）提供 AI 能力：

- AI 商品标题优化（`ai_config.title_prompt`）
- AI 商品描述生成
- AI 规格推荐
- 阿里巴巴 1688 商品导入时的 AI 重写（`ali_api/services/ai_processor.py`）

---

## 前端页面 Frontend Shop Pages

| 路由 | 模板 | 功能 |
|------|------|------|
| `/shop` | `shop.html` | 商品列表页 |
| `/shop/<pid>` | `shop_detail.html` | 商品详情页（含 SKU 选择器） |
| `/shop/preview/<pid>` | `shop_detail.html` | 管理员预览 |
| `/shop/cart` | `cart.html` | 购物车页 |
| `/shop/ucenter` | — | 用户中心（订单列表+支付跳转回） |
| `/shop/cloud` | `cloud_instances.html` | 云服务实例管理页 |

---

## 文件索引 File Index

| 文件 | 用途 |
|------|------|
| `auth-center/routes/shop_admin.py` | 管理端商品/订单/SKU/分类 API |
| `auth-center/routes/shop_public.py` | 前端商品/购物车/订单/支付 API |
| `auth-center/services/payment_service.py` | 支付宝支付创建 + 订单确认 |
| `auth-center/models/database.py` | 所有表定义 + 数据迁移 |
| `analytics/processor.py` | 60 秒聚合处理器 |
| `platform/templates/shop.html` | 商城列表页模板 |
| `platform/templates/shop_detail.html` | 商品详情页模板 |
| `platform/templates/cart.html` | 购物车页模板 |
| `platform/templates/cloud_instances.html` | 云服务管理页模板 |
| `plugins/logistics/services.py` | 快递鸟物流查询服务（已解耦为插件） |
| `auth-center/routes/subscription/gateway/alipay.py` | 支付宝底层签名/验签 |
| `auth-center/routes/subscription/gateway/wechat.py` | 微信支付底层 API |
| `agent_matrix/engine.py` | AI 引擎（Shop Agent 调用） |
| `ali_api/services/ai_processor.py` | 阿里巴巴商品 AI 处理 |
