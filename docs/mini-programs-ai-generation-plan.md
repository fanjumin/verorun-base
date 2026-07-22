# Mini Programs AI 生成改造 — 实施计划

> 版本: v1.0 | 制定日期: 2026-07-22
> 关联方案: `新建文件夹/mini-programs-ai-generation-plan.md`（原始方案文档）
> 关联文档: `docs/site-builder.md`、`docs/mini-app-generator-standard.md`、`docs/site-widgets-reference.md`

---

## 0. 执行纪律（最高优先级）

### 0.1 绝对不偏离方案

1. **严格按本文档执行**，不擅自优化、不擅自扩展、不顺手改无关代码。
2. **每阶段执行前**，必须在对话中完成 5 问检查（文件清单、改动范围、影响分析、负面清单、验证步骤），经确认后才动手。
3. **修改范围锁定**：只改本文档列出的文件和函数，清单外的文件不 Read、不 Edit、不 Write。

### 0.2 预览编辑框架已存在，不重复建设

- 项目已有完整的 **预览即编辑器**（`ai_site_preview.html` + 8 个 JS 模块），内置移动端设备模拟器（iPhone 多机型）。
- 本项目**仅补齐"提示词 → AI 生成计划 → 接入已有预览编辑器"**这条管线。
- **禁止**重新实现或修改已有的编辑器功能（拖拽排序、内联编辑、颜色面板、间距滑块、撤销重做、导航编辑器等）。

### 0.3 改动纪律

- 每改完一个文件，立即提交（Git 小步提交）。
- 每个阶段独立验证通过后，再进入下一阶段。
- 部署前生成服务器文件快照，部署后 diff 对比，确认无意外文件变动。

---

## 1. 国际化规范（i18n）

### 1.1 翻译架构

项目使用 **DB-first + YAML fallback** 三层翻译架构：

| 层级 | 位置 | 说明 |
|------|------|------|
| DB 层 | `i18n_strings` 表（PostgreSQL） | 管理员可后台编辑，热加载生效 |
| YAML 层 | `i18n/en.yml`、`i18n/zh-CN.yml` | 基础翻译数据的静态存储和 fallback |
| 原文 fallback | — | DB 和 YAML 都找不到时，直接返回原文 |

翻译查找优先级：**DB > YAML fallback > 原文**

### 1.2 Python 文件规范

所有包含用户可见文本的 Python 文件，必须：

```python
from i18n import _    # 文件顶部导入

# 所有用户可见字符串使用 _() 包裹
error_msg = _('请输入小程序需求描述')
success_msg = _('AI 计划生成成功')
flash(_('生成失败，请重试'), 'error')
```

### 1.3 Jinja2 模板规范

```jinja2
<!-- 静态文本：_() 包裹 -->
<span>{{ _('AI 生成') }}</span>
<label>{{ _('描述你的小程序需求') }}</label>

<!-- 禁止：嵌套 _() 和模板变量 -->
<!-- 错误示例：{{ _('{{ brand_name }}') }}  ← 绝对禁止 -->

<!-- 正确做法：变量不套 _() -->
<span>{{ brand_name }}</span>
```

### 1.4 新增翻译 key 流程

1. 代码中使用 `_('原文')` 标记所有用户可见文本。
2. 新增的 key 追加到 `i18n/en.yml`（英文原文）和 `i18n/zh-CN.yml`（中文翻译）。
3. 提交前确认两个 YAML 文件条目数一致。

---

## 2. 目标与范围

### 2.1 目标

让 Mini Programs 模块支持：**用户输入自然语言提示词 → AI 生成结构化计划 → HTML 可视化预览/编辑 → 代码生成 → 多平台打包下载**。

### 2.2 范围界定

| 在范围内 | 不在范围内 |
|----------|-----------|
| 新增 4 个 YAML 提示词模板 | 修改现有编辑器 JS 模块 |
| 新增 `MiniAppPreviewRenderer` 渲染器 | 改造 `ai_site_preview.html` 的编辑器功能 |
| 改造 `/mini-app/generate` 接口（新增 prompt 参数） | 修改设计令牌系统 |
| 新增 `/mini-app/preview/<id>` 和 `/data` 路由 | 修改打包器/部署器 |
| `ai_site_preview.html` 新增 tabBar + Widget 注入点 | 修改 Widget API 端点 |
| `mini_apps.html` 新增 AI 生成标签页 | 新增设备模拟器（已有） |
| Generator 层支持 `ai_plan` 参数 | 修改 CMS/商城/广告后端 |
| `mini_app_versions` 表新增 4 个字段 | 修改 auth-center |

