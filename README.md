# VeroRun — 易站AI

**Multi-Agent AI Operating System** — 多智能体驱动的全栈 SaaS 建站与商业管理平台

VeroRun（易站AI）是一个基于 **7 角色 Agent 协作矩阵 + 工具注册中心** 的全栈平台，集成多供应商 AI 引擎、商城运营、CMS 内容管理、AI 客服、自动化工作流、云服务开通、分析统计、系统健康巡检、插件化扩展等能力，采用 PostgreSQL 多 Schema 架构。

> 版本：**v0.33.1**  
> 仓库：`https://github.com/fanjumin/VeroRunSystem`

---

## 一、系统架构

### 服务拓扑

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│    Site     │    │  Platform   │    │   Admin     │    │  Community   │
│   :8081     │    │   :8083     │    │   :8084     │    │  (独立服务)   │
│ 主站后端    │    │ 用户控制台  │    │ 管理后台    │    │ AI 社区/广场  │
│ OAuth/用户  │    │ 商城前端    │    │ Agent矩阵   │    │ Agent 市集    │
│ 订阅        │    │ CMS展示     │    │ 插件管理    │    │ 飞书/企微集成 │
│ 官网页面    │    │ 登录/定价   │    │ 订阅/支付   │    │ 充值/续费    │
│             │    │ 用户中心    │    │ 分析/健康   │    │              │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬───────┘
       │                   │                   │                  │
       └───────────────────┼───────────────────┼──────────────────┘
                           │                   │
                    ┌──────┴──────┐    ┌───────┴───────┐
                    │ PostgreSQL  │    │    Redis      │
                    │  verorun    │    │  (缓存/队列)   │
                    │ (多Schema)  │    │               │
                    └─────────────┘    └───────────────┘
```

### Nginx 生产部署

| 域名 | 端口 | 服务 |
|------|------|------|
| easykai.cn / www.easykai.cn（根路由 `/`） | `:8081` | 主站后端（Site） |
| easykai.cn `/admin/` | `:8084` | 管理后台（Admin） |
| easykai.cn `/auth/` `/subscribe` | `:8083` | 认证/订阅（Platform） |
| easykai.cn `/auth/oauth/` `/user/` | `:8081` | OAuth/用户（Site） |
| platform.easykai.cn | `:8083` | Platform 用户控制台 |
| agent.easykai.cn | `:8084` | Admin（Agent 矩阵入口） |
| 子域名 `*` | 自定端口 | Site Domains 插件管理 |

---

## 二、核心模块

### 2.1 Agent 矩阵系统

位置：`agent_matrix/`

核心组件 — 基于 **YAML 角色定义 + 多供应商 AI 引擎 + ReAct 工具循环 + 并行调度 + 自检重试 + 智能记忆提取**。

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
│  • 对话结束自动提取知识 → Cleaner 入库                        │
└───────────────────────────────┬──────────────────────────────┘
                                │
                  Orchestrator  │  并行/串行调度（ThreadPoolExecutor 最多5并发，300s超时）
                                │  上下文压缩（>8条→LLM摘要）
    ┌──────┬──────┬──────┬──────┼──────┬──────┬──────┐
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
 ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
 │Cont│ │Shop│ │Buil│ │Stew│ │Ops │ │Serv│ │Tool│
 │ent │ │    │ │der │ │ard │ │    │ │ice │ │Reg.│
 ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤
 │    │ │    │ │    │ │    │ │    │ │    │ │14个│
 │    │ │    │ │    │ │    │ │    │ │    │ │工具│
 └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
```

#### AI 供应商（6 个）

| 供应商 | 用途 | 典型模型 |
|--------|------|----------|
| **DashScope**（阿里通义） | 主推理 + 图像生成 | qwen-turbo, qwen-plus |
| **DeepSeek** | 子 Agent 推理 | deepseek-chat |
| **OpenAI** | 主控 Agent | gpt-4o, gpt-4o-mini |
| **SiliconFlow**（硅基流动） | 备用推理 + 图像生成 | DeepSeek-V3, FLUX.1-dev |
| **OpenRouter** | 多模型路由 | 多模型 |
| **Ollama** | 本地推理 | llama3 等 |

