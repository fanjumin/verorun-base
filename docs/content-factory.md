# 内容工厂（Content Factory）

> 信息捕获与 AI 内容加工管道，是易站智能建站系统的核心内容供应链。

---

## 一、概览（Overview）

**Content Factory**（内容工厂/信息捕获）是一套**自动化内容供应链**，覆盖从外部信息源采集、AI 智能加工、审核流转到多渠道发布的全流程。它使网站运营者可以"一次配置，持续生产"——将 RSS 订阅、Web 页面、外部 API 等来源的内容自动抓取，经 AI 清洗、提炼、排版，最终推送至 CMS 文章、社交媒体、知识库或 Agent Skill。

**核心理念**：用 AI 替代人工编辑，将信息处理效率提升 10 倍以上。

### 流水线模型（Pipeline）

```
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │  来源    │ →  │  采集器  │ →  │  原始    │ →  │  AI 加工  │ →  │  加工后  │
  │  Sources │    │Collectors│    │  Raw     │    │Processor │    │Processed│
  │ (RSS/API │    │(rss/web/│    │  Content │    │(Qwen)    │    │ Content │
  │  /Web)   │    │  api)   │    │          │    │          │    │         │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └────┬─────┘
                                                                       │
                                          ┌────────────────────────────┼──────────────┐
                                          ▼                            ▼              ▼
                                    ┌──────────┐              ┌────────────┐  ┌────────────┐
                                    │  CMS     │              │  技能推送  │  │  知识库    │
                                    │  文章发布 │              │Skill Push │  │Knowledge   │
                                    └──────────┘              │(Hermes/   │  │  Base      │
                                                              │ OpenClaw) │  │(Cleaner)   │
                                                              └────────────┘  └────────────┘
```

---

## 二、架构设计（Architecture）

### 2.1 模块结构

```
auth-center/
├── services/
│   └── content_factory/              # 内容工厂业务逻辑
│       ├── __init__.py               # 采集管理器入口 + COLLECTOR_MAP
│       ├── base_collector.py          # BaseCollector 抽象基类 + CollectResult
│       ├── collectors/
│       │   └── rss_collector.py       # RSS/Atom 通用采集器
│       ├── ai_processor.py            # AI 加工引擎（Qwen）
│       └── skill_pusher.py            # Skill 推送器
└── routes/
    └── content_factory.py             # 管理后台路由（14组API）
```

### 2.2 数据库表（Tables）

所有表位于同一 SQLite 数据库 `data/site.db` 中，在 `auth-center/models/database.py` 的 `init_db()` 中统一创建。

| 表名 | 用途 | 核心字段 |
|------|------|---------|
| `content_sources` | 内容源配置 | `source_type` (rss/api/web), `url`, `config_json`, `crawl_interval`, `is_active` |
| `raw_contents` | 采集原始数据 | `source_id`, `content_hash` (去重), `content_text/html`, `status` (pending/processing/processed/failed) |
| `processed_contents` | AI 加工结果 | `raw_id`, `content_type` (article/short_comment/social_card), `body`, `keywords`, `risk_level`, `status` (draft/review/approved/rejected/published) |
| `content_tasks` | 采集/加工任务记录 | `source_id`, `task_type`, `status`, `total_items`, `done_items`, `log_text` |
| `skill_pushes` | Skill 推送记录 | `processed_id`, `skill_name`, `target_agent` (hermes/openclaw), `status` |

#### content_sources 字段详解

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增主键 |
| `name` | TEXT NOT NULL | 来源名称（如"雪球热门"） |
| `source_type` | TEXT | 类型：`rss` / `web` / `api` |
| `platform` | TEXT | 平台标识（如 `xueqiu` / `sec`） |
| `url` | TEXT | 来源 URL（RSS feed 地址/API 端点/Web 页面） |
| `config_json` | TEXT JSON | 扩展配置（请求头、解析规则等） |
| `crawl_interval` | INTEGER | 自动采集间隔（秒），0=仅手动 |
| `keywords` | TEXT | 关键词过滤 |
| `max_per_run` | INTEGER | 单次最大采集量，默认 10 |
| `is_active` | INTEGER | 是否启用 |
| `sort_order` | INTEGER | 排序权重 |
| `last_crawled_at` | TEXT | 上次采集时间 |

---

## 三、采集器系统（Collector System）

### 3.1 采集器注册表（COLLECTOR_MAP）

在 `__init__.py` 中定义，采用懒加载工厂模式：

```python
COLLECTOR_MAP = {
    'rss': 'collectors.rss_collector.RSSCollector',
    # 'web': 'collectors.web_collector.WebCollector',   # 待实现
    # 'api': 'collectors.api_collector.ApiCollector',   # 待实现
}
```

通过 `get_collector(source_type, source_id, config)` 工厂函数实例化对应采集器。

### 3.2 BaseCollector 抽象基类

路径：`auth-center/services/content_factory/base_collector.py`

