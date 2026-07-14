#!/usr/bin/env python3
"""
Payment Plugin — /admin/payment/configs 配置管理路由
====================================================
支付凭证存储在插件独立数据库 payment.db（payment_configs 表），
完全独立于主库 system_config。
"""
import os
import sys

from flask import Blueprint, request, jsonify

# 首次导入时初始化独立数据库
from plugins.payment.models import init_payment_tables, migrate_from_main_db
init_payment_tables()
migrate_from_main_db()

payment_admin_bp = Blueprint('payment_admin', __name__, url_prefix='/admin/payment')

# 支持的提供商及字段定义
PAYMENT_PROVIDERS = {
    'alipay': {
        'label': 'Alipay',
        'label_zh': '支付宝',
        'market': 'cn',
        'fields': [
            {'key': 'app_id', 'label': 'Alipay App ID', 'label_zh': '支付宝 App ID', 'type': 'text'},
            {'key': 'private_key', 'label': 'Alipay Private Key', 'label_zh': '支付宝支付私钥', 'type': 'password'},
            {'key': 'public_key', 'label': 'Alipay Public Key', 'label_zh': '支付宝支付公钥', 'type': 'password'},
            {'key': 'notify_base', 'label': 'Payment Callback Domain', 'label_zh': '支付回调域名', 'type': 'text'},
            {'key': 'sandbox', 'label': 'Sandbox Mode', 'label_zh': '沙箱模式', 'type': 'checkbox', 'hint': 'Use Alipay sandbox environment for testing', 'hint_zh': '使用支付宝沙箱环境进行测试'},
        ]
    },
    'wechat': {
        'label': 'WeChat Pay',
        'label_zh': '微信支付',
        'market': 'cn',
        'fields': [
            {'key': 'app_id', 'label': 'WeChat Pay AppID', 'label_zh': '微信支付 AppID', 'type': 'text'},
            {'key': 'mchid', 'label': 'WeChat Merchant ID', 'label_zh': '微信支付商户号', 'type': 'text'},
            {'key': 'api_v3_key', 'label': 'WeChat Pay API V3 Key', 'label_zh': '微信支付 API V3 密钥', 'type': 'password'},
            {'key': 'cert_serial', 'label': 'WeChat Cert Serial Number', 'label_zh': '微信支付证书序列号', 'type': 'text'},
            {'key': 'plan_id', 'label': 'WeChat Pay Plan ID', 'label_zh': '微信支付扣费计划ID', 'type': 'text'},
        ]
    },
    'stripe': {
        'label': 'Stripe',
        'label_zh': 'Stripe',
        'market': 'intl',
        'fields': [
            {'key': 'secret_key', 'label': 'Secret Key', 'label_zh': 'Secret Key', 'type': 'password'},
            {'key': 'publishable_key', 'label': 'Publishable Key', 'label_zh': 'Publishable Key', 'type': 'text'},
            {'key': 'webhook_secret', 'label': 'Webhook Secret', 'label_zh': 'Webhook Secret', 'type': 'password'},
        ]
    },
    'paypal': {
        'label': 'PayPal',
        'label_zh': 'PayPal',
        'market': 'intl',
        'fields': [
            {'key': 'client_id', 'label': 'Client ID', 'label_zh': 'Client ID', 'type': 'text'},
            {'key': 'client_secret', 'label': 'Client Secret', 'label_zh': 'Client Secret', 'type': 'password'},
            {'key': 'webhook_id', 'label': 'Webhook ID', 'label_zh': 'Webhook ID', 'type': 'text'},
            {'key': 'mode', 'label': 'Mode', 'label_zh': '模式', 'type': 'select', 'options': [{'value': 'sandbox', 'label': 'Sandbox (Test)', 'label_zh': '沙箱（测试）'}, {'value': 'live', 'label': 'Live (Production)', 'label_zh': '生产环境'}], 'default': 'sandbox'},
        ]
    }
}


def _require_admin():
    from routes.admin import _require_admin as _ra
    return _ra()