> 注：火山引擎（Volcengine）作为独立服务客户端（`auth-center/services/volcengine_client.py`），提供语音克隆和数字人视频能力，不通过 AI 引擎统一接口调用。

#### 7 个角色（YAML 定义）

角色定义位于 `agent_matrix/roles/`，基于 YAML 文件配置，支持 `managed_modules` 模块权限、`allowed_tools` 工具白名单、`capabilities` 能力声明。

| 角色 | 类型 | 文件 | 默认模型 | 核心能力 |
|------|------|------|----------|----------|
| **Athena** | master | `01-athena.yaml` | GPT-4o | 任务分解 → 指派子 Agent → 汇总报告 → 自检质量 |
| **Content** | sub | `02-content.yaml` | qwen-turbo | 内容生成、图像生成、PPT/文档制作、知识清洗 |
| **Shop** | sub | `03-shop.yaml` | qwen-turbo | 商品 CRUD、SKU/规格、订单、优惠券、AI 优化 |
| **Builder** | sub | `04-builder.yaml` | qwen-turbo | 一键建站、站点设计、主题配置 |
| **Steward** | sub | `05-steward.yaml` | qwen-turbo | 用户管理、API Key、系统配置、财务/订阅 |
| **Ops** | sub | `06-ops.yaml` | qwen-turbo | 自动化 Cron、Workflow 编排、DAG 管理 |
| **Service** | sub | `07-service.yaml` | deepseek-chat | 全站 FAQ、多轮对话、工单反馈、健康巡检、分析 |

#### 12 个 Prompt 文件

`agent_matrix/prompts/`：`master_prompt.md`、`sub_shop_prompt.md`、`sub_cms_prompt.md`、`sub_content_prompt.md`、`sub_builder_prompt.md`、`sub_finance_prompt.md`、`sub_user_prompt.md`、`sub_automation_prompt.md`、`sub_health_check_prompt.md`、`sub_chatbot_prompt.md`、`sub_supply_chain_prompt.md`、`sub_ops_prompt.md`

#### 工具注册中心（14 个工具）

| 工具 | 类型 | 描述 |
|------|------|------|
| `get_system_health` | 只读 | 获取系统健康巡检结果汇总（健康分/通过/警告/错误） |
| `query_stats` | 只读 | 查询站点访问统计（PV/UV/趋势/来源/热门页面） |
| `search_knowledge` | 只读 | 在平台知识库中检索关键词相关内容片段 |
| `ads_list` | 只读 | 列出广告位，按站点/位置/启用状态筛选 |
| `ads_create` | 读写 | 创建新广告位（图片/代码/定向/频控） |
| `ads_update` | 读写 | 更新广告位字段（启用/禁用/代码/权重） |
| `ads_delete` | 读写 | 删除指定广告位 |
| `ads_get_stats` | 只读 | 广告统计（展示/点击/CTR/每日趋势） |
| `ads_analyze` | 只读 | 广告效果分析与优化建议 |
| `ads_render_snippet` | 只读 | 生成 Jinja2 模板渲染代码片段 |
| `generate_ppt` | 生成 | AI 生成 PPT 演示文稿（主题/页数/风格） |
| `generate_image` | 生成 | AI 图像生成（SiliconFlow FLUX/Stable Diffusion） |
| `generate_markdown` | 生成 | AI 生成 Markdown 文档 |
| `generate_docx` | 生成 | AI 生成 Word 文档（.docx，含格式样式） |

工具执行统一带 try/except 兜底，失败返回字符串错误信息，保证 ReAct 循环不会崩溃。

#### ReAct 工具循环

```
思考 → 模型返回 tool_calls → 执行工具 → 结果回灌 → 再思考 → ...
                                                                  ↓
                                                   模型返回纯文本 → 终态答复
```

- 轮次上限（默认 5 轮），达到后强制收尾
- 工具结果截断（4000 字符），防止上下文膨胀
- 空返回自动回退到普通 `chat()` 模式
- 无工具可用的 Agent 走原单轮逻辑

#### 意图分类器

