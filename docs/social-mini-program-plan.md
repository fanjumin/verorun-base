# Social Media Mini-Program Generation System — Architecture Plan

> Version: v1.0 | Date: 2026-07-13 | Status: Confirmed  
> System: VeroRun / easykai.cn

---

## Table of Contents

1. [Overview](#1-overview)
2. [Current System Analysis](#2-current-system-analysis)
3. [Platform Research Summary](#3-platform-research-summary)
4. [System API Endpoints Specification](#4-system-api-endpoints-specification)
5. [System SDK Design](#5-system-sdk-design)
6. [Plugin Standard Update](#6-plugin-standard-update)
7. [AI Advisor Integration](#7-ai-advisor-integration)
8. [Site_builder Mini-Program Generation](#8-site_builder-mini-program-generation)
9. [Developer Account Management Plugin](#9-developer-account-management-plugin)
10. [Site_builder Preview Enhancement](#10-site_builder-preview-enhancement)
11. [Implementation Roadmap](#11-implementation-roadmap)
12. [Risks & Considerations](#12-risks--considerations)

---

## 1. Overview

### 1.1 Objective

Extend the existing `Site_builder` module to generate social media mini-programs for five platforms, integrating the system's real-time chat API and RAG knowledge base to deliver AI Advisor functionality directly within each platform.

### 1.2 Target Platforms

| Region | Platform | Mini-Program Type | Priority |
|--------|----------|-------------------|----------|
| China Mainland | **Douyin** (抖音) | Native Mini-Program (`tt.*` API) | P0 |
| China Mainland | **Toutiao** (头条) | Native Mini-Program (same as Douyin) | P1 |
| China Mainland | **WeChat** (微信) | Native Mini-Program (`wx.*` API) | P0 |
| Overseas | **Telegram** | Mini App (WebView + Bot API) | P0 |
| Overseas | **LINE** | LINE MINI App (LIFF v2) | P1 |

### 1.3 Key Deliverables

- Unified SDK layer (`sdks/`) for all five platforms
- MiniApp generation engine integrated into `Site_builder`
- Platform-specific project templates and generators
- Developer account management plugin
- Mobile device preview in Site_builder
- Updated documentation (API endpoints, SDK reference, plugin standards, AI Advisor integration)

---

## 2. Current System Analysis

### 2.1 Site_builder Module

**Location**: `site_builder/`

**Core Engine** (`site_builder/engine.py`):

```python
class SiteBuilderEngine:
    """DAG Flow: Parse → Plan → Execute (Brand → Theme → Nav → Pages → Docs)"""
    
    def _get_master_agent(self):
        """Get Master Agent from agent_matrix.models"""
        from agent_matrix import models as m
        agents = m.list_agents(role_type='master', active_only=True)
        return agents[0]
    
    def _get_ai_engine(self):
        """Get AIEngine instance"""
        from agent_matrix.engine import AIEngine
        master = self._get_master_agent()
        return AIEngine(master)
    
    def _call_llm(self, system_prompt, user_message, temperature=0.3, max_tokens=2000):
        """Call LLM, return raw text"""
        engine = self._get_ai_engine()
        return engine.chat([...], temperature=temperature, max_tokens=max_tokens)
    
    def parse_requirement(self, prompt_template, user_input) -> dict:
        """Parse user input → structured info"""
    
    def generate_plan(self, prompt_template, parsed, user_input) -> dict:
        """Generate complete site build plan"""
    
    def execute_plan(self, plan, prompt_template, draft=False) -> dict:
        """Execute DAG build, write to cms_blocks / cms_posts tables"""
```

**Routes** (`site_builder/routes.py`): 13 endpoints, prefix `/admin/site-builder/`

**Data Models** (`site_builder/models.py`):
- `site_builder_prompts` — industry prompt templates
- `site_builder_tasks` — build task records

**Generators** (`site_builder/generators/`):
- `brand.py` → `BrandGenerator.apply()`
- `theme.py` → `ThemeGenerator.apply_theme()`
- `navigation.py` → `NavigationGenerator.apply_nav()` / `apply_footer()`
- `pages.py` → `PageGenerator.apply_page_blocks()` / `apply_document()`

**Site Settings** (`site_builder/site_settings/`):
- `models.py` → `get_draft_tokens()`, `promote_draft_tokens()`, `backup_tokens()`
- `token_renderer.py` → renders tokens as CSS variables

### 2.2 AI Advisor Module

**Location**: `plugins/chatbot/`

**Plugin Config** (`plugin.json`):
```json
{
    "name": "AI Advisor",
    "identifier": "chatbot",
    "config": {
        "agent_id": "kai_assistant",
        "max_history": "20",
        "provider": "dashscope",
        "model_name": "qwen-turbo"
    },
    "agents": [{
        "identifier": "kai_assistant",
        "role_type": "sub",
        "domain": "chatbot",
        "prompt_file": "prompts/sub_chatbot_prompt.md",
        "capabilities": ["chatbot.faq", "chatbot.ticket", "chatbot.human_handoff"]
    }]
}
```

**Multi-Channel Router** (`plugins/chatbot/channels/router.py`):
```python
def _get_channel_config(channel):
    """Read channel config from im_gateway DB"""
    from plugins.im_gateway.models import get_im_db
    conn = get_im_db()
    row = conn.execute(
        "SELECT config_json FROM channel_configs WHERE channel=? AND is_enabled=1 LIMIT 1",
        (channel,)
    ).fetchone()
    return json.loads(row['config_json'])

def _call_ai(user_query, session_id=''):
    """Call AIEngine.chat_stream()"""
    from agent_matrix.engine import AIEngine
    engine = AIEngine({'provider': provider, 'model_name': model_name, 'system_prompt': system_prompt})
    for token in engine.chat_stream([...]):
        full_reply += token
    return full_reply, session_id, intent, sentiment

def telegram_handle_webhook(body):
    """Handle Telegram Update → call AI → sendMessage via Bot API"""

def line_handle_webhook(body):
    """Handle LINE Webhook events → call AI → reply via Messaging API"""
```

**Chat API** (`platform/routes/api_v1.py`):
```python
@api_v1_bp.route('/chat/request', methods=['POST'])
def chat_request():
    """Non-streaming AI chat with RAG enhancement"""

@api_v1_bp.route('/chat', methods=['POST'])
def chat_stream():
    """SSE streaming AI chat with RAG + intent classification + agent routing"""

def _rag_search(query, top_k=5, category=None):
    """Search knowledge_blocks table, return scored results"""

def _build_rag_context(knowledge):
    """Format retrieved knowledge as system prompt context"""
```

### 2.3 Existing Social Media Infrastructure

| Platform | Existing Capability | File |
|----------|-------------------|------|
| Douyin | Mini-program login (`/douyin_mp/login/code`) | `auth-center/routes/douyin_miniprogram.py` |
| Douyin | OAuth login (`/auth/douyin/qr`, `/auth/douyin/callback`) | `auth-center/routes/auth.py` |
| Telegram | Bot Webhook handler | `plugins/chatbot/channels/router.py` |
| Telegram | IM Gateway adapter | `plugins/im_gateway/adapters/telegram.py` |
| LINE | Webhook handler | `plugins/chatbot/channels/router.py` |
| LINE | IM Gateway adapter (LIFF) | `plugins/im_gateway/adapters/line.py` |
| WeChat | OAuth login | `auth-center/routes/auth.py` |

### 2.4 Plugin System

**Base Class** (`plugins/base.py`):
```python
class BasePlugin:
    name: str
    identifier: str
    version: str
    
    def on_install(self, registry=None) -> bool: ...
    def on_enable(self, registry=None) -> bool: ...
    def on_disable(self, registry=None) -> bool: ...
    def register_routes(self) -> List[Blueprint]: ...
    def register_jobs(self) -> List[dict]: ...
    def register_dag_nodes(self) -> Dict[str, Any]: ...
    def register_health_checks(self) -> List[dict]: ...
    def get_event_handlers(self) -> Dict[str, Any]: ...
    def get_config_value(self, key, default=None): ...
    def set_config_value(self, key, value): ...
```

---

## 3. Platform Research Summary

### 3.1 Platform Comparison

| Platform | Mini-Program Type | SDK / API | Language | Auth Method |
|----------|-------------------|-----------|----------|-------------|
| **Douyin** | Native Mini-Program | `tt.*` JS API + OpenAPI SDK (Java/Node/Go) | JS + ByteDance IDE | `tt.login()` → code → session_key |
| **Toutiao** | Same ecosystem as Douyin | `tt.*` JS API (shared) | JS + ByteDance IDE | Same as Douyin |
| **WeChat** | Native Mini-Program | `wx.*` JS API + Customer Service Message API | JS + WeChat DevTools | `wx.login()` → code → openid + session_key |
| **Telegram** | Mini App (WebView) | `telegram-web-app.js` SDK + Bot API | HTML/JS + Any backend | `initData` HMAC verification |
| **LINE** | LINE MINI App (LIFF v2) | `@line/liff` SDK + Messaging API | HTML/JS + Any backend | LIFF `getAccessToken()` |

### 3.2 Key Findings

1. **Douyin + Toutiao** share the same ByteDance mini-program ecosystem. One codebase can target both platforms. Requires enterprise verification (`企业主体认证`).

2. **WeChat** has the most mature mini-program ecosystem with built-in customer service message webhook support. Requires enterprise-verified mini-program account.

3. **Telegram Mini App** is essentially an H5 page running in a WebView. Lowest development cost, no review process. Already has Bot webhook integration.

4. **LINE MINI App** (LIFF v2) is also a WebView-based H5 app. Uses `@line/liff` SDK. Already has Messaging API integration.

5. **Core difference**: Douyin/WeChat are "native mini-programs" (require platform-specific IDEs and private APIs), while Telegram/LINE are "WebView mini-programs" (standard HTML/JS, deployed as static pages).

### 3.3 SDK Directory Structure

```
sdks/
├── douyin/              # Douyin/Toutiao Mini-Program SDK
│   ├── api.js           # tt.request() wrapper for system API
│   └── components/      # Reusable mini-program components
├── wechat/              # WeChat Mini-Program SDK
│   ├── api.js           # wx.request() wrapper for system API
│   └── components/
├── telegram/            # Telegram Mini App SDK
│   ├── webapp.js        # telegram-web-app.js wrapper
│   └── bot.js           # Bot API wrapper
├── line/                # LINE MINI App SDK
│   ├── liff.js          # @line/liff SDK wrapper
│   └── messaging.js     # Messaging API wrapper
└── common/              # Cross-platform shared layer
    ├── chat.js          # Unified chat interface (VeroChat class)
    ├── auth.js          # Unified auth (JWT SSO)
    └── rag.js           # RAG knowledge base query
```

---

## 4. System API Endpoints Specification

### 4.1 Unified Mini-Program API (New)

Prefix: `/api/v1/mini-program/`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/auth/login` | Platform login (code exchange → JWT) | Platform token |
| `POST` | `/chat/send` | Send message to AI Advisor (non-streaming) | JWT Bearer |
| `POST` | `/chat/stream` | SSE streaming chat with RAG | JWT Bearer |
| `GET` | `/chat/history` | Get conversation history | JWT Bearer |
| `GET` | `/knowledge/search` | RAG knowledge base search | JWT Bearer |
| `GET` | `/user/profile` | Get user profile | JWT Bearer |
| `GET` | `/site/info` | Get site config (brand, theme tokens) | Public |
| `GET` | `/site/pages` | Get page list | Public |
| `GET` | `/site/page/<slug>` | Get page content by slug | Public |

#### Request/Response Examples

**POST `/api/v1/mini-program/auth/login`**

```json
// Request
{
    "platform": "douyin",
    "code": "081cBcGa1xXBaA0kF3Ha1OYk5e4cBcGm",
    "nickname": "John",
    "avatar": "https://example.com/avatar.jpg"
}

// Response
{
    "success": true,
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": {
            "id": 123,
            "username": "dy_abc12345",
            "display_name": "John",
            "platform": "douyin",
            "platform_user_id": "ou_xxxx",
            "is_new_user": true
        }
    }
}
```

**POST `/api/v1/mini-program/chat/stream`**

```json
// Request
{
    "message": "What products do you offer?",
    "history": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you?"}
    ],
    "platform": "telegram"
}

// Response: SSE stream (text/event-stream)
data: {"type": "token", "content": "We"}
data: {"type": "token", "content": " offer"}
data: {"type": "token", "content": " various"}
...
data: {"type": "done", "reply": "We offer various AI-powered...", "retrievedKnowledge": [...]}
```

### 4.2 Site_builder Mini-App Generation API (New)

Prefix: `/admin/site-builder/mini-app/`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/generate` | Trigger mini-program generation | Admin JWT |
| `GET` | `/status/<task_id>` | Query generation status | Admin JWT |
| `GET` | `/download/<platform>/<task_id>` | Download generated package (.zip) | Admin JWT |
| `POST` | `/deploy/<platform>` | Deploy to social platform | Admin JWT |
| `GET` | `/platforms` | List available platforms and configs | Admin JWT |
| `PUT` | `/platforms/<platform>` | Update platform config | Admin JWT |

#### Request/Response Examples

**POST `/admin/site-builder/mini-app/generate`**

```json
// Request
{
    "platforms": ["douyin", "wechat", "telegram", "line"],
    "options": {
        "include_chat": true,
        "include_rag": true,
        "include_pages": ["home", "about"],
        "theme_color": "#1890ff",
        "app_name": "VeroRun AI"
    },
    "prompt_id": 1,
    "dev_account_id": 1
}

// Response
{
    "success": true,
    "data": {
        "task_id": "MA-20260713-A1B2C3D4",
        "platforms": {
            "douyin": {"status": "queued"},
            "wechat": {"status": "queued"},
            "telegram": {"status": "queued"},
            "line": {"status": "queued"}
        }
    }
}
```

### 4.3 Developer Account Management API (New)

Prefix: `/admin/dev-accounts/`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/` | List developer accounts | Admin JWT |
| `POST` | `/` | Add developer account | Admin JWT |
| `PUT` | `/<id>` | Update developer account | Admin JWT |
| `DELETE` | `/<id>` | Delete developer account | Admin JWT |
| `POST` | `/<id>/test` | Test connection | Admin JWT |

---

## 5. System SDK Design

### 5.1 Common Layer (`sdks/common/`)

```javascript
// sdks/common/chat.js
class VeroChat {
    /**
     * @param {Object} config
     * @param {string} config.baseURL  - System base URL (e.g., 'https://easykai.cn')
     * @param {string} config.token    - JWT token from auth
     * @param {string} config.platform - 'douyin' | 'wechat' | 'telegram' | 'line'
     */
    constructor(config) {
        this.baseURL = config.baseURL;
        this.token = config.token;
        this.platform = config.platform;
    }

    /**
     * Send message (non-streaming)
     * @param {string} message
     * @param {Array} history - Previous messages [{role, content}]
     * @returns {Promise<Object>} {success, data: {reply, retrievedKnowledge}}
     */
    async send(message, history = []) {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/chat/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({ message, history, platform: this.platform })
        });
        return res.json();
    }

    /**
     * Streaming chat via SSE
     * @param {string} message
     * @param {Array} history
     * @param {Function} onToken - Callback for each token
     * @param {Function} onDone - Callback when stream completes
     */
    async streamChat(message, history = [], onToken, onDone) {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({ message, history, platform: this.platform })
        });
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullReply = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    if (data.type === 'token') {
                        fullReply += data.content;
                        onToken && onToken(data.content);
                    } else if (data.type === 'done') {
                        onDone && onDone({ reply: fullReply, retrievedKnowledge: data.retrievedKnowledge });
                    }
                }
            }
        }
    }

    /**
     * Search RAG knowledge base
     * @param {string} query
     * @returns {Promise<Object>}
     */
    async searchKnowledge(query) {
        const res = await fetch(
            `${this.baseURL}/api/v1/mini-program/knowledge/search?q=${encodeURIComponent(query)}`,
            { headers: { 'Authorization': `Bearer ${this.token}` } }
        );
        return res.json();
    }
}

// sdks/common/auth.js
class VeroAuth {
    /**
     * @param {Object} config
     * @param {string} config.baseURL
     * @param {string} config.platform
     */
    constructor(config) {
        this.baseURL = config.baseURL;
        this.platform = config.platform;
    }

    /**
     * Login with platform credentials
     * @param {Object} credentials - Platform-specific credentials
     * @returns {Promise<Object>} {token, user}
     */
    async login(credentials) {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...credentials, platform: this.platform })
        });
        return res.json();
    }
}

