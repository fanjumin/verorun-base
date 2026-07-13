#!/usr/bin/env python3
"""Site Builder — Flask Blueprint Routes

Endpoints: ~13
Prefix: /admin/site-builder/
"""

import os, sys, json

from flask import Blueprint, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))

from services.jwt_service import validate_token
from i18n import _

site_builder_bp = Blueprint('site_builder', __name__, url_prefix='/admin/site-builder')


# ── Auth ───────────────────────────────────────────────

def _require_admin():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        token = request.cookies.get('sso_token')
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': _('Admin access required')}), 401)
    return payload, None


def _success(data=None, message='ok'):
    return jsonify({'success': True, 'data': data, 'message': message})


def _error(message, code=400):
    return jsonify({'success': False, 'error': message}), code


# ── Prompt Template Management ─────────────────────────

@site_builder_bp.route('/prompts', methods=['GET'])
def list_prompts():
    """List all industry prompt templates"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import list_prompts as _list
    active_only = request.args.get('active_only', '0') == '1'
    industry = request.args.get('industry', '')
    prompts = _list(active_only=active_only, industry=industry if industry else None)
    return _success(prompts)


@site_builder_bp.route('/prompts/<identifier>', methods=['GET'])
def get_prompt(identifier):
    """Get single prompt template details (with full prompt text)"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_prompt as _get
    # Try to parse as id first
    try:
        pid = int(identifier)
        prompt = _get(pid)
    except ValueError:
        prompt = _get(identifier)

    if not prompt:
        return _error(_('Prompt template not found'), 404)
    return _success(prompt)


