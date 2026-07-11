# Platform — 易站AI 前端门户模块

## 概述

**Platform** 是易站智能建站系统（easykai.cn）的**前端门户**（Frontend Portal），运行在 **8083** 端口，面向公众用户提供官网浏览、内容消费、套餐订阅、用户登录等功能。

与 Admin 后台（8084，管理端）不同，Platform 是用户直接看到的"网站"——它既是 easykai.cn 的对外展示页，也是已购用户的订阅管理入口。

> 技术栈：Flask + Jinja2 + SQLite + JWT + 数据库驱动模板

---

## 架构概览

```
用户请求 (Browser)
    │
    ▼
Nginx (反向代理, easykai.cn:443)
    │
    ▼
Platform (8083, Flask)
    │
    ├── app.py               ← 主入口：路由注册、中间件、全局上下文
    ├── cms_public.py         ← CMS 公开路由蓝图 (cms_bp)
    ├── routes/site_routes.py ← 多租户站点路由蓝图 (site_bp)
    ├── routes/api_v1.py      ← API v1 蓝图
    ├── routes/shop_public.py ← 商城公开蓝图
    │
    └── auth-center/          ← SSO 认证 + 数据库模型
         ├── models/cms.py    ← CMS 表操作 (blocks, posts, categories)
         └── models/database.py ← 全局数据库定义
```

**请求流程示例**（首页 `/`）：

```
Browser → GET /
    │
    ├── get_domain_config()      ← 判断是否为 platform 子域名
    ├── handle_oauth_callback()  ← 检查 URL token 登录
    ├── handle_platform_auth()   ← platform 子域名强制登录
    ├── get_page_blocks('home')  ← 从 cms_blocks 表加载页面块
    ├── load_footer_data()       ← 页脚：社媒/导航/链接
    ├── get_site_plans()         ← 订阅套餐
    ├── get_live_stats()         ← 实时统计数据
    ├── get_header_nav()         ← 顶部导航栏
    ├── check_login_state()      ← 检查登录状态
    │
    └── render_template('cms_page.html')
```

---

## 路由地图

### 主入口路由（`app.py`）

| 路由 | 方法 | 功能 | 说明 |
|------|------|------|------|
| `/` | GET | 首页 | 数据库驱动，CMS 页面块渲染 |
| `/login` | GET | 登录页 | 双栏布局：套餐展示 + 登录表单 |
| `/register` | GET | 注册页 | |
| `/reset-password` | GET | 重置密码 | |
| `/pricing` | GET | 定价页面 | 数据库驱动套餐列表 |
| `/subscribe` | GET | 订阅页面 | 需登录，展示所有订阅计划 |
| `/preview/<slug>` | GET | 文章预览 | 未发布文章需登录才可查看 |
| `/about` | GET | 关于我们 | 品牌信息、团队、数据 |
| `/knowledge` | GET | 知识中心 | 指南、AI 技巧、文章 |
| `/health` | GET | 健康检查 | `{"status": "ok"}` |
| `/avatar/gen/<seed>` | GET | 首字母头像 SVG | |
| `/chat-widget-embed` | GET | 客服组件嵌入页 | iframe 用 |
| `/user-console/` | GET | 旧用户中心 | 301 → `/` |
| `/orders` | GET | 旧订单页 | 301 → `/` |
| `/api-keys` | GET | 旧 API 密钥页 | 301 → `/` |

### 验证码代理（`app.py` → captcha service 8090）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/captcha/generate` | GET | 生成拼图验证码 |
| `/api/captcha/verify` | POST | 验证拼图 |
| `/api/captcha/consume` | POST | 消费验证码令牌 |
| `/puzzle-captcha.js` | GET | 验证码前端 JS |
| `/puzzle-captcha.css` | GET | 验证码前端 CSS |

### CMS 公开路由（`cms_public.py` — `cms_bp`）

