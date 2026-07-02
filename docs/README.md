# VeroRon 维洛智能 — 模块文档索引

> VeroRon 维洛智能（verorun.com / verorun.cn）是一个多智能体驱动的 AI 建站与商业枢纽平台。  
> 本文档是全部模块 README 的总入口，每个模块覆盖：架构设计、数据库结构、API 参考、核心流程、配置说明。

---

## 服务拓扑

```
用户 ─→ Nginx (443)
           │
           ├──→ Platform (:8083)     ── 前端门户（公开页面 + CMS 渲染）
           │       └── auth-center blueprint ── 认证/用户/CMS/内容工厂/商城
           │
           ├──→ Admin (:8084)        ── 管理后台（SPA 单页应用）
           │       └── auth-center blueprint ── 同上
           │       └── agent_matrix blueprint ── Agent 矩阵
           │       └── orchestrator blueprint  ── 工作流引擎
           │
           ├──→ Captcha (:8090)      ── 验证码服务（独立 FastAPI）
           │
           ├──→ Auth-Center (:8081)  ── 认证中心（内部服务，非公开）
           │
           └──→ Agent Matrix         ── AI矩阵编排（嵌入 Admin）
```

---

## 模块文档清单

### 🏗 核心服务

| # | 文档 | 端口 | 说明 |
|---|------|------|------|
| 1 | [Platform — 前端门户](platform.md) | 8083 | Flask + Jinja2 门户，CMS 渲染、页面块、预览、SSO 登录 |
| 2 | [Admin — 管理后台](admin.md) | 8084 | 单页应用，50+ 功能模块，主题/广告/CMS/商城/Agent 管理 |
| 3 | [Auth Center — 认证中心](auth-center.md) | - | JWT SSO、用户体系、OAuth、Blueprint 架构、18 个路由文件 |
| 4 | [Captcha — 验证码服务](captcha.md) | 8090 | 独立 FastAPI 服务，拼图验证码 + 行为分析 |

### 📄 内容管理

| # | 文档 | 说明 |
|---|------|------|
| 5 | [CMS — 内容管理系统](cms.md) | 文章/栏目/页面块、预览路由、内容净化、社交推送 |
| 6 | [Content Factory — 内容工厂](content-factory.md) | 信息捕获 Pipeline：RSS → 采集 → AI 加工 → 发布 |
| 7 | [Knowledge — 知识库 & 数据清洗](knowledge.md) | Cleaner Agent 全局知识库，RAG 检索，3 条调用路径 |

### 🛒 电商与支付

| # | 文档 | 说明 |
|---|------|------|
| 8 | [Shop — 商城系统](shop.md) | 商品/SKU/购物车/订单 13 张表，支付网关，云服务商品触发云开通 |
| 9 | [Payment & Subscription — 支付与订阅](payment.md) | 支付宝/微信支付，套餐管理，自动续费，优惠券系统 |
| 10 | [Alibaba Integration — 1688 对接](alibaba-integration.md) | 1688 商品采集，AI 加工，一键发布，OAuth 双版本客户端 |

### 🤖 AI 与自动化

| # | 文档 | 说明 |
|---|------|------|
| 11 | [Agent Matrix — AI矩阵编排](agent-matrix.md) | 1 Master + 12 Sub Agent，5 家 AI 供应商，83 个 API 端点 |
| 12 | [Workflow — 工作流引擎](workflow.md) | Cron 调度 + DAG 工作流，13 种节点类型，Safe Eval 沙箱 |

### 🎨 主题与站点

| # | 文档 | 说明 |
|---|------|------|
| 13 | [Theme System — 主题系统](theme.md) | 多站点独立主题，CSS 变量，Header/Footer 管理，模板覆盖 |

### ☁️ 云服务

| # | 文档 | 说明 |
|---|------|------|
| 14 | [Cloud Provisioner — 云服务自动开通](cloud-provisioner.md) | 下单支付后自动开通云资源，Provider 适配器架构 |

### 📚 开发参考

| # | 文档 | 说明 |
|---|------|------|
| 15 | [API 参考 — 接口文档](api-reference.md) | 全平台 ~380+ API 端点，认证方式、请求/响应格式、错误码 |
| 16 | [SDK 参考 — 开发工具包](sdk-reference.md) | Python/JavaScript SDK，客户端封装，SSE 流式，最佳实践 |

---

## 快速定位

| 你想找什么？ | 看哪个文档 |
|-------------|-----------|
| 页面为什么跳转 302？ | [Platform](platform.md) → 认证流程 |
| 后台某个功能没反应？ | [Admin](admin.md) → 功能清单 + JS 模块 |
| 怎么加个 CMS 文章？ | [CMS](cms.md) → 文章管理 |
| RSS 抓取怎么配？ | [Content Factory](content-factory.md) → 采集器系统 |
| AI Agent 怎么调？ | [Agent Matrix](agent-matrix.md) → API 参考 |
| 套餐价格怎么改？ | [Payment](payment.md) → 套餐管理 |
| 1688 商品怎么同步？ | [Alibaba Integration](alibaba-integration.md) → 管理后台接口 |
| 云服务器自动开通？ | [Cloud Provisioner](cloud-provisioner.md) → 开通流程 |
| 主题颜色怎么改？ | [Theme System](theme.md) → CSS 变量系统 |
| 知识库数据怎么来？ | [Knowledge](knowledge.md) → 3 条调用路径 |

---

## 技术栈总览

| 层次 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web 框架 | Flask 3.x, Jinja2 |
| 数据库 | SQLite 3 |
| 认证 | JWT (PyJWT), OAuth 2.0 |
| AI | DashScope, OpenAI, DeepSeek, OpenRouter, Ollama, SiliconFlow |
| 调度 | APScheduler |
| 支付 | Alipay SDK, WeChat Pay SDK |
| 部署 | systemd, Nginx, Docker |

---

## 系统目录结构

```
/home/easykai/easykai-workspace/easykai.cn/
├── platform/                  # 前端门户 (:8083)
├── admin/                     # 管理后台 (:8084)
├── auth-center/                # 认证中心 + 所有业务蓝图
│   ├── routes/                # ~18 个路由文件
│   ├── models/                # 数据库模型
│   ├── services/              # 业务服务层
│   └── templates/             # 通用模板
├── captcha-service/           # 验证码服务 (:8090)
├── agent_matrix/              # Agent 矩阵
├── orchestrator/              # 工作流引擎
├── ali_api/                   # 1688 对接
├── cloud_provisioner/         # 云服务开通
└── docs/                      # ✅ 本文档目录
```