// sdks/common/rag.js
class VeroRAG {
    /**
     * @param {Object} config
     * @param {string} config.baseURL
     * @param {string} config.token
     */
    constructor(config) {
        this.baseURL = config.baseURL;
        this.token = config.token;
    }

    /**
     * Search knowledge base
     * @param {string} query
     * @param {number} topK
     * @param {string} category
     * @returns {Promise<Array>}
     */
    async search(query, topK = 5, category = null) {
        const params = new URLSearchParams({ q: query, topK: String(topK) });
        if (category) params.set('category', category);
        const res = await fetch(
            `${this.baseURL}/api/v1/mini-program/knowledge/search?${params}`,
            { headers: { 'Authorization': `Bearer ${this.token}` } }
        );
        return res.json();
    }
}
```

### 5.2 Douyin SDK (`sdks/douyin/api.js`)

```javascript
// sdks/douyin/api.js
const DouyinMP = {
    baseURL: 'https://easykai.cn',
    token: null,

    /**
     * Initialize and login
     * Calls tt.login() → exchanges code for JWT
     */
    async init() {
        const { code } = await this._promisify(tt.login)();
        const res = await this.request('/api/v1/mini-program/auth/login', {
            method: 'POST',
            data: { code, platform: 'douyin' }
        });
        if (res.success) {
            this.token = res.data.token;
            // Store token in tt storage
            tt.setStorageSync('vero_token', this.token);
        }
        return res;
    },

    /**
     * Restore token from storage
     */
    restoreToken() {
        this.token = tt.getStorageSync('vero_token') || null;
        return !!this.token;
    },

    /**
     * Wrapper for tt.request()
     * @param {string} url
     * @param {Object} options
     * @returns {Promise<Object>}
     */
    request(url, options = {}) {
        return new Promise((resolve, reject) => {
            tt.request({
                url: `${this.baseURL}${url}`,
                method: options.method || 'GET',
                data: options.data,
                header: {
                    'Content-Type': 'application/json',
                    'Authorization': this.token ? `Bearer ${this.token}` : '',
                    ...options.header
                },
                success: (res) => resolve(res.data),
                fail: reject
            });
        });
    },

    /**
     * Get user profile
     * @returns {Promise<Object>}
     */
    async getUserProfile() {
        const res = await this.request('/api/v1/mini-program/user/profile');
        return res.data;
    },

    _promisify(fn) {
        return (options = {}) => new Promise((resolve, reject) => {
            fn({ ...options, success: resolve, fail: reject });
        });
    }
};

