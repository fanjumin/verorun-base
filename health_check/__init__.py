#!/usr/bin/env python3
"""
Health Check — 系统健康巡检中心
===================================
全站自动化健康巡检系统，提供：
  - 可扩展的检查框架
  - 一键手动巡检 + 定时自动巡检
  - 仪表盘总览、详细报告、历史趋势
  - 异常告警（邮件/站内信/Webhook）
  - 与 Workflow 引擎集成（自动恢复）

使用方式:
    from health_check import health_bp
    from health_check.models import init_health_tables
    app.register_blueprint(health_bp)
"""

from .routes import health_bp
from .models import init_health_tables, get_db

__all__ = ['health_bp', 'init_health_tables', 'get_db']
