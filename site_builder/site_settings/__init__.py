#!/usr/bin/env python3
"""Site Settings — 统一站点配置模块（替代 brand_settings + header_nav + footer_* + themes）"""

from flask import Blueprint

site_settings_bp = Blueprint('site_settings', __name__, url_prefix='/admin')


def init_site_settings(app):
    """初始化站点设置模块"""
    from site_builder.site_settings.models import init_tables, migrate_from_legacy
    init_tables()
    migrate_from_legacy()

    from site_builder.site_settings.routes import register_routes
    register_routes(site_settings_bp)

    app.register_blueprint(site_settings_bp)
    print('[SiteSettings] Unified site settings module initialized')