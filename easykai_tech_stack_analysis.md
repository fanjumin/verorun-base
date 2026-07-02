# easykai.cn 技术栈深度分析报告

## "数据清洗 → 口令控制台(AI对话) → RAG知识库 → 聊天机器人/抖音小程序"

> 分析日期: 2026-06-11
> 项目路径: /home/***REMOVED***/projects/easykai.cn

---

## 一、整体架构概览

easykai.cn（易站智能）是一个多服务微架构（非微服务）系统，由5个主要子站点组成：

| 站点 | 域名 | 端口 | 核心功能 |
|------|------|------|---------|
| 管理后台 | agent.easykai.cn | 8084 | 全站管理、智能体矩阵、数据清洗、CMS |
| 用户面板 | platform.easykai.cn | 8083 | 用户控制台、AI客服、RAG检索 |
| 社区 | community.easykai.cn | 8082 | 纯AI Agent驱动的知识社区 + 聊天机器人 |
| TradeMind | tm.easykai.cn | 8081 | A股智能分析系统 |
| 官网门户 | (8083) | 8083 | CMS动态页面、产品展示 |

**核心技术栈**：Python 3.12 + Flask（多服务独立进程）、SQLite (WAL模式)、Vanilla JS SPA + SSE流式

---

## 二、模块1：数据清洗 (Cleaner Agent)

### 2.1 文件位置
- **主文件**: `auth-center/routes/cleaner_agent.py` (296行)
- **注册**: 在 `admin/app.py` 中注册为蓝图 `cleaner_bp`，URL前缀 `/shop/cleaner`
- **Agent Matrix 注册**: 启动时自动注册为 `agent_matrix` 的子Agent (`domain='cleaner'`)

### 2.2 输入与触发方式
- **管理员手动触发**: 通过HTTP API POST提交原始内容
  - `POST /shop/cleaner/submit` — 单条提交
- **通过Agent Matrix触发**: 管理员在AI对话中输入清洗指令
  - AI对话（`/admin/agent-matrix/chat/tool`）识别"clean"意图后，直接调用 `process_clean_content()`
- **批量处理**: 
  - `POST /shop/cleaner/run-all` — 批量清洗所有待处理项
  - `POST /shop/cleaner/run/<qid>` — 单条重跑

### 2.3 数据源
原始内容由**管理员直接输入**（粘贴文本、文档片段等），**不是自动采集**。
数据源可以是：行业文章、白皮书、产品说明书、FAQ文本等任意原始文本。

### 2.4 清洗流程

```
管理员提交原始文本
       ↓
写入 knowledge_queue 表（状态: pending）
       ↓
调用 LLM (默认 deepseek-chat / deepseek)
  - System Prompt: 要求输出JSON {"title","content","category","keywords","is_duplicate"}
  - Temperature: 0.3 (低随机性，保证结构化)
  - 去重: 用已有 knowledge_blocks 的 title 做字符串匹配去重
       ↓
清洗结果写入 knowledge_blocks 表
  - kb_id 格式: kb_cleaner_{qid}_{title前10个字符}
  - 分类(category): company/product/price/tech/service/faq/industry
  - 优先级(priority): 固定为5
       ↓
knowledge_queue 状态更新为 'done' 或 'failed'
```

### 2.5 数据流向
```
knowledge_queue (中间表) 
    ↓ (清洗后)
knowledge_blocks (核心知识库)
    ↓
平台API /rag/search 消费 (混合检索)
    ↓
社区聊天机器人 FAQ系统间接消费
    ↓
抖音小程序AI客服 API /chat/request 消费
```

### 2.6 关键设计评价
| 维度 | 评价 |
|------|------|
| **去重机制** | 仅靠标题字符串完全匹配，较为简陋。高相似度但不同标题的内容可能重复入库 |
| **LLM配置** | 通过 `system_config` 表配置，可换供应商/模型，灵活 |
| **批量能力** | 支持 `run-all` 串行批量处理，但大数据量下性能有限 |
| **无向量嵌入** | 清洗结果只存文本，不做embedding，后续检索依赖关键词匹配 |
| **无版本管理** | 知识块没有版本号，更新是覆盖式的 |

