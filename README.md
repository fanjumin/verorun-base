# VeroRunSystem

**Multi-Agent AI Operating System** — 多智能体驱动的 AI 内容与商业枢纽

VeroRunSystem 是一个基于 **13 个 AI Agent 协作矩阵** 的全栈 SaaS 建站与商业管理平台，集成了智能建站、商城运营、CMS 内容管理、AI 客服、自动化工作流、云服务开通、分析统计、系统健康巡检等能力。

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
│ 订阅        │    │ CMS展示     │    │ 智能体     │    │             │
│ 官网页面    │    │ 登录/定价   │    │ 订阅/支付   │    │             │
│             │    │ 用户中心    │    │ 云服务/分析 │    │             │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                   │                   │                   │
       └───────────────────┼───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │   SQLite    │
                    │  easykai.db │
                    └─────────────┘
```

### 15 个子系统一览

| # | 子系统 | 位置 | 职责 |
|---|--------|------|------|
| 1 | **Agent 矩阵** | `agent_matrix/` | 13 Agent 协作引擎 — 任务分解/调度/执行/汇总 |
| 2 | **商城模块** | `auth-center/routes/shop_admin.py` + `platform/routes/shop_public.py` | 商品、SKU、订单、购物车、优惠券、AI 优化 |
| 3 | **CMS 内容管理** | `auth-center/routes/cms_admin.py` + `auth-center/models/cms.py` | 文章、页面块、分类、下载管理 |
| 4 | **工作流引擎** | `orchestrator/` | DAG 工作流编排、Cron 调度、12 种节点 |
| 5 | **云服务开通** | `cloud_provisioner/` | VPS/OSS/CDN/RDS 自动部署与销毁 |
| 6 | **数据清洗** | `auth-center/routes/cleaner_agent.py` | 原始内容 → LLM 清洗 → 知识库 |
| 7 | **认证中心** | `auth-center/` | JWT SSO、用户、OAuth、企业认证 |
| 8 | **支付订阅** | `auth-center/routes/subscription/` | 支付宝/微信/Stripe/PayPal 订阅支付 |
| 9 | **主题系统** | `themes/` | 5 个主题 + Jinja2 ChoiceLoader 模板覆盖 |
| 10 | **健康检查** | `health_check/` | 服务探活、异常诊断、AI 自动修复 |
| 11 | **验证码服务** | `captcha-service/` | 拼图行为验证码（独立服务 8090） |
| 12 | **分析系统** | `analytics/` | 访客追踪、IP 地理定位、UA 解析 |
| 13 | **社交分发** | `auth-center/routes/social_push.py` | 微博/微信/头条/抖音 内容分发 |
| 14 | **内容工厂** | `auth-center/services/content_factory/` | RSS 采集 → AI 加工 → Skill 推送 |
| 15 | **插件系统** | `plugins/` | BasePlugin 框架 + 可选插件（1688 采集等） |

---

## 二、核心模块详解

### 2.1 Agent 矩阵系统（核心创新）

位置：`agent_matrix/`

这是本系统最核心的组件 — 一个 **1 个 Master Agent + 12 个 Sub Agent 的多智能体协作矩阵**，支持多供应商 AI、并行调度、自检重试、Token 审计。

#### 架构

```
用户指令
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│  Master Agent (Athena)        模型: GPT-4o                   │
│  • 理解用户意图 → 任务分解 → 指派子 Agent                    │
│  • 汇总子 Agent 结果 → 格式化报告                             │
│  • 关键词模板 Fallback（LLM 不可用时）                        │
└───────────────────────────────┬──────────────────────────────┘
                                │
                  Orchestrator  │  并行/串行调度
                                │
    ┌──────┬──────┬──────┬──────┼──────┬──────┬──────┐
    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼
 ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
 │Shop│ │CMS │ │Fina│ │User│ │Auto│ │Anal│ │Tick│ │Kai │
 │    │ │    │ │nce │ │    │ │mat │ │ytics│ │et  │ │Chat│
 ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤ ├────┤
 │Heal│ │Image│ │Voi │ │Vid │ │    │ │    │ │    │ │    │
 │th  │ │    │ │ce  │ │eo  │ │    │ │    │ │    │ │    │
 └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
