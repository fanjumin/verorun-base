# EasyKai 主题系统 — 完整文档

> 一个**多站点多租户**（Multi-Tenant）的主题管理系统。每个子站（主站 / 用户后台 / 管理后台）可**独立切换主题**，互不干扰。

---

## 一、系统架构总览

```
┌─────────────────────────────────────────────────┐
│                   用户浏览器                       │
└────────┬────────────┬────────────┬──────────────┘
         │            │            │
┌────────▼──┐  ┌─────▼─────┐  ┌──▼───────────┐
│ 主站       │  │ 用户后台   │  │ 管理后台      │
│ (main)    │  │ (platform)│  │ (admin)      │
│ 8082      │  │ 8083      │  │ 8084         │
└────────┬──┘  └─────┬─────┘  └──┬───────────┘
         │            │            │
         └────────────┼────────────┘
                      ▼
            ┌──────────────────┐
            │  auth-center     │
            │  认证 + 共享 DB   │
            │  themes / site   │
            │  configs 集中管  │
            └──────────────────┘
```

每个子站 (`Flask app`) 独立运行，共享同一个 SQLite 数据库（`auth-center` 管理），通过 `site_theme_config` 表查询各自激活的主题。

### 关键文件

| 文件 | 用途 |
|------|------|
| `auth-center/routes/theme_admin.py` | 旧版主题管理 API（含 community site_key，已废弃） |
| `admin/routes/theme_admin.py` | 新版**主 Theme API** — 安装 / 列表 / 激活 / 删除 |
| `admin/routes/header_admin.py` | 顶部导航 CRUD |
| `admin/routes/footer_admin.py` | 页脚管理 CRUD（链接 / 导航 / 文章 / 伙伴） |
| `auth-center/models/database.py` | 数据库表定义 |
| `docs/theme-development-guide.md` | 第三方开发者主题开发规范 |
| `themes/*/theme.json` | 各主题清单文件 |
| `themes/*/theme.css` | 各主题 CSS 变量覆盖 |

---

## 二、数据库设计

### 1. `site_configs` 表 — 站点基本配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `domain` | TEXT UNIQUE | 域名（唯一标识） |
| `name` | TEXT | 站点名称 |
| `industry` | TEXT | 所属行业 |
| `theme_color` | TEXT | 主色（如 `#6366f1`） |
| `accent_color` | TEXT | 强调色（如 `#8b5cf6`） |
| `logo_url` | TEXT | Logo 地址 |
| `favicon_url` | TEXT | Favicon 地址 |
| `tier` | TEXT | 套餐等级 (`free` / ...) |
| `features` | TEXT | JSON 特性列表 |

这是一个 key-value 风格的基本配置表，每个独立域名一个条目。`theme_color` 和 `accent_color` 为旧版直接配色字段。

### 2. `themes` 表 — 主题注册表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `name` | TEXT | 主题显示名称（如"暖橙"） |
| `slug` | TEXT UNIQUE | 机器标识（如 `warm`，也是目录名） |
| `version` | TEXT | 版本号（默认 `1.0.0`） |
| `author` | TEXT | 作者 |
| `author_url` | TEXT | 作者链接 |
| `description` | TEXT | 描述 |
| `industry` | TEXT | 推荐行业 |
| `tags` | TEXT | JSON 标签数组 |
| `config_json` | TEXT | 完整 theme.json 的 JSON 存储 |
| `dir_name` | TEXT | 文件目录名（= slug） |
| `installed_at` | TEXT | 安装时间 |

### 3. `site_theme_config` 表 — 站点与主题关联

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `site_key` | TEXT UNIQUE | 站点标识：`main` / `platform` / `admin` |
| `theme_id` | INTEGER FK → themes.id | 当前激活的主题 ID（NULL = 默认主题） |
| `overrides_json` | TEXT | 额外的变量覆盖（JSON） |
| `updated_at` | TEXT | 更新时间 |

**SITE_KEYS 常量**（见 `admin/routes/theme_admin.py`）：

| Key | 标签 | 端口 | 说明 |
|-----|------|------|------|
| `main` | 主站 | 8082 | 官方网站首页 |
| `platform` | 用户后台 | 8083 | 用户登录后的操作面板 |
| `admin` | 管理后台 | 8084 | 管理员控制面板 |

> `community`（Agent 社区）已下线，从 SITE_KEYS 中移除。

### 4. `header_nav` 表 — 顶部导航

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | |
| `site` | TEXT | 所属站点 (`platform` / `trademind`) |
| `title` | TEXT | 显示文字 |
| `url` | TEXT | 链接地址 |
| `sort_order` | INTEGER | 排序值（升序） |
| `is_enabled` | INTEGER | 启用状态 (0/1) |

### 5. Footer 相关表（4 张）

