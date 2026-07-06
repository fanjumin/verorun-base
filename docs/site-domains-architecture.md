# 子域名自动站点引擎 — 架构方案

## 一、背景与目标

### 当前状态
- 已有 `site_configs` + `site_blocks` + `site_plans` 表结构和 API，但**种子数据为空，无实际路由使用**
- Nginx 按域名分发到不同端口（site=8081 / platform=8083 / admin=8084），各端口独立运行
- 导航和品牌设置已在 `DeployConfig` 中通过环境变量 `DEPLOY_DOMAIN` 统一管理
- JWT SSO 和 Cookie 已使用 `.domain.com` 通配符支持跨子域

### 目标
所有客户站点都在 **同一个主域**（如 `.easykai.cn`）下，以**子域名**区分。子域名配额按订阅套餐层级分配：

| 套餐 | plan_key | 子域名配额 |
|------|----------|-----------|
| 基础版 | `deploy_basic` | 3 个（含 1 个主站） |
| 专业版 | `deploy_pro` | 10 个 |
| 企业版 | `deploy_enterprise` | 20 个 |

### 非目标
- 不支持独立一级域名（如 `customer.com`），所有站点都在 `.easykai.cn` 下
- 不为每个客户独立部署，所有站点共享同一套代码 + 同一套数据库

---

## 二、数据库设计（新增 `site_domains` 表）

```sql
CREATE TABLE IF NOT EXISTS site_domains (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    site_config_id  INTEGER NOT NULL REFERENCES site_configs(id),
    subdomain       TEXT NOT NULL,                        -- "shop"（不含主域）
    full_domain     TEXT NOT NULL UNIQUE,                 -- "shop.easykai.cn"
    display_name    TEXT NOT NULL DEFAULT '',              -- "商城"
    template        TEXT DEFAULT 'default',                -- 绑定的页面模板 key
    is_published    INTEGER DEFAULT 1,                    -- 是否对外访问
    page_keys_json  TEXT DEFAULT '["home"]',              -- 启用的页面列表
    sort_order      INTEGER DEFAULT 0,                    -- 排序
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sd_config ON site_domains(site_config_id);
CREATE INDEX IF NOT EXISTS idx_sd_domain ON site_domains(full_domain);
```

### 与现有表的关系

```
site_configs (已存在)
  ├── id / domain / name / industry
  ├── theme_color / accent_color / logo_url / favicon_url
  └── tier / features (JSON)
        ↑
site_domains (新增)
  ├── subdomain → "shop" / "admin" / "platform"
  ├── full_domain → "shop.easykai.cn"
  └── site_config_id → site_configs.id
        ↑
site_blocks (已存在)
  └── site_id → site_configs.id  (子站点复用)
        ↑
site_plans (已存在)
  └── site_id → site_configs.id
```

### subscription_plans 配额配置

不新增表结构，在 `features_json` 数组中增加一个描述性元素（保持和现有功能列表同一格式）：

```python
# features_json 示例（当前已是 JSON 数组）
["AI智能建站","AI智能客服...", "子域名配额: 10 个"]
```

配额校验时通过 `plan_key` 在代码内部映射：

```python
# 硬编码映射（与 subscription_plans 价格一一对应）
_PLAN_DOMAIN_LIMITS = {
    'deploy_basic': 3,
    'deploy_pro': 10,
    'deploy_enterprise': 20,
}
```

---

## 三、核心逻辑：子域名识别中间件

### 3.1 实现位置

新建：`auth-center/middleware/site_domain_middleware.py`（在所有 Flask 应用中共享使用）

### 3.2 核心逻辑

```python
def resolve_current_site():
    """
    在请求处理前调用。
    1. 获取 request.headers['Host']
    2. 从 Host 中提取子域名（如 "shop.easykai.cn" → "shop"）
    3. 查 site_domains WHERE full_domain = host
    4. 查 site_configs WHERE id = site_config_id
    5. 将 site_config + site_domain 注入 g.current_site 和 g.current_domain
    6. 如果未匹配到任何站点 → g.current_site = None（走默认逻辑）
    """
    host = request.headers.get('Host', '').split(':')[0].lower()
    deploy_domain = os.environ.get('DEPLOY_DOMAIN', '')
    
    # 提取子域名：host = "shop.easykai.cn", deploy_domain = "easykai.cn"
    # → subdomain = "shop"
    subdomain = host.replace('.' + deploy_domain, '') if host.endswith(deploy_domain) else ''
    
    with get_db() as conn:
        row = conn.execute(
            "SELECT sd.*, sc.name as site_name, sc.theme_color, sc.accent_color, "
            "sc.logo_url, sc.favicon_url, sc.tier "
            "FROM site_domains sd "
            "JOIN site_configs sc ON sc.id = sd.site_config_id "
            "WHERE sd.full_domain = ? AND sd.is_published = 1",
            (host,)
        ).fetchone()
    
    if row:
        g.current_domain = dict(row)
        g.current_site = {
            'id': row['site_config_id'],
            'name': row['site_name'],
            'theme_color': row['theme_color'],
            'accent_color': row['accent_color'],
            'logo_url': row['logo_url'],
            'favicon_url': row['favicon_url'],
            'tier': row['tier'],
        }
    else:
        g.current_domain = None
        g.current_site = None
```