`agent_matrix/intent.py` — 独立于 chatbot 插件的轻量级 LLM 意图分类器，支持 6 种意图（purchase/aftersale/complaint/consult/technical/other）和 4 种情绪（positive/neutral/negative/urgent）。

#### 语音接口（预留）

`agent_matrix/audio.py` — 定义 AudioInputProcessor（ASR）和 AudioOutputProcessor（TTS）标准接口，预留 Vosk + 阿里云实现。

#### 工作流程

1. **接收**：用户通过管理面板或 chatbot 输入指令
2. **分解**：Athena（GPT-4o）将任务分解为子任务列表（LLM 失败时走关键词模板 Fallback）
3. **调度**：Orchestrator 根据子任务 domain 分配到对应 Sub Agent（ThreadPoolExecutor 并行，最多 5 并发，300s 超时熔断）
4. **执行**：各 Sub Agent 并行执行，有工具的 Agent 进入 ReAct 循环
5. **自检**：每 Agent 输出后自我评分（0-1），低置信度（<0.7）自动重试（最多 3 次）；灰区（0.5~0.8）触发 LLM 结构化自评
6. **汇总**：Athena 收集所有结果，整合为结构化报告
7. **智能记忆**：对话结束后异步提取知识要点 → Cleaner 自动入库

---

### 2.2 Site Builder（LLM 一键建站）

位置：`site_builder/`

LLM 驱动的站内网页一键建站核心模块，复用 Agent 矩阵的 Master Agent 生成站点内容，按建站 DAG 逐步落地。

#### 模块结构

| 子模块 | 位置 | 职责 |
|--------|------|------|
| **建站引擎** | `site_builder/engine.py` + `routes.py` | 解析需求 → 结构化方案 → 执行建站 DAG（品牌→主题→导航→页面→文档） |
| **统一设计令牌** | `site_builder/site_settings/` | 一套设计令牌（brand/colors/typography/navigation/footer/seo）统一替代多套独立模块 |
| **Mini App 生成器** | `site_builder/mini_app/` | 小程序/轻应用打包与部署（engine + packager + deployer） |
| **国际化** | `site_builder/i18n/` | 建站模块独立翻译（zh-CN / en） |

#### 内置行业模板

`site_builder/prompts/`：`tech_company`（科技公司）、`law_firm`（律所）、`restaurant`（餐饮）、`education`（教育）

#### 建站流程

```
用户需求（自然语言）
      ↓
Master Agent（AIEngine）解析 → 结构化建站方案
      ↓
建站 DAG：品牌 → 主题 → 导航 → 页面 → 文档
      ↓
写入统一设计令牌 + CMS 页面块 → 站点生效
```

---

### 2.3 商城模块（Shop）

后台管理：`auth-center/routes/shop_admin.py`  
前端 API：`platform/routes/shop_public.py`

| 功能 | 说明 |
|------|------|
| **商品管理** | CRUD + 多图上传/排序/删除 + AI 优化标题/描述/卖点 |
| **SKU 管理** | 规格组 → 笛卡尔积生成 SKU，自动生成 sku_code |
| **分类管理** | 无限级分类树，树形结构 + 批量排序 |
| **购物车** | 增/删/改/查/批量，有效期 30 天 |
| **订单管理** | 发货/退款/物流查询，幂等性 + 限流 |
| **优惠券** | 固定减/百分比减，限定商品，批量发放 |
| **支付** | 支付宝电脑网站支付（RSA2 签名 + 桩模式降级） |
| **订阅支付** | 独立于商城，支持 4 网关：支付宝/微信/Stripe/PayPal |

---

### 2.4 CMS 内容管理

模型：`auth-center/models/cms.py`  
管理路由：`auth-center/routes/cms_admin.py`

- **页面块系统**：text / hero / features / gallery / cta / contact 等类型，拖拽排序，独立发布控制
- **文章管理**：slug、分类、标签、受众、发布渠道
- **社交发布**：一键分发到微博、微信、头条、抖音

---

### 2.5 数据清洗（Cleaner Agent）

位置：`auth-center/routes/cleaner_agent.py`

```
原始内容 → 写入 knowledge_queue → LLM 清洗（DeepSeek/DashScope/OpenAI）
→ 结构化 JSON {title, content, category, keywords, is_duplicate}
→ 去重检测 → 写入 knowledge_blocks → 自动注册为 Agent Matrix 可调用能力
```