// Usage in mini-program page:
// const douyin = Object.create(DouyinMP);
// await douyin.init();
// const chat = new VeroChat({ baseURL: douyin.baseURL, token: douyin.token, platform: 'douyin' });
```

### 5.3 WeChat SDK (`sdks/wechat/api.js`)

```javascript
// sdks/wechat/api.js
const WechatMP = {
    baseURL: 'https://easykai.cn',
    token: null,

    async init() {
        const { code } = await this._promisify(wx.login)();
        const res = await this.request('/api/v1/mini-program/auth/login', {
            method: 'POST',
            data: { code, platform: 'wechat' }
        });
        if (res.success) {
            this.token = res.data.token;
            wx.setStorageSync('vero_token', this.token);
        }
        return res;
    },

    restoreToken() {
        this.token = wx.getStorageSync('vero_token') || null;
        return !!this.token;
    },

    request(url, options = {}) {
        return new Promise((resolve, reject) => {
            wx.request({
                url: `${this.baseURL}${url}`,
                method: options.method || 'GET',
                data: options.data,
                header: {
                    'Content-Type': 'application/json',
                    'Authorization': this.token ? `Bearer ${this.token}` : '',
                    ...options.header
                },
                success: (res) => resolve(res.data),
                fail: reject
            });
        });
    },

    _promisify(fn) {
        return (options = {}) => new Promise((resolve, reject) => {
            fn({ ...options, success: resolve, fail: reject });
        });
    }
};
```

### 5.4 Telegram Mini App SDK (`sdks/telegram/webapp.js`)

```javascript
// sdks/telegram/webapp.js
const TelegramMiniApp = {
    tg: null,
    baseURL: 'https://easykai.cn',
    token: null,
    user: null,

    /**
     * Initialize Telegram WebApp
     */
    init() {
        this.tg = window.Telegram.WebApp;
        this.tg.ready();
        this.tg.expand(); // Full screen
        this.user = this.tg.initDataUnsafe?.user;
        // Apply Telegram theme colors
        document.documentElement.style.setProperty('--tg-bg-color', this.tg.backgroundColor);
        document.documentElement.style.setProperty('--tg-text-color', this.tg.textColor);
        return this;
    },

    /**
     * Authenticate using Telegram initData
     */
    async authenticate() {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: 'telegram',
                initData: this.tg.initData
            })
        });
        const data = await res.json();
        if (data.success) {
            this.token = data.data.token;
            localStorage.setItem('vero_token', this.token);
        }
        return data;
    },

    restoreToken() {
        this.token = localStorage.getItem('vero_token') || null;
        return !!this.token;
    },

    /**
     * Show Telegram native popup
     */
    showPopup(message, callback) {
        this.tg.showPopup({ title: 'VeroRun AI', message }, callback);
    },

    /**
     * Show back button
     */
    showBackButton(callback) {
        this.tg.BackButton.show();
        this.tg.BackButton.onClick(callback);
    },

    hideBackButton() {
        this.tg.BackButton.hide();
    }
};
```

### 5.5 LINE MINI App SDK (`sdks/line/liff.js`)

```javascript
// sdks/line/liff.js
const LineMiniApp = {
    baseURL: 'https://easykai.cn',
    token: null,
    profile: null,

    /**
     * Initialize LIFF
     * @param {string} liffId - LIFF ID from LINE Developers Console
     */
    async init(liffId) {
        await liff.init({ liffId, withLoginOnExternalBrowser: true });
        if (!liff.isLoggedIn()) {
            liff.login();
        }
        this.token = liff.getAccessToken();
        this.profile = await liff.getProfile();
        return this;
    },

    /**
     * Authenticate with system backend
     */
    async authenticate() {
        const res = await fetch(`${this.baseURL}/api/v1/mini-program/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: 'line',
                accessToken: this.token,
                userId: this.profile.userId
            })
        });
        const data = await res.json();
        if (data.success) {
            this.token = data.data.token; // Replace with system JWT
            localStorage.setItem('vero_token', this.token);
        }
        return data;
    },

    restoreToken() {
        this.token = localStorage.getItem('vero_token') || null;
        return !!this.token;
    },

    /**
     * Send message via LINE Messaging API (from backend)
     * Frontend sends request to our backend, which calls LINE API
     */
    async sendMessage(text) {
        // Handled by backend webhook
    },

    /**
     * Close LIFF app
     */
    close() {
        liff.closeWindow();
    }
};
```

---

## 6. Plugin Standard Update

### 6.1 New Section: Social Media Mini-Program Plugin Standard

Add to `docs/plugin-system.md`:

#### Directory Structure for Mini-Program Plugins

```
plugins/your_mini_program/
├── __init__.py              # BasePlugin subclass
├── plugin.json              # Metadata (with platforms field)
├── manifest.json            # Mini-program manifest (target platforms, permissions)
├── sdks/                    # Platform-specific SDK wrappers
│   ├── douyin/
│   ├── wechat/
│   ├── telegram/
│   └── line/
├── templates/               # Mini-program page templates
│   ├── chat.html            # AI chat page
│   ├── home.html            # Home page
│   └── profile.html         # User profile page
├── routes.py                # Backend API routes
├── deploy.py                # Deployment scripts
└── i18n/                    # Plugin translations
    ├── zh-CN.yml
    └── en.yml
```

#### New `plugin.json` Fields

```json
{
    "name": "my_mini_program",
    "identifier": "my_mini_program",
    "version": "1.0.0",
    "category": "mini_program",
    "platforms": ["douyin", "wechat", "telegram", "line"],
    "mini_app": {
        "entry_page": "chat.html",
        "permissions": ["chat", "knowledge_search", "user_profile"],
        "theme": {
            "primary_color": "#1890ff",
            "mode": "auto"
        },
        "features": {
            "ai_chat": true,
            "rag_search": true,
            "user_auth": true,
            "push_notifications": false
        }
    }
}
```

#### New Method: `register_mini_apps()`

```python
class BasePlugin:
    def register_mini_apps(self) -> Dict[str, Any]:
        """Return mini-program manifests generated by this plugin

        Returns:
            {
                "douyin": {
                    "app_id": "ttxxxxxxxx",
                    "app_name": "VeroRun AI",
                    "pages": ["chat", "home", "profile"],
                    "output_dir": "dist/douyin/",
                    "permissions": ["chat", "knowledge_search"]
                },
                "wechat": {...},
                "telegram": {...},
                "line": {...}
            }
        """
        return {}
```

---

## 7. AI Advisor Integration

### 7.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Social Media User                         │
│  Douyin │ WeChat │ Telegram │ LINE                          │
└────────┬──────────┬──────────┬──────────┬───────────────────┘
         │          │          │          │
         ▼          ▼          ▼          ▼
   ┌──────────────────────────────────────────────────┐
   │            Platform Mini-Program                  │
   │  ┌────────────────────────────────────────────┐  │
   │  │         sdks/common/chat.js                 │  │
   │  │         VeroChat class                      │  │
   │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
   │  │  │  auth.js │  │  rag.js  │  │ chat.js  │  │  │
   │  │  └──────────┘  └──────────┘  └──────────┘  │  │
   │  └────────────────────────────────────────────┘  │
   └──────────────────────┬───────────────────────────┘
                          │ HTTPS
                          ▼
   ┌──────────────────────────────────────────────────┐
   │              System Backend API                   │
   │  /api/v1/mini-program/auth/login                 │
   │  /api/v1/mini-program/chat/stream                │
   │  /api/v1/mini-program/knowledge/search           │
   └──────────────────────┬───────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌──────────────┐
   │  AIEngine  │  │  RAG       │  │  Intent       │
   │  (agent_   │  │  Search    │  │  Router       │
   │   matrix)  │  │  (_rag_    │  │  (_route_     │
   │            │  │   search)  │  │   agent_by_   │
   │  DashScope │  │            │  │   intent)     │
   │  Qwen      │  │  knowledge │  │               │
   │            │  │  _blocks   │  │  agent_matrix │
   └────────────┘  └────────────┘  └──────────────┘
```

### 7.2 Authentication Bridge

| Platform | Platform Auth | → | System JWT |
|----------|--------------|---|------------|
| Douyin | `tt.login()` → `code` | → | `POST /douyin_mp/login/code` → JWT |
| WeChat | `wx.login()` → `code` | → | `POST /api/v1/mini-program/auth/login` → JWT |
| Telegram | `initData` (HMAC-signed) | → | `POST /api/v1/mini-program/auth/login` → JWT |
| LINE | `liff.getAccessToken()` | → | `POST /api/v1/mini-program/auth/login` → JWT |

### 7.3 Chat Bridge

All platforms route through the same backend endpoint:

```python
# New route in platform/routes/api_v1.py or a new blueprint
@mini_program_bp.route('/chat/stream', methods=['POST'])
def mini_program_chat_stream():
    """Unified streaming chat for all mini-program platforms"""
    data = request.get_json() or {}
    message = data.get('message', '')
    history = data.get('history', [])
    platform = data.get('platform', 'website')
    user_id = get_current_user_id_from_token()

    # RAG knowledge retrieval
    knowledge = _rag_search(message, top_k=5)
    rag_context = _build_rag_context(knowledge)

    # Intent classification
    intent, sentiment = classify_intent(message)

    # Get chatbot agent config
    cfg = _get_chatbot_config()
    agent = _route_agent_by_intent(intent) or _get_chatbot_agent(cfg.get('agent_id', 'kai_assistant'))

    # Build system prompt with RAG context
    system_prompt = agent['system_prompt'] if agent else ''
    if rag_context:
        system_prompt += f'\n\n{rag_context}'

    engine = AIEngine({
        'provider': agent.get('provider', cfg.get('provider', 'dashscope')),
        'model_name': agent.get('model_name', cfg.get('model_name', 'qwen-turbo')),
        'system_prompt': system_prompt
    })

    def generate():
        full_reply = ''
        for token in engine.chat_stream([
            {'role': 'system', 'content': system_prompt},
            *history[-int(cfg.get('max_history', 20)):],
            {'role': 'user', 'content': message[:1000]}
        ]):
            full_reply += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'reply': full_reply, 'retrievedKnowledge': knowledge})}\n\n"

        # Log session asynchronously
        threading.Thread(target=log_session, args=(session_id,), kwargs={
            'user_query': message, 'ai_reply': full_reply,
            'source': platform, 'intent': intent, 'sentiment': sentiment
        }).start()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
