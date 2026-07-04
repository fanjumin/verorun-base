# Agent 矩阵 — 完整架构设计  v2.0

> 基于 易站智能 全部 22 个管理模块的 Agent 全覆盖方案
> 日期：2026-05-10

---

## 一、管理后台全局模块清单

当前 `admin/templates/admin.html` 的 NAV 定义包含 **22 个功能模块**，分布在 4 个分类下：

```
┌── 📋 管理 ──────────────────────────────────────┐
│  总览 / 用户管理 / Agent管理 / API Key          │
│  社区内容 / 工单 / 邮件 / 短信管理 / Agent矩阵   │
├── 📄 内容 ──────────────────────────────────────┤
│  CMS管理 / 内容工厂 / 自动调度                   │
│  统计分析 / 评论管理                             │
├── 💰 财务 ──────────────────────────────────────┤
│  套餐管理 / 订阅列表 / 订单管理                  │
│  优惠券 / 收入看板 / 扣款日志                    │
├── ⚙️ 系统 ──────────────────────────────────────┤
│  社区板块 / 系统设置 / 操作日志                  │
└─────────────────────────────────────────────────┘
```

后端文件及 API 端点数量：
| 路由文件 | 端点数 | 对应模块 |
|---------|--------|---------|
| admin.py | 36 | 总览、用户、Agent、API Key、社区内容、工单、短信、操作日志 |
| cms_admin.py | 18 | CMS管理 |
| comments.py | 5 | 评论管理 |
| content_factory.py | 23 | 内容工厂 |
| subscription/__init__.py | 21 | 套餐、订阅、订单、优惠券、收入、扣款 |
| social_push.py | 9 | 社媒推送 (已合并入CMS) |
| payment.py | 4 | 支付 |
| user.py | 20 | 系统设置、邮件、用户配置 |
| orchestrator/routes.py | 28 | 自动调度 (Cron + Workflow) |
| analytics/dashboard.py | ~15 | 统计分析 |

---

## 二、Agent 全覆盖映射

设计原则：**每个模块都有至少一个 Sub Agent 覆盖**，同时每个 Sub Agent 可管辖多个相关模块。

### Master Agent: Athena (雅典娜)

| 角色 | 覆盖模块 | 说明 |
|------|---------|------|
| **Orchestrator** | 全部 22 个模块 | 统一入口，任务分解，协调所有 Sub Agent |
| **总览(Dashboard)** | dashboard | 聚合所有 Sub Agent 的统计到统一看板 |

> Athena 是唯一与人类直接对话的 Agent。用户只需告诉 Athena 要做什么，她负责拆解、分配、监控、汇总。

---

### Sub Agent 1: CMS & Content Agent

**管辖模块：**
| 模块 | 管理后台名 | 关键能力 |
|------|-----------|---------|
| 📄 CMS管理 | cms | 文章CRUD、AI排版、AI配图、AI写作、栏目管理 |
| 💬 评论管理 | comments | 评论审核(通过/拒绝/删除)、AI敏感词检测、批量管理 |
| 🏭 内容工厂 | contentfactory | 采集源管理、RSS采集、AI加工、审核流、Skill推送、发布 |

**对接的后端 API：** cms_admin.py (18端点) + comments.py (5端点) + content_factory.py (23端点)

**典型任务：**
- "写一篇关于智能体的深度文章，AI配图，发布到技术和人工智能栏目，再推送到微信公众号"
- "审核今天所有的新评论，标记出包含敏感词的内容"
- "采集36氪最新3篇文章，AI加工作为本站内容"

---

### Sub Agent 2: Finance & Subscription Agent

**管辖模块：**
| 模块 | 管理后台名 | 关键能力 |
|------|-----------|---------|
| 📋 套餐管理 | plans | 套餐CRUD、定价调整、功能配置 |
| 💳 订阅列表 | subscriptions | 订阅状态查询、续费/过期/取消管理 |
| 🧾 订单管理 | sub_orders | 订单查询、退款处理、异常订单 |
| 🎫 优惠券 | coupons | 优惠券创建/发放/使用统计 |
| 📊 收入看板 | sub_stats | 月度/年度收入统计、付费用户分析 |
| 📄 扣款日志 | sub_events | 扣款记录查询、失败重试处理 |

