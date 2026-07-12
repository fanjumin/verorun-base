import json
import sys
import os
from flask import Blueprint, request, jsonify, g


chatbot_bp = Blueprint('chatbot_admin', __name__)


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
        pm = request.app.extensions.get('plugin_manager')
    return pm


@chatbot_bp.route('/settings', methods=['GET'])
def get_settings():
    err = _require_admin()
    if err:
        return err

    keys = [
        'enabled', 'title', 'subtitle', 'welcome_message', 'help_hint',
        'avatar_url', 'agent_id', 'max_history', 'float_button_text'
    ]

    try:
        pm = _get_plugin_manager()
        inst = pm.get_instance('chatbot') if pm else None
        cfg = {k: inst.get_config_value(k) if inst else '' for k in keys}
        return jsonify({'success': True, 'data': cfg})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@chatbot_bp.route('/settings', methods=['POST'])
def save_settings():
    err = _require_admin()
    if err:
        return err

    data = request.get_json() or {}
    allowed = {
        'enabled', 'title', 'subtitle', 'welcome_message', 'help_hint',
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
