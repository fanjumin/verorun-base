#!/usr/bin/env python3
"""Mini-Program Unified API — routes for all social media mini-program platforms

Moved from main_site/routes/mini_program.py into the mini_app_builder plugin
(v2.0.0 decoupling).  Provides authentication, streaming chat, RAG knowledge
search, and site content endpoints for Douyin, WeChat, Telegram, and LINE
mini-programs.

Prefix: /api/v1/mini-program/
"""

import json
import os
import sys
import threading
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, stream_with_context

# Create blueprint
mini_program_bp = Blueprint('mini_program', __name__, url_prefix='/api/v1/mini-program')


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _ensure_auth_center():
    """Ensure auth-center is importable (main_site removes it from sys.path
    after startup; user_registry is a new module not cached in sys.modules)."""
    import sys as _sys
    _auth_center = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if os.path.isdir(_auth_center) and _auth_center not in _sys.path:
        _sys.path.insert(0, _auth_center)


def _ok(data=None):
    return jsonify({'success': True, 'data': data})


def _err(msg, code=400):
    return jsonify({'success': False, 'error': msg}), code


def _get_user_id():
    """Extract user_id from JWT Bearer token"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth.replace('Bearer ', '')
    try:
        from routes.api_v1 import get_current_user_id
        return get_current_user_id(token)
    except ImportError:
        from services.jwt_service import validate_token
        payload = validate_token(token)
        return payload.get('user_id') if payload else None


def _require_auth():
    """Require valid JWT token, return (user_id, error_response)"""
    user_id = _get_user_id()
    if not user_id:
        return None, _err('Invalid or expired token', 401)
    return user_id, None


# ═══════════════════════════════════════════════════════════════
# Auth
# ═══════════════════════════════════════════════════════════════

@mini_program_bp.route('/auth/login', methods=['POST'])
def mp_auth_login():
    """Platform login — exchange platform credentials for system JWT.

    Request body:
        {
            "platform": "douyin" | "wechat" | "telegram" | "line",
            "code": "..."           (Douyin/WeChat: tt.login()/wx.login() code)
            "initData": "..."       (Telegram: WebApp.initData)
            "accessToken": "...",   (LINE: liff.getAccessToken())
            "userId": "...",        (LINE: liff.getProfile().userId)
            "nickname": "...",
            "avatar": "..."
        }

    Response:
        {
            "success": true,
            "data": {
                "token": "eyJ...",
                "user": {
                    "id": 123,
                    "username": "dy_abc123",
                    "display_name": "John",
                    "platform": "douyin",
                    "platform_user_id": "ou_xxxx",
                    "is_new_user": true
                }
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
        return _err(f'Unsupported platform: {platform}', 400)


@mini_program_bp.route('/auth/validate', methods=['POST'])
def mp_auth_validate():
    """Validate a JWT token"""
    user_id, err = _require_auth()
    if err:
        return err
    return _ok({'valid': True, 'user_id': user_id})


def _douyin_login(data):
    """Handle Douyin mini-program login.

    v2.1.0：通过 auth-center 服务层注册/获取主库用户（douyin_open_id 列），
    并在独立库记录 平台身份 -> user_id 映射（联邦身份）。
    """
    code = data.get('code', '')
    if not code:
        return _err('code is required', 400)

    try:
        _ensure_auth_center()
        from plugins.oauth_config.services.douyin_service import code2session

        domain = (request.headers.get('Host', '') or '').split(':')[0]
        if domain.startswith('www.'):
            domain = domain[4:]
        result = code2session(code, site_domain=domain) if code2session else None
        if not result or not result.get('openid'):
            return _err('Failed to exchange code with Douyin', 400)

        openid = result['openid']
        nickname = data.get('nickname', '') or ''
        avatar = data.get('avatar', '') or ''
        import hashlib
        username = 'dy_' + hashlib.md5(openid.encode()).hexdigest()[:12]
        display_name = nickname or f'DouyinUser_{openid[-6:]}'

        from services.user_registry import register_or_get_platform_user
        user = register_or_get_platform_user(
            'douyin', openid, username, display_name, avatar)

        from .platform_users import upsert_mapping
        upsert_mapping('douyin', openid, user['id'], username, display_name, avatar)

        from services.jwt_service import generate_token
        token = generate_token({
            'user_id': user['id'],
            'username': user['username'],
            'platform': 'douyin',
            'platform_user_id': openid,
        })

        return _ok({
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'display_name': user.get('display_name', ''),
                'platform': 'douyin',
                'platform_user_id': openid,
                'is_new_user': False,
            }
        })
    except Exception as e:
        import logging
        logging.error(f'[MiniProgram] Douyin login failed: {e}')
        return _err(f'Login failed: {e}', 500)


def _wechat_login(data):
    """Handle WeChat mini-program login.

    v2.1.0：通过 oauth_config 换取 openid/unionid，经 auth-center 服务层
    注册主库用户（wechat_openid 列），独立库记录映射（联邦身份）。
    """
    code = data.get('code', '')
    if not code:
        return _err('code is required', 400)

    try:
        _ensure_auth_center()
        from plugins.oauth_config.services.wechat_service import get_openid_by_code

        session_info = get_openid_by_code(code)
        if not session_info or not session_info.get('openid'):
            return _err('Failed to exchange code with WeChat', 400)

        openid = session_info.get('openid', '')
        unionid = session_info.get('unionid', openid)

        import hashlib
        username = 'wx_' + hashlib.md5(openid.encode()).hexdigest()[:12]
        nickname = data.get('nickname', '') or 'WeChat User'
        avatar = data.get('avatar', '') or ''

        from services.user_registry import register_or_get_platform_user
        user = register_or_get_platform_user(
            'wechat', unionid, username, nickname, avatar)

        from .platform_users import upsert_mapping
        upsert_mapping('wechat', unionid, user['id'], username, nickname, avatar)

        from services.jwt_service import generate_token
        token = generate_token({
            'user_id': user['id'],
            'username': user['username'],
            'platform': 'wechat',
            'platform_user_id': unionid,
        })

        return _ok({
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'display_name': user.get('display_name', ''),
                'platform': 'wechat',
                'platform_user_id': unionid,
                'is_new_user': False,
            }
        })
    except Exception as e:
        import logging
        logging.error(f'[MiniProgram] WeChat login failed: {e}')
        return _err(f'Login failed: {e}', 500)


