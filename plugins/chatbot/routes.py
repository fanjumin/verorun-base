import json
import sys
import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g, current_app


chatbot_bp = Blueprint('chatbot_admin', __name__)
logger = logging.getLogger(__name__)

# ── 公开 Webhook 蓝图（多渠道）─────────────────────────
webhook_bp = Blueprint('chatbot_webhook', __name__, url_prefix='/api/v1/channels')

# ── 统计报表 ────────────────────────────────────────────

def _stats_import():
    """延迟导入 stats 模块，避免循环依赖。"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from stats import log_session, get_today_stats, record_csat
    return log_session, get_today_stats, record_csat


# ── 数据库辅助 ────────────────────────────────────────────

def _get_main_db():
    """主库连接（user_tickets 表在主库）"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
    from models import get_db
    return get_db()


def create_ticket_from_chat(title, content, contact='', user_id=None, session_id=None):
    """AI 转人工时创建工单。
    
    可被 api_v1.py 直接调用（不经过 HTTP）。
    返回 {success, ticket_id, error}。
    """
    try:
        with _get_main_db() as conn:
            cur = conn.execute(
                """INSERT INTO user_tickets
                   (user_id, type, category, title, content, contact,
                    status, priority, created_at, updated_at)
                   VALUES (?, 'aftersale', 'chatbot_escalation',
                           ?, ?, ?,
                           'open', 'normal',
                           datetime('now'), datetime('now'))""",
                (user_id, title, content, contact)
            )
            conn.commit()
            ticket_id = cur.lastrowid
            logger.info(f'[Chatbot] Ticket created: #{ticket_id} — {title}')
        return {'success': True, 'ticket_id': ticket_id}
    except Exception as e:
        logger.error(f'[Chatbot] Create ticket failed: {e}')
        return {'success': False, 'error': str(e)}


def parse_escalation_from_reply(full_reply):
    """从 AI 回复中解析 [TICKET_CREATE] 标记。
    
    返回 (cleaned_reply, ticket_data | None)
    ticket_data = {title, content, contact}
    """
    marker = '[TICKET_CREATE]'
    idx = full_reply.rfind(marker)
    if idx == -1:
        return full_reply, None

    cleaned = full_reply[:idx].rstrip()
    json_part = full_reply[idx + len(marker):].strip()

    # 提取第一对大括号中的 JSON
    brace_start = json_part.find('{')
    brace_end = json_part.rfind('}')
    if brace_start == -1 or brace_end == -1:
        return cleaned, None

    try:
        data = json.loads(json_part[brace_start:brace_end + 1])
        ticket_data = {
            'title': str(data.get('title', '用户咨询'))[:200],
            'content': str(data.get('content', '')),
            'contact': str(data.get('contact', '')),
        }
        return cleaned, ticket_data
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f'[Chatbot] Parse escalation JSON failed: {e}')
        return cleaned, None


def _require_admin():
    """鉴权守卫：优先 Authorization header，回退 cookie，使用 JWT is_admin 声明。"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
    from services.jwt_service import validate_token
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return (jsonify({'success': False, 'error': '需要管理权限'}), 401)
    return None


def _get_plugin_manager():
    pm = getattr(request, 'plugin_manager', None) or g.get('plugin_manager')
    if pm is None:
        pm = current_app.extensions.get('plugin_manager')
    return pm


@chatbot_bp.route('/settings', methods=['GET'])
def get_settings():
    err = _require_admin()
    if err:
        return err

    keys = [
        'enabled', 'auto_escalate', 'title', 'subtitle', 'welcome_message', 'help_hint',
        'avatar_url', 'agent_id', 'max_history', 'float_button_text'
    ]

    try:
        pm = _get_plugin_manager()
        inst = pm.get_instance('chatbot') if pm else None
        cfg = {k: inst.get_config_value(k) if inst else '' for k in keys}
        return jsonify({'success': True, 'data': cfg})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chatbot_bp.route('/log_session', methods=['POST'])
def log_session_route():
    """记录一次 AI 对话回合（由 api_v1.py 内部调用）。"""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id', '')
    user_query = data.get('user_query', '')
    ai_reply = data.get('ai_reply', '')
    escalated = data.get('escalated', False)
    source = data.get('source', 'chatbot')
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id 不能为空'}), 400
    ls, _, _ = _stats_import()
    ok = ls(session_id, user_query, ai_reply, escalated=escalated, source=source)
    return jsonify({'success': ok})


@chatbot_bp.route('/stats', methods=['GET'])
def stats():
    """获取今日统计概览。"""
    err = _require_admin()
    if err:
        return err
    _, gts, _ = _stats_import()
    data = gts()
    return jsonify({'success': True, 'data': data})


@chatbot_bp.route('/hot_topics', methods=['GET'])
def hot_topics():
    """获取今日热门问题。"""
    err = _require_admin()
    if err:
        return err
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from stats import get_hot_topics
        data = get_hot_topics(limit=10)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chatbot_bp.route('/agent_performance', methods=['GET'])
def agent_performance():
    """座席绩效数据。"""
    err = _require_admin()
    if err:
        return err
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from stats import get_agent_performance
        data = get_agent_performance()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chatbot_bp.route('/qa_check', methods=['POST'])
def qa_check():
    """对话质检：分析一轮对话质量。"""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id', '')
    user_query = data.get('user_query', '')
    ai_reply = data.get('ai_reply', '')
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from stats import qa_check_conversation
        result = qa_check_conversation(session_id, user_query, ai_reply)
        if result:
            return jsonify({'success': True, 'data': result})
        return jsonify({'success': False, 'error': '质检失败'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chatbot_bp.route('/copilot_suggest', methods=['POST'])
def copilot_suggest():
    """Agent Copilot：根据对话上下文，为坐席生成回复建议。"""
    data = request.get_json(silent=True) or {}
    user_query = data.get('user_query', '')
    history = data.get('history', '')  # 之前的对话记录
    if not user_query:
        return jsonify({'success': False, 'error': '缺少用户消息'}), 400
    try:
        import sys as _sys, os as _os, json as _json
        _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', '..'))
        from agent_matrix.engine import AIEngine

        context = f"对话历史：\n{history[:500]}\n\n用户最新消息：{user_query[:300]}" if history else f"用户消息：{user_query[:300]}"
        prompt = f"""你是一个 AI 坐席助手（Agent Copilot）。根据以下对话，生成 2-3 条回复建议供坐席选择。