**对接的后端 API：** subscription/__init__.py (21端点) + payment.py (4端点)

**典型任务：**
- "帮我查一下本月收入，和上个月对比"
- "给所有 pro 套餐快要到期的用户发续费提醒"
- "创建一个 '618大促' 优惠券，8折，有效期7天"
- "检查昨天的扣款日志，有没有失败记录"

---

### Sub Agent 3: User & System Agent

**管辖模块：**
| 模块 | 管理后台名 | 关键能力 |
|------|-----------|---------|
| 👥 用户管理 | users | 用户查询/禁启用、角色管理、登录历史 |
| 🤖 Agent 管理 | agents | 智能体配置、API Key关联、状态管理 |
| 🔑 API Key | keys | Key生成/吊销、使用统计、配额管理 |
| ⚙️ 系统设置 | config | 系统配置项管理(短信/SMTP/社媒/AI Key) |
| 📄 操作日志 | logs | 审计日志查询、时间段筛选、操作类型过滤 |

**对接的后端 API：** admin.py (36端点中的相关部分) + user.py (20端点)

**典型任务：**
- "查一下用户 139xxxxxxx 的当前套餐和API用量"
- "帮我系统设置中的 dashscope_text_key 是否已配置"
- "列出今天所有管理员的操作日志"
- "创建一个新用户，设置为管理员"

---

### Sub Agent 4: Health Check Agent

**管辖模块：**
| 模块 | 管理后台名 | 关键能力 |
|------|-----------|---------|
| ✉️ 邮件 | email | IMAP收信/SMTP发信、邮件搜索、草稿管理 |
| 📱 短信管理 | sms | 短信发送、发送记录、频率限制查询 |

**对接的后端 API：** admin.py (相关部分) + user.py (邮件相关)

**典型任务：**
- "审核今天所有待审核的社区帖子"
- "新增一个'金融AI'板块，放到第二位"
- "检查 support@easykai.cn 的收件箱，有没有新工单"
- "给用户 139xxxxxxx 发送验证短信"

---

### Sub Agent 5: Automation & Workflow Agent

**管辖模块：**
| 模块 | 管理后台名 | 关键能力 |
|------|-----------|---------|
| ⚡ 自动调度 | automation | Cron任务管理、Workflow设计/执行/监控 |
| 🔄 任务编排 | (自动化内部) | DAG 流程节点配置、条件分支、审批节点 |

**对接的后端 API：** orchestrator/routes.py (28端点)

**典型任务：**
- "新建一个 Cron 任务，每天早上8点统计昨天的数据"
- "创建一个内容流水线工作流：采集 → AI加工 → 人工审批 → 发布"
- "查一下有哪些工作流执行失败了"
- "暂停所有低优先级的任务"

> 此 Agent 是整个矩阵的**调度引擎接口**，复杂 DAG 工作流委托给已有的 orchestrator 执行。

---

### Sub Agent 6: Analytics & Intelligence Agent

**管辖模块：**
| 模块 | 管理后台名 | 关键能力 |
|------|-----------|---------|
| 📊 统计分析 | analytics | 访问统计、趋势分析、用户行为分析 |
| 📈 数据洞察 | (统计内部) | AI 解读数据、异常发现、趋势预测 |
| ⏰ 报告生成 | (统计内部) | 日报/周报/月报自动生成 |

**对接的后端 API：** analytics/dashboard.py (~15端点) + 分析系统处理器

**典型任务：**
- "分析本周的访问趋势，和前两周对比"
- "生成昨天的运营日报"
- "哪些栏目阅读量最高？TOP5排行"
- "检查是否有异常流量模式"

---

### Sub Agent 7: Ticket & Support Agent

**管辖模块：**
| 模块 | 管理后台名 | 关键能力 |
|------|-----------|---------|
| ✉️ 工单 | contacts | 工单(联系表单)处理、回复、状态管理 |
| 🎧 全站客服 | (全局) | 全站 AI 机器人客服、FAQ、转人工 |

**对接的后端 API：** admin.py (contacts 相关部分)

**典型任务：**
- "查看所有未读工单"
- "回复用户关于套餐购买的问题"
- "标记已处理完毕的工单"
- "统计本周工单量和平均响应时间"

