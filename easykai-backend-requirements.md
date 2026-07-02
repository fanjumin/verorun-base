# easykai.cn 后端新增 API 需求文档

## 1. 目的

本文件基于小程序代码和项目根目录中的三份 API 文档（`DOUYIN_MINIPROGRAM_API.md`、`DOUYIN_MINIPROGRAM_FRONTEND_GUIDE.md`、`DOUYIN_MINIPROGRAM_INTEGRATION.md`）编写。

目标是明确 easykai.cn 后端需要新增或补齐的 REST API 接口，保证小程序能够正常对接、替换抖音云原有后端能力，并补全当前代码调用与文档说明间的差距。

---

## 2. 现状总结

### 2.1 小程序代码对后端的期望

前端 `AI 赋能建站` 小程序中依赖以下 `easykaiApi` 接口：

- 会话存储：`saveMessages`、`fetchMessages`
- 用户画像：`saveProfile`、`fetchProfile`、`saveSummary`
- 知识库：`fetchKnowledgeList`、`saveKnowledge`、`deleteKnowledge`
- RAG 语义检索：`semanticSearch`
- AI 对话：`chatRequest`（非流式）和 `chatStream`（SSE 流式）
- 飞书通知：`sendFeishuNotify`
- 用户反馈：`saveFeedback`
- 来访统计：`incrementVisit`

此外，配置中的 `EASYKAI_API_CONFIG` 还包含：

- `CHAT_SAVE: /api/v1/chat/save`
- `CHAT_HISTORY: /api/v1/chat/history`
- `CHAT_STREAM: /api/v1/chat`
- `PROFILE_SAVE: /api/v1/profile/save`
- `PROFILE_GET: /api/v1/profile/get`
- `PROFILE_SUMMARY: /api/v1/profile/summary`
- `KNOWLEDGE_LIST: /api/v1/knowledge/list`
- `KNOWLEDGE_SAVE: /api/v1/knowledge/save`
- `KNOWLEDGE_DELETE: /api/v1/knowledge/delete`
- `RAG_SEARCH: /api/v1/rag/search`
- `FEISHU_NOTIFY: /api/v1/notify/feishu`
- `FEEDBACK_SAVE: /api/v1/feedback/save`
- `CHAT_REQUEST: /api/v1/chat/request`
- `VISIT_INCREMENT: /api/v1/visit/increment`

### 2.2 文档提到但当前代码未完全覆盖的接口

根目录三份 API 文档还说明了以下接口能力：

- 抖音小程序用户接口：`/douyin_mp/user/info`、`/douyin_mp/user/bind_status`、`/douyin_mp/user/unbind_douyin`
- 抖音 OAuth/登录认证：`/auth/sms/send`、`/auth/sms/login`、`/auth/douyin/qr`、`/auth/douyin/callback`
- 聊天机器人状态检查：`/api/v1/chat/status`
- 转人工客服：`/api/v1/chat/escalate`

这些接口是后端对接能力的一部分，即使当前 `AI 赋能建站` 代码未直接调用，也应被视为后端需求的一部分，以保证文档与实际对接环境一致。

---

## 3. 主要新增/补齐接口需求

### 3.1 认证与用户身份

#### 3.1.1 POST `/auth/sms/send`

- 功能：发送短信验证码
- 请求：
```json
{
  "phone": "13800138000",
  "purpose": "login",
  "captcha_id": "可选"
}
```
- 返回：
```json
{
  "success": true,
  "data": { "message": "验证码已发送" }
}
```

#### 3.1.2 POST `/auth/sms/login`

- 功能：使用短信验证码登录 / 注册
- 请求：
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```
- 返回：
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOi...",
    "user": { "id": 123, "phone": "13800138000", "nickname": "张三" }
  }
}
```

#### 3.1.3 GET `/auth/douyin/qr`

- 功能：获取抖音登录授权 URL
- 返回：
```json
{
  "success": true,
  "data": { "url": "https://open.douyin.com/..." }
}
```

#### 3.1.4 GET `/auth/douyin/callback`

- 功能：处理抖音 OAuth 回调，生成 JWT token
- 返回：重定向到小程序可读取的页面或 `token` 参数

#### 3.1.5 GET `/douyin_mp/user/info`

- 功能：获取当前抖音小程序用户信息
- 返回：
```json
{
  "success": true,
  "data": {
    "id": 123,
    "phone": "13800138000",
    "username": "user123",
    "display_name": "张三",
    "is_admin": false,
    "douyin_bound": true,
    "douyin_nickname": "抖音用户",
    "douyin_avatar": "https://...",
    "agent_id": "agent_001",
    "agent_nickname": "AI助手",
    "agent_avatar_url": "https://..."
  }
}
```

#### 3.1.6 GET `/douyin_mp/user/bind_status`

