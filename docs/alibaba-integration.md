# 1688 / 阿里巴巴供应链对接系统

> **阿里供应链对接文档** &mdash; 1688 Product Sourcing & Automated Listing System

---

## 目录

- [1. 系统概述](#1-系统概述)
- [2. 子系统架构](#2-子系统架构)
- [3. API 客户端](#3-api-客户端)
- [4. AI 智能处理](#4-ai-智能处理)
- [5. 管理后台接口](#5-管理后台接口)
- [6. 数据库表结构](#6-数据库表结构)
- [7. 配置说明](#7-配置说明)

---

## 1. 系统概述

本模块是 **易站智能建站系统** 的 1688 供应链对接子系统，提供完整的阿里巴巴开放平台集成能力：

- **商品采集** &mdash; 通过 1688 API 获取商品详情与搜索
- **AI 加工** &mdash; 自动优化标题、重写营销文案、生成卖点标签
- **一键发布** &mdash; 将 1688 商品采集后发布到本地商城 (`products` 表)
- **风控体系** &mdash; 用户限流、并发控制、熔断保护、审计告警四层机制
- **缓存加速** &mdash; 内存缓存 + Redis 双缓存策略

集成位置：`admin` 服务 (8084 端口) &rarr; [`/admin/ali-api/*`](/admin/ali-api/)

---

## 2. 子系统架构

### 2.1 `ali_api/` &mdash; Alibaba API Client 主模块

| 路径 | 说明 |
|---|---|
| [`ali_api/__init__.py`](ali_api/__init__.py) | 模块入口，`init_ali_api(app)` 注册蓝图并初始化表 |
| [`ali_api/config.py`](ali_api/config.py) | 配置中心（system_config 表 &rarr; 环境变量 &rarr; 默认值） |
| [`ali_api/models.py`](ali_api/models.py) | 5 张数据库表的数据模型 |
| [`ali_api/routes/admin.py`](ali_api/routes/admin.py) | 管理后台 API 路由（~1567 行） |
| [`ali_api/services/alibaba_client.py`](ali_api/services/alibaba_client.py) | **v1 客户端**：HMAC-SHA1 签名，单例模式 |
| [`ali_api/services/alibaba_client_v2.py`](ali_api/services/alibaba_client_v2.py) | **v2 客户端**：OAuth 2.0 + access_token 签名 |
| [`ali_api/services/ai_processor.py`](ali_api/services/ai_processor.py) | AI 内容生成引擎（集成 agent_matrix） |
| [`ali_api/services/rate_limiter.py`](ali_api/services/rate_limiter.py) | 四层风控限流 |
| [`ali_api/services/cache_service.py`](ali_api/services/cache_service.py) | Redis + 内存双缓存 |
| [`ali_api/templates/ali_admin/index.html`](ali_api/templates/ali_admin/index.html) | 管理控制台页面 |
| [`ali_api/static/ali_console.js`](ali_api/static/ali_console.js) | 管理控制台前端交互（Bootstrap + Axios） |

### 2.2 `laodeng-publish/` &mdash; Smart Listing System

> ❌ **目录不存在。** 该子系统尚未创建。智能发布逻辑当前由 `ali_api/routes/admin.py` 中的 `publish_product()` 路由直接处理，将 1688 商品数据插入 `products` 表并附带 `ali_source` 标记。

---

## 3. API 客户端

### 3.1 v1 客户端 &mdash; HMAC-SHA1 (`alibaba_client.py`)

通过 API 网关 + AppKey/AppSecret 签名调用。

```python
from ali_api.services.alibaba_client import get_client
client = get_client()
success, data, err = client.get_product("productID")
```

**签名流程**：参数排序 &rarr; `AppSecret + key1value1... + AppSecret` &rarr; HMAC-SHA1 &rarr; Base64

**API 端点**：

| 方法 | 对应 API | 用途 |
|---|---|---|
| `get_product()` | `alibaba.product.get` | 获取商品详情 |
| `search_products()` | `alibaba.product.search` | 关键词搜索 |
| `get_category()` | `alibaba.category.get` | 类目查询 |
| `get_logistics()` | `alibaba.logistics.get` | 物流查询 |

**特性**：自动重试（指数退避）、响应解析标准化、单例复用

### 3.2 v2 客户端 &mdash; OAuth 2.0 (`alibaba_client_v2.py`)

新版 1688 开放平台，需要 access_token（OAuth 授权）。

```python
from ali_api.services.alibaba_client_v2 import get_product, call_api
result = get_product("productID", access_token="xxx")
```

**签名差异**：
- 路径格式 `param2/1/com.alibaba.product/`（非旧版 `cn.alibaba.open`）
- 参数名前缀 `_aop_signature`、`_aop_timestamp`
- 签名公式：`access_token + 排序参数串 + access_token` &rarr; HMAC-SHA1 &rarr; Base64

**OAuth 授权流程**（管理后台内置）：

| 路由 | 方法 | 说明 |
|---|---|---|
| `/admin/ali-api/oauth/url` | GET | 获取授权 URL（含 state CSRF 防护） |
| `/admin/ali-api/oauth/callback` | GET/POST | 授权码 &rarr; access_token，持久化存储 |
| `/admin/ali-api/oauth/status` | GET | 查询当前授权状态 |
| `/admin/ali-api/oauth/refresh` | POST | 自动刷新 access_token |
| `/admin/ali-api/oauth/disconnect` | POST | 解除授权 |

### 3.3 限流与风控 (`rate_limiter.py`)

四层保护机制：

1. **用户级限流** &mdash; 每日/每小时调用次数限制（默认 1000/100）
2. **全局并发控制** &mdash; 全站并发请求上限（默认 10），QPS 限制（默认 5）
3. **熔断保护** &mdash; 错误率超过阈值自动熔断（默认 50%），冷却后恢复
4. **审计告警** &mdash; 完整 `ali_api_logs` 记录

### 3.4 缓存服务 (`cache_service.py`)

| 层级 | 实现 | TTL 默认值 |
|---|---|---|
| L1 | 内存缓存 (`MemoryCache`) | 商品 1h / 分类 24h |
| L2 | Redis（可选启用） | 同内存缓存 |

---

## 4. AI 智能处理

集成 `agent_matrix.AIEngine` 模块，支持 DeepSeek / OpenAI / 本地模型。

### 核心功能 (`ai_processor.py`)

| 方法 | 用途 | 输出 |
|---|---|---|
| `optimize_title()` | 单标题优化 | 优化后标题字符串 |
| `generate_title_options()` | 多版本标题生成 | `[{id, title, style, reason}, ...]`（专业/吸引力/简洁三风格） |
| `optimize_description()` | 描述文案重写 | 优化后描述字符串 |
| `generate_marketing_copy()` | 全案生成 | `{optimized_title, optimized_description, selling_points, tags}` |
| `_generate_selling_points()` | 卖点提取 | 3&ndash;5 条核心卖点 |
| `_generate_tags()` | 标签生成 | 5&ndash;8 个商品标签 |

**配置**：`ALIBABA_AI_PROVIDER`（默认 deepseek）、`ALIBABA_AI_MODEL`（默认 deepseek-chat）

**提示词工程**：系统 prompt 定义为"电商文案优化专家"，标题限制 60 字，描述限制 500 字。

---

## 5. 管理后台接口

所有路由前缀：`/admin/ali-api/`，挂载于 Flask Blueprint `ali_admin_bp`。

### 5.1 仪表板

| 路由 | 方法 | 说明 |
|---|---|---|
| `/` | GET | 管理页面入口（渲染 HTML） |
| `/dashboard` | GET | 仪表板数据：商品统计、API 调用量、风控状态、缓存状态、AI 可用性 |

### 5.2 商品管理

| 路由 | 方法 | 说明 |
|---|---|---|
| `/items` | GET | 商品列表（分页 + 按状态筛选 + 关键词搜索） |
| `/items/<id>` | GET | 商品详情 |
| `/items/collect` | POST | 采集单个商品（优先走缓存 &rarr; 调用 v1 API） |
| `/items/search` | POST | 批量搜索商品（关键词 + 分页 + 5 分钟缓存） |

### 5.3 AI 处理

| 路由 | 方法 | 说明 |
|---|---|---|
| `/items/<id>/ai-optimize` | POST | AI 全面优化（标题 + 描述 + 卖点 + 标签） |
| `/items/<id>/ai-titles` | POST | AI 生成多版本标题选项（3 风格） |
| `/items/<id>/select-title` | POST | 选中某版本标题 |

### 5.4 发布管理

| 路由 | 方法 | 说明 |
|---|---|---|
| `/items/<id>/publish` | POST | 发布到本地商城（插入 `products` 表 + `product_skus` 表） |
| `/items/<id>/unpublish` | POST | 下架商品（`is_active = 0`） |

### 5.5 图片管理

| 路由 | 方法 | 说明 |
|---|---|---|
| `/items/<id>/images` | GET | 图片列表 |
| `/items/<id>/images/upload` | POST | 上传图片（5MB 限制，支持拖拽） |
| `/items/<id>/images/<index>` | DELETE | 删除图片 |
| `/items/<id>/images/reorder` | POST | 重新排序 |
| `/uploads/<filename>` | GET | 图片文件服务 |

### 5.6 日志与监控

| 路由 | 方法 | 说明 |
|---|---|---|
| `/logs` | GET | API 调用日志（按 endpoint/success 筛选） |
| `/cache/stats` | GET | 缓存统计 |
| `/cache/clear` | POST | 清除缓存（all / product / api） |
| `/rate-limit/stats` | GET | 风控实时数据 |
| `/config` | GET | 脱敏配置查看 |

### 5.7 v2 商品查询

| 路由 | 方法 | 说明 |
|---|---|---|
| `/v2/products/<product_id>` | GET | 新版 API 查询商品详情（需 OAuth token） |

### 安全机制

- CSRF 防护（双重提交 Cookie 模式）
- JWT SSO 管理员认证
- redirect_uri 白名单校验（防止开放重定向）
- OAuth state 持久化（防 CSRF + 防重放）
- 响应头安全加固（`X-Content-Type-Options`、`X-Frame-Options`、`X-XSS-Protection`）

---

## 6. 数据库表结构

所有表均在 `ali_api/models.py` 中定义，共用主项目 SQLite 数据库。

### 6.1 `ali_api_items` &mdash; 商品缓存表

核心字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `product_id` | TEXT UNIQUE | 1688 商品 ID |
| `title` / `original_title` | TEXT | 标题 / 原始标题 |
| `ai_title` / `ai_title_options` / `selected_title` | TEXT | AI 标题相关 |
| `ai_description` | TEXT | AI 优化描述 |
| `price` / `original_price` | DECIMAL | 价格（CNY） |
| `images` | TEXT (JSON) | 图片 URL 列表 |
| `specs` | TEXT (JSON) | 规格参数 |
| `product_sku` | TEXT (JSON) | SKU 列表 |
| `publish_status` | TEXT | draft / published / unpublished |
| `target_product_id` | INTEGER | 关联本地 `products` 表 ID |
| `api_response` | TEXT (JSON) | 原始 API 响应 |

索引：`product_id`、`status`、`category`、`user_id`、`publish_status`

### 6.2 `ali_api_logs` &mdash; API 调用日志

记录每次 API 调用的完整链路信息，用于审计和故障排查。

### 6.3 `ali_api_user_stats` &mdash; 用户调用统计

用户级日调用计数，支持每日自动重置。

### 6.4 `ali_api_tokens` &mdash; 1688 OAuth Token

存储 access_token 和 refresh_token，支持自动过期刷新。

### 6.5 `ali_oauth_states` &mdash; OAuth State

CSRF 防护 + 防重放攻击的一次性 state 存储。

---

## 7. 配置说明

优先级：**system_config 表** &rarr; **环境变量** &rarr; **代码默认值**

### 关键配置项

| system_config key | 环境变量 | 说明 |
|---|---|---|
| `alibaba_app_key` | `ALIBABA_APP_KEY` | 1688 App Key |
| `alibaba_app_secret` | `ALIBABA_APP_SECRET` | 1688 App Secret |
| `alibaba_api_gateway` | `ALIBABA_API_GATEWAY` | API 网关（默认 `https://gw.open.1688.com/openapi`） |
| `alibaba_redirect_domains` | &mdash; | OAuth 回调域名白名单（逗号分隔） |
| &mdash; | `ALIBABA_AI_PROVIDER` | AI 供应商（默认 `deepseek`） |
| &mdash; | `ALIBABA_AI_MODEL` | AI 模型（默认 `deepseek-chat`） |
| &mdash; | `ALIBABA_USER_DAILY_LIMIT` | 用户日限（默认 1000） |
| &mdash; | `REDIS_HOST` | Redis 地址（可选） |

---

> **注意事项**
>
> 1. v1 客户端使用旧版 1688 API，某些端点可能不再维护，建议优先使用 v2。
> 2. v2 客户端必须先通过 OAuth 授权获取 access_token，否则返回 401。
> 3. AI 处理依赖 `agent_matrix` 模块，请确保该模块已正确安装。
> 4. `laodeng-publish/` 智能发布子系统尚未开发，当前发布逻辑在 `admin.py` 中内联实现。