---

### 全覆盖总览图

```
用户指令
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│              Athena (Master Agent / Coornidator)              │
│  总览 Dashboard | 任务分解 | Agent选择 | 进度监控 | 报告生成  │
└──┬──┬──┬──┬──┬──┬──┬──────────────────────────────────────┘
   │  │  │  │  │  │  │
   │  │  │  │  │  │  │
┌──▼──┴──┬──▼──┬──┴──┬──▼──┬──┴──┬──▼──┬──┴──┬──▼──┐
│ CMS &   │Finance│User &│Commu-│Auto- │Analy-│Ticket│
│ Content │& Subs│System│nicat.│mation│tics &│& Sup-│
│ Agent   │Agent │Agent │Agent │Agent │Intel.│port  │
├─────────┼──────┼──────┼──────┼──────┼──────┼──────┤
│📄CMS    │📋套餐│👥用户│💬社区│⚡自动│📊统计│✉️工单│
│💬评论   │💳订阅│🤖Agent│🌐板块│调度  │分析  │      │
│🏭内容   │🧾订单│🔑Key │✉️邮件│  ├─Cron│      │      │
│工厂     │🎫优惠│⚙️设置│📱短信│ ├─WF  │      │      │
│         │📊收入│📄日志│      │ └─DAG │      │      │
│         │📄扣款│      │      │      │      │      │
└─────────┴──────┴──────┴──────┴──────┴──────┴──────┘
```

**覆盖矩阵：22/22 模块 ✅ 100% 全覆盖**

---

## 三、任务流程详解

### 3.1 典型任务 — "帮我做个月度运营报告"

```
用户: "帮我做个月度运营报告，包含用户增长、收入、内容产出、流量分析"

Step 1 — Athena 任务分解
├── #[1] User & System Agent → "查询本月用户增长数据（新增用户、活跃用户）"
├── #[2] Finance Agent       → "查询本月收入数据（总收入、付费转化率）"
├── #[3] CMS & Content Agent → "查询本月内容产出数据（文章数、评论数）"
├── #[4] Analytics Agent     → "查询本月流量数据（PV/UV、来源渠道）"
└── #[5] Athena 自身         → "整合4份数据，生成月度运营报告"

Step 2 — 并行下发 (任务可并行执行)
  #[1] ──→ UserAgent ──→ completed ✅
  #[2] ──→ FinanceAgent ──→ completed ✅
  #[3] ──→ CMSAgent ──→ completed ✅
  #[4] ──→ AnalyticsAgent ──→ completed ✅

Step 3 — Athena 汇总
  ├── 各子任务结果 confidence >= 0.9 全部通过
  └── 整合为结构化报告

Step 4 — 报告输出
  ✅ **任务完成：月度运营报告**
  📊 用户增长: +15.3% (较上月)
  💰 收入: ¥128,500 (+22.1%)
  📝 内容: 85篇文章，1,234条评论
  📈 流量: 45,678 PV (+18.7%)
  ⚠️ 关注: 跳出率上升2.1%，建议优化首页加载
  ▶️ 建议: 推送月度报告给管理层
```

### 3.2 复杂任务 — DAG 流程

```
用户: "每天自动采集行业新闻，AI加工，人工审核后发布到CMS，再推送微信公众号"

Athena 将此注册为 Cron + Workflow 流程：
  ┌─────────────────────────────────────────────────────┐
  │ [Automation Agent] → 创建 Cron Job (每日08:00)      │
  │                      → 创建 Workflow DAG:           │
  │                         node1: ContentFactory采集    │
  │                         node2: ContentFactory AI加工 │
  │                         node3: 人工审批 (CMS Agent)  │
  │                         node4: CMS发布 (CMS Agent)  │
  │                         node5: 微信推送 (CMS Agent)  │
  └─────────────────────────────────────────────────────┘
  
  此流程注册后永久运行，每日自动执行。
```

---

## 四、数据库设计 (4张新表)

### 4.1 agent_matrix — Agent 配置表