| 路由 | 功能 |
|------|------|
| `/start` | 快速开始页 |
| `/brand` | 品牌页 |
| `/services` | 服务详情页（Hero + DB 驱动服务卡片） |
| `/cases` | 案例展示页 |
| `/pricing` | CMS 版本定价页 |
| `/pricing/calculator` | 价格计算器 |
| `/ai-experience` | AI 体验页 |
| `/download` | 下载中心 |
| `/download/<slug>` | 下载详情 |
| `/docs` | 文档首页 |
| `/docs/<cat_slug>/` | 文档分类列表 |
| `/docs/<cat_slug>/<slug>` | 文档详情 |
| `/legal/<slug>` | 法律页面 |
| `/insights` | 产品动态列表 |
| `/insights/<slug>` | 文章详情 |
| `/api/v1/insights/latest` | 最新动态 API |

### API 路由（`app.py`）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/pricing/calculator-config` | GET | 价格计算器配置（零硬编码） |
| `/api/social-links` | GET | 页脚社媒链接（旧表） |
| `/api/social-media` | GET | 页脚社媒链接（新表） |
| `/api/interests` | GET | 兴趣标签列表 |
| `/api/video/homepage` | GET | 首页视频（代理 8084） |
| `/api/notifications` | GET | 用户通知列表 |
| `/api/notifications/unread-count` | GET | 未读通知数 |
| `/api/notifications/<id>/read` | PUT | 标记已读 |
| `/api/notifications/read-all` | PUT | 全部标记已读 |
| `/api/notifications/<id>` | DELETE | 删除通知 |
| `/api/feedback` | POST | 提交投诉/建议 |

### 静态文件路由

| 路由 | 说明 |
|------|------|
| `/static/<path>` | 平台本地静态文件 |
| `/static/media/<path>` | 媒体库文件（代理到 admin/static/media/） |
| `/themes/<slug>/<path>` | 主题静态文件 |

### 多租户站点路由（`site_routes.py` — `site_bp`）

为未来多租户建站能力预留，支持 `/<slug>/` 动态路由：

| 路由 | 功能 |
|------|------|
| `/<slug>/` | 站点首页 |
| `/<slug>/pricing` | 站点定价 |
| `/<slug>/features` | 站点功能页 |
| `/<slug>/contact` | 站点联系页 |
| `/api/site/config` | 站点配置 API |
| `/api/site/blocks` | 站点页面块 API |
| `/api/site/plans` | 站点套餐 API |
| `/<slug>/api/config` | 站点配置 API（slug 方式） |

---

## 模板系统与页面块

### 核心模板

Platform 使用 Jinja2 模板引擎，核心模板位于 `platform/templates/`：

| 模板 | 用途 |
|------|------|
| `cms_page.html` | CMS 通用页面（首页、品牌等） |
| `login.html` | 登录页（双栏布局） |
| `register.html` | 注册页 |
| `pricing.html` | 定价页 |
| `subscribe.html` | 订阅页 |
| `services.html` | 服务页 |
| `cms_preview.html` | 文章预览页 |
| `insights_list.html` / `insights_detail.html` | 动态列表/详情 |
| `docs_index.html` / `docs_list.html` / `docs_detail.html` | 文档系统 |
| `knowledge.html` | 知识中心 |
| `about.html` | 关于我们 |
| `calculator.html` | 价格计算器 |
| `download_list.html` / `download_detail.html` | 下载中心 |
| `ai_experience.html` | AI 体验 |
| `cases.html` | 案例展示 |
| `start.html` | 快速开始 |

### 页面块系统（Page Blocks）

页面块是 Platform 的核心内容方案。所有 CMS 页面由 **cms_blocks** 表中的多个块按 `position` 排序组成。

**表结构**（`auth-center/models/cms.py`）：

```sql
cms_blocks (
    id, page, section, block_type, position,
    title, subtitle, content, image_url, link_url, link_text,
    icon, extra_json, is_published, created_at, updated_at
)
```

**10 种块类型**：