---

## 3. 阶段 A：基础设施（模板 + 数据模型）

### A1. 新增 4 个 YAML 提示词模板

**新增文件**：

| 文件 | identifier | 行业 | 页面数 |
|------|-----------|------|:---:|
| `site_builder/prompts/mini_shop.yml` | mini_shop | 电商/零售 | 4 |
| `site_builder/prompts/mini_service.yml` | mini_service | 服务预约 | 4 |
| `site_builder/prompts/mini_brand.yml` | mini_brand | 品牌展示 | 3 |
| `site_builder/prompts/mini_community.yml` | mini_community | 社区/论坛 | 4 |

**模板结构**（每个 YAML 包含）：
- `identifier`、`name`、`description`、`icon`、`industry`、`tags`
- `mini_app` 专属配置（`tabBar.default`、`supported_features`）
- `defaults`（站点名、行业、风格、主色调等）
- `pages`（页面列表，标注 required）
- `prompts`（`parse`、`brand`、`tabBar`、`page_home`、`page_*` 等 LLM prompt）

**i18n 注意**：模板中的 `name`、`description`、`tags` 中使用 `_()` 标记中文字段。

**验证方式**：`python -c "import yaml; yaml.safe_load(open('site_builder/prompts/mini_shop.yml'))"` 无报错。

---

### A2. `mini_app_versions` 表新增字段

**文件**：`site_builder/models.py`

**新增字段**（ALTER TABLE）：

```sql
ALTER TABLE mini_app_versions ADD COLUMN prompt TEXT DEFAULT '';
ALTER TABLE mini_app_versions ADD COLUMN prompt_template TEXT DEFAULT '';
ALTER TABLE mini_app_versions ADD COLUMN ai_plan_json TEXT DEFAULT '{}';
ALTER TABLE mini_app_versions ADD COLUMN widgets_json TEXT DEFAULT '[]';
```

**Python 模型对应的字段定义**需同步更新。

**风险**：SQLite ALTER TABLE 语法兼容；现有数据默认值保证 NULL 安全。

**验证方式**：执行迁移后 `PRAGMA table_info(mini_app_versions)` 确认字段存在。

---

## 4. 阶段 B：AI 生成管线（后端核心）

### B1. 新增 `MiniAppPreviewRenderer` 类

**新增文件**：`site_builder/mini_app/preview_renderer.py`

**职责**：将 AI 生成的 JSON 计划渲染为 HTML 预览页面，复用现有的 `ai_site_preview.html` 模板。

**公开方法**：

| 方法 | 说明 |
|------|------|
| `__init__(template_path=None)` | 加载 `ai_site_preview.html` 模板 |
| `render(plan, draft_tokens=None)` | 主入口：AI plan JSON → HTML 字符串 |
| `_build_draft_blocks(pages)` | 将 AI 页面 sections 转为 `ai_site_preview.html` 兼容的 block 结构 |
| `_build_draft_tokens(plan)` | 从 AI plan 构建 `design_tokens` 格式（brand/colors/typography/spacing/navigation/footer/seo/meta） |
| `_build_widget_html(widgets)` | 生成 Widget 占位符 HTML |
| `_build_tabbar_html(tabBar)` | 生成小程序底部 tabBar HTML |

**关键设计**：
- `render()` 调用 `render_template_string()` 传入 `draft_tokens`、`draft_blocks`、`mini_app_tabbar`、`mini_app_widgets` 四个变量。
- 默认设备设为 `iphone-12`（小程序预览）。不新增设备模拟器。
- `_build_draft_blocks()` 将 `block_type` 映射到现有 block 结构：`hero` → `{id, title, content, icon, link_text, link_url}`，`grid` → 每个 item 展开为独立 block。

**i18n 注意**：文件顶部 `from i18n import _`，所有硬编码的用户可见字符串使用 `_()` 包裹。

**需要先阅读**：`ai_site_preview.html` 中 `draft_tokens` 和 `draft_blocks` 的确切结构，确保映射正确。

**验证方式**：用固定 mock plan JSON 调用 `render()`，检查输出 HTML 包含正确的 CSS 变量和 DOM 结构。

---

### B2. 改造 `/mini-app/generate` 接口

**文件**：`site_builder/routes.py`

**当前接口**（保持兼容）：

```python
POST /admin/site-builder/mini-app/generate
Body: { "project_id": 1, "platforms": ["douyin", "wechat"], "options": {...} }
```

**改造后**（新增字段，向后兼容）：

