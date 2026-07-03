# VeroRunSystem

**Multi-Agent AI Operating System** — 多智能体驱动的 AI 内容与商业枢纽

VeroRunSystem 是一个基于 **13 个 AI Agent 协作矩阵** 的全栈 SaaS 建站与商业管理平台，集成了智能建站、商城运营、内容管理、AI 客服、阿里巴巴供应链、自动化工作流、云服务开通等能力。

> 仓库：`https://github.com/fanjumin/VeroRunSystem`

---

## 一、系统架构

### 服务拓扑

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    Site     │    │  Platform   │    │   Admin     │    │   Captcha   │
│   :8081     │    │   :8083     │    │   :8084     │    │   :8090     │
│ 主站后端    │    │ 前台门户    │    │ 管理后台    │    │ 验证码服务  │
│ OAuth/用户  │    │ 商城前端    │    │ Agent矩阵   │    │             │
│             │    │ CMS展示     │    │ 1688管理    │    │             │
│             │    │ 登录/定价   │    │ 订阅/支付   │    │             │
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

### 13 个子系统一览

| # | 子系统 | 位置 | 职责 |
|---|--------|------|------|
| 1 | **Agent 矩阵** | `agent_matrix/` | 13 Agent 协作引擎 |
| 2 | **商城模块** | `auth-center/routes/shop_admin.py` + `platform/routes/shop_public.py` | 商品、订单、购物车、支付 |
| 3 | **阿里巴巴对接** | `ali_api/` | 1688 商品采集、发布 |
| 4 | **CMS 内容管理** | `auth-center/routes/cms_admin.py` + `auth-center/models/cms.py` | 文章、页面块、分类 |
| 5 | **工作流引擎** | `orchestrator/` | DAG 自动化、Cron 调度 |
| 6 | **云服务开通** | `cloud_provisioner/` | 云资源自动部署 |
| 7 | **认证中心** | `auth-center/` | JWT SSO、用户、OAuth |
| 8 | **支付订阅** | `auth-center/routes/payment.py` + `subscription/` | 支付宝/微信支付 |
| 9 | **主题系统** | `themes/` | 5 个主题 + 模板覆盖 |
| 10 | **验证码服务** | `captcha-service/` | 行为验证码 |
| 11 | **分析系统** | `analytics/` | 访客追踪、聚合 |
| 12 | **社交推送** | `auth-center/services/social_push/` | 多平台内容分发 |
| 13 | **内容工厂** | `auth-center/services/content_factory/` | RSS 采集、AI 内容生成 |

---

## 二、核心模块详解

### 2.1 Agent 矩阵系统（核心创新）

位置：`agent_matrix/`

这是本系统最核心的组件 — 一个 **1 + 12 的多智能体协作矩阵**。

#### 架构

```
用户指令
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  Master Agent (Athena)       模型: GPT-4o            │
│  • 理解用户意图 → 任务分解 → 指派子Agent              │
│  • 汇总子Agent结果 → 格式化报告                       │
└───────────────────────┬──────────────────────────────┘
                        │
          Orchestrator  │  并行下发
                        │
    ┌────────┬────────┬──┴──┬────────┬────────┐
    ▼        ▼        ▼     ▼        ▼        ▼
 ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐
 │ Shop │ │ CMS  │ │Finance│ │User  │ │Community│ │Automation│
 │Agent │ │Agent │ │Agent │ │Agent │ │Agent   │ │Agent     │
 ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├───────┤ ├──────────┤
 │Kai   │ │Image │ │Voice │ │Video │ │Ticket │ │Analytics │
 │Chat  │ │Agent │ │Agent │ │Agent │ │Agent  │ │Agent     │
 └──────┘ └──────┘ └──────┘ └──────┘ └───────┘ └──────────┘
```

#### AI 供应商

支持 5 个 AI 供应商，按优先级配置：

| 供应商 | 用途 | 典型模型 |
|--------|------|----------|
| **DashScope** (阿里通义) | 主推理 + 图像生成 | qwen-plus, wan2.7-image |
| **OpenAI** | 主控 Agent | gpt-4o |
| **DeepSeek** | 子 Agent 推理 | deepseek-chat |
| **OpenRouter** | 备用供应商 | 多模型 |
| **Ollama** | 本地推理 | 本地私有部署 |