@site_builder_bp.route('/prompts', methods=['POST'])
def create_prompt():
    """Create custom prompt template"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return _error(_('Name cannot be empty'))

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
    return _success({'id': new_id}, _('Created'))


@site_builder_bp.route('/prompts/<int:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Update prompt template"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    from site_builder.models import update_prompt as _update
    _update(prompt_id, data)
    return _success(message=_('Updated'))


@site_builder_bp.route('/prompts/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete custom prompt template"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import delete_prompt as _delete
    _delete(prompt_id)
    return _success(message=_('Deleted'))


# ── Site Building Flow ─────────────────────────────────

@site_builder_bp.route('/preview', methods=['POST'])
def preview_plan():
    """Generate site plan preview (no execution, returns plan only)"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    prompt_id = data.get('prompt_id') or data.get('prompt_identifier', '')
    user_input = data.get('message', '').strip()

    if not user_input:
        return _error(_('Message cannot be empty'))

    from site_builder.models import get_prompt as _get_prompt
    # Parse prompt_id
    try:
        prompt_id = int(prompt_id)
        prompt_template = _get_prompt(prompt_id)
    except (ValueError, TypeError):
        prompt_template = _get_prompt(prompt_id) if prompt_id else None

    if not prompt_template:
        return _error(_('No available prompt template'), 404)

    from site_builder.engine import SiteBuilderEngine
    engine = SiteBuilderEngine()

    try:
        # Phase 1: Parse requirement
        parsed = engine.parse_requirement(prompt_template, user_input)

        # Phase 2: Generate plan
        plan = engine.generate_plan(prompt_template, parsed, user_input)

        return _success({
            'parsed': parsed,
            'plan': plan,
            'summary': plan.get('summary', ''),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _error(_('Plan generation failed') + f': {e}', 500)


@site_builder_bp.route('/execute', methods=['POST'])
def execute_build():
    """Execute build plan (write to draft)"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    plan = data.get('plan', {})
    prompt_id = data.get('prompt_id', '')
    user_input = data.get('message', '')

    if not plan:
        return _error('Plan data cannot be empty')

    from site_builder.models import get_prompt as _get_prompt
    try:
        prompt_id = int(prompt_id)
        prompt_template = _get_prompt(prompt_id)
    except (ValueError, TypeError):
        prompt_template = _get_prompt(prompt_id) if prompt_id else None

    if not prompt_template:
        return _error(_('No available prompt template'), 404)

    # Create task record
    from site_builder.models import create_task, update_task
    task_id = create_task(
        user_id=admin['user_id'],
        prompt_id=prompt_template.get('id', 0),
        user_input=user_input,
    )
    update_task(task_id, status='executing', current_step='Brand settings')

    try:
        from site_builder.engine import SiteBuilderEngine
        engine = SiteBuilderEngine()
        # Always write to draft first; use /site-builder/publish to make it live
        results = engine.execute_plan(plan, prompt_template, draft=True)

        update_task(task_id, status='completed', result_json=results)
        return _success({
            'task_id': task_id,
            'results': results,
            'summary': results.get('_summary', {}),
        }, _('Draft generated — preview and publish via the Publish button'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_task(task_id, status='failed', error_message=str(e))
        return _error(_('Build execution failed') + f': {e}', 500)


# ── Publish Draft to Production ────────────────────────

@site_builder_bp.route('/publish', methods=['POST'])
def publish_draft():
    """Promote draft data to production (backup + publish)"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.site_settings.models import (
        get_draft_tokens, promote_draft_tokens, backup_tokens
    )
    from models import get_db

    # 1. Check draft exists
    draft_tokens = get_draft_tokens()
    if draft_tokens is None:
        return _error('No draft to publish', 404)

    # 2. Check draft blocks exist
    has_blocks = False
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM cms_blocks WHERE is_published=0").fetchone()
        if row and row['c'] > 0:
            has_blocks = True

    if not has_blocks:
        return _error('No draft content to publish (run /execute first)', 404)

    # 3. Backup current production
    try:
        backup_tokens()
    except Exception as e:
        logger.warning(f'Backup failed (non-critical): {e}')

    # 4. Promote tokens: draft_json → token_json
    promote_draft_tokens()

    # 5. Promote blocks: is_published=0 → is_published=1
    with get_db() as conn:
        conn.execute("UPDATE cms_blocks SET is_published=1 WHERE is_published=0")
        conn.execute("UPDATE cms_posts SET is_published=1 WHERE is_published=0")
        conn.commit()

    return _success({'published': True}, 'Draft published to production')


# ── Get Draft Data (for preview) ───────────────────────

@site_builder_bp.route('/draft-data', methods=['GET'])
def get_draft_data():
    """Return all draft data for preview rendering"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.site_settings.models import get_draft_tokens
    from models import get_db

    draft_tokens = get_draft_tokens()
    if draft_tokens is None:
        return _error('No draft found', 404)

    # Get draft blocks grouped by page
    blocks = {}
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM cms_blocks WHERE is_published=0 ORDER BY page, position"
        ).fetchall()
        for r in rows:
            d = dict(r)
            page = d['page']
            if page not in blocks:
                blocks[page] = []
            blocks[page].append(d)

    # Get draft documents
    documents = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT slug, title, content FROM cms_posts WHERE is_published=0 AND category='legal'"
        ).fetchall()
        documents = [dict(r) for r in rows]

    return _success({
        'tokens': draft_tokens,
        'blocks': blocks,
        'documents': documents,
    })


# ── Render Preview Page (iframe) ───────────────────────

@site_builder_bp.route('/preview-site', methods=['GET'])
def preview_site_page():
    """Render AI-generated draft site in an iframe-friendly page"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.site_settings.models import get_draft_tokens
    from models import get_db
    from services.brand_service import get_brand_settings

    draft_tokens = get_draft_tokens()
    if draft_tokens is None:
        return 'No draft to preview. Generate a plan and execute first.', 404

    brand = get_brand_settings()

    # Get draft blocks
    blocks = {}
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM cms_blocks WHERE is_published=0 ORDER BY page, position"
        ).fetchall()
        for r in rows:
            d = dict(r)
            page = d['page']
            if page not in blocks:
                blocks[page] = []
            blocks[page].append(d)

    # Get draft documents
    documents = []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT slug, title, content FROM cms_posts WHERE is_published=0 AND category='legal'"
        ).fetchall()
        documents = [dict(r) for r in rows]

    from flask import render_template
    return render_template(
        'ai_site_preview.html',
        brand=brand,
        draft_tokens=draft_tokens,
        draft_blocks=blocks,
        draft_docs=documents,
        preview_mode=True,
    )


# ── Minimal Edit ───────────────────────────────────────

@site_builder_bp.route('/modify', methods=['POST'])
def modify_block():
    """Minimal edit: analyze user intent, locate block, execute modification"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    message = data.get('message', '').strip()
    page = data.get('page', 'home')

    if not message:
        return _error(_('Message cannot be empty'))

    try:
        from site_builder.engine import SiteBuilderEngine
        engine = SiteBuilderEngine()
        result = engine.modify_block(message, page)
        return _success(result, _('Modified') if result.get('success') else _('Could not locate block to modify'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return _error(str(e), 500)


# ── Task Management ────────────────────────────────────

@site_builder_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """List build tasks"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import list_tasks as _list
    limit = request.args.get('limit', 20, type=int)
    tasks = _list(user_id=admin['user_id'], limit=limit)
    return _success(tasks)