---

## 三、模块2：口令控制台（AI 对话 / Athena）

### 3.1 文件位置
- **前端**: `admin/templates/admin.html`
  - `l_ai_chat()` (行3087) — 独立全页面AI对话
  - `cmsTabChat()` (行4705) — CMS内的AI对话标签
  - `aiSend()` (行3305) — 消息发送函数
- **后端(核心)**: `agent_matrix/routes.py`
  - `chat_with_master()` (行311) — `/agent-matrix/chat` POST
  - `chat_tool()` (行370) — `/agent-matrix/chat/tool` POST (工具模式)
- **编排核心**: `agent_matrix/orchestrator.py` — `AgentOrchestrator`
- **AI引擎**: `agent_matrix/engine.py` — `AIEngine`

### 3.2 功能说明
管理员后台的"AI对话"页面，本质上是一个**与Master Agent（Athena）的对话界面**。

工作模式：

| 模式 | 按钮 | 说明 |
|------|------|------|
| ⚡ 快速 | aiSetMode('fast') | 默认模式，直接对话+任务分解 |
| 🧠 深度思考 | aiSetMode('deep') | 注入"深入全面细致分析"指令 |
| 🎨 图像处理 | aiSetMode('image') | 优先委派给Image Agent |
| 🔧 工具调用 | aiSetMode('tool') | `/chat/tool` 端点，分析意图后调用具体功能 |

### 3.3 与大模型的交互方式

```
用户输入消息
  ↓
aiSend() 前端函数
  - 构造 body: {message, mode, session_id}
  - aiMode='tool' → 发到 /agent-matrix/chat/tool
  - 其他模式 → 发到 /agent-matrix/chat
  ↓
agent_matrix/routes.py
  - chat_with_master() 或 chat_tool()
  ↓
AgentOrchestrator.process_instruction()
  1. 获取 Master Agent (Athena) 配置
  2. 调用 LLM (AIEngine) 进行任务分解
  3. 并行分发子任务给 Sub Agents
  4. 收集结果
  5. 生成汇总报告
  ↓
返回 {summary, decomposition, sub_task_results, actions}
```

**使用的模型**: 从 `agent_matrix` 表的 Master Agent 记录中读取 `provider/model_name`。默认使用 `deepseek/deepseek-chat`。

### 3.4 与外部模块的交互

```
Athena (Master Agent)
  ├── CMS Agent → 写文章/内容管理 (通过 Flask API 调用)
  ├── Finance Agent → 订单/财务 (通过 Flask API 调用)
  ├── User System Agent → 用户管理
  ├── Community Agent → 社区管理
  ├── Automation Agent → 工作流/Cron
  ├── Analytics Agent → 统计分析
  ├── Ticket Agent → 工单系统
  ├── Image Agent → 图像生成/处理
  ├── Cleaner Agent → 数据清洗（通过 process_clean_content 函数直接调用）
  └── RAG知识库: 不直接消费 knowledge_blocks，需通过子Agent或工具调用桥接
```

**关键发现**: Master Agent（Athena）的 system prompt 中**没有注入 knowledge_blocks 的内容**。Athena 不直接知道知识库内容。知识库数据由平台API（/api/v1）和社区聊天机器人消费。

### 3.5 功能边界
- ✅ 与AI大模型对话（文本对话、任务分解、子Agent编排）
- ✅ PPT生成（python-pptx库）
- ✅ 图像生成/处理（Wan2.7 + PIL）
- ✅ CMS文章撰写与发布
- ✅ 数据清洗（通过tool模式或直接调用cleaner）
- ✅ 文件上传（图片/文档）
- ❌ 不直接对话知识库（无RAG注入）
- ❌ 不控制抖音小程序
- ❌ 不访问用户聊天历史（只管理后台会话）

