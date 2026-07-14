# 管理后台 (Admin Panel)

> 易站 AI 建站系统的统一运营管理控制台，独立端口 **8084**。

---

## 1. 概述 (Overview)

管理后台是一个**单页面应用** (SPA)，运行在独立端口 `8084`，服务于整个平台的集中运维。所有功能模块以纯前端 JS 模块（`l_xxx` 函数）的方式动态加载，通过 `fetch` API 调用后端接口并渲染内容，无需页面刷新。

- **入口**：`http://localhost:8084/admin`
- **主模板**：[`admin/templates/admin.html`](../../../admin/templates/admin.html)（~10000+ 行纯 JS 模块）
- **后端入口**：[`admin/app.py`](../../../admin/app.py)
- **JS 模块数量**：**50+** 个

---

## 2. 架构 (Architecture)

### 2.1 SPA 设计模式

```
用户点击侧栏 → go('module_name')
                     ↓
          window['l_module_name']()
                     ↓
      fetch API → 渲染 HTML → innerHTML 注入
```

每个功能模块由 `window.l_xxx` 函数定义，通过 `<nav>` 侧栏的 `go()` 函数统一调度。侧栏菜单在 `GROUPS` 数组中静态定义，支持分组折叠/展开。

### 2.2 Blueprint 注册 (Blueprint Registration)

[`admin/app.py`](../../../admin/app.py) 集中注册了以下 Blueprint：

| Blueprint | 前缀 | 来源模块 |
|---|---|---|
| `user_bp` | — | `routes.user` |
| `auth_bp` | — | `routes.auth` |
| `admin_bp` | — | `routes.admin` |
| `cms_admin_bp` | — | `routes.cms_admin` |
| `social_bp` | — | `routes.social_push` |
| `social_media_bp` | — | `routes.social_media` |
| `footer_bp` | — | `routes.footer_admin` |
| `header_bp` | — | `routes.header_admin` |
| `comments_bp` | — | `routes.comments` |
| `cf_bp` | — | `routes.content_factory` |
| `theme_bp` | `/admin` | `routes.theme_admin` |
| `analytics_bp` | — | `analytics.dashboard` |
| `douyin_mp_bp` | — | `routes.douyin_miniprogram` |
| `shop_bp` | — | `routes.shop_admin` |
| `sub_bp` | — | `routes.subscription` |
| `cleaner_bp` | — | `routes.cleaner_agent` |
| `health_bp` | — | `health_check` |
| 纯后端 (无 UI) | `init_automation(app)` | `orchestrator.routes` |
| 纯后端 (无 UI) | `init_agent_matrix(app)` | `agent_matrix.routes` |

另外，认证中心 (`auth-center`) 的 Blueprint 也通过 `routes.auth`、`routes.admin` 等挂载，实现统一会话管理。

### 2.3 Captcha 代理

管理后台通过反向代理将验证码请求转发到 Captcha 服务（端口 `8090`）：

- `GET /api/captcha/generate`
- `POST /api/captcha/verify`
- `POST /api/captcha/consume`

静态文件 (`puzzle-captcha.js` / `.css`) 同样从 Captcha 服务代理提供。

---

## 3. 导航系统 (Navigation System)

### 3.1 侧栏分组 (Sidebar Groups)

侧栏菜单定义在 `GROUPS` 数组中（`admin.html`），共 **12 个分组**，支持折叠展开：

| 分组名称 | 折叠 | 包含模块 |
|---|---|---|
| **仪表盘** | 否 | 仪表盘 |
| **AI 与内容** | 是 | 指令控制台、内容列表、文章创作、下载管理、媒体库 |
| **系统管理** | 是 | 站点设置、小程序、基本设置、模型管理、管理员 |
| **AI 矩阵** | 是 | 智能体系、数据清洗 |
| **发布管理** | 是 | 自动调度、发布历史 |
| **订阅与计费** | 是 | 套餐管理、订阅列表、计划订单、功能订单、部署码、收入看板、扣款日志、完成度奖励 |
| **商城管理** | 是 | 商品分类、商品管理、商城订单、购买记录 |
| **用户与支持** | 是 | 主体管理、实例节点、访问令牌、通知推送、用户工单 |
| **安全与合规** | 是 | 动态审核、评论审核 |
| **支付与运营** | 是 | *（纯插件功能：支付配置、货币设置、广告管理、供应链采集、物流追踪）* |
| **监控与数据** | 是 | Token 用量、操作日志 |
| **插件与国际化** | 否 | 插件管理、插件商店、许可证管理、插件订阅、翻译管理 |

### 3.2 权限控制

访问 `GET /admin` 时，后端验证 JWT Token 的 `is_admin` 字段：

```python
payload = validate_token(token)
if not payload or not payload.get('is_admin'):
    return redirect('/login?redirect=/admin')
```