@site_builder_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get task details"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_task as _get
    task = _get(task_id)
    if not task:
        return _error('Task not found', 404)
    return _success(task)


# ── Page Summary (for LLM modification context) ────────

@site_builder_bp.route('/page-summary/<page>', methods=['GET'])
def page_summary(page):
    """Get page block summary"""
    admin, err = _require_admin()
    if err: return err

    from site_builder.generators.pages import PageGenerator
    summary = PageGenerator.get_page_summary(page)
    return _success(summary)


# ══════════════════════════════════════════════════════════════
# ── Mini-App Generation & Deployment ─────────────────────────
# ══════════════════════════════════════════════════════════════

import uuid
import threading
import shutil
from datetime import datetime

# In-memory task store (tasks persist for 1 hour)
_mini_app_tasks = {}
_MINI_APP_TASK_TTL = 3600


def _cleanup_old_tasks():
    now = datetime.now().timestamp()
    expired = [k for k, v in _mini_app_tasks.items()
               if now - v.get('created_at', 0) > _MINI_APP_TASK_TTL]
    for k in expired:
        _mini_app_tasks.pop(k, None)


@site_builder_bp.route('/mini-app/platforms', methods=['GET'])
def mini_app_platforms():
    """List supported platforms with their status"""
    admin, err = _require_admin()
    if err: return err

    platforms = [
        {
            'id': 'douyin',
            'name': 'Douyin / TikTok China',
            'type': 'native',
            'icon': 'douyin',
            'compatible_with': ['toutiao'],
            'description': 'ByteDance mini-program ecosystem (Douyin, Toutiao)',
        },
        {
            'id': 'wechat',
            'name': 'WeChat',
            'type': 'native',
            'icon': 'wechat',
            'compatible_with': [],
            'description': 'WeChat Mini Program ecosystem',
        },
        {
            'id': 'telegram',
            'name': 'Telegram',
            'type': 'webview',
            'icon': 'telegram',
            'compatible_with': [],
            'description': 'Telegram Mini App (WebView-based)',
        },
        {
            'id': 'line',
            'name': 'LINE',
            'type': 'webview',
            'icon': 'line',
            'compatible_with': [],
            'description': 'LINE MINI App (LIFF-based)',
        },
    ]

    # Check dev_accounts for configured platforms
    try:
        from plugins.dev_accounts.models import get_all
        accounts = get_all()
        configured = {a['platform']: a['is_active'] for a in accounts}
    except Exception:
        configured = {}

    for p in platforms:
        p['configured'] = bool(configured.get(p['id'], False))

    return _success(platforms)