---

### 2.6 工作流引擎（Orchestrator）

位置：`orchestrator/`（11 个 .py 文件）

轻量级 DAG 工作流引擎，支持 12 种节点类型：`ai_agent`、`rss_fetch`、`ai_process`、`condition`、`approval`、`publish`、`notify`、`wait`、`http_request`、`script`、`sub_workflow`、`data_transform`。

新增 `trigger_dispatch.py`（触发器分发）和 `workflow_templates.py`（工作流模板）。

---

### 2.7 认证与支付

位置：`auth-center/`

- **JWT SSO**：`sso_token` cookie 跨子域名共享，支持 `is_admin` 权限标记
- **OAuth**：支付宝 OAuth 登录 + 企业工商认证
- **订阅支付**：4 种网关（支付宝周期扣款 / 微信委托扣款 / Stripe Checkout / PayPal Orders）
- **服务层**（27 个文件）：JWT、OAuth、支付、社交分发、AI 引擎、邮件/短信、加密、许可、验证码、部署等

---

### 2.8 主题系统

位置：`themes/` — 5 个主题（default / light / nature / ocean / warm），Jinja2 `ChoiceLoader` 模板覆盖。

---

### 2.9 国际化（i18n）

位置：`i18n/` — DB `i18n_strings` 表 + YAML 文件双存储，三阶降级（DB → YAML → 原文），LRU 内存缓存，插件隔离（`self.t()`）。默认语言为英文，内置中文（zh-CN）翻译，避免操作系统编码差异导致的乱码问题。

---

### 2.10 插件系统

位置：`plugin_manager/`（18 个 .py 文件）+ `plugins/`（24 个插件）

#### 架构

```
PluginManager
├── manager.py        # 核心：生命周期管理、依赖解析、路由挂载
├── base.py           # BasePlugin 抽象基类
├── discovery.py      # 文件系统扫描 + plugin.json 解析
├── models.py         # PluginInfo / PluginStatus / PluginRegistry
├── routes.py         # Flask 管理 API（32 个端点）
├── event_bus.py      # EventBus 事件总线（46 个预定义事件）
├── hooks.py          # Hook 系统（Action + Filter 模式）
├── config_validator.py  # JSON Schema 配置校验
├── deps.py           # 依赖解析器（拓扑排序、循环检测）
├── injectors.py      # 依赖注入辅助
├── exceptions.py     # 7 种自定义异常
├── logger.py         # 独立日志系统
├── store.py          # 插件商店 API
├── models_store.py   # 商店数据模型
├── subscription.py   # 商店订阅
├── payment.py        # 支付网关
├── license.py        # 许可管理
└── license_server/   # 许可服务器
```

#### 24 个内置插件

| 插件 | 数据库 | 描述 |
|------|--------|------|
| **ads** | ads.db | 全站广告位创建、编辑、管理、统计、分析 |
| **ali_api** | ali_api.db（7 表） | 1688 商品搜索、评论、按图搜索、店铺采集 + AI 优化 |
| **analytics** | analytics.db | 无 Cookie 分析中间件 + 仪表盘 |
| **captcha_embedded** | — | 滑块拼图验证码（嵌入式蓝图） |
| **chatbot** | — | AI 聊天机器人前端组件 |
| **content_factory** | content_factory.db | 多源采集、AI 加工、审核发布、Skill 推送 |
| **coupons** | coupons.db（2 表） | 场景券 + AI 推荐 + 订阅联动 |
| **currency_converter** | — | 多币种汇率转换 |
| **dev_accounts** | — | 开发者账号管理 |
| **email** | email.db | 邮件发送配置与收发记录 |
| **enterprise_verify** | enterprise_verify.db | OCR 营业执照识别 + AI 自动审核 |
| **health_check** | health.db | 系统健康巡检/告警/趋势分析 |
| **im_gateway** | im_gateway.db | 飞书/企业微信/钉钉/QQ 多适配器消息网关 |
| **logistics** | — | 快递鸟物流查询 |
| **oauth_config** | 主库 | 第三方 OAuth 登录配置管理 |
| **order_notify** | 无持久化 | 自动站内信：下单/支付/发货/退款/取消/完成 |
| **payment** | — | 支付网关插件 |
| **reviews** | reviews.db | 5 星评分 + 晒图 + 匿名评价 + 管理回复 |
| **site_domains** | 主库 | 子域名管理 + Nginx 配置自动生成/reload |
| **sms** | — | 短信服务插件 |
| **social_push** | 主库 | 微博/微信/头条/抖音内容分发 |
| **subscription** | — | 订阅管理插件 |
| **verification** | — | 实名认证插件 |
| **wishlist** | wishlist.db | 收藏/取消/检查/列表/数量统计 |