```

### 7.4 Multi-Channel Conversation Management

Extend existing `chat_messages` table:

```sql
-- Add platform tracking to chat_messages
ALTER TABLE chat_messages ADD COLUMN platform TEXT DEFAULT 'website';
ALTER TABLE chat_messages ADD COLUMN platform_user_id TEXT DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_chat_platform ON chat_messages(platform, platform_user_id);
```

### 7.5 Chat UI Component

```html
<!-- sdks/common/chat-widget.html -->
<div class="vero-chat-widget" id="chatWidget">
    <div class="chat-header">
        <span class="chat-title">AI Advisor</span>
        <span class="chat-subtitle">Powered by VeroRun AI</span>
    </div>
    <div class="chat-messages" id="chatMessages"></div>
    <div class="chat-input-area">
        <input type="text" id="chatInput" placeholder="Type your question..." />
        <button id="sendBtn">Send</button>
    </div>
</div>

<script>
(async function() {
    // Initialize based on platform
    const platform = detectPlatform(); // 'douyin' | 'wechat' | 'telegram' | 'line'
    const auth = new VeroAuth({ baseURL: 'https://easykai.cn', platform });
    const { token } = await auth.login(getPlatformCredentials(platform));
    const chat = new VeroChat({ baseURL: 'https://easykai.cn', token, platform });

    document.getElementById('sendBtn').addEventListener('click', async () => {
        const input = document.getElementById('chatInput');
        const text = input.value.trim();
        if (!text) return;
        appendMessage('user', text);
        input.value = '';

        const msgEl = appendMessage('assistant', '');
        await chat.streamChat(text, getHistory(),
            (token) => { msgEl.textContent += token; },
            (result) => { console.log('Done:', result.retrievedKnowledge); }
        );
    });
})();
</script>
```

---

## 8. Site_builder Mini-Program Generation

### 8.1 Core Concept

Add a 6th phase to the existing Site_builder DAG:

```
Existing: Parse → Plan → Execute (Brand → Theme → Nav → Pages → Docs)
New:      Parse → Plan → Execute (Brand → Theme → Nav → Pages → Docs) → MiniApp
```

### 8.2 Module Structure

```
site_builder/
├── mini_app/                          # New: mini-program generation module
│   ├── __init__.py
│   ├── engine.py                      # MiniAppEngine — core generation engine
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseMiniAppGenerator
│   │   ├── douyin.py                  # DouyinGenerator (also covers Toutiao)
│   │   ├── wechat.py                  # WechatGenerator
│   │   ├── telegram.py                # TelegramGenerator
│   │   └── line.py                    # LINEGenerator
│   ├── templates/                     # Mini-program project templates
│   │   ├── douyin/                    # Douyin mini-program template
│   │   │   ├── app.js                 # App entry (tt.* API init)
│   │   │   ├── app.json               # App config (pages, window, etc.)
│   │   │   ├── app.ttss               # Global styles
│   │   │   ├── pages/
│   │   │   │   ├── chat/              # AI chat page
│   │   │   │   │   ├── chat.js
│   │   │   │   │   ├── chat.ttml
│   │   │   │   │   └── chat.ttss
│   │   │   │   ├── home/              # Home page (from site content)
│   │   │   │   │   ├── home.js
│   │   │   │   │   ├── home.ttml
│   │   │   │   │   └── home.ttss
│   │   │   │   └── profile/           # User profile page
│   │   │   │       ├── profile.js
│   │   │   │       ├── profile.ttml
│   │   │   │       └── profile.ttss
│   │   │   ├── components/            # Reusable components
│   │   │   │   └── chat-widget/       # Chat widget component
│   │   │   └── project.config.json    # Douyin project config
│   │   ├── wechat/                    # WeChat mini-program template
│   │   │   ├── app.js
│   │   │   ├── app.json
│   │   │   ├── app.wxss
│   │   │   ├── pages/
│   │   │   │   ├── chat/
│   │   │   │   ├── home/
│   │   │   │   └── profile/
│   │   │   ├── components/
│   │   │   └── project.config.json
│   │   ├── telegram/                  # Telegram Mini App template
│   │   │   ├── index.html             # Main entry (H5)
│   │   │   ├── chat.html              # Chat page
│   │   │   ├── css/
│   │   │   │   └── style.css
│   │   │   ├── js/
│   │   │   │   └── app.js
│   │   │   └── manifest.json
│   │   └── line/                      # LINE MINI App template
│   │       ├── index.html
│   │       ├── chat.html
│   │       ├── css/
│   │       │   └── style.css
│   │       ├── js/
│   │       │   └── app.js
│   │       └── manifest.json
│   ├── packager.py                    # Packager (generate .zip download)
│   └── deployer.py                    # Deployer (push to platforms)
```

### 8.3 MiniAppEngine

```python
# site_builder/mini_app/engine.py
#!/usr/bin/env python3
"""MiniAppEngine — Generate social media mini-programs from Site_builder output"""