```python
POST /admin/site-builder/mini-app/generate
Body: {
    "project_id": 1,
    "platforms": ["douyin", "wechat"],
    "prompt": "生成一个奶茶店小程序...",   # 新增，可选
    "template": "mini_shop",              # 新增，可选
    "options": { ... }
}
```

**改造逻辑**：
- 若 `prompt` 为空 → 走原有静态模板流程（零改动，完全兼容）。
- 若 `prompt` 非空 → 走新 AI 流程：
  1. 加载模板 YAML → `parse_requirement(prompt, tmpl)` → `generate_plan(parsed, tmpl)`
  2. 保存 draft 到 `design_tokens.draft_json` + `mini_app_versions.ai_plan_json`
  3. 返回 `task_id` + `version_id` + `preview_url` + `plan_summary`

**i18n 注意**：返回的 `plan_summary` 中如有用户可见文本，需使用 `_()` 标记翻译键。

**需要先阅读**：`routes.py` 中 `/mini-app/generate` 当前的完整实现。

**验证方式**：POST 不带 `prompt` → 旧流程正常；POST 带 `prompt` → 返回 `preview_url`。

---

### B3. 新增预览和编辑数据 API 路由

**文件**：`site_builder/routes.py`（同 B2）

**新增路由**：

| 路由 | 方法 | 说明 |
|------|------|------|
| `/mini-app/preview/<int:version_id>` | GET | 渲染小程序预览页面 |
| `/mini-app/preview/<int:version_id>/data` | GET | 获取草稿数据（供编辑器 JS API 使用） |

**`/preview/<id>` 逻辑**：
1. 从 DB 读取 `mini_app_versions.ai_plan_json`
2. 实例化 `MiniAppPreviewRenderer`
3. 调用 `renderer.render(plan)` 返回 HTML

**`/preview/<id>/data` 逻辑**：
1. 从 DB 读取 plan
2. 构建与现有编辑器 API 兼容的 `{draft_tokens, draft_blocks}` 格式
3. 返回 JSON（含 `mini_app: True` 标识）

**鉴权**：两个路由均需 admin 登录态（与现有 `/mini-app/generate` 一致）。

**验证方式**：浏览器访问 `/mini-app/preview/<id>` 渲染正常；`/data` 返回的 JSON 与现有编辑器 API 格式一致。

---

## 5. 阶段 C：Generator 层改造（代码生成）

### C1. `engine.py` 新增 `ai_plan` 参数分支

**文件**：`site_builder/mini_app/engine.py`

**改动**：`generate()` 方法新增 `ai_plan=None` 参数。

```python
def generate(self, platforms, options, output_base, ai_plan=None):
    for platform in platforms:
        generator = self._get_generator(platform)
        if ai_plan:
            result = generator.generate_from_plan(ai_plan, platform, options)
        else:
            result = generator.generate(site_config, brand, options)  # 旧流程不变
```

**风险**：回退路径必须稳定。`ai_plan is None` 时必须完全等价于改造前的行为。

**验证方式**：不传 `ai_plan` 调用 `generate()`，输出与改造前一致。

---

### C2. `base.py` 新增 `generate_from_plan()` 基类方法

**文件**：`site_builder/mini_app/generators/base.py`

**新增方法**：`generate_from_plan(ai_plan, platform, options)`

**方法流程**：
1. `self._copy_template(output_dir)` — 复制模板骨架
2. `self._build_app_config_from_plan(ai_plan, platform)` — 生成 `app.json`（含 AI tabBar + 页面路由）
3. `self._render_global_css_from_plan(ai_plan, platform)` — 生成全局样式（CSS 变量注入 AI 主题色）
4. 遍历 `ai_plan.pages`，逐个 `_generate_page_from_plan(page, context, output_dir, platform)`
5. `self._inject_widgets_from_plan(ai_plan.widgets, platform, output_dir)` — 注入 Widget JS SDK

**新增辅助方法**：

| 方法 | 说明 |
|------|------|
| `_build_app_config_from_plan()` | 构建 `app.json`，含 pages/window/tabBar 配置 |
| `_render_global_css_from_plan()` | CSS 变量注入：`--color-primary` 等从 theme 取值 |
| `_generate_page_from_plan()` | 读取平台页面模板 → `_render_sections(sections)` 渲染块内容 → `_render_page_widgets(widgets, page_slug)` 渲染 Widget 占位符 → 替换 `{{ page_title }}` 等模板变量 → 写入文件 |
| `_render_sections()` | 按 `block_type` 分派：`hero` → `<view class="hero-section">`, `grid` → `<view class="grid-container">`, `text` → `<view class="section-block">` |
| `_render_page_widgets()` | 生成页面级 Widget 占位符（`data-widget` 属性） |
| `_inject_widgets_from_plan()` | 写入 `utils/widgets.js`，包含 Widget 初始化逻辑 |