| block_type | 用途 | 渲染方式 |
|-----------|------|---------|
| `text` | 纯文本/富文本内容块 | 直接输出 `content` |
| `image` | 单图/多图展示 | `image_url` + `link_url` |
| `video` | 视频嵌入 | `extra_json` 提供视频源 |
| `html` | 自定义 HTML | 原样输出（允许白名单标签） |
| `products` | 产品/服务卡片列表 | `extra_json` 含产品数组 |
| `posts` | 最新文章列表 | 自动查询 `cms_posts` |
| `faq` | 常见问题折叠区 | `extra_json` 含 Q&A 列表 |
| `feature` | 功能特性展示（图标+标题+描述） | `icon` + `title` + `content` |
| `cta` | 行动号召按钮 | `title` + `link_text` + `link_url` |
| `carousel` | 轮播图 | `extra_json` 含轮播项数组 |

每个 block 的 `extra_json` 字段存储结构化配置（如轮播项列表、FAQ 数据、产品列表），模板端预解析为 Python dict 后渲染。

---

## CMS 集成

### 文章系统（`cms_posts`）

文章通过 `cms_posts` 表管理，核心字段：

| 字段 | 说明 |
|------|------|
| `slug` | URL 友好标识（唯一） |
| `category` | 分类名称（关联 `cms_categories.name`） |
| `title` / `excerpt` / `content` | 标题/摘要/正文 |
| `content_format` | 格式：`html` / `markdown` |
| `audience` | 可见范围：`public` / `internal` |
| `tags` | JSON 标签数组 |
| `is_published` | 是否已发布 |
| `publish_channels` | 发布渠道 JSON |

**文章分类**（`cms_categories`）默认种子数据：

| ID | 名称 | 标识 |
|----|------|------|
| 1 | 快速入门 | `getting-started` |
| 2 | Agent 开发 | `agent-dev` |
| 3 | 金融分析 | `finance` |
| 4 | 最佳实践 | `best-practices` |
| 5 | 产品动态 | `insights` |
| 6 | 帮助中心 | `help` |
| 7 | 法律合规 | `legal` |

### 文档系统（`/docs/`）

三层 URL 结构：

```
/docs/                  ← 分类索引页（列出所有公开分类）
/docs/<cat_slug>/      ← 分类文章列表
/docs/<cat_slug>/<slug> ← 单篇文章详情
```

### 文章预览（`/preview/<slug>`）

- 已发布文章 → 直接预览
- 未发布文章 → 需登录验证（JWT cookie）

### HTML 内容安全

`cms.py` 中的 `sanitize_html()` 函数实现白名单式 HTML 净化：
- 只允许 `p, div, span, h1-h6, a, img, ul/ol/li, table, blockquote` 等安全标签
- 过滤所有脚本、iframe、object、form 等危险标签
- 只保留白名单属性（`href`, `src`, `alt`, `class`, `id`, `style` 等）
- 阻止 `javascript:`、`vbscript:` 等危险协议

---

## 认证与登录流程

Platform 的认证体系基于 **SSO（Single Sign-On）**：

```ascii
用户访问平台页面
    │
    ├── Cookie 中有 sso_token/tm_token？
    │   ├── 是 → JWT 验证 → 有效 → 渲染页面
    │   │                   → 无效 → 重定向到 /login
    │   └── 否 → URL 中有 token 参数？
    │           ├── 是 → OAuth 回调 → 设 cookie → 重定向回原页面
    │           └── 否 → 渲染页面（未登录状态）
    │
    └── platform 子域名访问？
        └── 是且未登录 → 强制重定向到 /login
```

关键细节：
- **Cookie 域名**：`cookie_domain` 读取自 `brand.site_domain`，跨子域共享
- **Token 来源**：`sso_token`（SSO 登录）、`tm_token`（旧兼容）
- **OAuth**：支持第三方登录（动态加载，最多 2 个），通过 `GET /auth/oauth/providers` API 获取
- **登录页**：双栏布局，左栏展示订阅套餐，右栏为登录表单

---

## 导航系统

### 顶部导航（Header Nav）

从 `header_nav` 表读取，按 `site='platform'` 筛选，按 `sort_order` 排序：

```sql
SELECT title, url FROM header_nav
WHERE site='platform' AND is_enabled=1
ORDER BY sort_order ASC
```

### 底部页脚（Footer）

由 `load_footer_data()` 函数统一加载，包含：

