# 自动化调度与工作流引擎 — Orchestrator / Workflow Engine

> 为「易站智能建站系统」（easykai.cn）提供高可靠**定时调度**（Cron Scheduler）+ **DAG 工作流编排**（Workflow Engine）能力。

---

## 一、系统概述（Overview）

Orchestrator 由**两个子系统**组成：

| 子系统 | 核心 | 用途 |
|---|---|---|
| Cron Scheduler | APScheduler `BackgroundScheduler` | 定时/周期/一次性任务调度 |
| DAG Workflow Engine | 自研轻量级 DAG 执行器 | 可视化的多步骤工作流编排 |

两者协同工作：Cron Scheduler 到期后，可通过 Worker Pool 触发 Workflow Engine 运行指定的工作流定义，形成完整的**自动化闭环**。

### 源文件索引

| 文件 | 职责 |
|---|---|
| `orchestrator/__init__.py` | 包声明 |
| `orchestrator/models.py` | 数据库模型 + CRUD 操作 |
| `orchestrator/scheduler.py` | APScheduler 调度器核心 |
| `orchestrator/workflow_engine.py` | DAG 工作流执行引擎 |
| `orchestrator/nodes.py` | 工作流节点类型处理器 |
| `orchestrator/worker.py` | Worker Pool 多级线程池 |
| `orchestrator/routes.py` | Flask Blueprint — REST API 路由 |
| `orchestrator/safe_eval.py` | 沙箱安全表达式评估器 |

---

## 二、数据库表结构（Database Tables）

所有表位于 `data/easykai.db`（SQLite），通过 `init_orchestrator_tables()` 幂等初始化。

### 2.1 `cron_jobs` — 定时任务定义

支持三种调度方式：`cron`（Cron 表达式）、`interval`（固定间隔）、`once`（一次性）。每条记录可指定 target_type（workflow / api / script / agent_task）和关联的 Agent（system / user）。

### 2.2 `workflow_definitions` — 工作流定义

核心字段 `definition` 存储 DAG 的 JSON 结构：

```json
{
  "nodes": [
    { "id": "node_1", "type": "data_collect", "name": "采集36氪",
      "config": { "source_ids": [1, 2], "max_per_source": 10 },
      "position": { "x": 100, "y": 200 } }
  ],
  "edges": [
    { "from": "node_1", "to": "node_2", "condition": "success" }
  ]
}
```

### 2.3 `workflow_instances` — 工作流运行实例

状态机：`pending → running → completed / failed / paused / timeout / cancelled`

### 2.4 `workflow_node_instances` — 节点运行实例

状态机：`pending → running → completed / failed / skipped / waiting_approval`

### 2.5 `execution_logs` — 执行日志

统一日志存储（source_type: cron / workflow / node / system），支持按级别（debug / info / warn / error / fatal）查询。

### 2.6 `alerts` — 告警配置

支持 job_failed / workflow_failed / timeout / node_failed / custom 规则，通过 email / webhook / sms / notification 渠道推送。

### 2.7 `system_agents` — 系统 Agent 配置

平台内置 AI Agent 配置表，用于执行内容工厂、市场监控等自动化任务。

### 2.8 `job_dependencies` — 任务依赖关系

Cron 任务间的 DAG 依赖（success / failure / any / completed），用于构建复杂定时链路。

---

## 三、Cron 调度子系统（Cron Scheduler）

### 3.1 调度方式（Scheduling Modes）

| 类型 | 配置方式 | 示例 |
|---|---|---|
| Cron 表达式 | `cron_expr` | `0 30 9 * * 1-5` |
| 自然语言 | `natural_expr` | `每个交易日 9:30` |
| 固定间隔 | `interval_seconds` | `3600`（每小时） |
| 一次性 | `start_at` | `2026-07-01 08:00:00` |

### 3.2 自然语言解析（Natural Language Parser）

`scheduler.py` 中的 `parse_natural_cron()` 支持中文短语到标准 Cron 的转换，内置规则包括：

- `每个交易日` → `0 30 9 ? * MON-FRI`
- `每小时` / `每10分钟` / `每天` / `每周一`
- 模式匹配：`每个交易日 HH:MM`、`每 N 分钟`、`每天 HH:MM`、`周X HH:MM`

### 3.3 执行特性