---

### 2.11 新增服务模块

#### providers/ — 第三方服务抽象层

| 子模块 | 适配器 |
|--------|--------|
| **logistics** | Shippo（国际物流） |
| **payment** | Stripe / PayPal |
| **sms** | 阿里云短信 / Twilio |
| **social** | LinkedIn / Twitter |

#### cognition-service — 认知服务

独立 FastAPI 服务（`cognition-service/server.py`），提供：
- 地图服务（`maps.py`）
- 价格获取（`price_fetcher.py`）
- 声誉评分（`reputation.py`）
- 结算服务（`settlement.py`）
- 嵌入向量（`embedding.py`）
- 搜索（`search.py`）
- 预测（`predictions.py`）
- 数据验证（`validator.py`）

#### community — AI 社区

独立服务（`community/app.py`），提供：
- Agent 社区/广场（`agent_community.py`）
- 任务市场（`agent_tasks.py`）
- 飞书/企业微信机器人集成（`feishu.py` / `wecom.py`）
- 自动充值/续费（`auto_recharge.py` / `auto_renew.py`）
- 每日用量归档（`daily_usage_archive.py`）
- SSE 事件推送（`sse_events.py`）

#### health_service — 健康守护

独立健康守护进程（`health_service/runner.py`），提供服务级别的健康监控与自动恢复。

---

## 三、技术栈

### 后端

| 技术 | 用途 |
|------|------|
| **Python 3.11+** | 主要开发语言 |
| **Flask** | Web 框架（Site/Platform/Admin 独立实例） |
| **FastAPI** | cognition-service 异步服务 |
| **PostgreSQL** | 主数据库（多 Schema：public/shop/analytics/health/payment/order_notify） |
| **Redis** | 缓存 / 消息队列 |
| **psycopg2** | PostgreSQL 连接池（ThreadedConnectionPool, 3-20 连接） |
| **Jinja2** | 模板引擎（ChoiceLoader 主题覆盖） |
| **JWT（PyJWT）** | SSO 单点登录（跨子域名 Cookie） |
| **APScheduler** | 定时任务调度 |
| **Gunicorn** | WSGI 生产服务器 |
| **Docker** | 容器化部署 |

### AI 能力

| 能力 | 供应商/模型 |
|------|------------|
| 主控推理（Master） | OpenAI GPT-4o |
| 子 Agent 推理 | DashScope qwen-turbo / DeepSeek Chat |
| 原生 Function Calling | AIEngine.chat_with_tools() + Tool Registry |
| ReAct 工具循环 | AgentRunner._run_react_loop() — 最多 5 轮 |
| 图像生成 | SiliconFlow FLUX.1-dev / Stable Diffusion |
| 声音克隆 | 火山引擎 volc-voice-clone-v2 |
| 数字人视频 | 火山引擎 volc-avatar-v3 |
| 意图分类 | DashScope qwen-turbo（agent_matrix/intent.py） |
| 语音接口（预留） | Vosk / 阿里云 ASR-TTS（agent_matrix/audio.py） |

### 第三方集成

