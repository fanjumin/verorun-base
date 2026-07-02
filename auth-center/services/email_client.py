#!/usr/bin/env python3
"""邮件客户端 — IMAP 收信 + SMTP 发信 + 附件
   配置来源：DB system_config → 环境变量 → 默认值"""
import os, re, email, quopri, base64, json
from email.header import decode_header
import imaplib
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.utils import formataddr, parsedate_to_datetime
from models import get_db, now_iso

_MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB

# ── Config keys shared with mail_service.py ──
_MAIL_KEYS = ['smtp_host','smtp_port','smtp_user','smtp_pass','smtp_from','imap_host','imap_port']
_DEFAULTS  = {
    'smtp_host': 'smtp.qiye.aliyun.com', 'smtp_port': '465',
    'smtp_user': '', 'smtp_pass': '', 'smtp_from': '',
    'imap_host': 'imap.qiye.aliyun.com', 'imap_port': '993',
}
_ENV_MAP = {
    'smtp_host': 'SMTP_HOST', 'smtp_port': 'SMTP_PORT',
    'smtp_user': 'SMTP_USER', 'smtp_pass': 'SMTP_PASS',
    'smtp_from': 'SMTP_FROM', 'imap_host': 'IMAP_HOST', 'imap_port': 'IMAP_PORT',
}

def _get_mail_config():
    """Merge DB → env → defaults for all mail config keys."""
    result = {}
    try:
        keys = list(_MAIL_KEYS)
        placeholders = ','.join('?' for _ in keys)
        with get_db() as conn:
            rows = conn.execute(
                f"SELECT key, value FROM system_config WHERE key IN ({placeholders})", keys
            ).fetchall()
            for r in rows:
                result[r['key']] = r['value']
    except Exception:
        pass
    cfg = {}
    for k in _MAIL_KEYS:
        v = result.get(k) or os.environ.get(_ENV_MAP[k], '') or _DEFAULTS[k]
        cfg[k] = v
    if not cfg['smtp_from']:
        cfg['smtp_from'] = cfg['smtp_user']
    if not cfg['smtp_user']:
        cfg['smtp_user'] = cfg['smtp_from']
    try:
        cfg['smtp_port'] = int(cfg['smtp_port'])
    except (ValueError, TypeError):
        cfg['smtp_port'] = 465
    try:
        cfg['imap_port'] = int(cfg['imap_port'])
    except (ValueError, TypeError):
        cfg['imap_port'] = 993
    return cfg


# ─── IMAP ───

def _connect_imap():
    cfg = _get_mail_config()
    imap = imaplib.IMAP4_SSL(cfg['imap_host'], cfg['imap_port'])
    imap.login(cfg['smtp_user'], cfg['smtp_pass'])
    imap.select("INBOX")
    return imap

def _decode_mime_header(val):
    if not val:
        return ""
    parts = decode_header(val)
    result = []
    for data, charset in parts:
        if isinstance(data, bytes):
            try:
                result.append(data.decode(charset or "utf-8", errors="replace"))
            except:
                result.append(data.decode("utf-8", errors="replace"))
        else:
            result.append(str(data))
    return "".join(result)

def _decode_body(payload, encoding=None):
    if encoding:
        try:
            if encoding.lower() in ("base64", "b"):
                payload = base64.b64decode(payload)
            elif encoding.lower() in ("quoted-printable", "q"):
                payload = quopri.decodestring(payload)
        except:
            pass
    if isinstance(payload, bytes):
        for cs in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                return payload.decode(cs)
            except:
                continue
        return payload.decode("utf-8", errors="replace")
    return payload

def _get_text_from_part(part):
    ct = part.get_content_type()
    encoding = part.get("Content-Transfer-Encoding", "")
    payload = part.get_payload(decode=True)
    if ct == "text/plain":
        return _decode_body(payload, encoding)
    elif ct == "text/html":
        return _decode_body(payload, encoding)  # return html too
    return None

def _get_email_body(msg):
    """Return (plain_text, html_text) tuple."""
    plain_text, html_text = None, None
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if part.is_multipart():
                continue
            encoding = part.get("Content-Transfer-Encoding", "")
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            if ct == "text/plain":
                plain_text = _decode_body(payload, encoding)
            elif ct == "text/html":
                html_text = _decode_body(payload, encoding)
    else:
        ct = msg.get_content_type()
        encoding = msg.get("Content-Transfer-Encoding", "")
        payload = msg.get_payload(decode=True)
        if ct == "text/plain":
            plain_text = _decode_body(payload, encoding)
        elif ct == "text/html":
            html_text = _decode_body(payload, encoding)
    return plain_text or "(无文本内容)", html_text