| 表名 | 字段 | 用途 |
|------|------|------|
| `footer_links` | `id, section, title, url, sort_order, is_enabled` | 分组页脚链接（如"产品/支持/公司"各为一组 section） |
| `footer_nav` | `id, title, url, sort_order, is_enabled` | 底部导航栏 |
| `footer_articles` | `id, title, url, sort_order, is_enabled` | 推荐文章 |
| `partner_links` | `id, name, url, icon_url, sort_order, is_enabled` | 生态合作伙伴链接 |

每个 footer 表都提供 **管理 API（需 JWT 认证）**和 **公开 API（无需认证，仅返回 is_enabled=1 的记录）**。

---

## 三、CSS 变量系统

主题通过覆盖 `:root` 的 CSS 变量实现视觉切换。变量分 6 大类：

### 变量体系

```css
:root {
  /* 1. 背景层级 — 深→浅 */
  --bg-deep:      #020617;   /* 最深背景 */
  --bg:           #0f172a;   /* 主背景 */
  --bg-elevated:  #1e293b;   /* 卡片/面板背景 */
  --bg-card:      #1e293b;   /* 卡片背景 */
  --bg-glass:     rgba(...); /* 玻璃态背景 */
  --bg-overlay:   rgba(...); /* 遮罩层 */

  /* 2. 语义主色 */
  --blue:         #0ea5e9;   /* 主要行动色 */
  --violet:       #7c3aed;   /* 次要/强调色 */
  --green:        #10b981;   /* 成功/正向 */
  --indigo:       #4f46e5;   /* 链接/选中 */
  --cyan:         #06b6d4;   /* 信息色 */
  --gold:         #d97706;   /* 警告/高亮 */
  --rose:         #e11d48;   /* 危险/错误 */
  --orange:       #ea580c;   /* 热力色 */

  /* 3. 文字色阶 */
  --text:         #f1f5f9;   /* 正文 */
  --text-dim:     #94a3b8;   /* 次要文字 */
  --text-muted:   #64748b;   /* 禁用/占位 */
  --text-high:    #ffffff;   /* 高亮文字 */

  /* 4. 边框 */
  --border:        rgba(...); /* 标准边框 */
  --border-light:  rgba(...); /* 淡边框 */
  --border-accent: rgba(...); /* 强调边框 */

  /* 5. 渐变 */
  --gradient-primary:  linear-gradient(...);
  --gradient-electric: linear-gradient(...);
  --gradient-neon:     linear-gradient(...);
  --gradient-fire:     linear-gradient(...);
  --gradient-dark:     linear-gradient(...);

  /* 6. 阴影 */
  --shadow-sm:   ...;
  --shadow-md:   ...;
  --shadow-lg:   ...;
  --shadow-glow: ...;
}
```

### 应用方式

1. **默认主题** (`default`) — `theme.css` 为空文件，使用 `design-system.css` 的硬编码值
2. **第三方主题** — 只需在 `:root` 中覆盖需要变化的变量，未覆盖的继承默认值
3. **运行时注入** — 管理后台在 `<head>` 中通过 `{{ theme_css_url }}` 条件引入 `<link rel="stylesheet">`

### 内置主题一览

| 主题 | slug | 预设 | 主色 | 推荐行业 |
|------|------|------|------|----------|
| EasyKai 默认 | `default` | dark | 电光蓝紫 | 通用（内置） |
| 暖橙 | `warm` | light | 琥珀/橙 | 零售、生活服务、美容、家居 |
| 深海蓝 | `ocean` | dark | 深蓝 | 企业、制造、物流、金融 |
| 自然绿 | `nature` | light | 自然绿 | 餐饮、健康、农业、环保 |
| 纯净白 | `light` | light | 靛蓝 | 教育、咨询、法律服务 |

---

## 四、Header 导航管理

顶部导航是**按站点隔离**的（`platform` / `trademind`），每个站点有独立的链接列表。

### API 端点（`/admin/header-nav`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/header-nav?site=platform` | 获取指定站点的导航列表 |
| POST | `/admin/header-nav` | 新增导航链接 |
| PUT | `/admin/header-nav/<id>` | 更新 |
| DELETE | `/admin/header-nav/<id>` | 删除 |
| POST | `/admin/header-nav/reorder` | 批量排序（拖拽） |

---

## 五、Footer 管理

页脚管理提供 4 个独立维度，每维均有管理 API + 公开 API。

| 维度 | 管理 API | 公开 API | 数据结构 |
|------|----------|----------|----------|
| 分组链接 | `/admin/footer-links` | `/api/footer-links` | section（组名）+ title + url |
| 底部导航 | `/admin/footer-nav` | `/api/footer-nav` | title + url |
| 推荐文章 | `/admin/footer-articles` | `/api/footer-articles` | title + url |
| 合作伙伴 | `/admin/partners` | `/api/partners` | name + url + icon_url |

公开 API 无需认证，自动过滤 `is_enabled=1` 并按 `sort_order` 升序排列。

---

## 六、主题预设 — 安装 / 切换 / 卸载

### 主题包结构