```

#### AI 供应商

支持 7 个 AI/媒体供应商：

| 供应商 | 用途 | 典型模型 |
|--------|------|----------|
| **DashScope** (阿里通义) | 主推理 + 图像生成 | qwen-plus, wan2.7-image |
| **DeepSeek** | 子 Agent 推理 | deepseek-chat |
| **OpenAI** | 主控 Agent | gpt-4o |
| **Volcengine** (火山引擎) | 语音克隆 + 数字人视频 | volc-voice-clone-v2, volc-avatar-v3 |
| **SiliconFlow** (硅基流动) | 备用推理 | deepseek-ai/DeepSeek-V3 |
| **OpenRouter** | 备用供应商 | 多模型 |
| **Ollama** | 本地推理 | llama3 等 |

#### 13 个 Agent 职责

| Agent | 类型 | 默认模型 | domain | 核心能力 |
|-------|------|----------|--------|----------|
| **Athena** (Master) | master | GPT-4o | orchestration | 任务分解 → 指派子 Agent → 汇总报告 → 自检质量 |
| **Shop Agent** | sub | qwen-turbo | shop | 商品 CRUD、SKU/规格、订单、优惠券、AI 优化、云服务开通、数据清洗 |
| **CMS Agent** | sub | qwen-turbo | cms | 文章撰写/排版、评论审核、内容工厂对接 |
| **Finance Agent** | sub | qwen-turbo | finance | 套餐、订阅、订单、收入统计、扣款 |
| **User System Agent** | sub | qwen-turbo | system | 用户管理、API Key、系统配置、日志 |
| **Automation Agent** | sub | qwen-turbo | automation | Cron 任务、Workflow 编排、DAG 管理 |
| **Analytics Agent** | sub | qwen-turbo | analytics | 统计分析、数据解读、趋势报告 |
| **Ticket Agent** | sub | qwen-turbo | support | 工单管理、客户服务、AI 客服 |
| **Kai Assistant** | sub | deepseek-chat | chatbot | 全站 FAQ、多轮对话、飞书通知 |
| **Image Agent** | sub | wan2.7-image | image | 文生图、商品配图、社媒素材 |
| **Voice Agent** | sub | volc-voice-clone-v2 | voice | 声音克隆、文本转语音 |
| **Video Agent** | sub | volc-avatar-v3 | video | 照片驱动口播视频、抖音发布 |
| **Health Check Agent** | sub | qwen-turbo | health_check | 服务监控、异常诊断、告警、修复建议 |

#### 工作流程

1. **接收**：用户通过管理面板输入指令
2. **分解**：Athena（GPT-4o）将任务分解为子任务列表（LLM 失败时走关键词模板 Fallback）
3. **调度**：Orchestrator 根据子任务 domain 分配到对应 Sub Agent（支持并行下发）
4. **执行**：各 Sub Agent 并行执行，调用各自 API/工具
5. **自检**：每 Agent 输出后自我评分（0-1），低置信度（<0.7）自动重试（最多 3 次）
6. **汇总**：Athena 收集所有结果，整合为结构化报告返回用户

#### 技术亮点

- **智能任务分解**：先尝试 AI 分解（GPT-4o），失败或超时则 Fallback 到关键词模板
- **自检重试**：Agent 输出附带置信度评分，`self_critique_score < 0.7` 自动重试
- **多供应商路由**：每个 Agent 可单独配置供应商和模型（`provider_model_id`）
- **Token 审计**：完整记录每次调用的 token 消耗，支持每日汇总（`agent_token_logs` + `agent_token_daily`）
- **供应商切换**：管理后台支持 50+ 模型配置，随时切换

---

### 2.2 商城模块（Shop）

后台管理：`auth-center/routes/shop_admin.py`（前缀 `/shop`，19 个蓝图之一）  
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
| **云服务开通** | 订单确认 → 自动创建云实例 | — | 对接 cloud_provisioner |

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
                ↓
    (若为云服务商品) → 异步调用 ProvisionerEngine.provision()
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
接收原始内容 (知识/文章/商品数据)
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

位置：`orchestrator/`

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
| `data_collect` | 数据采集 | RSS/API 数据拉取（对接 content_factory） |
| `ai_process` | AI 加工 | 内容分析/改写（调用 DashScope） |
| `condition` | 条件分支 | 表达式评估 |
| `approval` | 人工审批 | 暂停等待审批 |
| `publish` | 内容发布 | 文章/商品发布到多平台 |
| `notify` | 通知 | 站内信/Webhook/邮件 |
| `wait` | 等待 | 定时延迟 |
| `http_request` | HTTP 调用 | 外部 API 请求 |
| `script` | 脚本执行 | 安全沙箱（safe_eval） |
| `sub_workflow` | 子工作流 | 嵌套执行 |
| `market_check` | 行情检查 | 腾讯行情 API / 模拟数据 |

#### 架构

```
Cron Scheduler ──→ Workflow Engine ──→ Worker Pool
       │                                      │
  定时触发                             并发执行节点