---

## 四、模块3：RAG知识库 + 聊天机器人 + 抖音小程序

### 4.1 RAG知识库数据模型

**表: `knowledge_blocks`** (在 auth-center 的数据库中)

```sql
CREATE TABLE knowledge_blocks (
    id          TEXT PRIMARY KEY,      -- kb_{类型}_{序号}_{标题}
    title       TEXT NOT NULL,         -- 标题（最多200字）
    content     TEXT NOT NULL,         -- 正文
    keywords    TEXT DEFAULT '',       -- 关键词（逗号分隔）
    category    TEXT DEFAULT '',       -- company/product/price/tech/service/faq/industry
    priority    INTEGER DEFAULT 0,     -- 优先级（10最高）
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);
```

**预置种子数据**: 20条（覆盖公司信息、产品功能、价格方案、技术特点、服务流程、FAQ）

### 4.2 知识注入流程

```
途径1: 数据清洗 (Cleaner Agent)
  管理员提交文本 → LLM清洗 → 写入 knowledge_blocks
  工具链: cleaner_agent.py → knowledge_queue表 → LLM → knowledge_blocks表

途径2: 平台API管理
  POST /api/v1/knowledge/save — 新增/更新知识块
  POST /api/v1/knowledge/delete — 删除知识块
  ⚠️ 这两个接口当前是"TODO"状态，只有占位符，未实现真实逻辑

途径3: 数据库迁移种子
  database.py 迁移代码在首次运行时插入20条种子数据
```

### 4.3 RAG检索实现 (平台API)

**端点**: `POST /api/v1/rag/search`

**检索算法** (并非真正的向量RAG，而是混合关键词检索):

```python
1. 从 knowledge_blocks 读取所有记录（按priority降序）
2. 对每条记录计算评分:
   - 关键词匹配: 用户查询词是否在keywords字段中出现（权重0.6）
   - 字符重叠: 查询词字符与content/title字符的overlap（权重0.4）
   - 精确短语匹配加分: query in content (+0.3), query in title (+0.2)
3. 排序取 Top-K (默认5条，最大20条)
```

**关键问题**: 这不是真正的语义向量检索。没有embedding、没有向量数据库，只是**关键词+字符匹配**。对于同义词（如"价格"vs"费用"）无法匹配。

### 4.4 聊天机器人（平台AI客服）

**端点**: `POST /api/v1/chat/request`

- 直接从 `system_config` 读取 `mp_ai_provider/mp_ai_model/mp_ai_api_key` 配置
- 直接调用 LLM API（默认 deepseek-chat）
- **不做RAG检索增强**：直接将用户消息转发给大模型，不注入knowledge_blocks内容
- 记录token用量到 `agent_token_logs` 表

### 4.5 聊天机器人（社区AI客服 — Kai Assistant）

**文件**: `community/chatbot.py` (469行)

架构:

```
用户消息
  ↓
chat_bp /api/v1/chat (SSE流式)
  ↓
_build_msgs()
  1. 检查是否需转人工 (escalate keywords)
  2. FAQ检索 (_search_faq) — 从 faq.json 中关键词匹配
  3. 工单分类 (_classify_ticket_type) — presale/aftersale/complaint/suggestion
  ↓
如果FAQ命中 → 直接返回FAQ答案（不调用LLM）
如果转人工 → 返回转人工提示 + 创建contact_conversations工单
如果LLM需回答 → 调用_stream()
  ↓
_stream() 
  - 优先使用 AIEngine (从 agent_matrix 的 "Kai Assistant" 记录读取配置)
  - 回退到 urllib 直接调用 DeepSeek API
```

**知识来源（社区聊天机器人）**:
1. **FAQ文件** (`community/easykai_faq.md`) — 硬编码的FAQ文档，约207行
2. **FAQ-JSON** (`community/faq.json`) — 结构化FAQ，约5.8KB
3. **白皮书** (`community/chatbot_whitepaper.md`) — 技术白皮书，约12KB
4. **LLM自身知识** — 大模型训练数据中的通用知识
5. **Agent Matrix 的 Kai Assistant 配置** — 从 `agent_matrix` 表读取 `system_prompt`