**职责**：
- 提供 `_random_ua()`、`_random_delay()`、`_headers()` 等常用工具
- 提供 `content_hash()`（SHA-256）和 `title_similar()`（SequenceMatcher > 80%）去重机制
- 提供 `save_results()` 方法，批量写入 `raw_contents` 表，自动去重
- 子类需实现 `collect(**kwargs) → List[CollectResult]`

**CollectResult 值对象**：包含 `title`, `content_text`, `content_html`, `source_url`, `author`, `publish_time`, `summary`, `tags`, `content_json`, `content_hash`

### 3.3 RSS 采集器（RSSCollector）

路径：`auth-center/services/content_factory/collectors/rss_collector.py`

基于 **feedparser** 库实现，支持 RSS 2.0 和 Atom 格式。核心逻辑：

1. 调用 `feedparser.parse(url, agent=UA)` 获取 feed
2. 遍历 `feed.entries`，按 `max_per_run` 限制数量
3. 依次尝试从 `entry.content` → `entry.summary` → `entry.description` 提取正文
4. 正则提取第一张图片作为封面（`content_json.cover_url`）
5. 解析 `published_parsed` / `updated_parsed` 为 `YYYY-MM-DD HH:MM:SS`
6. 提取 `entry.tags` 作为标签

### 3.4 Web / API 采集器

> ⚠️ **当前状态：未实现**。`COLLECTOR_MAP` 中仅注册了 `rss` 类型。Web 采集器（通用爬虫）和 API 采集器（JSON 接口适配）预留了扩展位置，待后续开发。

---

## 四、AI 加工程擎（AI Processor）

路径：`auth-center/services/content_factory/ai_processor.py`

### 4.1 API 对接

使用阿里云 **DashScope（通义千问 Qwen）** API，模型为 `qwen-turbo`。API Key 从 `system_config` 表 `dashscope_text_key` 读取。

| 配置项 | 值 |
|--------|-----|
| API Endpoint | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` |
| 模型 | `qwen-turbo` |
| 超时 | 60s |
| max_tokens | 4096 |
| temperature | 0.7 |

### 4.2 加工流程

```
原始内容 (raw_contents)
    │
    ▼
标记 status = 'processing'
    │
    ▼
调用 Qwen(PROCESS_PROMPT)  ─── 输入：标题 + 作者 + 正文(~24000字符)
    │
    ▼
解析 AI 返回 JSON
    ├── title:     优化标题（≤20字）
    ├── summary:   一句话摘要（≤50字）
    ├── body:      Markdown 重排正文
    ├── keywords:  关键词列表
    └── risk_level: low / normal / high / critical
    │
    ▼
写入 processed_contents，标记 raw.status = 'processed'
    │
    ▼
失败处理：JSON 解析失败 → 尝试修复（去除 ``` 包裹）→ 二次失败则标记 failed
```

### 4.3 Prompt 模板

- **SYSTEM_PROMPT**：定义 AI 作为"专业内容编辑"的角色，要求提取正文 → Markdown 重排 → 保留关键数据
- **PROCESS_PROMPT**：指定 JSON 输出格式，包含标题/摘要/正文/关键词/风险等级字段

### 4.4 批量处理

`batch_process(raw_ids, admin_id)` 逐条调用 `process_raw_content()`，返回 `{ok, fail, results}`。

---

## 五、管理后台（Admin Interface）

所有路由在 `auth-center/routes/content_factory.py` 中注册，Blueprint 前缀为 `/admin/content-factory`，统一通过 `_require_admin()` 鉴权。

| # | 路由 | 方法 | 说明 |
|---|------|------|------|
| 1 | `/sources` | GET | 来源列表（含分页、筛选） |
| 2 | `/sources` | POST | 新增来源 |
| 3 | `/sources/<id>` | PUT | 编辑来源 |
| 4 | `/sources/<id>` | DELETE | 删除来源 |
| 5 | `/crawl` | POST | 触发一次采集 |
| 6 | `/contents` | GET | 原始内容列表 |
| 7 | `/contents/<id>` | DELETE | 删除原始内容（级联删除加工内容） |
| 8 | `/process` | POST | AI 加工（批量） |
| 9 | `/processed` | GET | 加工内容列表 |
| 10 | `/processed/<id>` | GET/PUT | 编辑加工内容 |
| 11 | `/processed/batch-delete` | POST | 批量删除加工内容 |
| 12 | `/review` | POST | 审核流转（提交/通过/驳回/退回） |
| 13 | `/publish` | POST | 发布到 CMS / 社交媒体 |
| 14 | `/push-skill` | POST | 推送到 Agent Skill |
| 15 | `/pushed-skills` | GET/DELETE | 已推送 Skill 管理 |
| 16 | `/push-to-knowledge` | POST | 推送到知识库（Cleaner Agent） |
| 17 | `/ai-format` | POST | AI 深度排版（CMS 编辑器辅助） |
| 18 | `/ai-cover` | POST | AI 配图生成 |
| 19 | `/generate-static` | POST | 一键生成静态 HTML |
| 20 | `/stats` | GET | 仪表盘统计 |
| 21 | `/tasks` | GET | 任务列表 |
| 22 | `/api/v1/skills` | GET | 用户端 Skill 列表（无鉴权） |
| 23 | `/api/v1/skills/<id>/download` | GET | 用户端下载单个 Skill |

