# VeroRunSystem

**Multi-Agent AI Operating System** — 多智能体驱动的 AI 内容与商业枢纽

VeroRunSystem 是一个基于 **9 个 AI Agent 协作矩阵 + 工具注册中心** 的全栈 SaaS 建站与商业管理平台，集成了多供应商 AI 引擎、商城运营、CMS 内容管理、AI 客服、自动化工作流、云服务开通、分析统计、系统健康巡检、插件化扩展等能力。

> 仓库：`https://github.com/fanjumin/VeroRunSystem`

---

## 一、系统架构

### 服务拓扑

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Site     │    │  Platform   │    │   Admin     │    │   Captcha   │
│   :8081     │    │   :8083     │    │   :8084     │    │   :8090     │
│ 主站后端    │    │ 用户控制台  │    │ 管理后台    │    │ 验证码服务  │
│ OAuth/用户  │    │ 商城前端    │    │ Agent矩阵   │    │             │
│ 订阅        │    │ CMS展示     │    │ 插件管理    │    │             │
│ 官网页面    │    │ 登录/定价   │    │ 订阅/支付   │    │             │
│             │    │ 用户中心    │    │ 分析/健康   │    │             │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │                   │
       └───────────────────┼───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │   SQLite    │
                    │  easykai.db │
                    └─────────────┘
```

### Nginx 生产部署拓扑

| 域名 | 端口 | 服务 |
|------|------|------|
| easykai.cn / www.easykai.cn（根路由 `/`） | `:8081` | 主站后端（Site） |
| easykai.cn `/admin/` | `:8084` | 管理后台（Admin） |
| easykai.cn `/auth/` `/subscribe` | `:8083` | 认证/订阅（Platform） |
| easykai.cn `/auth/oauth/` `/user/` | `:8081` | OAuth/用户（Site） |
| platform.easykai.cn | `:8083` | Platform 用户控制台 |
| agent.easykai.cn | `:8084` | Admin（Agent 矩阵入口） |

### 15 个子系统一览

| # | 子系统 | 位置 | 职责 |
|---|--------|------|------|
| 1 | **Agent 矩阵** | `agent_matrix/` | 9 Agent 协作引擎 — 任务分解/ReAct 工具循环/调度/执行/汇总 |
| 2 | **工具注册中心** | `agent_matrix/tools.py` | 3 个只读内置工具 + 白名单过滤 + function calling |
| 3 | **商城模块** | `auth-center/routes/shop_admin.py` + `platform/routes/shop_public.py` | 商品、SKU、订单、购物车、优惠券、AI 优化、评价、收藏、订单通知 |
| 4 | **CMS 内容管理** | `auth-center/routes/cms_admin.py` + `auth-center/models/cms.py` | 文章、页面块、分类、下载管理 |
| 5 | **工作流引擎** | `orchestrator/` | DAG 工作流编排、Cron 调度、12 种节点 |
| 6 | **数据清洗** | `auth-center/routes/cleaner_agent.py` | 原始内容 → LLM 清洗 → 知识库 |
| 7 | **Site Domains** | `auth-center/routes/admin.py` + `auth-center/middleware/site_domain_middleware.py` | 子域名管理、独立服务 Nginx 配置自动生成与 reload |
| 8 | **认证中心** | `auth-center/` | JWT SSO、用户、OAuth、企业认证 |
| 9 | **支付订阅** | `auth-center/routes/subscription/` | 支付宝/微信/Stripe/PayPal 订阅支付（4 网关） |
| 10 | **主题系统** | `themes/` | 5 个主题 + Jinja2 ChoiceLoader 模板覆盖 |
| 11 | **健康检查** | `health_check/` | 服务探活、异常诊断、AI 自动修复、定时巡检 |
| 12 | **验证码服务** | `captcha-service/` | 拼图行为验证码（独立服务 8090） |
| 13 | **分析系统** | `analytics/` | 访客追踪、IP 地理定位、UA 解析、60s 聚合 |
| 14 | **社交分发** | `auth-center/routes/social_push.py` | 微博/微信/头条/抖音 内容分发 |
| 15 | **插件系统** | `plugin_manager/` + `plugins/` | PluginManager 统一管理 — 发现/安装/启用/卸载，12 个内置插件，各自独立数据库 |

---

## 二、核心模块详解

### 2.1 Agent 矩阵系统（核心创新）

位置：`agent_matrix/`

这是本系统最核心的组件 — 一个 **1 个 Master Agent + 8 个 Sub Agent 的多智能体协作矩阵**，支持多供应商 AI、ReAct 工具循环、并行调度、自检重试、上下文压缩、Token 审计。

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
 │    │ │    │ │    │ │    │ │    │ │    │ │    │ │Tool│
 │    │ │    │ │    │ │    │ │    │ │    │ │    │ │Reg.│
 └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
```

#### AI 供应商

支持 7 个 AI/媒体供应商：

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

#### 工具注册中心（Tool Registry）

每个 Sub Agent 可按 `allowed_tools` 白名单获取可用工具。当前内置 **3 个只读工具**：

