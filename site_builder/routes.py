#!/usr/bin/env python3
"""Site Builder — Flask Blueprint 路由

端点统计: ~10 个
前缀: /admin/site-builder/
"""

import os, sys, json

from flask import Blueprint, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))

from services.jwt_service import validate_token
from i18n import _

site_builder_bp = Blueprint('site_builder', __name__, url_prefix='/admin/site-builder')


# ── 鉴权 ──────────────────────────────────────────────

def _require_admin():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        token = request.cookies.get('sso_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': _('需要管理权限')}), 401)
    return payload, None


def _success(data=None, message='ok'):
    return jsonify({'success': True, 'data': data, 'message': message})


def _error(message, code=400):
    return jsonify({'success': False, 'error': message}), code


# ── 提示词模板管理 ────────────────────────────────────

@site_builder_bp.route('/prompts', methods=['GET'])
def list_prompts():
    """列出所有行业提示词模板"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import list_prompts as _list
    active_only = request.args.get('active_only', '0') == '1'
    industry = request.args.get('industry', '')
    prompts = _list(active_only=active_only, industry=industry if industry else None)
    return _success(prompts)


@site_builder_bp.route('/prompts/<identifier>', methods=['GET'])
def get_prompt(identifier):
    """获取单个提示词模板详情（含完整提示词文本）"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_prompt as _get
    # 尝试先按 id 解析
    try:
        pid = int(identifier)
        prompt = _get(pid)
    except ValueError:
        prompt = _get(identifier)

    if not prompt:
        return _error(_('没有可用的提示词模板'), 404)
    return _success(prompt)


@site_builder_bp.route('/prompts', methods=['POST'])
def create_prompt():
    """创建自定义提示词模板"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return _error(_('名称不能为空'))

    from site_builder.models import create_prompt as _create
    new_id = _create({
        'identifier': data.get('identifier', ''),
        'name': name,
        'description': data.get('description', ''),
        'icon': data.get('icon', '📄'),
        'industry': data.get('industry', ''),
        'tags': data.get('tags', []),
        'defaults': data.get('defaults', {}),
        'pages': data.get('pages', []),
        'documents': data.get('documents', []),
        'prompts': data.get('prompts', {}),
        'created_by': admin['user_id'],
    })
    return _success({'id': new_id}, _('已创建'))


@site_builder_bp.route('/prompts/<int:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """更新提示词模板"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    from site_builder.models import update_prompt as _update
    _update(prompt_id, data)
    return _success(message=_('已更新'))


@site_builder_bp.route('/prompts/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """删除自定义提示词模板"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import delete_prompt as _delete
    _delete(prompt_id)
    return _success(message=_('已删除'))


# ── 建站流程 ──────────────────────────────────────────

@site_builder_bp.route('/preview', methods=['POST'])
def preview_plan():
    """生成建站方案预览（不执行，仅返回方案）"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    prompt_id = data.get('prompt_id') or data.get('prompt_identifier', '')
    user_input = data.get('message', '').strip()

    if not user_input:
        return _error(_('消息不能为空'))

    from site_builder.models import get_prompt as _get_prompt
    # 解析 prompt_id
    try:
        prompt_id = int(prompt_id)
        prompt_template = _get_prompt(prompt_id)
    except (ValueError, TypeError):
        prompt_template = _get_prompt(prompt_id) if prompt_id else None

    if not prompt_template:
        return _error(_('没有可用的提示词模板'), 404)

    from site_builder.engine import SiteBuilderEngine
    engine = SiteBuilderEngine()

    try:
        # 阶段 1: 解析需求
        parsed = engine.parse_requirement(prompt_template, user_input)

        # 阶段 2: 生成方案
        plan = engine.generate_plan(prompt_template, parsed, user_input)

        return _success({
            'parsed': parsed,
            'plan': plan,
            'summary': plan.get('summary', ''),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _error(_('建站方案生成失败') + f': {e}', 500)


@site_builder_bp.route('/execute', methods=['POST'])
def execute_build():
    """执行建站方案（写入数据库）"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    plan = data.get('plan', {})
    prompt_id = data.get('prompt_id', '')
    user_input = data.get('message', '')

    if not plan:
        return _error('方案数据不能为空')

    from site_builder.models import get_prompt as _get_prompt
    try:
        prompt_id = int(prompt_id)
        prompt_template = _get_prompt(prompt_id)
    except (ValueError, TypeError):
        prompt_template = _get_prompt(prompt_id) if prompt_id else None

    if not prompt_template:
        return _error(_('没有可用的提示词模板'), 404)

    # 创建任务记录
    from site_builder.models import create_task, update_task
    task_id = create_task(
        user_id=admin['user_id'],
        prompt_id=prompt_template.get('id', 0),
        user_input=user_input,
    )
    update_task(task_id, status='executing', current_step='品牌设置')

    try:
        from site_builder.engine import SiteBuilderEngine
        engine = SiteBuilderEngine()
        results = engine.execute_plan(plan, prompt_template)

        update_task(task_id, status='completed', result_json=results)
        return _success({
            'task_id': task_id,
            'results': results,
            'summary': results.get('_summary', {}),
        }, _('建站完成'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_task(task_id, status='failed', error_message=str(e))
        return _error(_('当前步骤执行失败') + f': {e}', 500)


# ── 最小化修改 ────────────────────────────────────────

@site_builder_bp.route('/modify', methods=['POST'])
def modify_block():
    """最小化修改：分析用户意图，定位具体区块，执行修改"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    message = data.get('message', '').strip()
    page = data.get('page', 'home')

    if not message:
        return _error(_('消息不能为空'))

    try:
        from site_builder.engine import SiteBuilderEngine
        engine = SiteBuilderEngine()
        result = engine.modify_block(message, page)
        return _success(result, _('已修改') if result.get('success') else _('无法定位需要修改的区块'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _error(str(e), 500)


# ── 任务管理 ──────────────────────────────────────────

@site_builder_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """列出建站任务"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import list_tasks as _list
    limit = request.args.get('limit', 20, type=int)
    tasks = _list(user_id=admin['user_id'], limit=limit)
    return _success(tasks)


@site_builder_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_task as _get
    task = _get(task_id)
    if not task:
        return _error('任务不存在', 404)
    return _success(task)


# ── 页面摘要（用于 LLM 修改上下文）─────────────────────

@site_builder_bp.route('/page-summary/<page>', methods=['GET'])
def page_summary(page):
    """获取页面区块摘要"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.generators.pages import PageGenerator
    summary = PageGenerator.get_page_summary(page)
    return _success(summary)