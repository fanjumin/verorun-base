# 系统模块插件化改造分期工作计划

> 创建日期：2026-07-08
> 目标：将非核心模块逐步插件化，减轻 admin/app.py 冷启动负担，实现独立数据库

---

## 总览

```
Phase 1 · 零风险清理        bot/                    删除
Phase 2 · 低果实            analytics               独立 DB + 插件化
Phase 3 · 轻量解耦          captcha-service          注册解耦
                             health_service          注册解耦
Phase 4 · 路由抽取          AI Tools                从 admin.py/social_push.py 拆出
Phase 5 · 跨模块改造         health_check            独立 DB + 改 cron_jobs 注册方式
Phase 6 · 深度耦合（后期）    content_factory         需抽象 ContentRepository
                             shop                    体量大，需稳定
                             subscription            核心收入，需谨慎
```

### 预期效果

| 指标 | 改造前 | 改造后 |
|------|--------|--------|
| admin/app.py 行数 | ~917 | ~500 |
| 冷启动加载模块 | 25+ | ~10 |
| 后台线程 | 1 (AnalyticsProcessor) | 0 |
| 请求中间件 | 1 (AnalyticsMiddleware) | 0 |
| DB 写竞争 | 所有模块共用主库 | 各插件独立 DB |

### 保留不动（核心组件）

| 模块 | 原因 |
|------|------|
| **agent_matrix** | AI Agent 矩阵，与 AI 引擎紧密绑定 |
| **cognition-service** | AI 聊天 RAG 向量搜索（api_v1.py#L400），核心依赖 |

---

## Phase 1 — 删除 bot/（零风险）

### 背景

`bot/` 目录包含 Telegram 和 LINE Bot 的早期代码，零引用、零路由注册、零数据库表，纯占位代码。以后需要时重建。

### 删除清单

```
bot/__init__.py          (2 行)
bot/telegram_bot.py      (108 行)
bot/line_bot.py          (87 行)
```

### 验证步骤

```bash
# 确认无引用
grep -r "from bot" --include="*.py" f:/Sites/VeroRun/
grep -r "import bot" --include="*.py" f:/Sites/VeroRun/
# 应返回 0 结果（除 bot/ 自身外）
```

### 回滚

```bash
git revert <commit_hash>
```

---

## Phase 2 — analytics 插件化（独立 DB）

### 背景