| 工具 | 描述 | 参数 |
|------|------|------|
| `get_system_health` | 获取系统最近一次健康巡检结果汇总（健康分/通过/警告/错误） | 无参 |
| `query_stats` | 查询站点访问统计报告（PV/UV/趋势/来源/热门页面） | `days`（整数，默认 7） |
| `search_knowledge` | 在平台知识库中检索关键词相关内容片段 | `keyword`（字符串，必填） |

工具执行统一带 try/except 兜底，失败返回字符串错误信息，保证 ReAct 循环不会因单个工具出错而崩溃。

#### ReAct 工具循环

AIEngine 通过 `chat_with_tools()` 提供原生 function calling，AgentRunner 的 `_run_react_loop()` 实现完整的 ReAct 循环：

```
思考 → 模型返回 tool_calls → 执行工具 → 结果回灌 → 再思考 → ...
                                                                  ↓
                                                   模型返回纯文本 → 终态答复
```

特性：
- 轮次上限（默认 5 轮），达到后强制收尾
- 工具结果截断（4000 字符），防止上下文膨胀
- 空返回自动回退到普通 `chat()` 模式
- 无工具可用的 Agent 走原单轮逻辑，不影响 ReAct Agent

#### 工作流程

1. **接收**：用户通过管理面板输入指令
2. **分解**：Athena（GPT-4o）将任务分解为子任务列表（LLM 失败时走关键词模板 Fallback）
3. **调度**：Orchestrator 根据子任务 domain 分配到对应 Sub Agent（支持并行下发，ThreadPoolExecutor 最多 5 并发，300s 超时熔断）
4. **执行**：各 Sub Agent 并行执行，有工具的 Agent 进入 ReAct 循环
5. **自检**：每 Agent 输出后自我评分（0-1），低置信度（<0.7）自动重试（最多 3 次）；灰区（0.5~0.8）触发 LLM 结构化自评
6. **汇总**：Athena 收集所有结果，整合为结构化报告返回用户

#### 上下文压缩

长会话（>8 条消息）自动触发上下文压缩，对早期历史生成 LLM 摘要并替换，失败时回退保留最近 6 条。

#### 技术亮点

- **智能任务分解**：先尝试 AI 分解（GPT-4o），失败或超时则 Fallback 到关键词模板
- **自检重试**：Agent 输出附带置信度评分，`self_critique_score < 0.7` 自动重试；灰区触发 LLM 结构化自评
- **多供应商路由**：每个 Agent 可单独配置供应商和模型（`provider_model_id`）
- **Token 审计**：完整记录每次调用的 token 消耗，支持每日汇总（`agent_token_logs` + `agent_token_daily`）
- **供应商切换**：管理后台支持 50+ 模型配置，随时切换
- **流式输出**：支持 SSE（Server-Sent Events）实时流式聊天
- **媒体能力**：声音克隆（火山引擎）、数字人视频生成、文生图（通义万相）

---

### 2.2 商城模块（Shop）

后台管理：`auth-center/routes/shop_admin.py`（前缀 `/shop`）  
前端 API：`platform/routes/shop_public.py`（前缀 `/shop`）  
支付服务：`auth-center/services/payment_service.py`

#### 功能矩阵

| 功能 | 后台管理 | 前端 API | 说明 |
|------|----------|----------|------|
| **商品管理** | CRUD + 多图上传/排序/删除 | 列表/详情/搜索/按分类筛选 | 支持 AI 优化标题/描述/卖点 |
| **SKU 管理** | 规格组 → 笛卡尔积生成 SKU | 按规格选 SKU | 自动生成 sku_code |
| **分类管理** | 无限级分类树 | 分类筛选 | 树形结构，含批量排序 |
| **购物车** | — | 增/删/改/查/批量 | 有效期 30 天 |
| **订单管理** | 发货/退款/物流查询 | 下单/取消/确认收货 | 幂等性 + 限流 |
| **优惠券** | 创建/发放/核销/统计/批量发放 | 下单时使用 | 固定减/百分比减，限定商品 |
| **支付** | — | 支付宝 | RSA2 签名 + 桩模式降级 |
| **物流** | — | 快递鸟查询 | kdniao_service.py |
| **AI 优化** | 标题多版本/描述重写/卖点/标签/批量 | — | ShopAIProcessor → AIEngine |
| **商品评价**（插件） | 回复/删除/审核 | 列表/统计 | `plugins/reviews/` 5 星评分 + 晒图 + 匿名 |
| **收藏心愿单**（插件） | — | 收藏/取消/检查/数量 | `plugins/wishlist/` |
| **订单通知**（插件） | — | 自动站内信 | `plugins/order_notify/` 6 种事件通知 |

#### 支付系统

商城订单采用支付宝电脑网站支付：

```
订单创建 → 调起支付宝（GET URL 跳转）
                ↓
         用户扫码支付
                ↓
    异步通知 → verify_notify() RSA2 签名验证
                ↓
    confirm_shop_order() 更新订单状态 + 创建购买记录
```

- **安全**：RSA2 签名验证，通知域名从 DB 动态读取
- **桩模式**：未配置支付宝时自动降级，标注 `stub_auto_confirm`
- **三层降级**：DB `system_config` → 环境变量 → 桩模式

#### 订阅支付（独立于商城）

`auth-center/routes/subscription/gateway/` 支持 4 种支付网关：