def _telegram_login(data):
    """Handle Telegram Mini App login (initData HMAC verification)"""
    init_data = data.get('initData', '')
    if not init_data:
        return _err('initData is required', 400)

    try:
        import hmac
        import hashlib
        from urllib.parse import parse_qs, unquote

        # Verify HMAC signature
        from .submodules.accounts.models import get_by_platform_raw
        from .submodules.accounts.crypto import decrypt

        account = get_by_platform_raw('telegram')
        if not account or not account.get('bot_token'):
            return _err('Telegram bot not configured', 500)

        bot_token = decrypt(account['bot_token'])

        # Parse initData
        params = parse_qs(init_data)
        received_hash = params.pop('hash', [None])[0]
        if not received_hash:
            return _err('Missing hash in initData', 400)

        # Build data_check_string
        data_pairs = sorted(
            (k, unquote(v[0])) for k, v in params.items()
        )
        data_check_string = '\n'.join(f'{k}={v}' for k, v in data_pairs)

        # Compute secret key
        secret_key = hmac.new(
            b'WebAppData', bot_token.encode(), hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if computed_hash != received_hash:
            return _err('Invalid initData signature', 403)

        # Extract user info
        user_json = params.get('user', ['{}'])[0]
        user_info = json.loads(unquote(user_json))
        tg_user_id = str(user_info.get('id', ''))
        tg_username = user_info.get('username', '')
        tg_first_name = user_info.get('first_name', '')

        display_name = tg_first_name or tg_username or f'TG{tg_user_id}'
        username = 'tg_' + hashlib.md5(tg_user_id.encode()).hexdigest()[:12]

        _ensure_auth_center()
        from services.user_registry import register_or_get_platform_user
        user = register_or_get_platform_user(
            'telegram', tg_user_id, username, display_name, '')

        from .platform_users import upsert_mapping
        upsert_mapping('telegram', tg_user_id, user['id'], username, display_name, '')

        from services.jwt_service import generate_token
        token = generate_token({
            'user_id': user['id'],
            'username': user['username'],
            'platform': 'telegram',
            'platform_user_id': tg_user_id,
        })

        return _ok({
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'display_name': user.get('display_name', ''),
                'platform': 'telegram',
                'platform_user_id': tg_user_id,
                'is_new_user': False,
            }
        })
    except Exception as e:
        import logging
        logging.error(f'[MiniProgram] Telegram login failed: {e}')
        return _err(f'Login failed: {e}', 500)