```
my-theme.zip
├── theme.json       # 必需: 清单文件
├── theme.css        # 必需: CSS 变量覆盖
├── preview.png      # 必需: 1200×800 预览图
└── templates/       # 可选: Jinja2 模板覆盖
    ├── base.html
    └── ...
```

### `theme.json` 清单格式

```json
{
  "name": "暖橙",
  "slug": "warm",
  "version": "1.0.0",
  "author": "EasyKai",
  "author_url": "https://easykai.cn",
  "description": "暖橙色风格...",
  "industry": "retail",
  "tags": ["warm", "orange", "retail"],
  "sites": ["main", "platform"],
  "variables": { "preset": "light", "font_scale": 1.0, "border_radius": 16 }
}
```

### 管理 API（`/admin/themes`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/themes` | 列出所有已安装主题（含 active_sites、thumbnail） |
| GET | `/admin/themes/<id>` | 获取单个主题详情 |
| POST | `/admin/themes/install` | 上传 ZIP 包安装（安全检查：文件类型白名单、大小限制 10MB、路径遍历防护） |
| DELETE | `/admin/themes/<id>` | 卸载主题（不能删除 default） |
| GET | `/admin/themes/sites` | 查询所有站点的当前主题分配 |
| PUT | `/admin/themes/sites` | 切换某站点的主题（body: `{site_key, theme_id}`） |

### 安全机制

- 白名单扩展名：`.css`, `.html`, `.json`, `.png`, `.svg`, `.jpg`, `.jpeg`, `.woff2`, `.ttf`, `.md`, `.txt`
- 黑名单：`.py`, `.js`, `.php`, `.sh`, `.exe`, `.bat`, `.dll`, `.so`
- 单文件 ≤ 2MB，总包 ≤ 10MB
- 路径遍历字符自动拦截（`/` `\\` → `_`）

---

## 七、模板覆盖系统（Template Overlay）

利用 Jinja2 的 `ChoiceLoader`（多优先级加载器）实现主题模板覆盖：

```
                       用户请求
                          │
                          ▼
┌─────────────────────────────────┐
│  ChoiceLoader（优先级顺序）      │
│                                 │
│  ① 主题模板目录（最高优先级）     │
│     themes/{slug}/templates/    │
│                                 │
│  ② 应用自身模板（默认）          │
│     app/templates/              │
│                                 │
│  ③ 平台共享模板                 │
│     platform/templates/         │
│                                 │
│  ④ 项目根目录（共享组件）        │
│     project_root/               │
└─────────────────────────────────┘
```

代码位置：
- **管理后台**：`admin/app.py` 第 404–426 行
- **用户后台**：`platform/app.py` 第 938–959 行

两个 app 都通过 `_get_active_theme_slug_*()` 查询激活主题，若有主题模板目录则插入 `ChoiceLoader` 首位。

另外，每个 app 通过 `@app.context_processor` 向所有模板注入 `theme_css_url` 变量，用于动态加载主题 CSS。

---

## 八、Admin UI — 后台管理界面

主题管理在管理后台左侧菜单「系统管理 → 模板管理」下，入口为 `window.l_themes()`。

### 功能

1. **主题网格展示** — 显示所有已安装主题的卡片（名称、缩略图、标签、适用站点）
2. **安装主题** — 点击上传 ZIP 包，实时反馈进度和结果
3. **激活主题** — 选择目标站点（main / platform / admin），即时切换
4. **卸载主题** — 删除主题文件和数据，默认主题不可删除

对应前端代码位于 `admin/templates/admin.html` 约第 8472–8520 行。

---

## 九、Header / Footer 前台调用示例

```javascript
// 前台获取页脚链接
fetch('/api/footer-links')
  .then(r => r.json())
  .then(data => {
    // data.data 按 section 分组渲染
    renderFooterLinks(data.data);
  });

// 前台获取顶部导航
fetch('/admin/header-nav?site=platform')
  .then(r => r.json())
  .then(data => renderHeaderNav(data.data));
```

---

## 十、常见问题

**Q: 如何新增一个站点类型？**
修改 `admin/routes/theme_admin.py` 中的 `SITE_KEYS` 和 `SITE_LABELS`，并在 `site_theme_config` 表中种子对应记录。

**Q: 主题 CSS 不生效？**
1. 检查 `site_theme_config` 中该站点是否激活了非 default 主题
2. 确认 `themes/{slug}/theme.css` 文件存在
3. 检查浏览器 Network 面板中 `/themes/{slug}/theme.css` 是否 200

**Q: 模板覆盖不生效？**
确认主题目录下有 `templates/` 子目录，且模板文件名与被覆盖的模板一致。ChoiceLoader 优先级：主题目录 > 应用自身目录 > 共享目录。

---

*文档版本 v2.0 — 2026.06*
*相关文件：[theme_admin.py](path/to/admin/routes/theme_admin.py) | [header_admin.py](path/to/auth-center/routes/header_admin.py) | [footer_admin.py](path/to/auth-center/routes/footer_admin.py) | [theme-development-guide.md](path/to/docs/theme-development-guide.md)*
