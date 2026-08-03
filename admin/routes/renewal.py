#!/usr/bin/env python3
"""
VeroRon 维洛智能 — 订阅续费页面路由

过期封锁时，用户唯一可访问的管理后台页面。
展示订阅状态、剩余天数，引导用户前往官网续费。
"""
from flask import Blueprint, render_template, jsonify, request
import os, sys

renew_bp = Blueprint('renewal', __name__, url_prefix='/admin')


@renew_bp.route('/renew')
def renew_page():
    """续费页面 — 展示订阅状态和续费指引"""
    try:
        from services.license_service import LicenseService
        ls = LicenseService()
        status = ls.get_status()
    except Exception as e:
        print(f'[Renewal] LicenseService error: {e}')
        status = {
            'valid': False,
            'days_remaining': 0,
            'status': 'unknown',
            'message': '无法获取授权信息',
            'needs_refresh': False,
        }

    return render_template('renew.html', license=status)


@renew_bp.route('/api/license-status')
def license_status_api():
    """API: 获取当前授权状态（前端 AJAX 刷新用）"""
    try:
        from services.license_service import LicenseService
        ls = LicenseService()
        status = ls.get_status()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'data': status})


@renew_bp.route('/api/license-refresh', methods=['POST'])
def license_refresh_api():
    """API: 主动刷新授权状态（调用主服务器心跳）"""
    try:
        from services.license_service import LicenseService
        ls = LicenseService()
        status = ls.refresh()
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'data': status})
