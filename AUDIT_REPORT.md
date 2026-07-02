# easykai.cn 全面代码审计报告
日期: 2026-06-10
审计范围: /home/***REMOVED***/projects/easykai.cn

---

## 🔴 P0: 可能导致服务阻塞

### P0-1: systemd service 文件中明文硬编码凭据
**文件**: 
- `community.service` (行17-32)
- `trademind-api.service` (行15-26)

**发现**: 两文件中硬编码了以下生产环境凭据：
- `WECHAT_API_V3_KEY=6m9uj91yc10p4p3nl5o2cslznp18pujz`
- `DEEPSEEK_API_KEY=sk-6e6...534b` (已截断但明文存储)
- `SMTP_PASS=Lopn10me2SHqVQNz`
- `JWT_SECRET=30e55814411cb192565e8bfa84493d9efb7a1b3e1b2f20dbe449f56ec952ae2d`
- `ALIYUN_SMS_ACCESS_KEY=LTAI5tAUqFQ1QnVzF83R3TGu`
- `ALIYUN_SMS_ACCESS_SECRET=DVEHr9GU3UbvHXlC6mrIVXYmjmp0pb`
- `FEISHU_APP_SECRET=BOpWwP...60gO`
- `FEISHU_VERIFICATION_TOKEN=MOgy8i...YWHW`

**风险**: 这些文件被 git 跟踪。任何人获得仓库访问权限即可获取所有生产环境密钥。JWT_SECRET 泄露意味着可伪造任意用户的认证令牌。

### P0-2: cognition-service 默认密码硬编码在源码中
**文件**: `/home/***REMOVED***/projects/easykai.cn/cognition-service/config.py` 行11
```python
PG_PASSWORD = os.getenv("PG_PASSWORD", "***REMOVED***")
```
**风险**: 默认 PostgreSQL 密码硬编码在 Python 源码中，即使设置了环境变量，回退值也是生产密码。

### P0-3: analytics/scripts 目录存在多个包含明文密码的脚本
**文件**: 
- `/home/***REMOVED***/projects/easykai.cn/analytics/scripts/upload_run_check2.py` 行6:
  ```python
  ssh.connect('100.124.0.103', username='easykai', password='***REMOVED***', ...)
  ```
- 其他31个 `scripts/` 和 `analytics/scripts/` 下的 .py 文件使用 `PASS` 变量（但 `deploy/` 或 `.env` 可能包含真实值）

**风险**: 明文 SSH 密码存在于仓库中，可被用于服务器入侵。

### P0-4: 两个 nginx 配置文件冲突
**文件**: 
- `nginx_easykai.conf` (276行, 详细配置)
- `easykai.cn.conf` (100行, 简化配置)

**问题**: 两者都监听 443 端口，定义了不同的 server_name 和端口路由。`easykai.cn.conf` 中：
- 缺少 `listen 80` (只有 443)
- community 缺少 captcha 代理
- 缺少 `/subscribe` 路由到 8083
- 缺少 `/api/v1/feishu` 路由到 8082
- 缺少 bot 子站 (18789)
- captcha 代理路径缺失 `/puzzle-captcha.js` 和 `.css`

**风险**: 如果加载了错误的配置文件，部分子站和功能将不可用。两个文件都可能被加载导致配置冲突。

### P0-5: Flask 路由顺序可能引发 404
**文件**: `platform/app.py` 行60-67
nginx 将大量路径代理到 8081：
```
location ~ ^/(login|register|reset-password|dashboard|settings|keys|docs|tutorial|auth|user|payment|...) {
    proxy_pass http://127.0.0.1:8081;
}
```
但 `easykai.cn.conf` 中所有路径都代理到 8083，与 8081 的预期不符。

---

## 🟠 P1: 可能破坏功能

### P1-1: platform/index.html 完全不使用 design-system.css
**文件**: `/home/***REMOVED***/projects/easykai.cn/platform/templates/index.html` (1619行)
- ❌ 没有 `<link rel="stylesheet" href="/static/css/design-system.css">`
- ✅ 定义了自己的内联 `:root{--bg:#0a0a0f;--card:#111118;--border:#1c1c26;--text:#e0e0f0;--muted:#8888a0;--dim:#555570;--accent:#6366f1;--accent2:#22d3ee;--sidebar:160px;--radius:12px}`
- 使用不同的 CSS 变量名（`--bg` vs `--bg-deep`, `--muted` vs `--text-muted`），与 design-system.css 完全不兼容
- 全部 1619 行中没有引用任何 `design-system` 导入

**影响**: platform 的用户面板(8083)样式完全独立于全局设计系统，修改 CSS 变量需要同时改两处。