@site_builder_bp.route('/mini-app/platforms/<platform>', methods=['PUT'])
def mini_app_update_platform(platform):
    """Update platform configuration (app_id, etc.)"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    allowed = ['douyin', 'wechat', 'telegram', 'line', 'toutiao']
    if platform not in allowed:
        return _error(f'Unsupported platform: {platform}', 400)

    try:
        from plugins.dev_accounts.models import get_all, update
        accounts = get_all()
        match = next((a for a in accounts if a['platform'] == platform), None)

        if match:
            update(match['id'], **data)
        else:
            return _error('Platform not configured in dev_accounts', 404)

        return _success(None, 'Platform updated')
    except Exception as e:
        return _error(str(e), 500)


@site_builder_bp.route('/mini-app/generate', methods=['POST'])
def mini_app_generate():
    """Trigger mini-app generation for specified platforms"""
    admin, err = _require_admin()
    if err: return err

    _cleanup_old_tasks()

    data = request.get_json(force=True, silent=True) or {}
    platforms = data.get('platforms', ['telegram'])
    options = data.get('options', {})

    if not isinstance(platforms, list) or not platforms:
        return _error('platforms must be a non-empty list')

    task_id = str(uuid.uuid4())[:8]
    _mini_app_tasks[task_id] = {
        'id': task_id,
        'status': 'pending',
        'platforms': platforms,
        'created_at': datetime.now().timestamp(),
        'results': {},
    }

    def _run_generation():
        try:
            _mini_app_tasks[task_id]['status'] = 'running'

            from services.brand_service import get_brand_settings
            from site_builder.site_settings.models import get_draft_tokens
            from site_builder.mini_app.engine import MiniAppEngine

            brand = get_brand_settings() or {}
            draft_tokens = get_draft_tokens() or {}
            site_config = {'draft_tokens': draft_tokens}

            engine = MiniAppEngine(site_config=site_config, brand_settings=brand)
            results = engine.generate(platforms, options)

            _mini_app_tasks[task_id]['results'] = results
            _mini_app_tasks[task_id]['status'] = 'completed'
        except Exception as e:
            import traceback
            _mini_app_tasks[task_id]['status'] = 'failed'
            _mini_app_tasks[task_id]['error'] = str(e)
            _mini_app_tasks[task_id]['traceback'] = traceback.format_exc()

    thread = threading.Thread(target=_run_generation, daemon=True)
    thread.start()

    return _success({'task_id': task_id, 'status': 'pending'})


@site_builder_bp.route('/mini-app/status/<task_id>', methods=['GET'])
def mini_app_status(task_id):
    """Query mini-app generation task status"""
    admin, err = _require_admin()
    if err: return err

    _cleanup_old_tasks()
    task = _mini_app_tasks.get(task_id)
    if not task:
        return _error('Task not found or expired', 404)

    return _success({
        'id': task['id'],
        'status': task['status'],
        'platforms': task['platforms'],
        'results': task.get('results', {}),
        'error': task.get('error', ''),
    })


@site_builder_bp.route('/mini-app/download/<platform>/<task_id>', methods=['GET'])
def mini_app_download(platform, task_id):
    """Download generated mini-app as .zip file"""
    admin, err = _require_admin()
    if err: return err

    task = _mini_app_tasks.get(task_id)
    if not task:
        return _error('Task not found or expired', 404)

    if task['status'] != 'completed':
        return _error('Generation not completed yet', 400)

    result = task.get('results', {}).get(platform)
    if not result or result.get('status') != 'completed':
        return _error(f'No completed output for platform: {platform}', 404)

    output_dir = result.get('output_dir', '')
    if not output_dir or not os.path.isdir(output_dir):
        return _error('Output directory not found', 404)

    try:
        from site_builder.mini_app.packager import MiniAppPackager
        packager = MiniAppPackager()
        zip_path = packager.package(platform, output_dir)

        from flask import send_file
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{platform}-mini-app-{task_id}.zip'
        )
    except Exception as e:
        return _error(str(e), 500)


@site_builder_bp.route('/mini-app/deploy/<platform>', methods=['POST'])
def mini_app_deploy(platform):
    """Deploy mini-app to target platform"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    task_id = data.get('task_id', '')

    allowed = ['telegram', 'line']
    if platform not in allowed:
        return _success({
            'platform': platform,
            'deployed': False,
            'auto_deploy': False,
            'hint': f'For {platform}, manual deployment is required. Download the .zip and upload via the platform developer console.',
        })

    if not task_id:
        return _error('task_id is required')

    task = _mini_app_tasks.get(task_id)
    if not task:
        return _error('Task not found or expired', 404)

    if task['status'] != 'completed':
        return _error('Generation not completed yet', 400)

    result = task.get('results', {}).get(platform)
    if not result:
        return _error(f'No output for platform: {platform}', 404)

    try:
        from plugins.dev_accounts.models import get_all
        accounts = get_all()
        match = next((a for a in accounts if a['platform'] == platform and a['is_active']), None)

        if not match:
            return _error(f'No active dev_account found for {platform}', 404)

        from site_builder.mini_app.deployer import MiniAppDeployer
        deployer = MiniAppDeployer(dev_accounts=match)

        deploy_url = data.get('deploy_url', '')
        if platform == 'telegram':
            res = deployer.deploy_telegram(
                webapp_url=deploy_url or result.get('output_dir', ''),
                bot_token=match.get('bot_token', '')
            )
        elif platform == 'line':
            res = deployer.deploy_line(
                liff_id=match.get('channel_id', ''),
                endpoint_url=deploy_url or result.get('output_dir', ''),
                channel_token=match.get('access_token', '')
            )
        else:
            res = {'success': False, 'error': 'Unsupported platform'}

        return _success(res)
    except Exception as e:
        return _error(str(e), 500)