```sql
CREATE TABLE IF NOT EXISTS agent_matrix (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,                       -- Agent 名称（如 "CMS Agent"）
    role_type       TEXT NOT NULL DEFAULT 'sub'
                    CHECK(role_type IN ('master','sub')), -- master / sub
    description     TEXT DEFAULT '',                     -- 职责描述（如 "内容管理专家"）
    
    -- 管辖模块
    domain          TEXT NOT NULL DEFAULT 'general',     -- 主领域标识
    managed_modules TEXT DEFAULT '[]',                   -- JSON: 管辖的模块列表
                                                         -- ["cms","comments","content_factory"]
    
    -- AI 引擎配置
    provider        TEXT NOT NULL DEFAULT 'dashscope',   -- openai|deepseek|openrouter|ollama|dashscope
    model_name      TEXT NOT NULL DEFAULT 'qwen-turbo',
    api_key_ref     TEXT DEFAULT 'dashscope_text_key',   -- 引用 system_config 中的 key
    base_url        TEXT DEFAULT '',
    
    -- Prompt 系统
    system_prompt   TEXT DEFAULT '',                     -- 主 System Prompt
    role_prompt     TEXT DEFAULT '',                     -- 角色定义（简短版）
    task_template   TEXT DEFAULT '',                     -- 任务执行模板
    
    -- 能力清单
    capabilities    TEXT DEFAULT '[]',                   -- JSON: ["text_gen","read_data","publish","review"]
    
    -- 权限与资源
    allowed_tools   TEXT DEFAULT '[]',                   -- JSON: 允许的 tool 列表
    max_concurrency INTEGER DEFAULT 1,
    priority        INTEGER DEFAULT 5,                  -- 1-10
    auto_approve    INTEGER DEFAULT 0,                   -- 是否自动批准结果
    
    -- 状态
    is_active       INTEGER DEFAULT 1,
    
    -- 统计
    tasks_total     INTEGER DEFAULT 0,
    tasks_success   INTEGER DEFAULT 0,
    tasks_failed    INTEGER DEFAULT 0,
    last_run_at     TEXT DEFAULT '',
    
    -- 时间
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    
    UNIQUE(name, role_type)
);
```

### 4.2 agent_tasks — 任务调度表

```sql
CREATE TABLE IF NOT EXISTS agent_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT UNIQUE NOT NULL,                -- 'AT-20260510-XXXX'
    parent_task_id  TEXT DEFAULT NULL,                   -- 父任务ID（树形结构）
    master_task_id  TEXT DEFAULT NULL,                   -- 顶层Master任务ID
    
    source_agent_id INTEGER NOT NULL,                    -- 发起Agent (agent_matrix.id)
    target_agent_id INTEGER NOT NULL,                    -- 执行Agent (agent_matrix.id)
    
    -- 任务内容
    task_type       TEXT NOT NULL DEFAULT 'execute'
                    CHECK(task_type IN ('execute','review','approve','composite','cron')),
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    input_data      TEXT DEFAULT '{}',                   -- JSON
    expected_output TEXT DEFAULT '{}',                   -- JSON
    
    -- 模块关联
    target_module   TEXT DEFAULT '',                     -- 目标模块名（如 "cms","users"）
    target_api      TEXT DEFAULT '',                     -- 特定API端点（可选）
    
    -- 执行控制
    priority        INTEGER DEFAULT 5,
    max_retries     INTEGER DEFAULT 3,
    retry_count     INTEGER DEFAULT 0,
    timeout_seconds INTEGER DEFAULT 300,
    
    -- 状态机
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','running','completed','failed',
                                     'cancelled','needs_review','retrying')),
    
    -- 结果
    result_data     TEXT DEFAULT '{}',                   -- JSON
    confidence      REAL DEFAULT 0.0,
    error_message   TEXT DEFAULT '',
    
    -- 自检与互检
    self_review     TEXT DEFAULT '',
    cross_review    TEXT DEFAULT '',
    
    -- 时间
    created_at      TEXT DEFAULT (datetime('now')),
    started_at      TEXT DEFAULT '',
    completed_at    TEXT DEFAULT '',
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_at_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_at_source ON agent_tasks(source_agent_id);
CREATE INDEX IF NOT EXISTS idx_at_target ON agent_tasks(target_agent_id);
CREATE INDEX IF NOT EXISTS idx_at_master ON agent_tasks(master_task_id);
CREATE INDEX IF NOT EXISTS idx_at_module ON agent_tasks(target_module);
```