- 功能：检查抖音账号绑定状态
- 返回：
```json
{
  "success": true,
  "data": { "bound": true }
}
```

#### 3.1.7 POST `/douyin_mp/user/unbind_douyin`

- 功能：解绑抖音账号
- 请求：无额外 body，仅鉴权
- 返回：
```json
{
  "success": true,
  "data": { "message": "抖音账号已成功解绑" }
}
```

---

### 3.2 会话与聊天相关接口

#### 3.2.1 POST `/api/v1/chat/save`

- 功能：保存用户会话消息
- 前端调用：`easykaiApi.saveMessages(openid, messages)`
- 请求：
```json
{
  "openid": "string",
  "messages": [
    { "id": "msg1", "role": "user", "content": "你好", "timestamp": 168... },
    { "id": "msg2", "role": "assistant", "content": "您好，有什么可以帮您？", "timestamp": 168... }
  ]
}
```
- 返回：
```json
{ "code": 0, "message": "success", "data": { "saved": true } }
```

#### 3.2.2 POST `/api/v1/chat/history`

- 功能：获取会话历史
- 前端调用：`easykaiApi.fetchMessages(openid)`
- 请求：
```json
{ "openid": "string" }
```
- 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": { "messages": [ ... ] }
}
```

#### 3.2.3 POST `/api/v1/chat/request`

- 功能：非流式 AI 对话请求
- 前端调用：`easykaiApi.chatRequest({ messages, temperature, maxTokens })`
- 请求：
```json
{
  "messages": [ { "role": "system", "content": "..." }, ... ],
  "temperature": 0.7,
  "max_tokens": 2048
}
```
- 返回：
```json
{ "code": 0, "message": "success", "data": { "content": "生成的回复文本" } }
```

#### 3.2.4 POST `/api/v1/chat`

- 功能：SSE 流式 AI 对话
- 前端调用：`easykaiApi.chatStream(messages, profile, visitCount, threeAskState, callbacks)`
- 请求：
```json
{
  "messages": [ ... ],
  "profile": { ... },
  "visitCount": 1,
  "threeAskState": 0
}
```
- 响应：SSE 格式，至少支持以下事件结构

1. `data: { "type": "token", "content": "..." }`
2. `data: { "type": "done", "reply": "...", "retrievedKnowledge": [...] }`
3. `data: { "type": "error", "message": "..." }`

---

### 3.3 用户画像与会话摘要

#### 3.3.1 POST `/api/v1/profile/save`

- 功能：保存用户画像
- 前端调用：`easykaiApi.saveProfile(openid, profile)`
- 请求：
```json
{ "openid": "string", "profile": { ... } }
```

#### 3.3.2 POST `/api/v1/profile/get`

- 功能：获取用户画像
- 前端调用：`easykaiApi.fetchProfile(openid)`
- 请求：
```json
{ "openid": "string" }
```
- 返回：
```json
{ "code": 0, "message": "success", "data": { "profile": { ... } } }
```

#### 3.3.3 POST `/api/v1/profile/summary`

- 功能：保存会话摘要文本
- 前端调用：`easykaiApi.saveSummary(openid, summary)`
- 请求：
```json
{ "openid": "string", "summary": "今天用户咨询了AI建站报价..." }
```

---

### 3.4 知识库与 RAG 检索

#### 3.4.1 GET `/api/v1/knowledge/list`

- 功能：获取知识库列表
- 前端调用：`easykaiApi.fetchKnowledgeList({})`
- 请求参数（可选）：`category`, `keyword`, `page`, `pageSize`
- 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "kb_product_001",
      "title": "易站智能概述",
      "content": "...",
      "keywords": ["智策", "AI建站"],
      "category": "product",
      "priority": 10
    }
  ]
}
```

#### 3.4.2 POST `/api/v1/knowledge/save`

- 功能：新增/更新知识块
- 前端调用：`easykaiApi.saveKnowledge(params)`
- 请求：
```json
{
  "id": "kb_product_001",
  "title": "...",
  "content": "...",
  "keywords": ["..."],
  "category": "product",
  "priority": 9
}
```

#### 3.4.3 POST `/api/v1/knowledge/delete`

- 功能：删除知识块
- 前端调用：`easykaiApi.deleteKnowledge(id)`
- 请求：
```json
{ "id": "kb_product_001" }
```

#### 3.4.4 POST `/api/v1/rag/search`

- 功能：混合语义检索
- 前端调用：`easykaiApi.semanticSearch(query, topK, category)`
- 请求：
```json
{
  "query": "我想了解产品功能",
  "topK": 5,
  "category": "product"
}
```
- 返回：
```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "block": { "id": "kb_product_001", "title": "...", "content": "..." },
      "score": 0.92
    }
  ]
}
```

---

### 3.5 其他业务接口

#### 3.5.1 POST `/api/v1/notify/feishu`

