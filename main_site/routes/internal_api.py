#!/usr/bin/env python3
"""main_site — Internal Service API (v2.1.0).

mini_app_builder 插件数据库解耦后，不再直连主库读取共享数据
（cms_posts / cms_blocks / 品牌设置 / draft tokens）。本蓝图向插件提供
只读内部 API，用 X-Internal-Token 保护（未配置 INTERNAL_SERVICE_TOKEN 时
默认仅信任本机来源，部署时应设置环境变量）。

前缀：/api/internal/*，仅供服务间调用，不对公网开放。
"""

import os

from flask import Blueprint, jsonify, request

internal_api_bp = Blueprint('internal_api', __name__, url_prefix='/api/internal')


def _authorized() -> bool:
    token = os.environ.get('INTERNAL_SERVICE_TOKEN', '')
    if not token:
        return True  # 未配置 token：默认放行（部署环境应配置）
    return request.headers.get('X-Internal-Token', '') == token


@internal_api_bp.before_request
def _guard():
    if not _authorized():
        return jsonify({'error': 'Forbidden'}), 403
    return None


@internal_api_bp.route('/brand')
def internal_brand():
    """品牌设置（site_name / tagline / colors / logo）。"""
    try:
        from services.brand_service import get_brand_settings
        return jsonify(get_brand_settings() or {})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@internal_api_bp.route('/cms/pages')
def internal_cms_pages():
    """已发布页面列表（slug/title/meta）。"""
    try:
        from models import get_db
        with get_db() as conn:
            rows = conn.execute(
                "SELECT slug, title, meta_description, updated_at FROM cms_posts "
                "WHERE status='published' AND post_type='page' ORDER BY sort_order ASC"
            ).fetchall()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@internal_api_bp.route('/cms/page/<slug>')
def internal_cms_page(slug):
    """单个已发布页面（含 blocks）。"""
    try:
        from models import get_db
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM cms_posts WHERE slug=%s AND status='published' "
                "AND post_type='page' LIMIT 1",
                (slug,)
            ).fetchone()
            if not row:
                return jsonify({'error': 'Page not found'}), 404
            page = dict(row)
            blocks = conn.execute(
                "SELECT * FROM cms_blocks WHERE post_id=%s AND status='published' "
                "ORDER BY sort_order ASC",
                (page['id'],)
            ).fetchall()
            page['blocks'] = [dict(b) for b in blocks]
        return jsonify(page)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@internal_api_bp.route('/site/draft-tokens')
def internal_draft_tokens():
    """site_builder draft tokens（生成站点时使用）。"""
    try:
        from site_builder.site_settings.models import get_draft_tokens
        return jsonify(get_draft_tokens() or {})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@internal_api_bp.route('/users/register-platform', methods=['POST'])
def internal_register_platform():
    """平台登录用户注册（get-or-create，联邦身份）。

    请求体：
        {
            "platform": "douyin|wechat|telegram|line",
            "platform_user_id": "...",
            "username": "wx_xxxx",
            "display_name": "...",
            "avatar": "..."
        }
    返回： {"id", "username", "display_name", "avatar"}

    供 mini_app_builder 插件（或未来跨服务调用方）经 X-Internal-Token 认证后调用。
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        platform = data.get('platform', '')
        platform_user_id = data.get('platform_user_id', '')
        username = data.get('username', '')
        display_name = data.get('display_name', '')
        avatar = data.get('avatar', '')
        if not platform or not platform_user_id or not username:
            return jsonify({'error': 'platform/platform_user_id/username required'}), 400

        from services.user_registry import register_or_get_platform_user
        user = register_or_get_platform_user(
            platform, platform_user_id, username, display_name, avatar)
        return jsonify(user)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
