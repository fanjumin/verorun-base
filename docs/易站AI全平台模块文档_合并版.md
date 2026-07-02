# 易站AI 全平台模块文档（合并版）

> 易站智能建站系统（easykai.cn）完整模块文档  
> 合并日期：2026-06-28（修正版）

---

## 目录

1. [系统架构总览](#1-系统架构总览)
2. [Platform — 前端门户](#2-platform--前端门户)
3. [Admin — 管理后台](#3-admin--管理后台)
4. [Auth Center — 认证中心](#4-auth-center--认证中心)
5. [CMS — 内容管理系统](#5-cms--内容管理系统)
6. [Content Factory — 内容工厂](#6-content-factory--内容工厂)
7. [Knowledge — 知识库与数据清洗](#7-knowledge--知识库与数据清洗)
8. [Shop — 商城系统](#8-shop--商城系统)
9. [Alibaba Integration — 1688供应链对接](#9-alibaba-integration--1688供应链对接)
10. [Payment & Subscription — 支付与订阅](#10-payment--subscription--支付与订阅)
11. [Agent Matrix — AI矩阵编排](#11-agent-matrix--ai矩阵编排)
12. [Orchestrator — 自动化调度与工作流](#12-orchestrator--自动化调度与工作流)
13. [Cloud Provisioner — 云服务自动开通](#13-cloud-provisioner--云服务自动开通)
14. [Theme — 主题系统](#14-theme--主题系统)
15. [Captcha — 验证码服务](#15-captcha--验证码服务)

---

## 1. 系统架构总览

### 1.1 服务拓扑

| 服务 | 端口 | 域名 | 职责 |
|------|------|------|------|
| **Platform** | 8083 | easykai.cn | 前端用户门户（Flask + Jinja2） |
| **Admin** | 8084 | agent.easykai.cn | 管理后台 SPA（Flask + 前端JS模块） |
| **Auth-Center** | — | — | 不独立运行，以约18个 Blueprint 嵌入 Platform 和 Admin（认证/数据模型/AI引擎） |
| **Captcha** | 8090 | — | 独立验证码服务（FastAPI） |

### 1.2 数据存储

- **统一数据库**：`easykai.db`（SQLite），运行时自动创建于 auth-center 目录，由 auth-center 管理
- **共享层**：auth-center 以约18个 Blueprint 嵌入 Platform 和 Admin
- **JWT SSO**：HS256 JWT 跨子域单点登录（`.easykai.cn` domain cookie）

### 1.3 模块依赖关系

```
用户浏览器 → Platform(:8083) / Admin(:8084)
                  │
                  ├── Auth-Center Blueprints（认证/用户/支付/CMS管理/Agent...）
                  ├── Agent Matrix（AI引擎 + 13个Agent）
                  ├── Orchestrator（Cron调度 + DAG工作流）
                  ├── Content Factory（RSS采集 + AI加工）
                  ├── Knowledge & Cleaner（RAG检索 + 数据清洗，嵌入auth-center）
                  ├── Shop（电商，auth-center Blueprint + ali_api）
                  ├── Payment Gateway（支付宝/微信支付）
                  ├── Cloud Provisioner（云资源自动开通）
                  ├── Theme System（多租户主题管理）
                  └── Captcha Service(:8090)（行为验证码）
```

---

## 2. Platform — 前端门户

**端口**：8083 | **域名**：easykai.cn | **技术栈**：Flask + Jinja2 + SQLite

### 2.1 架构

```
用户请求 → Nginx → Platform Flask App
  ├── app.py（主入口：路由/中间件/上下文）
  ├── cms_public.py（CMS公开路由）
  ├── routes/site_routes.py（多租户站点路由）
  ├── routes/api_v1.py（REST API）
  ├── routes/shop_public.py（商城公开API）
  └── auth-center/（SSO认证 + 数据库模型）
```

### 2.2 路由地图

| 路由 | 功能 | 说明 |
|------|------|------|
| `/` | 首页 | CMS页面块渲染 |
| `/login` | 登录页 | 双栏布局 |
| `/register` | 注册页 | |
| `/reset-password` | 重置密码 | |
| `/pricing` | 定价页 | 数据库驱动 |
| `/subscribe` | 订阅页 | 需登录 |
| `/about` | 关于我们 | 品牌信息 |
| `/knowledge` | 知识中心 | 指南/AI技巧 |
| `/services` | 产品服务 | DB驱动服务卡片 |
| `/cases` | 客户案例 | |
| `/ai-matrix` | AI矩阵 | 渲染services.html（非重定向） |
| `/ai-experience` | AI体验 | 交互式Demo |
| `/start` | 快速开始 | |
| `/docs` | 文档首页 | |
| `/insights` | 产品动态 | |
| `/download` | 下载中心 | |
| `/shop` | 商城首页 | 商品列表 |
| `/shop/cart` | 购物车 | |
| `/shop/orders` | 订单列表 | 当前跳转到首页（待完善） |
| `/shop/cloud` | 云服务 | |
| `/chat-widget-embed` | 客服组件 | iframe嵌入 |
| `/preview/<slug>` | 文章预览 | 未发布需登录 |
| `/avatar/gen/<seed>` | 首字母头像 | SVG生成 |
| `/api/captcha/generate` | 验证码生成 | → captcha:8090 |
| `/api/captcha/verify` | 验证码校验 | → captcha:8090 |
| `/api/captcha/consume` | 验证码消费 | → captcha:8090 |
| `/api/social-links` | 旧表社媒链接 | JSON |
| `/api/social-media` | 新表社媒链接 | JSON |
| `/api/interests` | 兴趣标签 | 按分类分组 |
| `/api/feedback` | 投诉建议 | POST提交 |
| `/api/notifications/*` | 通知系统 | CRUD/未读计数 |
| `/api/pricing/calculator-config` | 价格计算器 | 配置JSON |
| `/api/video/homepage` | 首页视频 | JSON |

### 2.3 模板列表

核心模板位于 `platform/templates/`：
`public_home.html`（首页）, `about.html`, `services.html`, `subscribe.html`, `subscribe_portal.html`, `cases.html`, `ai_experience.html`, `start.html`, `knowledge.html`, `shop.html`, `shop_detail.html`, `cart.html`, `login.html`, `register.html`, `reset_password.html`, `calculator.html`, `admin.html`, `cms_page.html`, `cms_preview.html`, `cms_404.html`, `insights_list.html`, `insights_detail.html`, `docs_index.html`, `docs_list.html`, `docs_detail.html`, `download_list.html`, `download_detail.html`, `legal.html`, `_footer.html`, `api_keys.html`, `payment.html`, `orders.html`, `cloud_instances.html`, `douyin_login.html`, `douyin_success.html`, `site_home.html`, `site_pricing.html`, `site_features.html`, `site_contact.html`, `index.html`

### 2.4 页面块系统（Page Blocks）

CMS块类型驱动页面渲染：

| block_type | 用途 |
|-----------|------|
| `text` | 纯文本/富文本 |
| `image` | 单图/多图 |
| `video` | 视频嵌入 |
| `html` | 自定义HTML |
| `products` | 服务卡片列表 |
| `posts` | 最新文章列表 |
| `faq` | 常见问题折叠区 |
| `feature` | 功能特性展示 |
| `cta` | 行动号召按钮 |
| `hero` | 大屏主视觉 |

---

## 3. Admin — 管理后台

**端口**：8084 | **域名**：agent.easykai.cn | **技术栈**：SPA（Flask + JS模块）

### 3.1 SPA架构

```
侧栏点击 → go('module_name')
              ↓
        window['l_module_name']()
              ↓
    fetch API → 渲染HTML → innerHTML注入
```

### 3.2 功能模块清单（47个模块，12组）

| 分组 | 模块 |
|------|------|
| **仪表盘** | 仪表盘 |
| **AI对话** | 指令控制台 |
| **系统管理** | 基本设置、OAuth登录、导航设置、模型维护、管理员设置、品牌设置、站群管理、模板管理 |
| **内容生态** | 信息捕获、全媒体创作、下载管理、媒体库 |
| **AI创作** | PPT生成、图像生成、多媒体 |
| **运行策略** | 智能体系、数据清洗、自动调度、IM网关 |
| **运营支撑** | 套餐管理、订阅列表、部署码管理、收入看板、优惠券、扣款日志、完成度奖励、广告管理、商品分类、商品管理、订单管理、优惠券管理、购买记录 |
| **消息与支持** | 邮件服务、通知推送、用户工单 |
| **租户生态** | 主体管理、实例节点、访问令牌 |
| **风控审计** | 动态审计、评论审核 |
| **运维数据** | 统计分析、健康巡检、Token用量、操作日志 |

### 3.3 Blueprint注册

Admin注册的蓝图：user_bp, auth_bp, admin_bp, cms_admin_bp, social_bp, social_media_bp, footer_bp, header_bp, comments_bp, cf_bp, theme_bp, analytics_bp, douyin_mp_bp, shop_bp, sub_bp, cleaner_bp, health_bp, init_automation(), init_agent_matrix()

---

## 4. Auth Center — 认证中心

**不独立运行**，以约18个 Blueprint 嵌入 Platform 和 Admin

### 4.1 核心能力

| 功能 | 说明 |
|------|------|
| **JWT SSO** | HS256 JWT，跨 `.easykai.cn` 子域SSO，7天有效 |
| **密码登录** | pbkdf2:sha256 哈希 |
| **短信登录** | 阿里云短信，6位验证码，10分钟有效 |
| **OAuth第三方** | 支付宝/微信/抖音，自动注册+绑定 |
| **用户体系** | username/display_name分离，角色admin/user |
| **TOTP二步验证** | 可选开启 |
| **API密钥** | 用户级API Key（创建/吊销）|
| **会话管理** | 单令牌/全用户撤销 |

### 4.2 用户模型

| 字段 | 说明 |
|------|------|
| `username` | 登录名，唯一，30天可改一次 |
| `display_name` | 显示名，可修改 |
| `phone` / `email` | 联系方式 |
| `password_hash` | pbkdf2:sha256 |
| `is_admin` | 管理员标志 |
| `wechat_openid` / `douyin_open_id` / `alipay_user_id` | 第三方绑定 |
| `totp_secret` / `totp_enabled` | TOTP二步验证 |
| `is_real_name_verified` | 实人认证 |

### 4.3 SSO流程

```
浏览器 → 登录 → JWT签发 → Set-Cookie: sso_token（Domain=.easykai.cn）
       → 访问其他子域 → Cookie自动携带 → validate_token()验证
```

### 4.4 频率控制

- 短信发送：每小时每手机号上限5条
- 短信验证码：同一会话尝试≥5次报错
- 发送前触发滑块验证码（高频场景）

---

## 5. CMS — 内容管理系统

### 5.1 数据表

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `cms_posts` | 文章主表 | slug, category, title, content, is_published, publish_channels |
| `cms_categories` | 栏目表 | name, slug, sort_order, is_active |
| `cms_blocks` | 页面区块 | page, section, block_type, position, extra_json |
| `cms_settings` | 配置表 | key, value |

### 5.2 文章管理

- CRUD接口：`/admin/cms/posts`
- Slug自动生成：`article-{uuid[:8]}`
- 草稿/发布双态，预览路由 `/preview/<slug>`（需登录）
- 支持多渠道发布（local微博微信头条）

### 5.3 默认栏目

快速入门、Agent开发、金融分析、最佳实践、产品动态、帮助中心、法律合规

### 5.4 前端展示

/knowledge（知识库聚合页）、/insights（产品动态）、/docs（帮助文档）

---

## 6. Content Factory — 内容工厂

自动化内容供应链：RSS采集 → AI加工 → 审核 → 多渠道发布

### 6.1 流水线

```
来源(RSS/API/Web) → 采集器 → 原始内容 → AI加工(Qwen) → 加工内容
                                                          ├→ CMS发布
                                                          ├→ 知识库入库
                                                          └→ Skill推送
```

### 6.2 数据库表

| 表 | 用途 |
|----|------|
| `content_sources` | 内容源配置（RSS/API/Web） |
| `raw_contents` | 采集原始数据（SHA-256去重） |
| `processed_contents` | AI加工结果（多类型） |
| `content_tasks` | 任务记录 |
| `skill_pushes` | Skill推送记录 |

### 6.3 AI加工

- 模型：通义千问 Qwen（qwen-turbo）
- 输入：标题+作者+正文
- 输出：优化标题/一句话摘要/Markdown重排/关键词/风险等级

### 6.4 管理路由

25个路由端点：来源管理/采集触发/原始内容列表/AI加工/加工内容管理/Skill推送/知识库推送等

---

## 7. Knowledge — 知识库与数据清洗

### 7.1 核心数据表

| 表 | 用途 |
|----|------|
| `knowledge_blocks` | 知识条目（id/title/content/keywords/category/priority） |
| `knowledge_queue` | 清洗任务队列（pending→cleaning→done/failed）|

### 7.2 RAG检索机制

混合关键词检索（非向量RAG），评分算法：

| 维度 | 权重 |
|------|------|
| 关键词匹配 | 0.60 |
| 字符重叠 | 0.25 |
| 标题重叠 | 0.15 |
| 精确命中正文 | +0.30 |
| 精确命中标题 | +0.20 |

### 7.3 数据清洗管道

```
原始文本 → 截断(≤50000字) → 去重检测(>85%) → AI提取(LLM) → 分类 → knowledge_blocks写入
```

### 7.4 三种调用路径

1. 管理后台手动提交（`POST /shop/cleaner/submit`）
2. 内容工厂自动推送
3. Agent Matrix意图路由（`intent: "clean"`）

---

## 8. Shop — 商城系统

### 8.1 数据库表（10张）

| 表 | 用途 |
|----|------|
| `products` | 商品主表（type: service/cloud_service） |
| `categories` | 商品分类（多级） |
| `product_specs` | 规格名（颜色/尺寸） |
| `product_spec_values` | 规格值（红色/XL） |
| `product_skus` | SKU库存（独立定价） |
| `order_items` | 订单明细 |
| `carts` | 购物车（SKU级别） |
| `coupons` | 优惠券管理 |
| `coupon_redemptions` | 核销记录 |
| `user_purchases` | 购买记录 |

### 8.2 订单状态机

pending → paid → shipped → completed → refunding → refunded → cancelled

### 8.3 支付网关

支付宝（RSA2签名）、微信支付（V3 API）、Stub桩模式

### 8.4 前端页面

- `/shop` — 商品列表
- `/shop/<id>` — 商品详情
- `/shop/cart` — 购物车
- `/shop/orders` — 订单列表（当前跳转到首页，待完善）
- `/shop/cloud` — 云服务

### 8.5 管理端

商品分类CRUD、商品管理、订单处理、优惠券管理、购买记录

---

## 9. Alibaba Integration — 1688供应链对接

### 9.1 系统架构

```
Admin UI → ali_api Blueprint → Alibaba Open Platform API
  ├── v1客户端（HMAC-SHA1签名）
  ├── v2客户端（OAuth 2.0 + access_token）
  ├── AI处理器（DeepSeek优化标题/描述/卖点）
  ├── 四层风控（用户级/全局/熔断/审计）
  └── 双缓存（内存 + Redis）
```

### 9.2 核心能力

| 功能 | 说明 |
|------|------|
| 商品采集 | 通过1688 API获取商品详情与搜索 |
| AI加工 | 自动优化标题/重写文案/生成卖点标签 |
| 一键发布 | 1688商品 → 本地商城（products表） |
| 四层风控 | 用户限流/并发控制/熔断保护/审计告警 |
| 双缓存 | 内存缓存1h + Redis |

### 9.3 管理后台路由

| 路由 | 功能 |
|------|------|
| `/admin/ali-api/` | 控制台首页 |
| `/admin/ali-api/items` | 商品列表/采集/搜索 |
| `/admin/ali-api/items/<id>/ai-optimize` | AI全面优化 |
| `/admin/ali-api/items/<id>/publish` | 发布到本地商城 |
| `/admin/ali-api/oauth/*` | OAuth授权流程 |
| `/admin/ali-api/logs` | API调用日志 |

### 9.4 AI处理

支持：单标题优化、多版本标题生成（3风格）、描述重写、全案生成（标题+描述+卖点+标签）

---

## 10. Payment & Subscription — 支付与订阅

### 10.1 支付网关

| 网关 | 支付模式 | 自动续费 |
|------|---------|---------|
| 支付宝 | 即时到账/RSA2签名 | 周期扣款签约 |
| 微信支付 | Native扫码/V3 API | 委托扣款签约 |
| Stub | 降级桩模式 | — |

### 10.2 订阅管理系统

| 表 | 用途 |
|----|------|
| `subscription_plans` | 套餐定义（plan_key/月价/年价/特性） |
| `subscriptions` | 用户订阅（一人一订阅） |
| `subscription_orders` | 订阅订单 |
| `coupons` | 优惠券 |
| `invoices` | 电子发票 |
| `payment_events` | 支付事件日志 |
| `subscription_audit_log` | 审计日志 |

### 10.3 套餐定义

| 字段 | 说明 |
|------|------|
| plan_key | 标识（deploy_basic/deploy_pro/deploy_enterprise）|
| price_month | 月付价格（分）|
| price_year | 年付价格（分）|
| features_json | 特性列表JSON |
| tier | basic / popular / premium |

### 10.4 订单流程

```
用户选择套餐 → 创建订单 → 跳转支付网关 → 异步回调 → 履约
```

### 10.5 回调统一入口

`POST /subscription/notify/<channel>`（channel = wechat | alipay）

---

## 11. Agent Matrix — AI矩阵编排

### 11.1 核心架构

1个Master Agent（Athena）+ 12个Sub Agent，5家AI供应商集成

```
用户指令 → Master Agent(Athena) → 任务分解 → ThreadPool(5路并行)
              ↓                                       ↓
          Sub Agents(12个) ←────────────── 自检重试(置信度<0.7)
              ↓
          汇总报告
```

### 11.2 13个默认Agent

| Agent | 角色 | 模型 | 职责 |
|-------|------|------|------|
| Athena | Master | gpt-4o | 任务分解/协调/汇总 |
| CMS Agent | Sub | qwen-turbo | 文章写作/内容管理 |
| Finance Agent | Sub | qwen-turbo | 财务分析/报表 |
| User System Agent | Sub | qwen-turbo | 用户管理/权限 |
| Community Agent | Sub | qwen-turbo | 社区内容 |
| Automation Agent | Sub | qwen-turbo | 自动化流程 |
| Analytics Agent | Sub | qwen-turbo | 数据分析 |
| Ticket Agent | Sub | qwen-turbo | 工单/客服 |
| Kai Assistant | Sub | deepseek-chat | 对话助手的 |
| Voice Agent | Sub | volc-voice | 语音克隆/TTS |
| Video Agent | Sub | volc-avatar | 数字人视频 |
| Image Agent | Sub | wan2.7-image | 图像生成 |
| Shop Agent | Sub | qwen-turbo | 商品/订单/供应链 |

### 11.3 供应商集成

| 供应商 | 模型示例 | 用途 |
|--------|---------|------|
| DashScope | qwen-turbo, qwen-max | 主力文本 |
| OpenAI | gpt-4o, gpt-4o-mini | Master Agent |
| DeepSeek | deepseek-chat | 客服对话 |
| OpenRouter | 多模型路由 | 备用 |
| Ollama | 本地模型 | 离线场景 |

### 11.4 核心流程

1. 接收指令 → 意图分析 → 任务分解（AI/模板）
2. 调度执行（最多5路并行，300s超时）
3. 自检重试（置信度<0.7自动重试，最多3次）
4. 汇总报告

### 11.5 Token审计

每次LLM调用的token消耗精确记录，按日汇总与费用估算

---

## 12. Orchestrator — 自动化调度与工作流

### 12.1 两个子系统

| 子系统 | 核心 | 用途 |
|--------|------|------|
| Cron Scheduler | APScheduler | 定时/周期/一次性任务 |
| DAG Workflow | 自研引擎 | 多步骤工作流编排 |

### 12.2 调度方式

- Cron表达式（`0 30 9 * * 1-5`）
- 自然语言（`每个交易日 9:30`）
- 固定间隔（`3600`秒）
- 一次性（指定时间）

### 12.3 数据表（9张）

cron_jobs, workflow_definitions, workflow_instances, workflow_node_instances, execution_logs, alerts, system_agents, job_dependencies

### 12.4 节点类型（12种）

ai_agent, data_collect, ai_process, condition, approval, publish, notify, wait, sub_workflow, market_check, http_request, script

### 12.5 输出验证

每节点输出通过 `conditions` 定义验证规则（success/failure/timeout），决定DAG下步走向

---

## 13. Cloud Provisioner — 云服务自动开通

### 13.1 三层架构

```
ProvisionerEngine → Provider Adapter → Cloud Resource
                    ├── TemplateProvider（Docker容器）
                    └── AliyunProvider（预留，未实现）
```

### 13.2 开通流程

```
用户下单 → 支付成功 → create_instance(pending)
                    → validate_config()
                    → provision()（创建Docker容器）
                    → poll status（等待running）
                    → update_instance（连接信息）
                    → add_log()
```

### 13.3 数据库表

| 表 | 用途 |
|----|------|
| `cloud_instances` | 云实例记录（状态/连接信息/规格） |
| `provision_logs` | 开通日志 |

### 13.4 API路由

- 公开：`/cloud/create`, `/cloud/<id>/status`, `/cloud/<id>/terminate`
- 管理：`/admin/cloud/instances`, `/admin/cloud/<id>/retry`, `/admin/cloud/<id>/terminate`

### 13.5 初始化脚本

- `init_ubuntu.sh` — Ubuntu容器初始化（建站环境）
- `init_centos.sh` — CentOS容器初始化

---

## 14. Theme — 主题系统

### 14.1 多租户架构

```
平台门户(:8083, site_key=platform) → theme_id
管理后台(:8084, site_key=admin) → theme_id
    共享同一个SQLite数据库
```

### 14.2 数据库表

| 表 | 用途 |
|----|------|
| `themes` | 主题注册（name/slug/version/config_json） |
| `site_theme_config` | 站点-主题关联（site_key/theme_id/overrides） |
| `site_configs` | 站点基本配置（domain/colors/logo） |

### 14.3 主题覆盖

每个站点独立切换主题，互不干扰，支持CSS变量覆盖（overrides_json）

### 14.4 管理功能

安装/列表/激活/删除主题，顶部导航CRUD，页脚管理CRUD

---

## 15. Captcha — 验证码服务

**独立服务**：FastAPI，端口 8090

### 15.1 验证码类型

| 类型 | 说明 |
|------|------|
| 形状匹配拼图（新版） | 随机形状+实景图背景+干扰形状+旋转 |
| 水平滑块（旧版） | 纯Python实现，行为轨迹分析 |

### 15.2 请求链路

```
Nginx(:443) → /api/captcha/* → Captcha(:8090)
     └→ Platform/Admin 代理转发
          └→ Auth-Center 内联（旧版）
```

### 15.3 安全机制

- HMAC-SHA256 Token（防篡改/重放）
- IP限流 + 失败计数
- 行为轨迹分析（速度/加速度/停顿检测）

### 15.4 管理端

统计面板（需Bearer token鉴权）

---

## 附录：已删除的文档

以下文件已被移除以保持文档库干净：
- ~~易站AI网站重构方案_v2.md~~（内容已整合）
- ~~IAM架构文档~~（历史版本）
- ~~市场/商业分析文档~~（独立文件）
- ~~商城评估/差距分析~~（独立文件）