import os, json, logging
from datetime import datetime
import secrets

logger = logging.getLogger(__name__)


class MiniAppEngine:
    """Core engine for generating mini-programs across platforms"""

    def __init__(self, site_config=None, brand_settings=None):
        self.site_config = site_config or {}
        self.brand = brand_settings or {}

    def generate(self, platforms: list, options: dict = None) -> dict:
        """Generate mini-programs for specified platforms

        Args:
            platforms: ['douyin', 'wechat', 'telegram', 'line']
            options: {
                'include_chat': True,
                'include_rag': True,
                'include_pages': ['home', 'about'],
                'theme_color': '#1890ff',
                'app_name': 'VeroRun AI',
                'app_id': {'douyin': 'ttxxx', 'wechat': 'wxxxxx'},
                'dev_account_id': 1,
            }

        Returns:
            {
                'douyin': {'status': 'completed', 'output_dir': 'dist/douyin/', 'files': [...]},
                'telegram': {'status': 'completed', 'output_dir': 'dist/telegram/', 'files': [...]},
                ...
            }
        """
        options = options or {}
        results = {}

        for platform in platforms:
            try:
                generator = self._get_generator(platform)
                result = generator.generate(self.site_config, self.brand, options)
                results[platform] = {'status': 'completed', **result}
            except Exception as e:
                logger.error(f'[{platform}] Generation failed: {e}')
                results[platform] = {'status': 'failed', 'error': str(e)}

        return results

    def _get_generator(self, platform: str):
        """Get platform-specific generator instance"""
        from site_builder.mini_app.generators.douyin import DouyinGenerator
        from site_builder.mini_app.generators.wechat import WechatGenerator
        from site_builder.mini_app.generators.telegram import TelegramGenerator
        from site_builder.mini_app.generators.line import LINEGenerator

        generators = {
            'douyin': DouyinGenerator,
            'toutiao': DouyinGenerator,  # Toutiao shares Douyin ecosystem
            'wechat': WechatGenerator,
            'telegram': TelegramGenerator,
            'line': LINEGenerator,
        }
        generator_cls = generators.get(platform)
        if not generator_cls:
            raise ValueError(f'Unsupported platform: {platform}')
        return generator_cls()
```

### 8.4 Base Generator

```python
# site_builder/mini_app/generators/base.py
#!/usr/bin/env python3
"""Base class for mini-program generators"""

import os, json, shutil
from abc import ABC, abstractmethod