| 网关 | 文件 | 能力 |
|------|------|------|
| 支付宝 | `gateway/alipay.py` | 电脑网站支付 + 周期扣款签约 + 自动扣款 |
| 微信支付 | `gateway/wechat.py` | Native 扫码支付 + 委托扣款 |
| Stripe | `gateway/stripe.py` | Checkout Session + Webhook |
| PayPal | `gateway/paypal.py` | PayPal Order + Webhook |

---

### 2.3 CMS 内容管理系统

模型定义：`auth-center/models/cms.py`  
管理路由：`auth-center/routes/cms_admin.py`

#### 数据库表

| 表名 | 用途 | 核心字段 |
|------|------|----------|
| `cms_blocks` | 页面块构建器 | page, section, block_type, title, content, image_url, link_url, position, extra_json |
| `cms_posts` | 文章 | slug, category, title, content, tags, audience, is_published, publish_channels |
| `cms_categories` | 文章分类 | name, icon, slug, audience, sort_order |
| `cms_settings` | 站点设置 | key, value |
| `downloads` | 下载资源 | slug, name, version, download_url, file_size, license |

#### 页面块系统

CMS 核心是 **Block 页面构建器** — 每页面由多个 Block 组成，支持拖拽排序。

- **类型**：text / hero / features / gallery / cta / contact 等
- **额外数据**：`extra_json` 存储任意结构化数据
- **发布控制**：每个 block 独立 `is_published`

#### 社交发布集成

文章支持一键分发：发布到 `cms_posts` 表的同时，可分发到微博、微信、今日头条、抖音等。

---

### 2.4 数据清洗（Cleaner Agent）

位置：`auth-center/routes/cleaner_agent.py`（蓝图前缀 `/shop/cleaner`）

Data Cleaner Agent 是连接"原始数据"与"结构化知识"的桥梁，支持从 Agent 矩阵直接调用。

#### 工作流程

```
接收原始内容（知识/文章/商品数据）
        ↓
写入 knowledge_queue 队列
        ↓
调用 LLM（DeepSeek/DashScope/OpenAI/OpenRouter）
        ↓
LLM 输出结构化 JSON: {title, content, category, keywords, is_duplicate}
        ↓
去重检测 → 写入 knowledge_blocks 表
        ↓
自动注册为 Agent Matrix 可调用能力
```

#### API 端点

| 路由 | 方法 | 说明 |
|------|------|------|
| `/shop/cleaner/submit` | POST | 提交原始内容 |
| `/shop/cleaner/list` | GET | 队列列表 |
| `/shop/cleaner/run/<qid>` | POST | 执行单条清洗 |
| `/shop/cleaner/run-all` | POST | 批量清洗所有待处理项 |

LLM 配置通过 `system_config` 管理：`cleaner_ai_provider`、`cleaner_ai_model`、`cleaner_ai_base_url`、`cleaner_ai_api_key`。

---

### 2.5 工作流引擎（Orchestrator）

位置：`orchestrator/`（10 个 .py 文件）

轻量级 DAG 工作流引擎，支持 12 种节点类型。

#### 状态机

```
工作流实例:
  pending → running → completed
                  ↓ → failed
                  ↓ → paused → running
                  ↓ → timeout
                  ↓ → cancelled

节点实例:
  pending → running → completed
                  ↓ → failed
                  ↓ → skipped
                  ↓ → waiting_approval → completed / rejected
```

#### 节点类型（12 种）

| 节点类型 | 用途 | 说明 |
|----------|------|------|
| `ai_agent` | AI Agent 任务 | 调用 Agent 矩阵中的子 Agent |
| `rss_fetch` | 数据采集 | RSS/API 数据拉取（对接 content_factory） |
| `ai_process` | AI 加工 | 内容分析/改写（调用 DashScope） |
| `condition` | 条件分支 | 表达式评估 |
| `approval` | 人工审批 | 暂停等待审批 |
| `publish` | 内容发布 | 文章/商品发布到多平台 |
| `notify` | 通知 | 站内信/Webhook/邮件 |
| `wait` | 等待 | 定时延迟 |
| `http_request` | HTTP 调用 | 外部 API 请求 |
| `script` | 脚本执行 | 安全沙箱（safe_eval） |
| `sub_workflow` | 子工作流 | 嵌套执行 |
| `data_transform` | 数据转换 | 格式转换/映射 |

#### 架构

```
Cron Scheduler ──→ Workflow Engine ──→ Worker Pool
       │                                      │
  定时触发                             并发执行节点
```

---

### 2.6 认证与支付系统

位置：`auth-center/`

#### JWT SSO 单点登录

```
         ┌──────────┐    sso_token cookie     ┌──────────┐
         │ Platform │ ◄──────────────────────► │  Admin   │
         │:8083     │      共享 cookie domain   │:8084     │
         └──────────┘                          └──────────┘
                │                                    │
                └────────── JWT 验证 ────────────────┘
```

- JWT 签发 + 验证，支持 `is_admin` 权限标记
- Cookie 共享：`sso_token` 跨子域名共享
- 支持支付宝 OAuth 登录 + 企业工商认证

#### 服务层（auth-center/services/，30 个文件）