| 服务 | 用途 |
|------|------|
| 支付宝 | 商城支付 + 订阅周期扣款 |
| 微信支付 | 订阅扫码支付 + 委托扣款 |
| Stripe / PayPal | 国际订阅支付 |
| 快递鸟 / Shippo | 物流查询 |
| 微博/微信/头条/抖音/LinkedIn/Twitter | 社交内容分发 |
| 飞书/企业微信/钉钉/QQ | IM 消息网关 |

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
VeroRun/
├── site/                      # 主站后端（Flask, 端口 8081）
│   ├── app.py                 # 入口
│   └── templates/             # 43 个站点模板
│
├── admin/                     # 管理后台（Flask, 端口 8084）
│   ├── app.py                 # 入口：20+ 蓝图 + PluginManager + AgentMatrix
│   ├── routes/                # 管理路由
│   ├── templates/             # 管理模板（含 workflow_editor）
│   └── static/                # 静态资源
│
├── platform/                  # 用户控制台（Flask, 端口 8083）
│   ├── app.py                 # 入口：auth/cms/shop/API 注册
│   ├── routes/                # shop_public / api_v1 / site_routes / mini_program
│   ├── templates/             # 42 个前端模板
│   └── static/                # 静态资源
│
├── community/                 # AI 社区（独立 Flask 服务）
│   ├── app.py                 # 社区入口
│   ├── agent_community.py     # Agent 广场
│   ├── agent_tasks.py         # 任务市场
│   ├── chatbot.py             # AI 聊天
│   ├── feishu.py / wecom.py   # 飞书/企微集成
│   ├── auto_recharge.py       # 自动充值
│   ├── auto_renew.py          # 自动续费
│   └── payment.py             # 支付
│
├── auth-center/               # 认证中心 + 业务核心
│   ├── models/database.py     # PostgreSQL 连接池 + 多 Schema（2763 行）
│   ├── routes/                # 16 个路由模块
│   │   ├── shop_admin.py      # 商城管理
│   │   ├── cleaner_agent.py   # 数据清洗
│   │   ├── subscription/      # 订阅模块（4 网关）
│   │   └── ...
│   └── services/              # 27 个服务模块
│
├── agent_matrix/              # Agent 矩阵系统
│   ├── engine.py              # AIEngine（6 供应商统一接口 + function calling）
│   ├── tools.py               # 工具注册中心（14 工具 + 白名单过滤）
│   ├── orchestrator.py        # 任务编排 + 关键词路由 + 智能记忆提取（1037 行）
│   ├── agent_runner.py        # Agent 执行器 + ReAct 循环 + 自检重试
│   ├── intent.py              # 意图分类器（6 意图 + 4 情绪）
│   ├── audio.py               # 语音接口（预留 ASR/TTS）
│   ├── routes.py              # API 路由（29+ 端点）
│   ├── models.py              # 数据模型 + YAML 角色加载（917 行）
│   ├── prompts/               # 12 个 Agent Prompt 文件
│   └── roles/                 # 7 个 YAML 角色定义
│
├── site_builder/              # LLM 一键建站
│   ├── engine.py / routes.py  # 建站引擎
│   ├── generators/            # 分步生成器（brand/theme/navigation/pages）
│   ├── prompts/               # 4 个行业模板
│   ├── site_settings/         # 统一设计令牌
│   ├── mini_app/              # 小程序生成器
│   └── i18n/                  # 建站模块翻译
│
├── orchestrator/              # DAG 工作流引擎（11 个 .py）
│   ├── workflow_engine.py     # 引擎核心
│   ├── nodes.py               # 12 种节点类型
│   ├── trigger_dispatch.py    # 触发器分发
│   ├── workflow_templates.py  # 工作流模板
│   └── ...
│
├── cognition-service/         # 认知服务（FastAPI）
│   ├── server.py              # 服务入口
│   ├── routes/                # agents/maps/predictions/search/settlements
│   ├── services/              # embedding/map/price/reputation/settlement/validator
│   └── db/schema.sql          # 数据库 Schema
│
├── health_service/            # 健康守护进程
│   ├── runner.py              # 运行器
│   └── app.py                 # 健康检查应用
│
├── providers/                 # 第三方服务抽象层
│   ├── logistics/             # Shippo 物流
│   ├── payment/               # Stripe/PayPal
│   ├── sms/                   # 阿里云/Twilio 短信
│   └── social/                # LinkedIn/Twitter 社交
│
├── plugins/                   # 24 个插件
├── plugin_manager/            # 插件管理引擎（18 个 .py）
├── themes/                    # 5 个主题
├── i18n/                      # 国际化翻译
├── data/                      # 运行时数据
├── docs/                      # 项目文档
├── scripts/                   # 运维脚本
├── deploy/                    # 部署配置
└── docker-compose.yml         # Docker 编排
```

---

## 五、快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 14+
- Redis（可选）
- OpenAI / DeepSeek / DashScope API Key（Agent 矩阵功能）

### 安装

```bash
git clone https://github.com/fanjumin/VeroRunSystem.git verorun
cd verorun

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 .\venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 PG_HOST/PG_PASSWORD 等
```

### 启动

```bash
# ① 站点后端（端口 8081）
cd site && python app.py 8081 &

