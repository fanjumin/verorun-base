"""Captcha Flask Blueprint — 【已迁移】2026-08-06 迁移至插件 plugins/captcha_embedded/routes.py。

本文件保留仅为回滚兜底，主系统（admin/app.py）与插件均不再引用。
待插件新路由验证通过后，删除本文件需用户单独批准。

迁移前说明：
  端点：
    GET  /api/captcha/generate   → 生成拼图挑战
    POST /api/captcha/verify     → 验证位置 + 行为分析
    POST /api/captcha/consume    → 一次性消费 Token
    GET  /api/admin/captcha/stats → 统计数据
"""
import sys, os

# Ensure captcha-service/ is importable from admin's cwd
CAPTCHA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'captcha-service')
if CAPTCHA_DIR not in sys.path:
    sys.path.insert(0, CAPTCHA_DIR)

from flask import Blueprint, request, jsonify

from captcha.generator import generate_puzzle
from captcha.security import generate_token, verify_token
from captcha.store import (
    save_challenge, consume_challenge, peek_challenge,
    check_rate_limit, record_fail, check_ip_blocked, record_stat, get_stats,
)
from captcha.behavior import analyze_trajectory, compute_risk
from config import TOLERANCE, RISK_THRESHOLD

captcha_bp = Blueprint('captcha', __name__, url_prefix='/api/captcha')

# i18n 桥接 — 由插件 on_enable 注入
_t = lambda s: s


def init_i18n(t_func):
    global _t
    _t = t_func


def _client_ip():
    """从请求中提取客户端 IP。"""
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.headers.get('X-Real-IP', request.remote_addr or 'unknown')


# ── /generate ──────────────────────────────────────────────

@captcha_bp.route('/generate', methods=['GET'])
def captcha_generate():
    ip = _client_ip()
    if check_ip_blocked(ip):
        return jsonify({'error': _t('IP blocked')}), 403

    rate = check_rate_limit(ip)
    if not rate['allowed']:
        return jsonify({'error': f'{_t("Too many attempts")}, retry in {rate["reset_after"]}s'}), 429

    try:
        puzzle = generate_puzzle()
    except Exception as e:
        return jsonify({'error': f'{_t("Puzzle generation failed")}: {e}'}), 500

    token = generate_token(
        puzzle['hole']['x'], puzzle['hole']['y'],
        puzzle['image_id'],
        puzzle['hole']['w'], puzzle['hole']['h'],
    )
    save_challenge(token, puzzle['hole']['x'], puzzle['hole']['y'],
                   puzzle['image_id'], puzzle['hole']['w'], puzzle['hole']['h'])

    return jsonify({
        'token': token,
        'background': puzzle['background_b64'],
        'hole': puzzle['hole'],
        'pieces': puzzle['pieces'],
    })


# ── /verify ────────────────────────────────────────────────

@captcha_bp.route('/verify', methods=['POST'])
def captcha_verify():
    ip = _client_ip()
    data = request.get_json() or {}
    token = data.get('token', '')
    drag_distance = data.get('drag_distance', 0)
    drag_trace_raw = data.get('drag_trace', [])

    if check_ip_blocked(ip):
        return jsonify({'success': False, 'risk_score': 0, 'next_action': 'block', 'detail': _t('IP blocked')})

    rate = check_rate_limit(ip)
    if not rate['allowed']:
        return jsonify({'success': False, 'risk_score': 0, 'next_action': 'block', 'detail': _t('Rate limited')})

    payload = verify_token(token)
    if payload is None:
        record_fail(ip)
        return jsonify({'success': False, 'risk_score': 0, 'next_action': 'refresh', 'detail': _t('Invalid or expired token')})

    stored = peek_challenge(token)
    if stored is None:
        record_fail(ip)
        return jsonify({'success': False, 'risk_score': 0, 'next_action': 'refresh', 'detail': _t('Token not found or already used')})

    target_x = int(stored.get('target_x', -1))
    target_y = int(stored.get('y_position', 0))

    # 位置匹配
    position_match = False
    if drag_trace_raw and len(drag_trace_raw) >= 2:
        last = drag_trace_raw[-1]
        dx = abs(last.get('x', 0) - target_x)
        dy = abs(last.get('y', 0) - target_y)
        position_match = dx <= 20 and dy <= 20
    elif abs(drag_distance - target_x) <= TOLERANCE:
        position_match = True

    # 行为分析（将 dict 列表转为 TracePoint 兼容对象）
    behavior = {'human_score': 0.5, 'risk_level': 'medium'}
    if drag_trace_raw and len(drag_trace_raw) >= 3:
        from collections import namedtuple
        TracePt = namedtuple('TracePt', ['t', 'x', 'y'])
        trace_pts = [TracePt(p['t'], p['x'], p['y']) for p in drag_trace_raw]
        behavior = analyze_trajectory(trace_pts, target_x)

    risk = compute_risk(position_match, behavior)
    passed = risk >= RISK_THRESHOLD

    record_stat(passed, risk, ip)
    if not passed:
        record_fail(ip)

    if passed:
        return jsonify({'success': True, 'risk_score': risk, 'next_action': 'ok'})
    elif behavior.get('risk_level') == 'high':
        return jsonify({'success': False, 'risk_score': risk, 'next_action': 'refresh', 'detail': _t('Suspicious activity detected')})
    else:
        return jsonify({'success': False, 'risk_score': risk, 'next_action': 'refresh', 'detail': _t('Position mismatch')})


# ── /consume ───────────────────────────────────────────────

@captcha_bp.route('/consume', methods=['POST'])
def captcha_consume():
    data = request.get_json() or {}
    token = data.get('token', '')
    payload = verify_token(token)
    if payload is None:
        return jsonify({'valid': False, 'reason': 'invalid_token'})
    stored = consume_challenge(token)
    if stored is None:
        return jsonify({'valid': False, 'reason': 'already_used_or_expired'})
    return jsonify({'valid': True})


# ── Admin stats ──


@captcha_bp.route('/admin/stats/', methods=['GET'])
def admin_captcha_stats():
    return jsonify(get_stats())