- 功能：飞书卡片通知代理发送
- 前端调用：`easykaiApi.sendFeishuNotify(cardData)`
- 请求：
```json
{ "cardData": { ... } }
```

#### 3.5.2 POST `/api/v1/feedback/save`

- 功能：保存用户反馈
- 前端调用：`easykaiApi.saveFeedback(openid, feedbackData)`
- 请求：
```json
{
  "openid": "string",
  "messageId": "string",
  "feedback": "good | bad | ...",
  "content": "assistant reply",
  "query": "user query",
  "retrievedIds": ["kb_product_001"],
  "aiReply": "...",
  "retrievedKnowledge": [ ... ],
  "timestamp": 168...
}
```

#### 3.5.3 POST `/api/v1/visit/increment`

- 功能：递增用户来访次数并返回最新值
- 前端调用：`easykaiApi.incrementVisit(openid)`
- 请求：
```json
{ "openid": "string" }
```
- 返回：
```json
{ "code": 0, "message": "success", "data": { "visitCount": 5 } }
```

#### 3.5.4 GET `/api/v1/chat/status`

- 功能：检查聊天机器人服务状态
- 文档提及，建议补齐
- 返回：
```json
{
  "ok": true,
  "engine": "agent_matrix",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "agent_id": "agent_001",
  "is_active": 1,
  "faq": true
}
```

#### 3.5.5 POST `/api/v1/chat/escalate`

- 功能：转人工客服
- 文档提及，建议补齐
- 请求：
```json
{
  "contact": "13800138000",
  "message": "我想咨询产品定制方案",
  "type": "presale",
  "category": "",
  "priority": "normal"
}
```
- 返回：
```json
{ "success": true, "ticket_id": "ES-20260609-0001", "message": "已转人工" }
```

---

## 4. 数据格式和兼容性要求

### 4.1 后端返回格式兼容

`utils/easykai-api.js` 已兼容以下后端返回格式：

- `{ code: 0, data: ... }`
- `{ success: true, data: ... }`
- 以及 SSE 流式返回

因此后端应优先满足这两类成功响应结构，错误响应应包含 `code`/`message` 或 `success:false`。

### 4.2 字段规范

- 所有 `openid` 字段必须为字符串，且在后端唯一标识用户
- `messages` 数组中每条消息须包含 `role`、`content`，可附加 `id` 和 `timestamp`
- `profile` 对象可存在部分字段，后端应支持部分更新
- `knowledge` 块应包含 `id`、`title`、`content`、`keywords`、`category`、`priority`
- `semantic-search` 返回结果需包含 `block` 和 `score`

---

## 5. 兼容性与降级策略

### 5.1 前端降级逻辑

小程序代码已经实现以下降级策略：

- 会话消息保存失败时降级到本地存储 `__cloud_fallback__messages_{openid}`
- 用户画像获取/保存失败时降级到本地存储 `__cloud_fallback__profile_{openid}`
- 用户反馈保存失败时降级到本地存储 `__cloud_fallback__feedback_{openid}`
- 检索或聊天失败时可使用本地知识库内容

### 5.2 后端可用性要求

为了保证用户体验，建议 easykai.cn 后端优先保证：

- `/api/v1/chat` / `/api/v1/chat/request` 高可用
- `/api/v1/profile/get` 与 `/api/v1/chat/history` 可用
- `/api/v1/rag/search` 作为增强接口，若不可用前端可降级

---

## 6. 补充说明

### 6.1 与现有文档对齐

本需求文档已对齐以下三份根目录文档：

- `DOUYIN_MINIPROGRAM_API.md`
- `DOUYIN_MINIPROGRAM_FRONTEND_GUIDE.md`
- `DOUYIN_MINIPROGRAM_INTEGRATION.md`

其中 `easykai.cn` 后端需要补齐的接口包括：

- 小程序认证与抖音绑定接口
- 会话保存/读取接口
- AI 流式与非流式对话接口
- 知识库 CRUD 与语义检索接口
- 飞书通知与用户反馈接口
- 来访计数与聊天状态检测接口

### 6.2 当前代码待确认点

如果后端没有以下接口，则小程序会出现功能缺失或异常：

- `/api/v1/chat/save` 与 `/api/v1/chat/history`
- `/api/v1/profile/get` 返回 `{ profile: ... }`
- `/api/v1/rag/search` 返回 `[{ block, score }]`
- `/api/v1/chat` SSE 返回 `data: { type: 'token' | 'done' | 'error' }`

---

## 7. 建议优先级

1. `chat/save`、`chat/history`、`chat`、`chat/request`
2. `profile/get`、`profile/save`、`profile/summary`
3. `knowledge/list`、`knowledge/save`、`knowledge/delete`
4. `rag/search`
5. `feedback/save`、`visit/increment`
6. `feishu/notify`
7. `douyin_mp/*`、`auth/*`、`chat/status`、`chat/escalate`