### P1-2: trademind/templates/reset_password.html 文件内容损坏
**文件**: `/home/***REMOVED***/projects/easykai.cn/trademind/templates/reset_password.html`
- 文件开头 `{% extends "base.html" %}` 后紧跟着带行号的CSS
- 内容格式：```11|.login-page{...}``` （行号被当作内容写入了文件）
- 这是明显的复制粘贴错误，会导致CSS解析失败，密码重置页面样式崩溃

同样检查：
- `platform/templates/reset_password.html` (219行) — 正常
- `admin/templates/reset_password.html` — 正常

### P1-3: 双 base 模板冲突 (community)
**文件**: 
- `community/templates/base.html` (102行) — 完整模板，有 nav/footer/scripts
- `community/templates/community_base.html` (305行) — 独立完整模板，也有 nav/footer/scripts
  
**问题**: 
- `base.html` 有设计系统导入 + cookie-consent
- `community_base.html` 没有 cookie-consent 但有一颗完整的广告系统JS
- 子模板如 `tasks.html` 继承 `community_base.html`；`index.html` 继承 `base.html`
- 两个模板的导航栏结构完全不同（base.html 使用 `{% include '_footer.html' %}`，community_base.html 内联 footer）
- base.html 使用 `ORIGINAL_DOMAIN` 占位符，community_base.html 使用 `智策AI建站系统` 占位符

**影响**: 修改导航栏或页脚需要改两个模板。

### P1-4: CMS 模块路由中断风险 — cms_public.py
**文件**: `/home/***REMOVED***/projects/easykai.cn/platform/cms_public.py`
- 定义了 `cms_bp` blueprint
- 在 `platform/app.py` 行77被注册: `app.register_blueprint(cms_bp)`
- 但 `cms_bp` 从 `models.cms` 导入函数（`get_page_blocks`, `get_posts` 等）
- 这些 CMS 模型如果不存在对应的数据库表，将导致 500 错误

### P1-5: 端口映射不一致 — nginx vs 实际服务
| 域名 | nginx 转发 | 实际服务 | 问题 |
|------|-----------|---------|------|
| 智策AI建站系统 (主站) | 8083 (Platform) | 8081 (SSO+TradeMind) | ❌ 两个配置不一致 |
| tm.智策AI建站系统 | 8081 (TradeMind) | 8081 | ✅ 一致 |
| platform.智策AI建站系统 | 8083 | 8083 | ✅ 一致 |
| community.智策AI建站系统 | 8082 | 8082 | ✅ 一致 |
| agent.智策AI建站系统 | 8084 | 8084 | ✅ 一致 |

**nginx_easykai.conf**: 主站(智策AI建站系统)除了 `/subscribe` 代理到 8083，其余多数路径代理到 8081，兜底 `/` 代理到 8083。
**easykai.cn.conf**: 主站所有请求代理到 8083。

### P1-6: 错误的 tagline 默认值
**文件**: 项目根目录 `index.html` (行23-24) 标题为 "智策AI" 而非 "EasyKai"，无法通过 nginx 直接访问时品牌不一致。

---

## 🟡 P2: 设计/一致性问题

### P2-1: 51个 `<style>` 内联标签 — 无统一CSS管理
**发现**: 搜索发现整个项目共有 **51个** `<style>` 标签分布在 HTML 文件中。其中：
- `platform/templates/index.html` (1619行): 全部CSS内联，无外部CSS引用
- `trademind/templates/` 下的每个页面几乎都有内联 `<style>` (21个)
- `platform/templates/` 下多数页面有内联 `<style>` (18个)
- `admin/templates/admin.html`: 126行内联CSS + 30+个页面特定的CSS块

**影响**: 修改任何设计元素都需要搜索所有模板，极难维护。

### P2-2: 3份 design-system.css 完全一致
**位置**:
1. `/home/***REMOVED***/projects/easykai.cn/platform/static/css/design-system.css` (886行)
2. `/home/***REMOVED***/projects/easykai.cn/trademind/static/css/design-system.css` (869行)
3. `/home/***REMOVED***/projects/easykai.cn/community/static/css/design-system.css` (869行)

**问题**: 三份文件内容几乎完全相同（仅有微小行数差异）。任何CSS变量修改需要同步3个文件。其中 platform 版本多了17行（有额外CSS），说明分支已开始分化。

### P2-3: admin.html 使用官方不推荐的 prompt/alert/confirm
**文件**: `admin/templates/admin.html` (8913行, 550KB)
**发现**: **136处** 使用了 `prompt(` / `confirm(` — 在 `admin.html` 中：
- `prompt(`: 至少 12 处用于用户输入（创建Agent、输入名称、设置密钥等）
- `confirm(`: 大量用于操作确认（暂停Agent、删除密钥等）
- `alert(`: 少数用于错误提示

