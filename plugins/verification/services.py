#!/usr/bin/env python3
"""
Verification Plugin Services — 实名认证核心逻辑
=================================================
与旧 auth-center/services/verification_service.py 兼容，
委托给 providers 层实际处理。
"""
import os
import sys

from .models import get_verification_db


def initiate_verification(user_id, return_url=''):
    """发起实名认证流程（委托给旧服务实现）"""
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)
    from services.verification_service import initiate_verification as _initiate
    return _initiate(user_id, return_url)


def verify_callback():
    """处理认证回调（委托给旧服务实现）"""
    _auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
    if _auth_dir not in sys.path:
        sys.path.insert(0, _auth_dir)
    from services.verification_service import verify_callback as _verify
    return _verify()
