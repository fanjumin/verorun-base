#!/usr/bin/env python3
"""
邮件发送服务 — 基于阿里云企业邮箱 SMTP
支持：纯文本 / HTML 邮件，单发 / 批量

配置来源优先级：DB system_config → 环境变量 → 默认值

DB key              | 说明                    | 默认值
--------------------|-------------------------|--------------------------
smtp_host           | SMTP 服务器              | smtp.qiye.aliyun.com
smtp_port           | SMTP 端口                | 465
smtp_user           | SMTP 账号                | （必填）
smtp_pass           | SMTP 密码                | （必填）
smtp_from           | 发件人地址              | 同 smtp_user
imap_host           | IMAP 服务器             | imap.qiye.aliyun.com
imap_port           | IMAP 端口               | 993
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# ── All supported config keys with descriptions ──

CONFIG_DEFS = {
    'smtp_host':  {'label': 'SMTP 服务器',    'default': 'smtp.qiye.aliyun.com', 'sensitive': False},
    'smtp_port':  {'label': 'SMTP 端口',      'default': '465',                  'sensitive': False},
    'smtp_user':  {'label': 'SMTP 账号',      'default': '',                     'sensitive': False},
    'smtp_pass':  {'label': 'SMTP 密码',      'default': '',                     'sensitive': True},
    'smtp_from':  {'label': '发件人地址',      'default': '',                     'sensitive': False},
    'imap_host':  {'label': 'IMAP 服务器',     'default': 'imap.qiye.aliyun.com','sensitive': False},
    'imap_port':  {'label': 'IMAP 端口',       'default': '993',                  'sensitive': False},
}

ENV_MAP = {
    'smtp_host': 'SMTP_HOST',
    'smtp_port': 'SMTP_PORT',
    'smtp_user': 'SMTP_USER',
    'smtp_pass': 'SMTP_PASS',
    'smtp_from': 'SMTP_FROM',
    'imap_host': 'IMAP_HOST',
    'imap_port': 'IMAP_PORT',
}


def _get_db_config():
    """Fetch all known mail config keys from system_config table."""
    result = {}
    try:
        from models import get_db
        keys = list(CONFIG_DEFS.keys())
        placeholders = ','.join('?' for _ in keys)
        with get_db() as conn:
            rows = conn.execute(
                f"SELECT key, value FROM system_config WHERE key IN ({placeholders})",
                keys
            ).fetchall()
            for r in rows:
                result[r['key']] = r['value']
    except Exception as e:
        logger.debug(f"DB config read failed (will use env/fallback): {e}")
    return result


def get_smtp_config():
    db_cfg = _get_db_config()
    cfg = {}
    for key, meta in CONFIG_DEFS.items():
        # Priority: DB > env > default
        val = db_cfg.get(key)
        if not val:
            env_key = ENV_MAP.get(key)
            val = os.environ.get(env_key, '') if env_key else ''
        if not val:
            val = meta['default']
        cfg[key] = val

    # smtp_from defaults to smtp_user if not set
    if not cfg['smtp_from']:
        cfg['smtp_from'] = cfg['smtp_user']

    try:
        cfg['smtp_port'] = int(cfg['smtp_port'])
    except (ValueError, TypeError):
        cfg['smtp_port'] = 465
    try:
        cfg['imap_port'] = int(cfg['imap_port'])
    except (ValueError, TypeError):
        cfg['imap_port'] = 993

    return cfg


def send_email(to_addr, subject, body_text, body_html=None, cc=None, reply_to=None):
    cfg = get_smtp_config()
    if not cfg['smtp_user'] or not cfg['smtp_pass']:
        return False, "SMTP 未配置 (请先设置 smtp_user/smtp_pass)"

    if isinstance(to_addr, str):
        to_addr = [to_addr]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["smtp_from"]
    msg["To"] = ", ".join(to_addr)

    if cc:
        if isinstance(cc, str):
            cc = [cc]
        msg["Cc"] = ", ".join(cc)
        to_addr = list(to_addr) + cc

    if reply_to:
        msg["Reply-To"] = reply_to

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        if cfg["smtp_port"] == 465:
            with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=15) as server:
                server.login(cfg["smtp_user"], cfg["smtp_pass"])
                server.sendmail(cfg["smtp_from"], to_addr, msg.as_string())
        else:
            with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15) as server:
                server.starttls()
                server.login(cfg["smtp_user"], cfg["smtp_pass"])
                server.sendmail(cfg["smtp_from"], to_addr, msg.as_string())

        logger.info(f"Email sent to {to_addr}: {subject}")
        return True, "发送成功"

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP 认证失败")
        return False, "SMTP 认证失败，请检查 smtp_user/smtp_pass"
    except smtplib.SMTPException as e:
        logger.error(f"SMTP 发送失败: {e}")
        return False, f"SMTP 错误: {e}"
    except Exception as e:
        logger.error(f"邮件发送异常: {e}")
        return False, f"发送异常: {e}"


def send_contact_email(name, email, subject, message):
    admin_email = os.environ.get("CONTACT_TO", "")
    full_subject = f"[联系表单] {subject}"

    body_text = f"""来自 易站智能 联系表单

姓名: {name}
邮箱: {email}
主题: {subject}
---
{message}
"""

    body_html = (
        '<!DOCTYPE html><html><body style="font-family:sans-serif;'
        'color:#333;max-width:600px;margin:20px auto">'
        '<h2 style="color:#00d4aa">📬 来自 VeroRun 联系表单</h2>'
        '<table style="width:100%;border-collapse:collapse">'
        f'<tr><td style="padding:8px;color:#888">姓名</td><td style="padding:8px">{name}</td></tr>'
        f'<tr><td style="padding:8px;color:#888">邮箱</td><td style="padding:8px"><a href="mailto:{email}">{email}</a></td></tr>'
        f'<tr><td style="padding:8px;color:#888">主题</td><td style="padding:8px">{subject}</td></tr>'
        '</table>'
        f'<div style="margin-top:16px;padding:16px;background:#f5f5f5;border-radius:8px">{message}</div>'
        '</body></html>'
    )

    return send_email(
        to_addr=admin_email,
        subject=full_subject,
        body_text=body_text,
        body_html=body_html,
        reply_to=email,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = get_smtp_config()
    print("=== SMTP Config ===")
    for k, v in cfg.items():
        masked = v[:4]+'****' if k.endswith('pass') or k.endswith('secret') else v
        print(f"  {k}: {masked}")
    print()
    success, msg = send_email(
        to_addr=cfg.get("smtp_user", ""),
        subject="📧 VeroRon 维洛智能 邮件服务测试",
        body_text="这是一封测试邮件，确认 SMTP 配置正确。",
        body_html="<h2 style='color:#00d4aa'>✅ 测试成功</h2><p>邮件服务配置正确！</p>",
    )
    print(f"{'✅' if success else '❌'} {msg}")