| 类别 | 文件 | 功能 |
|------|------|------|
| **认证** | `jwt_service.py`, `oauth_service.py`, `verification_service.py`, `enterprise_verify_service.py` | JWT、OAuth、实名认证、企业认证 |
| **支付** | `payment_service.py`, `alipay_service.py`, `completion_service.py`, `invoice_service.py` | 支付宝支付、结算、发票 |
| **社交** | `wechat_service.py`, `weibo_service.py`, `toutiao_service.py`, `douyin_service.py`, `wechat_push_service.py` | 多平台社交分发 |
| **AI** | `agent_engine.py`, `ai_content_generator.py`, `avatar_service.py` | Agent 引擎、AI 内容生成、头像 |
| **通讯** | `email_client.py`, `mail_service.py`, `sms_service.py`, `notification_service.py` | 邮件、短信、通知 |
| **安全** | `crypto.py`, `password_validator.py`, `name_validator.py`, `sensitive_words.py` | 加密、验证、敏感词 |
| **业务** | `kdniao_service.py`, `license_service.py`, `brand_service.py`, `renewal_reminder.py`, `captcha_service.py`, `comment_review.py`, `deployment_config.py` | 物流、许可、续费、验证码、评论审核、部署 |
| **媒体** | `volcengine_client.py` | 火山引擎语音/视频 |

---

### 2.7 主题系统（Theme System）

位置：`themes/`

#### 内置主题

| 主题 | 目录 | 风格 |
|------|------|------|
| default | `themes/default/` | 默认现代风格 |
| light | `themes/light/` | 清爽亮色 |
| nature | `themes/nature/` | 自然绿色 |
| ocean | `themes/ocean/` | 海洋蓝色 |
| warm | `themes/warm/` | 温暖橙色 |

#### 实现机制

Jinja2 `ChoiceLoader` 模板覆盖：

```python
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(theme_tpl_dir),     # 优先：激活主题的 templates/
    app.jinja_loader,                    # 回退：默认模板
])
```

主题支持：模板覆盖、自定义 CSS（`theme.css`）、静态文件服务（`/themes/<slug>/`）。

---

### 2.8 系统健康检查（Health Check）

位置：`health_check/`（9 个 .py 文件）

独立的系统健康监控模块，由 Agent 矩阵中的 **Health Check Agent** 调用。每条检查项支持 **AI 分析** 和 **一键修复**，调用 LLM 诊断根因并自动执行修复脚本。

#### 功能架构

```
┌─────────────────────────────────────────────┐
│              Health Check                    │
├─────────────────────────────────────────────┤
│  ① Service Discovery    端口探活 / 路由发现  │
│  ② Health Checkers      HTTP / Ping / MySQL  │
│  ③ Alerter              邮件 / Webhook 告警  │
│  ④ AI Fixer             LLM 诊断 + 修复      │
│  ⑤ Scheduler            定时巡检（APScheduler）│
└─────────────────────────────────────────────┘
```

---

### 2.9 插件系统（Plugin System）

位置：`plugin_manager/`（管理引擎，19 个 .py 文件）+ `plugins/`（插件代码目录）

标准化插件管理系统，由 PluginManager 统一管理插件的完整生命周期：**发现 → 安装 → 启用 → 激活 → 禁用 → 卸载**。每个插件拥有独立的 SQLite 数据库，卸载时自动删除 `.db` 文件，零残留。

#### 系统架构

```
PluginManager (plugin_manager/)
├── manager.py        # 核心：生命周期管理、依赖解析、路由挂载
├── base.py           # BasePlugin 抽象基类（所有插件继承）
├── discovery.py      # 文件系统扫描 + plugin.json 解析
├── models.py         # PluginInfo / PluginStatus 数据模型
├── routes.py         # Flask 管理 API（32 个端点）
├── event_bus.py      # EventBus 事件总线（46 个预定义事件）
├── hooks.py          # Hook 系统（Action + Filter 模式）
├── config_validator.py # JSON Schema 配置校验器
├── deps.py           # 依赖解析器（拓扑排序、循环检测）
├── injectors.py      # 依赖注入辅助
├── exceptions.py     # 7 种自定义异常
├── logger.py         # 独立日志系统
├── store.py          # 插件商店 API
├── models_store.py   # 商店数据模型
├── subscription.py   # 商店订阅
├── payment.py        # 支付网关（支付宝 + Mock）
├── license.py        # 许可管理
└── license_server/   # 许可服务器
```

#### 插件生命周期

```
  发现（discover）     安装（install）       启用（enable）         激活（activate）
  ┌─────────┐        ┌──────────┐         ┌────────┐           ┌──────────┐
  │ 扫描    │        │ 写入 DB  │         │ setup  │           │ 注册路由  │
  │ plugins/│ ──────→│ 记录元   │ ───────→│ 建表   │ ────────→ │ 注册事件  │
  │ 目录    │  发现   │ 数据     │  安装   │ 初始化  │  启用    │ 启动任务  │
  └─────────┘        └──────────┘         └────────┘           └──────────┘

  卸载（uninstall）               禁用（disable）
  ┌────────────┐               ┌──────────┐
  │ 删除.db文件 │  ←────────── │ deactivate│
  │ 清理DB记录  │   卸载       │ 取消事件  │
  │ 删除配置    │              │ 停止任务  │
  └────────────┘              └──────────┘
```