```

---

### 2.6 云服务自动开通（Cloud Provisioner）

位置：`cloud_provisioner/`

支持商品下单后自动创建云资源，当前支持 `vps` / `oss` / `cdn` / `rds` 四种服务类型。

#### 工作流程

```
下单支付 → 自动触发开通请求
                ↓
    ProvisionerEngine.provision()
                ↓
    ① 验证配置 (validate_config)
    ② 创建实例记录 (DB)
    ③ 选择 Provider 适配器
    ④ provider.provision() 创建资源
    ⑤ 轮询状态 (get_status)
    ⑥ 更新连接信息 (IP/端口/密钥)
    ⑦ 返回实例详情
```

#### API 端点

| 路由 | 方法 | 说明 |
|------|------|------|
| `/cloud/products` | GET | 云服务商品列表 |
| `/cloud/instances` | GET | 我的云资源 |
| `/cloud/instances/<iid>` | GET | 实例详情 |
| `/cloud/instances/provision` | POST | 手动开通（管理员） |
| `/cloud/instances/<iid>/terminate` | POST | 销毁实例 |

#### Provider 抽象

```
Provider (抽象基类)
  └── TemplateProvider    — 模板化输出（开发/测试）
  └── AliyunProvider      — 阿里云 API 对接（预留）
```

初始化脚本：`init_ubuntu.sh` / `init_centos.sh`（安装 Nginx/Python/Node.js/Docker）。

---

### 2.7 认证与支付系统

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

#### 服务层（auth-center/services/，32 个文件）

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

### 2.8 主题系统（Theme System）

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

### 2.9 系统健康检查（Health Check）

位置：`health_check/`

独立的系统健康监控模块，通过 Admin 后台自动加载，由 Agent 矩阵中的 **Health Check Agent** 调用。

#### 功能架构

```
┌─────────────────────────────────────────────┐
│              Health Check                    │
├─────────────────────────────────────────────┤
│  ① Service Discovery    端口探活 / 路由发现  │
│  ② Health Checkers      MySQL / HTTP / Ping  │
│  ③ Alerter              邮件 / Webhook 告警  │
│  ④ AI Fixer             自动诊断 + 修复建议  │
│  ⑤ Scheduler            定时巡检（APScheduler）│
└─────────────────────────────────────────────┘
```

---

### 2.10 插件系统（Plugin System）

位置：`plugins/`

标准化的插件框架，支持 i18n 隔离翻译、自动路由挂载、事件钩子。

#### 插件规范

```python
class AliApiPlugin(BasePlugin):
    def __init__(self):
        self.name = 'ali_api'
        self.version = '1.0.0'
        self.description = '1688/阿里巴巴商品采集'

    def t(self, text, locale=None):
        """插件自有翻译，从本插件 i18n/{locale}.yml 读取"""
        locale = locale or get_lang()
        return self._yaml.get(locale, {}).get(text, text)