### 3.3 哪些服务需要注册

| Flask 应用 | 端口 | 需要中间件 | 原因 |
|-----------|------|-----------|------|
| site (主站) | 8081 | ✅ | 主站多站点通过子域名访问 |
| platform (用户控制台) | 8083 | ❌ | 固定绑定到 subdomain="platform" |
| admin (管理后台) | 8084 | ❌ | 固定绑定到 subdomain="agent" |

### 3.4 模板注入

在各服务的 `context_processor` 中注入：

```python
@app.context_processor
def inject_site_context():
    return {
        'current_site': getattr(g, 'current_site', None),
        'current_domain': getattr(g, 'current_domain', None),
    }
```

---

## 四、管理后台：子域名管理 UI

### 4.1 路由（新增到 `auth-center/routes/admin.py`）

| 端点 | 方法 | 功能 |
|------|------|------|
| `/admin/domains` | GET | 子域名管理页面（模板） |
| `/admin/api/domains` | GET | 列出所有子域名（含站点信息 + 配额使用量） |
| `/admin/api/domains` | POST | 创建子域名（校验配额） |
| `/admin/api/domains/<id>` | PUT | 更新子域名配置 |
| `/admin/api/domains/<id>` | DELETE | 删除子域名 |
| `/admin/api/domains/quota` | GET | 返回当前套餐的配额使用情况 |

### 4.2 配额校验逻辑（创建/删除时）

```python
def _check_domain_quota(user_id):
    """检查用户是否还能添加子域名"""
    conn = _get_db()
    # 查询用户当前订阅的 plan_key
    sub = conn.execute(
        "SELECT plan_key FROM subscriptions WHERE user_id=? AND status='active'",
        (user_id,)
    ).fetchone()
    if not sub:
        return {'allowed': 0, 'used': 0, 'limit': 0}
    
    limit = _PLAN_DOMAIN_LIMITS.get(sub['plan_key'], 0)
    used = conn.execute(
        "SELECT COUNT(*) as c FROM site_domains sd "
        "JOIN site_configs sc ON sc.id = sd.site_config_id "
        "WHERE sc.id = (SELECT id FROM site_configs LIMIT 1)"  # 当前部署实例的 site_config
    ).fetchone()['c']
    conn.close()
    
    return {'allowed': limit - used, 'used': used, 'limit': limit}
```

### 4.3 前端页面

新增 `admin/templates/partials/site_domains.html`，包含：

- 当前配额使用量指示器（`3/10 已用`）
- 子域名列表（表格：子域名、全域名、显示名、页面数、状态、操作）
- 添加对话框（输入子域名前缀 + 选择模板 + 显示名）
- 编辑对话框（修改显示名、模板、页面列表）

### 4.4 与现有模板/导航的关系

当前导航菜单中的图标栏和侧栏导航在 `admin/templates/admin.html` 中通过 `brand` + `DeployConfig` 渲染。添加子域名管理后：

- 在侧栏 **System** 分类下增加 "Site Domains" 入口
- 图标使用现有 `icons.html` 中的 `globe` 或 `layers` 图标
- 品牌设置保持不变，子域名管理是独立页面

---

## 五、种子数据

### 5.1 site_configs 种子（当前部署实例）

```python
def init_site_seeds():
    with get_db() as conn:
        # 当前部署实例的配置
        conn.execute("""
            INSERT OR IGNORE INTO site_configs (id, domain, name, industry, tier, features)
            VALUES (1, ?, ?, ?, 'self_hosted', '["main"]')
        """, (os.environ.get('DEPLOY_DOMAIN', 'localhost'), 
              os.environ.get('DEPLOY_BRAND', 'VeroRon 维洛智能'),
              'ai'))
```

