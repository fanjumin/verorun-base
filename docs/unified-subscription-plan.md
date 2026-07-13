# 全站统一订阅管理 — 重构方案与实施计划

> Version: v1.0 | Date: 2026-07-13  
> System: VeroRun / easykai.cn  
> 前提：基于现有 24 个插件、3 档套餐、双轨订阅体系的完整摸底

---

## 目录

1. [现状诊断](#1-现状诊断)
2. [业务模型设计](#2-业务模型设计)
3. [数据结构重构](#3-数据结构重构)
4. [插件标准升级](#4-插件标准升级)
5. [实施阶段](#5-实施阶段)
6. [文件改动清单](#6-文件改动清单)

---

## 1. 现状诊断

### 1.1 双层订阅体系（互不相通）

```
┌── 主站订阅层 ─────────────────────────────┐
│ subscription_plans + subscriptions         │
│ 用途：平台建站套餐（deploy_basic/pro/ent）│
│ 粒度：用户级，一个用户一份订阅             │
│ 计费：月/年，支持支付宝/微信/Stripe/PayPal │
│ 定价：hardcoded 在 INSERT 语句中           │
└────────────────────────────────────────────┘
                    ‖ (无关联)
┌── 插件商店层 ────────────────────────────┐
│ plugin_manager/subscription.py             │
│ 用途：插件独立订阅                         │
│ 粒度：plugin 级别                          │
│ 计费：Mock（未对接真实支付）               │
│ 定价：plugin.json.price_type/price          │
└────────────────────────────────────────────┘
```

| 问题 | 严重度 |
|------|--------|
| 两套 DB 表互不关联，用户订阅状态无法统一查询 | 高 |
| 插件订阅走 Mock 支付，未对接真实网关 | 高 |
| 套餐 features_json 是静态字符串列表，无法做动态权限检查 | 高 |
| 小程序生成无任何订阅/权限控制（免费开放） | 高 |
| feed（AI 对话/内容生成/矩阵）无用量计费 | 中 |
| 插件没有统一的"功能开关"机制（只能通过 enabled 整体关闭） | 中 |

### 1.2 插件能力声明的缺失

24 个插件中仅 `site_domains` 声明了 `price_type: "free"`。其余 23 个：
- 无 `features` 字段
- 无 `price_type`/`price` 字段
- 无 `tier_required` 或 `subscription` 元数据
- 能力全靠 `hooks.provides` + `permissions` 字符串隐式表达

### 1.3 当前套餐结构

| 套餐 | plan_key | 月价 | 特点 |
|------|----------|------|------|
| 基础版 | `deploy_basic` | ¥199 | AI 基础建站 |
| 专业版 | `deploy_pro` | ¥399 | + 电商 + 1688 + RAG |
| 企业版 | `deploy_enterprise` | ¥699 | + Agent 矩阵 + 社媒 + 巡检 |

三档都写了 `"小程序增值入口(定制费另计)"` — 即小程序在此体系里是「预告但未实现」的状态。

---

## 2. 业务模型设计

### 2.1 核心理念：以 Feature 为计费单位，取代以套餐为计费单位

```
旧模型：
  用户 → 买一个套餐 → 获得一捆固定功能

新模型（Feature-based Subscription）：
  用户 → 订阅若干 Feature → 按 Feature 检查权限
  套餐 = 预打包的 Feature 集合（降价）
  单 Feature = 独立购买（Add-on）
```

### 2.2 Feature 分类体系

```
feature_catalog
├── AI 底座
│   ├── ai_chat         AI 智能对话
│   ├── ai_rag          知识库 RAG 检索
│   ├── ai_tokens       大模型 Token 用量（按量计费）
│   └── ai_image        AI 图片生成
├── CMS / 建站
│   ├── site_builder    AI 智能建站
│   ├── cms_basic       基础内容管理
│   ├── cms_seo         SEO 优化（sitemap/TDK）
│   └── media_library   媒体库
├── 电商
│   ├── shop_basic      商品/分类/订单
│   ├── shop_1688       1688 供应链采集
│   └── shop_coupon     智能优惠券引擎
├── Agent 矩阵
│   ├── agent_matrix    Agent 协作矩阵
│   └── agent_chatbot   AI Advisor 客服
├── 社媒 / 自动化
│   ├── social_push     社媒推送（微博/微信/头条）
│   ├── content_factory AI 内容工厂
│   └── automation      自动定时任务
├── 小程序生成（每频道独立）
│   ├── miniapp_douyin  抖音小程序
│   ├── miniapp_wechat  微信小程序
│   ├── miniapp_telegram Telegram 小程序
│   └── miniapp_line    LINE 小程序
├── 企业功能
│   ├── enterprise_verify 企业认证
│   ├── oauth_config    OAuth 登录配置
│   └── site_domains    自定义域名
└── 运维 / 合规
    ├── analytics       数据分析
    ├── health_check    健康巡检
    ├── sms_service     短信服务
    ├── email_service   邮件服务
    ├── captcha         验证码
    └── logistics       物流查询
```

### 2.3 套餐重新定义（Feature 包）

| 套餐 | 月价(分) | 包含 Features |
|------|----------|---------------|
| `free` (新) | 0 | `ai_chat`(限频), `captcha` |
| `basic` | 19900 | `site_builder`, `cms_basic`, `cms_seo`, `ai_chat`, `media_library` |
| `pro` | 39900 | basic 全部 + `shop_basic`, `shop_1688`, `shop_coupon`, `ai_rag`, `content_factory`, `miniapp_*`(1 个免费) |
| `enterprise` | 69900 | pro 全部 + `agent_matrix`, `agent_chatbot`, `social_push`, `enterprise_verify`, `oauth_config`, `automation`, `miniapp_*`(2 个免费), `sms_service`, `analytics` |
| Add-on | 单买 | 任意单个 Feature（如 `miniapp_telegram` ¥199/月, `ai_image` ¥99/月） |

### 2.4 小程序频道定价示例

| 频道 | feature_id | 月价(分) | 说明 |
|------|------------|----------|------|
| 抖音/Toutiao | `miniapp_douyin` | 9900 | 原生小程序 |
| 微信 | `miniapp_wechat` | 9900 | 原生小程序 |
| Telegram | `miniapp_telegram` | 19900 | WebView + Bot API |
| LINE | `miniapp_line` | 19900 | LIFF + Messaging API |

---

## 3. 数据结构重构

### 3.1 新增表

```sql
-- 能力目录（系统定义，不是用户数据）
CREATE TABLE feature_catalog (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id    TEXT UNIQUE NOT NULL,       -- 'miniapp_telegram', 'ai_rag'...
    category      TEXT NOT NULL,             -- 'miniapp' / 'ai' / 'cms' / 'shop' / ...
    name          TEXT NOT NULL,             -- 显示名
    description   TEXT DEFAULT '',           -- 简介
    price_month   INTEGER DEFAULT 0,         -- Add-on 月价(分), 0=不可单独购买
    is_addon      INTEGER DEFAULT 1,         -- 1=可单独订阅, 0=仅套餐内
    sort_order    INTEGER DEFAULT 0,
    is_active     INTEGER DEFAULT 1
);

-- 套餐包含的 Feature（取代旧 features_json 硬编码）
CREATE TABLE plan_features (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_key      TEXT NOT NULL,             -- 'basic' / 'pro' / 'enterprise' / 'free'
    feature_id    TEXT NOT NULL,             -- FK → feature_catalog.feature_id
    UNIQUE(plan_key, feature_id)
);

-- 用户 Feature 订阅（Add-on 逐条记录；套餐的 Features 通过 subscriptions.plan_key 推导）
CREATE TABLE user_feature_subs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    feature_id    TEXT NOT NULL,             -- FK → feature_catalog.feature_id
    status        TEXT DEFAULT 'active',     -- active / expired / cancelled
    source        TEXT DEFAULT 'addon',      -- 'package' (来自套餐) / 'addon' (单独购买)
    period_start  TEXT NOT NULL,
    period_end    TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, feature_id)
);

CREATE INDEX idx_ufs_user   ON user_feature_subs(user_id);
CREATE INDEX idx_ufs_status ON user_feature_subs(status);
```

### 3.2 改现有表

```sql
-- subscriptions 表新增（不删不改旧列，向下兼容）：
ALTER TABLE subscriptions ADD COLUMN extra_features_json TEXT DEFAULT '[]';
-- extra_features_json 存用户额外购买的 Add-on feature_id 列表（如 ["miniapp_telegram"]）

-- subscription_plans 表 features_json 字段保留，但新逻辑优先查 plan_features 表。
```

### 3.3 废弃的表（保留数据，代码不再依赖）

- `plugin_manager/subscription.py` 管理的插件订阅表 → 合入 `user_feature_subs`
- `app_authorizations` 的 tier 字段 → 由 `get_active_features(user_id)` 替代

---

## 4. 插件标准升级

### 4.1 plugin.json 新增字段

```json
{
    "name": "Social Push",
    "identifier": "social_push",
    "version": "0.2.0",
    "enabled": true,
    "permissions": ["social_push.read", "social_push.write"],
    "features": [
        {
            "feature_id": "social_push",
            "name": "Social Push",
            "description": "Auto-publish content to social media platforms",
            "price_month": 0,
            "is_addon": false,
            "tier_required": "enterprise"
        }
    ],
    "menu": { "group": "Automation", "key": "social", "icon": "social_media", "label": "Social Push" }
}
```

### 4.2 规则

| 字段 | 必填 | 说明 |
|------|------|------|
| `features` | **是**（新标准） | 数组，声明该插件提供的可计费能力 |
| `features[].feature_id` | 是 | 全局唯一，与 `feature_catalog` 对应 |
| `features[].price_month` | 是 | Add-on 月价(分)，0=不单独出售 |
| `features[].tier_required` | 否 | 最低套餐要求(`free`/`basic`/`pro`/`enterprise`) |
| `features[].is_addon` | 否 | 默认为 true |

- 插件 `enabled=false` 时其 features 自动不可用
- 安装/更新插件时自动 upsert `feature_catalog`

---

## 5. 实施阶段

### Phase 1：统一 Feature 目录 + 权限门（3-4 天）

| # | 任务 | 涉及文件 |
|---|------|---------|
| 1.1 | 新增 `feature_catalog` + `plan_features` + `user_feature_subs` 表，seed 全部 feature（按本文 2.2 分类） | [database.py](file:///f:/Sites/VeroRun/auth-center/models/database.py) |
| 1.2 | 写统一权限检查器 `has_feature(user_id, feature_id)` — 查套餐内 feature + addon 订阅 | 新建 `services/feature_gate.py` |
| 1.3 | Flask 装饰器 `@require_feature('miniapp_telegram')` | `services/feature_gate.py` |
| 1.4 | `/mini-app/generate` 加装饰器（每个频道独立校验） | [routes.py](file:///f:/Sites/VeroRun/site_builder/routes.py) |
| 1.5 | Admin API：feature 管理（增删改查 feature_catalog、plan_features 绑定） | [admin.py](file:///f:/Sites/VeroRun/auth-center/routes/admin.py) |
| 1.6 | 现有套餐三档 → 拆入 `plan_features` 表 | 数据迁移脚本 |

### Phase 2：插件标准适配 + UI 改造（3-5 天）

| # | 任务 | 涉及文件 |
|---|------|---------|
| 2.1 | 24 个插件 `plugin.json` 补充 `features` 字段（逐一定价/分级） | `plugins/*/plugin.json` |
| 2.2 | 插件管理器读取 `features` 并在加载时同步 `feature_catalog` | [manager.py](file:///f:/Sites/VeroRun/plugin_manager/manager.py) |
| 2.3 | Admin "插件管理" 页展示每个插件的 Feature / 订阅状态 / 价格 | [plugins_admin.html](file:///f:/Sites/VeroRun/admin/templates/partials/plugins_admin.html) |
| 2.4 | 口令控制台 AI Site Builder 面板底部嵌入小程序生成区块（展示频道订阅状态） | [ai_chat.html](file:///f:/Sites/VeroRun/admin/templates/partials/ai_chat.html) |

### Phase 3：Add-on 购买 + 订单/支付对接（3-5 天）

| # | 任务 | 涉及文件 |
|---|------|---------|
| 3.1 | Add-on 购买 API (`POST /subscription/addon/<feature_id>`) — 走现有支付网关 | [subscription/__init__.py](file:///f:/Sites/VeroRun/auth-center/routes/subscription/__init__.py) |
| 3.2 | 订单表扩展（`order_type`: `package`/`addon`） | [database.py](file:///f:/Sites/VeroRun/auth-center/models/database.py) |
| 3.3 | 支付成功后回调 → 写入 `user_feature_subs` | subscription webhook |
| 3.4 | 用户自助门户：查看/管理 Add-on 订阅、续费、取消 | subscription portal |
| 3.5 | 套餐升级/降级时 features 计算（addon 保留还是退订） | subscription upgrade logic |

### Phase 4：废弃旧层 + 清理（1-2 天）

| # | 任务 |
|---|------|
| 4.1 | `plugin_manager/subscription.py` 标记 deprecated，读 `user_feature_subs` |
| 4.2 | `app_authorizations.tier` 改用 `get_active_features` 逻辑 |
| 4.3 | 旧 features_json 静态解析 → 全部改用 `plan_features` 表 |
| 4.4 | 回归测试：套餐购买 → 升级 → addon → 小程序生成 → 全链路 |

---

## 6. 文件改动清单

### 6.1 新增文件

| 文件 | 用途 |
|------|------|
| `services/feature_gate.py` | `has_feature()`, `@require_feature`, `get_active_features()` |
| `auth-center/models/migrations/xxx_feature_subs.py` | Phase 1 建表迁移脚本 |

### 6.2 改动文件

| 文件 | Phase | 改动 |
|------|-------|------|
| [auth-center/models/database.py](file:///f:/Sites/VeroRun/auth-center/models/database.py) | 1 | +3 表，subscriptions 加 extra_features_json |
| [auth-center/routes/admin.py](file:///f:/Sites/VeroRun/auth-center/routes/admin.py) | 1 | feature 管理 CRUD |
| [site_builder/routes.py](file:///f:/Sites/VeroRun/site_builder/routes.py) | 1 | `/mini-app/generate` 加 `@require_feature(miniapp_<platform>)` |
| [plugins/*/plugin.json](file:///f:/Sites/VeroRun/plugins/) (24 个) | 2 | 补充 features 字段 |
| [plugin_manager/manager.py](file:///f:/Sites/VeroRun/plugin_manager/manager.py) | 2 | 加载时同步 feature_catalog |
| [admin/templates/partials/plugins_admin.html](file:///f:/Sites/VeroRun/admin/templates/partials/plugins_admin.html) | 2 | 插件详情展示 Feature/价格 |
| [admin/templates/partials/ai_chat.html](file:///f:/Sites/VeroRun/admin/templates/partials/ai_chat.html) | 2 | 小程序生成区块 |
| [auth-center/routes/subscription/__init__.py](file:///f:/Sites/VeroRun/auth-center/routes/subscription/__init__.py) | 3 | + addon 购买 API |
| [auth-center/routes/subscription/gateway/wechat.py](file:///f:/Sites/VeroRun/auth-center/routes/subscription/gateway/wechat.py) | 3 | addon 订单支持 |
| [auth-center/routes/subscription/gateway/alipay.py](file:///f:/Sites/VeroRun/auth-center/routes/subscription/gateway/alipay.py) | 3 | addon 订单支持 |
| [plugin_manager/subscription.py](file:///f:/Sites/VeroRun/plugin_manager/subscription.py) | 4 | deprecated |

---

> **执行方式**：将此文档加载到新任务中，从 Phase 1 Task 1.1 开始逐项执行。
> **注意**：Phase 1 的建表是关键路径，一旦完成，后续各 Phase 可并行推进。