### 4.3 task_logs — 执行日志

```sql
CREATE TABLE IF NOT EXISTS task_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL REFERENCES agent_tasks(task_id),
    agent_id        INTEGER NOT NULL REFERENCES agent_matrix(id),
    
    log_level       TEXT NOT NULL DEFAULT 'info' CHECK(log_level IN ('debug','info','warn','error')),
    log_type        TEXT NOT NULL DEFAULT 'execution'
                    CHECK(log_type IN ('execution','self_review','cross_review','approval','api_call')),
    
    message         TEXT NOT NULL,
    metadata        TEXT DEFAULT '{}',                   -- JSON
    
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tl_task ON task_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_tl_type ON task_logs(log_type);
```

### 4.4 agent_conversations — 对话记录

```sql
CREATE TABLE IF NOT EXISTS agent_conversations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    master_task_id  TEXT DEFAULT '',                     -- 关联顶层任务
    session_id      TEXT NOT NULL,                       -- 对话会话ID
    
    role            TEXT NOT NULL CHECK(role IN ('user','master','sub','system')),
    agent_id        INTEGER DEFAULT NULL,                -- agent_matrix.id 当 role=sub
    agent_name      TEXT DEFAULT '',                     -- 冗余，显示用
    
    content         TEXT NOT NULL,                       -- 消息内容
    metadata        TEXT DEFAULT '{}',                   -- JSON
    
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ac_session ON agent_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_ac_task ON agent_conversations(master_task_id);
```

---

## 五、各 Sub Agent 专属 System Prompt

### 5.1 CMS & Content Agent Prompt

```markdown
# 角色定义
你是 **CMS & Content Agent**，易站智能 的内容专家。你管辖所有与内容创作、管理、发布相关的模块。

# 管辖模块
📄 **CMS管理** — 文章创建/编辑/排版/发布/栏目管理
💬 **评论管理** — 评论审核/敏感词检测/批量管理
🏭 **内容工厂** — RSS采集源/AI加工/审核流/Skill推送

# 核心能力
1. 调用 cms_admin API 进行文章全生命周期管理
2. 调用 Qwen 进行 AI 写作、排版、摘要生成
3. 调用通义万相 Wan2.7-Image 生成配图
4. 调用评论 API 审核/管理评论
5. 调用内容工厂 API 进行采集、加工、发布
6. 调用社媒推送 API 发布到微信/微博/头条

# 行为准则
- 文章质量标准：标题≤30字吸引人，正文科技类≥800字，新闻类≥300字
- 必须有分段、关键句加粗、配图
- 评论审核：先过本地敏感词库，再过Qwen语义分析
- 内容加工：保留原文核心信息，添加深度分析
- 执行完成后必须自检（confidence 分数）
- confidence < 0.7 时自动重试，最多3次
```

### 5.2 Finance Agent Prompt

```markdown
# 角色定义
你是 **Finance & Subscription Agent**，易站智能 的财务专家。你管理所有订阅、支付、收入模块。

# 管辖模块
📋 **套餐管理** — 套餐定义/定价/功能配置 CRUD
💳 **订阅列表** — 用户订阅状态/续费/过期/取消
🧾 **订单管理** — 订单查询/退款/异常处理
🎫 **优惠券** — 创建/发放/使用统计
📊 **收入看板** — 月度收入/付费用户/ARPU
📄 **扣款日志** — 扣款记录/失败重试

# 核心能力
1. 套餐 CRUD：创建/编辑/启用/禁用套餐
2. 订阅管理：查询用户订阅，处理续费/取消
3. 订单处理：查询订单详情，处理退款
4. 优惠券：创建优惠券、查看使用情况
5. 收入分析：月收入、付费转化率、ARPU
6. 扣款监控：检查失败记录，执行重试

# 行为准则
- 涉及财务数据必须精确，不做近似
- 退款操作必须明确请求用户二次确认
- 收入分析要提供同比/环比
- 订单异常需标记优先级
```

### 5.3 User & System Agent Prompt