def _line_login(data):
    """Handle LINE LIFF login.

    v2.1.0：经 auth-center 服务层注册主库用户（line 无专用列，按 username
    匹配），独立库记录映射（联邦身份）。
    """
    access_token = data.get('accessToken', '')
    user_id = data.get('userId', '')
    if not access_token or not user_id:
        return _err('accessToken and userId are required', 400)

    try:
        import hashlib
        _ensure_auth_center()

        username = 'line_' + hashlib.md5(user_id.encode()).hexdigest()[:12]
        display_name = data.get('displayName', data.get('nickname', 'LINE User'))
        avatar = data.get('avatar', '') or ''

        from services.user_registry import register_or_get_platform_user
        user = register_or_get_platform_user(
            'line', user_id, username, display_name, avatar)

        from .platform_users import upsert_mapping
        upsert_mapping('line', user_id, user['id'], username, display_name, avatar)

        from services.jwt_service import generate_token
        token = generate_token({
            'user_id': user['id'],
            'username': user['username'],
            'platform': 'line',
            'platform_user_id': user_id,
        })

        return _ok({
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'display_name': user.get('display_name', ''),
                'platform': 'line',
                'platform_user_id': user_id,
                'is_new_user': False,
            }
        })
    except Exception as e:
        import logging
        logging.error(f'[MiniProgram] LINE login failed: {e}')
        return _err(f'Login failed: {e}', 500)


# ═══════════════════════════════════════════════════════════════
# Chat
# ═══════════════════════════════════════════════════════════════

@mini_program_bp.route('/chat/stream', methods=['POST'])
def mp_chat_stream():
    """SSE streaming AI chat with RAG + intent routing.

    Request body:
        {
            "message": "What products do you offer?",
            "history": [{"role": "user", "content": "..."}, ...],
            "platform": "telegram"
        }

    Response: text/event-stream
        data: {"type":"token","content":"We"}
        data: {"type":"token","content":" offer"}
        ...
        data: {"type":"done","reply":"...","retrievedKnowledge":[...]}
    """
    data = request.get_json(force=True, silent=True) or {}
    message = data.get('message', '')
    history = data.get('history', [])
    platform = data.get('platform', 'website')

    if not message:
        return _err('message is required', 400)

    # Optional auth (chat works without login too)
    auth_header = request.headers.get('Authorization', '')
    user_id = None
    if auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '')
        try:
            from routes.api_v1 import get_current_user_id
            user_id = get_current_user_id(token)
        except Exception:
            pass

    # RAG knowledge retrieval
    try:
        from routes.api_v1 import _rag_search, _build_rag_context
        knowledge = _rag_search(message, top_k=5, scope='user')
        rag_context = _build_rag_context(knowledge)
    except Exception as e:
        import logging
        logging.warning(f'[MiniProgram] RAG retrieval failed: {e}')
        knowledge = []
        rag_context = ''

    # Intent classification
    try:
        from plugins.chatbot.stats import classify_intent
        intent, sentiment = classify_intent(message)
    except Exception:
        intent, sentiment = 'other', 'neutral'

    # Get chatbot agent config
    try:
        from routes.api_v1 import _get_chatbot_config, _get_chatbot_agent, _route_agent_by_intent
        cfg = _get_chatbot_config()
        agent = _route_agent_by_intent(intent) or _get_chatbot_agent(cfg.get('agent_id', 'chat_assistant'))
    except Exception:
        cfg = {'provider': 'dashscope', 'model_name': 'qwen-turbo', 'max_history': '20'}
        agent = None

    system_prompt = agent.get('system_prompt', '') if agent else ''
    if rag_context:
        system_prompt += f'\n\n{rag_context}'

    # Build messages
    msgs = [{'role': 'system', 'content': system_prompt}]
    if history and isinstance(history, list):
        valid_history = [h for h in history if isinstance(h, dict) and 'role' in h and 'content' in h]
        msgs.extend(valid_history[-int(cfg.get('max_history', 20)):])
    msgs.append({'role': 'user', 'content': message[:1000]})

    session_id = f"mp_{platform}_{uuid.uuid4().hex[:8]}"

    def generate():
        full_reply = ''
        try:
            from agent_matrix.engine import UnifiedLLM
            engine = UnifiedLLM({
                'provider': agent.get('provider', cfg.get('provider', 'dashscope')) if agent else cfg.get('provider', 'dashscope'),
                'model_name': agent.get('model_name', cfg.get('model_name', 'qwen-turbo')) if agent else cfg.get('model_name', 'qwen-turbo'),
                'system_prompt': system_prompt,
            })

            for token in engine.chat_stream(msgs):
                if not token.startswith('Error:'):
                    full_reply += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'reply': full_reply, 'retrievedKnowledge': [{'title': k['title'], 'content': k['content'][:200]} for k in knowledge]})}\n\n"

            # Log session asynchronously
            threading.Thread(
                target=_log_session_async,
                args=(session_id, user_id, message, full_reply, platform, intent, sentiment),
                daemon=True
            ).start()

        except Exception as e:
            import logging
            logging.error(f'[MiniProgram] Chat stream error: {e}')
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


