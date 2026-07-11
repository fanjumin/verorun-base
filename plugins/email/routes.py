#!/usr/bin/env python3
"""
Email Plugin Routes — 邮件管理 API 路由
========================================
完全独立，使用插件 email.db + 主库 contact_messages 的 Python 级合并。
"""

import sys
import os
import io

_auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
if _auth_dir not in sys.path:
    sys.path.insert(0, _auth_dir)

from flask import Blueprint, request, jsonify, send_file

email_bp = Blueprint('email', __name__, url_prefix='/admin/email')


def _require_admin():
    """复用主系统的管理员鉴权"""
    from routes.admin import _require_admin as _ra
    return _ra()


def _log(admin_id, action, target_type='', target_id='', detail=''):
    """复用主系统的操作日志"""
    from routes.admin import _log as _l
    _l(admin_id, action, target_type, target_id, detail)


# ── GET /admin/email/inbox ──
@email_bp.route('/inbox', methods=['GET'])
def admin_email_inbox():
    admin, err = _require_admin()
    if err:
        return err
    from plugins.email.services import fetch_inbox
    try:
        emails = fetch_inbox(per_page=50)
        return jsonify({'success': True, 'data': emails})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── GET /admin/email/read/<uid> ──
@email_bp.route('/read/<int:uid>', methods=['GET'])
def admin_email_read(uid):
    admin, err = _require_admin()
    if err:
        return err
    from plugins.email.services import read_email
    try:
        email_data = read_email(uid)
        return jsonify({'success': True, 'data': email_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── POST /admin/email/send ──
@email_bp.route('/send', methods=['POST'])
def admin_email_send():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    to_addr = data.get('to', '').strip()
    subject = data.get('subject', '').strip()
    body = data.get('body', '').strip()
    body_html = data.get('body_html', '')
    attachments = data.get('attachments')
    reply_to_uid = data.get('reply_to_uid')
    if not to_addr or not subject or (not body and not body_html):
        return jsonify({'success': False, 'error': '收件人、主题、内容不能为空'}), 400
    from plugins.email.services import send_email
    try:
        ok, msg = send_email(to_addr, subject, body or '',
                             body_html=body_html or None,
                             reply_to=reply_to_uid,
                             attachments=attachments)
        if not ok:
            return jsonify({'success': False, 'error': msg}), 400
        _log(admin['user_id'], 'send_email', 'email', '', f'To: {to_addr}, Subject: {subject}')
        return jsonify({'success': True, 'data': {'message': msg}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── GET /admin/email/sent ──
@email_bp.route('/sent', methods=['GET'])
def admin_email_sent():
    admin, err = _require_admin()
    if err:
        return err
    from plugins.email.services import get_sent_emails
    try:
        emails = get_sent_emails(per_page=50)
        return jsonify({'success': True, 'data': emails})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── GET /admin/email/contacts ──
@email_bp.route('/contacts', methods=['GET'])
def admin_email_contacts():
    """合并已发送邮件联系人 + 联系表单联系人（Python 级合并，不依赖 SQL JOIN）"""
    admin, err = _require_admin()
    if err:
        return err
    contacts = {}

    # 1. 从 email.db 读取已发送邮件中的联系人
    from plugins.email.services import get_sent_emails
    sent = get_sent_emails(page=1, per_page=999)
    for item in sent.get('items', []):
        to_addrs = [a.strip() for a in item['to_addr'].split(',') if a.strip()]
        for addr in to_addrs:
            if addr not in contacts:
                contacts[addr] = {'email': addr, 'name': '', 'source': 'sent', 'count': 0}
            contacts[addr]['count'] += 1

    # 2. 从主库 contact_messages 读取联系表单提交的联系人
    try:
        from models import get_db
        with get_db() as conn:
            rows = conn.execute(
                "SELECT DISTINCT email, name FROM contact_messages WHERE email IS NOT NULL AND email != ''"
            ).fetchall()
            for r in rows:
                addr = r['email'].strip().lower()
                if addr not in contacts:
                    contacts[addr] = {'email': addr, 'name': r['name'] or '', 'source': 'contact', 'count': 0}
                if r['name']:
                    contacts[addr]['name'] = r['name']
    except Exception:
        pass  # contact_messages 表可能不存在，静默跳过

    return jsonify({'success': True, 'data': sorted(contacts.values(), key=lambda c: -c['count'])})


# ── GET /admin/email/attachment/<uid>/<filename> ──
@email_bp.route('/attachment/<int:uid>/<path:filename>', methods=['GET'])
def admin_email_attachment(uid, filename):
    admin, err = _require_admin()
    if err:
        return err
    from plugins.email.services import get_attachment
    data, content_type = get_attachment(uid, filename)
    if data is None:
        return jsonify({'success': False, 'error': content_type}), 404
    return send_file(
        io.BytesIO(data),
        mimetype=content_type or 'application/octet-stream',
        as_attachment=True,
        download_name=filename,
    )