**⚠️ 关键发现**: 社区聊天机器人**不查询 knowledge_blocks 表**。它的FAQ知识来自独立文件，与数据清洗模块的知识库是**两套独立的系统**。

### 4.6 抖音小程序AI客服

从 `api_v1.py` 的 `chat_request()` 端点看：

1. 抖音小程序通过 `POST /api/v1/chat/request` 调用
2. 需要JWT Token认证（`require_auth()`）
3. 直接调用LLM（deepseek-chat）
4. **不执行RAG检索**，不注入knowledge_blocks内容
5. 消息直接透传到大模型，无知识增强

### 4.7 cognition-service（独立的认知推理服务）

这是一个**独立的服务**（PostgreSQL + pgvector），与主项目共享部分目录但使用独立数据库：

- 主要用于 TradeMind 股票分析系统的 thesis（分析论点）的**语义向量存储与检索**
- 使用 `sentence-transformers/all-MiniLM-L6-v2` 生成384维embedding
- 通过 `pgvector` 实现余弦相似度搜索
- **与主项目 data_cleaner → knowledge_blocks 体系完全隔离**

---

## 五、"数据清洗→知识库→聊天机器人" 数据流向图（文字版）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        管理员管理后台 (agent.easykai.cn)                     │
│                                                                            │
│  ┌──────────────┐     ┌──────────────────┐      ┌───────────────────────┐  │
│  │  AI对话输入   │────→│ Agent Matrix      │─────→│ 子Agent执行结果        │  │
│  │  (clean意图)  │     │ (Athena编排)      │      │                       │  │
│  └──────────────┘     └────────┬─────────┘      └───────────────────────┘  │
│                                │                                           │
│  ┌──────────────┐              │ process_clean_content()                   │
│  │ 清洗API提交   │─────────────┘                                           │
│  │ /shop/cleaner │                                                         │
│  └───────┬──────┘                                                         │
│          │                                                                 │
└──────────┼─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据库 (auth-center/data/easykai.db)              │
│                                                                            │
│  ┌──────────────────┐      ┌──────────────────────────────────────┐        │
│  │ knowledge_queue   │─────→│ knowledge_blocks                     │        │
│  │ (待清洗队列)       │ LLM  │ (RAG知识库核心)                       │        │
│  │                   │ 清洗  │  - 20条种子数据                       │        │
│  │ source,           │      │  - 清洗写入新条目                     │        │
│  │ raw_content,      │      │  - 分类: company/product/price/...    │        │
│  │ status,           │      │  - 无embedding/向量索引               │        │
│  │ cleaned_id        │      │  - 仅关键词+字符检索                  │        │
│  └──────────────────┘      └──────────┬───────────────────────────┘        │
│                                       │                                    │
│  ┌────────────────────────────────────┼──────┐                             │
│  │  community/faq.json  ←─ 独立数据  │      │  ← 不互通                    │
│  │  community/easykai_faq.md          │      │                             │
│  └────────────────────────────────────┼──────┘                             │
└───────────────────────────────────────┼─────────────────────────────────────┘
                                        │
          ┌─────────────────────────────┼──────────────────────────┐
          │                             │                          │
          ▼                             ▼                          ▼