def _log_session_async(session_id, user_id, user_query, ai_reply, platform, intent, sentiment):
    """Persist chat session to the independent DB (background thread).

    v2.1.0：会话历史独立存储于 mini_app_builder.mini_app_sessions。
    """
    try:
        from .db import get_db
        with get_db() as conn:
            conn.execute(
                "INSERT INTO mini_app_sessions "
                "(session_id, user_id, platform, query_text, reply_text, intent, sentiment) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (session_id, user_id or 0, platform, user_query, ai_reply, intent, sentiment)
            )
    except Exception as e:
        import logging
        logging.warning(f'[MiniProgram] Session persist failed: {e}')
    # 兼容：保留原 stats 统计（主库 chatbot_sessions），失败静默
    try:
        from plugins.chatbot.stats import log_session
        log_session(
            session_id=session_id,
            user_query=user_query,
            ai_reply=ai_reply,
            source=f'mini_program_{platform}',
            intent=intent,
            sentiment=sentiment,
        )
    except Exception as e:
        import logging
        logging.warning(f'[MiniProgram] Stats session logging failed: {e}')


@mini_program_bp.route('/chat/send', methods=['POST'])
def mp_chat_send():
    """Non-streaming AI chat with RAG.

    Request body:
        {
            "message": "What products do you offer?",
            "history": [{"role": "user", "content": "..."}, ...],
            "platform": "telegram"
        }

    Response:
        {
            "success": true,
            "data": {
                "reply": "We offer various products...",
                "retrievedKnowledge": [...]
            }
        }
    """
    data = request.get_json(force=True, silent=True) or {}
    message = data.get('message', '')
    history = data.get('history', [])
    platform = data.get('platform', 'website')

    if not message:
        return _err('message is required', 400)

    try:
        from routes.api_v1 import _rag_search, _build_rag_context, _get_chatbot_config, _get_chatbot_agent
        knowledge = _rag_search(message, top_k=5, scope='user')
        rag_context = _build_rag_context(knowledge)

        cfg = _get_chatbot_config()
        agent = _get_chatbot_agent(cfg.get('agent_id', 'chat_assistant'))

        system_prompt = agent.get('system_prompt', '') if agent else ''
        if rag_context:
            system_prompt += f'\n\n{rag_context}'

        msgs = [{'role': 'system', 'content': system_prompt}]
        if history and isinstance(history, list):
            valid_history = [h for h in history if isinstance(h, dict) and 'role' in h and 'content' in h]
            msgs.extend(valid_history[-int(cfg.get('max_history', 20)):])
        msgs.append({'role': 'user', 'content': message[:1000]})

        from agent_matrix.engine import UnifiedLLM
        engine = UnifiedLLM({
            'provider': agent.get('provider', 'dashscope') if agent else 'dashscope',
            'model_name': agent.get('model_name', 'qwen-turbo') if agent else 'qwen-turbo',
            'system_prompt': system_prompt,
        })

        reply = engine.chat(msgs)

        return _ok({
            'reply': reply,
            'retrievedKnowledge': [{'title': k['title'], 'content': k['content'][:200]} for k in knowledge],
        })
    except Exception as e:
        import logging
        logging.error(f'[MiniProgram] Chat send error: {e}')
        return _err(f'Chat failed: {e}', 500)