| 数据 | 来源表 | 说明 |
|------|--------|------|
| 社交媒体链接 | `social_media_links` | 图标 + URL + hover 文字 |
| 联系邮箱 | `system_config` | key=`contact_email` |
| 页脚导航分区 | `footer_links` | 按 section 分组 |
| 下栏导航 | `footer_nav` | 底部一排链接 |
| 推荐文章 | `footer_articles` | 页脚文章展示 |
| 合作伙伴 | `partner_links` | 带图标的外链 |

---

## 主题系统

Platform 支持 **Jinja2 模板覆盖 + CSS 主题**：

1. **模板覆盖**：`ChoiceLoader` 先搜索 `themes/<slug>/templates/`，再搜索默认模板路径
2. **主题 CSS**：通过 `theme_css_url` 上下文变量注入到模板
3. **静态文件**：`/themes/<slug>/<path>` 路由服务主题静态资源

主题目录结构：

```
themes/
  └── <slug>/
       ├── templates/     ← 可覆盖平台模板
       └── theme.css      ← 主题样式
```

---

## 安全策略

Platform 采用多层安全策略：

| 层 | 实现 |
|----|------|
| **CSP** | `script-src 'self' 'unsafe-inline' unpkg.com cdn.jsdelivr.net` |
| **HTTP 头** | X-Frame-Options: DENY, X-XSS-Protection, X-Content-Type-Options |
| **Referrer** | `strict-origin-when-cross-origin` |
| **验证码** | 拼图验证码（captcha service 8090），内存限速（10次/分钟/IP） |
| **登录** | HttpOnly + Secure + SameSite=Lax Cookie |
| **HTML 净化** | 白名单标签过滤（`sanitize_html()`）|

---

## 注册的 Blueprint 清单

| Blueprint | 来源 | 注册名 | 用途 |
|-----------|------|--------|------|
| `auth_bp` 等 | auth-center | — | SSO 登录/注册/重置密码（排除 admin/cms_admin） |
| `cms_bp` | `cms_public.py` | `'cms'` | CMS 公开页面 |
| `sub_bp` | auth-center | `'platform_subscription'` | 订阅相关 |
| `api_v1_bp` | `routes/api_v1.py` | — | API v1 |
| `douyin_mp_bp` | auth-center | — | 抖音小程序 |
| `shop_public_bp` | `routes/shop_public.py` | — | 公开商城 |
| `site_bp` | `routes/site_routes.py` | `'site'` | 多租户站点 |

---

## 关键文件索引

| 文件 | 路径 |
|------|------|
| 主入口 | [file:///F:/Sites/VeroRunSystem/platform/app.py](file:///F:/Sites/VeroRunSystem/platform/app.py) |
| CMS 公开路由 | [file:///F:/Sites/VeroRunSystem/platform/cms_public.py](file:///F:/Sites/VeroRunSystem/platform/cms_public.py) |
| 站点路由 | [file:///F:/Sites/VeroRunSystem/platform/routes/site_routes.py](file:///F:/Sites/VeroRunSystem/platform/routes/site_routes.py) |
| CMS 模型 | [file:///F:/Sites/VeroRunSystem/auth-center/models/cms.py](file:///F:/Sites/VeroRunSystem/auth-center/models/cms.py) |
| 数据库定义 | [file:///F:/Sites/VeroRunSystem/auth-center/models/database.py](file:///F:/Sites/VeroRunSystem/auth-center/models/database.py) |
| 模板目录 | [file:///F:/Sites/VeroRunSystem/platform/templates/](file:///F:/Sites/VeroRunSystem/platform/templates/) |
| 主题目录 | [file:///F:/Sites/VeroRunSystem/themes/](file:///F:/Sites/VeroRunSystem/themes/) |
| 静态文件 | [file:///F:/Sites/VeroRunSystem/platform/static/](file:///F:/Sites/VeroRunSystem/platform/static/) |
| 媒体文件 | [file:///F:/Sites/VeroRunSystem/admin/static/media/](file:///F:/Sites/VeroRunSystem/admin/static/media/) |
