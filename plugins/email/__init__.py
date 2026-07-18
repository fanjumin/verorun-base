#!/usr/bin/env python3
"""
Email Service Plugin — 邮件服务插件（完全独立）
================================================
统一的邮件服务：SMTP 发信 + IMAP 收信 + 附件 + 已发送记录。
- 独立数据库：email.db（不依赖主库）
- 独立配置：环境变量 + plugin.json 默认值（不依赖 system_config）
- 独立 i18n：插件自带翻译文件
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from plugin_manager.base import BasePlugin

# 模块级 i18n 引用，由 on_enable 注入
_t = lambda text: text


def init_i18n(t_fn):
    """供插件启用时注入 i18n 翻译函数"""
    global _t
    _t = t_fn


class EmailPlugin(BasePlugin):
    name = 'email'
    version = '1.0.0'
    description = 'Email Service — SMTP/IMAP email client with inbox, compose, attachments, and contact management'
    author = 'VeroRun'

    def on_install(self, registry):
        """安装时初始化独立 email.db"""
        from .models import init_email_db
        init_email_db()
        return True

    def on_enable(self, registry):
        """启用时初始化数据库 + i18n（幂等）"""
        from .models import init_email_db
        init_email_db()
        init_i18n(self.t)
        print(_'[EmailPlugin] ✅ Email service plugin enabled (email.db)')
        return True

    def register_routes(self):
        """注册 Flask 路由"""
        from .routes import email_bp
        return [email_bp]

    def on_disable(self, registry):
        """禁用时清理"""
        print(_'[EmailPlugin] ⚠️ Email service plugin disabled')
        return True