def _get_db():
    from plugins.payment.models import get_payment_db
    return get_payment_db()


def _get_provider_configs(provider):
    from plugins.payment.models import get_provider_configs
    return get_provider_configs(provider)


def _set_provider_configs(provider, configs):
    from plugins.payment.models import set_provider_configs
    set_provider_configs(provider, configs)


def _log(admin_id, action, target_type='', target_id='', detail=''):
    from routes.admin import _log as _l
    _l(admin_id, action, target_type, target_id, detail)


# ── API: 获取提供商定义 ──

@payment_admin_bp.route('/providers', methods=['GET'])
def get_providers():
    """返回所有支持的提供商定义（含字段结构）"""
    a, e = _require_admin()
    if e:
        return e
    market = request.args.get('market', 'all')
    result = {}
    for k, v in PAYMENT_PROVIDERS.items():
        if market == 'all' or v['market'] == market:
            result[k] = v
    return jsonify({'success': True, 'data': result})


# ── API: 获取全部配置概览 ──

@payment_admin_bp.route('/configs', methods=['GET'])
def get_all_configs():
    """获取所有支付提供商当前配置"""
    a, e = _require_admin()
    if e:
        return e
    from plugins.payment.models import get_all_providers_summary
    summary = get_all_providers_summary()
    return jsonify({'success': True, 'data': summary})


# ── API: 获取单个提供商配置 ──

@payment_admin_bp.route('/configs/<provider>', methods=['GET'])
def get_provider_config(provider):
    """获取指定提供商的配置"""
    a, e = _require_admin()
    if e:
        return e
    if provider not in PAYMENT_PROVIDERS:
        return jsonify({'success': False, 'error': f'Unknown provider: {provider}'}), 400
    configs = _get_provider_configs(provider)
    return jsonify({'success': True, 'data': {provider: configs}})


# ── API: 保存提供商配置 ──

@payment_admin_bp.route('/configs/<provider>', methods=['PUT'])
def save_provider_config(provider):
    """保存指定提供商的配置"""
    a, e = _require_admin()
    if e:
        return e
    if provider not in PAYMENT_PROVIDERS:
        return jsonify({'success': False, 'error': f'Unknown provider: {provider}'}), 400

    body = request.get_json(silent=True) or {}
    configs = body.get('configs', {})

    _set_provider_configs(provider, configs)
    _log(a, 'update', 'payment_config', provider, f'Updated {provider} payment config ({len(configs)} fields)')

    return jsonify({'success': True, 'message': f'{provider} config saved'})


# ── API: 删除提供商配置 ──

@payment_admin_bp.route('/configs/<provider>', methods=['DELETE'])
def delete_provider_config(provider):
    """清空指定提供商的配置"""
    a, e = _require_admin()
    if e:
        return e
    if provider not in PAYMENT_PROVIDERS:
        return jsonify({'success': False, 'error': f'Unknown provider: {provider}'}), 400

    conn = _get_db()
    conn.execute('DELETE FROM payment_configs WHERE provider=?', (provider,))
    conn.commit()
    _log(a, 'delete', 'payment_config', provider, f'Cleared {provider} payment config')
    return jsonify({'success': True, 'message': f'{provider} config cleared'})


# ── API: 检查是否已配置（供支付网关调用） ──

@payment_admin_bp.route('/check/<provider>', methods=['GET'])
def check_provider_configured(provider):
    """检查提供商是否已配置完整"""
    configs = _get_provider_configs(provider)
    if provider not in PAYMENT_PROVIDERS:
        return jsonify({'success': False, 'error': f'Unknown provider: {provider}'}), 400
    required = [f['key'] for f in PAYMENT_PROVIDERS[provider]['fields'] if f['type'] == 'password']
    missing = [k for k in required if not configs.get(k)]
    return jsonify({
        'success': True,
        'data': {
            'provider': provider,
            'configured': len(missing) == 0,
            'configured_fields': list(configs.keys()),
            'missing_required': missing
        }
    })
