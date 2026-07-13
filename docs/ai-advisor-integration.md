# AI Advisor Integration Guide — Social Media Mini-Programs

> Version: v1.0 | Date: 2026-07-13  
> System: VeroRun / easykai.cn

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Authentication Bridge](#2-authentication-bridge)
3. [Chat Bridge](#3-chat-bridge)
4. [RAG Knowledge Retrieval](#4-rag-knowledge-retrieval)
5. [Multi-Channel Session Management](#5-multi-channel-session-management)
6. [Configuration Guide](#6-configuration-guide)
7. [API Reference](#7-api-reference)

---

## 1. Architecture Overview

### 1.1 Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Social Media Platform                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Douyin  │  │  WeChat  │  │ Telegram │  │   LINE   │        │
│  │  (TT)    │  │  (WX)    │  │ (WebApp) │  │  (LIFF)  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │              │              │              │              │
│       ▼              ▼              ▼              ▼              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Platform SDKs (sdks/*/)                      │   │
│  │  douyin/api.js  wechat/api.js  telegram/webapp.js  ...   │   │
│  └──────────────────────────┬───────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Unified SDKs (sdks/common/)                      │   │
│  │  VeroChat.js  VeroAuth.js  VeroRAG.js                     │   │
│  └──────────────────────────┬───────────────────────────────┘   │
└─────────────────────────────┼────────────────────────────────────┘
                              │ HTTPS (JWT Bearer)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   VeroRun Backend (easykai.cn)                    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  /api/v1/mini-program/  Blueprint                         │   │
│  │                                                           │   │
│  │  POST /auth/login      →  Platform Login → JWT Token      │   │
│  │  POST /chat/stream     →  SSE Streaming Chat              │   │
│  │  POST /chat/send       →  Non-Streaming Chat              │   │
│  │  GET  /chat/history    →  Session History                 │   │
│  │  GET  /knowledge/search →  RAG Knowledge Retrieval        │   │
│  │  GET  /user/profile    →  User Profile                    │   │
│  │  GET  /site/info       →  Brand / Site Config             │   │
│  │  GET  /site/pages      →  Published Pages                 │   │
│  └──────────────┬───────────────────────────────────────────┘   │
│                 │                                                 │
│     ┌───────────┼───────────┐                                    │
│     ▼           ▼           ▼                                    │
│  ┌──────┐  ┌──────┐  ┌──────────┐                               │
│  │ AI   │  │ RAG  │  │ Intent   │                               │
│  │Engine│  │Search│  │Classifier│                               │
│  └──────┘  └──────┘  └──────────┘                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Components

| Component | Path | Role |
|-----------|------|------|
| `AIEngine` | `agent_matrix/engine.py` | LLM chat streaming (DashScope, DeepSeek, OpenAI) |
| `_rag_search()` | `platform/routes/api_v1.py` | Knowledge base semantic search |
| `classify_intent()` | `plugins/chatbot/stats.py` | User intent classification |
| `_build_rag_context()` | `platform/routes/api_v1.py` | Format RAG results as system prompt |
| `mini_program_bp` | `platform/routes/mini_program.py` | API blueprint for mini-programs |

---

## 2. Authentication Bridge

### 2.1 Flow Diagram

```
User (Mini-Program)                Platform API              VeroRun Backend
      │                                │                          │
      │ 1. Platform Login              │                          │
      │ (tt.login/wx.login/            │                          │
      │  tg.initData/liff.login)       │                          │
      │───────────────────────────────>│                          │
      │                                │                          │
      │ 2. Get code / initData /       │                          │
      │    accessToken                 │                          │
      │<───────────────────────────────│                          │
      │                                │                          │
      │ 3. POST /auth/login            │                          │
      │──────────────────────────────────────────────────────────>│
      │     { platform, code,          │                          │
      │       initData, accessToken }  │                          │
      │                                │                          │
      │                                │  4. Verify platform      │
      │                                │     credentials          │
      │                                │                          │
      │                                │  5. Create/link user     │
      │                                │     in system DB         │
      │                                │                          │
      │ 6. Return JWT token            │                          │
      │<──────────────────────────────────────────────────────────│
      │     { token, user }            │                          │
      │                                │                          │
      │ 7. Store token in              │                          │
      │    localStorage/StorageSync    │                          │
```

### 2.2 Platform-Specific Authentication

| Platform | Auth Method | Credential Field | API Call |
|----------|-------------|-----------------|----------|
| Douyin | `tt.login()` → code | `code` | POST `/auth/login` `{ platform: "douyin", code }` |
| WeChat | `wx.login()` → code | `code` | POST `/auth/login` `{ platform: "wechat", code }` |
| Telegram | `tg.initData` | `initData` | POST `/auth/login` `{ platform: "telegram", initData }` |
| LINE | `liff.getProfile()` | `accessToken`, `userId` | POST `/auth/login` `{ platform: "line", accessToken, userId }` |

### 2.3 JWT Payload

```json
{
    "user_id": 123,
    "username": "douyin_user_abc",
    "display_name": "抖音用户",
    "is_admin": false,
    "platform": "douyin",
    "platform_user_id": "douyin_abc123",
    "exp": 1715000000
}
```

---

## 3. Chat Bridge

### 3.1 Streaming Chat (SSE)

The mini-program chat endpoint mirrors the existing AI Advisor chatbot flow:

```python
# platform/routes/mini_program.py

@mini_program_bp.route('/chat/stream', methods=['POST'])
def mini_program_chat_stream():
    data = request.get_json()
    message = data.get('message', '')
    history = data.get('history', [])
    platform = data.get('platform', 'website')

    # 1. RAG Knowledge Retrieval
    from platform.routes.api_v1 import _rag_search, _build_rag_context
    knowledge = _rag_search(message, top_k=5)
    rag_context = _build_rag_context(knowledge)

    # 2. Intent Classification
    from plugins.chatbot.stats import classify_intent
    intent, sentiment = classify_intent(message)

    # 3. Agent Configuration
    from platform.routes.api_v1 import _get_chatbot_config, _get_chatbot_agent
    cfg = _get_chatbot_config()
    agent = _get_chatbot_agent(cfg.get('agent_id', 'kai_assistant'))

    # 4. AI Engine Chat
    from agent_matrix.engine import AIEngine
    engine = AIEngine({
        'provider': agent.get('provider', 'dashscope'),
        'model_name': agent.get('model_name', 'qwen-turbo'),
        'system_prompt': system_prompt,
    })

    # 5. SSE Streaming Response
    def generate():
        for token in engine.chat_stream(messages):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'reply': full_reply})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
```

### 3.2 SSE Event Format

| Event Type | Field | Description |
|------------|-------|-------------|
| `token` | `content` | Single text token from AI response |
| `done` | `reply`, `retrievedKnowledge` | Full reply + knowledge sources |
| `error` | `error` | Error message |

### 3.3 Client-Side Implementation

```javascript
// Using VeroChat SDK
const chat = new VeroChat({
    baseURL: 'https://platform.easykai.cn',
    token: jwtToken,
    platform: 'telegram'
});

await chat.streamChat(
    message,
    history,
    (token) => { /* render token */ },
    (result) => { /* done */ }
);
```

---

## 4. RAG Knowledge Retrieval

### 4.1 How It Works

1. User sends a message to the mini-program
2. Backend extracts the last user message (max 200 chars)
3. `_rag_search()` searches `knowledge_blocks` table using:
   - Keyword matching (60% weight)
   - Character overlap scoring (25% content + 15% title)
   - Exact match bonus (30% content + 20% title)
4. Top 5 results are formatted as system prompt context
5. Context is prepended to the AI engine's system prompt

### 4.2 Direct Knowledge Search API

```http
GET /api/v1/mini-program/knowledge/search?q=product+return+policy&topK=5&category=faq
Authorization: Bearer <jwt_token>
```

### 4.3 Using VeroRAG SDK

```javascript
const rag = new VeroRAG({
    baseURL: 'https://platform.easykai.cn',
    token: jwtToken
});

const results = await rag.search('How to return a product?', 5, 'faq');
```

---

## 5. Multi-Channel Session Management

### 5.1 Session Tracking

The `chat_messages` table tracks sessions per platform:

```sql
-- Table structure (extended)
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY,
    openid TEXT,
    messages TEXT,          -- JSON array of messages
    platform TEXT DEFAULT 'website',     -- NEW: douyin/wechat/telegram/line
    platform_user_id TEXT DEFAULT '',     -- NEW: platform-specific user ID
    created_at TEXT,
    updated_at TEXT
);
```

### 5.2 Intent Classification

The `classify_intent()` function from `plugins/chatbot/stats.py` is reused:

| Intent | Description | AI Behavior |
|--------|-------------|-------------|
| `purchase` | Buying intent | Route to sales agent, product recommendations |
| `aftersale` | After-sales | Order lookup, return policy |
| `complaint` | Complaint | Escalate priority, apologize |
| `consult` | General inquiry | Knowledge base search |
| `technical` | Technical support | Debug guidance, API docs |
| `other` | Uncategorized | General chat |

### 5.3 Sentiment Analysis

| Sentiment | Description | Action |
|-----------|-------------|--------|
| `positive` | Happy user | Standard response |
| `neutral` | Neutral | Standard response |
| `negative` | Unhappy user | Empathetic response, offer escalation |
| `urgent` | Critical issue | Immediate escalation to human agent |

---

## 6. Configuration Guide

### 6.1 AI Engine Configuration

Configure via system_config table:

```sql
INSERT INTO system_config (key, value) VALUES
    ('mp_ai_provider', 'deepseek'),
    ('mp_ai_model', 'deepseek-chat'),
    ('mp_ai_base_url', 'https://api.deepseek.com'),
    ('mp_ai_api_key', 'sk-your-api-key');
```

### 6.2 Chatbot Configuration

Configure via plugin_configs table:

```sql
INSERT INTO plugin_configs (plugin_name, key, value) VALUES
    ('chatbot', 'agent_id', 'kai_assistant'),
    ('chatbot', 'max_history', '20'),
    ('chatbot', 'welcome_message', 'Hello! I am your AI advisor.');
```

### 6.3 Environment Variables

```ini
# .env
DEPLOY_DOMAIN=easykai.cn
DEPLOY_MARKET=cn
DEV_ACCOUNTS_ENCRYPTION_KEY=your_32_byte_encryption_key
```

---

## 7. API Reference

### 7.1 Authentication

```http
POST /api/v1/mini-program/auth/login
Content-Type: application/json

{
    "platform": "douyin",
    "code": "tt_code_from_login",
    "nickname": "User Name",
    "avatar": "https://..."
}
```

### 7.2 Chat

```http
POST /api/v1/mini-program/chat/stream
Content-Type: application/json
Authorization: Bearer <jwt>

{
    "message": "What is your return policy?",
    "history": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"}
    ],
    "platform": "telegram"
}
```

### 7.3 Knowledge

```http
GET /api/v1/mini-program/knowledge/search?q=return+policy&topK=5
Authorization: Bearer <jwt>
```

### 7.4 Site Info

```http
GET /api/v1/mini-program/site/info
Authorization: Bearer <jwt>
```

### 7.5 User Profile

```http
GET /api/v1/mini-program/user/profile
Authorization: Bearer <jwt>
```