#### 13 个 Agent 职责

| Agent | 角色 | 模型 | 核心能力 |
|-------|------|------|----------|
| **Athena (Master)** | 主控协调 | GPT-4o | 任务分解 → 指派子Agent → 汇总结果 → 自检质量 |
| **Shop Agent** | 商城运营 | deepseek-chat | 商品管理、订单处理、SKU、AI 标题/描述优化 |
| **Supply Chain Agent** | 供应链管理 | deepseek-chat | 1688 商品采集、AI 优化、本地商城发布 |
| **CMS Agent** | 内容管理 | deepseek-chat | 文章撰写、排版、配图生成、评论审核 |
| **Finance Agent** | 财务管理 | deepseek-chat | 套餐、订阅、订单、收入统计 |
| **User System Agent** | 系统管理 | deepseek-chat | 用户、API Key、系统配置 |
| **Community Agent** | 社区运营 | deepseek-chat | 社区互动、邮件、短信推送 |
| **Automation Agent** | 自动化 | deepseek-chat | Cron 任务配置、Workflow 编排 |
| **Analytics Agent** | 数据分析 | deepseek-chat | 统计报告、趋势分析 |
| **Ticket Agent** | 客服工单 | deepseek-chat | 工单管理、客户服务 |
| **Kai Assistant (Chatbot)** | 智能客服 | deepseek-chat | 全站 FAQ、多轮对话、问题分类 |
| **Image Agent** | 图像生成 | wan2.7-image | 文生图、商品配图 |
| **Voice Agent** | 语音合成 | volc-voice-clone-v2 | 声音克隆、TTS |
| **Video Agent** | 视频生成 | volc-avatar-v3 | 数字人口播视频 |

#### 工作流程

1. **接收**：用户通过管理面板输入指令
2. **分解**：Athena（GPT-4o）将任务分解为子任务列表（同时使用关键词模板 Fallback）
3. **调度**：Orchestrator 根据子任务类型分配到对应 Sub Agent
4. **执行**：各 Sub Agent（DeepSeek）并行执行，调用各自 API/工具
5. **自检**：每 Agent 输出后自我评分（0-1），低置信度（<0.7）自动重试
6. **汇总**：Athena 收集所有结果，整合为结构化报告返回用户

#### 技术亮点

- **智能任务分解**：先尝试 AI 分解（GPT-4o），失败或超时则 Fallback 到关键词模板
- **自检重试**：Agent 输出附带置信度评分，`self_critique_score < 0.7` 自动重试（最多 3 次）
- **多供应商路由**：每个 Agent 可单独配置供应商和模型
- **Token 审计**：完整记录每次调用的 token 消耗，支持每日汇总

---

### 2.2 商城模块（Shop）

后台管理：`auth-center/routes/shop_admin.py`（前缀 `/shop`）  
前端 API：`platform/routes/shop_public.py`（前缀 `/shop`）  
支付服务：`auth-center/services/payment_service.py`

#### 功能矩阵

| 功能 | 后台管理 | 前端 API | 说明 |
|------|----------|----------|------|
| **商品管理** | CRUD + 多图（上传/排序/删除） | 商品列表/详情/搜索 | 支持 AI 优化标题/描述 |
| **SKU 管理** | 规格组 → 笛卡尔积生成 SKU | 前端按规格选择 | 自动生成 sku_code |
| **分类管理** | 无限级分类 | 分类筛选 | 树形结构 |
| **购物车** | — | 增/删/改/查 | 有效期 30 天 |
| **订单管理** | 发货/退款/物流 | 下单/取消/确认收货 | 幂等性 + 限流 |
| **优惠券** | 创建/发放/核销/统计 | 下单时使用 | 满减/折扣 |
| **支付** | — | 支付宝/微信 | RSA2 签名 + 桩模式 |
| **物流** | — | 快递鸟查询 | kdniao_service.py |
| **AI 优化** | 标题多版本/描述优化/卖点/标签 | — | 集成 DeepSeek |
| **云服务开通** | 订单确认 → Docker 容器创建 | — | cloud_provisioner |

#### 支付系统