```markdown
# 角色定义
你是 **User & System Agent**，易站智能 的用户管理和系统配置专家。

# 管辖模块
👥 **用户管理** — 用户查询/禁启用/角色/登录历史
🤖 **Agent管理** — 智能体配置/API Key关联
🔑 **API Key** — Key生成/吊销/使用统计/配额
⚙️ **系统设置** — 所有配置项管理
📄 **操作日志** — 审计日志/操作追踪

# 核心能力
1. 用户查询：按ID/手机号/用户名搜索用户
2. 用户管理：启用/禁用、管理员角色设置
3. Agent配置：管理已有agents表
4. API Key：生成、吊销、查看使用量和限额
5. 系统配置：读写 system_config 表
6. 日志查询：按时间/类型/管理员筛选

# 行为准则
- 禁用用户需要二次确认
- API Key 吊销后不可恢复
- 操作日志不可删除，只可查询
- 系统配置项修改后记录变更
```

### 5.4 Health Check Agent Prompt

```markdown
# 角色定义
你是 **Health Check Agent**，易站智能 的系统健康监控与运维专家。

# 管辖模块
💬 **社区内容** — Agent经验帖审核/管理
🌐 **社区板块** — 7大板块CRUD/排序
✉️ **邮件** — IMAP收信/SMTP发信/邮件管理
📱 **短信管理** — 短信发送/记录查询

# 核心能力
1. 社区内容：审核经验帖、管理发布状态
2. 社区板块：创建/编辑/排序/禁用版块
3. 邮件客户端：查看收件箱、发送邮件、搜索
4. 短信管理：发送验证短信、查询发送记录

# 行为准则
- 社区内容审核：检查是否违规/重复/低质
- 版块操作：path 有 UNIQUE 约束，删除需清空内容
- 邮件：遵守 IMAP 协议，不删除非垃圾邮件
- 短信：遵守频率限制，不重复发送
```

### 5.5 Automation Agent Prompt

```markdown
# 角色定义
你是 **Automation & Workflow Agent**，易站智能 的调度和自动化专家。你负责所有定时任务和工作流。

# 管辖模块
⚡ **自动调度** — Cron任务管理/执行/监控
🔄 **工作流引擎** — Workflow DAG设计/运行/状态管理
📋 **任务依赖** — DAG边/条件分支/审批节点

# 核心能力
1. Cron任务：创建/编辑/暂停/恢复/删除定时任务
2. Workflow：设计DAG工作流（节点+边）
3. 执行监控：查看运行实例/日志/重试
4. 调度器：启动/暂停/恢复全局调度
5. 节点类型：12种内置节点（ai_agent, data_collect, condition, publish等）

# 行为准则
- 创建 Cron 任务时指定明确的调度表达式
- Workflow 设计遵循节点依赖关系
- 分析节点需 analytics 模块已注册
- 暂停/恢复不影响正在执行的任务
```

### 5.6 Analytics Agent Prompt

```markdown
# 角色定义
你是 **Analytics & Intelligence Agent**，易站智能 的数据分析专家。你从数据中发现洞察。

# 管辖模块
📊 **统计分析** — 访问统计/趋势/用户行为
📈 **数据洞察** — AI解读/异常发现/趋势预测
⏰ **报告生成** — 日报/周报/月报

# 核心能力
1. 访问统计：PV/UV/来源/时段分析
2. 趋势分析：周环比/月同比/热门内容排行
3. AI解读：用自然语言解释数据趋势
4. 报告生成：结构化的运营报告
5. 异常检测：流量突变/访问异常

# 行为准则
- 数据必须有基数对比（环比/同比），单一数值无意义
- AI解读要具体，不要泛泛而谈
- 异常检测需提供时间范围和严重程度
- 报告结尾必须有 actionable insights
```

### 5.7 Ticket Agent Prompt

```markdown
# 角色定义
你是 **Ticket & Support Agent**，易站智能 的客服专家。你处理所有用户咨询和工单。

# 管辖模块
✉️ **工单** — 联系表单处理/回复/状态管理
🎧 **全站客服** — AI客服/FAQ/转人工

# 核心能力
1. 工单查询：按时间/状态/用户查看工单
2. 工单处理：回复用户、标记已处理
3. 统计：工单量、响应时间、处理率

# 行为准则
- 未读工单优先处理
- 回复清晰、礼貌、完整
- 复杂问题标记后升级给管理员
- 记录每次回复内容
```

---

## 六、JSON 通信协议

