#!/usr/bin/env python3
"""
VeroRon 维洛智能 — 独立部署订阅管理 API

功能：
1. 管理端：生成/列出/作废部署码
2. 客户端：心跳验证（部署的实例定期联系主服务器）

两种模式：
  A) 主服务器模式（本代码运行在主站）
     - 管理 deployment_codes 表
     - 响应心跳请求
  B) 客户端模式（运行在客户服务器上的部署实例）
     - 调用心跳 API 验证订阅
     - 本地缓存结果在 system_config 中

过期封锁逻辑：
  - 管理后台：心跳失败 → 仅允许访问续费页面
  - 前端网页：正常访问，不受影响
  - AI 功能：调用时返回 "subscription_expired" 错误
"""
import os, sys, json, secrets, hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'models'))
from database import get_db
from i18n import _

deploy_bp = Blueprint('deployment', __name__, url_prefix='/api/subscription')


def _require_admin():
    """验证管理员 JWT — 使用 JWT payload 中的 is_admin，避免额外 DB 查询"""
    from services.jwt_service import validate_token
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else ''
    if not token:
        token = request.cookies.get('sso_token', '') or request.cookies.get('tm_token', '')
    payload = validate_token(token) if token else None
    if not payload:
        return None, (jsonify({'success': False, 'error': _('请先登录')}), 401)
    if not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': _('需要管理员权限')}), 403)
    return payload, None


# ══════════════════════════════════════════════
# 管理端：部署码管理
# ══════════════════════════════════════════════

@deploy_bp.route('/admin/codes', methods=['GET'])
def admin_list_codes():
    """列出所有部署码"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM deployment_codes ORDER BY created_at DESC'
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@deploy_bp.route('/admin/codes/generate', methods=['POST'])
def admin_generate_code():
    """生成新的部署码（绑定到用户/套餐）"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    user_id = data.get('user_id')
    plan_key = data.get('plan_key', 'deploy_basic')
    duration_days = data.get('duration_days', 365)

    if not user_id:
        return jsonify({'success': False, 'error': _('缺少 user_id')}), 400

    # 生成唯一部署码: DC-YYYYMMDD-XXXXXX
    raw = f"{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
    code = f"DC-{raw}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]

    expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()

    with get_db() as conn:
        conn.execute('''INSERT INTO deployment_codes
            (code, code_hash, user_id, plan_key, duration_days, expires_at, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s)''',
            (code, code_hash, user_id, plan_key, duration_days, expires_at, 'active'))
        conn.commit()

    return jsonify({
        'success': True,
        'data': {
            'code': code,
            'user_id': user_id,
            'plan_key': plan_key,
            'duration_days': duration_days,
            'expires_at': expires_at,
        }
    })


@deploy_bp.route('/admin/codes/<int:code_id>/revoke', methods=['POST'])
def admin_revoke_code(code_id):
    """作废部署码"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute("UPDATE deployment_codes SET status='revoked', updated_at=CURRENT_TIMESTAMP WHERE id=%s", (code_id,))
        conn.commit()
    return jsonify({'success': True, 'message': _('部署码已作废')})


# ══════════════════════════════════════════════
# 客户端：心跳验证（部署实例调用）
# ══════════════════════════════════════════════

@deploy_bp.route('/heartbeat', methods=['POST'])
def heartbeat():
    """
    心跳验证 — 由客户部署的实例定期调用

    请求体:
        code: str — 部署码
        hostname: str — 客户服务器主机名（可选，用于记录）
        version: str — 当前版本（可选，用于版本跟踪）

    返回:
        valid: bool — 是否有效
        days_remaining: int — 剩余天数
        status: str — active / expired / revoked
        message: str — 提示信息
    """
    data = request.get_json(force=True) or {}
    code = data.get('code', '').strip()
    hostname = data.get('hostname', '')
    version = data.get('version', '')

    if not code:
        return jsonify({'success': False, 'error': _('缺少部署码')}), 400

    now = datetime.now()

    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM deployment_codes WHERE code=%s',
            (code,)
        ).fetchone()

    if not row:
        return jsonify({
            'success': True,
            'data': {'valid': False, 'status': 'not_found', 'message': _('部署码不存在')}
        })

    d = dict(row)

    # 检查状态
    if d['status'] == 'revoked':
        return jsonify({
            'success': True,
            'data': {'valid': False, 'status': 'revoked', 'message': _('部署码已被作废')}
        })

    # 检查有效期
    expires_at = datetime.fromisoformat(d['expires_at']) if d['expires_at'] else now
    days_remaining = (expires_at - now).days
    is_valid = d['status'] == 'active' and days_remaining >= 0

    # 更新最后心跳时间
    if is_valid:
        with get_db() as conn:
            conn.execute(
                "UPDATE deployment_codes SET last_heartbeat=CURRENT_TIMESTAMP, last_hostname=%s, last_version=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                (hostname[:200], version[:50], d['id'])
            )
            conn.commit()

    return jsonify({
        'success': True,
        'data': {
            'valid': is_valid,
            'days_remaining': max(days_remaining, 0),
            'status': 'active' if is_valid else 'expired',
            'message': _('订阅有效') if is_valid else _('订阅已过期，请续费'),
            'plan_key': d['plan_key'],
        }
    })


@deploy_bp.route('/check', methods=['GET'])
def check_subscription_public():
    """
    公共查询：根据部署码查询订阅状态
    用于部署期间的安装验证
    """
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'success': False, 'error': _('缺少部署码')}), 400

    with get_db() as conn:
        row = conn.execute(
            'SELECT code, plan_key, status, expires_at, created_at FROM deployment_codes WHERE code=%s',
            (code,)
        ).fetchone()

    if not row:
        return jsonify({'success': False, 'error': _('部署码不存在')}), 404

    d = dict(row)
    now = datetime.now()
    expires_at = datetime.fromisoformat(d['expires_at']) if d['expires_at'] else now

    return jsonify({
        'success': True,
        'data': {
            'code': d['code'],
            'plan_key': d['plan_key'],
            'status': d['status'],
            'expires_at': d['expires_at'],
            'days_remaining': max((expires_at - now).days, 0),
            'is_valid': d['status'] == 'active' and expires_at > now,
        }
    })


# ══════════════════════════════════════════════
# 初始化表（幂等）
# ══════════════════════════════════════════════

def init_deployment_tables():
    """创建 deployment_codes 表"""
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS deployment_codes (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            code            TEXT UNIQUE NOT NULL,
            code_hash       TEXT NOT NULL,
            user_id         BIGINT NOT NULL,
            plan_key        TEXT NOT NULL DEFAULT 'deploy_basic',
            duration_days   BIGINT NOT NULL DEFAULT 365,
            expires_at      TEXT NOT NULL,
            status          TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','used','expired','revoked')),
            last_heartbeat  TEXT,
            last_hostname   TEXT DEFAULT '',
            last_version    TEXT DEFAULT '',
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_dc_code ON deployment_codes(code)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_dc_user ON deployment_codes(user_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_dc_status ON deployment_codes(status)')
        conn.commit()
    print('[DeploymentAPI] ✅ deployment_codes table ready')