#### 管理 API（32 个端点）

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/plugins` | GET | 列出所有插件 |
| `/admin/plugins/discover` | GET | 扫描新插件 |
| `/admin/plugins/<id>/install` | POST | 安装 |
| `/admin/plugins/<id>/enable` | POST | 启用 |
| `/admin/plugins/<id>/disable` | POST | 禁用 |
| `/admin/plugins/<id>/activate` | POST | 激活 |
| `/admin/plugins/<id>/uninstall` | POST | 卸载 |
| `/admin/plugins/<id>/config` | GET/POST | 配置读写 |
| `/admin/plugins/hooks/actions` | GET | Action 钩子列表 |
| `/admin/plugins/hooks/filters` | GET | Filter 钩子列表 |
| `/admin/plugins/dependency-order` | GET | 拓扑排序 |
| `/admin/plugins/<id>/dependencies` | GET | 依赖树 |
| `/admin/plugins/<id>/config/validate` | POST | 校验配置 |
| `/admin/plugins/<id>/config/batch` | POST | 批量保存 |
| `/admin/plugins/<id>/log` | GET/DELETE | 日志读取/清空 |
| `/admin/plugins/store/browse` | GET | 商店浏览 |
| `/admin/plugins/store/<id>` | GET | 商店详情 |
| `/admin/plugins/store/<id>/install` | POST | 商店安装 |
| `/admin/plugins/license/*` | * | License 管理 |
| `/admin/plugins/payment/*` | * | 支付管理 |
| `/admin/plugins/subscriptions/*` | * | 订阅管理 |
| `/admin/plugins/menus` | GET | 插件菜单 |

#### 事件系统

EventBus 定义了 46 个预定义事件，覆盖以下领域：

| 领域 | 事件 |
|------|------|
| **应用生命周期** | `app.ready`, `app.shutdown` |
| **用户** | `user.registered`, `user.login`, `user.logout`, `user.updated`, `user.deleted` |
| **订单** | `order.created`, `order.paid`, `order.refunded`, `order.cancelled`, `order.shipped`, `order.completed` |
| **订阅** | `sub.created`, `sub.renewed`, `sub.expired`, `sub.cancelled` |
| **CMS 内容** | `cms.published`, `cms.updated`, `cms.deleted` |
| **调度器** | `scheduler.job_started`, `scheduler.job_completed`, `scheduler.job_failed` |
| **健康检查** | `health.passed`, `health.warning`, `health.error` |
| **插件生命周期** | `plugin.installed`, `plugin.enabled`, `plugin.disabled`, `plugin.uninstalled` |

#### 内置插件（12 个）

| 插件 | 位置 | 版本 | 描述 | 独立数据库 |
|------|------|------|------|-----------|
| **1688 供应链采集** | `plugins/ali_api/` | 0.2.1 | 阿里巴巴商品搜索、评论、按图搜索、店铺全量采集 + AI 优化 | ali_api.db（7 表） |
| **广告管理** | `plugins/ads/` | 0.1.0 | 全站广告位创建、编辑、管理 | ads.db |
| **内容工厂** | `plugins/content_factory/` | 0.1.0 | 多源采集、AI 加工、审核发布、Skill 推送 | content_factory.db |
| **企业认证** | `plugins/enterprise_verify/` | 0.1.0 | OCR 营业执照识别 + AI 自动审核 | enterprise_verify.db |
| **商品评价** | `plugins/reviews/` | 1.0.0 | 5 星评分 + 晒图 + 匿名评价 + 管理回复 + 统计 | reviews.db |
| **收藏心愿单** | `plugins/wishlist/` | 1.0.0 | 收藏/取消/检查/列表/数量统计 | wishlist.db |
| **订单通知** | `plugins/order_notify/` | 1.0.0 | 自动站内信：下单/支付/发货/退款/取消/完成 | 无持久化 |
| **智能优惠券** | `plugins/coupons/` | 0.1.0 | 场景券 + AI 推荐 + 订阅联动 | coupons.db（2 表） |
| **AI 工具** | `plugins/ai_tools/` | 0.1.0 | PPT 生成、图像生成 | ai_tools.db |
| **分析看板** | `plugins/analytics/` | 0.1.0 | 无 Cookie 分析中间件 + 仪表盘 | analytics.db |
| **验证码服务** | `plugins/captcha_embedded/` | 0.1.0 | 滑块验证码 | — |
| **健康检查** | `plugins/health_check/` | 0.1.0 | 系统健康巡检/告警/趋势分析 | health.db |

#### 插件规范

```python
from plugin_manager.base import BasePlugin

class MyPlugin(BasePlugin):
    name = 'my_plugin'
    version = '1.0.0'
    description = '我的插件'
    author = 'VeroRun'

    def on_install(self, registry) -> bool:
        """安装时初始化插件自有数据库"""
        init_db()  # 在 plugins/my_plugin/my_plugin.db 中建表
        return True

    def on_uninstall(self, registry) -> bool:
        """卸载时清理 — BasePlugin 默认自动删除 .db 文件"""
        return True

    def register_routes(self):
        """注册 Flask 蓝图（自动挂载 /plugin/<name>/）"""
        from flask import Blueprint
        bp = Blueprint('my_plugin', __name__, url_prefix='/plugin/my_plugin')
        return [bp]
```

#### 目录结构规范

```
plugins/<name>/
├── __init__.py        # 插件类（继承 BasePlugin）
├── plugin.json        # 元数据（含 permissions 声明）
├── <name>.db          # 插件自有数据库（自动创建/删除）
├── i18n/              # 插件自有翻译（隔离于系统 _()）
│   ├── zh-CN.yml
│   └── en.yml
├── routes/            # Flask 蓝图（自动挂载 /plugin/<name>/）
├── services/          # 业务逻辑
├── static/            # 静态资源
└── templates/         # 模板
```

---

### 2.10 国际化（i18n）

位置：`i18n/`

全域 i18n 支持，50+ 文件使用 `_()` 翻译函数。

- **存储方式**：DB `i18n_strings` 表 + YAML 文件双存储
- **查找链**：DB（管理后台可编辑）→ YAML → 原文（三阶降级）
- **语言包**：`zh-CN.yml` / `en.yml`
- **性能**：`get_all_translations()` 使用 LRU 内存缓存，避免每次翻译新建 SQLite 连接
- **插件隔离**：插件使用 `self.t()`，不与系统 `_()` 冲突
- **静态语言**：通过 `DEPLOY_LANG` 环境变量决定

---

### 2.11 内容工厂（Content Factory）

位置：`auth-center/services/content_factory/`（已解耦为独立插件 `plugins/content_factory/`）

```
RSS/API 采集 → AI 加工（DashScope）→ Skill 推送
```

| 组件 | 文件 | 功能 |
|------|------|------|
| 基类采集器 | `base_collector.py` | HASH 去重、标题相似度检测、批量写入 |
| AI 处理器 | `ai_processor.py` | 调用通义千问提取/分析/改写 |
| Skill 推送器 | `skill_pusher.py` | 导出为 SKILL.md，推送到 Hermes/OpenClaw |

---

### 2.12 其他服务

#### 验证码服务（captcha-service）

独立服务（端口 8090），通过 Platform/Admin 反向代理接入：

```
用户请求 → Platform:8083 → /api/captcha/* → Captcha:8090
```

能力：拼图验证码生成 / 验证 / 消耗限流。

#### 分析系统（analytics）

- **中间件**：自动记录访问日志（路径、IP、UA、耗时），支持报告生成
- **处理器**：每 60 秒聚合一次原始日志
- **GeoIP**：IP 地理定位（`ip2region/`）
- **仪表板**：管理后台查看统计

#### 社交分发（social_push）

| 平台 | 服务文件 | 能力 |
|------|----------|------|
| 微博 | `weibo_service.py` | 内容发布 |
| 微信公众号 | `wechat_push_service.py` | 图文推送 |
| 今日头条 | `toutiao_service.py` | 内容发布 |
| 抖音 | `douyin_service.py` | 视频发布 + AI 配图/文案 |

#### 评论系统（comments）

- 数据库表：`comments`
- 管理路由：`auth-center/routes/comments.py`
- AI 审核：`comment_review.py` 自动过滤敏感内容

---

## 三、技术栈

### 后端

| 技术 | 用途 |
|------|------|
| **Python 3** | 主要开发语言 |
| **Flask** | Web 框架（5 个独立服务实例：Site/Platform/Admin/Captcha） |
| **SQLite** | 数据库（主库 `data/easykai.db` + 各插件独立 `.db`） |
| **Jinja2** | 模板引擎（ChoiceLoader 主题覆盖） |
| **JWT** | SSO 单点登录（跨子域名 Cookie 共享） |
| **APScheduler** | 定时任务（工作流调度 + 健康检查 + 分析聚合） |
| **cryptography** | RSA2 签名（支付宝） |
| **Paramiko** | SSH 自动化部署 |

### AI 能力

| 能力 | 供应商/模型 |
|------|------------|
| 主控推理（Master） | OpenAI GPT-4o |
| 子 Agent 推理 | DashScope qwen-turbo / DeepSeek Chat |
| 原生 Function Calling | AIEngine.chat_with_tools() + Tool Registry |
| ReAct 工具循环 | AgentRunner._run_react_loop() — 最多 5 轮 |
| 图像生成 | 通义万相 wan2.7-image |
| 声音克隆 | 火山引擎 volc-voice-clone-v2 |
| 数字人视频 | 火山引擎 volc-avatar-v3 |
| 备用推理 | SiliconFlow / OpenRouter / Ollama |
| AI 引擎统一封装 | `agent_matrix/engine.py` → AIEngine（7 供应商统一接口） |

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
| **Vanilla JS** | SPA 前端 |
| **Unpkg / CDN** | 第三方库 |
| **CSS Custom Properties** | 主题系统变量 |
| **AdminLTE** | 管理面板 UI |

---

## 四、项目结构

```
VeroRunSystem/
├── site/                      # 主站后端（Flask, 端口 8081）
│   ├── app.py                 # 入口：auth/cms/shop/site 蓝图注册
│   └── templates/             # 站点模板
│
├── admin/                     # 管理后台（Flask, 端口 8084）
│   ├── app.py                 # 入口：17+ 蓝图 + PluginManager + AgentMatrix
│   ├── routes/                # 管理路由
│   ├── templates/             # 管理模板
│   └── static/                # 静态资源
│
├── platform/                  # 用户控制台（Flask, 端口 8083）
│   ├── app.py                 # 入口：auth/cms/shop/API 注册
│   ├── routes/
│   │   ├── shop_public.py     # 商城前端 API
│   │   ├── api_v1.py          # 通用 API
│   │   └── site_routes.py     # 页面路由
│   ├── templates/             # 前端模板
│   └── static/                # 静态资源
│
├── captcha-service/           # 验证码服务（独立 Flask, 端口 8090）
│   ├── server.py              # 入口
│   ├── routes/captcha.py      # 验证码 API
│   └── captcha/               # 行为验证/生成/安全
│
├── auth-center/               # 认证中心 + 业务核心
│   ├── auth_blueprint.py      # 蓝图注册中心（7 蓝图统一注册）
│   ├── models/                # 数据模型
│   │   ├── database.py        # 数据库连接 + 全部建表 + 种子数据
│   │   └── cms.py             # CMS 模型
│   ├── routes/                # 18 个路由模块
│   │   ├── shop_admin.py      # 商城管理（含 ShopAIProcessor）
│   │   ├── cleaner_agent.py   # 数据清洗
│   │   ├── agents.py          # Agent 管理
│   │   ├── admin.py           # 管理员路由
│   │   ├── auth.py            # 登录/注册/OAuth
│   │   ├── user.py            # 用户管理
│   │   ├── cms_admin.py       # CMS 管理
│   │   ├── comments.py        # 评论管理
│   │   ├── sessions.py        # 会话管理
│   │   ├── social_push.py     # 社交推送
│   │   ├── social_media.py    # 社交媒体管理
│   │   ├── theme_admin.py     # 主题管理
│   │   ├── footer_admin.py    # 页脚管理
│   │   ├── header_admin.py    # 头部导航管理
│   │   ├── deployment_api.py  # 部署 API
│   │   ├── douyin_miniprogram.py # 抖音小程序
│   │   └── subscription/      # 订阅模块（4 种支付网关）
│   │       ├── renewal.py
│   │       └── gateway/
│   │           ├── alipay.py
│   │           ├── wechat.py
│   │           ├── stripe.py
│   │           └── paypal.py
│   └── services/              # 30 个服务模块
│       ├── payment_service.py
│       ├── jwt_service.py
│       ├── agent_engine.py
│       ├── kdniao_service.py
│       ├── volcengine_client.py
│       └── ...（共 30 个）
│
├── agent_matrix/              # Agent 矩阵系统
│   ├── engine.py              # AIEngine（7 供应商统一接口 + function calling）
│   ├── tools.py               # 工具注册中心（3 只读工具 + 白名单过滤）
│   ├── orchestrator.py        # 任务编排 + 关键词路由 + 上下文压缩
│   ├── agent_runner.py        # Agent 执行器 + ReAct 工具循环 + 自检重试
│   ├── routes.py              # API 路由（29+ 端点）
│   ├── models.py              # 数据模型 + 9 Agent 种子数据 + 6 张表
│   └── prompts/               # 10 个 Agent Prompt 文件
│       ├── master_prompt.md
│       ├── sub_shop_prompt.md
│       ├── sub_cms_prompt.md
│       ├── sub_health_check_prompt.md
│       └── ...（共 10 个）
│
├── orchestrator/              # DAG 工作流引擎（10 个 .py）
│   ├── workflow_engine.py     # 引擎核心
│   ├── nodes.py               # 节点定义
│   ├── scheduler.py           # Cron 调度
│   ├── worker.py              # Worker 池
│   ├── safe_eval.py           # 安全沙箱
│   ├── routes.py              # API 路由
│   └── models.py              # 数据模型
│
├── health_check/              # 健康检查模块（9 个 .py）
│   ├── routes.py              # 蓝图
│   ├── models.py              # 检查记录模型
│   ├── checkers.py            # HTTP/Ping/MySQL 检查器
│   ├── discovery.py           # 服务发现
│   ├── alerter.py             # 邮件/Webhook 告警
│   ├── ai_fixer.py            # LLM 自动诊断修复
│   └── scheduler_setup.py     # 定时巡检
│
├── analytics/                 # 分析系统（10 个 .py）
│   ├── middleware.py          # 请求日志中间件
│   ├── processor.py           # 60 秒聚合处理器
│   ├── dashboard.py           # 仪表板蓝图
│   ├── models.py              # 数据模型
│   ├── tracker.py             # 跟踪模块（报告生成）
│   ├── geoip.py               # IP 地理定位
│   ├── ua_parser.py           # UA 解析
│   └── ip2region/             # IP 库
│
├── plugin_manager/            # 插件管理引擎（19 个 .py）
│   ├── __init__.py            # 包入口
│   ├── manager.py             # PluginManager — 生命周期管理核心
│   ├── base.py                # BasePlugin 抽象基类
│   ├── discovery.py           # PluginDiscovery — 文件系统扫描
│   ├── models.py              # PluginInfo / PluginStatus / PluginRegistry
│   ├── routes.py              # /admin/plugins/* 管理 API（32 端点）
│   ├── event_bus.py           # EventBus 事件总线（46 事件）
│   ├── deps.py                # 依赖解析器
│   ├── config_validator.py    # 配置验证器
│   ├── exceptions.py          # 7 种异常定义
│   ├── hooks.py               # Hook 系统
│   ├── injectors.py           # 依赖注入
│   ├── logger.py              # 独立日志系统
│   ├── store.py               # 插件商店 API
│   ├── models_store.py        # 商店数据模型
│   └── subscription.py        # 商店订阅
│
├── plugins/                   # 插件代码目录（独立数据库）
│   ├── ads/                   # 广告管理（ads.db）
│   ├── ai_tools/              # AI 工具（ai_tools.db）
│   ├── ali_api/               # 1688 供应链采集（ali_api.db, 7 表, 0.2.1）
│   ├── analytics/             # 分析看板（analytics.db）
│   ├── captcha_embedded/      # 验证码嵌入
│   ├── content_factory/       # 内容工厂（content_factory.db）
│   ├── coupons/               # 智能优惠券（coupons.db, 2 表）
│   ├── enterprise_verify/     # 企业认证（enterprise_verify.db）
│   ├── health_check/          # 健康检查（health.db）
│   ├── order_notify/          # 订单通知（无持久化, 1.0.0）
│   ├── reviews/               # 商品评价（reviews.db, 1.0.0）
│   └── wishlist/              # 收藏心愿单（wishlist.db, 1.0.0）
│
├── themes/                    # 5 个主题
│   ├── default/
│   ├── light/
│   ├── nature/
│   ├── ocean/
│   └── warm/
│       └── theme.css + theme.json
│
├── i18n/                      # 国际化翻译
│   ├── __init__.py            # i18n 引擎（DB + YAML + LRU 缓存）
│   ├── zh-CN.yml
│   └── en.yml
│
├── docs/                      # 项目文档
├── scripts/                   # 运维脚本
├── PLANS/                     # 开发计划
└── .trae/                     # Trae IDE 配置
```

---

## 五、快速开始

### 环境要求

- Python 3.9+
- pip / venv
- SQLite（内置）
- OpenAI / DeepSeek API Key（如需 Agent 矩阵功能）

### 安装

```bash
# 克隆项目
git clone <repo-url> easykai-site
cd easykai-site

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 .\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 启动全部服务

```bash
# ① 验证码服务（端口 8090）
cd captcha-service
python server.py &

# ② 站点后端（端口 8081）
cd ../site
python app.py 8081 &

# ③ 用户控制台（端口 8083）
cd ../platform
python app.py 8083 &

# ④ 管理后台（端口 8084）
cd ../admin
python app.py 8084 &
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
3. 可选：在 `orchestrator.py` 的 `_template_decompose()` 中添加关键词路由
4. 可选：在管理后台单独配置 Agent 的供应商/模型
5. 可选：如需 ReAct 工具能力，在 Agent 配置的 `allowed_tools` 中声明白名单

### 新增一个工具（Tool）

1. 在 `agent_matrix/tools.py` 的 `TOOL_SCHEMAS` 字典中添加 schema（OpenAI function calling 格式）
2. 在 `TOOL_EXECUTORS` 字典中绑定执行函数
3. 在管理后台将 Agent 的 `allowed_tools` 字段加上新工具名称

### 新增一个插件

1. 创建 `plugins/<name>/__init__.py`（继承 `plugin_manager.base.BasePlugin`）
2. 创建 `plugins/<name>/plugin.json` 填写元数据（含 `permissions` 声明）
3. 添加翻译：`plugins/<name>/i18n/{locale}.yml`
4. 添加路由：`plugins/<name>/routes/`（自动挂载到 `/plugin/<name>/`）
5. 在 `on_install()` 中调用 `init_db()` 创建插件自有数据库
6. 通过 `event_bus.on(EventName.XXX, self.handler)` 订阅事件

### 添加事件钩子

1. 在核心路由中调用 `get_event_bus().emit('EVENT_NAME', key1=val1, key2=val2)`
2. 插件通过 `event_bus.on(EventName.XXX, handler_func)` 订阅
3. 参见 `plugins/order_notify/__init__.py` 完整示例

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
- 插件隔离：每个插件拥有独立 SQLite 数据库，卸载时自动删除 `.db` 文件，零残留

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
| `NGINX_SNIPPETS_DIR` | 独立服务子域名 Nginx 配置写入目录 |

### Site Domains 子域名管理

管理后台 `agent.easykai.cn/admin` → **System → Site Domains** 操作：

- **类型**：内容站点（走 site app 8081）或 独立服务（自定义端口，自动生成 Nginx 配置）
- **配额**：按套餐限制（deploy_basic=20 / pro=20 / enterprise=20）
- **Nginx 部署**：创建独立服务 → 自动写入 Nginx snippets 目录 → 自动 `nginx -s reload`
- **中间件**：`g.current_site` 注入 `service_type` / `service_port`，支持按子域名路由分发

### 部署同步

```bash
rsync -av --delete --exclude='.git' --exclude='__pycache__' --exclude='venv' \
  ./ easykai@server:/home/easykai/easykai-workspace/easykai.cn/
```

---

> VeroRunSystem v0.10.5 — Multi-Agent AI Operating System  
> 多智能体驱动的 AI 内容与商业枢纽  
> © 2026 VeroRunSystem 版权所有