┌──────────────────┐   ┌──────────────────────────┐  ┌─────────────────────┐
│ 平台AI客服        │   │ 社区聊天机器人 (Kai)      │  │ 抖音小程序AI客服     │
│ (platform)        │   │ (community)              │  │ (抖音小程序)         │
│                   │   │                          │  │                     │
│ /api/v1/          │   │ /api/v1/chat (SSE)       │  │ /api/v1/chat/request│
│ chat/request      │   │                          │  │                     │
│                   │   │ 知识来源:                 │  │ 知识来源:            │
│ 知识来源:         │   │ 1. faq.json (关键词匹配)  │  │ 直接调用LLM          │
│ 直接调用LLM       │   │ 2. easykai_faq.md        │  │ (deepseek-chat)     │
│ (deepseek-chat)   │   │ 3. chatbot_whitepaper.md │  │ **不查询             │
│                   │   │ 4. LLM自身知识            │  │ knowledge_blocks**  │
│ **不查询          │   │ 5. Kai Assistant prompt   │  │                     │
│ knowledge_blocks**│   │                          │  │                     │
│                   │   │ **不查询                  │  │                     │
│                   │   │ knowledge_blocks**       │  │                     │
└──────────────────┘   └──────────────────────────┘  └─────────────────────┘
```

---

## 六、瓶颈与问题汇总

### 6.1 知识库未实际被消费

| 问题 | 严重程度 |
|------|---------|
| **平台AI客服不查询 knowledge_blocks** — 直接透传消息给LLM，无RAG增强 | 🔴 高 |
| **社区聊天机器人不查询 knowledge_blocks** — 使用独立的faq.json文件 | 🔴 高 |
| **抖音小程序AI客服不查询 knowledge_blocks** — 直接调用LLM | 🔴 高 |
| **Athena Master Agent不感知 knowledge_blocks** — Prompt中无知识库注入 | 🟡 中 |

### 6.2 检索实现粗糙

| 问题 | 说明 |
|------|------|
| **无向量embedding** | `rag/search` 仅靠关键词+字符匹配，不是真正的语义检索 |
| **同义词不识别** | "价格"和"费用"在关键词匹配中是不同的 |
| **无索引优化** | 全表扫描，数据量大时性能差 |
| **无排序算法** | 评分公式简单，缺乏BM25等经典算法 |

### 6.3 数据清洗的局限

| 问题 | 说明 |
|------|------|
| **仅管理员手动输入** | 无自动采集/爬虫机制，知识注入依赖人工 |
| **去重机制简单** | 仅按标题字符串去重，内容相似但标题不同的会重复 |
| **单条清洗速率** | 串行逐条调用LLM，大批量时耗时长 |
| **无审核流程** | 清洗后直接入库，没有人工审核环节 |

### 6.4 知识体系割裂

```
知识库A: knowledge_blocks (数据清洗产出，20+条种子+清洗条目)
  → 目前没有被任何聊天机器人消费

知识库B: faq.json + easykai_faq.md (社区聊天机器人使用)
  → 独立维护，与知识库A不同步

知识库C: chatbot_whitepaper.md (社区聊天机器人使用)
  → 独立维护

知识库D: prompts/master_prompt.md (Athena的AI知识)
  → 写死在Prompt中
```

### 6.5 cognition-service 的割裂

cognition-service 使用 PostgreSQL + pgvector，处理的是 TradeMind 证券分析的thesis语义检索，与主项目的知识库体系完全独立，不共享数据。

---

## 七、建议优化方向（优先级排序）

1. **🔴 打通知识库→聊天机器人管道**
   - 在 `/api/v1/chat/request` 中加入 `/rag/search` 调用，注入检索结果到LLM context
   - 社区聊天机器人增加 `knowledge_blocks` 查询作为备选知识源

2. **🟡 引入向量检索**
   - 为 knowledge_blocks 生成embedding（可用cognition-service的sentence-transformers）
   - 替换纯关键词匹配为语义向量检索

3. **🟡 统一知识管理**
   - 将 faq.json、easykai_faq.md 迁移到 knowledge_blocks 表中
   - 建立知识版本管理和审核流程

4. **🟢 数据清洗自动化**
   - 增加URL抓取功能，自动采集指定源的内容
   - 用更好的去重算法（如SimHash）

5. **🟢 Agent Matrix 集成知识库**
   - 在 Athena 的任务分解中注入 knowledge_blocks 作为参考上下文