```json
{
  "protocol": "agent-matrix-v1",
  "task": {
    "task_id": "AT-20260510-0001",
    "parent_task_id": null,
    "master_task_id": "AT-20260510-0001",
    "source_agent": "Athena",
    "target_agent": "CMS Agent",
    "module": "cms",
    "type": "execute",
    "title": "创建智能体科普文章",
    "input": {
      "action": "create_article",
      "params": {
        "title": "智能体技术科普：从概念到实践",
        "content": "请生成一篇...",
        "category": "技术",
        "publish": true,
        "social_push": false
      }
    },
    "expected_output": {
      "fields": ["post_id", "title", "publish_status", "url"]
    },
    "timeout": 300,
    "max_retries": 3
  },
  "result": {
    "task_id": "AT-20260510-0001",
    "status": "completed",
    "confidence": 0.95,
    "data": {
      "post_id": 42,
      "title": "智能体技术科普：从概念到实践",
      "publish_status": "published",
      "url": "https://easykai.cn/article/42"
    },
    "self_review": "文章结构完整，AI配图已生成，通过质量检查",
    "logs": [
      {"at": "09:00:01", "level": "info", "msg": "接收任务"},
      {"at": "09:00:02", "level": "info", "msg": "调用Qwen生成文章"},
      {"at": "09:00:15", "level": "info", "msg": "调用Wan2.7生成配图"},
      {"at": "09:00:45", "level": "info", "msg": "发布到CMS成功"},
      {"at": "09:00:46", "level": "info", "msg": "自检通过 (0.95)"}
    ],
    "duration_ms": 45000
  }
}
```

---

## 七、文件结构

```
agent-matrix/
├── __init__.py
├── models.py              # 4张表的 CRUD 操作
├── engine.py              # AI 引擎封装（复用 crypto + dashscope）
├── orchestrator.py        # 任务协调核心
│     └── AgentOrchestrator
│           ├── decompose_task()    — 任务分解
│           ├── select_agent()      — 选择合适 Sub Agent
│           ├── assign_task()       — 下发任务
│           ├── execute_task()      — 执行（同步）
│           ├── execute_batch()     — 批量并行执行
│           ├── collect_results()   — 收集结果
│           ├── retry_failed()      — 重试失败任务
│           └── generate_report()   — 生成报告
├── agent_runner.py        # Agent 执行器
│     └── AgentRunner
│           ├── run()              — 执行一次 Agent 对话
│           ├── self_critique()    — 自检
│           └── call_api()         — 调用后台 API
├── routes.py              # Flask Blueprint (~40端点)
└── prompts/
      ├── master_prompt.md         # Athena Prompt
      ├── sub_cms_prompt.md        # CMS Agent Prompt
      ├── sub_finance_prompt.md    # Finance Agent Prompt
      ├── sub_user_prompt.md       # User & System Agent Prompt
      ├── sub_automation_prompt.md # Automation Agent Prompt
      ├── sub_analytics_prompt.md  # Analytics Agent Prompt
      └── sub_ticket_prompt.md     # Ticket Agent Prompt

admin/
├── app.py                         # +agent_matrix_bp 注册
└── templates/admin.html           # +Agent Matrix 导航 + l_matrix + 对话UI
```

---

## 八、API 端点设计

### 8.1 Agent 管理 (17端点)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/agent-matrix/agents | Agent列表 (?role=master\|sub&domain=...) |
| POST | /admin/agent-matrix/agents | 创建Agent |
| GET | /admin/agent-matrix/agents/<id> | Agent详情 |
| PUT | /admin/agent-matrix/agents/<id> | 更新Agent |
| DELETE | /admin/agent-matrix/agents/<id> | 删除Agent |
| POST | /admin/agent-matrix/agents/<id>/test | 测试Agent |
| POST | /admin/agent-matrix/agents/<id>/toggle | 启用/禁用 |

### 8.2 任务管理 (9端点)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/agent-matrix/tasks | 任务列表 (?status=&module=&agent=) |
| GET | /admin/agent-matrix/tasks/<task_id> | 任务详情 |
| POST | /admin/agent-matrix/tasks/<task_id>/cancel | 取消 |
| POST | /admin/agent-matrix/tasks/<task_id>/retry | 重试 |
| GET | /admin/agent-matrix/tasks/<task_id>/logs | 任务日志 |