### 审核状态机（Review State Machine）

```
draft ──submit_review──→ review ──approve──→ approved ──publish──→ published
                            │                      │
                            └──reject──→ rejected   └──back_to_draft──→ draft
                            submitted──→ review
                            back_to_draft──→ draft
```

---

## 六、发布系统（Publishing）

### 6.1 内部 CMS 发布

调用 `models.cms.upsert_post()` 将加工内容写入 CMS 文章表，设置 `category='content_factory'`，自动生成 slug `cf-{pid}-{timestamp}`。发布后 `processed_contents.status` 更新为 `published`。

### 6.2 社交媒体发布

通过 `routes.social_push._publish_to_platform()` 推送至微信等平台，支持 `auto_publish` 参数。支持多平台同时发布。

### 6.3 Skill 推送（Skill Pusher）

路径：`auth-center/services/content_factory/skill_pusher.py`

将加工内容导出为 **SKILL.md** 格式，供 Hermes / OpenClaw Agent 使用：

- 生成包含 YAML 前置元数据的 Markdown 文件
- 安全命名（小写+连字符）
- 记录推送历史到 `skill_pushes` 表
- 提供用户端只读 API `/api/v1/skills` 供 Agent 拉取

### 6.4 知识库推送

通过 `routes.cleaner_agent.process_clean_content()` 调用数据清洗智能体（Cleaner Agent），将加工内容清洗后写入知识库。

### 6.5 静态页面生成

调用 `platform/staticgen.py` 的 `generate_post()` / `generate_all()` / `generate_category()` 等方法，生成静态 HTML 文件。

---

## 七、当前状态（Current Status）

| 功能 | 状态 | 说明 |
|------|------|------|
| RSS 采集 | ✅ 已完成 | 基于 feedparser，支持 RSS 2.0 / Atom |
| Web 采集 | ⏳ 待实现 | 预留 `web` 类型，采集器未编写 |
| API 采集 | ⏳ 待实现 | 预留 `api` 类型，采集器未编写 |
| AI 加工 | ✅ 已完成 | Qwen-turbo 单 Agent 加工 |
| 审核流转 | ✅ 已完成 | 5 状态状态机 |
| CMS 发布 | ✅ 已完成 | 写入 CMS 文章表 |
| 社交媒体发布 | ✅ 已完成 | 微信等多平台 |
| Skill 推送 | ✅ 已完成 | 生成 SKILL.md 供 Agent 使用 |
| 知识库推送 | ✅ 已完成 | 调用 Cleaner Agent |
| 静态页面生成 | ✅ 已完成 | 调用 staticgen 模块 |
| 自动定时采集 | ⏳ 待实现 | `crawl_interval` 字段已预留 |
| 多 Agent 加工链 | 💡 规划中 | 目前为单 Agent，计划引入质量审查 Agent |

---

## 八、相关文件索引（File Index）

| 文件 | 说明 |
|------|------|
| `auth-center/services/content_factory/__init__.py` | 采集管理器入口、COLLECTOR_MAP、`run_collection()` |
| `auth-center/services/content_factory/base_collector.py` | BaseCollector 基类、CollectResult、去重工具 |
| `auth-center/services/content_factory/collectors/rss_collector.py` | RSS/Atom 通用采集器 |
| `auth-center/services/content_factory/ai_processor.py` | AI 加工引擎（`process_raw_content` + `batch_process`） |
| `auth-center/services/content_factory/skill_pusher.py` | Skill 推送器（生成 SKILL.md） |
| `auth-center/routes/content_factory.py` | 管理后台路由（23 个端点） |
| `auth-center/models/database.py` | 数据库 Schema（5 张 Content Factory 表） |

---

## 九、开发指南（Dev Guide）

### 添加新采集器

1. 在 `collectors/` 下创建新文件，继承 `BaseCollector`
2. 实现 `collect(**kwargs) → List[CollectResult]`
3. 在 `__init__.py` 的 `COLLECTOR_MAP` 中注册
4. 在 `content_sources` 表中使用对应 `source_type`

### 配置 AI Key

在管理后台的"系统配置"中设置 `dashscope_text_key`，或在 `system_config` 表中直接插入：

```sql
INSERT INTO system_config (key, value) VALUES ('dashscope_text_key', 'sk-xxx');
```

### 依赖

- `feedparser`：RSS/Atom 解析
- `requests`：HTTP 请求（AI API 调用）