- **优先级调度**：critical / high / normal / low 四级
- **重试机制**：指数退避（`retry_delay × backoff^attempt`）
- **超时控制**：`timeout_seconds` 后自动终止
- **依赖触发**：任务完成后自动触发下游依赖任务
- **日历支持**：工作日历 / 交易日过滤（`calendar` 字段）
- **心跳检测**：每 30 秒写 `scheduler_state` 表，支持分布式 Leader 漂移

---

## 四、DAG 工作流引擎（DAG Workflow Engine）

### 4.1 节点类型（Node Types）

| 节点类型 | 标识 | 说明 | 处理器位置 |
|---|---|---|---|
| Trigger | — | 起始触发节点（隐式，无专门类型） | — |
| AI Agent | `ai_agent` | 调用 智能体（DashScope LLM） | `nodes.py` |
| Data Collect | `data_collect` | 数据采集（RSS/API → 内容工厂） | `nodes.py` |
| AI Process | `ai_process` | AI 加工内容（生成摘要/改写） | `nodes.py` |
| Condition | `condition` | 条件分支判断（`safe_eval` 表达式） | `nodes.py` |
| Approval | `approval` | 人工审批节点 | `engine.py` 内置 |
| Publish | `publish` | 多平台发布（CMS / Skill / Social） | `nodes.py` |
| Notify | `notify` | 通知（站内 / Webhook / 邮件） | `nodes.py` |
| Wait | `wait` | 延时等待（秒级） | `engine.py` 内置 |
| HTTP Request | `http_request` | HTTP API 调用 | `engine.py` 内置 |
| Script | `script` | 执行自定义 Python 脚本 | `engine.py` 内置 |
| Sub Workflow | `sub_workflow` | 嵌套子工作流 | `engine.py` 内置 |
| Market Check | `market_check` | 市场数据检查（行情 API） | `nodes.py` |

### 4.2 执行引擎（WorkflowEngine）

核心执行流程：

1. `run_workflow()` — 创建实例 → 解析 DAG → 寻找起始节点（入度为 0）
2. 异步线程 `_execute_workflow_async()` — BFS 遍历 DAG
3. `_execute_node()` — 分发到注册的处理器或内置逻辑
4. 边条件检查 — `success` / `failure` / `any` / `completed` / 自定义表达式
5. 上下文传递 — 节点输出自动写入 `context_data`，下游节点可引用

### 4.3 DAG 示例

```json
{
  "nodes": [
    { "id": "collect", "type": "data_collect", "name": "采集36氪",
      "config": { "source_ids": [1], "max_per_source": 5 } },
    { "id": "process", "type": "ai_process", "name": "AI 摘要",
      "config": { "instruction": "生成中文摘要", "fields": ["title", "summary"] } },
    { "id": "check",    "type": "condition", "name": "质量检查",
      "config": { "expression": "node_process_output.success == true" } },
    { "id": "publish",  "type": "publish", "name": "发布到 CMS",
      "config": { "platforms": ["cms"] } },
    { "id": "notify",   "type": "notify", "name": "通知管理员",
      "config": { "channels": ["notification"], "title": "内容已发布" } }
  ],
  "edges": [
    { "from": "collect", "to": "process", "condition": "success" },
    { "from": "process", "to": "check",   "condition": "success" },
    { "from": "check",   "to": "publish", "condition": "success" },
    { "from": "check",   "to": "notify",  "condition": "failure" }
  ]
}
```

### 4.4 Worker Pool（worker.py）

两级线程池隔离：

| 池 | Worker 数 | 服务对象 |
|---|---|---|
| `dedicated_pool` | 4 | critical / high 优先级任务 |
| `shared_pool` | 8 | normal / low 优先级任务 |

`submit()` 方法统一入口，自动按优先级分发。

---

## 五、安全表达式评估器（Safe Eval）

`safe_eval.py` 基于 Python AST 实现沙箱化表达式求值，用于 Condition 节点和 Transform 场景。

### 允许的操作

- 比较运算：`<`, `<=`, `>`, `>=`, `==`, `!=`, `in`, `not in`, `is`, `is not`
- 逻辑运算：`and`, `or`, `not`
- 算术运算：`+`, `-`, `*`, `/`, `%`, `//`, `**`
- 内置常量：`True`, `False`, `None`

### 禁止的操作（安全防护）

