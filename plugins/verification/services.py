#!/usr/bin/env python3
"""
Verification Plugin Services — 实名认证核心逻辑
=================================================
与旧 auth-center/services/verification_service.py 兼容，
委托给 auth-center 服务层实际处理。
"""
import os
from urllib.parse import urlparse

from .models import get_verification_db  # noqa: F401 — 保持模块导出

# F-003: 额外允许的回跳域名白名单（逗号分隔，可选）。
# 默认安全策略：仅允许空值 / 相对路径 / 与当前请求同源的绝对 URL，杜绝开放重定向。
_ALLOWED_REDIRECT_HOSTS = {
    h.strip().lower() for h in
    os.environ.get('VERIFICATION_ALLOWED_REDIRECT_HOSTS', '').split(',')
    if h.strip()
}


def _is_current_origin(netloc):
    """判断 netloc 是否为当前请求同源（无请求上下文时返回 False）。"""
    try:
        from flask import request, has_request_context
        if not has_request_context():
            return False
        return urlparse(request.host_url).netloc.lower() == netloc
    except Exception:
        return False


def _validate_verification_input(user_id, return_url):
    """F-003: 输入校验 — 防类型混淆与开放重定向。

    - user_id: 必须为正整数
    - return_url: 空 / 相对路径 / 同源绝对 URL / 白名单域名，禁止 javascript: 等危险 scheme
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(f'Invalid user_id: {user_id!r}')

    if not return_url:
        return
    parsed = urlparse(return_url)
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        raise ValueError(f'Disallowed URL scheme: {parsed.scheme}')
    if parsed.username or parsed.password:
        raise ValueError('Credentials are not allowed in return_url')
    if parsed.netloc:
        host = parsed.netloc.lower()
        if host not in _ALLOWED_REDIRECT_HOSTS and not _is_current_origin(host):
            raise ValueError(f'Disallowed redirect host: {parsed.netloc}')


def _load_verification_service():
    """F-002: 惰性导入 auth-center 服务。

    admin/auth-center 进程启动时已将 auth-center 加入 sys.path，
    此处直接导入、不再修改 sys.path，避免全局路径污染与模块遮蔽。
    导入失败时抛出明确错误。
    """
    try:
        import services.verification_service as _svc
        return _svc
    except Exception as e:
        raise RuntimeError(
            f'[VerificationPlugin] auth-center services.verification_service import failed: {e}'
        ) from e


def initiate_verification(user_id, return_url='', cert_name='', cert_no=''):
    """发起实名认证流程（委托给 auth-center 服务实现）。

    签名与 auth-center/routes/user.py 调用方一致（cert_name/cert_no 透传）。
    """
    _validate_verification_input(user_id, return_url)
    _svc = _load_verification_service()
    return _svc.initiate_verification(user_id, return_url, cert_name=cert_name, cert_no=cert_no)


def verify_callback(user_id, params=None):
    """处理认证回调（委托给 auth-center 服务实现）。

    签名与 auth-center/routes/user.py 调用方一致（user_id + 回调参数 dict）。
    """
    _svc = _load_verification_service()
    return _svc.verify_callback(user_id, params or {})