每个 API 接口通过 `_require_admin()` 装饰器或显式 JWT 验证确保权限。

---

## 4. 功能清单 (Feature Inventory)

### 4.1 仪表盘与监控 (Dashboard & Monitoring)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 仪表盘 | `l_dashboard` | 核心指标卡片（总用户/活跃订阅/API 调用/Agent 状态/月收入）；Token 消耗排行；服务状态指示灯；待处理事项（审核/工单/失败任务）；今日流量 PV/UV/在线；热门页面；最近注册用户；最近订单 |
| 统计分析 | `l_analytics` | iframe 嵌入 `/admin/analytics/` 页面，展示流量趋势、渠道来源、用户行为等 |
| 健康巡检 | `l_health` | iframe 嵌入 `/admin/health/` 页面，各服务模块健康状态检查列表 |
| Token 用量 | `l_token_monitoring` | Token 消耗监控看板 |
| 操作日志 | `l_logs` | 系统操作日志审计 |

### 4.2 用户管理 (User Management)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 主体管理 | `l_users` | 用户列表（行业/职业/地域筛选）；用户详情弹窗（基本资料/扩展资料/收货地址）；头像上传/切换；Agent 创建/暂停/激活；导出 CSV |
| 实例节点 | `l_agents` | Agent 实例列表、状态管理 |
| 访问令牌 | `l_keys` | API 访问密钥管理 |
| 管理员设置 | `l_admins` | 管理员账号管理（添加/删除管理员） |

### 4.3 内容管理 (CMS)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 全媒体创作 | `l_cms` | 三 Tab 切换：文章编辑（含 Quill 富文本编辑器、AI 排版、AI 配图、多渠道发布）、AI 对话（Athena Agent 聊天）、PPT 生成 |
| 信息捕获 | `l_contentfactory` | 三 Tab：来源管理（RSS/API 数据源）、原始内容列表、加工内容管理 |
| 下载管理 | `l_downloads` | 资源下载链接管理 |
| 媒体库 | `l_media_library` | 图片/视频/文件等媒体资源统一管理 |
| 动态审计 | `l_posts` | 用户动态帖子审核管理 |
| 评论审核 | `l_comments` | 全部/待审核/已通过/已拒绝 四态筛选审核 |

### 4.4 AI 创作 (AI Creation)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| PPT 生成 | `l_ppt_gen` | 输入主题/页数/风格，AI 自动生成 PPT 大纲与内容 |
| 图像生成 | `l_media_video` | 输入提示词，AI 生成图像/视频 |
| 多媒体 | `l_media_tools` | 多媒体工具集 |

### 4.5 Agent 矩阵 (Agent Matrix)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 智能体系 | `l_matrix` | 主 Agent Athena 状态；子 Agent 列表（领域/管辖模块/模型/任务统计）；创建/编辑/测试 Agent；最近任务追踪 |
| 数据清洗 | `l_cleaner` | 粘贴原始内容，AI 自动清洗为结构化知识库条目；清洗队列管理（批量/单条） |
| 自动调度 | `l_automation` | Cron 定时任务和 Workflow 工作流的可视化调度管理（底层由 APScheduler + 线程池 Worker 实现） |
| 指令控制台 | `l_ai_chat` | 全页面 AI 对话界面，支持快速/深度思考/图像理解/工具调用四种模式；会话历史管理（搜索/批量删除） |
| IM 网关 | `l_channels` | 即时消息渠道配置（如企业微信、飞书、Slack 等） |

### 4.6 订阅与计费 (Subscription & Billing)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 套餐管理 | `l_plans` | 套餐 CRUD（plan_key/名称/月价/年价/日限/描述/特性 JSON）；启用/禁用 |
| 订阅列表 | `l_subscriptions` | 订阅记录查询（按用户/状态筛选：活跃/试用/逾期/已取消/已过期） |
| 订单管理 | `l_sub_orders` | 付费订单列表 |
| 收入看板 | `l_sub_stats` | 收入统计图表（月度/年度） |
| 优惠券 | `l_coupons` | 优惠券生成与发放管理 |
| 扣款日志 | `l_sub_events` | 自动扣款事件记录查询 |
| 完成度奖励 | `l_reward_rules` | 用户完成度奖励规则配置 |

### 4.7 商城 (Shop)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 商品分类 | `l_shop_categories` | 商城商品分类管理 |
| 商品管理 | `l_shop_products` | 商品 CRUD（名称/价格/库存/描述/图片） |
| 订单管理 | `l_shop_orders` | 商城订单处理与状态流转 |
| 优惠券管理 | `l_shop_coupons` | 商城专属优惠券管理 |
| 购买记录 | `l_shop_purchases` | 用户购买记录查询 |