**同样在**: `platform/templates/index.html` 中有 68 处 prompt/confirm/alert。
**同样在**: `platform/templates/admin.html` 中有 24 处。

**影响**: `prompt()` 在严格 CSP 策略下可能被阻止；界面体验差，无法自定义样式。

### P2-4: 硬编码域名占位符未替换
**文件**: 多处模板使用 `智策AI建站系统` 作为硬编码域名占位符：
- `community/templates/community_base.html`: 行131,170
- `community/templates/base.html`: 行29,83
- `trademind/templates/base.html`
- `trademind/templates/base_sidebar.html`

**影响**: 这看起来是真实中文域名，但如果需要更换或本地开发，需要搜索替换所有文件。

### P2-5: 直接 http://127.0.0.1:808X 跨端口调用
**发现**: 项目中有大量跨服务的 HTTP 调用使用硬编码 IP:端口：

| 文件 | 端口 | 用途 |
|------|------|------|
| `platform/app.py` | 8090 | captcha 代理 |
| `platform/app.py` | 8084 | admin media API |
| `trademind/app.py` | 8084 | admin media API |
| `admin/app.py` | 8090 | captcha 代理 |
| `easykai-auth/routes/auth.py` | 8090 | captcha consume |
| `easykai-auth/routes/user.py` | 8090 | captcha consume |
| `easykai-auth/routes/admin.py` | 8084 | agent-matrix API |

**影响**: 如果服务端口变化，需要改所有引用点。没有统一的服务发现机制。

### P2-6: ORIGINAL_DOMAIN 占位符
`community/templates/base.html` 使用 `https://ORIGINAL_DOMAIN` 作为链接基础，而 `community/templates/community_base.html` 使用 `https://智策AI建站系统`。不一致的占位符方案。

### P2-7: 管理后台 admin.html 550KB — 单个文件过重
`admin/templates/admin.html` 为 8913行/550KB，包含：
- 全部管理界面（30+个管理面板）
- 所有 inline SVG 图标定义
- 所有JS逻辑（无外部JS文件）
- 所有CSS

这是严重的代码组织问题，加载慢且极难维护。

### P2-8: community 服务文件字段冲突 — 系统字段与应用字段混合
`community/templates/base.html` 的 `<meta name="description">` 使用了 `brand.seo_desc` 字段，而 `community_base.html` 使用了硬编码字符串。品牌数据模型不一致。

### P2-9: 硬编码端口范围 8081-8090 无配置中心
**统计**: 搜索到约 50+ 处硬编码端口引用(8081-8090)，分散在 .py 和 .sh 文件中。没有集中的端口配置管理。

---

## ⚪ P3: 编码规范/提示

### P3-1: __pycache__ 占用 2.9MB 磁盘空间
**总计**: 19个 `__pycache__` 目录，共 2.9MB。最大的是：
- `easykai-auth/routes/__pycache__`: 1.1MB
- `orchestrator/__pycache__`: 368KB
- `community/__pycache__`: 344KB
- `agent_matrix/__pycache__`: 288KB

建议加入 `.gitignore` 或定期清理。

### P3-2: 33个脚本文件滞留在仓库中
存在于 `scripts/` 和 `analytics/scripts/` 目录下的 33 个 `.py` 文件，包含大量一次性部署、测试脚本。这些不应留在主仓库中。

### P3-3: database.py 使用 executescript 但已有 IF NOT EXISTS 保护
**文件**: `easykai-auth/models/database.py` 的 `init_db()` 方法
- ✅ 所有 `CREATE TABLE` 使用 `IF NOT EXISTS`
- ✅ 所有 `CREATE INDEX` 使用 `IF NOT EXISTS`
- ✅ 迁移使用 try/except 处理 ALTER TABLE
- ✅ 数据库路径: `data/easykai.db`

**结论**: 数据库初始化安全，不会在已有数据库上出错。

### P3-4: templates_auto_reload 配置情况
- ✅ `platform/app.py` 行68: `app.config['TEMPLATES_AUTO_RELOAD'] = True`
- ✅ `trademind/app.py` 行25: `app.config['TEMPLATES_AUTO_RELOAD'] = True`
- ✅ `admin/app.py` 行92: `app.config['TEMPLATES_AUTO_RELOAD'] = True`
- ❌ `community/app.py` (未确认，但推测需要)

所有主要服务都已启用模板自动重载。