采用支付宝电脑网站支付，关键设计：

```
订单创建 → 调起支付宝（GET URL 跳转）
                ↓
         用户扫码支付
                ↓
    异步通知 → verify_notify() 签名验证
                ↓
    confirm_shop_order() 更新订单状态 + 创建购买记录
```

- **安全**：RSA2 签名验证，通知域名从 DB 动态读取
- **桩模式**：未配置支付宝时自动降级为桩模式，标注 `stub_auto_confirm`
- **配置**：DB `system_config` → 环境变量 → 桩模式，三层降级

---

### 2.3 阿里巴巴/1688 对接模块

位置：`ali_api/`

完整的 1688 开放平台集成，从商品采集到本地商城发布的一条龙服务。

#### 功能模块

```
┌──────────────────────────────────────────────────────┐
│                  阿里 API 管理                         │
├──────────────────────────────────────────────────────┤
│  ① 商品采集         搜索 / 分类浏览 / 批量采集        │
│  ② AI 标题优化      多版本生成 / 选择最佳 / 描述重写  │
│  ③ 本地商城发布     同步到 products 表 + SKU          │
│  ④ OAuth 授权管理   URL 生成 / 回调 / 刷新 / 解除     │
│  ⑤ 风控系统         频率限制 / 并发控制 / 配额管理    │
│  ⑥ 缓存服务         Redis + 内存二级缓存               │
│  ⑦ 日志审计         API 调用日志 / 统计               │
│  ⑧ 图片管理         上传 / 删除 / 排序                │
└──────────────────────────────────────────────────────┘
```

#### 技术实现

- **API 网关**：`alibaba.product.get`、`alibaba.product.search` 等标准接口
- **签名**：HMAC-SHA1 + Base64
- **重试**：指数退避（最大 3 次）
- **OAuth**：1688 标准授权码模式，state 持久化防 CSRF + 防重放
- **AI 处理器**：DeepSeek 生成营销文案、标题选项
- **发布**：数据写入 `products` + `product_skus` 表，支持 `ali_source` 标记

---

### 2.4 CMS 内容管理系统

模型定义：`auth-center/models/cms.py`  
管理路由：`auth-center/routes/cms_admin.py`

#### 数据库表

| 表名 | 用途 | 核心字段 |
|------|------|----------|
| `cms_blocks` | 页面块管理 | page, section, block_type, position, content, image_url, extra_json |
| `cms_categories` | 文章分类 | name, slug, audience (public/internal), sort_order |
| `cms_posts` | 文章 | slug, category, title, content, tags, is_published, publish_channels |
| `cms_settings` | 站点设置 | key-value |
| `downloads` | 下载资源 | slug, name, version, platforms, tags, download_count |

#### 页面块系统

CMS 的核心是 **Block 页面构建器** — 每个页面由多个 Block 组成，支持：

- **拖拽排序**：前端拖拽 → `reorder_blocks()` 更新 position
- **多种类型**：text / hero / features / gallery / cta / contact 等
- **额外数据**：`extra_json` 字段存储任意结构化数据
- **发布控制**：每个 block 独立 `is_published` 状态

#### 社交发布

文章发布时支持一键分发到多平台：
- **本地**：发布到 `cms_posts` 表
- **社交**：微博、微信、今日头条、抖音等（`social_push.py`）

---

### 2.5 工作流引擎（Orchestrator）

位置：`orchestrator/`

轻量级 DAG 工作流引擎，用于自动化任务编排。

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

#### 节点类型（10 种）

| 节点类型 | 用途 | 说明 |
|----------|------|------|
| `ai_agent` | AI Agent 任务 | 调用 Agent 矩阵 |
| `data_collect` | 数据采集 | RSS/API 数据拉取 |
| `ai_process` | AI 处理 | 内容分析/生成 |
| `condition` | 条件分支 | 表达式评估 |
| `approval` | 人工审批 | 暂停等待审批 |
| `publish` | 内容发布 | 文章/商品发布 |
| `notify` | 通知 | 邮件/短信/站内信 |
| `wait` | 等待 | 定时延迟 |
| `http_request` | HTTP 调用 | 外部 API 请求 |
| `script` | 脚本执行 | 安全沙箱执行 |
| `sub_workflow` | 子工作流 | 嵌套执行 |
| `market_check` | 行情检查 | 金融数据监控 |

