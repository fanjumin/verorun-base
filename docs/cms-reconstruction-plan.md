# CMS 模块重构方案与执行计划

> 版本：v1.3 | 日期：2026-07-08 | 状态：Phase 1/2 完成；Phase 3 部分完成（3.1~3.3、3.8 已落地，3.4~3.7 待办）| 验证：静态检测通过

---

## 目录

- [一、背景与问题分析](#一背景与问题分析)
- [二、重构目标与原则](#二重构目标与原则)
- [三、删减清单](#三删减清单)
- [四、菜单结构重构方案](#四菜单结构重构方案)
- [五、Content Factory 与 CMS 统一方案](#五content-factory-与-cms-统一方案)
- [六、AI 深度集成方案](#六ai-深度集成方案)
- [七、工作流与定时任务集成方案](#七工作流与定时任务集成方案)
- [八、数据库变更清单](#八数据库变更清单)
- [九、执行计划（分阶段）](#九执行计划分阶段)
- [十、风险与回滚](#十风险与回滚)
- [十一、文件索引](#十一文件索引)

---

## 一、背景与问题分析

### 1.1 现状总结

系统在演进过程中陆续增加了 Content Factory（内容工厂）、Agent 内容生成、Social Push（社交发布）、AI 工具集等功能，但核心 CMS 模块没有相应重构，导致功能叠加而非整合。

### 1.2 已识别的问题

| # | 问题 | 严重程度 | 涉及文件 |
|---|------|---------|---------|
| 1 | CMS 编辑器内 Tab1~4（AI对话/PPT/图片/多媒体）与侧边栏 **AI Create** 分组完全重复 | **高** | `cms.html`, `icons.html` |
| 2 | CMS 编辑器与 Content Factory 两套写入流程操作同一张 `cms_posts` 表，UI 完全隔离 | **高** | `cms_admin.py`, `content_factory.py`, `cms.html`, `contentfactory.html` |
| 3 | Post Audit 审核的是 `agent_experiences` 表，审核后无法自动进入 CMS 发布流程 | **中** | `posts.html`, `admin.py` |
| 4 | 静态页面生成有两个入口（CMS 编辑器 + Content Factory API） | **中** | `cms.html`, `content_factory.py` |
| 5 | 社交发布（Social Push）配置分散在 CMS 编辑器和 Content Factory 两处 | **中** | `social_push.py`, `cms_admin.py`, `cms.html` |
| 6 | 导航管理分拆两处（nav_settings + headernav） | **低** | `nav_settings.html`, `headernav.html` |
| 7 | AI Create 分组命名模糊，与 Content 分组中的 AI 工具定位不清 | **中** | `icons.html` |

---

## 二、重构目标与原则

### 2.1 目标

1. **消除功能重复**：合并重叠入口，减少用户困惑
2. **统一内容视图**：所有内容（手动/工厂/Agent）在一个页面管理
3. **AI 深度嵌入**：AI 工具为内容创作服务，融入编辑器而非独立存在
4. **自动化串联**：Content Factory + 工作流引擎 + 定时任务形成完整的内容生产流水线

### 2.2 原则

- **不重写后端核心逻辑**：只重构菜单结构、页面入口、数据视图
- **向后兼容**：所有现有 API 路由不变，仅前端重新编排
- **渐进式**：分 3 个阶段执行，每阶段可独立上线
- **数据不动代码动**：尽量减少数据库变更，优先通过代码/配置实现

---

## 三、删减清单

### 3.1 直接删除（无副作用）

| 删除对象 | 位置 | 理由 |
|---------|------|------|
| CMS 编辑器内 Tab1~4 切换按钮及对应渲染函数 | `cms.html` 第 51~60 行附近 | 功能已被侧边栏 AI Create 分组完全覆盖 |
| CMS 编辑器底部的 "Generate Full Site Static Pages" 按钮 | `cms.html` 第 17 行 | Content Factory 已有相同功能的独立 API |
| CMS 编辑器内的 Tab 函数：`cmsTabAiChat()`, `cmsTabPpt()`, `cmsTabImage()`, `cmsTabMedia()` | `cms.html` 中对应函数定义 | 删除重复入口 |

### 3.2 移动/合并（非删除）

| 对象 | 从 | 到 | 操作方式 |
|------|---|----|---------|
| Post Audit（文章审核） | `Risk & Audit` 分组 | `Content > All Content` 的筛选视图 | 不删代码，只改菜单映射 |
| Social Push（社交发布） | 无独立菜单，分散各处 | `Automation > Social Push` | 在 `icons.html` 中增加菜单项，路由不变 |
| AI Create 分组 | 一级分组 | 更名为 **AI Tools** | 改 `icons.html` 分组标签 |
| Risk & Audit 分组 | 一级分组 | **可删除**，Comment Moderation 移入 Content | 改 `icons.html` |

### 3.3 不改动的部分

- Download Management（下载管理）
- Media Library（媒体库）
- Categories（栏目管理）
- Model Management（AI 模型配置）
- Navigation Settings（导航设置）
- 所有后端 API 路由

---

## 四、菜单结构重构方案

### 4.1 新侧边栏菜单（修改 `icons.html` 的 GROUPS 数组）

```
Dashboard（仪表盘）
AI Chat（AI 对话）

Content（内容管理）
  ├── All Content     ← 新增：统一内容列表（所有来源）
  ├── Create Article  ← 从 Omni-Media Creation 拆分出的纯编辑器
  ├── Content Factory ← 原名 Capture，改名明确定位
  ├── Categories      ← 栏目管理（从 CMS 编辑器独立出来）
  ├── Downloads       ← 保持不变
  └── Media Library   ← 保持不变

AI Tools（AI 工具集）       ← 原名 AI Create，改名聚焦
  ├── AI Writing       ← AI 写文章
  ├── AI Image         ← AI 配图
  ├── AI Format        ← AI 排版
  └── AI Chat          ← AI 对话辅助

Automation（自动化工作流）  ← 从 Strategy 提升为一级
  ├── Workflows        ← DAG 工作流编排（已有）
  ├── Cron Jobs        ← 定时任务管理（已有）
  ├── Social Push      ← 社交发布（从分散整合至此）
  └── Publish History  ← 发布历史

System（系统）
  └── ...（保持不变）

Strategy（策略）             ← 去掉 Automation 子项
  ├── Matrix
  ├── Cleaner
  └── IM Gateway（原 Channels）

Operations（运营）
  └── ...（保持不变）

Messages & Support（消息与支持）
  └── ...（保持不变）

Customer Management（客户管理）
  └── ...（保持不变）

International（国际化）
  └── ...（保持不变）

Ops Data（运营数据）
  └── ...（保持不变）

Plugin Management（插件管理）
  └── ...（保持不变）
```

**关键变更总结**：

| 操作 | 说明 |
|------|------|
| 删除 | Risk & Audit 分组 |
| 删除 | AI Create 分组（改名重建） |
| 提升 | Automation 从 Strategy 子项提升为一级分组 |
| 新增 | Content > All Content |
| 新增 | Automation > Social Push |
| 新增 | Automation > Publish History |
| 更名 | Capture → Content Factory |
| 更名 | Omni-Media Creation → Create Article |
| 更名 | AI Create → AI Tools |
| 拆分 | Strategy 去掉 Automation 相关子项 |

### 4.2 函数映射保持不变

所有 `l_xxx()` 函数名和实现不变，仅修改 GROUPS 中的调用方式：

```javascript
// 当前
["Content", true, [
  ["contentfactory", I.contentfactory, "Capture"],
  ["cms", I.cms, "Omni-Media Creation"],
  ...
]]

// 目标
["Content", true, [
  ["all_content", I.all_content, "All Content"],         // 新增函数
  ["cms", I.cms_simple, "Create Article"],               // 简化后的编辑器
  ["contentfactory", I.contentfactory, "Content Factory"],// 原名 Capture
  ["categories", I.categories, "Categories"],            // 独立出栏目管理
  ["downloads", I.downloads, "Download Management"],
  ["media_library", I.media_library, "Media Library"],
]]
```

---

## 五、Content Factory 与 CMS 统一方案

### 5.1 核心设计：Content Bus（内容总线）

```
                         ┌──────────────┐
                         │  All Content │ ← 统一视图
                         │  (统一的     │
                         │  内容列表)   │
                         └──────┬───────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   ┌───────────┐       ┌──────────────┐       ┌──────────────┐
   │ 手动创建  │       │ 内容工厂生产 │       │ Agent 生成    │
   │ source=   │       │ source=      │       │ source=      │
   │ 'manual'  │       │ 'factory'    │       │ 'agent'      │
   └───────────┘       └──────────────┘       └──────────────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                                ▼
                        ┌──────────────┐
                        │  cms_posts   │
                        │  (+source    │
                        │   字段)      │
                        └──────────────┘
```

### 5.2 cms_posts 表变更

```sql
-- 新增字段
ALTER TABLE cms_posts ADD COLUMN source TEXT DEFAULT 'manual';
-- source 取值: 'manual'(手动创建), 'factory'(内容工厂), 'agent'(Agent生成), 'api'(API导入)

ALTER TABLE cms_posts ADD COLUMN source_id INTEGER DEFAULT NULL;
-- 关联原始来源 ID（raw_contents.id / agent_experiences.id）
```

### 5.3 All Content 页面功能

新的 `l_all_content()` 函数提供一个统一内容列表，支持：

- **筛选栏**：All | Manual（手动） | Factory（内容工厂） | Agent（AI生成）
- **状态栏**：All | Draft | Published | Pending Review
- **列表列**：Title | Source（图标标识） | Category | Status | Channels | Date | Actions
- **批量操作**：Publish（发布）、Unpublish（撤回）、Delete（删除）
- **行内操作**：Edit（编辑）、Preview（预览）、Publish

### 5.4 Content Factory 流程增强

在来源管理中增加：

- `启用自动采集` 开关 → 保存时自动创建 cron_jobs 记录
- `采集间隔` → Cron 表达式或分钟数
- `跳过人工审核` 开关 → 低风险内容自动发布
- `AI 加工模板` → 自定义输出格式

---

## 六、AI 深度集成方案

### 6.1 AI Tools 分组

| 菜单项 | 功能 | 后端 API | 状态 |
|-------|------|---------|------|
| AI Writing | 按主题/关键词生成文章 | `POST /admin/social/generate` | 已有 |
| AI Image | 生成配图/封面图 | `POST /admin/content-factory/ai-cover` | 已有 |
| AI Format | 对已有内容做排版优化 | `POST /admin/content-factory/ai-format` | 已有 |
| AI Chat | AI 对话辅助 | `l_ai_chat()` | 已有 |

### 6.2 编辑器内 AI 嵌入

**Create Article** 页面（简化后的 `l_cms_simple()`）增加：

- **工具栏按钮**：AI 润色、AI 续写、AI 翻译、AI 摘要
- **右侧面板**：可折叠的 AI 助手面板，显示 AI 建议
- **一键配图**：根据文章内容自动生成封面图

所有新增功能复用现有的 `ai_content_generator.py` 和 `content_factory` 的 AI API。

---

## 七、工作流与定时任务集成方案

### 7.1 预置内容工作流模板

在 `Automation > Workflows` 中预置 4 个模板：

| 模板名称 | 触发方式 | 节点链 | 用途 |
|---------|---------|--------|------|
| 每日内容采集 | Cron 每天 08:00 | RSS采集 → AI加工 → 低风险自动审核 → 发布 | 自动持续生产内容 |
| 全站静态生成 | Cron 每天 03:00 | 检测新文章 → 增量生成静态页 → 通知 | 静态化加速 |
| 文章同步发布 | 事件触发（文章发布） | 推送到微信/微博/头条 | 多渠道分发 |
| 知识库同步 | 事件触发（文章发布） | 推送到 Cleaner Agent → 知识库 | 知识库建设 |

### 7.2 发布即工作流触发

改造 `publish_post()`（[cms_admin.py](file:///f:/Sites/VeroRun/auth-center/routes/cms_admin.py) 第 129 行）增加事件触发：

```python
# 发布成功后
fire_hook('cms/published', {
    'post_id': post_id,
    'categories': local_cats,
    'social_platforms': social_platforms,
})
```

该 Hook 查找 `workflow_triggers` 表中匹配的工作流并执行。

### 7.3 定时采集

在 Content Factory 来源管理中，保存时自动同步到 cron_jobs：

```python
# 伪代码
if source.auto_crawl:
    upsert_cron_job(
        name=f"crawl_source_{source.id}",
        cron_expr=to_cron(source.crawl_interval),
        target_type='workflow',
        target_config={'workflow_id': crawl_workflow_id, 'source_id': source.id}
    )
```

---

## 八、数据库变更清单

| 表 | 变更类型 | 变更内容 | 影响范围 |
|---|---------|---------|---------|
| `cms_posts` | **新增字段** | + `source` TEXT DEFAULT 'manual' | 所有读取 cms_posts 的地方 |
| `cms_posts` | **新增字段** | + `source_id` INTEGER DEFAULT NULL | 仅 Content Factory 和 Agent 写入时需要 |
| `content_sources` | **新增字段** | + `auto_crawl` INTEGER DEFAULT 0 | 来源管理页 |
| `content_sources` | **新增字段** | + `crawl_cron` TEXT DEFAULT NULL | 来源管理页 |
| `content_sources` | **新增字段** | + `skip_review` INTEGER DEFAULT 0 | 审核流程判断 |
| `content_sources` | **新增字段** | + `ai_prompt_template` TEXT DEFAULT NULL | AI 加工流程 |
| `workflow_triggers` | **新建表** | event, workflow_id, match_rules(JSON), is_active | 事件驱动工作流 |

---

## 九、执行计划（分阶段）

### 阶段一：菜单重构 + 删减重复（预计 1~2 天）

**目标**：重建菜单结构，删除明显重复的入口

| 步骤 | 任务 | 涉及文件 | 交付物 |
|------|------|---------|--------|
| 1.1 | 修改 `icons.html` 的 GROUPS 数组，按新菜单结构重组 | `icons.html` | 侧边栏新结构上线 |
| 1.2 | 删除 `cms.html` 中 Tab1~4 的切换按钮和渲染函数 | `cms.html` | CMS 编辑器只保留文章编辑 |
| 1.3 | 删除 `cms.html` 中的静态生成按钮 | `cms.html` | 删除重复入口 |
| 1.4 | 新增 `l_cms_simple()` 函数作为 Create Article 入口 | `cms.html` | 纯净的文章编辑器 |
| 1.5 | `l_cms()` 保留作为旧入口兼容（加迁移提示） | `cms.html` | 向后兼容 |

**验证**：确认所有页面渲染正常，无 JS 错误

---

### 阶段二：All Content 统一列表 + Content Factory 增强（预计 2~3 天）

**目标**：实现统一内容视图，打通 Content Factory 与 CMS 的数据流

| 步骤 | 任务 | 涉及文件 | 交付物 |
|------|------|---------|--------|
| 2.1 | 执行数据库迁移（新增 source/source_id 字段） | `database.py` | 表结构就绪 |
| 2.2 | 新增 `l_all_content()` 前端页面 | `all_content.html`（新建） | 统一内容列表页 |
| 2.3 | 修改 Content Factory 发布逻辑，写入 source='factory' | `content_factory.py` | 数据源可追溯 |
| 2.4 | 查看 Agent 审核列表是否需写入 source='agent'（可选） | `admin.py`, `posts.html` | Agent 内容可追溯 |
| 2.5 | Content Factory 来源管理增加定时/审核/模板配置 | `contentfactory.html`, `content_factory.py` | 来源配置增强 |
| 2.6 | 新增 `l_content_factory()` 重命名为 Content Factory | 改菜单映射即可 | 名称更新 |

**验证**：新建文章、Content Factory 发布、Agent 文章都能在 All Content 中看到

---

### 阶段三：Automation 分组 + 工作流模板 + Social Push 整合（预计 2~3 天）

**目标**：将 Social Push 迁入 Automation，预置工作流模板，实现发布即触发

| 步骤 | 任务 | 涉及文件 | 交付物 | 状态 |
|------|------|---------|--------|------|
| 3.1 | 在菜单中加入 Automation > Social Push 和 Publish History | `icons.html` | 入口就绪 | ✅ 完成 |
| 3.2 | Social Push 页面接入菜单（复用现有 `l_social` + social_push.py API） | `icons.html`, `social.html` | Social Push 管理页 | ✅ 完成（`l_social` 原为孤立页，已接入 `social` 菜单键） |
| 3.3 | 新增 `l_publish_history()` 独立发布历史页 | `social.html` | 发布历史统一视图 | ✅ 完成（复用 `/admin/social/history` API） |
| 3.4 | 预置 4 个内容工作流模板 | `orchestrator/workflow_templates.py`, `routes.py` | 开箱即用的模板 | ✅ 完成（只读蓝图 + `GET /admin/automation/workflow-templates`） |
| 3.5 | 改造 `publish_post()` 触发匹配工作流 | `cms_admin.py`, `orchestrator/trigger_dispatch.py` | 发布可触发工作流 | ✅ 完成（fire-and-forget，失败静默不影响发布） |
| 3.6 | 新建 `workflow_triggers` 表 | `orchestrator/models.py` | 事件驱动基础 | ✅ 完成（建在 orchestrator 库，幂等） |
| 3.7 | 删除 `Risk & Audit` 菜单分组 | `icons.html` | 菜单精简 | ⬜ 待办（破坏性操作，需单独确认） |
| 3.8 | 删除 AI Create 分组，替换为 AI Tools | `icons.html` | 菜单精简 | ✅ 完成（Phase 1 已落地） |

**验证**：工作流模板可加载、Social Push 页面正常、发布触发工作流正常

> ✅ **已修复（2026-07-08）**：`orchestrator/models.py` 的 `get_db()` 上下文管理器原先退出时只 `close()` 不 `commit()`，导致 `create_workflow`/`create_cron_job`/`update_*`/`delete_*` 等写函数的操作在连接关闭时被回滚。现已修改 `get_db()`：正常退出自动 `commit()`、异常 `rollback()`。已验证 create/update/delete 工作流、create cron、异常回滚均正确，且原有显式 commit 的函数不受影响。至此 3.5 的"发布触发工作流"可端到端生效。

---

## 十、风险与回滚

### 10.1 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 现有用户习惯被打乱 | **中** | 中 | 保留旧入口 1 周，加迁移提示条 |
| 新 All Content 页面性能问题 | **低** | 高 | 后端增加分页和搜索，前端做虚拟滚动 |
| 数据库迁移出错 | **低** | 中 | 所有变更可回滚，先备份再执行 |
| 工作流触发影响发布流程 | **低** | 高 | Hook 采用 fire-and-forget 模式，不阻塞主流程 |

### 10.2 回滚方案

| 阶段 | 回滚操作 |
|------|---------|
| 阶段一 | 恢复 `icons.html` 的 GROUPS 数组到旧版本 |
| 阶段二 | 移除新增字段（ALTER 语句不删列），删除 `all_content.html` |
| 阶段三 | 删除 `workflow_triggers` 表，回滚 `icons.html` 菜单，恢复 `cms_admin.py` 的 publish_post |

### 10.3 灰度策略

1. 阶段一可随时上线/回滚（只改前端菜单映射）
2. 阶段二先在测试环境验证 All Content 页面，确认数据无误后上线
3. 阶段三的工作流触发功能先做手动测试，验证通过后再放开

---

## 十一、文件索引

### 11.1 需要修改的文件

| 文件 | 阶段 | 修改内容 |
|------|------|---------|
| `admin/templates/partials/icons.html` | 一、三 | 重写 GROUPS 数组 |
| `admin/templates/partials/cms.html` | 一 | 删除 Tab1~4、静态生成按钮；新增 `l_cms_simple()` |
| `admin/templates/partials/posts.html` | 二 | 改为 All Content 可筛选的视图（或新建） |
| `admin/templates/partials/contentfactory.html` | 二 | 来源管理增加定时/审核/AI模板配置项 |
| `auth-center/routes/cms_admin.py` | 三 | publish_post 增加 Hook 事件触发 |
| `auth-center/routes/content_factory.py` | 二 | 写入 source='factory'，增加定时任务同步 |
| `auth-center/models/database.py` | 二、三 | cms_posts 加字段，新建 workflow_triggers 表 |

### 11.2 需要新建的文件

| 文件 | 阶段 | 用途 |
|------|------|------|
| `admin/templates/partials/all_content.html` | 二 | 统一内容列表页面 JS |
| `admin/templates/partials/social_push.html` | 三 | Social Push 管理页面 |
| `admin/templates/partials/publish_history.html` | 三 | 发布历史统一视图 |

### 11.3 不修改但需知晓的文件

| 文件 | 用途 |
|------|------|
| `auth-center/routes/social_push.py` | API 路由不变，仅菜单入口迁移 |
| `orchestrator/scheduler.py` | APScheduler 引擎，不变 |
| `orchestrator/workflow_engine.py` | DAG 工作流引擎，不变 |
| `orchestrator/nodes.py` | 节点处理器 registry，不变 |
| `auth-center/services/ai_content_generator.py` | AI 服务，不变 |
| `auth-center/services/content_factory/ai_processor.py` | AI 加工引擎，不变 |

---

## 十二、补充事项

### 12.1 图标补全（2026-07-08）

静态检测发现 `admin/templates/partials/icons.html` 的 `I` 对象缺少 6 个被菜单引用的图标定义，会触发前端 `I.xxx is not a function` 错误。本次同步补全：

| 图标键 | 用途 | SVG 含义 |
|--------|------|---------|
| `admins` | 用户组/管理员列表 | 用户组 + 头像徽章 |
| `ai_chat` | AI 对话终端 | 终端框 + AI 节点 |
| `channels` | IM 渠道/网关 | 对话气泡 |
| `email` | 邮件营销 | 信封 |
| `logs` | 审计日志 | 文档列表 |
| `tickets` | 工单系统 | 票据 + 销孔 |

**变更文件**：
- `admin/templates/partials/icons.html` — 在 `posts` 定义后追加 6 行 `S('...')`

**风险**：纯 SVG 字符串追加，无任何逻辑依赖。所有 SVG 已通过 `viewBox`/`stroke` 兼容性检查（与既有图标风格一致）。

---

## 附录 A：新旧菜单对照表

| 旧菜单 | 新菜单 | 操作 |
|-------|-------|------|
| Dashboard > Dashboard | Dashboard > Dashboard | 不变 |
| AI Chat > Command Console | AI Chat > Command Console | 不变 |
| **System** | **System** | 不变 |
| **Content > Capture** | **Content > Content Factory** | **更名** |
| **Content > Omni-Media Creation** | **Content > Create Article** | **拆分**，AI工具Tab移除 |
| — | **Content > All Content** | **新增** |
| — | **Content > Categories** | **新增**（从编辑器独立） |
| Content > Download Management | Content > Download Management | 不变 |
| Content > Media Library | Content > Media Library | 不变 |
| **AI Create** | **AI Tools** | **更名重组** |
| AI Create > PPT/Image/Multimedia | AI Tools > AI Writing/Image/Format/Chat | **重组** |
| **Strategy > Automation** | **Automation** | **提升为一级** |
| — | Automation > Social Push | **新增**（从分散整合） |
| — | Automation > Publish History | **新增** |
| **Risk & Audit** | **删除** | 内容并入 Content/保留Comment |
| Risk & Audit > Post Audit | Content > All Content（筛选视图） | **迁移** |
| Risk & Audit > Comment Moderation | Content > Comments | **迁移** |

---

## 附录 B：API 兼容性说明

**所有现有 API 路由不变**，仅修改前端调用方式：

| 旧前端函数 | 新前端函数 | API 路由 | 备注 |
|-----------|-----------|---------|------|
| `l_cms()` | `l_cms_simple()` | 同 `/admin/cms/*` | 简化版编辑器 |
| `l_posts()` | `l_all_content()` 含 source='agent' 筛选 | 同 `/admin/posts` | 统一视图 |
| `l_contentfactory()` | 同名 | 同 `/admin/content-factory/*` | 不变 |
| `cmsPublishPost()` | 复用 | 同 `POST /admin/cms/posts/{id}/publish` | 不变 |

---

> 本文档由 2026-07-08 的系统分析生成，将随执行进度更新。