def _get_attachments_from_msg(msg):
    """Extract attachment info from email message."""
    attachments = []
    if not msg.is_multipart():
        return attachments
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get_content_maintype() == 'text':
            continue
        filename = part.get_filename()
        if not filename:
            continue
        filename = _decode_mime_header(filename)
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        # Check size
        if len(payload) > _MAX_ATTACHMENT_SIZE:
            attachments.append({
                "filename": filename,
                "size": len(payload),
                "content_type": part.get_content_type(),
                "too_large": True,
            })
            continue
        attachments.append({
            "filename": filename,
            "size": len(payload),
            "content_type": part.get_content_type(),
            "data": base64.b64encode(payload).decode(),
            "too_large": False,
        })
    return attachments

def fetch_inbox(page=1, per_page=20):
    try:
        imap = _connect_imap()
    except Exception as e:
        return {"error": f"IMAP 连接失败: {e}", "items": [], "total": 0}
    try:
        status, data = imap.search(None, "ALL")
        if status != "OK":
            return {"error": "无法搜索收件箱", "items": [], "total": 0}
        all_uids = data[0].split()
        total = len(all_uids)
        start = max(0, total - page * per_page)
        end = max(0, total - (page - 1) * per_page)
        page_uids = all_uids[start:end] if start < end else []
        page_uids = list(reversed(page_uids))
        items = []
        for uid in page_uids:
            items.append(_fetch_one_inbox(imap, uid))
        imap.logout()
        return {"items": [i for i in items if i], "total": total, "page": page, "per_page": per_page, "pages": max(1, (total + per_page - 1) // per_page)}
    except Exception as e:
        try: imap.logout()
        except Exception as logout_e:
            import logging
            logging.warning(f"[Email] Failed to logout IMAP: {logout_e}")
        return {"error": str(e), "items": [], "total": 0}

def _fetch_one_inbox(imap, uid):
    """Fetch one email's metadata + attachment count for inbox list."""
    try:
        status, msg_data = imap.fetch(uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)] BODYSTRUCTURE)")
        if status != "OK":
            return None
        raw_header = msg_data[0][1] if isinstance(msg_data[0], tuple) else b""
        msg = email.message_from_bytes(raw_header)
        subject = _decode_mime_header(msg.get("Subject", "(无主题)"))
        _from = _decode_mime_header(msg.get("From", ""))
        date_str = msg.get("Date", "")
        
        # Check for attachments by looking at BODYSTRUCTURE
        has_attachments = False
        raw_flags = msg_data[0][0] if isinstance(msg_data[0], tuple) else b""
        
        # Full bodystructure available?
        if len(msg_data[0]) > 2:
            bodystructure = str(msg_data[0][2])
            has_attachments = '("attachment"' in bodystructure.lower() or 'name="' in bodystructure.lower()
        
        return {
            "uid": int(uid.decode() if isinstance(uid, bytes) else uid),
            "from": _from,
            "subject": subject,
            "date": date_str,
            "is_seen": b"\\Seen" in raw_flags if isinstance(raw_flags, bytes) else False,
            "has_attachments": has_attachments,
        }
    except:
        return None

def read_email(uid):
    try:
        imap = _connect_imap()
    except Exception as e:
        return {"error": f"IMAP 连接失败: {e}"}
    try:
        uid_bytes = str(uid).encode() if isinstance(uid, int) else uid.encode() if isinstance(uid, str) else uid
        status, msg_data = imap.uid("fetch", uid_bytes, "(BODY[])")
        if status != "OK":
            imap.logout()
            return {"error": "无法读取邮件"}
        raw_email = msg_data[0][1] if isinstance(msg_data[0], tuple) else b""
        msg = email.message_from_bytes(raw_email)
        subject = _decode_mime_header(msg.get("Subject", "(无主题)"))
        _from = _decode_mime_header(msg.get("From", ""))
        _to = _decode_mime_header(msg.get("To", ""))
        _cc = _decode_mime_header(msg.get("Cc", ""))
        date_str = msg.get("Date", "")
        body_plain, body_html = _get_email_body(msg)
        attachments = _get_attachments_from_msg(msg)
        imap.uid("store", uid_bytes, "+FLAGS", "\\Seen")
        imap.logout()
        return {
            "uid": int(uid) if isinstance(uid, int) else uid,
            "from": _from, "to": _to, "cc": _cc,
            "subject": subject, "date": date_str,
            "body": body_plain, "body_html": body_html,
            "attachments": attachments,
        }
    except Exception as e:
        try: imap.logout()
        except Exception as logout_e:
            import logging
            logging.warning(f"[Email] Failed to logout IMAP: {logout_e}")
        return {"error": str(e)}

