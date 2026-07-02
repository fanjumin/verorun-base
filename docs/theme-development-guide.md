```markdown
# EasyKai 主题开发规范 v1.1

**面向第三方设计师 / 前端开发者**  
开发一个主题**主要只需要 CSS**，几乎无需接触后端代码。门槛低，但必须严格遵守本规范。

---

## 1. 主题目录结构（必须严格遵守）

```
my-theme/                     # 文件夹名必须与 slug 一致
├── theme.json                # 必需：主题清单文件
├── theme.css                 # 必需：CSS 变量覆盖（主题核心）
├── preview.png               # 必需：1200×800 预览图（后台展示用）
├── screenshot.jpg            # 可选：更多宣传图
└── templates/                # 可选：Jinja2 模板覆盖（仅高级需求使用）
    ├── base.html
    ├── footer.html
    ├── cms_page.html
    └── ...
```

**硬性规则**：
- 主题文件夹名必须与 `theme.json` 中的 `slug` 完全一致（小写 + 连字符）
- `theme.css` 只允许覆盖 CSS 变量，**不要复制整个 design-system.css**
- 禁止放入 `.js`、`.py`、`.php`、`.sh` 等任何可执行文件
- ZIP 打包时，根目录必须直接包含 `theme.json`，不要多套一层文件夹

---

## 2. theme.json 规范

```json
{
  "name": "金融专业深色版",
  "slug": "finance-pro-dark",
  "version": "1.0.0",
  "author": "你的名字",
  "author_url": "https://example.com",
  "description": "专为金融数据平台设计的专业深色主题，强化数据可读性和科技感。",
  "industry": ["finance"],
  "tags": ["dark", "professional", "data-dense"],
  "sites": ["main", "platform", "admin", "community"],
  "preview": "preview.png",
  "variables": {
    "preset": "dark",
    "radius": 12,
    "font_scale": 1.0
  },
  "compatibility": {
    "min_version": "2.0.0"
  }
}
```

---

## 3. theme.css 规范（最核心部分）

```css
/* finance-pro-dark/theme.css */
:root {
  /* 主色系 */
  --blue:         #0ea5e9;
  --violet:       #7c3aed;
  --green:        #10b981;
  --indigo:       #4f46e5;
  --cyan:         #06b6d4;
  --gold:         #d97706;

  /* 背景层级 */
  --bg-deep:      #020617;
  --bg:           #0f172a;
  --bg-elevated:  #1e293b;
  --bg-card:      #1e293b;
  --bg-glass:     rgba(15, 23, 42, 0.85);

  /* 文字 */
  --text:         #f1f5f9;
  --text-dim:     #94a3b8;
  --text-muted:   #64748b;

  /* 边框 */
  --border:       rgba(148, 163, 184, 0.08);
  --border-light: rgba(148, 163, 184, 0.15);

  /* 圆角 */
  --radius:       12px;
  --radius-sm:    8px;
  --radius-lg:    16px;

  /* 渐变 */
  --gradient-primary: linear-gradient(135deg, #4f46e5, #06b6d4);
  --gradient-electric: linear-gradient(135deg, #0ea5e9, #7c3aed);
}
```

---

## 4. 安全与禁止事项（必须严格遵守）

**严格禁止**以下行为，否则主题将被拒绝：
- 任何 JavaScript 文件或内联 `<script>`
- 使用 `expression()`、`behavior:` 等危险 CSS 属性
- 外部不可信资源引用（除知名字体 CDN）
- 路径遍历（`../`）
- 恶意代码、广告、追踪脚本
- 单文件超过 2MB，整个主题包超过 10MB

---

## 5. 开发工作流（推荐）

1. 复制 `themes/default` 文件夹，重命名为你的主题 slug
2. 修改 `theme.json`（name、slug、description 等）
3. 修改 `theme.css` 中的 CSS 变量
4. 在浏览器开发者工具中实时调试（修改 `:root` 变量即时生效）
5. 制作 `preview.png`（推荐 1200×800）
6. 打包成 zip（根目录直接包含 `theme.json`）
7. 在管理后台「模板管理」上传安装并启用

---

## 6. 行业设计指南

| 行业       | 推荐主色               | 设计重点                     |
|------------|------------------------|------------------------------|
| 金融       | 蓝、绿、紫             | 数据可读性、专业感、涨跌色   |
| 教育       | 靛蓝、青、金           | 温暖、清晰、大字体           |
| 电商       | 橙、玫红、金           | 高对比、促销感、强 CTA       |
| 企业服务   | 深蓝、靛蓝             | 稳重、专业、低饱和度         |
| 通用 SaaS  | 青、紫、绿             | 现代、简洁、科技感           |

---

**文档结束**  
**版本**：v1.1  
**更新日期**：2026.05

---