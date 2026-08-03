"""知识库权限检查模块 — 统一入口，供所有知识库 API 使用"""
from flask import jsonify


def get_admin_role(token_payload: dict) -> str:
    """从 JWT payload 中提取角色。
    返回: 'super_admin' | 'admin' | 'operator' | 'user'
    """
    return token_payload.get('role', 'user')


def check_kb_permission(scope: str, owner_id: int, action: str,
                        token_payload: dict) -> tuple:
    """检查当前用户对知识库条目的操作权限。

    参数:
        scope:  'system' | 'user'
        owner_id: 知识库条目的 owner_id
        action: 'read' | 'write' | 'delete' | 'update_system'
        token_payload: JWT 解码后的 payload

    返回: (True, None) 或 (False, error_response)
    """
    user_id = token_payload.get('user_id')
    role = get_admin_role(token_payload)

    if action == 'read':
        # 读操作：所有登录用户均可读系统KB和用户KB
        return True, None

    if scope == 'system':
        if action == 'update_system':
            # 系统在线更新：仅超级管理员
            if role == 'super_admin':
                return True, None
            return False, (jsonify({
                'success': False,
                'error': '系统知识库在线更新仅超级管理员可执行'
            }), 403)

        if action == 'write':
            # 系统KB写入：仅超级管理员
            if role == 'super_admin':
                return True, None
            return False, (jsonify({
                'success': False,
                'error': '系统知识库仅超级管理员可修改'
            }), 403)

        if action == 'delete':
            # 系统KB删除：完全禁止
            return False, (jsonify({
                'success': False,
                'error': '系统知识库禁止删除。如需更新请使用在线更新功能'
            }), 403)

    elif scope == 'user':
        if role in ('super_admin', 'admin'):
            # 管理员可以操作所有用户KB
            return True, None

        if action in ('read', 'write', 'delete'):
            if owner_id == user_id:
                return True, None
            return False, (jsonify({
                'success': False,
                'error': '仅可操作自己的知识库条目'
            }), 403)

    return False, (jsonify({
        'success': False,
        'error': '未知的知识库作用域'
    }), 400)