@mini_program_bp.route('/chat/history', methods=['GET'])
def mp_chat_history():
    """Get conversation history for the current user (independent DB)."""
    user_id, err = _require_auth()
    if err:
        return err

    try:
        from .db import get_db
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, session_id, platform, query_text, reply_text, intent, "
                "sentiment, created_at FROM mini_app_sessions "
                "WHERE user_id=%s ORDER BY created_at DESC LIMIT 50",
                (user_id,)
            ).fetchall()
        return _ok([dict(r) for r in rows])
    except Exception as e:
        return _err(f'Failed to get history: {e}', 500)


# ═══════════════════════════════════════════════════════════════
# Knowledge / Site Content
# ═══════════════════════════════════════════════════════════════

@mini_program_bp.route('/knowledge/search', methods=['GET'])
def mp_knowledge_search():
    """Search the RAG knowledge base.

    Query params: q (required), topK (default 5), category (optional)
    """
    query = request.args.get('q', '')
    if not query:
        return _err('q parameter is required', 400)

    top_k = request.args.get('topK', 5, type=int)
    category = request.args.get('category', None)
    if top_k < 1:
        top_k = 5
    if top_k > 20:
        top_k = 20

    try:
        from routes.api_v1 import _rag_search
        results = _rag_search(query, top_k=top_k, category=category, scope='user')
        return _ok(results)
    except Exception as e:
        return _err(f'Search failed: {e}', 500)


@mini_program_bp.route('/site/info', methods=['GET'])
def mp_site_info():
    """Get site brand and theme configuration (public, via internal API)."""
    try:
        from .internal_client import get_brand_settings
        brand = get_brand_settings()
        return _ok({
            'site_name': brand.get('site_name', 'VeroRun'),
            'tagline': brand.get('tagline', ''),
            'primary_color': brand.get('primary_color', '#1890ff'),
            'secondary_color': brand.get('secondary_color', ''),
            'logo_url': brand.get('logo_url', ''),
            'favicon_url': brand.get('favicon_url', ''),
        })
    except Exception as e:
        return _err(f'Failed to get site info: {e}', 500)


@mini_program_bp.route('/site/pages', methods=['GET'])
def mp_site_pages():
    """Get published page list (public, via internal API)."""
    try:
        from .internal_client import get_published_pages
        return _ok(get_published_pages())
    except Exception as e:
        return _ok([])


@mini_program_bp.route('/site/page/<slug>', methods=['GET'])
def mp_site_page(slug):
    """Get a specific page by slug (public, via internal API)."""
    try:
        from .internal_client import get_published_page
        page = get_published_page(slug)
        if not page:
            return _err('Page not found', 404)
        return _ok(page)
    except Exception as e:
        return _err(f'Failed to get page: {e}', 500)


@mini_program_bp.route('/user/profile', methods=['GET'])
def mp_user_profile():
    """Get current user profile (via auth-center service layer)."""
    user_id, err = _require_auth()
    if err:
        return err

    try:
        _ensure_auth_center()
        from services.user_registry import get_user_by_id
        user = get_user_by_id(user_id)
        if not user:
            return _err('User not found', 404)
        return _ok(user)
    except Exception as e:
        return _err(f'Failed to get profile: {e}', 500)
