# Agent 矩阵 — AI矩阵编排系统

> 易站 AI 平台的核心智能引擎：1 个 Master Agent (Athena) + 12 个 Sub Agent  
> 5 家 AI 供应商集成 · 6 张核心表 · 9 张调度表 · ~82 个 API 端点  
> 支持 DAG 工作流 · Cron 调度 · 自动任务分解 · 自检重试 · 多模态生成

---

## 目录

1. [系统概述](#一系统概述)
2. [架构总览](#二架构总览)
3. [Agent 体系](#三agent-体系)
4. [核心流程](#四核心流程)
5. [AI 引擎 & 供应商集成](#五ai-引擎--供应商集成)
6. [数据库设计](#六数据库设计)
7. [API 参考](#七api-参考)
8. [Orchestrator 自动化调度](#八orchestrator-自动化调度)
9. [Workflow 工作流引擎](#九workflow-工作流引擎)
10. [工具调用模式](#十工具调用模式)
11. [监控 & 可观测性](#十一监控--可观测性)
12. [Prompt 系统](#十二prompt-系统)
13. [集成与扩展](#十三集成与扩展)
14. [配置指南](#十四配置指南)
15. [常见问题](#十五常见问题)

---

## 一、系统概述

Agent 矩阵（Agent Matrix）是易站 AI 平台的 AI矩阵编排系统，提供从指令输入到任务执行、结果汇总的完整闭环。

### 核心能力

- **智能任务分解**：Master Agent (Athena) 自动将复杂指令拆解为可并行执行的子任务
- **多供应商路由**：5 家 AI 供应商（DashScope / OpenAI / DeepSeek / OpenRouter / Ollama）统一接口
- **并行执行**：ThreadPoolExecutor 最多 5 路并行，300 秒超时熔断
- **自检重试**：每 Agent 输出自我评分，置信度 < 0.7 自动重试（最多 3 次）
- **多模态支持**：文本 / 图像生成 / 语音克隆 / 数字人视频
- **Token 审计**：精确记录每次 LLM 调用的 token 消耗，支持按日汇总与费用估算
- **异步调度**：APScheduler Cron 定时任务 + DAG 工作流引擎

### 适用场景

| 场景 | 说明 |
|------|------|
| 智能客服 | 用户提问 → Master 分解 → Sub Agent 查询 → 汇总回复 |
| 内容创作 | 写文章 → CMS Agent + Image Agent 并行输出 → 一键发布 |
| 数据清洗 | 脏数据 → Cleaner Agent 清洗 → 写入知识库 |
| 供应链管理 | 库存查询 → Shop Agent 协同 |
| 自动化工作流 | 定时拉取 RSS → AI 加工 → CMS 发布（全自动） |
| 多模态生成 | 生成 PPT / 数字人视频 / 语音克隆 |

---

## 二、架构总览

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        管理后台 (agent.easykai.cn:8084)                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Agent 矩阵 UI (Admin Panel)                   │   │
│  │  创建/配置 Agent | 下发指令 | 监控执行 | 查看报告               │   │
│  └──────────────────────────┬───────────────────────────────────────┘   │
│                             │                                            │
│  ┌──────────────────────────▼───────────────────────────────────────┐   │
│  │                      Agent 矩阵核心层                              │   │
│  │                                                                    │   │
│  │  ┌──────────────────────┐  ┌────────────────────────────────┐    │   │
│  │  │    Master Agent      │  │    Task Orchestrator            │    │   │
│  │  │    (Athena, GPT-4o)  │─▶│  - process_instruction()       │    │   │
│  │  │    接收指令           │  │  - decompose_task() (AI/模板)   │    │   │
│  │  │    任务分解            │  │  - dispatch_sub_tasks()       │    │   │
│  │  │    汇总报告            │  │  - _build_summary()           │    │   │
│  │  │    自检 & 重试         │  │  - 熔断/超时/重试              │    │   │
│  │  └──────────────────────┘  └──────────────┬─────────────────┘    │   │
│  │                                            │                        │   │
│  │  ┌────────────────────────────────────────┴─────────────────────┐  │   │
│  │  │                     ThreadPool Executor                      │  │   │
│  │  │               (最多 5 路并行，300s 超时)                      │  │   │
│  │  └────────┬───────────┬───────────┬───────────┬────────────────┘  │   │
│  │           │           │           │           │                    │   │
│  │  ┌────────▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────────┐           │   │
│  │  │ CMS Agent  │ │ Image  │ │ Shop   │ │ ... (12     │           │   │
│  │  │ (文章/内容) │ │ Agent  │ │ Agent  │ │  Sub Agents)│           │   │
│  │  └─────────────┘ └────────┘ └────────┘ └─────────────┘           │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                             │                                            │
├─────────────────────────────┼────────────────────────────────────────────┤
│                         现有服务集成层                                      │
│  ┌─────────┐ ┌────────┐ ┌───────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │ CMS API │ │ 内容   │ │ Work  │ │ Cleaner │ │ 云服务   │ │Social   │ │
│  │         │ │ 工厂   │ │ flow  │ │ Agent   │ │ 开通     │ │Push     │ │
│  └─────────┘ └────────┘ └───────┘ └─────────┘ └─────────┘ └─────────┘ │
│                             │                                            │
├─────────────────────────────┼────────────────────────────────────────────┤
│                          数据库层                                           │
│  Agent Matrix 6 张表  |  Orchestrator 9 张表  |  现有 easykai.db 所有表   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 服务拓扑

| 服务 | 端口 | 域名 | 职责 |
|------|------|------|------|
| Platform | 8083 | easykai.cn | 前端用户门户 |
| Admin | 8084 | agent.easykai.cn | 管理后台 + Agent 矩阵 UI |
| Auth-Center | 8081 | — | 认证 + 数据模型 + AI 引擎 |
| Captcha | 8090 | — | 验证码服务 |

### 模块文件结构

```
agent_matrix/
├── __init__.py              # 初始化 + blueprint 注册
├── models.py                # 6 张表的 CRUD + 种子数据
├── engine.py                # AIEngine — 5 供应商统一封装
├── orchestrator.py          # AgentOrchestrator — 核心编排器
├── agent_runner.py          # AgentRunner — 单 Agent 执行器
├── routes.py                # ~35 个 API 端点
├── ARCHITECTURE.md          # 架构设计文档 v1
├── ARCHITECTURE_v2.md       # 架构设计文档 v2（22 模块覆盖）
├── README.md                # 本文档
└── prompts/
    ├── master_prompt.md         # Athena (Master Agent) 系统提示词
    ├── sub_cms_prompt.md        # CMS Agent
    ├── sub_finance_prompt.md    # Finance Agent
    ├── sub_user_prompt.md       # User System Agent
    ├── sub_health_check_prompt.md  # Health Check Agent
    ├── sub_automation_prompt.md # Automation Agent
    ├── sub_analytics_prompt.md  # Analytics Agent
    ├── sub_ticket_prompt.md     # Ticket Agent
    ├── sub_chatbot_prompt.md    # Kai Assistant (聊天机器人)
    ├── sub_voice_prompt.md      # Voice Agent
    ├── sub_video_prompt.md      # Video Agent
    ├── sub_image_prompt.md      # Image Agent
    ├── sub_shop_prompt.md       # Shop Agent
    └── sub_supply_chain_prompt.md # [用户模板] 自定义供应链 Agent

orchestrator/
├── __init__.py              # 包标记
├── models.py                # 9 张调度相关表 CRUD + 建表
├── scheduler.py             # APScheduler Cron 调度引擎
├── workflow_engine.py       # DAG 工作流执行引擎
├── nodes.py                 # 12 种工作流节点处理器
├── worker.py                # Worker Pool 线程池管理
├── routes.py                # ~30 个 API 端点
└── safe_eval.py             # 安全 AST 表达式评估器
```

---

## 三、Agent 体系

### 3.1 Agent 分类

| 类型 | 数量 | 职责 |
|------|------|------|
| Master Agent | 1 | 接收用户指令、任务分解、协调分发、汇总报告 |
| Sub Agent | 12 | 领域专家，并行执行具体子任务 |

### 3.2 13 个默认 Agent

| Agent | 角色 | 领域 | 供应商 | 模型 | 职责描述 |
|-------|------|------|--------|------|---------|
| **Athena** | master | orchestration | OpenAI | gpt-4o | 任务分解、协调、汇总、质量把控 |
| CMS Agent | sub | cms | DashScope | qwen-turbo | 文章写作、内容管理、分类 |
| Finance Agent | sub | finance | DashScope | qwen-turbo | 财务分析、报表、对账 |
| User System Agent | sub | system | DashScope | qwen-turbo | 用户管理、权限、套餐 |
| Health Check Agent | sub | health_check | DashScope | qwen-turbo | 系统健康监控、告警、诊断 |
| Automation Agent | sub | automation | DashScope | qwen-turbo | 自动化流程、任务编排 |
| Analytics Agent | sub | analytics | DashScope | qwen-turbo | 数据分析、趋势、看板 |
| Ticket Agent | sub | support | DashScope | qwen-turbo | 工单、客服、故障排查 |
| Kai Assistant | sub | chatbot | DeepSeek | deepseek-chat | 对话式 AI 助手 |
| Voice Agent | sub | voice | VolcEngine | volc-voice-clone-v2 | 语音克隆、TTS |
| Video Agent | sub | video | VolcEngine | volc-avatar-v3 | 数字人视频生成 |
| Image Agent | sub | image | DashScope | wan2.7-image | 图像生成、编辑 |
| Shop Agent | sub | shop | DashScope | qwen-turbo | 商品、订单、供应链 |
| Health Check Agent | sub | health_check | DashScope | qwen-turbo | 系统健康监控、告警、诊断 |

### 3.3 Agent 配置字段

每个 Agent 在 `agent_matrix` 表中存储如下配置：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | TEXT | Agent 名称 |
| `role_type` | ENUM | `master` / `sub` |
| `domain` | TEXT | 领域标识（cms / finance / system / ...） |
| `managed_modules` | JSON | 管辖的子模块列表 |
| `provider` | TEXT | AI 供应商 ID |
| `model_name` | TEXT | 模型名称 |
| `api_key_ref` | TEXT | 引用 system_config 中的 API Key |
| `base_url` | TEXT | 自定义 API 地址（覆盖默认） |
| `system_prompt` | TEXT | System Prompt（文件路径或内联文本） |
| `capabilities` | JSON | 能力清单 |
| `allowed_tools` | JSON | 允许调用的工具列表 |
| `max_concurrency` | INT | 最大并发数 |
| `priority` | INT | 优先级（1-10） |
| `auto_approve` | BOOL | 是否自动批准 |
| `is_active` | BOOL | 启用/禁用 |
| `tasks_total / tasks_success / tasks_failed` | INT | 任务统计 |
| `last_run_at` | TEXT | 最后执行时间 |

---

## 四、核心流程

### 4.1 指令处理全流程

```
用户输入指令
     │
     ▼
┌──────────────────────────────────┐
│  process_instruction()           │
│  1. 模式选择 (fast/deep/image)   │
│  2. 创建 Master Task (composite) │
│  3. 获取 Master Agent 配置       │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  decompose_task()               │
│  ┌─ 模式 A: AI 分解 (主路径)    │
│  │  Master 调用 LLM，注入       │
│  │  可用 Sub Agent 团队列表     │
│  │  输出 JSON 分解方案          │
│  ├─ 模式 B: 模板分解 (Fallback) │
│  │  关键词匹配（如"文章"→CMS）  │
│  └─────────────────────────────  │
│  返回: [{title, description,     │
│         target_agent_id,         │
│         priority, input_data}]   │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  dispatch_sub_tasks()           │
│  ThreadPoolExecutor (max=5)     │
│  ┌─ 标准 Agent → AgentRunner    │
│  │  1. 构建 Prompt              │
│  │  2. 调用 AIEngine.ask()      │
│  │  3. 自检 self_critique()     │
│  │  4. < 0.7 自动重试 (×3)      │
│  ├─ 图像 Agent → 特殊处理       │
│  │  裁切/缩放/加文字/生成       │
│  └─ 超时熔断: 300s              │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  _build_summary()               │
│  结构化报告: 子任务状态/置信度/  │
│  产出内容/耗时                  │
└──────────────┬───────────────────┘
               │
               ▼
           返回结果
```

### 4.2 自检机制

AgentRunner 在每次执行后调用 `_self_critique()`：

```
1. 检查输出长度是否充足
2. 检查是否包含错误标志（error/失败/抱歉等）
3. 检查是否匹配 expected_output 要求
4. 计算 confidence 分数 (0.0 - 1.0)

if confidence < 0.7:
    retry_count += 1
    if retry_count < max_retries (默认3):
        重新执行 + 注入上次失败原因
    else:
        标记为 failed，汇报失败原因
```

### 4.3 任务 ID 规范

- 格式：`AT-YYYYMMDD-XXXX`（如 `AT-20260510-0001`）
- `master_task_id`：顶层 Master 任务 ID
- `parent_task_id`：父任务 ID，支持树形分解结构

### 4.4 任务状态机

```
pending ──→ running ──→ completed
                │
                ├──→ failed ──→ retrying ──→ running
                │
                ├──→ cancelled
                │
                └──→ needs_review
```

---

## 五、AI 引擎 & 供应商集成

### 5.1 AIEngine 类

位于 `agent_matrix/engine.py`，是所有 AI 调用的统一入口。

**初始化配置解析**：
1. 优先使用 `provider_model_id` → 查询 `provider_models` 表 / `providers` 表
2. 回退到 Agent 自身的旧字段（`provider` + `model_name` + `api_key_ref`）

**API Key 查找优先级**：
1. `provider_model_id` 关联的 `api_key_ref`
2. Agent 的 `api_key_ref` → 从 `system_config` 读取
3. DashScope → `os.environ['DASHSCOPE_API_KEY']`
4. 其他供应商 → `config.get('api_key_enc')` 解密
5. 环境变量 `${PROVIDER}_API_KEY`
6. DB → `system_config` 中 `model_{provider}_api_key`

### 5.2 供应商配置

| 供应商 ID | 默认 Base URL | 默认模型 | 备注 |
|-----------|---------------|----------|------|
| `dashscope` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` | 阿里云通义千问，默认 |
| `openai` | `https://api.openai.com/v1` | `gpt-4o` | OpenAI |
| `deepseek` | `https://api.deepseek.com` | `deepseek-chat` | 深度求索 |
| `openrouter` | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini` | 统一路由 |
| `ollama` | `http://localhost:11434/v1` | `llama3` | 本地推理 |

### 5.3 主要方法

| 方法 | 说明 |
|------|------|
| `chat(messages, temperature, max_tokens) -> str` | 标准 LLM 调用 |
| `ask(user_query, temperature) -> str` | 一问一答 |
| `ask_with_history(history, user_query) -> str` | 多轮对话 |
| `chat_stream(messages, ...) -> Generator` | SSE 流式输出 |
| `ask_stream(user_query) -> Generator` | 流式一问一答 |
| `is_ready() -> bool` | 检查客户端是否就绪 |
| `voice_clone(audio_url, voice_name) -> dict` | 语音克隆 |
| `tts(text, voice_id, output_path) -> dict` | 文本转语音 |
| `avatar_video(text, voice_id, image_url) -> dict` | 数字人视频 |
| `query_media_task(task_id) -> dict` | 查询媒体任务状态 |
| `execute_media_action(action, params) -> dict` | 统一媒体路由 |

---

## 六、数据库设计

### 6.1 Agent Matrix 核心表（6 张）

#### `agent_matrix` — Agent 配置

```sql
CREATE TABLE agent_matrix (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    role_type       TEXT NOT NULL DEFAULT 'sub'
                    CHECK(role_type IN ('master','sub')),
    description     TEXT DEFAULT '',
    domain          TEXT NOT NULL DEFAULT 'general',
    managed_modules TEXT DEFAULT '[]',
    provider        TEXT NOT NULL DEFAULT 'dashscope',
    model_name      TEXT NOT NULL DEFAULT 'qwen-turbo',
    api_key_ref     TEXT DEFAULT 'dashscope_text_key',
    base_url        TEXT DEFAULT '',
    model_provider_id INTEGER DEFAULT NULL,
    provider_model_id INTEGER DEFAULT NULL,
    system_prompt   TEXT DEFAULT '',
    role_prompt     TEXT DEFAULT '',
    task_template   TEXT DEFAULT '',
    capabilities    TEXT DEFAULT '[]',
    allowed_tools   TEXT DEFAULT '[]',
    max_concurrency INTEGER DEFAULT 1,
    priority        INTEGER DEFAULT 5,
    auto_approve    INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    tasks_total     INTEGER DEFAULT 0,
    tasks_success   INTEGER DEFAULT 0,
    tasks_failed    INTEGER DEFAULT 0,
    last_run_at     TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(name, role_type)
);
```

#### `agent_tasks` — 任务调度

| 字段 | 说明 |
|------|------|
| `task_id` | 主键，格式 `AT-YYYYMMDD-XXXX` |
| `parent_task_id` | 父任务 ID（树形分解） |
| `master_task_id` | 顶层 Master 任务 ID |
| `source_agent_id` | 发起 Agent ID |
| `target_agent_id` | 执行 Agent ID |
| `target_module` | 目标模块标识 |
| `status` | pending / running / completed / failed / cancelled / needs_review / retrying |
| `task_type` | execute / review / approve / composite / cron |
| `title / description` | 任务描述 |
| `input_data / output_data` | JSON 输入/输出 |
| `confidence` | 置信度 0.0-1.0 |
| `self_review / cross_review` | JSON 自检/互检结果 |
| `retry_count / max_retries` | 重试计数/上限 |
| `priority` | 优先级 1-10 |
| `scheduled_at / started_at / completed_at` | 时间戳 |
| `duration_ms` | 执行耗时 |

索引：`status`, `source_agent_id`, `target_agent_id`, `master_task_id`, `target_module`

#### `task_logs` — 执行日志

| 字段 | 说明 |
|------|------|
| `log_level` | debug / info / warn / error |
| `log_type` | execution / self_review / cross_review / approval / api_call |
| `message` | 日志内容 |
| `metadata` | JSON 元数据 |

#### `agent_conversations` — 对话记录

| 字段 | 说明 |
|------|------|
| `session_id` | 会话 ID，格式 `SESSION-YYYYMMDD-xxxxxxxx` |
| `session_name` | 会话名称 |
| `role` | user / master / sub / system |
| `content` | 消息内容 |

#### `agent_token_logs` — Token 消耗日志

| 字段 | 说明 |
|------|------|
| `agent_id` | Agent ID |
| `dimension` | text / voice / video / image |
| `prompt_tokens` | 输入 Token 数 |
| `completion_tokens` | 输出 Token 数 |
| `model` | 模型名称 |
| `cost` | 费用估算 |

索引：`agent_id`, `created_at`, `dimension`

#### `agent_token_daily` — Token 每日汇总

| 字段 | 说明 |
|------|------|
| `agent_id` | Agent ID |
| `stat_date` | 统计日期 |
| `prompt_tokens / completion_tokens / total_tokens` | 汇总 |
| `call_count` | 调用次数 |

UNIQUE(`agent_id`, `stat_date`)

### 6.2 Orchestrator 调度表（9 张）

| 表名 | 说明 |
|------|------|
| `system_agents` | 平台内置系统 Agent |
| `cron_jobs` | Cron 任务定义（cron / interval / once） |
| `job_dependencies` | 任务依赖关系（DAG 边） |
| `workflow_definitions` | 工作流 DAG 定义（JSON） |
| `workflow_instances` | 工作流运行实例（状态机） |
| `workflow_node_instances` | 节点运行实例（状态机） |
| `execution_logs` | 执行日志 |
| `alerts` | 告警配置 |
| `scheduler_state` | 调度器节点状态（分布式支持） |

---

## 七、API 参考

### 7.1 Agent 管理（7 端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/agent-matrix/agents` | Agent 列表（?role=&domain=&active_only=） |
| POST | `/admin/agent-matrix/agents` | 创建 Agent（API Key 自动存入 system_config） |
| GET | `/admin/agent-matrix/agents/<id>` | Agent 详情（含 Key 配置状态） |
| PUT | `/admin/agent-matrix/agents/<id>` | 更新 Agent |
| DELETE | `/admin/agent-matrix/agents/<id>` | 删除 Agent（禁止删除 master） |
| POST | `/admin/agent-matrix/agents/<id>/test` | 测试 Agent 连通性 |
| POST | `/admin/agent-matrix/agents/<id>/toggle` | 启用 / 禁用 Agent |

### 7.2 任务管理（6 端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/agent-matrix/tasks` | 任务列表 |
| GET | `/admin/agent-matrix/tasks/<task_id>` | 任务详情（含子任务 + 日志） |
| POST | `/admin/agent-matrix/tasks/<task_id>/cancel` | 取消任务 |
| POST | `/admin/agent-matrix/tasks/<task_id>/retry` | 重试任务 |
| GET | `/admin/agent-matrix/tasks/<task_id>/logs` | 任务日志 |
| GET | `/admin/agent-matrix/tasks/recent` | 最近 20 条任务 |

### 7.3 Master Agent 对话（10 端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/agent-matrix/chat` | 向 Master 发指令（核心入口） |
| POST | `/admin/agent-matrix/chat/tool` | 工具调用模式（意图分析 + 路由） |
| POST | `/admin/agent-matrix/chat/stream` | SSE 流式聊天 |
| GET | `/admin/agent-matrix/chat/history` | 会话历史列表 |
| GET | `/admin/agent-matrix/chat/<session_id>` | 会话详情 |
| POST | `/admin/agent-matrix/chat/<session_id>/clear` | 清除会话 |
| GET | `/admin/agent-matrix/chat/search` | 全文检索会话 |
| POST | `/admin/agent-matrix/chat/batch-delete` | 批量删除会话 |
| GET | `/admin/agent-matrix/chat/knowledge` | 获取聊天知识库 |
| PUT | `/admin/agent-matrix/chat/knowledge` | 更新聊天知识库 |

### 7.4 调度 & 能力（3 端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/agent-matrix/dispatch` | 直接下发任务给指定 Sub Agent |
| GET | `/admin/agent-matrix/agents/<id>/capabilities` | 查询 Agent 能力清单 |
| GET | `/admin/agent-matrix/providers` | 列出可用 AI 供应商 |

### 7.5 Prompt 管理（2 端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/agent-matrix/prompts` | 列出 Prompt 模板（扫描 prompts/ 目录） |
| GET | `/admin/agent-matrix/prompts/load` | 加载指定 Prompt 文件内容 |

### 7.6 统计 & 监控（5 端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/agent-matrix/stats` | 矩阵统计概览 |
| GET | `/admin/agent-matrix/dashboard` | 实时看板数据 |
| GET | `/admin/agent-matrix/health` | 所有 Agent 健康检查 |
| GET | `/admin/agent-matrix/token-stats` | Token 消耗统计（含费用估算） |
| GET | `/admin/agent-matrix/token-logs` | Token 消耗日志列表（分页） |

### 7.7 文件处理（2 端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/agent-matrix/upload` | 上传文件（7 天有效期） |
| GET | `/admin/agent-matrix/download/<filename>` | 下载临时文件（含过期检查） |

### 7.8 图像生成（1 端点）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/admin/agent-matrix/generate-image` | 生成图片并保存到本地 |

### 7.9 Orchestrator 自动化端点（~30 端点）

| 分组 | 数量 | 前缀 |
|------|------|------|
| Cron Job CRUD | 6 | `/admin/automation/cron/*` |
| Workflow 定义 CRUD | 6 | `/admin/automation/workflow/*` |
| Workflow 执行 | 6 | `/admin/automation/workflow/*` |
| 日志 & 监控 | 6 | `/admin/automation/logs/*` |
| 告警 & 系统 | 6 | `/admin/automation/alerts/*` |

### 7.10 用户自有 Agent（10 端点）

位于 `auth-center/routes/agents.py`：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/agent/list` | 当前用户的 Agent 列表 |
| POST | `/agent/create` | 创建 Agent（含套餐限制） |
| GET | `/agent/<id>` | Agent 详情（含 API Key 列表） |
| PUT | `/agent/<id>` | 更新 Agent |
| DELETE | `/agent/<id>` | 删除 Agent（级联删除 Key 和日志） |
| GET | `/agent/<id>/keys` | 列出 API Key |
| POST | `/agent/<id>/keys/create` | 生成新 API Key |
| DELETE | `/agent/<id>/keys/<kid>` | 吊销 API Key |
| POST | `/agent/<id>/keys/<kid>/rotate` | 轮换 API Key |
| GET | `/agent/<id>/stats` | Agent 使用统计 |

---

## 八、Orchestrator 自动化调度

### 8.1 APScheduler Cron 引擎

位于 `orchestrator/scheduler.py`，基于 APScheduler 的定时任务调度。

**任务类型**：

| 类型 | 说明 |
|------|------|
| `cron` | Cron 表达式（如 `0 */6 * * *` 每6小时） |
| `interval` | 间隔执行（如 `interval:3600` 每小时） |
| `once` | 单次定时执行（如 `2026-06-01 00:00:00`） |

**支持配置**：
- 最大运行实例数
- 任务超时熔断
- 重试策略（次数 + 间隔）
- 分布式调度（通过 `scheduler_state` 表）

### 8.2 典型应用场景

| 场景 | Cron 表达式 | 说明 |
|------|------------|------|
| 定时抓取 RSS | `0 */2 * * *` | 每2小时抓取一次热门内容 |
| 内容 AI 加工 | `30 */4 * * *` | 每4小时 AI 处理后入知识库 |
| 数据备份 | `0 3 * * *` | 每天凌晨3点备份数据库 |
| 报表生成 | `0 9 * * 1` | 每周一早上9点生成周报 |
| 健康检查 | `*/5 * * * *` | 每5分钟自动巡检 |

---

## 九、Workflow 工作流引擎

### 9.1 DAG 工作流

位于 `orchestrator/workflow_engine.py`，支持有向无环图（DAG）工作流定义和执行。

**工作流定义**（JSON 格式）：

```json
{
  "name": "RSS 采集 → AI 加工 → CMS 发布",
  "nodes": [
    {"id": "fetch", "type": "rss_fetch", "params": {"source_id": 1}},
    {"id": "process", "type": "ai_process", "params": {"prompt": "..."}},
    {"id": "review", "type": "human_review", "params": {}},
    {"id": "publish", "type": "cms_publish", "params": {}}
  ],
  "edges": [
    {"from": "fetch", "to": "process"},
    {"from": "process", "to": "review"},
    {"from": "review", "to": "publish"}
  ]
}
```

### 9.2 12 种节点处理器

位于 `orchestrator/nodes.py`：

| 节点类型 | 说明 |
|----------|------|
| `rss_fetch` | RSS 采集 |
| `ai_process` | AI 内容加工 |
| `cms_publish` | CMS 发布 |
| `agent_call` | 调用任意 Agent |
| `http_request` | HTTP 请求 |
| `human_review` | 人工审核（阻塞等待） |
| `condition` | 条件分支（IF/ELSE） |
| `delay` | 延迟等待 |
| `code_exec` | 安全代码执行（AST） |
| `notification` | 通知推送 |
| `data_transform` | 数据转换 |
| `sub_workflow` | 嵌套子工作流 |

### 9.3 工作流状态机

```
pending ──→ running ──→ completed
                │
                ├──→ failed
                │
                ├──→ paused
                │
                └──→ cancelled
```

节点级别状态：`pending → running → completed / failed / skipped / waiting_review`

---

## 十、工具调用模式

### 10.1 意图路由

`POST /admin/agent-matrix/chat/tool` 端点支持 8 种意图的自动路由：

| 意图 | 检测关键词 | 处理方式 |
|------|-----------|---------|
| `ppt` | 演示文稿/PPT/幻灯片 | AI 生成大纲 → python-pptx 生成 Dark 科技风 PPT |
| `image` | 图片/生成/画/图 | 调用通义万相 / PIL 本地处理 |
| `voice` | 声音/语音/克隆 | 调用 VolcEngine 语音服务 |
| `video` | 数字人/视频 | 跳转到多媒体 Tab 手动操作 |
| `cms` | 文章/内容/写 | 跳转到文章编辑器 |
| `clean` | 清洗/去重/整理 | 调用 Cleaner Agent |
| `supply_chain` | 供应链/商品/订单 | Orchestrator 分配 |
| `chat` | 普通对话 | Orchestrator 处理 |

### 10.2 Cleaner Agent

位于 `auth-center/routes/cleaner_agent.py`，数据清洗智能体：

- `process_clean_content(raw_content, admin_id) -> dict`
- 使用 OpenAI 兼容接口（默认 DeepSeek）
- 清洗流程：去重 → AI 提取标题/正文/分类/关键词 → 写入 `knowledge_blocks` 表
- 自动注册为矩阵 Sub Agent（`auto_register_sub_agent()`）

---

## 十一、监控 & 可观测性

### 11.1 Token 审计系统

每次 LLM 调用记录 `agent_token_logs`，每日汇总到 `agent_token_daily`：

```
GET /admin/agent-matrix/token-stats
→ 返回: 总Token数 | 按Agent汇总 | 按日期趋势 | 费用估算
```

**费用估算逻辑**（按供应商/模型计价）：
- DashScope qwen-turbo: ¥0.003/1K prompt, ¥0.006/1K completion
- OpenAI gpt-4o: $0.01/1K prompt, $0.03/1K completion
- 其他模型类似处理

### 11.2 健康检查

```
GET /admin/agent-matrix/health
→ 返回: 每个 Agent 的 is_ready 状态 + 最后运行时间 + 成功率
```

### 11.3 统计看板

```
GET /admin/agent-matrix/dashboard
→ 返回: 实时执行数 | 队列深度 | 成功率 | 平均耗时 | Token 消耗
```

---

## 十二、Prompt 系统

### 12.1 Prompt 文件结构

所有 prompt 模板位于 `agent_matrix/prompts/`：

| 文件 | 用途 |
|------|------|
| `master_prompt.md` | Athena 系统提示词 — 任务分解 + 协调 + 报告 |
| `sub_cms_prompt.md` | CMS Agent — 文章创作 |
| `sub_finance_prompt.md` | Finance Agent — 财务分析 |
| `sub_user_prompt.md` | User System Agent — 用户管理 |
| `sub_health_check_prompt.md` | Health Check Agent — 系统健康监控 |
| `sub_automation_prompt.md` | Automation Agent — 流程自动化 |
| `sub_analytics_prompt.md` | Analytics Agent — 数据分析 |
| `sub_ticket_prompt.md` | Ticket Agent — 工单处理 |
| `sub_chatbot_prompt.md` | Kai Assistant — 聊天对话 |
| `sub_voice_prompt.md` | Voice Agent — 语音处理 |
| `sub_video_prompt.md` | Video Agent — 视频生成 |
| `sub_image_prompt.md` | Image Agent — 图像生成 |
| `sub_shop_prompt.md` | Shop Agent — 商城运营 |
| `sub_supply_chain_prompt.md` | [用户模板] 自定义供应链 Agent 参考 |

### 12.2 加载机制

API `GET /admin/agent-matrix/prompts/load` 支持：
- 读取 `prompts/*.md` 文件内容
- 支持按 Agent ID 或文件名加载
- 文件编码 UTF-8

---

## 十三、集成与扩展

### 13.1 当前集成

| 模块 | 集成方式 |
|------|---------|
| CMS | Agent Matrix 调用 CMS Agent → CMS Admin API |
| 内容工厂 | Agent Matrix 调用 → Content Factory API |
| 商城 | Agent Matrix 调用 Shop Agent → Shop Admin API |
| Cleaner Agent | 直接调用 `process_clean_content()` |
| Social Push | Agent 结果 → Social Push API 发布 |
| 云服务开通 | 订单 → Cloud Provisioner |
| Workflow 引擎 | Agent Matrix + Orchestrator 联动 |

### 13.2 扩展指南

**添加新的 Sub Agent**：
1. 在 `agent_matrix/prompts/` 创建 prompt 文件
2. 配置 agent_matrix 表（或通过 API POST）
3. 在 `orchestrator.py` 的 `decompose_task()` 中注册到可用列表

**添加新 AI 供应商**：
1. 在 `engine.py` 的 `PROVIDER_CONFIGS` 中添加配置
2. 在 `routes.py` 的 `PROVIDER_LIST` 中添加前端可选列表

---

## 十四、配置指南

### 14.1 必需配置

| 配置项 | 位置 | 说明 |
|--------|------|------|
| `dashscope_text_key` | `system_config` 表 | 通义千问 API Key |
| `openai_api_key` | `system_config` 表 | OpenAI API Key（可选） |
| `deepseek_api_key` | `system_config` 表 | DeepSeek API Key（可选） |
| `DASHSCOPE_API_KEY` | 环境变量 | 备用 DashScope Key |
| VolcEngine 配置 | `system_config` 表 | 语音/视频 Key |

### 14.2 可选配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `max_concurrency` | 5 | 并行任务数 |
| `task_timeout` | 300 | 单任务超时（秒） |
| `max_retries` | 3 | 自检重试上限 |
| `confidence_threshold` | 0.7 | 自检置信度阈值 |

### 14.3 初始化

系统启动时自动执行：
1. `init_agent_matrix_tables()` — 创建 6 张表
2. `seed_default_agents()` — 插入 13 个默认 Agent
3. 注册 Blueprint 到 Admin 服务

---

## 十五、常见问题

**Q: Master Agent 分解失败怎么办？**
A: 自动 Fallback 到模板分解模式，根据关键词匹配 Sub Agent。如果仍然失败，返回错误信息给用户。

**Q: Agent 返回结果不可信怎么办？**
A: 自检机制检测 confidence < 0.7 自动重试。管理员可通过 `needs_review` 状态手动审核。

**Q: 如何调整 Agent 的 AI 供应商？**
A: 通过 API `PUT /admin/agent-matrix/agents/<id>` 修改 `provider` 和 `model_name` 字段，或通过 Admin UI 操作。

**Q: Token 费用如何控制？**
A: 定期查看 `/admin/agent-matrix/token-stats`，可按 Agent 维度分析消耗。建议高频任务使用低成本模型（qwen-turbo / deepseek-chat）。

**Q: Worker 进程需要单独部署吗？**
A: 不需要。Agent Matrix 运行在 Admin 服务（8084）中，使用线程池执行任务。如需分布式部署，可通过 `scheduler_state` 表扩展。

**Q: 媒体 Agent（语音/视频）为什么需要 VolcEngine？**
A: 语音克隆、数字人视频等能力需要专用的媒体处理引擎，目前通过火山引擎 SDK 集成。纯文本 Agent 不依赖此服务。

---

> **参见**：[ARCHITECTURE.md](./ARCHITECTURE.md) — 原始架构设计 | [ARCHITECTURE_v2.md](./ARCHITECTURE_v2.md) — v2 架构升级方案  
> **主项目 README**：[../README.md](../README.md) — 易站 AI 平台完整文档