```

#### 内置插件

| 插件 | 位置 | 说明 |
|------|------|------|
| **1688 采集** | `plugins/ali_api/` | 阿里巴巴商品采集 + AI 优化（可选安装） |

#### 目录结构规范

```
plugins/<name>/
├── __init__.py        # 插件类 (继承 BasePlugin)
├── plugin.json        # 元数据
├── i18n/              # 插件自有翻译（隔离于系统 _()）
│   ├── zh-CN.yml
│   └── en.yml
├── README.zh-CN.md
├── README.en.md
├── routes/            # Flask 蓝图（自动挂载 /plugin/<name>/）
├── services/          # 业务逻辑
├── static/            # 静态资源
└── templates/         # 模板
```

---

### 2.11 广告管理（Ad Placements）

位置：`auth-center/routes/admin.py`

后台"运营支撑"菜单下的广告管理模块。

| 功能 | 说明 |
|------|------|
| **广告位 CRUD** | name, position, page, ad_type, image_url/code, sort_order, is_active |
| **类型** | 图片广告（image）和广告代码（code，如 AdSense） |
| **页面定位** | 可指定页面（`*` 全站） |
| **位置** | 侧边栏、头部、底部等 |

---

### 2.12 国际化（i18n）

位置：`i18n/`

全域 i18n 支持，50+ 文件使用 `_()` 翻译函数。

- **存储方式**：YAML 文件 + DB 双存储
- **查找链**：YAML → DB → 原文（三阶降级）
- **语言包**：`zh-CN.yml` / `en.yml`
- **插件隔离**：插件使用 `self.t()`，不与系统 `_()` 冲突
- **静态语言**：通过 `DEPLOY_LANG` 环境变量决定

---

### 2.13 其他服务

#### 验证码服务（captcha-service）

独立服务（端口 8090），通过 Platform/Admin 反向代理接入：

```
用户请求 → Platform:8083 → /api/captcha/* → Captcha:8090
```

能力：拼图验证码生成 / 验证 / 消耗限流。

#### 分析系统（analytics）

- **中间件**：自动记录访问日志（路径、IP、UA、耗时）
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

#### 内容工厂（content_factory）

```
RSS/API 采集 → AI 加工（DashScope）→ Skill 推送
```

| 组件 | 文件 | 功能 |
|------|------|------|
| 基类采集器 | `base_collector.py` | HASH 去重、标题相似度检测、批量写入 |
| AI 处理器 | `ai_processor.py` | 调用通义千问提取/分析/改写 |
| Skill 推送器 | `skill_pusher.py` | 导出为 SKILL.md，推送到 Hermes/OpenClaw |

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
| **Flask** | Web 框架（4 个独立服务实例） |
| **SQLite** | 数据库（单文件 `data/easykai.db`） |
| **Jinja2** | 模板引擎 |
| **JWT** | SSO 单点登录 |
| **APScheduler** | 定时任务（工作流调度 + 健康检查 + 分析聚合） |
| **cryptography** | RSA2 签名（支付宝） |

### AI 能力

| 能力 | 供应商/模型 |
|------|------------|
| 主控推理 (Master) | OpenAI GPT-4o |
| 子 Agent 推理 | DashScope qwen-turbo / DeepSeek Chat |
| 图像生成 | 通义万相 wan2.7-image |
| 声音克隆 | 火山引擎 volc-voice-clone-v2 |
| 数字人视频 | 火山引擎 volc-avatar-v3 |
| 备用推理 | SiliconFlow / OpenRouter / Ollama |
| AI 引擎统一封装 | `agent_matrix/engine.py` → AIEngine |

### 第三方集成

| 服务 | 用途 |
|------|------|
| 支付宝 | 商城支付 + 订阅周期扣款 |
| 微信支付 | 订阅扫码支付 + 委托扣款 |
| Stripe | 订阅支付 (国际) |
| PayPal | 订阅支付 (国际) |
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
├── site/                      # 主站后端 (Flask, 端口 8081)
│   ├── app.py                 # 入口：auth/cms/shop/site 蓝图注册
│   └── templates/             # 站点模板
│
├── admin/                     # 管理后台 (Flask, 端口 8084)
│   ├── app.py                 # 入口：30+ 蓝图自动注册
│   ├── routes/                # 管理路由
│   ├── templates/             # 管理模板
│   └── static/                # 静态资源
│
├── platform/                  # 用户控制台 (Flask, 端口 8083)
│   ├── app.py                 # 入口：auth/cms/shop/API 注册
│   ├── routes/
│   │   ├── shop_public.py     # 商城前端 API
│   │   ├── api_v1.py          # 通用 API
│   │   └── site_routes.py     # 页面路由
│   ├── templates/             # 前端模板 (~38 个 HTML)
│   └── static/                # 静态资源
│
├── captcha-service/           # 验证码服务 (独立 Flask, 端口 8090)
│   ├── server.py              # 入口
│   ├── routes/captcha.py      # 验证码 API
│   └── captcha/               # 行为验证/生成/安全
│
├── auth-center/               # 认证中心 + 业务核心
│   ├── auth_blueprint.py      # 蓝图注册中心
│   ├── models/                # 数据模型
│   │   ├── database.py        # 数据库连接 + 全部建表 + 种子数据
│   │   └── cms.py             # CMS 模型
│   ├── routes/                # 18 个路由模块
│   │   ├── shop_admin.py      # 商城管理 (含 ShopAIProcessor)
│   │   ├── cleaner_agent.py   # 数据清洗
│   │   ├── agents.py          # Agent 管理
│   │   ├── admin.py           # 管理员路由 (含广告管理)
│   │   ├── auth.py            # 登录/注册/OAuth
│   │   ├── user.py            # 用户管理
│   │   ├── cms_admin.py       # CMS 管理
│   │   ├── comments.py        # 评论管理
│   │   ├── content_factory.py # 内容工厂
│   │   ├── sessions.py        # 会话管理
│   │   ├── social_push.py     # 社交推送
│   │   ├── social_media.py    # 社交媒体管理
│   │   ├── theme_admin.py     # 主题管理
│   │   ├── footer_admin.py    # 页脚管理
│   │   ├── header_admin.py    # 头部导航管理
│   │   ├── deployment_api.py  # 部署 API
│   │   ├── douyin_miniprogram.py # 抖音小程序
│   │   └── subscription/      # 订阅模块 (4 种支付网关)
│   │       ├── renewal.py
│   │       └── gateway/
│   │           ├── alipay.py
│   │           ├── wechat.py
│   │           ├── stripe.py
│   │           └── paypal.py
│   └── services/              # 32 个服务模块
│       ├── payment_service.py
│       ├── jwt_service.py
│       ├── agent_engine.py
│       ├── kdniao_service.py
│       ├── volcengine_client.py
│       ├── content_factory/   # 采集 → AI → 推送
│       └── ... (共 32 个 .py)
│
├── agent_matrix/              # Agent 矩阵系统
│   ├── engine.py              # AIEngine (7 供应商统一接口)
│   ├── orchestrator.py        # 任务编排 + 关键词路由
│   ├── agent_runner.py        # Agent 执行器 + 自检重试
│   ├── routes.py              # API 路由 (chat/execute/history)
│   ├── models.py              # 数据模型 + 13 Agent 种子数据
│   └── prompts/               # 14 个 Agent Prompt 文件
│       ├── master_prompt.md
│       ├── sub_shop_prompt.md
│       ├── sub_cms_prompt.md
│       ├── sub_health_check_prompt.md
│       └── ... (14 个 .md)
│
├── orchestrator/              # DAG 工作流引擎
│   ├── workflow_engine.py     # 引擎核心
│   ├── nodes.py               # 节点定义
│   ├── scheduler.py           # Cron 调度
│   ├── worker.py              # Worker 池
│   ├── safe_eval.py           # 安全沙箱
│   ├── routes.py              # API 路由
│   └── models.py              # 数据模型
│
├── cloud_provisioner/         # 云服务自动开通
│   ├── engine.py              # ProvisionerEngine
│   ├── routes.py              # /cloud/* API
│   ├── models.py              # 实例/日志模型
│   ├── providers/             # Provider 适配器
│   │   ├── base.py
│   │   └── template.py
│   └── scripts/               # 初始化脚本
│       ├── init_ubuntu.sh
│       └── init_centos.sh
│
├── health_check/              # 健康检查模块
│   ├── routes.py              # 蓝图
│   ├── models.py              # 检查记录模型
│   ├── checkers.py            # HTTP/Ping/MySQL 检查器
│   ├── discovery.py           # 服务发现
│   ├── alerter.py             # 邮件/Webhook 告警
│   ├── ai_fixer.py            # LLM 自动诊断修复
│   └── scheduler_setup.py     # 定时巡检
│
├── analytics/                 # 分析系统
│   ├── middleware.py          # 请求日志中间件
│   ├── processor.py           # 60 秒聚合处理器
│   ├── dashboard.py           # 仪表板蓝图
│   ├── models.py              # 数据模型
│   ├── tracker.py             # 跟踪模块
│   ├── geoip.py               # IP 地理定位
│   ├── ua_parser.py           # UA 解析
│   └── ip2region/             # IP 库
│
├── plugins/                   # 插件系统
│   ├── base.py                # BasePlugin 基类
│   ├── registry.py            # 插件注册表
│   ├── hooks.py               # 事件总线
│   ├── __init__.py            # 插件加载器
│   └── ali_api/               # 1688 采集插件（可选）
│       ├── i18n/{zh-CN,en}.yml
│       ├── services/ (5)
│       ├── routes/admin.py
│       ├── static/ali_console.js
│       └── templates/ali_admin/
│
├── themes/                    # 5 个主题
│   ├── default/               # 默认 / light/ / nature/ / ocean/ / warm/
│   └── <name>/theme.css + theme.json
│
├── i18n/                      # 国际化翻译
│   ├── zh-CN.yml
│   └── en.yml
│
├── static/                    # 全局静态资源
├── templates/                 # 全局模板
├── docs/                      # 项目文档
├── scripts/                   # 运维脚本
├── tools/                     # 工具脚本
├── PLANS/                     # 开发计划
└── .trae/                     # Trae IDE 配置
```

---

## 五、快速开始

### 环境要求

- Python 3.9+
- pip / venv
- SQLite (内置)
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
| 管理后台 | `http://localhost:8084/admin` | Agent 矩阵 / 商品管理 / 系统设置 |

---

## 六、开发指南

### 新增一个 Sub Agent

1. 创建 Prompt 文件：`agent_matrix/prompts/sub_<name>_prompt.md`
2. 在 `agent_matrix/models.py` 的 `DEFAULT_AGENTS` 中添加种子数据
3. 可选：在 `orchestrator.py` 的 `_template_decompose()` 中添加关键词路由
4. 可选：在管理后台单独配置 Agent 的供应商/模型

### 新增一个插件

1. 创建 `plugins/<name>/__init__.py`（继承 `BasePlugin`）
2. 创建 `plugins/<name>/plugin.json` 填写元数据
3. 添加翻译：`plugins/<name>/i18n/{locale}.yml`
4. 添加路由：`plugins/<name>/routes/`（自动挂载到 `/plugin/<name>/`）

### 新增主题

1. 创建目录：`themes/<slug>/`
2. 添加模板覆盖：`themes/<slug>/templates/`
3. 添加 CSS：`themes/<slug>/theme.css`
4. 在管理后台选择激活

### 代码规范

- Python：PEP8
- 路由：Flask Blueprint，前缀明确
- 数据库：统一在 `models/database.py` 管理建表
- 翻译：统一使用 `_()`，插件使用 `self.t()`
- 禁止：创建独立数据库 / 独立配置文件

---

## 七、部署

### 部署架构

```
Nginx (反向代理 + SSL)  服务器: ***REMOVED***
    │
    ├── easykai.cn (/)               ──→ Site:8081
    ├── easykai.cn /admin/           ──→ Admin:8084
    ├── easykai.cn /auth/ /subscribe ──→ Site:8081
    ├── platform.easykai.cn          ──→ Platform:8083
    └── agent.easykai.cn             ──→ Admin:8084
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

### rsync 同步

```bash
rsync -av --delete --exclude='.git' --exclude='__pycache__' --exclude='venv' \
  ./ easykai@server:/home/easykai/easykai-workspace/easykai.cn/
```

---

> VeroRunSystem v0.9.8 — Multi-Agent AI Operating System  
> 多智能体驱动的 AI 内容与商业枢纽  
> © 2026 VeroRunSystem 版权所有