#### 架构

```
Cron Scheduler ──→ Workflow Engine ──→ Worker Pool
       │                                      │
  定时触发                             并发执行节点
```

---

### 2.6 云服务自动开通（Cloud Provisioner）

位置：`cloud_provisioner/`

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

#### Provider 抽象

```
Provider (抽象基类)
  └── TemplateProvider    — 模板化输出（开发/测试）
  └── AliyunProvider      — 阿里云 API 对接（预留）
```

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
- 支持支付宝 OAuth 登录

#### 支付网关

| 网关 | 文件 | 方法 |
|------|------|------|
| 支付宝 | `payment_service.py` | RSA2 签名、`alipay.trade.page.pay` |
| 支付宝(订阅) | `routes/subscription/gateway/alipay.py` | 参数签名 |
| 微信支付 | `routes/subscription/gateway/wechat.py` | 对象签名 |

---

### 2.8 主题系统

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

采用 Jinja2 `ChoiceLoader` 实现模板覆盖：

```python
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(theme_tpl_dir),     # 优先：激活主题的 templates/
    app.jinja_loader,                    # 回退：默认模板
])
```

主题支持：
- 模板覆盖（`templates/` 下同名文件）
- 自定义 CSS（`theme.css` 注入）
- 静态文件服务（`/themes/<slug>/`）

---

### 2.9 广告管理（Ad Placements）

位置：`auth-center/routes/admin.py`（`# ── 广告管理 (Ad Placements) ──`）

后台"运营支撑"菜单下的广告管理模块，支持在指定页面位置投放广告。

| 功能 | 说明 |
|------|------|
| **广告位 CRUD** | 名称、页面、位置、类型、图片/代码、宽高、排序、启禁 |
| **广告类型** | 图片广告（image）和广告代码（code，如 Google AdSense） |
| **页面定位** | 可指定广告投放的页面（`*` 表示全站） |
| **位置设置** | 支持侧边栏（sidebar）、头部、底部等多种位置 |
| **排序控制** | `sort_order` 字段控制显示顺序 |

数据库表 `ad_placements`（字段：name, position, page, ad_type, image_url, link_url, ad_code, width, height, is_active, sort_order）。

---

### 2.10 其他服务

#### 验证码服务（captcha-service）

独立服务（端口 8090），通过 Platform/Admin 反向代理接入：

```
用户请求 → Platform:8083 → /api/captcha/* → Captcha:8090
```

支持接口：
- `/api/captcha/generate` — 生成拼图验证码
- `/api/captcha/verify` — 验证
- `/api/captcha/consume` — 消耗（限流保护）

#### 分析系统（analytics）

- 中间件：自动记录访问日志（路径、IP、UA、耗时）
- 处理器：每 60 秒聚合一次原始日志
- 仪表板：管理后台查看统计

#### 社交推送（social_push）

支持多平台内容分发：
- 微博 API
- 微信公众号
- 今日头条
- 抖音小程序

#### 内容工厂（content_factory）

- RSS 采集器：自动采集外部内容
- AI 处理器：对采集内容进行 AI 改写
- 技能推送器：将内容推送到指定渠道

---

## 三、技术栈

### 后端

| 技术 | 用途 |
|------|------|
| **Python 3** | 主要开发语言 |
| **Flask** | Web 框架（3 个独立服务实例） |
| **SQLite** | 数据库（单文件 `data/easykai.db`） |
| **Jinja2** | 模板引擎 |
| **JWT** | SSO 单点登录 |
| **APScheduler** | 定时任务调度 |
| **cryptography** | RSA2 签名（支付宝） |

### AI 能力

| 能力 | 供应商/模型 |
|------|------------|
| 主控推理 | OpenAI GPT-4o |
| 子 Agent 推理 | DeepSeek Chat |
| 图像生成 | 通义万相 wan2.7-image |
| 声音克隆 | 火山引擎 volc-voice-clone-v2 |
| 数字人视频 | 火山引擎 volc-avatar-v3 |
| 备用供应商 | OpenRouter, Ollama |