class BaseMiniAppGenerator(ABC):
    """Abstract base for platform-specific mini-program generators"""

    platform: str = ''          # 'douyin' | 'wechat' | 'telegram' | 'line'
    template_dir: str = ''      # Path to template directory
    output_base: str = 'dist'   # Base output directory

    @abstractmethod
    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        """Generate mini-program files

        Returns:
            {'output_dir': 'dist/douyin/', 'files': ['app.js', 'pages/chat/chat.js', ...]}
        """
        pass

    def _copy_template(self, output_dir: str):
        """Copy template files to output directory"""
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        shutil.copytree(self.template_dir, output_dir)

    def _render_template(self, template_path: str, context: dict) -> str:
        """Render a template file with Jinja2-style variable substitution"""
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for key, value in context.items():
            placeholder = f'{{{{ {key} }}}}'
            content = content.replace(placeholder, str(value))
        return content

    def _write_file(self, path: str, content: str):
        """Write content to file, creating directories as needed"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def _get_brand_context(self, brand: dict) -> dict:
        """Extract brand context from brand settings"""
        return {
            'app_name': brand.get('site_name', 'VeroRun AI'),
            'tagline': brand.get('tagline', ''),
            'primary_color': brand.get('primary_color', '#1890ff'),
            'logo_url': brand.get('logo_url', ''),
            'brand_story': brand.get('brand_story', ''),
        }

    def _get_api_context(self, options: dict) -> dict:
        """Extract API context from options"""
        return {
            'base_url': options.get('base_url', 'https://easykai.cn'),
            'api_prefix': '/api/v1/mini-program',
            'platform': self.platform,
        }
```

### 8.5 Douyin Generator

```python
# site_builder/mini_app/generators/douyin.py
#!/usr/bin/env python3
"""Douyin/Toutiao Mini-Program Generator"""

import os, json
from .base import BaseMiniAppGenerator


class DouyinGenerator(BaseMiniAppGenerator):
    platform = 'douyin'
    template_dir = os.path.join(os.path.dirname(__file__), '..', 'templates', 'douyin')

    def generate(self, site_config: dict, brand: dict, options: dict) -> dict:
        output_dir = os.path.join(self.output_base, 'douyin')
        self._copy_template(output_dir)

        brand_ctx = self._get_brand_context(brand)
        api_ctx = self._get_api_context(options)

        # Render app.json with page list
        pages = options.get('include_pages', ['home'])
        if options.get('include_chat', True):
            pages = ['chat'] + pages
        if options.get('include_profile', True):
            pages.append('profile')

        app_json = {
            'pages': [f'pages/{p}/{p}' for p in pages],
            'window': {
                'navigationBarBackgroundColor': brand_ctx['primary_color'],
                'navigationBarTitleText': brand_ctx['app_name'],
                'navigationBarTextStyle': 'white',
            },
        }
        self._write_file(
            os.path.join(output_dir, 'app.json'),
            json.dumps(app_json, ensure_ascii=False, indent=2)
        )

        # Render app.js with API initialization
        app_js_context = {
            **brand_ctx,
            **api_ctx,
            'app_id': options.get('app_id', {}).get('douyin', ''),
        }
        app_js = self._render_template(
            os.path.join(self.template_dir, 'app.js'),
            app_js_context
        )
        self._write_file(os.path.join(output_dir, 'app.js'), app_js)

        # Render project.config.json
        project_config = {
            'appid': options.get('app_id', {}).get('douyin', ''),
            'projectname': brand_ctx['app_name'],
            'setting': {
                'urlCheck': True,
                'es6': True,
            },
        }
        self._write_file(
            os.path.join(output_dir, 'project.config.json'),
            json.dumps(project_config, ensure_ascii=False, indent=2)
        )

        # Render each page
        for page in pages:
            page_dir = os.path.join(output_dir, 'pages', page)
            for ext in ['js', 'ttml', 'ttss']:
                template_path = os.path.join(self.template_dir, 'pages', page, f'{page}.{ext}')
                if os.path.exists(template_path):
                    content = self._render_template(template_path, {**brand_ctx, **api_ctx})
                    self._write_file(os.path.join(page_dir, f'{page}.{ext}'), content)

        # Collect file list
        files = []
        for root, _, filenames in os.walk(output_dir):
            for f in filenames:
                files.append(os.path.relpath(os.path.join(root, f), output_dir))

        return {
            'output_dir': output_dir,
            'files': files,
            'platform': 'douyin',
            'compatible_with': ['toutiao'],
        }
```

### 8.6 Packager & Deployer

```python
# site_builder/mini_app/packager.py
#!/usr/bin/env python3
"""Packager — Package generated mini-programs into .zip archives"""

import os, shutil, logging

logger = logging.getLogger(__name__)


class MiniAppPackager:
    """Package mini-program output directories into downloadable .zip files"""

    def __init__(self, output_base: str = 'dist'):
        self.output_base = output_base

    def package(self, platform: str, output_dir: str) -> str:
        """Package a platform's output into a .zip file

        Args:
            platform: 'douyin' | 'wechat' | 'telegram' | 'line'
            output_dir: Path to generated files

        Returns:
            Path to the .zip file
        """
        zip_name = f'{platform}_mini_program'
        zip_path = os.path.join(self.output_base, zip_name)
        archive_path = shutil.make_archive(zip_path, 'zip', output_dir)
        logger.info(f'[Packager] Created {archive_path}')
        return archive_path

    def package_all(self, results: dict) -> dict:
        """Package all platform results

        Returns:
            {'douyin': 'dist/douyin_mini_program.zip', ...}
        """
        packages = {}
        for platform, result in results.items():
            if result.get('status') == 'completed':
                packages[platform] = self.package(platform, result['output_dir'])
        return packages


# site_builder/mini_app/deployer.py
#!/usr/bin/env python3
"""Deployer — Deploy mini-programs to social media platforms"""

import json, logging, urllib.request as _ur

logger = logging.getLogger(__name__)


class MiniAppDeployer:
    """Deploy mini-programs to target platforms"""

    def __init__(self, dev_accounts: dict = None):
        """
        Args:
            dev_accounts: {platform: {app_id, app_secret, bot_token, ...}}
        """
        self.dev_accounts = dev_accounts or {}

    def deploy_telegram(self, webapp_url: str, bot_token: str = None) -> dict:
        """Set Telegram Mini App menu button via Bot API

        POST https://api.telegram.org/bot{token}/setChatMenuButton
        """
        token = bot_token or self.dev_accounts.get('telegram', {}).get('bot_token', '')
        if not token:
            return {'success': False, 'error': 'No bot_token configured'}

        try:
            payload = json.dumps({
                'menu_button': {
                    'type': 'web_app',
                    'text': 'Open App',
                    'web_app': {'url': webapp_url}
                }
            }).encode()
            req = _ur.Request(
                f'https://api.telegram.org/bot{token}/setChatMenuButton',
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            resp = json.loads(_ur.urlopen(req, timeout=10).read())
            return {'success': resp.get('ok', False), 'data': resp}
        except Exception as e:
            logger.error(f'[Deployer] Telegram deploy failed: {e}')
            return {'success': False, 'error': str(e)}

    def deploy_line(self, liff_id: str, endpoint_url: str, channel_token: str = None) -> dict:
        """Update LINE LIFF endpoint URL

        PUT https://api.line.me/liff/v1/apps/{liffId}
        """
        token = channel_token or self.dev_accounts.get('line', {}).get('access_token', '')
        if not token:
            return {'success': False, 'error': 'No channel access_token configured'}

        try:
            payload = json.dumps({
                'view': {
                    'type': 'tall',
                    'url': endpoint_url
                }
            }).encode()
            req = _ur.Request(
                f'https://api.line.me/liff/v1/apps/{liff_id}',
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                },
                method='PUT'
            )
            resp = json.loads(_ur.urlopen(req, timeout=10).read())
            return {'success': True, 'data': resp}
        except Exception as e:
            logger.error(f'[Deployer] LINE deploy failed: {e}')
            return {'success': False, 'error': str(e)}

    def get_manual_deploy_hint(self, platform: str) -> str:
        """Return manual deployment instructions for platforms that need IDE upload"""
        hints = {
            'douyin': (
                '1. Open ByteDance DevTools\n'
                '2. Import the dist/douyin/ directory\n'
                '3. Click "Upload" to submit for review\n'
                '4. Wait for review approval (1-3 business days)'
            ),
            'wechat': (
                '1. Open WeChat DevTools\n'
                '2. Import the dist/wechat/ directory\n'
                '3. Click "Upload" to submit for review\n'
                '4. Wait for review approval (1-7 business days)'
            ),
        }
        return hints.get(platform, 'Manual deployment required. See documentation.')
```

### 8.7 Routes Integration

```python
# New routes added to site_builder/routes.py

@site_builder_bp.route('/mini-app/generate', methods=['POST'])
def generate_mini_app():
    """Generate mini-program for specified platforms"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    platforms = data.get('platforms', [])
    options = data.get('options', {})

    if not platforms:
        return _error('No platforms specified')

    from site_builder.models import get_prompt as _get_prompt
    prompt_id = data.get('prompt_id', '')
    try:
        prompt_id = int(prompt_id)
        prompt_template = _get_prompt(prompt_id)
    except (ValueError, TypeError):
        prompt_template = _get_prompt(prompt_id) if prompt_id else None

    # Get draft site data
    from site_builder.site_settings.models import get_draft_tokens
    from services.brand_service import get_brand_settings

    draft_tokens = get_draft_tokens()
    brand = get_brand_settings()

    # Create task
    task_id = f"MA-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
    create_task(admin['user_id'], prompt_id or 0, json.dumps(platforms))

    try:
        from site_builder.mini_app.engine import MiniAppEngine
        engine = MiniAppEngine(
            site_config={'tokens': draft_tokens, 'prompt_template': prompt_template},
            brand_settings=brand,
        )
        results = engine.generate(platforms, options)

        # Package results
        from site_builder.mini_app.packager import MiniAppPackager
        packager = MiniAppPackager()
        packages = packager.package_all(results)

        return _success({
            'task_id': task_id,
            'results': results,
            'packages': packages,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _error(f'Generation failed: {e}', 500)
```

---

## 9. Developer Account Management Plugin

### 9.1 Data Model

```sql
CREATE TABLE IF NOT EXISTS dev_accounts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    platform         TEXT NOT NULL,          -- 'douyin' | 'wechat' | 'telegram' | 'line' | 'toutiao'
    account_name     TEXT NOT NULL,          -- Display name (e.g., "VeroRun Official")
    app_id           TEXT DEFAULT '',        -- Platform App ID
    app_secret       TEXT DEFAULT '',        -- Encrypted (AES-256)
    bot_token        TEXT DEFAULT '',        -- Telegram Bot Token (encrypted)
    channel_id       TEXT DEFAULT '',        -- LINE Channel ID
    channel_secret   TEXT DEFAULT '',        -- LINE Channel Secret (encrypted)
    access_token     TEXT DEFAULT '',        -- Access token (encrypted)
    extra_config     TEXT DEFAULT '{}',      -- Extra JSON config
    is_active        INTEGER DEFAULT 1,
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_dev_accounts_platform ON dev_accounts(platform);
```

### 9.2 Plugin Structure

```
plugins/dev_accounts/
├── __init__.py          # DevAccountsPlugin (BasePlugin subclass)
├── plugin.json
├── routes.py            # CRUD API endpoints
├── models.py            # Data access layer
└── crypto.py            # AES-256 encryption for sensitive fields
```

### 9.3 Encryption

```python
# plugins/dev_accounts/crypto.py
#!/usr/bin/env python3
"""AES-256 encryption for developer account credentials"""

import os, hashlib, base64
from cryptography.fernet import Fernet


def _get_encryption_key() -> bytes:
    """Derive Fernet key from environment variable"""
    raw_key = os.environ.get('DEV_ACCOUNTS_ENCRYPTION_KEY', '')
    if not raw_key:
        # Generate a deterministic fallback key (NOT for production)
        raw_key = 'vero_run_dev_accounts_default_key_2026'
    key_bytes = hashlib.sha256(raw_key.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)


_cipher = Fernet(_get_encryption_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a string value"""
    if not plaintext:
        return ''
    return _cipher.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a string value"""
    if not ciphertext:
        return ''
    return _cipher.decrypt(ciphertext.encode()).decode()


def mask(value: str, show_first: int = 4, show_last: int = 4) -> str:
    """Mask a sensitive value for display"""
    if not value or len(value) <= show_first + show_last:
        return '****'
    return value[:show_first] + '****' + value[-show_last:]
```

### 9.4 Plugin Registration

```python
# plugins/dev_accounts/__init__.py
#!/usr/bin/env python3
"""Developer Account Management Plugin"""

from plugin_manager.base import BasePlugin


class DevAccountsPlugin(BasePlugin):
    name = 'Developer Accounts'
    identifier = 'dev_accounts'
    version = '1.0.0'
    description = 'Manage developer accounts for social media platforms'
    author = 'VeroRun'

    def setup(self):
        super().setup()
        from .routes import dev_accounts_bp
        self.app.register_blueprint(dev_accounts_bp, url_prefix='/admin/dev-accounts')

    def on_install(self, registry=None) -> bool:
        self._ensure_table()
        return True

    def _ensure_table(self):
        from models import get_db
        with get_db() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS dev_accounts (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform         TEXT NOT NULL,
                    account_name     TEXT NOT NULL,
                    app_id           TEXT DEFAULT '',
                    app_secret       TEXT DEFAULT '',
                    bot_token        TEXT DEFAULT '',
                    channel_id       TEXT DEFAULT '',
                    channel_secret   TEXT DEFAULT '',
                    access_token     TEXT DEFAULT '',
                    extra_config     TEXT DEFAULT '{}',
                    is_active        INTEGER DEFAULT 1,
                    created_at       TEXT DEFAULT (datetime('now')),
                    updated_at       TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_dev_accounts_platform ON dev_accounts(platform);
            """)
            conn.commit()
```

---

## 10. Site_builder Preview Enhancement

### 10.1 Device Simulator

Add a device simulator to the existing preview page at `/admin/site-builder/preview-site`.

**Supported Devices**:
- iPhone 15 Pro (393 × 852)
- iPhone 15 (390 × 844)
- iPhone 14 Pro Max (430 × 932)
- iPhone SE (375 × 667)
- iPad Mini (768 × 1024)
- Desktop H5 (responsive)

**Preview Toolbar**:
```html
<div class="preview-toolbar">
    <select id="deviceSelector">
        <option value="h5">Desktop H5</option>
        <option value="iphone15pro">iPhone 15 Pro (393×852)</option>
        <option value="iphone15">iPhone 15 (390×844)</option>
        <option value="iphone14pro">iPhone 14 Pro Max (430×932)</option>
        <option value="iphoneSE">iPhone SE (375×667)</option>
        <option value="ipad">iPad Mini (768×1024)</option>
    </select>
    <button id="rotateDevice" title="Rotate">↻</button>
</div>
```

**Device Frame CSS** (pure CSS iPhone shell):
```css
.device-frame {
    display: flex;
    justify-content: center;
    align-items: center;
    background: #f0f0f0;
    border-radius: 40px;
    padding: 12px;
    box-shadow: 0 0 20px rgba(0,0,0,0.15);
    position: relative;
    margin: 20px auto;
    transition: all 0.3s ease;
}

.device-frame.iphone15pro {
    width: 423px;
    height: 882px;
}

.device-frame .notch {
    position: absolute;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    width: 120px;
    height: 30px;
    background: #000;
    border-radius: 0 0 20px 20px;
}

.device-frame .home-bar {
    position: absolute;
    bottom: 8px;
    left: 50%;
    transform: translateX(-50%);
    width: 134px;
    height: 5px;
    background: #333;
    border-radius: 100px;
}

.device-frame iframe {
    width: 100%;
    height: 100%;
    border: none;
    border-radius: 28px;
}
```

### 10.2 Files to Modify

| File | Change |
|------|--------|
| `site_builder/routes.py` | Add mobile render mode to `/preview-site` |
| `admin/templates/ai_site_preview.html` | Add device selector and frame |
| `admin/static/css/preview.css` | Add device simulator styles (new file) |

---

## 11. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

| # | Task | Output | Dependencies |
|---|------|--------|-------------|
| 1.1 | Create `sdks/` directory structure | Directory layout | None |
| 1.2 | Implement `sdks/common/chat.js` (VeroChat class) | `sdks/common/chat.js` | None |
| 1.3 | Implement `sdks/common/auth.js` (VeroAuth class) | `sdks/common/auth.js` | None |
| 1.4 | Implement `sdks/common/rag.js` (VeroRAG class) | `sdks/common/rag.js` | None |
| 1.5 | Create `/api/v1/mini-program/` blueprint + routes | `platform/routes/mini_program.py` | 1.2, 1.3 |
| 1.6 | Add `platform` + `platform_user_id` columns to `chat_messages` | DB migration | None |
| 1.7 | Create `dev_accounts` plugin skeleton | `plugins/dev_accounts/` | None |
| 1.8 | Implement `dev_accounts` CRUD routes + encryption | `plugins/dev_accounts/` | 1.7 |

### Phase 2: Platform SDKs (Week 2-3)

| # | Task | Output | Dependencies |
|---|------|--------|-------------|
| 2.1 | Implement `sdks/douyin/api.js` | `sdks/douyin/api.js` | 1.2 |
| 2.2 | Implement `sdks/wechat/api.js` | `sdks/wechat/api.js` | 1.2 |
| 2.3 | Implement `sdks/telegram/webapp.js` | `sdks/telegram/webapp.js` | 1.2 |
| 2.4 | Implement `sdks/telegram/bot.js` | `sdks/telegram/bot.js` | 1.2 |
| 2.5 | Implement `sdks/line/liff.js` | `sdks/line/liff.js` | 1.2 |
| 2.6 | Implement `sdks/line/messaging.js` | `sdks/line/messaging.js` | 1.2 |

### Phase 3: Site_builder Integration (Week 3-5)

| # | Task | Output | Dependencies |
|---|------|--------|-------------|
| 3.1 | Create `site_builder/mini_app/` module structure | Directory layout | None |
| 3.2 | Implement `BaseMiniAppGenerator` (base class) | `mini_app/generators/base.py` | 3.1 |
| 3.3 | Create Douyin template (`templates/douyin/`) | Template files | 2.1 |
| 3.4 | Implement `DouyinGenerator` | `mini_app/generators/douyin.py` | 3.2, 3.3 |
| 3.5 | Create WeChat template (`templates/wechat/`) | Template files | 2.2 |
| 3.6 | Implement `WechatGenerator` | `mini_app/generators/wechat.py` | 3.2, 3.5 |
| 3.7 | Create Telegram template (`templates/telegram/`) | Template files | 2.3 |
| 3.8 | Implement `TelegramGenerator` | `mini_app/generators/telegram.py` | 3.2, 3.7 |
| 3.9 | Create LINE template (`templates/line/`) | Template files | 2.5 |
| 3.10 | Implement `LINEGenerator` | `mini_app/generators/line.py` | 3.2, 3.9 |
| 3.11 | Implement `MiniAppEngine` | `mini_app/engine.py` | 3.4, 3.6, 3.8, 3.10 |
| 3.12 | Implement `MiniAppPackager` | `mini_app/packager.py` | 3.11 |
| 3.13 | Implement `MiniAppDeployer` | `mini_app/deployer.py` | 3.11 |
| 3.14 | Add mini-app routes to `site_builder/routes.py` | Routes | 3.11, 3.12, 3.13 |

### Phase 4: Preview & Testing (Week 5-6)

| # | Task | Output | Dependencies |
|---|------|--------|-------------|
| 4.1 | Add device simulator CSS | `admin/static/css/preview.css` | None |
| 4.2 | Update `ai_site_preview.html` with device selector | Template update | 4.1 |
| 4.3 | E2E test: Douyin generation → preview → package | Test report | 3.4 |
| 4.4 | E2E test: WeChat generation → preview → package | Test report | 3.6 |
| 4.5 | E2E test: Telegram generation → deploy → test | Test report | 3.8 |
| 4.6 | E2E test: LINE generation → deploy → test | Test report | 3.10 |

### Phase 5: Documentation (Week 6)

| # | Task | Output | Dependencies |
|---|------|--------|-------------|
| 5.1 | Update `docs/plugin-system.md` with mini-program section | Doc update | 3.11 |
| 5.2 | Write `docs/ai-advisor-integration.md` | New doc | 1.5 |
| 5.3 | Write `docs/sdk-reference.md` (update existing) | Doc update | 2.1-2.6 |
| 5.4 | Write `docs/mini-program-deployment.md` | New doc | 3.13 |

---

## 12. Risks & Considerations

### 12.1 Platform Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Douyin/WeChat require enterprise verification | Cannot create mini-program without it | Prepare enterprise credentials in advance |
| WeChat mini-program review takes 1-7 days | Delayed launch | Submit early, plan buffer time |
| LINE MINI App restricted to JP/TW/TH/ID regions | Limited audience | Prioritize for target markets |
| Telegram Mini App no review | Fast iteration but content risk | Implement content moderation |
| API rate limits vary by platform | Service disruption | Implement request queue + retry with backoff |

### 12.2 Security

- All platform credentials (`app_secret`, `bot_token`, `channel_secret`, `access_token`) must be encrypted with AES-256
- Encryption key from environment variable `DEV_ACCOUNTS_ENCRYPTION_KEY`
- API responses automatically mask sensitive fields (show first 4 + last 4 characters)
- All dev account operations logged to audit trail

### 12.3 Technical Constraints

- `Gunicorn --preload` must not be used with SQLite (existing constraint)
- Mini-program generation may be CPU-intensive; consider async task queue
- Telegram/LINE Mini Apps are deployed as static HTML pages; must be hosted on public HTTPS URL
- Douyin/WeChat mini-programs need platform-specific IDE for final upload

---

> **Next Steps**: Confirm this plan, then proceed with Phase 1 implementation.