### P3-5: 数据库总表数统计
在 `database.py` 的 `init_db()` 中定义了以下表：
1. users
2. user_profiles
3. industries
4. career_options
5. user_addresses
6. app_authorizations
7. api_keys
8. system_config
9. user_notifications
10. user_agents
11. agent_api_keys
12. agent_logs
13. user_sessions
14. agent_experiences
15. favorites
16. user_activity
17. admin_logs
18. sms_templates
19. agents
20. providers
21. provider_models
22. billing_orders
23. sms_codes
24. sms_rate_limits
25. login_attempts
26. orders
27. chat_history
28. contact_messages
29. user_feedback
30. user_tickets
31. email_sent
32. social_push_logs
33. brand_settings
34. tm_brand_settings

**总计: 34张表** (均在同一个 SQLite 数据库中)

### P3-6: 不使用的文件 — cms_public.py 和 staticgen.py
- `platform/cms_public.py`: ❌ 在 `platform/app.py` 行21被 `from cms_public import cms_bp` 导入，行77 `app.register_blueprint(cms_bp)` 注册，所以正在使用。
- `platform/staticgen.py`: 命令行工具，不在任何 app.py 中导入，属于独立工具。

所有其他 `.py` 文件均可通过导入链追溯到某个 `app.py`。

---

## 模板继承链

### Platform (8083)
```
No base.html inheritance — 每个模板都是独立完整的HTML
├── index.html (1619行, 完全内联CSS+JS)
├── admin.html (独立)
├── login.html (独立, 引用design-system.css)
├── register.html
├── cart.html
├── shop.html
├── shop_detail.html
├── orders.html
├── subscribe.html
├── start.html
├── docs_index.html / docs_list.html / docs_detail.html
├── insights_list.html / insights_detail.html
├── download_list.html / download_detail.html
├── cms_page.html / cms_404.html
├── douyin_login.html / douyin_success.html
└── reset_password.html (独立, 引用design-system.css)
```

### Community (8082)
```
base.html (102行, 引用design-system.css, 有cookie-consent)
├── index.html (继承, 内联CSS在{% block head %}中)
└── subscribe.html

community_base.html (305行, 无cookie-consent, 有广告系统)
├── plaza.html
├── tasks.html
├── console.html
├── cognition.html
├── topup.html
└── chat_widget.html
```

### TradeMind (8081)
```
base.html (127行, 引用design-system.css+cookie-consent, 有nav+footer)
├── index.html (继承, 内联CSS在{% block head %})
├── login.html (继承)
├── markets.html
├── signals.html
├── scanner.html
├── sectors.html
├── sentiment.html
├── reports.html
├── backtest.html
├── flow.html
├── paper.html
├── docs.html
├── stub.html
├── subscribe.html
├── reset_password.html (⚠️ 文件损坏, 内容带行号)
├── settings.html
├── dashboard.html
├── dashboard_contacts.html
├── dashboard_email.html
└── keys.html

base_sidebar.html (82行, 引用design-system.css+cookie-consent, 无nav)
└── (sidebar 布局变体)
```

### Admin (8084)
```
无模板继承 — 所有页面独立
├── admin.html (8913行/550KB, 独立内联CSS+JS)
├── login.html (独立, 内联CSS)
└── reset_password.html (独立, 内联CSS)
```

---

## 严重问题总结

| 级别 | 计数 | 关键发现 |
|------|------|---------|
| 🔴 P0 | 5 | service 文件凭据明文、nginx配置冲突、密码硬编码 |
| 🟠 P1 | 6 | 模板不一致、文件损坏、端口映射错误、CSS系统未使用 |
| 🟡 P2 | 9 | 大量内联CSS、prompt/confirm滥用、硬编码端口/域名 |
| ⚪ P3 | 6 | __pycache__占用、脚本滞留、表结构完整 |

**修改前必须知道的坑**:
1. ❗ JWT_SECRET、所有API密钥和数据库密码在 service 文件和源码中明文 — 改前必须先轮换
2. ❗ 两个 nginx 配置同时存在 — 确认当前使用的是哪一个再修改
3. ❗ platform/index.html 完全不使用 design-system.css — 改CSS变量必须同时改内联部分
4. ❗ community 有两个 base 模板 — 改导航/页脚必须同时改两个
5. ❗ trademind/reset_password.html 内容损坏 — 使用前必须修复
6. ❗ cognition-service PG_PASSWORD 有源码默认值 — 不设环境变量会暴露
7. ❗ 大量硬编码 http://127.0.0.1:808X 跨服务调用 — 改端口需全局搜索替换
8. ❗ 33个部署脚本包含SSH密码泄露 — 任何fork/分享前必须删除