| 操作 | 异常原因 |
|---|---|
| `ast.Call` — 函数调用 | 防止 `eval()` / `exec()` |
| `ast.Attribute` — 属性访问 | 防止 `__class__.__base__` |
| `ast.Subscript` — 下标访问 | 防止索引越界攻击 |
| `ast.Lambda` | 禁止匿名函数 |
| `ast.Import` / `ast.ImportFrom` | 禁止导入 |
| 推导式（DictComp / SetComp / ListComp / GeneratorExp） | 防止内存耗尽 |

同时维护 `forbidden_names` 黑名单（`__class__`、`__builtins__`、`eval`、`exec` 等）。执行时注入 `{"__builtins__": {}}` 空作用域。

---

## 六、REST API 端点（API Endpoints）

所有端点注册于 Flask Blueprint，前缀 `/admin/automation/`。

### 6.1 仪表盘

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/stats` | 系统统计（任务/工作流/运行中实例/今日完成数） |

### 6.2 Cron 任务管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/jobs` | 列表（分页、活跃筛选、优先级筛选） |
| POST | `/jobs` | 创建 |
| GET | `/jobs/<id>` | 详情 |
| PUT | `/jobs/<id>` | 更新（自动重新调度） |
| DELETE | `/jobs/<id>` | 删除（级联依赖） |
| POST | `/jobs/<id>/toggle` | 暂停/恢复 |
| POST | `/jobs/<id>/run` | 立即执行一次 |

### 6.3 工作流定义管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/workflows` | 列表 |
| POST | `/workflows` | 创建 |
| GET | `/workflows/<id>` | 详情（definition JSON 自动解析） |
| PUT | `/workflows/<id>` | 更新（版本自增） |
| DELETE | `/workflows/<id>` | 删除（级联实例和节点） |
| POST | `/workflows/<id>/run` | 手动触发执行 |

### 6.4 工作流实例控制

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/instances` | 实例列表（按工作流/状态筛选） |
| GET | `/instances/<id>` | 实例详情（含节点实例列表） |
| POST | `/instances/<id>/pause` | 暂停 |
| POST | `/instances/<id>/resume` | 恢复 |
| POST | `/instances/<id>/cancel` | 取消 |
| POST | `/instances/<id>/nodes/<nid>/approve` | 审批节点（通过/驳回） |

### 6.5 日志

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/logs` | 查询执行日志（分级、分源） |

### 6.6 系统 Agent

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/system-agents` | 列表 |
| PUT | `/system-agents/<id>` | 更新配置 |

### 6.7 调度器控制

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/scheduler/status` | 调度器运行状态 |
| POST | `/scheduler/pause` | 暂停调度器 |
| POST | `/scheduler/resume` | 恢复调度器 |

### 6.8 健康检查

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查（免认证） |

---

## 七、与 Agent Matrix 的集成（Integration）

Orchestrator 通过两种方式与易站智能的 Agent 矩阵交互：

| 方式 | 说明 |
|---|---|
| **Cron → Agent** | 定时任务可指定 `agent_type=system` 或 `agent_type=user`，调度到期后调用对应 Agent 执行任务 |
| **Workflow → AI Agent 节点** | 工作流中放置 `ai_agent` 节点，传递 prompt 给 DashScope 大模型，结果写回 workflow context |
| **Agent 能力映射** | `system_agents` 表的 `capabilities` 字段（JSON 数组）声明 Agent 能力，工作流据此路由 |
| **Agent 任务分发** | `agent_task` 类型的 Cron 任务通过 `WorkerPool._execute_agent_job()` 分发 |

---

## 八、初始化与启动（Initialization）

```python
# 由 admin/app.py 调用
from orchestrator.routes import init_automation

scheduler, worker_pool = init_automation(app)
# 自动完成：建表 → 建 Worker Pool → 建调度器 → 注册回调 → 启动调度器 → 注册蓝图
```

启动流程：
1. `init_orchestrator_tables()` — 幂等建表
2. `WorkerPool()` — 创建两级线程池，注册节点处理器
3. `SchedulerEngine()` — 创建 APScheduler，注册回调
4. `worker_pool.register_scheduler_callbacks(scheduler)` — 打通调度器 → Worker 链路
5. `scheduler.start()` — 启动心跳 + 从 DB 同步所有活跃任务
6. `app.register_blueprint(automation_bp)` — 注册 REST 路由