### 4.8 系统配置 (System Config)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 基本设置 | `l_config` | 系统配置项管理（按分类分组，支持敏感字段掩码）；短信模板编码设置 |
| OAuth 登录 | `l_oauth` | 第三方 OAuth 登录渠道配置（微信/微博/GitHub 等） |
| 导航设置 | `l_nav_settings` | 前端导航菜单配置（新增/编辑/排序/删除导航项） |
| 模型维护 | `l_model_providers` | AI 模型供应商与模型实例管理 |
| 品牌设置 | `l_brand` | 站点品牌信息配置（站点名称/Logo/Favicon/页脚版权等） |
| 站群管理 | `l_cluster_services` | 多站点集群服务管理 |
| 模板管理 | `l_themes` | 主题安装/启用/卸载；站点主题映射（main/platform/admin） |

### 4.9 广告管理 (Ad Management)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 广告管理 | `l_ads` | 广告位 CRUD：支持图片广告（image）和广告代码（code）两种类型；投放页面可选（全站/广场/阵营/辩论/预警/排行/竞技/认知地图）；位置支持侧边栏；搜索/启用禁用/排序 |

路由：`GET/POST/PUT/DELETE /admin/ads`

### 4.10 消息与通知 (Messaging & Notifications)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 邮件服务 | `l_email` | 邮件发送配置与记录管理 |
| 通知推送 | `l_notifications` | 系统通知推送管理（站内信/推送） |
| 用户工单 | `l_tickets` | 用户工单处理与回复 |

### 4.11 站群管理 (Cluster Management)

| 模块名 | JS 函数 | 功能描述 |
|---|---|---|
| 站群管理 | `l_cluster_services` | 多站点/多服务实例的统一监控与配置 |

---

## 5. 主题管理 (Theme Management)

### 5.1 站点密钥 (SITE_KEYS)

定义在 [`admin/routes/theme_admin.py`](../../../admin/routes/theme_admin.py)：

```python
SITE_KEYS = ['main', 'platform', 'admin']
SITE_LABELS = {'main': '主站', 'platform': '用户后台', 'admin': '管理后台'}
```

每个站点可以独立配置主题。

### 5.2 主题加载机制

在 [`admin/app.py`](../../../admin/app.py) 中，通过 `Jinja2 ChoiceLoader` 实现模板覆盖：

1. 查询 `site_theme_config` 表获取 `admin` 站点的激活主题 slug
2. 如果存在非默认主题，将其 `templates/` 目录加入 `ChoiceLoader` 优先队列
3. 主题的 `theme.css` 通过 `inject_theme()` 上下文处理器注入模板

### 5.3 主题 API

| 端点 | 方法 | 功能 |
|---|---|---|
| `/admin/themes` | GET | 主题列表（含激活站点信息） |
| `/admin/themes/install` | POST | ZIP 主题包安装（含安全校验） |
| `/admin/themes/<id>` | GET/DELETE | 主题详情/卸载 |
| `/admin/themes/sites` | GET | 站点-主题映射列表 |
| `/admin/themes/sites` | PUT | 切换某站点的主题 |

### 5.4 首部导航与页脚 (Header/Footer)

管理后台提供两套独立 API 用于管理前台页面的首部导航和页脚链接：

- **Header Nav**：`header_bp`（`routes/header_admin`），管理主站顶部导航菜单
- **Footer Links**：`footer_bp`（`routes/footer_admin`），管理页脚链接、社交媒体图标

---

## 6. 安全特性 (Security)

| 特性 | 说明 |
|---|---|
| JWT 认证 | 所有 API 通过 Bearer Token 鉴权，支持 Cookie/Header/Query 三种传递方式 |
| CSP 标头 | 严格的 Content-Security-Policy，限制脚本/样式/字体来源 |
| XSS 防护 | `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`X-XSS-Protection` |
| 速率限制 | 验证码消费接口带滑动窗口速率限制（10次/分钟） |
| 文件上传过滤 | 主题安装时白名单扩展名、黑名单文件类型、单文件 2MB 限制 |
| Captcha 代理 | 验证码生成/验证/消费走反向代理，不直接暴露 Captcha 服务 |

---

## 7. 开发扩展 (Extending the Admin)

添加新功能模块的步骤：

1. **后端**：在 `admin/routes/` 下创建新的 Blueprint，在 `admin/app.py` 中 `register_blueprint`
2. **前端**：在 `admin.html` 中添加 `window.l_xxx` 函数
3. **菜单**：在 `GROUPS` 数组中添加菜单项，使用 SVG 图标 `I.xxx`
4. **权限**：API 端点通过 `_require_admin()` 或 JWT 验证保护

> 参考现有模块如 `l_ads`（约 100 行）即可快速上手。
