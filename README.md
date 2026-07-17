# VeroRunSystem

**Multi-Agent AI Operating System** — 多智能体驱动的 AI 内容与商业枢纽

VeroRunSystem 是一个基于 **9 个 AI Agent 协作矩阵 + 工具注册中心** 的全栈 SaaS 建站与商业管理平台，集成了多供应商 AI 引擎、商城运营、CMS 内容管理、AI 客服、自动化工作流、云服务开通、分析统计、系统健康巡检、插件化扩展等能力。

> 仓库：`https://github.com/fanjumin/VeroRunSystem`
> 当前版本：`0.3.1`（WIP）

---

## 目录

- [一、系统架构](#一系统架构)
- [二、核心模块](#二核心模块)
  - [2.1 Agent 矩阵系统](#21-agent-矩阵系统)
  - [2.2 Site Builder（LLM 一键建站）](#22-site-builder)
  - [2.3 商城模块](#23-商城模块)
  - [2.4 CMS 内容管理](#24-cms-内容管理)
  - [2.5 数据清洗](#25-数据清洗)
  - [2.6 工作流引擎](#26-工作流引擎)
  - [2.7 认证与支付](#27-认证与支付)
  - [2.8 主题系统](#28-主题系统)
  - [2.9 健康检查](#29-健康检查)
  - [2.10 插件系统](#210-插件系统)
  - [2.11 国际化](#211-国际化)
  - [2.12 内容工厂](#212-内容工厂)
  - [2.13 其他服务](#213-其他服务)
- [三、技术栈](#三技术栈)
- [四、项目结构](#四项目结构)
- [五、快速开始](#五快速开始)
- [六、开发指南](#六开发指南)
- [七、部署](#七部署)

---

## 一、系统架构

### 服务拓扑

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Site     │    │  Platform   │    │   Admin     │
│   :8081     │    │   :8083     │    │   :8084     │
│ 主站后端    │    │ 用户控制台  │    │ 管理后台    │
│ OAuth/用户  │    │ 商城前端    │    │ Agent矩阵   │
│ 订阅        │    │ CMS展示     │    │ 插件管理    │
│ 官网页面    │    │ 登录/定价   │    │ 订阅/支付   │
│             │    │ 用户中心    │    │ 分析/健康   │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │   SQLite   │
                    │  easykai.db │
                    └─────────────┘
```

### Nginx 生产部署

| 域名 | 端口 | 服务 |
|------|------|------|
| `easykai.cn`（根路由 `/`） | `:8081` | 主站后端（Site） |
| `easykai.cn` `/admin/` | `:8084` | 管理后台（Admin） |
| `easykai.cn` `/auth/` `/subscribe` | `:8083` | 认证/订阅（Platform） |
| `easykai.cn` `/auth/oauth/` `/user/` | `:8081` | OAuth/用户（Site） |
| `platform.easykai.cn` | `:8083` | Platform 用户控制台 |
| `agent.easykai.cn` | `:8084` | Admin（Agent 矩阵入口） |

### 16 个子系统一览

| # | 子系统 | 位置 | 职责 |
|---|--------|------|------|
| 1 | **Agent 矩阵** | `agent_matrix/` | 9 Agent 协作引擎 — 任务分解/ReAct 工具循环/调度/执行/汇总 |
| 2 | **工具注册中心** | `agent_matrix/tools.py` | 3 个只读内置工具 + 白名单过滤 + function calling |
| 3 | **Site Builder** | `site_builder/` | LLM 驱动一键建站（品牌→主题→导航→页面→文档）+ 统一设计令牌 |
| 4 | **商城模块** | `auth-center/routes/shop_admin.py` + `platform/routes/shop_public.py` | 商品、SKU、订单、购物车、优惠券、AI 优化、评价、收藏、订单通知 |
| 5 | **CMS 内容管理** | `auth-center/routes/cms_admin.py` + `auth-center/models/cms.py` | 文章、页面块、分类、下载管理 |
| 6 | **工作流引擎** | `orchestrator/` | DAG 工作流编排、Cron 调度、12 种节点 |
| 7 | **数据清洗** | `auth-center/routes/cleaner_agent.py` | 原始内容 → LLM 清洗 → 知识库 |
| 8 | **Site Domains** | `plugins/site_domains/` | 子域名管理、Nginx 配置自动生成与 reload |
| 9 | **认证中心** | `auth-center/` | JWT SSO、用户、OAuth、企业认证 |
| 10 | **支付订阅** | `auth-center/routes/subscription/` | 支付宝/微信/Stripe/PayPal 4 网关 |
| 11 | **主题系统** | `themes/` | 5 个主题 + Jinja2 ChoiceLoader 模板覆盖 |
| 12 | **健康检查** | `plugins/health_check/` | 服务探活、异常诊断、AI 自动修复、定时巡检 |
| 13 | **验证码服务** | `plugins/captcha_embedded/` | 滑块拼图验证码，嵌入式蓝图 |
| 14 | **分析系统** | `plugins/analytics/` | 访客追踪、IP 地理定位、UA 解析、60s 聚合 |
| 15 | **社交分发** | `plugins/social_push/` | 微博/微信/头条/抖音 内容分发 |
| 16 | **插件系统** | `plugin_manager/` + `plugins/` | 完整生命周期管理，17 个内置插件，各自独立数据库，支持免重启启停 |

---

## 二、核心模块

### 2.1 Agent 矩阵系统（核心创新）

位置：`agent_matrix/`

**1 个 Master Agent + 8 个 Sub Agent** 的多智能体协作矩阵，支持多供应商 AI、ReAct 工具循环、并行调度、自检重试、上下文压缩、Token 审计。

#### 架构

```
用户指令
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│  Master Agent (Athena)        模型: GPT-4o                   │
│  • 理解用户意图 → 任务分解（LLM）→ 指派子 Agent              │
│  • 汇总子 Agent 结果 → 格式化报告                             │
│  • 关键词模板 Fallback（LLM 不可用时）                        │
└───────────────────────────────┬──────────────────────────────┘
                                │
                  Orchestrator  │  并行/串行调度（最多5并发）
                                │  上下文压缩（>8条→LLM摘要）
    ┌──────┬──────┬──────┬──────┼──────┬──────┬──────┐
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
 ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
 │Shop│ │CMS │ │Fina│ │User│ │Auto│ │Anal│ │Kai │ │Heal│
 │    │ │    │ │nce │ │    │ │mat │ │ytics│ │Chat│ │th  │
 ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤
 │ReAct│ │ReAct│ │ReAct│ │ReAct│ │ReAct│ │ReAct│ │对话│ │Tool│
 │回路│ │回路│ │回路│ │回路│ │回路│ │回路│ │模式│ │Reg.│
 └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
```

#### AI 供应商

| 供应商 | 用途 | 典型模型 |
|--------|------|----------|
| **DashScope**（阿里通义） | 主推理 + 图像生成 | qwen-plus, wan2.7-image |
| **DeepSeek** | 子 Agent 推理 | deepseek-chat |
| **OpenAI** | 主控 Agent | gpt-4o |
| **Volcengine**（火山引擎） | 语音克隆 + 数字人视频 | volc-voice-clone-v2, volc-avatar-v3 |
| **SiliconFlow**（硅基流动） | 备用推理 | deepseek-ai/DeepSeek-V3 |
| **OpenRouter** | 备用供应商 | 多模型 |
| **Ollama** | 本地推理 | llama3 等 |

#### 9 个 Agent 职责

| Agent | 类型 | 默认模型 | domain | 核心能力 |
|-------|------|----------|--------|----------|
| **Athena**（Master） | master | GPT-4o | orchestration | 任务分解 → 指派子 Agent → 汇总报告 → 自检质量 |
| **Shop Agent** | sub | qwen-turbo | shop | 商品 CRUD、SKU/规格、订单、优惠券、AI 优化、云服务开通、数据清洗 |
| **CMS Agent** | sub | qwen-turbo | cms | 文章撰写/排版、图像生成、评论审核、内容工厂对接 |
| **Finance Agent** | sub | qwen-turbo | finance | 套餐、订阅、订单、收入统计、扣款 |
| **User System Agent** | sub | qwen-turbo | system | 用户管理、API Key、系统配置、日志 |
| **Automation Agent** | sub | qwen-turbo | automation | Cron 任务、Workflow 编排、DAG 管理 |
| **Analytics Agent** | sub | qwen-turbo | analytics | 统计分析、数据解读、趋势报告 |
| **Kai Assistant** | sub | deepseek-chat | chatbot | 全站 FAQ、多轮对话、工单反馈、飞书通知 |
| **Health Check Agent** | sub | qwen-turbo | health_check | 服务监控、异常诊断、告警、修复建议 |

#### 工具注册中心

每个 Sub Agent 可按 `allowed_tools` 白名单获取可用工具。当前内置 **3 个只读工具**：

| 工具 | 描述 | 参数 |
|------|------|------|
| `get_system_health` | 获取系统最近一次健康巡检结果 | 无参 |
| `query_stats` | 查询站点访问统计报告（PV/UV/趋势/来源/热门页面） | `days`（整数，默认 7） |
| `search_knowledge` | 在平台知识库中检索关键词相关内容 | `keyword`（字符串） |

#### ReAct 工具循环

```
思考 → 模型返回 tool_calls → 执行工具 → 结果回灌 → 再思考 → ...
                                                                  ↓
                                                   模型返回纯文本 → 终态答复
```

- 轮次上限 5 轮，达到后强制收尾
- 工具结果截断 4000 字符，防止上下文膨胀
- 空返回自动回退到普通 `chat()` 模式
- 无工具可用 Agent 走原单轮逻辑

#### 工作流程

1. **接收**：用户通过管理面板输入指令
2. **分解**：Athena（GPT-4o）将任务分解为子任务列表（LLM 失败时走关键词模板 Fallback）
3. **调度**：Orchestrator 分配到对应 Sub Agent（ThreadPoolExecutor 最多 5 并发，300s 超时熔断）
4. **执行**：各 Sub Agent 并行执行，有工具的 Agent 进入 ReAct 循环
5. **自检**：每 Agent 输出后自我评分（0-1），置信度 < 0.7 自动重试（最多 3 次）；灰区（0.5~0.8）触发 LLM 结构化自评
6. **汇总**：Athena 收集所有结果，整合为结构化报告

#### 技术亮点

- **智能任务分解**：AI 分解（GPT-4o）优先，失败 Fallback 到关键词模板
- **自检重试**：置信度 < 0.7 自动重试；灰区触发 LLM 结构化自评
- **多供应商路由**：每个 Agent 可单独配置供应商和模型
- **Token 审计**：完整记录每次调用，支持每日汇总（`agent_token_logs` + `agent_token_daily`）
- **流式输出**：支持 SSE（Server-Sent Events）实时流式聊天
- **媒体能力**：声音克隆（火山引擎）、数字人视频生成、文生图（通义万相）

---

### 2.2 Site Builder（LLM 一键建站）

位置：`site_builder/`

| 子模块 | 位置 | 职责 |
|--------|------|------|
| **建站引擎** | `site_builder/engine.py` + `routes.py` | 解析需求 → 结构化方案 → 执行建站 DAG |
| **统一设计令牌** | `site_builder/site_settings/` | 一套令牌统一替代 brand/header/footer/themes |

建站流程：`用户需求 → AI 解析 → 品牌 → 主题 → 导航 → 页面 → 文档 → 写入令牌 + CMS 页面块`

内置行业提示词模板：科技公司、律所、餐饮、教育等。

---

### 2.3 商城模块

后台管理：`auth-center/routes/shop_admin.py` | 前端 API：`platform/routes/shop_public.py`

| 功能 | 后台管理 | 前端 API | 说明 |
|------|----------|----------|------|
| **商品管理** | CRUD + 多图上传/排序/删除 | 列表/详情/搜索/按分类筛选 | 支持 AI 优化标题/描述/卖点 |
| **SKU 管理** | 规格组 → 笛卡尔积生成 SKU | 按规格选 SKU | 自动生成 sku_code |
| **分类管理** | 无限级分类树 | 分类筛选 | 含批量排序 |
| **购物车** | — | 增/删/改/查/批量 | 有效期 30 天 |
| **订单管理** | 发货/退款/物流查询 | 下单/取消/确认收货 | 幂等性 + 限流 |
| **优惠券** | 创建/发放/核销/统计/批量 | 下单时使用 | 固定减/百分比，限定商品 |
| **支付** | — | 支付宝 RSA2 | 桩模式降级 |
| **物流** | — | 快递鸟查询 | `plugins/logistics/` |
| **AI 优化** | 标题多版本/描述重写/卖点/标签 | — | ShopAIProcessor → AIEngine |
| **商品评价** | 回复/删除/审核 | 列表/统计 | `plugins/reviews/` 5 星 + 晒图 |
| **收藏心愿单** | — | 收藏/取消/检查/数量 | `plugins/wishlist/` |
| **订单通知** | — | 自动站内信 | `plugins/order_notify/` 6 种事件 |

---

### 2.4 CMS 内容管理

模型：`auth-center/models/cms.py` | 路由：`auth-center/routes/cms_admin.py`

| 表名 | 用途 | 核心字段 |
|------|------|----------|
| `cms_blocks` | 页面块构建器 | page, section, block_type, title, content, image_url, extra_json |
| `cms_posts` | 文章 | slug, category, title, content, tags, is_published, publish_channels |
| `cms_categories` | 文章分类 | name, icon, slug, sort_order |
| `cms_settings` | 站点设置 | key, value |
| `downloads` | 下载资源 | slug, name, version, download_url, file_size, license |

页面块类型：text / hero / features / gallery / cta / contact 等，支持独立 `is_published` 控制。

---

### 2.5 数据清洗

位置：`auth-center/routes/cleaner_agent.py`

流程：`原始内容 → knowledge_queue → LLM 清洗 → 结构化 JSON → 去重检测 → knowledge_blocks`

API 端点：`/shop/cleaner/submit`、`/shop/cleaner/list`、`/shop/cleaner/run/<qid>`、`/shop/cleaner/run-all`

---

### 2.6 工作流引擎

位置：`orchestrator/`（10 个 .py 文件）

轻量级 DAG 工作流引擎，状态机：`pending → running → completed/failed/paused/timeout/cancelled`

12 种节点：`ai_agent` / `rss_fetch` / `ai_process` / `condition` / `approval` / `publish` / `notify` / `wait` / `http_request` / `script` / `sub_workflow` / `data_transform`

---

### 2.7 认证与支付

#### JWT SSO 单点登录

```
Platform (:8083) ← sso_token cookie → Admin (:8084)
       ↓                                    ↓
       └────── JWT 验证（共享 secret）──────┘
```

- Cookie 共享：`sso_token` 跨子域名（Domain=easykai.cn）
- 支持支付宝 OAuth 登录 + 企业工商认证

#### 支付系统

**商城支付**：支付宝电脑网站支付（RSA2 签名 + 桩模式降级）

**订阅支付**（4 网关）：

| 网关 | 能力 |
|------|------|
| 支付宝 | 电脑网站支付 + 周期扣款签约 + 自动扣款 |
| 微信支付 | Native 扫码支付 + 委托扣款 |
| Stripe | Checkout Session + Webhook |
| PayPal | PayPal Order + Webhook |

#### 服务层（auth-center/services/，30 个文件）

| 类别 | 核心文件 |
|------|----------|
| 认证 | `jwt_service.py`, `oauth_service.py`, `verification_service.py`, `enterprise_verify_service.py` |
| 支付 | `payment_service.py`, `alipay_service.py`, `completion_service.py`, `invoice_service.py` |
| 社交 | `wechat_service.py`, `weibo_service.py`, `toutiao_service.py`, `douyin_service.py` |
| AI | `agent_engine.py`, `ai_content_generator.py`, `avatar_service.py` |
| 通讯 | `email_client.py`, `mail_service.py`, `sms_service.py`, `notification_service.py` |
| 安全 | `crypto.py`, `password_validator.py`, `name_validator.py`, `sensitive_words.py` |
| 业务 | `license_service.py`, `brand_service.py`, `renewal_reminder.py`, `captcha_service.py` |
| 媒体 | `volcengine_client.py` |

---

### 2.8 主题系统

位置：`themes/`

| 主题 | 风格 |
|------|------|
| default | 默认现代风格 |
| light | 清爽亮色 |
| nature | 自然绿色 |
| ocean | 海洋蓝色 |
| warm | 温暖橙色 |

实现机制：Jinja2 `ChoiceLoader` 模板覆盖，优先加载激活主题的 `templates/`，回退到默认模板。

---

### 2.9 健康检查

位置：`plugins/health_check/`

```
Service Discovery → Health Checkers (HTTP/Ping/MySQL)
        ↓
Alerter (邮件/Webhook) ← AI Fixer (LLM 诊断 + 修复)
        ↓
Scheduler (APScheduler 定时巡检)
```

---

### 2.10 插件系统

位置：`plugin_manager/`（19 个 .py 文件）+ `plugins/`

#### 生命周期

```
发现 → 安装 → 启用 → 激活 → 禁用 → 卸载
```

每个插件拥有独立 SQLite 数据库，卸载时自动删除 `.db` 文件，零残留。启动期通过 `pm.mount_all_routes()` 挂载全部已安装插件路由，运行时由门卫按启用状态放行/拦截，**后台启用/禁用插件免重启**。

#### 管理 API（32 个端点）

| 路由 | 说明 |
|------|------|
| `/admin/plugins` | 列出所有插件 |
| `/admin/plugins/discover` | 扫描新插件 |
| `/admin/plugins/<id>/install` | 安装 |
| `/admin/plugins/<id>/enable` | 启用 |
| `/admin/plugins/<id>/disable` | 禁用 |
| `/admin/plugins/<id>/uninstall` | 卸载 |
| `/admin/plugins/<id>/config` | 配置读写 |
| `/admin/plugins/hooks/*` | 钩子管理 |
| `/admin/plugins/store/*` | 插件商店 |
| `/admin/plugins/license/*` | License 管理 |
| `/admin/plugins/payment/*` | 支付管理 |

#### 事件系统

EventBus 定义了 46 个预定义事件：应用生命周期、用户、订单、订阅、CMS 内容、调度器、健康检查、插件生命周期。

#### 内置插件（17 个）

| 插件 | 独立库 | 核心能力 |
|------|--------|----------|
| 1688 供应链采集 | ali_api.db（7 表） | 商品搜索、评论、按图搜索、店铺全量采集 + AI 优化 |
| 广告管理 | ads.db | 全站广告位创建、编辑、管理 |
| 内容工厂 | content_factory.db | 多源采集、AI 加工、审核发布、Skill 推送 |
| 企业认证 | enterprise_verify.db | OCR 营业执照识别 + AI 自动审核 |
| 商品评价 | reviews.db | 5 星评分 + 晒图 + 匿名 + 回复 |
| 收藏心愿单 | wishlist.db | 收藏/取消/检查/列表/数量统计 |
| 订单通知 | 无持久化 | 6 种事件自动站内信通知 |
| 智能优惠券 | coupons.db（2 表） | 场景券 + AI 推荐 + 订阅联动 |
| AI 工具 | ai_tools.db | PPT 生成、图像生成 |
| 分析看板 | analytics.db | 无 Cookie 分析中间件 + 仪表盘 |
| 验证码 | — | 滑块拼图验证码（嵌入式） |
| 健康检查 | health.db | 系统健康巡检/告警/趋势分析 |
| 社交分发 | 主库 | 微博/微信/头条/抖音 内容分发 |
| IM 网关 | im_gateway.db | 飞书/企微/钉钉/QQ 多适配器 |
| OAuth 登录配置 | 主库 | 第三方 OAuth 登录配置管理 |
| Site Domains | 主库 | 子域名管理 + Nginx 配置自动生成/reload |
| 邮件服务 | email.db | 邮件发送配置与收发记录管理 |

---

### 2.11 国际化（i18n）

位置：`i18n/`

- 存储方式：DB `i18n_strings` 表 + YAML 文件双存储
- 查找链：DB → YAML → 原文（三阶降级）
- 语言包：`zh-CN.yml` / `en.yml`
- 性能：`get_all_translations()` 使用 LRU 内存缓存
- 插件隔离：插件使用 `self.t()`，不与系统 `_()` 冲突

---

### 2.12 内容工厂

位置：`plugins/content_factory/`

```
RSS/API 采集 → AI 加工（DashScope）→ Skill 推送
```

---

### 2.13 其他服务

#### 验证码

嵌入式插件 `plugins/captcha_embedded/`，滑块拼图验证码生成/验证/行为分析/消耗限流。原独立服务 `captcha-service:8090` 已废弃。

#### 分析系统

中间件自动记录访问日志（路径、IP、UA、耗时），每 60 秒聚合一次原始日志。GeoIP 定位 + 管理后台仪表盘。

#### 社交分发

| 平台 | 能力 |
|------|------|
| 微博 | 内容发布 |
| 微信公众号 | 图文推送 |
| 今日头条 | 内容发布 |
| 抖音 | 视频发布 + AI 配图/文案 |

---

## 三、技术栈

### 后端

| 技术 | 用途 |
|------|------|
| **Python 3** | 主要开发语言 |
| **Flask** | Web 框架 |
| **SQLite** | 数据库（主库 + 各插件独立 .db） |
| **Jinja2** | 模板引擎（ChoiceLoader 主题覆盖） |
| **JWT** | SSO 单点登录 |
| **APScheduler** | 定时任务 |
| **Gunicorn** | 生产 WSGI 服务器 |
| **cryptography** | RSA2 签名（支付宝） |
| **Paramiko** | SSH 自动化部署 |

### AI 能力

| 能力 | 供应商/模型 |
|------|------------|
| 主控推理 | OpenAI GPT-4o |
| 子 Agent 推理 | DashScope qwen-turbo / DeepSeek Chat |
| Function Calling | AIEngine.chat_with_tools() + Tool Registry |
| ReAct 工具循环 | AgentRunner._run_react_loop()（最多 5 轮） |
| 图像生成 | 通义万相 wan2.7-image |
| 声音克隆 | 火山引擎 volc-voice-clone-v2 |
| 数字人视频 | 火山引擎 volc-avatar-v3 |
| 备用推理 | SiliconFlow / OpenRouter / Ollama |

### 第三方集成

| 服务 | 用途 |
|------|------|
| 支付宝 | 商城支付 + 订阅周期扣款 |
| 微信支付 | 订阅扫码支付 + 委托扣款 |
| Stripe | 订阅支付（国际） |
| PayPal | 订阅支付（国际） |
| 快递鸟 | 物流查询 |
| 微博/微信/头条/抖音 | 社交内容分发 |
| 火山引擎 | 语音合成 / 数字人视频 |
| 飞书 | 机器人通知 |

### 前端

| 技术 | 用途 |
|------|------|
| Vanilla JS | SPA 前端 |
| Unpkg / CDN | 第三方库 |
| CSS Custom Properties | 主题系统变量 |
| AdminLTE | 管理面板 UI |
| DiceBear | 头像生成 |

---

## 四、项目结构

```
VeroRunSystem/
├── site/                      # 主站后端（Flask, :8081）
│   ├── app.py                 # 入口：auth/cms/shop/site 蓝图注册
│   └── templates/             # 站点模板
│
├── admin/                     # 管理后台（Flask, :8084）
│   ├── app.py                 # 入口：17+ 蓝图 + PluginManager + AgentMatrix
│   ├── routes/                # 管理路由
│   ├── templates/             # 管理模板
│   └── static/                # 静态资源
│
├── platform/                  # 用户控制台（Flask, :8083）
│   ├── app.py                 # 入口：auth/cms/shop/API 注册
│   ├── routes/
│   │   ├── shop_public.py     # 商城前端 API
│   │   ├── api_v1.py          # 通用 API
│   │   └── site_routes.py     # 页面路由
│   ├── templates/             # 前端模板
│   └── static/                # 静态资源
│
├── captcha-service/           # 验证码核心算法库（供 captcha_embedded 插件引用）
│
├── auth-center/               # 认证中心 + 业务核心
│   ├── auth_blueprint.py      # 蓝图注册中心
│   ├── models/                # 数据模型
│   │   ├── database.py        # 数据库连接 + 全部建表 + 种子数据
│   │   └── cms.py             # CMS 模型
│   ├── routes/                # 18 个路由模块
│   │   ├── shop_admin.py      # 商城管理（含 ShopAIProcessor）
│   │   ├── cleaner_agent.py   # 数据清洗
│   │   ├── cms_admin.py       # CMS 管理
│   │   ├── agents.py          # Agent 管理
│   │   ├── auth.py            # 登录/注册/OAuth
│   │   ├── user.py            # 用户管理
│   │   ├── comments.py        # 评论管理
│   │   ├── sessions.py        # 会话管理
│   │   ├── social_media.py    # 社交媒体管理
│   │   ├── theme_admin.py     # 主题管理
│   │   ├── header_admin.py    # 头部导航管理
│   │   ├── footer_admin.py    # 页脚管理
│   │   ├── deployment_api.py  # 部署 API
│   │   ├── douyin_miniprogram.py # 抖音小程序
│   │   └── subscription/      # 订阅模块（4 支付网关）
│   └── services/              # 30 个服务模块
│
├── agent_matrix/              # Agent 矩阵系统
│   ├── engine.py              # AIEngine（7 供应商 + function calling）
│   ├── tools.py               # 工具注册中心（3 只读工具 + 白名单）
│   ├── orchestrator.py        # 任务编排 + 关键词路由 + 上下文压缩
│   ├── agent_runner.py        # Agent 执行器 + ReAct 循环 + 自检重试
│   ├── routes.py              # API 路由（29+ 端点）
│   ├── models.py              # 数据模型 + 9 Agent 种子数据 + 6 张表
│   └── prompts/               # 10 个 Agent Prompt 文件
│
├── site_builder/              # LLM 驱动一键建站
│   ├── engine.py              # 建站引擎
│   ├── routes.py              # 建站任务 API
│   ├── models.py              # 建站任务模型
│   ├── generators/            # 分步生成器
│   ├── prompts/               # 行业提示词模板
│   └── site_settings/         # 统一设计令牌系统
│
├── orchestrator/              # DAG 工作流引擎（10 个 .py）
│   ├── workflow_engine.py     # 引擎核心
│   ├── nodes.py               # 12 种节点定义
│   ├── scheduler.py           # Cron 调度
│   ├── worker.py              # Worker 池
│   ├── safe_eval.py           # 安全沙箱
│   ├── routes.py              # API 路由
│   └── models.py              # 数据模型
│
├── plugin_manager/            # 插件管理引擎（19 个 .py）
│   ├── manager.py             # 核心：生命周期管理
│   ├── base.py                # BasePlugin 抽象基类
│   ├── discovery.py           # 文件系统扫描
│   ├── routes.py              # 32 个管理 API 端点
│   ├── event_bus.py           # EventBus（46 个事件）
│   ├── hooks.py               # Hook 系统（Action + Filter）
│   ├── deps.py                # 依赖解析器（拓扑排序）
│   ├── config_validator.py    # JSON Schema 配置校验
│   ├── store.py               # 插件商店 API
│   ├── license.py             # 许可管理
│   └── payment.py             # 支付网关
│
├── plugins/                   # 17 个内置插件（各自独立数据库）
│   ├── ali_api/               # 1688 供应链采集
│   ├── ads/                   # 广告管理
│   ├── content_factory/       # 内容工厂
│   ├── enterprise_verify/     # 企业认证
│   ├── reviews/               # 商品评价
│   ├── wishlist/              # 收藏心愿单
│   ├── order_notify/          # 订单通知
│   ├── coupons/               # 智能优惠券
│   ├── ai_tools/              # AI 工具
│   ├── analytics/             # 分析看板
│   ├── captcha_embedded/      # 验证码
│   ├── health_check/          # 健康检查
│   ├── social_push/           # 社交分发
│   ├── im_gateway/            # IM 网关
│   ├── oauth_config/          # OAuth 配置
│   ├── site_domains/          # 子域名管理
│   └── email/                 # 邮件服务
│
├── health_check/              # 健康检查模块
├── analytics/                 # 分析系统
├── themes/                    # 5 个主题
├── i18n/                      # 国际化翻译
├── prompts/                   # 全局 Prompt 模板
├── docs/                      # 项目文档
├── templates/                 # 全局模板
├── static/                    # 全局静态资源
├── images/                    # 图像资源
├── node_modules/              # 前端依赖
├── sdks/                      # SDK 目录
├── backups/                   # 备份目录
├── deploy/                    # 部署配置
├── nginx-domains/             # Nginx 站点配置
├── scripts/                   # 运维脚本
├── tools/                     # 工具目录
├── GeoLite2-City/             # GeoIP 数据库
├── data/                      # 数据目录
├── docker-compose.yml         # Docker Compose
├── Dockerfile                 # Docker 镜像
├── requirements.txt           # Python 依赖
├── package.json               # Node.js 依赖
├── VERSION                    # 版本号
├── version.py                 # 版本读取模块
├── README.md                  # 本文件
├── AGENTS.md                  # Agent 开发铁律
├── CHANGELOG.md               # 修改记录
├── REGRESSIONS.md             # 性能回归记录
├── QUICK_START.md             # 快速开始
├── LICENSE                    # 许可证
└── .env.intl                  # 国际化环境配置
```

---

## 五、快速开始

### 环境要求

- Python 3.9+
- pip
- SQLite（内置）
- OpenAI / DeepSeek API Key（Agent 矩阵功能需要）

### 安装

```bash
# 克隆项目
git clone https://github.com/fanjumin/VeroRunSystem.git
cd VeroRunSystem

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 .\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 启动全部服务

```bash
# ① 站点后端（端口 8081）
cd site && python app.py 8081 &

# ② 用户控制台（端口 8083）
cd ../platform && python app.py 8083 &

# ③ 管理后台（端口 8084）
cd ../admin && python app.py 8084 &
```

### 访问

| 服务 | 地址 | 用途 |
|------|------|------|
| 官网 | `http://localhost:8081` | 主站页面 / 登录 / 订阅 |
| 用户控制台 | `http://localhost:8083` | 商城 / CMS / 用户中心 |
| 管理后台 | `http://localhost:8084/admin` | Agent 矩阵 / 商品管理 / 系统设置 / 插件管理 |

---

## 六、开发指南

### 新增一个 Sub Agent

1. 创建 Prompt 文件：`agent_matrix/prompts/sub_<name>_prompt.md`
2. 在 `agent_matrix/models.py` 的 `DEFAULT_AGENTS` 中添加种子数据
3. 在 `orchestrator.py` 的 `_template_decompose()` 中添加关键词路由
4. 在管理后台配置 Agent 的供应商/模型
5. 如需 ReAct 工具能力，在 `allowed_tools` 中声明白名单

### 新增一个工具

1. 在 `agent_matrix/tools.py` 的 `TOOL_SCHEMAS` 中添加 schema
2. 在 `TOOL_EXECUTORS` 中绑定执行函数
3. 在管理后台将 Agent 的 `allowed_tools` 加上新工具名称

### 新增一个插件

1. 创建 `plugins/<name>/__init__.py`（继承 `BasePlugin`）
2. 创建 `plugins/<name>/plugin.json`（含 `permissions` 声明）
3. 添加翻译：`plugins/<name>/i18n/{locale}.yml`
4. 添加路由：`plugins/<name>/routes/`（自动挂载到 `/plugin/<name>/`）
5. 在 `on_install()` 中调用 `init_db()` 创建插件自有数据库
6. 通过 `event_bus.on(EventName.XXX, self.handler)` 订阅事件

### 新增主题

1. 创建目录：`themes/<slug>/`
2. 添加模板覆盖：`themes/<slug>/templates/`
3. 添加 CSS：`themes/<slug>/theme.css`
4. 在管理后台选择激活

### 代码规范

- Python：PEP8
- 路由：Flask Blueprint，前缀明确
- 数据库：主库统一在 `models/database.py` 管理；插件使用自有 `.db` 文件
- 翻译：统一使用 `_()`，插件使用 `self.t()`
- 插件隔离：每个插件拥有独立 SQLite 数据库，卸载时自动删除 `.db` 文件

---

## 七、部署

### 部署架构

```
Nginx（反向代理 + SSL）  服务器: ***REMOVED***
    │
    ├── easykai.cn（/）                  ──→ Site:8081
    ├── easykai.cn /admin/               ──→ Admin:8084
    ├── easykai.cn /auth/ /subscribe     ──→ Platform:8083
    ├── easykai.cn /auth/oauth/ /user/   ──→ Site:8081
    ├── platform.easykai.cn              ──→ Platform:8083
    ├── agent.easykai.cn                 ──→ Admin:8084
    └── 子域名 *                        ──→ 端口自定（via Site Domains）

Nginx snippets: /etc/nginx/snippets/easykai-domains/*.conf（自动生成）
```

### 关键环境变量

| 变量 | 说明 |
|------|------|
| `FLASK_SECRET_KEY` | Flask 密钥 |
| `JWT_SECRET` | JWT 签名密钥 |
| `DEPLOY_DOMAIN` | 部署域名 |
| `NOTIFY_BASE` | 支付回调域名 |
| `ALIPAY_APP_ID` | 支付宝 AppID |
| `WECHAT_APP_ID` | 微信支付 AppID |
| `DASHSCOPE_API_KEY` | 阿里通义 API Key |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `OPENAI_API_KEY` | OpenAI API Key |
| `SILICONFLOW_API_KEY` | 硅基流动 API Key |
| `NGINX_SNIPPETS_DIR` | 子域名 Nginx 配置写入目录 |

### 部署同步

```bash
rsync -av --delete --exclude='.git' --exclude='__pycache__' --exclude='venv' \
  ./ easykai@server:/home/easykai/easykai-workspace/easykai.cn/
```

### Docker 部署

```bash
docker-compose up -d
```

---

> **VeroRunSystem** — Multi-Agent AI Operating System  
> 多智能体驱动的 AI 内容与商业枢纽  
> © 2026 VeroRunSystem