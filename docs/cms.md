# CMS 内容管理系统

> 易站 AI 建站系统的内容管理模块，提供文章发布、栏目管理、页面区块编排和社交平台推送能力。

---

## 目录

- [概览](#概览)
- [数据库结构](#数据库结构)
- [文章管理（Posts）](#文章管理posts)
- [栏目管理（Categories）](#栏目管理categories)
- [区块系统（Blocks）](#区块系统blocks)
- [预览路由（Preview）](#预览路由preview)
- [内容净化（Sanitize）](#内容净化sanitize)
- [社交推送（Social Push）](#社交推送social-push)
- [当前限制](#当前限制)
- [文件索引](#文件索引)

---

## 概览

CMS 模块是 EasyKai 站点的内容基础设施，覆盖三大部分：

| 子系统 | 职责 | 数据表 |
|--------|------|--------|
| **文章（Posts）** | 知识库、行业洞察、产品动态等内容发布 | `cms_posts` |
| **栏目（Categories）** | 文章分类与导航组织 | `cms_categories` |
| **区块（Blocks）** | 页面级可视化组件编排（首页、关于、服务等） | `cms_blocks` |

额外提供 `cms_settings` 键值配置表，以及关联的 `social_push_logs` 发布日志表。

---

## 数据库结构

### 1. `cms_posts` — 文章主表

```sql
CREATE TABLE cms_posts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    slug             TEXT UNIQUE NOT NULL,          -- URL 标识（如 "hermes-v2-release"）
    category         TEXT NOT NULL DEFAULT 'insights',  -- 所属栏目（外联 cms_categories.name）
    title            TEXT NOT NULL DEFAULT '',       -- 文章标题
    excerpt          TEXT DEFAULT '',                -- 摘要
    content          TEXT DEFAULT '',                -- HTML 正文（已净化）
    content_format   TEXT DEFAULT 'html',            -- 内容格式
    cover_image      TEXT DEFAULT '',                -- 封面图 URL
    author           TEXT DEFAULT '',                -- 作者
    tags             TEXT DEFAULT '[]',              -- JSON 数组
    audience         TEXT NOT NULL DEFAULT 'public', -- 可见范围
    is_published     INTEGER NOT NULL DEFAULT 0,     -- 发布状态（0=草稿, 1=已发布）
    publish_channels TEXT DEFAULT '[]',              -- 发布渠道 JSON
    published_at     TEXT DEFAULT NULL,              -- 发布时间
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cms_posts_cat ON cms_posts(category, published_at);
```

**关键字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `slug` | TEXT UNIQUE | 自动生成 `article-{uuid[:8]}`，创建后可通过更新接口修改 |
| `tags` | TEXT | 存储为 JSON 字符串，如 `["AI","金融","Agent"]` |
| `audience` | TEXT | `public` / `internal`，控制前端可见性 |
| `is_published` | INTEGER | `0` = 草稿，`1` = 已发布 |
| `publish_channels` | TEXT | 发布渠道 JSON，如 `["local:产品动态","wechat","weibo"]` |

### 2. `cms_categories` — 栏目表

```sql
CREATE TABLE cms_categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,           -- 栏目名称（如 "产品动态"）
    icon        TEXT DEFAULT '📄',       -- 图标 emoji
    slug        TEXT DEFAULT '',         -- 栏目 URL slug
    audience    TEXT NOT NULL DEFAULT 'public',
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);
```

系统初始化时自动插入 7 个默认栏目：

| ID | 名称 | slug | audience | sort |
|----|------|------|----------|------|
| 1 | 快速入门 | `getting-started` | public | 1 |
| 2 | Agent 开发 | `agent-dev` | internal | 2 |
| 3 | 金融分析 | `finance` | public | 3 |
| 4 | 最佳实践 | `best-practices` | internal | 4 |
| 5 | 产品动态 | `insights` | public | 5 |
| 6 | 帮助中心 | `help` | public | 6 |
| 7 | 法律合规 | `legal` | public | 90 |

### 3. `cms_blocks` — 区块表

```sql
CREATE TABLE cms_blocks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    page          TEXT NOT NULL,              -- 所属页面（home / brand / services / download / docs）
    section       TEXT NOT NULL,              -- 区块区域标识（hero / products / cta-final 等）
    block_type    TEXT NOT NULL DEFAULT 'text',
    position      INTEGER NOT NULL DEFAULT 0, -- 排序序号
    title         TEXT DEFAULT '',
    subtitle      TEXT DEFAULT '',
    content       TEXT DEFAULT '',
    image_url     TEXT DEFAULT '',
    link_url      TEXT DEFAULT '',
    link_text     TEXT DEFAULT '',
    icon          TEXT DEFAULT '',
    extra_json    TEXT DEFAULT '{}',          -- 额外配置（JSON）
    is_published  INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cms_blocks_page ON cms_blocks(page, position);
```

### 4. `cms_settings` — 配置表

```sql
CREATE TABLE cms_settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    description TEXT DEFAULT ''
);
```

存储站点的键值对配置，如 `site_name`、`site_tagline`、`theme` 等。

---

## 文章管理（Posts）

### CRUD 接口

所有接口位于 `/admin/cms/posts`，需要管理员认证。

| 方法 | 路径 | 功能 | 文件位置 |
|------|------|------|----------|
| GET | `/admin/cms/posts` | 列表查询（支持 `limit`/`offset`/`status` 参数） | [cms_admin.py:90](../auth-center/routes/cms_admin.py) |
| POST | `/admin/cms/posts` | 创建文章（自动生成 slug） | [cms_admin.py:100](../auth-center/routes/cms_admin.py) |
| PUT | `/admin/cms/posts/:id` | 更新文章 | [cms_admin.py:111](../auth-center/routes/cms_admin.py) |
| DELETE | `/admin/cms/posts/:id` | 删除文章 | [cms_admin.py:120](../auth-center/routes/cms_admin.py) |
| POST | `/admin/cms/posts/:id/publish` | 统一发布（本地+社交平台） | [cms_admin.py:128](../auth-center/routes/cms_admin.py) |

### Slug 生成策略

创建时自动生成：`article-{uuid4的前8位}`。例如：

```
article-a1b2c3d4
```

管理员可通过 PUT 接口修改 slug 为自定义值（如 `hermes-v2-release`）。

### 草稿/发布流程

- `is_published = 0`：草稿状态，仅管理员可通过预览路由查看
- `is_published = 1`：已发布，前端 `/knowledge`、`/insights` 等页面可见
- `published_at` 字段仅在发布时写入，草稿保存不更新该字段

### 前端展示路由

| 路由 | 功能 | 文件位置 |
|------|------|----------|
| `/knowledge` | 知识库页面（聚合 guides、articles、insights） | [app.py:718](../platform/app.py) |
| `/insights`（通过 `/knowledge` 聚合） | 行业洞察板块 | [app.py:718](../platform/app.py) |

---

## 栏目管理（Categories）

### CRUD 接口

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/admin/cms/categories` | 栏目列表 |
| POST | `/admin/cms/categories` | 创建栏目 |
| PUT | `/admin/cms/categories/:id` | 更新栏目 |
| DELETE | `/admin/cms/categories/:id` | 删除栏目 |
| POST | `/admin/cms/categories/reorder` | 批量排序 |

### 安全删除（Safe-Delete Check）

删除栏目前自动检查 `cms_posts` 中是否有文章引用该栏目名称：

```python
refs = conn.execute(
    "SELECT COUNT(*) as c FROM cms_posts WHERE category IN "
    "(SELECT name FROM cms_categories WHERE id=?)", (cat_id,)
).fetchone()
if refs['c'] > 0:
    return _err(f'该分类下有 {refs["c"]} 篇文章，请先迁移或删除后再操作')
```

有文章引用的栏目禁止直接删除，需先迁移或删除关联文章。

---

## 区块系统（Blocks）

区块是可拖拽编排的页面级内容组件，支持 10 种类型：

| block_type | 用途 | 示例页面 |
|-----------|------|----------|
| `hero` | 首屏大标题 + 副标题 + CTA | home, services, download, docs |
| `trust` | 信任数据条（数字动画） | home |
| `preview` | 产品功能预览卡片 | home |
| `cards` | 卡片式产品/场景展示 | home, services, download, docs |
| `features` | 带图标的功能列表 | home |
| `steps` | 步骤引导（1-2-3-4-5） | home |
| `insights` | 最新动态/博客列表（动态加载） | home |
| `cta` | 行动号召横幅 | home |
| `text` | 自由文本内容块 | brand |
| `gallery` / `team` / `faq` / `pricing` / `contact` | （预留类型） | — |

### 页面（page）维度

区块按页面隔离，目前支持的页面：

| page 值 | 对应站点路由 |
|---------|-------------|
| `home` | `/` 首页 |
| `brand` | `/about` 关于我们 |
| `services` | `/services` 产品服务 |
| `download` | `/download` 下载中心 |
| `docs` | `/docs` 文档中心 |

### 区块 CRUD

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/admin/cms/blocks/:page` | 获取某页面已发布区块 |
| GET | `/admin/cms/blocks/:page/all` | 获取所有区块（含未发布） |
| POST | `/admin/cms/blocks` | 创建区块 |
| PUT | `/admin/cms/blocks/:id` | 更新区块 |
| DELETE | `/admin/cms/blocks/:id` | 删除区块 |
| POST | `/admin/cms/blocks/:page/reorder` | 拖拽排序（提交 id 数组） |

所有数据通过 `get_page_blocks(page)` 方法按 `position` 升序取出，再由模板按 `block_type` 分发渲染。

---

## 预览路由（Preview）

提供两个层次的预览能力：

### 管理员内嵌预览（admin route）

位于 `/admin/cms/preview/<slug>`，直接返回内嵌 HTML：

```
[admin] /admin/cms/preview/<slug>  →  直接内联 HTML（无模板，轻量预览）
```

- **绕过 `is_published` 检查**：使用 `get_post_by_slug_preview()` 方法直接按 slug 查询，不附加发布状态过滤
- 页面顶部显示黄色横幅：「🔍 预览模式 — 仅管理员可见」

### 前端完整预览（public route）

位于 `/preview/<slug>`，使用完整设计系统模板：

```
[public] /preview/<slug>  →  render_template('cms_preview.html')
```

- 已发布文章（`is_published=1`）：直接渲染，任何访客可见
- 未发布文章（`is_published=0`）：验证 JWT token，未登录时重定向到登录页
- 使用 `cms_preview.html` 模板（[cms_preview.html](../platform/templates/cms_preview.html)），带品牌设置、主题 CSS、暗色设计系统

---

## 内容净化（Sanitize）

`sanitize_html()` 方法（[cms.py:243](../auth-center/models/cms.py)）使用白名单模式进行 HTML 净化，不依赖外部库：

### 允许的标签（24 个）

```
p, div, span, h1-h6, ul, ol, li, a, img, br, hr,
strong, em, b, i, u, s, sub, sup,
table, tr, td, th, thead, tbody, tfoot,
blockquote, pre, code, figure, figcaption
```

### 允许的属性（8 个）

```
href, src, alt, title, class, id, style, target, rel, width, height, loading, decoding
```

### 净化流程

1. **移除非白名单标签及其内容**：`script`、`iframe`、`object`、`embed`、`form`、`input`、`textarea`、`select`、`button`、`meta`、`link`、`style`、`base`、`noscript`、`applet`、`audio`、`video`
2. **移除危险自闭合标签**
3. **递归清理属性**：移除 `on*` 事件处理器、过滤 `javascript:` / `vbscript:` / `data:` 等危险协议

每次 `upsert_post()` 调用时自动执行净化。

---

## 社交推送（Social Push）

文章发布时可选择多平台同步推送（[social_push.py](../auth-center/routes/social_push.py)）：

### 支持平台

| 平台标识 | 名称 | 说明 |
|---------|------|------|
| `wechat` | 微信公众号 | 通过公众号 API 发布图文消息 |
| `weibo` | 微博 | 发布长微博 |
| `toutiao` | 今日头条 | 发布头条文章 |
| `douyin_video` | 抖音视频 | 视频内容推送 |

### 发布流程

统一发布接口 `POST /admin/cms/posts/:id/publish` 接收 `channels` 数组：

```json
{
  "channels": ["local:产品动态", "wechat", "weibo"],
  "auto_publish": true,
  "published_at": "2026-06-27T10:00:00"
}
```

- **`local:*` 前缀**：表示本地站点发布，冒号后为栏目名称
- **`wechat` / `weibo` / `toutiao` / `douyin_video`**：推送到对应社交平台
- **`auto_publish`**：控制社交平台是否立即发布（`false` 时为草稿待审核）

推送结果会记录到 `social_push_logs` 表中，包含 `platform`、`status`、`media_id`、`error_msg` 等字段。

---

## 当前限制

1. **无无限级分类**：`cms_categories` 为扁平结构，不支持父子层级分类
2. **无阅读计数**：`cms_posts` 不含 `read_count` 或 `view_count` 字段
3. **无版本/修订历史**：每次 `upsert_post()` 直接覆盖内容，不保留历史版本
4. **无定时发布**：`published_at` 仅为记录字段，系统不做定时发布调度
5. **无全文搜索**：文章搜索依赖 SQL `LIKE` 查询，未引入全文索引
6. **无 SEO 元数据**：文章级别不支持独立 `meta_description` / `og:image` 覆盖
7. **无批量操作**：不支持批量发布、批量删除、批量迁移分类

---

## 文件索引

| 文件 | 说明 |
|------|------|
| [auth-center/models/cms.py](../auth-center/models/cms.py) | 数据模型层：`init_cms_tables()`、所有 CRUD 函数、`sanitize_html()` |
| [auth-center/routes/cms_admin.py](../auth-center/routes/cms_admin.py) | 管理后台路由：区块/文章/栏目/配置的 API 端点 |
| [auth-center/routes/social_push.py](../auth-center/routes/social_push.py) | 社交平台推送逻辑 |
| [platform/app.py](../platform/app.py) | 前端路由：`/knowledge`、`/preview/<slug>` |
| [platform/templates/cms_preview.html](../platform/templates/cms_preview.html) | 文章预览模板（含暗色设计系统） |
| [scripts/seed_cms.py](../scripts/seed_cms.py) | 初始数据填充脚本 |

---

> 本文档对应系统版本：EasyKai CMS v1.0