### 第三方集成

| 服务 | 用途 |
|------|------|
| 1688 开放平台 | 商品数据采集 |
| 支付宝 | 在线支付 |
| 微信支付 | 在线支付 |
| 快递鸟 | 物流查询 |
| 微博/微信/头条 | 社交内容分发 |
| 火山引擎 | 语音/视频生成 |

### 前端

| 技术 | 用途 |
|------|------|
| **Vanilla JS** | SPA 前端 |
| **Unpkg / CDN** | 第三方库 |
| **CSS Custom Properties** | 主题系统 |
| **AdminLTE** | 管理面板 UI |

---

## 四、项目结构

```
VeroRunSystem/
├── admin/                     # 管理后台 (Flask, 端口 8084)
│   ├── app.py                 # 入口 → 注册所有 admin 蓝图
│   ├── routes/                # 管理后台路由
│   ├── templates/             # 管理后台模板
│   └── static/                # 静态资源
│
├── platform/                  # 前端门户 (Flask, 端口 8083)
│   ├── app.py                 # 入口 → CMS + 商城前端 + 登录
│   ├── routes/                # 前端路由
│   │   ├── shop_public.py     # 商城前端 API
│   │   ├── api_v1.py          # 通用 API
│   │   └── site_routes.py     # 站点页面路由
│   ├── templates/             # 前端模板 (~38 个 HTML)
│   └── static/                # 静态资源
│
├── auth-center/               # 认证中心 + 业务核心
│   ├── auth_blueprint.py      # 蓝图注册
│   ├── models/                # 数据模型
│   │   ├── database.py        # 数据库连接
│   │   ├── cms.py             # CMS 模型
│   │   └── __init__.py        # models 包
│   ├── routes/                # 所有业务路由
│   │   ├── auth.py            # 登录/注册/OAuth
│   │   ├── admin.py           # 管理路由
│   │   ├── shop_admin.py      # 商城管理
│   │   ├── payment.py         # 支付
│   │   ├── agents.py          # Agent 路由
│   │   ├── cms_admin.py       # CMS 管理
│   │   ├── agents.py          # 智能体路由
│   │   ├── subscription/      # 订阅模块
│   │   │   ├── renewal.py
│   │   │   └── gateway/
│   │   │       ├── alipay.py
│   │   │       └── wechat.py
│   │   └── ...                # 其他路由文件
│   └── services/              # 服务层
│       ├── payment_service.py # 支付服务
│       ├── alipay_service.py  # 支付宝服务
│       ├── agent_engine.py    # Agent 引擎
│       ├── kdniao_service.py  # 快递鸟
│       └── ...                # 其他服务
│
├── agent_matrix/              # Agent 矩阵系统
│   ├── engine.py              # AI 引擎核心
│   ├── orchestrator.py        # 任务编排
│   ├── agent_runner.py        # Agent 执行器
│   ├── routes.py              # API 路由
│   ├── models.py              # 数据模型 + 种子数据
│   └── prompts/               # 13 个 Agent Prompt
│       ├── master_prompt.md
│       ├── sub_shop_prompt.md
│       ├── sub_cms_prompt.md
│       └── ... (13 个 .md 文件)
│
├── ali_api/                   # 阿里巴巴/1688 对接
│   ├── config.py              # 配置
│   ├── models.py              # 数据模型
│   ├── routes/admin.py        # 管理界面路由
│   └── services/
│       ├── alibaba_client.py  # API 客户端
│       ├── alibaba_client_v2.py # 新版 API
│       ├── ai_processor.py    # AI 处理器
│       ├── rate_limiter.py    # 风控限流
│       └── cache_service.py   # 缓存服务
│
├── orchestrator/              # DAG 工作流引擎
│   ├── workflow_engine.py     # 引擎核心
│   ├── nodes.py               # 节点定义
│   ├── scheduler.py           # Cron 调度
│   ├── worker.py              # Worker 池
│   ├── routes.py              # API 路由
│   └── models.py              # 数据模型
│
├── cloud_provisioner/         # 云服务自动开通
│   ├── engine.py              # 编排引擎
│   ├── routes.py              # API 路由
│   ├── models.py              # 数据模型
│   └── providers/             # Provider 适配器
│       ├── base.py
│       └── template.py
│
├── captcha-service/           # 验证码服务 (端口 8090)
│
├── analytics/                 # 分析系统
│   ├── middleware.py          # 请求日志中间件
│   ├── processor.py           # 聚合处理器
│   └── dashboard.py           # 仪表板蓝图
│
├── themes/                    # 主题系统
│   ├── default/
│   ├── light/
│   ├── nature/
│   ├── ocean/
│   └── warm/
│
├── static/                    # 全局静态资源
├── templates/                 # 全局模板
├── data/                      # SQL 种子数据
├── docs/                      # 项目文档
├── scripts/                   # 运维脚本
├── tools/                     # 工具脚本
├── images/                    # 图片资源
├── prompts/                   # AI 公共 Prompt
├── PLANS/                     # 开发计划
└── .trae/                     # Trae IDE 配置
```

