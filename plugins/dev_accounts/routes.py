#!/usr/bin/env python3
"""Developer Accounts — API routes

Prefix: /admin/dev-accounts/
"""

from flask import Blueprint, request, jsonify
from services.jwt_service import validate_token

dev_accounts_bp = Blueprint('dev_accounts_api', __name__, url_prefix='/admin/dev-accounts')


def _ok(data=None):
    return jsonify({'success': True, 'data': data})


def _err(msg, code=400):
    return jsonify({'success': False, 'error': msg}), code


def _require_admin():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        token = request.args.get('token') or request.cookies.get('sso_token') or request.cookies.get('tm_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return _err('Requires admin permissions', 403)


@dev_accounts_bp.route('/', methods=['GET'])
def list_accounts():
    err = _require_admin()
    if err: return err
    """List all developer accounts."""
    platform = request.args.get('platform', None)
    try:
        from .models import get_all
        accounts = get_all(platform=platform)
        return _ok(accounts)
    except Exception as e:
        return _err(str(e), 500)


@dev_accounts_bp.route('/<int:account_id>', methods=['GET'])
def get_account(account_id):
    err = _require_admin()
    if err: return err
    """Get a single developer account."""
    try:
        from .models import get_by_id
        account = get_by_id(account_id)
        if not account:
            return _err('Account not found', 404)
        return _ok(account)
    except Exception as e:
        return _err(str(e), 500)


@dev_accounts_bp.route('/', methods=['POST'])
def create_account():
    err = _require_admin()
    if err: return err
    """Create a new developer account."""
    data = request.get_json(force=True, silent=True) or {}
    platform = data.get('platform', '')
    account_name = data.get('account_name', '')

    if not platform:
        return _err('platform is required', 400)
    if not account_name:
        return _err('account_name is required', 400)
    if platform not in ('douyin', 'toutiao', 'wechat', 'telegram', 'line'):
        return _err(f'Unsupported platform: {platform}', 400)

    try:
        from .models import create
        account_id = create(
            platform=platform,
            account_name=account_name,
            app_id=data.get('app_id', ''),
            app_secret=data.get('app_secret', ''),
            bot_token=data.get('bot_token', ''),
            channel_id=data.get('channel_id', ''),
            channel_secret=data.get('channel_secret', ''),
            access_token=data.get('access_token', ''),
            extra_config=data.get('extra_config', {}),
            is_active=data.get('is_active', 1),
        )
        return _ok({'id': account_id})
    except Exception as e:
        return _err(str(e), 500)


@dev_accounts_bp.route('/<int:account_id>', methods=['PUT'])
def update_account(account_id):
    err = _require_admin()
    if err: return err
    """Update an existing developer account."""
    data = request.get_json(force=True, silent=True) or {}
    if not data:
        return _err('No data provided', 400)

    try:
        from .models import update
        ok = update(account_id, **data)
        if not ok:
            return _err('No valid fields to update', 400)
        return _ok({'updated': True})
    except Exception as e:
        return _err(str(e), 500)


@dev_accounts_bp.route('/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    err = _require_admin()
    if err: return err
    """Delete a developer account."""
    try:
        from .models import delete
        delete(account_id)
        return _ok({'deleted': True})
    except Exception as e:
        return _err(str(e), 500)


@dev_accounts_bp.route('/<int:account_id>/test', methods=['POST'])
def test_account(account_id):
    err = _require_admin()
    if err: return err
    """Test connection for a developer account."""
    try:
        from .models import test_connection
        result = test_connection(account_id)
        return jsonify(result)
    except Exception as e:
        return _err(str(e), 500)