# ② 用户控制台（端口 8083）
cd ../platform && python app.py 8083 &

# ③ 管理后台（端口 8084）
cd ../admin && python app.py 8084 &

# ④ AI 社区（独立端口）
cd ../community && python app.py &

# ⑤ 认知服务
cd ../cognition-service && python server.py &
```

### Docker 部署

```bash
docker-compose up -d
```

### 访问

| 服务 | 地址 | 用途 |
|------|------|------|
| 官网 | `http://localhost:8081` | 主站页面 / 登录 / 订阅 |
| 用户控制台 | `http://localhost:8083` | 商城 / CMS / 用户中心 |
| 管理后台 | `http://localhost:8084/admin` | Agent 矩阵 / 商品管理 / 插件管理 |

---

## 六、开发指南

### 新增一个 Sub Agent 角色

1. 创建 YAML 角色定义：`agent_matrix/roles/XX-rolename.yaml`
2. 创建 Prompt 文件：`agent_matrix/prompts/sub_xxx_prompt.md`
3. 在 `agent_matrix/models.py` 的 `_load_all_role_yamls()` 中自动发现
4. 可选：在 `orchestrator.py` 中添加关键词路由
5. 可选：在管理后台配置 Agent 的供应商/模型/工具白名单

### 新增一个工具

1. 在 `agent_matrix/tools.py` 的 `TOOL_SCHEMAS` 中添加 schema
2. 在 `TOOL_EXECUTORS` 中绑定执行函数
3. 在对应 Agent 角色 YAML 的 `allowed_tools` 中声明

### 新增一个插件

1. 创建 `plugins/<name>/__init__.py`（继承 `BasePlugin`）
2. 创建 `plugins/<name>/plugin.json` 填写元数据
3. 在 `on_install()` 中调用 `init_db()` 创建自有数据库
4. 通过 `event_bus.on()` 订阅事件

### 代码规范

- Python：PEP8
- 路由：Flask Blueprint，前缀明确
- 数据库：主库 `auth-center/models/database.py` 统一管理；插件使用自有 `.db` 文件
- 翻译：统一使用 `_()`，插件使用 `self.t()`，建站模块独立 i18n
- 插件隔离：每个插件独立 SQLite 数据库，卸载时自动删除 `.db`，零残留

---

## 七、部署

### 生产环境

- 服务器：***REMOVED***
- 反向代理：Nginx（SSL 终端）
- 数据库：PostgreSQL 14（多 Schema）
- 进程管理：systemd / Gunicorn
- 容器化：Docker + docker-compose

### 关键环境变量

| 变量 | 说明 |
|------|------|
| `PG_HOST` / `PG_PORT` / `PG_DB` / `PG_USER` / `PG_PASSWORD` | PostgreSQL 连接 |
| `FLASK_SECRET_KEY` | Flask 密钥 |
| `JWT_SECRET` | JWT 签名密钥 |
| `DEPLOY_DOMAIN` | 部署域名 |
| `DEPLOY_MARKET` | 市场（cn/intl） |
| `DASHSCOPE_TEXT_KEY` | 阿里通义 API Key |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `OPENAI_API_KEY` | OpenAI API Key |
| `SILICONFLOW_API_KEY` | 硅基流动 API Key |
| `NGINX_SNIPPETS_DIR` | Site Domains 子域名 Nginx 配置目录 |

---

> **VeroRun v0.32.2** — Multi-Agent AI Operating System  
> 多智能体驱动的 AI 内容与商业枢纽  
> © 2026 VeroRunSystem