---

## 五、快速开始

### 环境要求

- Python 3.9+
- pip / venv
- SQLite (内置)

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

### 启动服务

```bash
# 启动验证码服务（端口 8090）
cd captcha-service
python app.py &

# 启动管理后台（端口 8084）
cd ../admin
python app.py 8084 &

# 启动前端门户（端口 8083）
cd ../platform
python app.py 8083 &
```

访问：
- 前端门户：`http://localhost:8083`
- 管理后台：`http://localhost:8084/admin`

---

## 六、开发指南

### 新增一个 Sub Agent

1. 创建 Prompt 文件：`agent_matrix/prompts/sub_<name>_prompt.md`
2. 在 `agent_matrix/models.py` 的 `seed_agents()` 中添加种子数据
3. 在 `engine.py` 的 `AGENT_MODEL_MAP` 中注册模型
4. （可选）注册 AI 供应商到 `SUPPLIER_REGISTRY`

### 新增主题

1. 创建主题目录：`themes/<slug>/`
2. 添加模板覆盖：`themes/<slug>/templates/`
3. 添加 CSS 文件：`themes/<slug>/theme.css`
4. 在管理后台主题管理中选择激活

### 代码规范

- Python：遵循 PEP8
- 路由：Flask Blueprint 组织，前缀明确
- 服务层：`auth-center/services/` 下按职责拆分
- 数据库：SQLite，models 层统一管理表结构

---

## 七、部署

### 部署架构

```
Nginx (反向代理 + SSL)  服务器: ***REMOVED***
    │
    ├── easykai.cn / www.easykai.cn (/)        ──→ Site:8081
    ├── easykai.cn /admin/                      ──→ Admin:8084
    ├── easykai.cn /auth/ /subscribe            ──→ Auth:8083
    ├── easykai.cn /auth/oauth/ /user/          ──→ Site:8081
    ├── platform.easykai.cn                     ──→ Platform:8083
    └── agent.easykai.cn (admin)                ──→ Admin:8084
```

### 关键环境变量

| 变量 | 说明 |
|------|------|
| `FLASK_SECRET_KEY` | Flask 密钥 |
| `JWT_SECRET` | JWT 签名密钥 |
| `DEPLOY_DOMAIN` | 部署域名 |
| `NOTIFY_BASE` | 支付回调域名 |
| `ALIPAY_APP_ID` | 支付宝 AppID |
| `DASHSCOPE_API_KEY` | 阿里通义 API Key |
| `OPENAI_API_KEY` | OpenAI API Key |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |

### rsync 同步

```bash
rsync -av --delete --exclude='.git' --exclude='__pycache__' --exclude='venv' \
  ./ easykai@server:/home/easykai/easykai-workspace/easykai.cn/
```

---

## 八、贡献指南

1. 遵循 AGENTS.md 铁律：先方案后执行，最小改动，禁止自作主张
2. 提交前确保无未提交代码
3. 逻辑独立的小改动（≤3 文件）主动提醒审查提交
4. 禁止创建独立数据库、独立配置文件
5. 所有修改必须在本地完成，通过 rsync 同步到服务器

---

> VeroRunSystem v0.9.3 — Multi-Agent AI Operating System  
> 多智能体驱动的 AI 内容与商业枢纽  
> © 2026 VeroRunSystem 版权所有