**需要先阅读**：`base.py` 现有的 `generate()` 方法签名和模板变量替换方式。

**验证方式**：用固定 plan JSON 调用 `generate_from_plan()`，检查输出目录文件结构。

---

### C3. 4 个平台 Generator 各实现 `generate_from_plan()`

**文件**：
- `site_builder/mini_app/generators/douyin.py`
- `site_builder/mini_app/generators/wechat.py`
- `site_builder/mini_app/generators/telegram.py`
- `site_builder/mini_app/generators/line.py`

**改动**：每个文件新增 `generate_from_plan()` 方法，继承基类实现。平台差异仅在于：

| 平台 | 文件扩展名 | 配置文件 | 特有 API |
|------|-----------|----------|----------|
| douyin | `.ttml` / `.ttss` | `app.json` | `tt.login()` |
| wechat | `.wxml` / `.wxss` | `app.json` + `project.config.json` | `wx.login()` |
| telegram | `.html` | `manifest.json` | Telegram Web App API |
| line | `.html` | `manifest.json` | LIFF API |

**验证方式**：对每个平台用相同 plan JSON 输入，检查输出文件扩展名和配置文件格式正确。

---

## 6. 阶段 D：前端 UI 改造

### D1. `ai_site_preview.html` 新增 tabBar + Widget 注入

**文件**：`admin/templates/ai_site_preview.html`

**增量改动**（不动现有编辑器代码）：

1. **新增 CSS**：`.mini-app-tabbar` 样式（固定底部、flex 布局、安全区适配）；`.widget-loading`、`.widget-title` 样式；`.preview-content.has-tabbar` 底部留白。
2. **新增 Jinja2 条件块**：`{% if mini_app_tabbar %} {{ mini_app_tabbar|safe }} {% endif %}` 和 `{% if mini_app_widgets %} {{ mini_app_widgets|safe }} {% endif %}`。
3. **devices 配置**：确认 `iphone-12` 等移动端设备配置已存在，不新增。

**不碰的内容**：所有 `<script src="/static/js/editor/xxx.js">` 引用、编辑器初始化代码、设备模拟器 JS 逻辑。

**i18n 注意**：新增的静态文本（如"加载中..."）使用 `{{ _('加载中...') }}`。

**验证方式**：渲染一个带 tabBar 的 Mini App 预览页，检查 tabBar 正确显示在设备模拟器底部，Widget 占位符正确注入。

---

### D2. `mini_apps.html` 新增 AI 生成标签页

**文件**：`admin/templates/partials/mini_apps.html`

**增量改动**（在现有表单上方新增标签切换）：

1. **标签切换 UI**："🤖 AI 生成" / "📋 手动生成" 两个 tab。
2. **AI 面板**：提示词输入框（`<textarea>`）、模板选择器（`<select>`）、平台勾选（checkboxes）、高级选项（AI 对话/购物车/优惠券）、生成按钮。
3. **结果面板**：显示应用名、页面数、Widget 数，提供"预览编辑"和"确认生成代码"两个按钮。
4. **JS 函数**：`switchMiniTab()`、`generateWithAI()`（调用 `/mini-app/generate`）、`openPreview()`（新窗口打开预览页）、`confirmGenerate()`（触发代码生成并轮询状态）。

**i18n 注意**：所有 label、placeholder、button 文本使用 `{{ _('xxx') }}` 包裹。JS 中的用户提示文本也需 `_()` 包裹（假设 `_()` 在 JS 全局作用域可用；如不可用，使用 Jinja2 注入）。

**验证方式**：浏览器打开应用管理页，切换 AI/手动 tab 正常；输入提示词点击生成，结果面板正常显示。

---

## 7. 复用清单（不需要修改的文件）

以下 17 个文件/模块**零改动**，直接复用：