### 5.2 site_domains 种子（默认 3 个标准子域名）

```python
def init_site_domains_seeds():
    domain = os.environ.get('DEPLOY_DOMAIN', 'localhost')
    brand = os.environ.get('DEPLOY_BRAND', 'VeroRon')
    with get_db() as conn:
        defaults = [
            ('www',  f'www.{domain}',    f'{brand} 官网',        'default',  1),
            ('agent', f'agent.{domain}',  f'{brand} 管理后台',   'default',  1),
            ('platform', f'platform.{domain}', f'{brand} 用户中心', 'default', 1),
        ]
        for sub, full, name, template, published in defaults:
            conn.execute("""
                INSERT OR IGNORE INTO site_domains 
                (subdomain, full_domain, display_name, template, is_published)
                VALUES (?, ?, ?, ?, ?)
            """, (sub, full, name, template, published))
        conn.commit()
```

---

## 六、与现有系统的衔接

### 6.1 Nginx 路由

**当前模式（无需改动）：**
```
所有 *.easykai.cn → :8081（主站）
agent.easykai.cn → :8084（admin）
platform.easykai.cn → :8083（platform）
```

**关键点：** 新增子域名（如 `shop.easykai.cn`）后**不需要修改 Nginx 配置**，系统自动在应用层识别并分发。

### 6.2 Cookie / JWT SSO

Cookie domain 已经是 `'.easykai.cn'`，跨子域认证天然可用，无需改动。

### 6.3 现有的 site_routes.py

三个 API 端点 (`/api/site/config`、`/api/site/blocks`、`/api/site/plans`) 已使用 `request.headers.get('Host')` 查询——**中间件接入后它们可以继续工作或升级为使用 `g.current_site`**。

### 6.4 模板改造

各模板中需要根据 `current_site` 切换渲染逻辑：

```html
{% if current_site %}
  <!-- 子域名站点模式 -->
  <title>{{ current_site.name }} | {{ brand.site_name_cn }}</title>
  <meta name="theme-color" content="{{ current_site.theme_color }}">
{% else %}
  <!-- 主站默认模式（原文不变） -->
  <title>{{ brand.seo_title or brand.site_name_cn }}</title>
{% endif %}
```

**除 `<title>` 和品牌色外，模板结构不需要大改。**

---

## 七、AI 页面生成（未来扩展）

当前阶段**不实现** AI 生成业务逻辑，只预留数据结构：

- `site_domains.template` 字段用于后续绑定"页面模板"
- `site_domains.page_keys_json` 记录该域名启用哪些页面
- 后续可通过 LLM API 生成 `site_blocks` 内容（利用现有 `ai_analyze` 能力）

---

## 八、实施路径

### Phase 1（当前）
| 步骤 | 文件 | 改动量 |
|------|------|--------|
| 1. 新增 `site_domains` 表 + `init_site_domains_seeds()` | `database.py` | ~40 行 |
| 2. 创建子域名识别中间件 | `middleware/site_domain_middleware.py` | ~60 行 |
| 3. 在 site app 注册中间件 + context_processor | `site/app.py` | ~20 行 |
| 4. 管理后台 API（CRUD + 配额校验） | `auth-center/routes/admin.py` | ~150 行 |
| 5. 管理后台前端 UI | `admin/templates/partials/site_domains.html` | ~200 行 |
| 6. 种子数据注入当前 3 个默认子域名 | `site_routes.py` 的 `init_site_seeds()` | ~20 行 |
| 7. 模板头信息适配 | `admin/partials/head.html` + 各 `<title>` | ~20 行 |
| **合计** | | **~510 行** |

### Phase 2（后续）
- AI 页面内容生成（利用现有 LLM API）
- 页面拖拽排序或区块管理
- 统计仪表盘（各子域名访问量）

---

## 九、风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| 子域名配额校验依赖于 `PLAN_DOMAIN_LIMITS` 硬编码 | 与 `subscription_plans` 表中的 `features_json` 联动，后续可迁移到 DB 配置 |
| 中间件添加后可能影响主站性能 | 中间件只做一次轻量 `SELECT` 查询，使用 `g` 上下文缓存 |
| 用户自行添加非预期子域名 | `subdomain` 字段只有创建时写入，必须通过管理员 UI |
| 与现有 Nginx 路由冲突 | 新子域名自动路由到 :8081，不修改 Nginx；agent 和 platform 仍由 Nginx 固定分发 |
| Cookie 覆盖问题 | 全站已使用 `.domain.com` 通配符 Cookie domain，不会冲突 |
