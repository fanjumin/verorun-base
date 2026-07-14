# Site Builder — AI 一键建站开发参考

> 版本: v1.0 | 更新日期: 2026-07-14  
> 模块位置: `site_builder/`

---

## 目录

1. [架构总览](#1-架构总览)
2. [建站流程（三阶段 DAG）](#2-建站流程三阶段-dag)
3. [API 参考](#3-api-参考)
4. [设计令牌系统（Site Settings）](#4-设计令牌系统site-settings)
5. [提示词模板标准](#5-提示词模板标准)
6. [生成器扩展](#6-生成器扩展)
7. [Agent 集成](#7-agent-集成)

---

## 1. 架构总览

### 1.1 模块关系

```
site_builder/
├── engine.py                # 核心引擎：三阶段 DAG 编排
├── routes.py                # 25+ API 端点（/admin/site-builder/*）
├── models.py                # 数据模型（4 张表）
│
├── generators/              # 建站生成器（CMS 层）
│   ├── brand.py             # 品牌写入
│   ├── theme.py             # 主题写入
│   ├── navigation.py        # 导航写入
│   └── pages.py             # 页面区块/文档写入
│
├── site_settings/           # 统一设计令牌系统
│   ├── models.py            # design_tokens 表
│   ├── routes.py            # 14+ API 端点（/admin/site-settings/*）
│   ├── token_service.py     # 令牌校验、合并
│   └── token_renderer.py    # 令牌 → CSS/HTML
│
├── mini_app/                # 小程序生成（见 mini-app-generator-standard.md）
│
├── prompts/                 # 内置行业提示词模板
└── i18n/                    # 国际化翻译
```

### 1.2 数据库表

| 表名 | 用途 | 说明 |
|------|------|------|
| `site_builder_prompts` | 行业提示词模板 | 内置 4 个 + 用户自定义 |
| `site_builder_tasks` | 建站任务记录 | task_id → 状态 → 结果 |
| `design_tokens` | 统一设计令牌 | 替代 5 张旧表（§4） |
| `mini_app_projects` / `mini_app_versions` | 小程序项目/版本 | 见独立文档 |

### 1.3 重要路径

| 路径 | 说明 |
|------|------|
| `site_builder/prompts/` | 内置 YAML 模板（`tech_company.yml` 等 4 个） |
| `site_builder/mini_app/templates/` | 各平台小程序模板文件 |
| `site_builder/mini_app/workspace/` | 生成产物缓存（gitignored） |

---

## 2. 建站流程（三阶段 DAG）

### 2.1 流程图

```
用户输入（自然语言）
      │
      ▼
Phase 1: parse_requirement()
  → 调用 LLM 解析：品牌名称、行业、风格
  → 返回结构化需求（JSON）
      │
      ▼
Phase 2: generate_plan()
  → 按 DAG 顺序调用 LLM 生成各模块
  → 品牌 → 主题 → 导航 → 页面 → 文档
  → 每个模块独立 LLM 调用，互不阻塞
  → 返回完整方案（不写库）
      │
      ▼
Phase 3: execute_plan()
  → 逐项写入数据库（draft 模式）
  → BrandGenerator.apply()
  → ThemeGenerator.apply_theme()
  → NavigationGenerator.apply_nav() + apply_footer()
  → PageGenerator.apply_page_blocks() → cms_blocks
  → PageGenerator.apply_document() → cms_posts
      │
      ▼
publish()
  → backup_tokens() 备份当前生产
  → promote_draft_tokens() draft → 生产
  → UPDATE cms_blocks SET is_published=1
  → UPDATE cms_posts SET is_published=1
```

### 2.2 最小化编辑（modify）

支持增量修改，不重新生成整个站点：

```
POST /admin/site-builder/modify
{
  "task_id": "...",
  "user_input": "把首页标题改成蓝色"
}

→ LLM 定位目标区块 → delta 应用 → 结果写回
```

支持操作类型：`modify_block` | `add_block` | `delete_block` | `reorder`

---

## 3. API 参考

所有端点前缀: `/admin/site-builder/`

### 3.1 提示词模板管理

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/prompts` | 列出模板（支持 `active_only`、`industry` 过滤） |
| GET | `/prompts/<identifier>` | 获取单个模板详情 |
| POST | `/prompts` | 创建自定义模板 |
| PUT | `/prompts/<int:prompt_id>` | 更新模板 |
| DEL | `/prompts/<int:prompt_id>` | 删除模板（仅自定义） |

### 3.2 建站流程

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/preview` | 生成建站方案预览（Phase 1+2，不写库） |
| POST | `/execute` | 执行建站（Phase 3，写入 draft 模式） |
| POST | `/publish` | 发布草稿到生产 |
| GET | `/draft-data` | 获取草稿数据（前端预览渲染） |
| GET | `/preview-site` | 渲染草稿站点预览页面 |
| POST | `/modify` | 最小化增量修改 |

### 3.3 建站任务

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/tasks` | 列出建站任务 |
| GET | `/tasks/<task_id>` | 获取任务详情 |

### 3.4 页面摘要

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/page-summary/<page>` | 获取指定页面区块摘要（供 LLM 修改上下文） |

### 3.5 小程序生成

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/mini-app/projects` | 列出小程序项目 |
| POST | `/mini-app/projects` | 创建项目 |
| GET | `/mini-app/projects/<id>` | 项目详情（含版本历史） |
| DEL | `/mini-app/projects/<id>` | 删除项目 |
| GET | `/mini-app/projects/<id>/versions` | 版本列表 |
| GET | `/mini-app/versions/<vid>/download/<platform>` | 下载版本包 |
| GET | `/mini-app/platforms` | 列出支持平台 |
| PUT | `/mini-app/platforms/<platform>` | 更新平台配置 |
| POST | `/mini-app/generate` | 触发异步生成（返回 task_id） |
| GET | `/mini-app/status/<task_id>` | 查询生成状态 |
| GET | `/mini-app/download/<platform>/<task_id>` | 下载生成结果 |
| POST | `/mini-app/deploy/<platform>` | 部署到平台 |

### 3.6 Site Settings 端点

见 §4.4。

---

## 4. 设计令牌系统（Site Settings）

### 4.1 概述

`site_settings/` 子模块用一套设计令牌统一替代了旧系统 5 张独立表：

| 旧表 | 替代 |
|------|------|
| `brand_settings` | `design_tokens.token_json.brand` |
| `header_nav` | `design_tokens.token_json.navigation` |
| `footer_links` | `design_tokens.token_json.footer` |
| `footer_articles` | `design_tokens.token_json.footer` |
| `site_theme_config` | `design_tokens.token_json.colors/typography` |

### 4.2 design_tokens 表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `site_key` | TEXT | 站点标识（默认 `'default'`） |
| `token_json` | TEXT | 生产环境令牌（JSON） |
| `draft_json` | TEXT | 草稿令牌（JSON） |
| `generated_by` | TEXT | 生成方式：`'manual'` / `'ai'` / `'migrated'` |
| `version` | INTEGER | 版本号，每次发布递增 |

### 4.3 令牌 Schema（10 个一级分区）

```json
{
  "brand": {
    "site_name": "VeroRun",
    "tagline": "AI 驱动建站",
    "logo_url": "/static/logo.png",
    "brand_story": "让每个人都能拥有智能网站"
  },
  "colors": {
    "primary": "#4F46E5",
    "secondary": "#10B981",
    "background": "#FFFFFF",
    "text": "#1F2937",
    "accent": "#F59E0B"
  },
  "typography": {
    "heading_font": "Inter",
    "body_font": "Inter",
    "base_size": "16px",
    "heading_weight": "700"
  },
  "navigation": {
    "items": [
      {"label": "首页", "href": "/", "order": 1},
      {"label": "关于", "href": "/about", "order": 2}
    ]
  },
  "footer": {
    "groups": [
      {"title": "产品", "links": [{"label": "功能", "href": "/features"}]}
    ]
  },
  "spacing": { "section_padding": "4rem" },
  "border_radius": { "default": "8px" },
  "shadows": { "card": "0 1px 3px rgba(0,0,0,0.1)" },
  "seo": { "title_template": "%s | VeroRun" },
  "meta": { "schema_version": "1.0" }
}
```

### 4.4 Site Settings API 端点

前缀: `/admin/site-settings/`

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/` | 获取完整设计令牌 |
| PUT | `/` | 更新设计令牌 |
| GET | `/schema` | 获取令牌 JSON Schema |
| GET | `/css` | 获取渲染后的 CSS 变量 |
| GET | `/render` | 获取完整 HTML 片段渲染 |
| GET | `/brand` | 获取品牌设置 |
| PUT | `/brand` | 更新品牌设置 |
| GET | `/navigation` | 获取导航 |
| PUT | `/navigation` | 更新导航 |
| GET | `/footer` | 获取页脚 |
| PUT | `/footer` | 更新页脚 |
| GET | `/colors` | 获取配色 |
| PUT | `/colors` | 更新配色 |
| GET | `/typography` | 获取排版 |
| PUT | `/typography` | 更新排版 |
| POST | `/migrate` | 强制从旧表迁移数据 |

### 4.5 扩展令牌 Schema

新增分区需同步修改：

1. `token_service.py` — `TOKEN_SCHEMA` 常量中添加新分区定义
2. `token_renderer.py` — 添加对应分区的渲染方法
3. `site_settings/models.py` — 无需改表（`token_json` 是 JSON 字段）

---

## 5. 提示词模板标准

### 5.1 YAML 格式

模板文件位于 `site_builder/prompts/*.yml`，结构如下：

```yaml
identifier: tech_company       # 唯一标识
name: 科技公司                  # 显示名称
description: 适用于科技创业公司、SaaS、互联网企业
icon: building                 # 图标（icons.html 体系）
industry: tech                 # 行业标签
tags: ["startup", "saas"]      # 搜索标签

# 预设参数（可选，覆盖 LLM 自动生成）
defaults:
  primary_color: "#2563EB"
  secondary_color: "#7C3AED"

# 页面结构
pages:
  - key: home                  # 页面标识
    name: 首页                  # 显示名称
    sections:                  # 页面区块大纲
      - hero                   # 轮播/主视觉
      - features               # 功能特点
      - pricing                # 定价
      - contact                # 联系方式
  - key: about
    name: 关于我们
    sections:
      - story
      - team

# 法律文档列表
documents:
  - key: privacy
    name: 隐私政策
  - key: terms
    name: 服务协议

# 各阶段 LLM 提示词
prompts:
  parse_requirement: |
    请分析用户以下需求，提取品牌名称、行业类型、设计风格等信息...
  brand: |
    基于以下信息，生成品牌方案...
  pages: |
    为以下页面生成区块内容...
```

### 5.2 内置模板

| 文件 | identifier | 行业 | 页面数 |
|------|-----------|------|--------|
| `tech_company.yml` | tech_company | 科技 | 6 |
| `law_firm.yml` | law_firm | 法律 | 6 |
| `restaurant.yml` | restaurant | 餐饮 | 6 |
| `education.yml` | education | 教育 | 6 |

### 5.3 创建自定义模板

通过 API 创建新模板，支持自定义 `prompts` 各阶段提示词。新模板 `is_builtin=0`，可删除。

---

## 6. 生成器扩展

### 6.1 现有生成器

| 生成器 | 文件 | 写入目标 |
|--------|------|----------|
| `BrandGenerator` | `generators/brand.py` | `design_tokens.draft_json.brand` |
| `ThemeGenerator` | `generators/theme.py` | `design_tokens.draft_json.colors/typography` + CSS 文件 |
| `NavigationGenerator` | `generators/navigation.py` | `design_tokens.draft_json.navigation/footer` |
| `PageGenerator` | `generators/pages.py` | `cms_blocks` / `cms_posts` |

### 6.2 新增生成器

所有生成器均幂等：先清旧数据再写入新数据。

```python
from site_builder.generators import BaseGenerator  # 若有基类

class MyGenerator:
    """自定义生成器示例"""

    def apply(self, plan: dict, site_key: str = 'default'):
        """将 plan 中的对应数据写入数据库"""
        with get_db() as conn:
            # 1. 清除旧数据
            conn.execute("DELETE FROM ...")
            # 2. 写入新数据
            conn.execute("INSERT INTO ...", (...))
            conn.commit()
```

在 `engine.py` 的 `execute_plan()` 中按 DAG 顺序调用新增生成器。

---

## 7. Agent 集成

Site Builder 通过 Agent Matrix 的 **Builder Agent** 与用户交互：

- Agent 识别 `intent == 'site_build'` 时调用 `SiteBuilderEngine`
- 支持 `action == 'execute'`（执行建站）和 `action == 'modify'`（增量修改）
- Builder Agent 角色配置在 `agent_matrix/roles/04-builder.yaml`

---

> **文档维护**  
> 本文档基于 v2026.07 代码生成。API 端点数量和响应格式以实际代码为准。