要求：
- 每条建议用一句话，简洁专业
- 保持友好语气
- 设计解决方案导向
- 输出 JSON 数组

{context}

输出格式：{{"suggestions": ["建议1", "建议2", "建议3"]}}"""

        engine = AIEngine({'provider': 'dashscope', 'model_name': 'qwen-turbo'})
        reply = ''
        for token in engine.chat_stream([
            {'role': 'system', 'content': '你是坐席助手。只输出 JSON。'},
            {'role': 'user', 'content': prompt}
        ], temperature=0.3, max_tokens=256):
            if not token.startswith('Error:'):
                reply += token

        data = _json.loads(reply.strip())
        suggestions = data.get('suggestions', [])
        return jsonify({'success': True, 'data': {'suggestions': suggestions[:5]}})
    except Exception as e:
        logger.warning(f"[Chatbot] Copilot suggest failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ── 多渠道 Webhook 端点 ────────────────────────────────

@webhook_bp.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Telegram Bot Webhook"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from channels.router import telegram_handle_webhook
        body = request.get_json(silent=True) or {}
        ok = telegram_handle_webhook(body)
        if ok:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'ignored'}), 200
    except Exception as e:
        logger.error(f"[Telegram webhook] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@webhook_bp.route('/line/webhook', methods=['POST'])
def line_webhook():
    """LINE Messaging Webhook"""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from channels.router import line_handle_webhook
        body = request.get_json(silent=True) or {}
        ok = line_handle_webhook(body)
        if ok:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'ignored'}), 200
    except Exception as e:
        logger.error(f"[LINE webhook] {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@chatbot_bp.route('/csat', methods=['POST'])
def csat():
    """提交 CSAT 满意度评分。"""
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id', '')
    score = data.get('score', 0)
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id 不能为空'}), 400
    try:
        score = int(score)
        if score < 1 or score > 5:
            return jsonify({'success': False, 'error': '评分范围 1-5'}), 400
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': '评分无效'}), 400
    _, _, rc = _stats_import()
    ok = rc(session_id, score)
    return jsonify({'success': ok})


DEFAULT_HANDOFF_KEYWORDS = [
    "人工", "客服", "转人工", "联系真人", "联系工作人员",
    "商务", "合作", "投诉", "定制", "开发"
]


@chatbot_bp.route('/handoff_rules', methods=['GET'])
def get_handoff_rules():
    """获取转人工规则配置。"""
    err = _require_admin()
    if err:
        return err
    try:
        keywords = DEFAULT_HANDOFF_KEYWORDS
        max_fails = 3
        try:
            from .models import get_config as _gc
            kw_raw = _gc('chatbot', 'handoff_keywords')
            if kw_raw:
                keywords = json.loads(kw_raw)
            mf_raw = _gc('chatbot', 'handoff_max_fails')
            if mf_raw:
                max_fails = int(mf_raw)
        except Exception:
            pass
        return jsonify({'success': True, 'data': {
            'keywords': keywords,
            'max_fails': max_fails,
        }})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chatbot_bp.route('/handoff_rules', methods=['POST'])
def save_handoff_rules():
    """保存转人工规则配置。"""
    err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    keywords = data.get('keywords', DEFAULT_HANDOFF_KEYWORDS)
    max_fails = data.get('max_fails', 3)
    try:
        from .models import set_config as _sc
        _sc('chatbot', 'handoff_keywords', json.dumps(keywords, ensure_ascii=False))
        _sc('chatbot', 'handoff_max_fails', str(max_fails))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chatbot_bp.route('/escalate', methods=['POST'])
def escalate():
    """AI 转人工 — 创建工单。
    
    可由 api_v1.py 内部调用，或由前端直接调用。
    请求体: {title, content, contact, user_id(可选), session_id(可选)}
    """
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    contact = (data.get('contact') or '').strip()
    user_id = data.get('user_id')
    session_id = data.get('session_id')

    if not title or not content:
        return jsonify({'success': False, 'error': '标题和内容不能为空'}), 400

    result = create_ticket_from_chat(title, content, contact,
                                     user_id=user_id, session_id=session_id)
    if result['success']:
        return jsonify({'success': True, 'data': {'ticket_id': result['ticket_id']}})
    else:
        return jsonify({'success': False, 'error': result.get('error', '创建工单失败')}), 500


@chatbot_bp.route('/settings', methods=['POST'])
def save_settings():
    err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    allowed = {
        'enabled', 'auto_escalate', 'title', 'subtitle', 'welcome_message', 'help_hint',
        'avatar_url', 'agent_id', 'max_history', 'float_button_text'
    }

    try:
        pm = _get_plugin_manager()
        inst = pm.get_instance('chatbot') if pm else None
        if not inst:
            return jsonify({'success': False, 'error': 'Plugin not loaded'}), 500

        for k, v in data.items():
            if k in allowed:
                inst.set_config_value(k, v)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
