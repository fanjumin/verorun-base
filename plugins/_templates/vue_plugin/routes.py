#!/usr/bin/env python3
"""
Vue Demo Plugin — routes

iframe 页面路由（§15.4）：/admin/vue-demo/
  - 页面通过 `?token=` 接收 goPlugin() 注入的 SSO token
  - before_request 校验管理员 JWT（Header / ?token= / Cookie 三通道，与 analytics 同模式）
"""
import os
import sys

# 项目根 + auth-center（与现插件同模式，须置于 Admin app 内运行）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'auth-center'))

from flask import Blueprint, request, jsonify, render_template, redirect, g

from i18n import _

vue_demo_bp = Blueprint(
    'vue_demo', __name__,
    url_prefix='/admin/vue-demo',
    template_folder='templates',
    static_folder='static',
    static_url_path='/admin/vue-demo/static',
)

# 静态资源免鉴权（iframe 加载时静态文件不带 token）
_AUTH_EXEMPT_PATHS = ('/admin/vue-demo/static',)


@vue_demo_bp.before_request
def _check_auth():
    path = request.path
    for exempt in _AUTH_EXEMPT_PATHS:
        if path.startswith(exempt):
            return None

    from services.jwt_service import validate_token
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.args.get('token')
    if not token:
        token = request.cookies.get('sso_token') or request.cookies.get('tm_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        if request.is_json:
            return jsonify({'success': False, 'error': _('Unauthorized')}), 401
        # 非 JSON 直接跳登录（与 unlogged 访问规则一致，无中间提示）
        return redirect('/admin/login')
    g.admin_token = token
    return None


@vue_demo_bp.route('/')
def index():
    """渲染 iframe 页面：注入 SSO token + i18n 字典（window.__t）"""
    token = request.args.get('token') or request.cookies.get('sso_token') or ''
    return render_template(
        'index.html',
        sso_token=token,
        translations={
            'demo.title': _('Vue Plugin Demo'),
            'demo.desc': _('This page is rendered by Vue 3 (local UMD, no CDN).'),
            'demo.token': _('SSO token'),
            'demo.call': _('Call API'),
        },
    )


@vue_demo_bp.route('/api/hello')
def hello():
    """示例同域 API（前端携带 Authorization: Bearer <token> 访问）"""
    return jsonify({'success': True, 'message': 'Hello from Vue plugin', 'plugin': 'vue_plugin'})
