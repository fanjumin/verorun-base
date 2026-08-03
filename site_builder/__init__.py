#!/usr/bin/env python3
"""Site Builder — LLM 驱动的站内网页一键建站核心模块

包含两个子模块：
  - site_builder/          → 提示词模板 + 建站任务 + 口令控制台集成
  - site_builder/site_settings/ → 统一设计令牌系统（替代 brand_settings + header_nav + footer_* + themes）
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))


def init_site_builder(app):
    """注册 Site Builder 蓝图到 Flask app"""
    # 注册站点设置（统一令牌系统）
    from site_builder.site_settings import init_site_settings
    init_site_settings(app)

    # 注册建站任务 API
    from site_builder.routes import site_builder_bp
    app.register_blueprint(site_builder_bp)
    print('[SiteBuilder] ✅ Blueprints 已注册 (/admin/site-builder/*, /admin/site-settings/*)')