def get_attachment(uid, filename):
    """Extract a specific attachment from an email by UID and filename."""
    try:
        imap = _connect_imap()
    except Exception as e:
        return None, str(e)
    try:
        uid_bytes = str(uid).encode() if isinstance(uid, int) else uid.encode() if isinstance(uid, str) else uid
        status, msg_data = imap.uid("fetch", uid_bytes, "(BODY[])")
        if status != "OK":
            imap.logout()
            return None, "无法读取邮件"
        raw_email = msg_data[0][1] if isinstance(msg_data[0], tuple) else b""
        msg = email.message_from_bytes(raw_email)
        attachments = _get_attachments_from_msg(msg)
        imap.logout()
        for att in attachments:
            if att["filename"] == filename and not att.get("too_large"):
                data = base64.b64decode(att["data"])
                return data, att["content_type"]
        return None, "附件不存在"
    except Exception as e:
        try: imap.logout()
        except Exception as logout_e:
            import logging
            logging.warning(f"[Email] Failed to logout IMAP: {logout_e}")
        return None, str(e)


# ─── SMTP ───

def send_email(to_addr, subject, body_text, body_html=None, reply_to=None, attachments=None):
    """Send email with optional HTML body and file attachments.
    attachments: list of {"filename": str, "data": base64_str, "content_type": str}
    """
    cfg = _get_mail_config()
    if not cfg['smtp_user'] or not cfg['smtp_pass']:
        return False, "SMTP 未配置 (请先设置 smtp_user/smtp_pass)"
    if isinstance(to_addr, str):
        to_addr = [to_addr]
    
    # Validate attachment sizes
    total_attach_size = 0
    if attachments:
        for att in attachments:
            data = base64.b64decode(att["data"]) if isinstance(att["data"], str) else att["data"]
            total_attach_size += len(data)
            if len(data) > _MAX_ATTACHMENT_SIZE:
                return False, f"附件 {att['filename']} 超过 10MB 限制"
    if total_attach_size > 50 * 1024 * 1024:
        return False, "附件总大小超过 50MB 限制"
    
    # Build message
    if attachments:
        # Mixed multipart for attachments
        msg = MIMEMultipart("mixed")
        msg_alt = MIMEMultipart("alternative")
        msg.attach(msg_alt)
        body_container = msg_alt
    else:
        msg = MIMEMultipart("alternative")
        body_container = msg
    
    msg["Subject"] = subject
    msg["From"] = cfg['smtp_from']
    msg["To"] = ", ".join(to_addr)
    if reply_to:
        msg["Reply-To"] = reply_to
    msg["Date"] = email.utils.formatdate(localtime=True)
    
    if body_html:
        body_container.attach(MIMEText(body_text, "plain", "utf-8"))
        body_container.attach(MIMEText(body_html, "html", "utf-8"))
    else:
        body_container.attach(MIMEText(body_text, "plain", "utf-8"))
    
    # Attachments
    if attachments:
        for att in attachments:
            data = base64.b64decode(att["data"]) if isinstance(att["data"], str) else att["data"]
            part = MIMEApplication(data, Name=att["filename"])
            part["Content-Disposition"] = f'attachment; filename="{att["filename"]}"'
            msg.attach(part)
    
    try:
        if cfg['smtp_port'] == 465:
            with smtplib.SMTP_SSL(cfg['smtp_host'], cfg['smtp_port'], timeout=15) as server:
                server.login(cfg['smtp_user'], cfg['smtp_pass'])
                server.sendmail(cfg['smtp_from'], to_addr, msg.as_string())
        else:
            with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port'], timeout=15) as server:
                server.starttls()
                server.login(cfg['smtp_user'], cfg['smtp_pass'])
                server.sendmail(cfg['smtp_from'], to_addr, msg.as_string())
        with get_db() as db:
            db.execute(
                "INSERT INTO email_sent (from_addr, to_addr, subject, body_text, body_html) VALUES (?, ?, ?, ?, ?)",
                (cfg['smtp_from'], ", ".join(to_addr), subject, body_text, body_html)
            )
            db.commit()
        return True, "发送成功"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP 认证失败"
    except Exception as e:
        return False, str(e)

def get_sent_emails(page=1, per_page=20):
    with get_db() as db:
        count = db.execute("SELECT COUNT(*) FROM email_sent").fetchone()[0]
        offset = (page - 1) * per_page
        rows = db.execute(
            "SELECT * FROM email_sent ORDER BY sent_at DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
        items = [dict(r) for r in rows]
        return {"items": items, "total": count, "page": page, "per_page": per_page, "pages": max(1, (count + per_page - 1) // per_page)}
