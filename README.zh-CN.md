# VeroRun — Multi-Agent AI 引擎操作系统

[![Version](https://img.shields.io/badge/version-0.56.5-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![Plugins](https://img.shields.io/badge/plugins-30-orange.svg)]()

**VeroRun 是部署在客户自有服务器上的 Multi-Agent AI 引擎操作系统——一套为企业级私有部署设计的通用智能执行引擎。**

引擎底座通过六大内核组件提供 **Agent 协作、知识检索、流程编排、模型接入、资产守护** 五类通用智能执行原语；知识库客服、内容生产、商业经营等任意业务形态，均以插件形式运行于内核之上，作为底座承载的应用实例。同一底座可支撑多种智能前端（WWW 网站、小程序、IM 机器人、内部业务门户、数据看板等）。

---

## 核心特性

- **可编排的多角色 Agent 矩阵**：Athena（主控）+ 8 个子角色，多专精 Agent + 角色分工 + 任务分解编排，扩展 Agent 自动注册。
- **四阶段讨论协议（Agent Discussion v2.0）**：Planner → Reviewer → Revise → Decider，生成与评审分离，方案在错误发生前被拦截。
- **动态提示词系统**：数据库驱动的 `PromptResolver`，四层组装 + 场景差异化 + 多版本管理。
- **知识库与记忆引擎（CogEvolution）**：向量检索（RAG）、分层记忆、Reflexion 反思学习、Prompt Evolution 版本进化，形成"记忆 → 反思 → 优化 → 行为进化"闭环。
- **可视化工作流引擎**：DAG 节点编排、Cron 调度、分级 Worker 池，任意流程的通用执行载体。
- **多供应商 LLM 网关（UnifiedLLM）**：供应商无关（provider-agnostic）的统一 API 接入，7 家原生 + 2 家动态解析，透明模型替换、自动故障转移、模型寻址、密钥管理、预算闸门、4 级配额。
- **VeroGuard 守护层**：健康监控 + 完整性校验 + 加密心跳，双进程互护，客户侧资产守护。
- **插件生态**：30 个内置插件承载任意业务形态，全生命周期管理、插件商店、许可引擎。

内核的设计准则是 **业务语义不侵入内核**：业务规则全部由插件声明，新增业务能力等价于装配一个插件，不触碰内核代码。

---

## 架构

### 引擎底座与应用分层

> **引擎底座定义"如何运转"，应用插件定义"运转什么"。**

```text
┌──────────────────────────────────────────────────────────────┐
│ 应用生态层  插件应用：知识管理 · 内容 · 商业经营 · 通信 · 运维…  │
│            30 个内置插件覆盖多领域，任意业务形态经插件装配落地  │
├──────────────────────────────────────────────────────────────┤
│ 引擎底座    多角色 AI Agent 矩阵 + 四阶段讨论协议              │
│            知识库记忆（向量检索）· 可视化工作流引擎 · PromptResolver │
├──────────────────────────────────────────────────────────────┤
│ 运行时层    多供应商 LLM 网关 UnifiedLLM · 插件管理器 · 主题模板 │
├──────────────────────────────────────────────────────────────┤
│ 守护层      VeroGuard 统一守护进程（健康 / 完整性 / 心跳）       │
└──────────────────────────────────────────────────────────────┘
```

### 服务拓扑

| 端口 | 域名 | systemd 单元 | 应用 | 职责 |
|---|---|---|---|---|
| 8081 | 主域名 | `verorun-main` | `auth_server` | 主站、登录、验证码代理 |
| 8083 | `platform.*` | `verorun-auth` | `main_site`（Platform Console） | 用户控制台、订阅管理 |
| 8084 | `admin.*` | `verorun-admin` | `admin.app` | 管理后台、Agent 矩阵、自动化、CMS |
| 8085 | — | `verorun-health` | `health_service.app` | 内部健康检查端点 |
| 8090 | — | 独立进程 | `captcha-service` | 拼图验证码 + 行为分析 |
| — | — | `verorun-guardian` | `veroguard.guardian` | 统一守护（健康 + 完整性 + 心跳） |

> 注：`auth-center/` 是被各服务 import 的 **共享代码库**（models / services / routes），并非独立运行在 8083 的服务；8083 实际运行 `main_site` 应用。

### 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.11+、Flask、Gunicorn |
| 数据库 | PostgreSQL（生产，含 pgvector）/ SQLite（开发回落） |
| 缓存 | Redis |
| 反向代理 | Nginx + Let's Encrypt |
| 工作流编辑器 | React 18.3.1 + React Flow |
| 可视化 | Chart.js、ECharts、Quill.js |
| 守护编译 | Nuitka（独立二进制） |
| 图像生成 | FLUX.1-pro（SiliconFlow）、通义万相 |

---

## 快速开始

### 一键部署（Ubuntu 22.04 / 24.04）

```bash
curl -fsSL https://raw.githubusercontent.com/fanjumin/verorun-pro/master/deploy/install.sh \
  | sudo bash -s -- install your-domain.com
```

区域选择：

```bash
sudo bash deploy/install.sh install your-domain.com --region=cn       # 中国大陆
sudo bash deploy/install.sh install your-domain.com --region=global    # 国际（默认）
```

安装后执行 `deploy/install.sh seed` 初始化数据、`deploy/install.sh configure-domain` 配置域名，certbot 自动签发 SSL。

### Docker

```bash
docker compose up -d
```

### 本地开发

```bash
pip install -r requirements.txt
cp .env.example .env
python scripts/dev_start.py
```

---

## 引擎底座

### AI 引擎 — 多角色 Agent 矩阵（9 角色）

与单一大模型应用不同，VeroRun 不把复杂任务压给一次对话，而是交给一组有分工、可评审的 Agent 角色：主控分解任务，子角色各司其职，评审质疑方案，决策签署结论。

| 角色 | Slug | 类型 | 模型 | 职责 |
|---|---|---|---|---|
| Athena | `athena` | master | — | 任务分解、编排、上报、系统管理 |
| Content | `content` | sub | siliconflow/DeepSeek-V3 | 内容创作、SEO、社媒、翻译 |
| Builder | `builder` | sub | siliconflow/DeepSeek-V3 | 建站、主题、域名、页面设计 |
| Finance | `finance` | sub | gemini/gemini-2.5-flash | 套餐、订阅、计费、发票、奖励 |
| Ops | `ops` | sub | deepseek/deepseek-v4-flash | 部署、健康检查、告警、云资源配置 |
| Service | `service` | sub | moonshot/moonshot-v1-32k | 客服、FAQ、工单、通知、IM |
| Vision | `vision` | sub | zhipu/glm-4v-plus | 图像分析、OCR、图表解读 |
| Creative | `creative` | sub | siliconflow/FLUX.1-pro | 文生图、创意视觉设计 |
| Business | `business` | sub | deepseek/deepseek-v4-flash | 商业分析、规划、供应链 |

**扩展 Agent**（经 `sub_*_prompt.md` 自动注册）：Supply Chain、Chatbot、Automation、Health Check、User、CMS、Cleaner。

**执行机制**：子任务经 ThreadPoolExecutor（≤5 并发）并行分发，单任务 300s 超时；Agent 自评（规则初判 + LLM 结构化复核），置信度阈值 0.7，低于阈值重试（默认 2 次）；LLM 响应缓存（temperature=0 时启用，TTL 3600s）。

### 四阶段讨论协议（Agent Discussion v2.0）

协作协议由 Planner、Reviewer、Decider 三角色构成，实际以 4 轮编排执行：

1. **Planner** 生成初版执行计划（plan_v1）。
2. **Reviewer** 评审，输出 issues 与 revised_steps。
3. **Planner** 依据评审修订为 plan_v2。
4. **Decider** 最终 approve / reject 并给出理由。

生成与评审分离，把工程组织里"方案评审 + 签署"的纪律移植进 LLM 工作流，以结构换取质量与可追溯。

### 动态提示词系统

系统已从静态 `.md` 文本提示词升级为 **数据库驱动、标签匹配、链式组装的动态提示词系统**。运行时由 `PromptResolver` 按任务上下文实时组装 System Prompt，`agent_matrix/prompts/*.md` 仅作为初始化种子（由 `seed_prompts.py` 迁移到 `agent_prompts` 表）。

**四层组装**：

1. **角色基础**：按 `agent_prompt_bindings` 的 default 绑定取角色基础 Prompt。
2. **全局安全规则**：`prompt_type='rule'` 且 `domain='general'` 的安全规则。
3. **场景模版**：`task_triggers` 精确匹配 `task_type` 的场景 Prompt。
4. **模式增强**：按 `mode` 标签 / mode 绑定匹配的工具或场景 Prompt。

**数据模型**：`agent_prompts`（version、is_active、priority、tags、task_triggers）+ `agent_prompt_bindings`；后台 `prompts_db.html` 提供可视化管理，同一 slug 可维护多版本，支持切换与回滚。

**开关与降级**：由 `system_config.prompt_resolver_enabled` 控制，仅在键存在且为真值时启用；键缺失或读取异常时安全回退。降级三层：开关关闭 → 回退读取 `agent_matrix.system_prompt`（文件路径或直接文本，含路径遍历防护）；任何装配异常 → 同样回退 legacy；四层检索无匹配 → 回退原 `system_prompt` 逻辑。遵循"可用性优先"——故障的默认方向是可用但降级。

**与认知进化联动**：动态提示词经内核 `before_prompt_resolve` 过滤器链注入记忆，并支撑 Prompt Evolution 的按版本聚合指标与一键应用新版本。

### 知识库与记忆引擎（CogEvolution）

自 v0.56.4 起，`memory_engine` 升级为认知进化引擎，形成"记忆 → 反思 → 优化 → 行为进化"闭环：

- **向量检索（RAG）**：从文档知识库中检索上下文，AI 问答带来源引用。
- **Reflexion 反思**：任务失败或置信度过低时触发，抽取失败上下文 → 根因分析 → 生成结构化反思 → 写入长期记忆，后续相似任务自动检索，避免重复犯错。
- **Prompt Evolution**：按 Prompt 版本聚合执行指标，统计显著时生成优化建议，管理员一键应用新版本。**注意：默认关闭**（`prompt_evolution_enabled: false`），需显式启用。
- **演化环可视化**：纯 SVG 交互组件，环形拓扑呈现决策路径、反思触发点与 Prompt 版本切换，支持重放与下钻。
- **分层记忆**：工作记忆（进程内）+ 长期向量记忆（pgvector）；支持 user / global / agent 三作用域；隐私优先（用户级 opt-in、PII 自动过滤、独立 schema 隔离）；pgvector 不可用时降级为关键词检索。

### 项目工作区（知识检索落地）

引擎的"知识检索"原语以 `project_workspace` 插件落地为项目级知识库：

- **Schema 隔离**：每项目独立 PostgreSQL schema，查询强制 `WHERE project_id=?`。
- **文档 RAG**：支持 PDF / DOCX / TXT / MD / PPTX / XLSX / CSV 上传，异步流水线（提取 → 切块 → 嵌入 → 存储）。
- **语义检索**：pgvector + 关键词兜底；AI 问答带来源引用与反馈评分。
- **工作区助手**：文档摘要、比对、溯源问答、内容分析。
- **RBAC**：Viewer（检索 / 问答）/ Editor（上传 / 编辑）/ Owner（管理项目与成员）。

### 可视化工作流引擎

任何可由 Agent 协作与流程编排驱动的任务，都可在可视化 DAG 上编排：

- **DAG 编排**：注册 12 种节点类型：`ai_agent`、`data_collect`、`ai_process`、`condition`、`approval`、`publish`、`notify`、`wait`、`sub_workflow`、`market_check`、`http_request`、`script`。
- **实现完整性警示**：其中 `approval`、`sub_workflow`、`script` 目前仅占位处理器，无真实逻辑，使用前需确认。
- **Cron 调度**：基于 APScheduler，支持 Cron / Interval / Date 触发、暂停 / 恢复、优先级（critical / high / normal / low）、指数退避重试、自然语言 cron 解析。
- **分级 Worker 池**：`dedicated_pool`（4 线程）+ `shared_pool`（8 线程）；优先级 ≤ HIGH 进 dedicated，否则进 shared。

### 多供应商 LLM 网关（UnifiedLLM）

`UnifiedLLM` 是全部 LLM 交互的统一入口：

| 能力 | 说明 |
|---|---|
| Provider 接入 | 原生 7 家：DashScope / OpenAI / DeepSeek / OpenRouter / SiliconFlow / Gemini / Grok；GLM、Moonshot 经 `provider_models` 表动态寻址 |
| 双解析方式 | 按 `provider_model_id`（推荐）或旧式 `provider + model` |
| 客户端缓存 | 5 分钟 TTL，线程安全 |
| 密钥解析优先级 | `provider_api_keys` 表（加密）→ 环境变量 → `system_config` 表 |
| 流式 | `chat_stream()` 自动统计 token 用量 |
| 工具调用 | `chat_with_tools()` 支持函数调用型 Agent |
| 预算门 | 日 token 上限（默认 200 万）+ 每分钟限速（默认 30 次 / 60s），fail-open |
| 4 级配额 | 优先级 User > Model > Module > Global |

**可编排性**：UnifiedLLM 对上层屏蔽供应商差异——应用统一以同一 API 形状对话，网关在背后完成接口翻译（interface translation）、模型路由与自动故障转移。模型可按能力与成本动态寻址，实现透明替换与自动降级，避免供应商锁定（vendor lock-in）；接入新供应商或切换模型无需改造业务代码。

---

### VeroGuard 守护层

将健康监控、代码完整性校验、加密心跳合并为单进程，7 个核心模块（health / integrity / fingerprint / runtime / communicator / executor / self_protect）：

| 通道 | 间隔 | 机制 |
|---|---|---|
| 健康看门狗 | 30s | 服务健康检查、分级恢复（重启 → 回滚）、webhook 告警 |
| 完整性校验 | 300s | 对加密 manifest（AES-GCM）逐文件 SHA256 比对 |
| 心跳上报 | 300s | AES-256-GCM + HMAC-SHA256 签名 + TLS1.3，5 分钟防重放窗口 |

- **自我保护**：双进程（`guardian` 监控业务服务，`self_protect` 监控 guardian），pipe / pidfile 心跳，父进程死亡自动重启。
- **远程命令**（6 个）：`warn`、`lock_ai`、`lock_full`、`shutdown`、`self_destruct`、`update_config`。

---

## 插件生态（"运转什么"）

全生命周期管理（6 状态：`UNKNOWN → INSTALLED → ENABLED → ACTIVE → DISABLED → UNINSTALLED`），含错误状态 `ERROR`。插件按领域覆盖六大方向：

| 领域 | 插件 |
|---|---|
| 商业经营 | `shop`、`payment`、`logistics`、`order_notify`、`reviews`、`wishlist`、`ali_api`、`subscription` |
| 内容传播 | `content_factory`、`site_builder`、`mini_app_builder`、`ads`、`coupons`、`social_push` |
| 知识管理 | `memory_engine`、`chatbot`、`project_workspace` |
| 通信协作 | `im_gateway`、`email`、`sms`、`oauth_config` |
| 运维安全 | `health_check`、`vault`、`verification`、`captcha_embedded`、`enterprise_verify` |
| 数据工具 | `currency_converter`、`site_domains`、`visitor_profile`、`analytics` |

**插件管理器机制**：自动扫描 `plugins/` 解析 `plugin.json`；依赖解析用 Kahn 拓扑排序 + 环检测；事件总线 31 个系统事件（线程池异步分发）；WordPress 风格 Action / Filter 钩子（带优先级）；配置 JSON Schema Draft-07 校验（含类型强制回落）；每插件独立日志（轮转 5MB×3）。

**插件商店**：浏览 / 搜索（远程 API + 本地缓存）、一键安装（SHA256 完整性 + Zip Slip 防护）、支付宝扫码支付、订阅（月 / 年）与优惠券。许可系统：在线校验（HMAC 签名请求）+ 离线 token（**HMAC-SHA256**，72h 宽限 + 7 天有效期，Site ID 绑定）+ 免费插件跳过校验。

---

## 内容生成

内容生成是引擎承载的通用能力之一，覆盖文章、图片、营销素材等多元内容形态的批量生产与分发。基于同一引擎，内容还可直接落地为网站与小程序等前端载体：

- **内容生产**（`content_factory`）：文章、图片、营销素材的批量生成与分发。
- **AI 建站**（`site_builder`）：生成网站、主题与页面，将内容以站点形态呈现。
- **小程序**（`mini_app_builder`）：将内容能力延伸至小程序前端。

内容生成与知识检索、流程编排、模型接入、资产守护等原语相互独立，均可由业务插件按需组合，构成完整应用。

---

## 商业模型与区域路由

**三阶段漏斗**：开源核心免费获客（`verorun-base` 公共仓库）→ 插件购买、订阅与商业授权持续变现 → VeroGuard 在客户侧保护代码资产与许可权益。**数据飞轮愿景**：以领域知识资产为核心，知识库经业务使用持续自进化，支撑领域模型微调与智能设备训练。

**区域路由**：`VERORUN_REGION=cn` → `api.verorun.cn`；`=global` → `api.verorun.com`。所有远程服务（许可 / 心跳 / 守护）按区域动态解析，支持单 URL 环境变量覆盖。

---

## SDK

| 包 | 平台 | 说明 |
|---|---|---|
| `@verorun/sdk-common` | 跨平台 | Auth、Chat、RAG |
| `@verorun/sdk-wechat` | 微信 | 微信小程序封装 |
| `@verorun/sdk-douyin` | 抖音 | 抖音 / 头条小程序封装 |
| `@verorun/sdk-telegram` | Telegram | Bot API + WebApp |
| `@verorun/sdk-line` | LINE | LIFF + Messaging API |

---

## 目录结构

```text
verorun-pro/
├── admin/                  # 管理后台（8084）
├── auth-center/            # 共享鉴权/模型/服务/路由（非独立服务）
├── main_site/              # 主站后端（8081）
├── agent_matrix/           # AI 引擎：多 Agent 编排
│   ├── roles/              # 9 角色 YAML 定义
│   ├── prompts/            # 动态提示词种子（15 个 .md，运行时从 agent_prompts 表加载）
│   ├── prompt_resolver.py  # 动态提示词调度引擎
│   ├── engine.py           # UnifiedLLM 网关 + 预算 + 配额
│   ├── orchestrator.py     # 任务分解、并行分发
│   └── agent_runner.py     # 自评执行
├── orchestrator/           # 可视化工作流引擎（DAG）
├── plugins/                # 30 内置插件（业务形态装配）
├── plugin_manager/         # 插件生命周期/商店/许可/区域路由
├── veroguard/              # VeroGuard 守护层（7 模块）
├── providers/              # 可插拔 Provider 抽象
├── sdks/                   # JavaScript SDK（5 包）
├── captcha-service/        # 独立拼图验证码服务（8090）
├── health_service/         # 健康检查服务（8085）
├── i18n/                   # 国际化（en, zh-CN）
├── deploy/                 # 部署脚本、Nginx 配置
├── themes/                 # 主题系统
├── tests/                  # 测试套件
├── GUIDE.md / CHANGELOG.md / VERSION
├── Dockerfile / docker-compose.yml
└── LICENSE
```

> 注：`site_builder/` 等业务目录是内容生成能力的具体落地，属于引擎承载的应用层，而非引擎本身。

---

## 文档

- `GUIDE.md` — 安装与使用指南
- `CHANGELOG.md` — 版本变更日志
- `agent_matrix/ARCHITECTURE.md` — Agent 矩阵设计
- `sdks/README.md` — SDK 使用说明
- `deploy/README.md` — 部署说明
- `plugins/memory_engine/README.md` — 认知进化引擎说明

---

## 已知生产约束

- Admin 服务 Gunicorn worker 限制为 2，避免低配服务器 OOM。
- SQLite 模式禁用 `--preload`，避免跨进程连接冲突。
- systemd `TimeoutStartSec` 需大于 `health_check.sh` 的 `MAX_WAIT=180`。
- 插件连接包装类必须实现 commit / rollback / close，避免连接池 idle in transaction。
- 部署脚本必须排除 `data/`，防止覆盖生产数据库。

---

## 许可证

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Copyright (c) 2026 Fan Jumin. 详见 [LICENSE](LICENSE)。