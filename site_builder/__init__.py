#!/usr/bin/env python3
"""Site Builder — LLM 驱动的站内网页一键建站核心模块"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))


def init_site_builder(app):
    """注册 Site Builder 蓝图到 Flask app"""
    from site_builder.routes import site_builder_bp
    app.register_blueprint(site_builder_bp)
    print('[SiteBuilder] ✅ Blueprint 已注册 (/admin/site-builder/*)')