analytics 模块在 [admin/app.py](file:///f:/Sites/VeroRun/admin/app.py) 中硬编码加载了三样东西：

1. `AnalyticsMiddleware(app, ...)` — 每个请求的 after_request 钩子
2. `AnalyticsProcessor` 后台线程 — 每 60 秒聚合日志
3. `analytics_bp` 蓝图 — 仪表盘页面

### 数据库方案

- 新建独立数据库：`data/analytics.db`
- 原有 11 张表全部迁入新库（不依赖主库任何表）

```sql
-- 迁移的 11 张表（全部自用，无跨模块引用）
analytics_logs
analytics_hourly_stats
analytics_daily_stats
analytics_visitor_sessions
analytics_events
analytics_page_stats
analytics_source_stats
analytics_geo_stats
analytics_device_stats
analytics_alerts
analytics_privacy_config
```

### 涉及文件

#### 新增

| 文件 | 说明 |
|------|------|
| `plugins/analytics/plugin.json` | 插件元数据 |
| `plugins/analytics/__init__.py` | BasePlugin 子类，生命周期管理 |

#### 修改

| 文件 | 改动 |
|------|------|
| `analytics/models.py` | `get_db()` 改为 `sqlite3.connect(data/analytics.db)` |
| [admin/app.py](file:///f:/Sites/VeroRun/admin/app.py) | 移除 L30-31（AnalyticsMiddleware + AnalyticsProcessor import）<br>移除 L110-123（Middleware 实例化 + 后台线程启动）<br>移除 L152（`analytics_bp` 注册） |

### 插件接口设计

```python
# plugins/analytics/__init__.py（伪代码）
class AnalyticsPlugin(BasePlugin):
    name = 'analytics'
    version = '0.1.0'
    description = 'Analytics Middleware & Dashboard'

    def on_enable(self, registry):
        from analytics.middleware import AnalyticsMiddleware
        from analytics.processor import AnalyticsProcessor
        from analytics.dashboard import analytics_bp
        
        self.middleware = AnalyticsMiddleware(self.app, service_name='admin')
        self.processor = AnalyticsProcessor()
        self.thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.thread.start()
    
    def register_routes(self):
        from analytics.dashboard import analytics_bp
        return [analytics_bp]
    
    def on_disable(self, registry):
        # 中间件和后台线程在 Flask 生命周期内无法安全移除，
        # disable 仅卸载 Blueprint，重启后生效
        pass
```

### 风险

- **低**：analytics 的所有表都是自用的，无跨模块查询
- 中间件在 `disable` 时无法热卸载（Flask 不支持），需重启生效 — 可接受

### 回滚

恢复 admin/app.py 的 import 和注册代码，恢复 analytics/models.py 的 DB 路径。

---

## Phase 3 — captcha-service + health_service 注册解耦

### 背景

这两个模块已是独立的微服务（有自己的 `server.py` / `runner.py`、独立的 requirements），仅在 [admin/app.py](file:///f:/Sites/VeroRun/admin/app.py) 中有几行注册代码。

### 数据库

两个模块已有独立数据库，无需改动。

### captcha-service 涉及文件

#### 新增

| 文件 | 说明 |
|------|------|
| `plugins/captcha_embedded/plugin.json` | 插件元数据 |
| `plugins/captcha_embedded/__init__.py` | BasePlugin 子类 |

#### 修改

| 文件 | 改动 |
|------|------|
| [admin/app.py](file:///f:/Sites/VeroRun/admin/app.py) | 移除 `from captcha_bp import captcha_bp, register_admin_stats`（L44）<br>移除 `app.register_blueprint(captcha_bp)`（L158）<br>移除 `register_admin_stats(app)`（L159） |

### health_service 涉及文件

health_service 目前仅在 [admin/app.py](file:///f:/Sites/VeroRun/admin/app.py) 中无对应的硬编码注册（它有自己的 [health_service/app.py](file:///f:/Sites/VeroRun/health_service/app.py)），可能已经是独立运行的。如果没有注册代码，则 Phase 3 只需处理 captcha。

### 回滚

恢复 admin/app.py 中被移除的 import 和注册代码。

---

## Phase 4 — AI Tools 路由抽取

### 背景

AI Tools 是 admin 侧边栏的一个菜单组（PPT Generation / Image Gen / Multimedia），其路由散落在 `admin_bp` 和 `social_bp` 中，需要抽取为独立 Blueprint。

### 当前分布

| 功能 | 前端 | 后端路由 | 所在文件 |
|------|------|---------|---------|
| PPT Generation | `social.html#L369` | `POST /admin/generate-ppt` | [admin.py#L3347](file:///f:/Sites/VeroRun/auth-center/routes/admin.py#L3347) |
| Image Gen | `social.html#L406` | `POST /admin/generate-image` | [admin.py#L3523](file:///f:/Sites/VeroRun/auth-center/routes/admin.py#L3523) |
| Multimedia | `social.html#L434` | `POST /admin/generate-image`（复用 social_bp） | [social_push.py#L138](file:///f:/Sites/VeroRun/auth-center/routes/social_push.py#L138) |

### 数据库

几乎不依赖（主要调用外部 AI API + 生成文件），无需独立 DB。

### 涉及文件

#### 新增

| 文件 | 说明 |
|------|------|
| `plugins/ai_tools/plugin.json` | 插件元数据 |
| `plugins/ai_tools/__init__.py` | BasePlugin 子类 |
| `plugins/ai_tools/routes.py` | 迁移 `generate-ppt`、`generate-image` 路由 |
| `plugins/ai_tools/static/ai_tools.js` | 从 social.html 抽离 AI Tools 相关 JS |
| `plugins/ai_tools/templates/ai_tools.html` | PPT/Image/Multimedia 模板片段 |

#### 修改

| 文件 | 改动 |
|------|------|
| `auth-center/routes/admin.py` | 删除 `/generate-ppt`、`/generate-image` 路由函数 |
| `auth-center/routes/social_push.py` | 删除多媒体生成相关路由 |
| `admin/templates/partials/social.html` | 删除 `l_ppt_gen()`、`imgGenerate()`、`l_media_video()` 及相关函数 |
| `admin/templates/partials/aliases.html` | 删除 `l_ppt`、`l_image`、`l_media_tools` 别名 |
| `admin/templates/partials/icons.html` | AI Tools 菜单组可能需要改为检查插件是否启用再渲染 |

### 模板注入方案

由于 AI Tools 的 HTML/JS 嵌入在 `social.html` 中，需要改为：

1. Plugin 提供独立 `ai_tools.html` 模板片段
2. 通过 `register_routes` 注册 Blueprint 时挂载 `/plugin/ai_tools/`
3. 前端菜单 `GROUPS` 在 `icons.html` 中动态检查插件是否可用

### 风险

- **低**：PPT/Image/Multimedia 三个功能调用外部 API，不操作数据库
- 前端菜单需要改为动态检测，否则 disabled 状态下仍显示菜单项（可接受，点击后报错提示启用插件）

---

## Phase 5 — health_check 独立 DB + cron 注册改造

### 背景

health_check 在 [admin/app.py](file:///f:/Sites/VeroRun/admin/app.py) 中硬编码加载：

1. `init_health_tables()` + `migrate_alert_schema()` + `seed_default_checks()` — 表初始化
2. `health_bp` 蓝图
3. `seed_health_schedules()` — 向 orchestrator 的 `cron_jobs` 表写入定时任务

### 数据库方案

- 新建独立数据库：`data/health.db`
- 原有 8 张表全部迁入新库

```sql
health_checks
check_runs
check_history
alert_config
alert_history
alert_silences
health_trend
fix_audit_log
```

### 关键改造：cron_jobs 注册方式

当前 [scheduler_setup.py](file:///f:/Sites/VeroRun/health_check/scheduler_setup.py) 直接向 orchestrator 的 `cron_jobs` 表 INSERT。改为通过 PluginManager 的 `register_jobs()` 接口注册：

```python
# 改造前（直写表）
from orchestrator.models import get_db as orch_db
with orch_db() as conn:
    conn.execute('INSERT INTO cron_jobs ...')

# 改造后（走插件标准接口）
def register_jobs(self):
    return [
        {
            'job_id': 'health_quick_scan',
            'func': self._run_quick_scan,
            'trigger': 'interval',
            'kwargs': {'seconds': 300},
        },
        # ...
    ]
```

### 涉及文件

#### 新增

| 文件 | 说明 |
|------|------|
| `plugins/health_check/plugin.json` | 插件元数据 |
| `plugins/health_check/__init__.py` | BasePlugin 子类 |

#### 修改

| 文件 | 改动 |
|------|------|
| `health_check/models.py` | `get_db()` 指向 `data/health.db` |
| `health_check/scheduler_setup.py` | 改为插件标准 `register_jobs()` 接口 |
| `health_check/__init__.py` | 调整蓝图导出 |
| [admin/app.py](file:///f:/Sites/VeroRun/admin/app.py) | 移除 L176-201（约 25 行初始化代码） |

### 风险

- **中**：cron_jobs 注册方式改造需要 orchestrator 支持从 PluginManager 获取 job 定义
- 如果 orchestrator 暂不支持 `register_jobs()` 回调，可先保留 `seed_health_schedules()` 的定时任务注册逻辑，仅做 DB 独立

---

## Phase 6 — 后期（暂不执行，仅列出）

### content_factory

- 与 `cms_posts`、`cms_categories`、`cms_tags` 共享表深度耦合
- 需要先设计 `ContentRepository` 抽象接口层
- 所有 DB 操作改为通过 Repository 接口，然后才能独立 DB

### shop（商城）

- 管理端 `shop_admin.py` + 用户端 `shop_public.py`，体量最大
- 与 `products`、`orders`、`categories` 等共享表耦合
- 周围已有 4 个插件（coupons/reviews/wishlist/order_notify）围绕它工作
- 需要稳定后再做

### subscription（订阅）

- 核心收入模块，与 `subscriptions`、`subscription_orders`、`subscription_plans`、`users` 等表耦合
- 4 个支付网关（支付宝/微信/Stripe/PayPal）延迟加载，当前无需减负
- 需要谨慎，放在最后

---

## 执行检查清单

### Phase 1
- [ ] 确认 `bot/` 零引用（grep 验证）
- [ ] 删除 `bot/` 目录
- [ ] git commit

### Phase 2
- [ ] 创建 `plugins/analytics/plugin.json`
- [ ] 创建 `plugins/analytics/__init__.py`（BasePlugin 子类）
- [ ] 修改 `analytics/models.py` 的 `get_db()` 指向 `data/analytics.db`
- [ ] 修改 `admin/app.py` 移除 analytics 硬编码
- [ ] 启动验证：插件自动激活，中间件正常工作，dashboard 可访问
- [ ] git commit

### Phase 3
- [ ] 创建 `plugins/captcha_embedded/plugin.json`
- [ ] 创建 `plugins/captcha_embedded/__init__.py`
- [ ] 修改 `admin/app.py` 移除 captcha 硬编码
- [ ] 确认 captcha 登录功能正常
- [ ] git commit

### Phase 4
- [ ] 创建 `plugins/ai_tools/plugin.json`
- [ ] 创建 `plugins/ai_tools/__init__.py`
- [ ] 创建 `plugins/ai_tools/routes.py`（迁移路由）
- [ ] 创建 `plugins/ai_tools/static/ai_tools.js`
- [ ] 修改 `admin.py` 删除 PPT/Image 路由
- [ ] 修改 `social_push.py` 删除多媒体路由
- [ ] 修改 `social.html` 删除 AI Tools JS
- [ ] 修改 `aliases.html` 删除别名
- [ ] 验证 PPT/Image/Multimedia 三项功能正常
- [ ] git commit

### Phase 5
- [ ] 创建 `plugins/health_check/plugin.json`
- [ ] 创建 `plugins/health_check/__init__.py`
- [ ] 修改 `health_check/models.py` 的 `get_db()` 指向 `data/health.db`
- [ ] 改造 `scheduler_setup.py` 使用 `register_jobs()` 接口
- [ ] 修改 `admin/app.py` 移除 health_check 硬编码
- [ ] 验证健康巡检 + 定时任务正常
- [ ] git commit

---

## 注意事项

1. **每次 Phase 独立 commit**，便于出问题时独立回滚
2. **Phase 间保持间隔**，确认上一 Phase 稳定后再开始下一 Phase
3. **在本地验证通过后**再同步到服务器
4. **不要同步 data/ 目录**到生产环境，避免覆盖生产数据
5. 如果某个 Phase 涉及新表/DB 迁移，需要在 `deploy_sftp.py` 或部署脚本中排除 `data/` 目录
