# Social Media Mini-Program — Detailed Implementation Plan

> Version: v1.0 | Date: 2026-07-13 | Status: Confirmed  
> System: VeroRun / easykai.cn  
> Based on: [docs/social-mini-program-plan.md](social-mini-program-plan.md)

---

## Table of Contents

1. [Prerequisites & Environment](#1-prerequisites--environment)
2. [Phase 0: Preparation](#2-phase-0-preparation)
3. [Phase 1: Foundation — SDK & API (Week 1-2)](#3-phase-1-foundation--sdk--api)
4. [Phase 2: Platform SDKs (Week 2-3)](#4-phase-2-platform-sdks)
5. [Phase 3: Site_builder Integration (Week 3-5)](#5-phase-3-site_builder-integration)
6. [Phase 4: Preview & Testing (Week 5-6)](#6-phase-4-preview--testing)
7. [Phase 5: Documentation & Deployment (Week 6)](#7-phase-5-documentation--deployment)
8. [DB Migration Details](#8-db-migration-details)
9. [Environment Variables](#9-environment-variables)
10. [Verification Checklist](#10-verification-checklist)

---

## 1. Prerequisites & Environment

### 1.1 System Requirements

| Component | Version / Value |
|-----------|----------------|
| Python | 3.10+ |
| Flask | `platform/app.py` existing version |
| SQLite | Existing `easykai.db` |
| Gunicorn | Existing (without `--preload`) |
| Nginx | `/etc/nginx/sites-enabled/easykai.conf` |

### 1.2 Platform Accounts Required (Before Development)

| Platform | What You Need | Status |
|----------|--------------|--------|
| Douyin | Enterprise mini-program account (`app_id`, `app_secret`) | To be created |
| WeChat | Enterprise mini-program account (`app_id`, `app_secret`) | To be created |
| Telegram | Bot token from [@BotFather](https://t.me/BotFather) | Existing |
| LINE | LINE Developers account (`channel_id`, `channel_secret`, LIFF ID) | Existing |

### 1.3 Python Dependencies to Add

```
cryptography>=41.0.0    # AES-256 encryption for dev_accounts crypto.py
```

### 1.4 Existing Code to Reference

| Module | Path | Used For |
|--------|------|----------|
| `SiteBuilderEngine` | `site_builder/engine.py` | DAG flow pattern, `_call_llm()`, `AIEngine` usage |
| `AIEngine` | `agent_matrix/engine.py` | `chat_stream()` for AI chat bridge |
| `_rag_search()` | `platform/routes/api_v1.py` | RAG knowledge retrieval |
| `_get_chatbot_config()` | `platform/routes/api_v1.py` | Chatbot agent config |
| `channel_router` | `plugins/chatbot/channels/router.py` | Multi-channel webhook pattern |
| `BasePlugin` | `plugins/base.py` | Plugin registration pattern |
| `get_draft_tokens()` | `site_builder/site_settings/models.py` | Site draft tokens |
| `get_brand_settings()` | `services/brand_service.py` | Brand settings |
| `douyin_miniprogram.py` | `auth-center/routes/douyin_miniprogram.py` | Existing Douyin login flow |

---

## 2. Phase 0: Preparation

### 2.0.1 Git Commit Before Starting

```bash
cd /home/easykai/easykai-workspace/easykai.cn/
git add -A
git status
git commit -m "pre: snapshot before social mini-program implementation"
```

### 2.0.2 Directory Structure to Create

```
/home/easykai/easykai-workspace/easykai.cn/
├── sdks/
│   ├── common/
│   ├── douyin/
│   │   └── components/
│   ├── wechat/
│   │   └── components/
│   ├── telegram/
│   └── line/
├── site_builder/
│   └── mini_app/
│       ├── generators/
│       └── templates/
│           ├── douyin/
│           │   ├── pages/
│           │   │   ├── chat/
│           │   │   ├── home/
│           │   │   └── profile/
│           │   └── components/
│           │       └── chat-widget/
│           ├── wechat/
│           │   ├── pages/
│           │   │   ├── chat/
│           │   │   ├── home/
│           │   │   └── profile/
│           │   └── components/
│           │       └── chat-widget/
│           ├── telegram/
│           │   ├── css/
│           │   └── js/
│           └── line/
│               ├── css/
│               └── js/
└── plugins/
    └── dev_accounts/
```

---

## 3. Phase 1: Foundation — SDK & API

### Task 1.1: Create `sdks/` Directory Structure

**Description**: Create the SDK directory layout with empty `__init__` placeholders.

**Files to create**:
- `sdks/__init__` (empty dir marker)
- `sdks/common/__init__` (empty dir marker)
- `sdks/douyin/__init__` (empty dir marker)
- `sdks/wechat/__init__` (empty dir marker)
- `sdks/telegram/__init__` (empty dir marker)
- `sdks/line/__init__` (empty dir marker)

**Verification**: `ls sdks/` shows all 5 platform directories.

---

### Task 1.2: Implement `sdks/common/chat.js`

**Description**: Core `VeroChat` class with `send()`, `streamChat()`, `searchKnowledge()` methods.

**File**: `sdks/common/chat.js`

**Key methods**:
- `constructor(config)` — accepts `baseURL`, `token`, `platform`
- `async send(message, history)` — POST to `/api/v1/mini-program/chat/send`
- `async streamChat(message, history, onToken, onDone)` — SSE streaming to `/api/v1/mini-program/chat/stream`
- `async searchKnowledge(query)` — GET `/api/v1/mini-program/knowledge/search`

**Dependencies**: None (pure fetch-based).

**Verification**: Code review for correct SSE parsing, JWT header injection, and `platform` field passthrough.

---

### Task 1.3: Implement `sdks/common/auth.js`

**Description**: `VeroAuth` class for unified platform login.

**File**: `sdks/common/auth.js`

**Key methods**:
- `constructor(config)` — accepts `baseURL`, `platform`
- `async login(credentials)` — POST to `/api/v1/mini-program/auth/login`

**Dependencies**: None.

**Verification**: Code review for correct `platform` field passthrough.

---

### Task 1.4: Implement `sdks/common/rag.js`

**Description**: `VeroRAG` class for knowledge base search.

**File**: `sdks/common/rag.js`

**Key methods**:
- `constructor(config)` — accepts `baseURL`, `token`
- `async search(query, topK, category)` — GET `/api/v1/mini-program/knowledge/search`

**Dependencies**: None.

**Verification**: Code review.

---

### Task 1.5: Create `/api/v1/mini-program/` Backend Blueprint

**Description**: Create the Flask blueprint with all mini-program API endpoints.

**File**: `platform/routes/mini_program.py` (new file)

**Register in**: `platform/app.py` (add blueprint registration)

**Endpoints**:

```python
# platform/routes/mini_program.py
from flask import Blueprint, request, jsonify, Response, stream_with_context
from auth_utils import verify_token, get_user_id_from_token

mini_program_bp = Blueprint('mini_program', __name__, url_prefix='/api/v1/mini-program')


@mini_program_bp.route('/auth/login', methods=['POST'])
def mini_program_login():
    """
    Platform login → exchange code/token for system JWT
    
    Request body:
        {
            "platform": "douyin" | "wechat" | "telegram" | "line",
            "code": "..." (for douyin/wechat),
            "initData": "..." (for telegram),
            "accessToken": "..." (for line),
            "userId": "..." (for line),
            "nickname": "...",
            "avatar": "..."
        }
    
    Response:
        {
            "success": true,
            "data": {
                "token": "eyJ...",
                "user": { "id": 123, "username": "...", "display_name": "...", ... }
            }
        }
    """
    data = request.get_json(force=True, silent=True) or {}
    platform = data.get('platform', '')

    if platform == 'douyin':
        return _douyin_login(data)
    elif platform == 'wechat':
        return _wechat_login(data)
    elif platform == 'telegram':
        return _telegram_login(data)
    elif platform == 'line':
        return _line_login(data)
    else:
        return jsonify({'success': False, 'error': f'Unsupported platform: {platform}'}), 400


@mini_program_bp.route('/chat/stream', methods=['POST'])
def mini_program_chat_stream():
    """SSE streaming chat with RAG + intent routing"""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get('message', '')
    history = data.get('history', [])
    platform = data.get('platform', 'website')

    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    user_id = get_user_id_from_token(token) if token else None

    # RAG
    from platform.routes.api_v1 import _rag_search, _build_rag_context
    knowledge = _rag_search(message, top_k=5)
    rag_context = _build_rag_context(knowledge)

    # Intent
    from platform.routes.api_v1 import classify_intent
    intent, sentiment = classify_intent(message)

    # Agent config
    from platform.routes.api_v1 import _get_chatbot_config, _route_agent_by_intent, _get_chatbot_agent
    cfg = _get_chatbot_config()
    agent = _route_agent_by_intent(intent) or _get_chatbot_agent(cfg.get('agent_id', 'kai_assistant'))

    system_prompt = agent.get('system_prompt', '') if agent else ''
    if rag_context:
        system_prompt += f'\n\n{rag_context}'

    from agent_matrix.engine import AIEngine
    engine = AIEngine({
        'provider': agent.get('provider', cfg.get('provider', 'dashscope')),
        'model_name': agent.get('model_name', cfg.get('model_name', 'qwen-turbo')),
        'system_prompt': system_prompt,
    })

    msgs = [{'role': 'system', 'content': system_prompt}]
    if history and isinstance(history, list):
        msgs.extend(history[-int(cfg.get('max_history', 20)):])
    msgs.append({'role': 'user', 'content': message[:1000]})

    def generate():
        full_reply = ''
        try:
            for token in engine.chat_stream(msgs):
                full_reply += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'reply': full_reply, 'retrievedKnowledge': knowledge})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@mini_program_bp.route('/chat/send', methods=['POST'])
def mini_program_chat_send():
    """Non-streaming chat"""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get('message', '')
    history = data.get('history', [])
    platform = data.get('platform', 'website')

    from platform.routes.api_v1 import _rag_search, _build_rag_context, _get_chatbot_config, _get_chatbot_agent
    knowledge = _rag_search(message, top_k=5)
    rag_context = _build_rag_context(knowledge)
    cfg = _get_chatbot_config()
    agent = _get_chatbot_agent(cfg.get('agent_id', 'kai_assistant'))

    system_prompt = agent.get('system_prompt', '') if agent else ''
    if rag_context:
        system_prompt += f'\n\n{rag_context}'

    from agent_matrix.engine import AIEngine
    engine = AIEngine({
        'provider': agent.get('provider', cfg.get('provider', 'dashscope')),
        'model_name': agent.get('model_name', cfg.get('model_name', 'qwen-turbo')),
        'system_prompt': system_prompt,
    })

    msgs = [{'role': 'system', 'content': system_prompt}]
    if history and isinstance(history, list):
        msgs.extend(history[-int(cfg.get('max_history', 20)):])
    msgs.append({'role': 'user', 'content': message[:1000]})

    reply = engine.chat(msgs)
    return jsonify({'success': True, 'data': {'reply': reply, 'retrievedKnowledge': knowledge}})


@mini_program_bp.route('/chat/history', methods=['GET'])
def mini_program_chat_history():
    """Get conversation history"""
    # TODO: implement session-based history retrieval


@mini_program_bp.route('/knowledge/search', methods=['GET'])
def mini_program_knowledge_search():
    """RAG knowledge base search"""
    query = request.args.get('q', '')
    top_k = request.args.get('topK', 5, type=int)
    category = request.args.get('category', None)

    from platform.routes.api_v1 import _rag_search
    results = _rag_search(query, top_k=top_k, category=category)
    return jsonify({'success': True, 'data': results})


@mini_program_bp.route('/user/profile', methods=['GET'])
def mini_program_user_profile():
    """Get user profile"""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
    user_id = get_user_id_from_token(token)
    if not user_id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    # TODO: return user profile data


@mini_program_bp.route('/site/info', methods=['GET'])
def mini_program_site_info():
    """Get site config (brand, theme)"""
    from services.brand_service import get_brand_settings
    brand = get_brand_settings()
    return jsonify({'success': True, 'data': brand})


@mini_program_bp.route('/site/pages', methods=['GET'])
def mini_program_site_pages():
    """Get page list"""
    # TODO: return published pages list


@mini_program_bp.route('/site/page/<slug>', methods=['GET'])
def mini_program_site_page(slug):
    """Get page content by slug"""
    # TODO: return page content
```

**Register in `platform/app.py`**:

```python
# In platform/app.py, after existing blueprint registrations:
from platform.routes.mini_program import mini_program_bp
app.register_blueprint(mini_program_bp)
```

**Verification**: 
```bash
curl -X POST http://localhost:8081/api/v1/mini-program/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","platform":"test"}'
```

---

### Task 1.6: DB Migration — Add Platform Columns to `chat_messages`

**Description**: Add `platform TEXT` and `platform_user_id TEXT` columns to the `chat_messages` table.

**SQL**:

```sql
ALTER TABLE chat_messages ADD COLUMN platform TEXT DEFAULT 'website';
ALTER TABLE chat_messages ADD COLUMN platform_user_id TEXT DEFAULT '';
CREATE INDEX IF NOT EXISTS idx_chat_platform ON chat_messages(platform, platform_user_id);
```

**Implementation**: Create a migration function in `platform/db_migrations.py` (or existing migration file).

**Verification**:
```sql
PRAGMA table_info(chat_messages);
-- Should show platform and platform_user_id columns
```

---

### Task 1.7: Create `plugins/dev_accounts/` Plugin Skeleton

**Description**: Create the plugin directory with `__init__.py`, `plugin.json`, empty `routes.py`, `models.py`, `crypto.py`.

**Files to create**:
- `plugins/dev_accounts/__init__.py`
- `plugins/dev_accounts/plugin.json`
- `plugins/dev_accounts/routes.py` (empty, with blueprint)
- `plugins/dev_accounts/models.py` (empty, with placeholder)
- `plugins/dev_accounts/crypto.py` (encrypt/decrypt/mask functions)

**`plugin.json`**:

```json
{
    "name": "Developer Accounts",
    "identifier": "dev_accounts",
    "version": "1.0.0",
    "description": "Manage developer accounts for social media platforms",
    "author": "VeroRun",
    "category": "admin",
    "permissions": ["admin"],
    "admin": {
        "menu": {
            "title": "Developer Accounts",
            "icon": "key",
            "url": "/admin/dev-accounts"
        }
    }
}
```

**Verification**: Plugin directory structure matches spec.

---

### Task 1.8: Implement `dev_accounts` CRUD + Encryption

**Description**: Full implementation of routes, models, and crypto.

**Files to implement**:
- `plugins/dev_accounts/crypto.py` — `encrypt()`, `decrypt()`, `mask()` using `cryptography.fernet`
- `plugins/dev_accounts/models.py` — `get_all()`, `get_by_id()`, `create()`, `update()`, `delete()`, `test_connection()`
- `plugins/dev_accounts/routes.py` — CRUD endpoints under `/admin/dev-accounts/`
- `plugins/dev_accounts/__init__.py` — `DevAccountsPlugin` class with `on_install()` table creation

**Verification**:
```bash
curl http://localhost:8084/admin/dev-accounts/ -H "Authorization: Bearer <admin_jwt>"
```

---

## 4. Phase 2: Platform SDKs

### Task 2.1: Implement `sdks/douyin/api.js`

**File**: `sdks/douyin/api.js`

**Object**: `DouyinMP` with methods:
- `init()` — `tt.login()` → code exchange → JWT, store in `tt.setStorageSync()`
- `restoreToken()` — `tt.getStorageSync('vero_token')`
- `request(url, options)` — `tt.request()` wrapper with `Authorization: Bearer {token}` header
- `getUserProfile()` — GET `/api/v1/mini-program/user/profile`
- `_promisify(fn)` — internal utility to convert `tt.*` callback APIs to Promises

**Verification**: Code review for correct `tt.*` API usage, Promise wrapping, and token storage.

---

### Task 2.2: Implement `sdks/wechat/api.js`

**File**: `sdks/wechat/api.js`

**Object**: `WechatMP` with methods:
- `init()` — `wx.login()` → code exchange → JWT, store in `wx.setStorageSync()`
- `restoreToken()` — `wx.getStorageSync('vero_token')`
- `request(url, options)` — `wx.request()` wrapper
- `_promisify(fn)` — internal utility

**Verification**: Code review for correct `wx.*` API usage.

---

### Task 2.3: Implement `sdks/telegram/webapp.js`

**File**: `sdks/telegram/webapp.js`

**Object**: `TelegramMiniApp` with methods:
- `init()` — `window.Telegram.WebApp.ready()`, `.expand()`, read `initDataUnsafe.user`
- `authenticate()` — POST `initData` to `/api/v1/mini-program/auth/login`
- `restoreToken()` — `localStorage.getItem('vero_token')`
- `showPopup(message, callback)` — `tg.showPopup()`
- `showBackButton(callback)` / `hideBackButton()`

**Verification**: Code review for correct Telegram WebApp API usage.

---

### Task 2.4: Implement `sdks/telegram/bot.js`

**File**: `sdks/telegram/bot.js`

**Object**: `TelegramBot` with methods:
- `setWebhook(url)` — POST `/bot{token}/setWebhook`
- `setMenuButton(webappUrl)` — POST `/bot{token}/setChatMenuButton`
- `sendMessage(chatId, text)` — POST `/bot{token}/sendMessage`

**Verification**: Code review.

---

### Task 2.5: Implement `sdks/line/liff.js`

**File**: `sdks/line/liff.js`

**Object**: `LineMiniApp` with methods:
- `init(liffId)` — `liff.init()`, `liff.isLoggedIn()`, `liff.getProfile()`
- `authenticate()` — POST `accessToken` + `userId` to `/api/v1/mini-program/auth/login`
- `restoreToken()` — `localStorage.getItem('vero_token')`
- `close()` — `liff.closeWindow()`

**Verification**: Code review for correct LIFF SDK usage.

---

### Task 2.6: Implement `sdks/line/messaging.js`

**File**: `sdks/line/messaging.js`

**Object**: `LineMessaging` with methods:
- `reply(replyToken, messages)` — through backend API
- `push(userId, messages)` — through backend API

**Verification**: Code review.

---

## 5. Phase 3: Site_builder Integration

### Task 3.1: Create `site_builder/mini_app/` Module Structure

**Files to create**:
- `site_builder/mini_app/__init__.py`
- `site_builder/mini_app/engine.py` (empty class)
- `site_builder/mini_app/generators/__init__.py`
- `site_builder/mini_app/generators/base.py` (empty class)
- `site_builder/mini_app/generators/douyin.py` (empty class)
- `site_builder/mini_app/generators/wechat.py` (empty class)
- `site_builder/mini_app/generators/telegram.py` (empty class)
- `site_builder/mini_app/generators/line.py` (empty class)
- `site_builder/mini_app/packager.py` (empty class)
- `site_builder/mini_app/deployer.py` (empty class)

**Verification**: `ls site_builder/mini_app/` shows all expected files.

---

### Task 3.2: Implement `BaseMiniAppGenerator`

**File**: `site_builder/mini_app/generators/base.py`

**Class**: `BaseMiniAppGenerator(ABC)`

**Attributes**:
- `platform: str = ''`
- `template_dir: str = ''`
- `output_base: str = 'dist'`

**Methods**:
- `@abstractmethod generate(site_config, brand, options) -> dict`
- `_copy_template(output_dir)` — `shutil.copytree()`
- `_render_template(template_path, context)` — `{{ var }}` substitution
- `_write_file(path, content)` — `os.makedirs()` + write
- `_get_brand_context(brand)` — normalize brand dict
- `_get_api_context(options)` — normalize API config dict

**Verification**: Code review for correct abstract method pattern, template rendering logic.

---

### Task 3.3: Create Douyin Mini-Program Template

**Files to create under `site_builder/mini_app/templates/douyin/`**:

| File | Content |
|------|---------|
| `app.js` | `App({})` entry, import `DouyinMP`, init + restore token |
| `app.json` | `{ pages: [...], window: { navigationBarBackgroundColor: '{{ primary_color }}' } }` |
| `app.ttss` | Global styles with CSS variables |
| `pages/chat/chat.js` | Page logic — import `VeroChat`, stream chat, render messages |
| `pages/chat/chat.ttml` | Chat UI — message list + input area |
| `pages/chat/chat.ttss` | Chat page styles |
| `pages/home/home.js` | Home page — fetch site content from API |
| `pages/home/home.ttml` | Home page template |
| `pages/home/home.ttss` | Home page styles |
| `pages/profile/profile.js` | Profile page — user info from API |
| `pages/profile/profile.ttml` | Profile page template |
| `pages/profile/profile.ttss` | Profile page styles |
| `components/chat-widget/chat-widget.js` | Reusable chat widget component |
| `components/chat-widget/chat-widget.ttml` | Chat widget template |
| `components/chat-widget/chat-widget.ttss` | Chat widget styles |
| `project.config.json` | `{ appid: '{{ app_id }}', projectname: '{{ app_name }}' }` |

**Template variables** (used in `{{ }}` placeholders):
- `{{ app_name }}` — from `brand.site_name`
- `{{ primary_color }}` — from `brand.primary_color`
- `{{ base_url }}` — from `options.base_url`
- `{{ api_prefix }}` — from `options` (default `/api/v1/mini-program`)
- `{{ app_id }}` — from `options.app_id` per platform

**Verification**: All template files exist, `{{ }}` placeholders match `_render_template()` logic.

---

### Task 3.4: Implement `DouyinGenerator`

**File**: `site_builder/mini_app/generators/douyin.py`

**Class**: `DouyinGenerator(BaseMiniAppGenerator)`

**`generate()` method flow**:
1. `_copy_template(output_dir)` — copy template to `dist/douyin/`
2. Build context from `brand` + `options`
3. Determine pages list: `['chat'] + include_pages + ['profile']`
4. Write `app.json` with correct page paths
5. Write `app.js` with rendered context
6. Write `project.config.json` with `app_id`
7. For each page, render `.js`, `.ttml`, `.ttss` files
8. Collect file list with `os.walk()`
9. Return `{'output_dir': ..., 'files': [...], 'platform': 'douyin', 'compatible_with': ['toutiao']}`

**Note**: Toutiao shares the same ByteDance ecosystem; `MiniAppEngine._get_generator('toutiao')` returns `DouyinGenerator`.

**Verification**: Manual check — inspect generated `dist/douyin/` output.

---

### Task 3.5: Create WeChat Mini-Program Template

**Files to create under `site_builder/mini_app/templates/wechat/`**:

Same structure as Douyin but with WeChat file extensions:
- `.wxss` instead of `.ttss`
- `.wxml` instead of `.ttml`
- `wx.*` API instead of `tt.*` API

**Verification**: All template files exist.

---

### Task 3.6: Implement `WechatGenerator`

**File**: `site_builder/mini_app/generators/wechat.py`

**Class**: `WechatGenerator(BaseMiniAppGenerator)`

Same logic as `DouyinGenerator` but with WeChat template paths and config format.

**Verification**: Manual check — inspect generated `dist/wechat/` output.

---

### Task 3.7: Create Telegram Mini App Template

**Files to create under `site_builder/mini_app/templates/telegram/`**:

| File | Content |
|------|---------|
| `index.html` | Main entry — load `telegram-web-app.js`, init `TelegramMiniApp`, show chat |
| `chat.html` | Chat page |
| `css/style.css` | Styles with Telegram theme variables (`--tg-bg-color`, `--tg-text-color`) |
| `js/app.js` | Application logic — `VeroChat`, `TelegramMiniApp`, auth flow |
| `manifest.json` | `{ "name": "{{ app_name }}", "url": "..." }` |

**Template variables**: Same as Douyin template.

**Verification**: All template files exist.

---

### Task 3.8: Implement `TelegramGenerator`

**File**: `site_builder/mini_app/generators/telegram.py`

**Class**: `TelegramGenerator(BaseMiniAppGenerator)`

**`generate()` method flow**:
1. Copy template to `dist/telegram/`
2. Render `index.html`, `chat.html`, `js/app.js` with brand + API context
3. Write `manifest.json` with app name
4. Return output info

**Verification**: Manual check — open `dist/telegram/index.html` in browser.

---

### Task 3.9: Create LINE Mini App Template

**Files to create under `site_builder/mini_app/templates/line/`**:

| File | Content |
|------|---------|
| `index.html` | Main entry — load `@line/liff`, init `LineMiniApp`, show chat |
| `chat.html` | Chat page |
| `css/style.css` | Styles |
| `js/app.js` | Application logic — `VeroChat`, `LineMiniApp`, auth flow |
| `manifest.json` | `{ "name": "{{ app_name }}", "liffId": "..." }` |

**Verification**: All template files exist.

---

### Task 3.10: Implement `LINEGenerator`

**File**: `site_builder/mini_app/generators/line.py`

**Class**: `LINEGenerator(BaseMiniAppGenerator)`

Same logic as `TelegramGenerator` but with LINE template and LIFF integration.

**Verification**: Manual check.

---

### Task 3.11: Implement `MiniAppEngine`

**File**: `site_builder/mini_app/engine.py`

**Class**: `MiniAppEngine`

**Methods**:
- `__init__(site_config, brand_settings)`
- `generate(platforms, options) -> dict` — iterate platforms, call generators, collect results
- `_get_generator(platform) -> BaseMiniAppGenerator` — factory method

**Verification**: Unit test — call `generate(['douyin', 'telegram'], {...})` and check output.

---

### Task 3.12: Implement `MiniAppPackager`

**File**: `site_builder/mini_app/packager.py`

**Class**: `MiniAppPackager`

**Methods**:
- `__init__(output_base='dist')`
- `package(platform, output_dir) -> str` — `shutil.make_archive()` → `.zip`
- `package_all(results) -> dict` — package all platforms

**Verification**: Check that `.zip` files are created correctly.

---

### Task 3.13: Implement `MiniAppDeployer`

**File**: `site_builder/mini_app/deployer.py`

**Class**: `MiniAppDeployer`

**Methods**:
- `__init__(dev_accounts)`
- `deploy_telegram(webapp_url, bot_token) -> dict` — Bot API `setChatMenuButton`
- `deploy_line(liff_id, endpoint_url, channel_token) -> dict` — LIFF API update
- `get_manual_deploy_hint(platform) -> str` — instructions for Douyin/WeChat

**Verification**: Code review for correct API calls.

---

### Task 3.14: Add Mini-App Routes to Site_builder

**File**: `site_builder/routes.py` (append new routes)

**New endpoints**:
- `POST /admin/site-builder/mini-app/generate` — Trigger generation
- `GET /admin/site-builder/mini-app/status/<task_id>` — Query status
- `GET /admin/site-builder/mini-app/download/<platform>/<task_id>` — Download .zip
- `POST /admin/site-builder/mini-app/deploy/<platform>` — Deploy to platform
- `GET /admin/site-builder/mini-app/platforms` — List platforms
- `PUT /admin/site-builder/mini-app/platforms/<platform>` — Update platform config

**Verification**: 
```bash
curl -X POST http://localhost:8084/admin/site-builder/mini-app/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_jwt>" \
  -d '{"platforms":["telegram"],"options":{"include_chat":true}}'
```

---

## 6. Phase 4: Preview & Testing

### Task 4.1: Add Device Simulator CSS

**File**: `admin/static/css/preview.css` (new file)

**CSS classes**:
- `.preview-toolbar` — toolbar with device selector
- `.device-frame` — base device frame with rounded corners, shadow
- `.device-frame.iphone*` — device-specific dimensions
- `.device-frame .notch` — iPhone notch
- `.device-frame .home-bar` — iPhone home indicator
- `.device-frame iframe` — embedded preview

**Verification**: Open preview page, check device frame rendering.

---

### Task 4.2: Update `ai_site_preview.html`

**File**: `admin/templates/ai_site_preview.html`

**Changes**:
- Add `<link rel="stylesheet" href="/static/css/preview.css">`
- Add `<div class="preview-toolbar">` with device selector
- Add `<div class="device-frame" id="deviceFrame">` wrapping the iframe
- Add JavaScript to switch device dimensions on selector change

**Verification**: Open `/admin/site-builder/preview-site`, switch devices, check iframe resizes.

---

### Task 4.3: E2E Test — Douyin Generation

**Steps**:
1. Create a test site via Site_builder (draft mode)
2. POST `/admin/site-builder/mini-app/generate` with `platforms: ["douyin"]`
3. Verify `dist/douyin/` directory has correct structure
4. Download .zip and verify contents
5. Open in ByteDance DevTools (if available)

**Expected**: All files generated, `app.json` has correct pages, `app.js` has correct API URLs.

---

### Task 4.4: E2E Test — WeChat Generation

Same as 4.3 but for WeChat platform.

**Expected**: `dist/wechat/` has correct `.wxml`/`.wxss` files.

---

### Task 4.5: E2E Test — Telegram Generation + Deploy

**Steps**:
1. Generate Telegram mini-program
2. Verify `dist/telegram/index.html` contains correct API URL
3. Deploy static files to server (e.g., `/home/easykai/easykai-workspace/easykai.cn/static/mini-apps/telegram/`)
4. Call `deploy_telegram(webapp_url)` to set menu button
5. Open Telegram, verify menu button appears and opens the mini-app
6. Test chat flow — send message, verify AI responds

**Expected**: Full chat flow works end-to-end.

---

### Task 4.6: E2E Test — LINE Generation + Deploy

**Steps**:
1. Generate LINE mini-program
2. Deploy static files
3. Call `deploy_line(liff_id, endpoint_url)` to update LIFF endpoint
4. Open LINE, verify LIFF app loads
5. Test chat flow

**Expected**: Full chat flow works end-to-end.

---

## 7. Phase 5: Documentation & Deployment

### Task 5.1: Update `docs/plugin-system.md`

**Sections to add**:
- "Social Media Mini-Program Plugin Standard" — directory structure, `plugin.json` fields, `register_mini_apps()` method
- Update `BasePlugin` class documentation with `register_mini_apps()`

**Verification**: Review doc for completeness.

---

### Task 5.2: Write `docs/ai-advisor-integration.md`

**Content**:
- Architecture diagram (platform → SDK → API → AIEngine → RAG)
- Authentication bridge table
- Chat bridge code example
- Multi-channel session management
- Configuration guide

**Verification**: Review doc.

---

### Task 5.3: Update `docs/sdk-reference.md`

**Add sections**:
- `VeroChat` class API reference
- `VeroAuth` class API reference
- `VeroRAG` class API reference
- Platform SDK API references (DouyinMP, WechatMP, TelegramMiniApp, LineMiniApp)

**Verification**: Review doc.

---

### Task 5.4: Write `docs/mini-program-deployment.md`

**Content**:
- Prerequisites for each platform
- Step-by-step deployment guide for each platform
- Telegram: upload to server, set menu button, verify
- LINE: upload to server, update LIFF endpoint, verify
- Douyin: import to DevTools, upload, submit for review
- WeChat: import to DevTools, upload, submit for review
- Troubleshooting common issues

**Verification**: Review doc.

---

### Task 5.5: Deploy to Production

**Steps**:
1. Commit all changes locally
2. `rsync -av --delete` to server (excluding `data/`)
3. Restart services: `systemctl restart admin.service auth-center.service`
4. Run DB migrations on server
5. Verify all endpoints respond correctly

**Verification**: Smoke test each endpoint on production.

---

## 8. DB Migration Details

### 8.1 Migration File

**File**: `platform/db_migrations.py` (append new migration function)

```python
@register_migration('20260713_mini_program')
def migrate_mini_program(conn):
    """Add platform columns to chat_messages"""
    conn.execute("ALTER TABLE chat_messages ADD COLUMN platform TEXT DEFAULT 'website'")
    conn.execute("ALTER TABLE chat_messages ADD COLUMN platform_user_id TEXT DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_platform ON chat_messages(platform, platform_user_id)")
    conn.commit()
```

### 8.2 `dev_accounts` Table (Created by Plugin)

```sql
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
```

---

## 9. Environment Variables

### 9.1 New Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DEV_ACCOUNTS_ENCRYPTION_KEY` | AES-256 encryption key for dev account credentials | Yes | (none) |

**Add to `.env`**:

```ini
DEV_ACCOUNTS_ENCRYPTION_KEY=your_secure_random_key_here_min_32_chars
```

### 9.2 Existing Variables to Reference

| Variable | Used In | Purpose |
|----------|---------|---------|
| `DEPLOY_DOMAIN` | All SDK `baseURL` | System domain (e.g., `easykai.cn`) |
| `DEPLOY_MARKET` | SDK `baseURL` | Market identifier (e.g., `cn`) |

---

## 10. Verification Checklist

### 10.1 Backend API

- [ ] `POST /api/v1/mini-program/auth/login` returns JWT for all 4 platforms
- [ ] `POST /api/v1/mini-program/chat/stream` SSE streaming works
- [ ] `POST /api/v1/mini-program/chat/send` non-streaming works
- [ ] `GET /api/v1/mini-program/chat/history` returns history
- [ ] `GET /api/v1/mini-program/knowledge/search` returns RAG results
- [ ] `GET /api/v1/mini-program/user/profile` returns user data
- [ ] `GET /api/v1/mini-program/site/info` returns brand config
- [ ] `GET /api/v1/mini-program/site/pages` returns page list
- [ ] `GET /api/v1/mini-program/site/page/<slug>` returns page content

### 10.2 Admin API

- [ ] `POST /admin/site-builder/mini-app/generate` triggers generation
- [ ] `GET /admin/site-builder/mini-app/status/<task_id>` returns status
- [ ] `GET /admin/site-builder/mini-app/download/<platform>/<task_id>` returns .zip
- [ ] `POST /admin/site-builder/mini-app/deploy/<platform>` deploys
- [ ] `GET /admin/site-builder/mini-app/platforms` lists platforms
- [ ] `PUT /admin/site-builder/mini-app/platforms/<platform>` updates config
- [ ] `GET /admin/dev-accounts/` lists accounts
- [ ] `POST /admin/dev-accounts/` creates account
- [ ] `PUT /admin/dev-accounts/<id>` updates account
- [ ] `DELETE /admin/dev-accounts/<id>` deletes account

### 10.3 Generated Output

- [ ] Douyin: `dist/douyin/` has `app.js`, `app.json`, `app.ttss`, `pages/chat/`, `project.config.json`
- [ ] WeChat: `dist/wechat/` has `.wxml`, `.wxss`, `project.config.json`
- [ ] Telegram: `dist/telegram/` has `index.html`, `chat.html`, `manifest.json`
- [ ] LINE: `dist/line/` has `index.html`, `chat.html`, `manifest.json`

### 10.4 Preview

- [ ] Device selector shows all iPhone models + H5
- [ ] Switching device resizes iframe correctly
- [ ] iPhone frame renders with notch and home bar
- [ ] Rotate button works (if implemented)

### 10.5 Security

- [ ] Dev account credentials are encrypted in database
- [ ] API responses mask sensitive fields
- [ ] JWT authentication required for protected endpoints
- [ ] Admin JWT required for admin endpoints

---

> **Implementation Order**: Execute tasks in Phase order (1 → 2 → 3 → 4 → 5). Each task depends on the previous phase's completion. Within each phase, tasks with no dependencies can be parallelized.