| 文件/模块 | 复用能力 |
|-----------|----------|
| `admin/static/js/editor/editor-init.js` | 编辑器初始化 |
| `admin/static/js/editor/block-actions.js` | 拖拽排序（HTML5 Drag & Drop） |
| `admin/static/js/editor/inline-editor.js` | 内联编辑（双击编辑） |
| `admin/static/js/editor/editor-toolbar.js` | 编辑器工具栏 |
| `admin/static/js/editor/state-manager.js` | 撤销/重做（Ctrl+Z，最多 20 步） |
| `admin/static/js/editor/color-palette.js` | 颜色面板 |
| `admin/static/js/editor/spacing-slider.js` | 间距滑块 |
| `admin/static/js/editor/nav-editor.js` | 导航编辑器 |
| `admin/static/js/editor/api-client.js` | API 客户端 |
| `admin/static/css/editor.css` | 编辑器样式 |
| `site_builder/engine.py` | LLM 调用入口 |
| `site_builder/generators/*.py` | AI 生成逻辑（品牌/页面） |
| `site_builder/site_settings/*.py` | 设计令牌系统 |
| `site_builder/mini_app/packager.py` | 打包逻辑 |
| `site_builder/mini_app/deployer.py` | 部署逻辑 |
| `plugins/*/plugin.json` | 插件配置 |
| `auth-center/**/*.py` | 认证中心 |

---

## 8. 验证清单

### 阶段 A 验证

- [ ] 4 个 YAML 模板可被 `yaml.safe_load()` 正常解析
- [ ] `mini_app_versions` 表新增的 4 个字段存在且默认值正确
- [ ] 现有 Mini App 生成流程不受影响（回归测试）

### 阶段 B 验证

- [ ] `MiniAppPreviewRenderer.render()` 用 mock plan 输出正确 HTML
- [ ] `/mini-app/generate` 无 `prompt` 时走旧流程正常
- [ ] `/mini-app/generate` 带 `prompt` 时返回 `preview_url`
- [ ] `/mini-app/preview/<id>` 浏览器访问正常渲染
- [ ] `/mini-app/preview/<id>/data` 返回的 JSON 与编辑器 API 格式兼容

### 阶段 C 验证

- [ ] `engine.py` 不传 `ai_plan` 时输出与改造前一致
- [ ] `base.py` `generate_from_plan()` 输出目录结构正确
- [ ] Douyin 平台输出文件扩展名为 `.ttml`/`.ttss`
- [ ] WeChat 平台输出文件扩展名为 `.wxml`/`.wxss`
- [ ] Telegram/LINE 平台输出文件扩展名为 `.html`

### 阶段 D 验证

- [ ] 预览页 tabBar 在设备模拟器底部正确显示
- [ ] Widget 占位符在预览中正确注入
- [ ] AI/手动标签切换正常
- [ ] 输入提示词 → 生成 → 预览 → 编辑 → 打包下载 全流程走通

### i18n 验证

- [ ] 所有新增 `.py` 文件顶部有 `from i18n import _`
- [ ] 所有新增用户可见文本使用 `_()` 包裹
- [ ] Jinja2 模板中无 `_('{{ var }}')` 嵌套写法
- [ ] 新增翻译 key 已同步到 `i18n/en.yml` 和 `i18n/zh-CN.yml`

---

## 9. 文件索引

### 新增文件（5 个）

| 文件 | 用途 |
|------|------|
| `site_builder/prompts/mini_shop.yml` | 商城小程序提示词模板 |
| `site_builder/prompts/mini_service.yml` | 服务预约小程序提示词模板 |
| `site_builder/prompts/mini_brand.yml` | 品牌展示小程序提示词模板 |
| `site_builder/prompts/mini_community.yml` | 社区论坛小程序提示词模板 |
| `site_builder/mini_app/preview_renderer.py` | AI 计划 → HTML 预览渲染器 |

### 修改文件（10 个）

| 文件 | 改动 |
|------|------|
| `site_builder/routes.py` | 改造 `/mini-app/generate` + 新增预览路由 |
| `site_builder/models.py` | `mini_app_versions` 新增 4 字段 |
| `site_builder/mini_app/engine.py` | `generate()` 支持 `ai_plan` 参数 |
| `site_builder/mini_app/generators/base.py` | 新增 `generate_from_plan()` 基类方法 |
| `site_builder/mini_app/generators/douyin.py` | 新增 `generate_from_plan()` 实现 |
| `site_builder/mini_app/generators/wechat.py` | 新增 `generate_from_plan()` 实现 |
| `site_builder/mini_app/generators/telegram.py` | 新增 `generate_from_plan()` 实现 |
| `site_builder/mini_app/generators/line.py` | 新增 `generate_from_plan()` 实现 |
| `admin/templates/ai_site_preview.html` | 新增 tabBar + Widget 注入点 |
| `admin/templates/partials/mini_apps.html` | 新增 AI 生成面板 |

---

> **文档维护**
> 本文档基于原始方案 `新建文件夹/mini-programs-ai-generation-plan.md` 编写。
> 实施过程中如发现偏差，必须先更新本文档并重新确认后再继续。