### 8.3 Master Agent 对话 (5端点)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /admin/agent-matrix/chat | 向Athena发指令（核心入口） |
| GET | /admin/agent-matrix/chat/history | 对话历史列表 |
| GET | /admin/agent-matrix/chat/<session_id> | 对话详情 |
| POST | /admin/agent-matrix/chat/<session_id>/clear | 清除会话 |

### 8.4 统计与监控 (4端点)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/agent-matrix/stats | 矩阵统计概览 |
| GET | /admin/agent-matrix/dashboard | 实时看板 |
| GET | /admin/agent-matrix/tasks/recent | 最近任务记录 |

### 8.5 内部调度 (2端点)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /admin/agent-matrix/dispatch | 直接下发任务给指定Agent |
| GET | /admin/agent-matrix/agents/<id>/capabilities | 查询Agent能力清单 |

---

## 九、预设 Seed 数据

创建时自动插入 1 个 Master + 7 个 Sub Agent：

| Agent | role_type | domain | model | managed_modules |
|-------|-----------|--------|-------|-----------------|
| Athena | master | orchestration | gpt-4o | (所有模块) |
| CMS Agent | sub | cms | qwen-turbo | ["cms","comments","content_factory"] |
| Finance Agent | sub | finance | qwen-turbo | ["plans","subscriptions","sub_orders","coupons","sub_stats","sub_events"] |
| User System Agent | sub | system | qwen-turbo | ["users","agents","keys","config","logs"] |
| Automation Agent | sub | automation | qwen-turbo | ["automation"] |
| Analytics Agent | sub | analytics | qwen-turbo | ["analytics"] |
| Ticket Agent | sub | support | qwen-turbo | ["contacts"] |

> 所有 Sub Agent 默认使用 `system_qwen` 引擎（复用 system_config 中的 `dashscope_text_key`），无需额外配置 API Key。

---

## 十、与现有基础设施的集成

### Workflow 引擎集成

Agent Matrix 的复杂/重复性任务可注册为 Workflow：

```
用户: "每天早上8点自动生成运营日报"
  → Automation Agent 创建 Cron Job (daily 08:00)
  → 触发 Workflow DAG:
     [Analytics Agent 拉数据] 
     → [Athena 聚合生成报告]
     → [通知管理员]
```

### Cron 任务集成

```
用户: "每隔2小时检查一次有没有新的工单"
  → Ticket Agent 设置 check_interval=2h
  → 注册到 orchestrator 的 APScheduler
  → 到期自动触发 Ticket Agent 执行
```

### 现有 agent_engine 复用

Agent Matrix 的 engine.py 直接复用 `auth-center/services/agent_engine.py` 的 `UniversalAgentEngine` 类，添加 Prompt 注入和自检逻辑。

---

## 十一、MVP 实施路线

### Phase 1 ⚡ (本次实现)
- [ ] 4张数据库表 + models.py
- [ ] engine.py (AI引擎封装)
- [ ] agent_runner.py (Agent执行器)
- [ ] orchestrator.py (任务协调核心)
- [ ] routes.py (全部API端点)
- [ ] admin/app.py 注册蓝图
- [ ] admin.html 新增导航 + 管理界面

### Phase 2 🚀 (Phase 1完成后)
- [ ] Master Agent 对话界面 (聊天窗口)
- [ ] Sub Agent 管理可视化
- [ ] 预设Prompt种子数据
- [ ] 任务监控看板

### Phase 3 🔧 (后续迭代)
- [ ] Workflow 深度集成
- [ ] 跨Agent互检
- [ ] 全自动运营（如日报自动生成）
- [ ] 可视化Agent编排

---

## 十二、安全与监控

1. **权限控制** — 所有 API 通过 `_require_admin()` 鉴权，复用现有 JWT
2. **操作审计** — agent_tasks + task_logs 提供完整审计链
3. **错误隔离** — 单个 Sub Agent 失败不影响其他 Agent
4. **重试机制** — 最多3次自动重试，指数退避
5. **超时保护** — 每个任务有 timeout_seconds，超时自动标记 failed
6. **资源控制** — max_concurrency 防止 API 过载
