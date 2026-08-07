#!/usr/bin/env python3
"""Mini App Builder — admin API routes (migrated from site_builder/routes.py)

Prefix: /admin/site-builder/mini-app/*
"""

import os
import json
import uuid
import threading
import shutil
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file
from i18n import _

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

mini_app_admin_bp = Blueprint('mini_app_admin', __name__, url_prefix='/admin/site-builder')


# ── Helpers ────────────────────────────────────────────────

def _require_admin():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        token = request.cookies.get('sso_token')
    from services.jwt_service import validate_token
    payload = validate_token(token) if token else None
    if not payload or not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': _('Admin access required')}), 401)
    return payload, None


def _success(data=None, message='ok'):
    return jsonify({'success': True, 'data': data, 'message': message})


def _error(message, code=400):
    return jsonify({'success': False, 'error': message}), code


# ── Task store ─────────────────────────────────────────────

# In-memory task store (tasks persist for 1 hour)
_mini_app_tasks = {}
_MINI_APP_TASK_TTL = 3600

# Workspace root — generated projects/versions are cached here
MINIAPP_WORKSPACE = os.path.join(BASE_DIR, 'workspace')


def _cleanup_old_tasks():
    now = datetime.now().timestamp()
    expired = [k for k, v in _mini_app_tasks.items()
               if now - v.get('created_at', 0) > _MINI_APP_TASK_TTL]
    for k in expired:
        _mini_app_tasks.pop(k, None)


def _project_version_dir(slug: str, version_no: int) -> str:
    """Return the absolute output dir for a project version."""
    return os.path.join(MINIAPP_WORKSPACE, slug, f'v{version_no}')


def _get_mini_app_platforms():
    """Return the supported platform list with dev-account configured flag."""
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
        from .submodules.accounts.models import get_all
        accounts = get_all()
        configured = {a['platform']: a['is_active'] for a in accounts}
    except Exception:
        configured = {}

    for p in platforms:
        p['configured'] = bool(configured.get(p['id'], False))

    return platforms


# ── Mini-App Project Management ────────────────────────

@mini_app_admin_bp.route('/mini-app/projects', methods=['GET'])
def mini_app_list_projects():
    """List all mini-app projects."""
    admin, err = _require_admin()
    if err: return err

    from .models import list_projects
    return _success(list_projects())


@mini_app_admin_bp.route('/mini-app/projects', methods=['POST'])
def mini_app_create_project():
    """Create a new mini-app project."""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return _error('Project name is required')

    from .models import create_project
    project = create_project(
        name=name,
        description=data.get('description', ''),
        created_by=admin.get('user_id', 0),
    )
    return _success(project, _('Project created'))


@mini_app_admin_bp.route('/mini-app/projects/<int:project_id>', methods=['GET'])
def mini_app_get_project(project_id):
    """Get a project with its version history."""
    admin, err = _require_admin()
    if err: return err

    from .models import get_project, list_versions
    project = get_project(project_id)
    if not project:
        return _error('Project not found', 404)
    project['versions'] = list_versions(project_id)
    return _success(project)


@mini_app_admin_bp.route('/mini-app/projects/<int:project_id>', methods=['DELETE'])
def mini_app_delete_project(project_id):
    """Delete a project (DB records + workspace files)."""
    admin, err = _require_admin()
    if err: return err

    from .models import get_project, delete_project
    project = get_project(project_id)
    if not project:
        return _error('Project not found', 404)

    # Remove workspace directory for this project
    proj_dir = os.path.join(MINIAPP_WORKSPACE, project['slug'])
    if os.path.isdir(proj_dir):
        shutil.rmtree(proj_dir, ignore_errors=True)

    delete_project(project_id)
    return _success(None, _('Project deleted'))


@mini_app_admin_bp.route('/mini-app/projects/<int:project_id>/versions', methods=['GET'])
def mini_app_list_versions(project_id):
    """List all versions of a project."""
    admin, err = _require_admin()
    if err: return err

    from .models import get_project, list_versions
    if not get_project(project_id):
        return _error('Project not found', 404)
    return _success(list_versions(project_id))


@mini_app_admin_bp.route('/mini-app/versions/<int:version_id>/download/<platform>', methods=['GET'])
def mini_app_download_version(version_id, platform):
    """Download a specific version's platform output as .zip (from workspace)."""
    admin, err = _require_admin()
    if err: return err

    from .models import get_version
    version = get_version(version_id)
    if not version:
        return _error('Version not found', 404)

    result = (version.get('result') or {}).get(platform)
    if not result or result.get('status') != 'completed':
        return _error(f'No completed output for platform: {platform}', 404)

    output_dir = result.get('output_dir', '')
    if not output_dir or not os.path.isdir(output_dir):
        return _error('Version output directory not found (may have been cleaned)', 404)

    try:
        from .mini_app.packager import MiniAppPackager
        # Package into the version's own directory to keep artifacts together
        pkg_base = os.path.join(os.path.dirname(output_dir), 'packages')
        os.makedirs(pkg_base, exist_ok=True)
        packager = MiniAppPackager(output_base=pkg_base)
        zip_path = packager.package(platform, output_dir)

        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{platform}-v{version["version_no"]}.zip'
        )
    except Exception as e:
        return _error(str(e), 500)


@mini_app_admin_bp.route('/mini-app/platforms', methods=['GET'])
def mini_app_platforms():
    """List supported platforms with their status"""
    admin, err = _require_admin()
    if err: return err
    return _success(_get_mini_app_platforms())


@mini_app_admin_bp.route('/mini-app/platforms/<platform>', methods=['PUT'])
def mini_app_update_platform(platform):
    """Update platform configuration (app_id, etc.)"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    allowed = ['douyin', 'wechat', 'telegram', 'line', 'toutiao']
    if platform not in allowed:
        return _error(f'Unsupported platform: {platform}', 400)

    try:
        from .submodules.accounts.models import get_by_platform_raw, update
        match = get_by_platform_raw(platform, active_only=False)

        if match:
            update(match['id'], **data)
        else:
            return _error('Platform not configured in dev_accounts', 404)

        return _success(None, 'Platform updated')
    except Exception as e:
        return _error(str(e), 500)


# ── Mini App AI Helpers ──────────────────────────────

def _mini_app_generate_with_ai(project, platforms, prompt, template, options,
                                create_version, next_version_no, admin):
    """AI-prompt branch: call LLM to build plan, create version, return preview URL."""
    try:
        # 1. Load template
        tmpl = _load_prompt_template(template or 'mini_shop')

        # 2. Build AI plan via Master Agent LLM (falls back to template defaults)
        plan = _build_ai_plan_from_template(tmpl, prompt)

        # 3. Create version with AI plan saved
        version_no = next_version_no(project['id'])
        output_base = _project_version_dir(project['slug'], version_no)

        version_id = create_version(
            project_id=project['id'],
            version_no=version_no,
            platforms=platforms,
            options=options,
            result={'ai_generated': True, 'plan': plan},
            output_path=output_base,
            status='draft',
        )

        # 4. Save AI fields to the version record
        _save_ai_fields(version_id, prompt, template, plan)

        return _success({
            'task_id': None,
            'status': 'draft',
            'version_id': version_id,
            'project_id': project['id'],
            'project_slug': project['slug'],
            'version_no': version_no,
            'preview_url': '/admin/site-builder/mini-app/preview/%d' % version_id,
            'plan_summary': {
                'app_name': plan['brand']['app_name'],
                'pages': len(plan['pages']),
                'widgets': len(plan.get('widgets', [])),
                'tabBar': len(plan.get('tabBar', [])),
            },
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error('[MiniApp] AI generation failed: %s', e)
        return _error(str(e), 500)


def _save_ai_fields(version_id, prompt, template, plan):
    """Persist AI-generation metadata to the mini_app_versions row."""
    try:
        from .models import get_db
        from .models import TABLE_MINIAPP_VERSIONS
        with get_db() as conn:
            conn.execute(
                'UPDATE %s SET prompt=%%s, prompt_template=%%s, ai_plan_json=%%s, widgets_json=%%s WHERE id=%%s'
                % TABLE_MINIAPP_VERSIONS,
                (prompt, template,
                 json.dumps(plan, ensure_ascii=False),
                 json.dumps(plan.get('widgets', []), ensure_ascii=False),
                 version_id)
            )
            conn.commit()
    except Exception as e:
        print('[MiniApp] _save_ai_fields failed: %s' % e)


def _load_prompt_template(identifier):
    """Load a prompt template YAML by its identifier. Falls back to mini_shop."""
    import yaml
    prompts_dir = os.path.join(BASE_DIR, 'prompts')
    for fname in sorted(os.listdir(prompts_dir)):
        if not fname.endswith('.yml'):
            continue
        fpath = os.path.join(prompts_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as fh:
            data = yaml.safe_load(fh) or {}
        if data.get('identifier') == identifier:
            return data
    # fallback: try mini_shop
    fallback = os.path.join(prompts_dir, 'mini_shop.yml')
    if os.path.isfile(fallback):
        with open(fallback, 'r', encoding='utf-8') as fh:
            return yaml.safe_load(fh) or {}
    return {}


def _build_basic_plan_from_template(tmpl, prompt):
    """Fallback: build a basic plan from template defaults without LLM.

    Used when Master Agent is unavailable. Returns empty sections and widgets.
    """
    pages = []
    for p in tmpl.get('pages', []):
        pages.append({
            'slug': p.get('id', ''),
            'title': p.get('name', p.get('id', '')),
            'sections': [],
        })

    tab = tmpl.get('mini_app', {}).get('tabBar', {}).get('default', [])

    d = tmpl.get('defaults', {})
    brand_name = d.get('site_name', '').replace('{品牌名称}', 'Mini App')

    return {
        'brand': {
            'app_name': brand_name,
            'tagline': d.get('tone', ''),
            'brand_story': '',
        },
        'theme': {
            'primary_color': d.get('primary_color', '#4F46E5'),
            'secondary_color': d.get('accent_color', '#10B981'),
            'accent_color': d.get('accent_color', '#F59E0B'),
        },
        'tabBar': tab,
        'pages': pages,
        'widgets': [],
    }


def _build_ai_plan_from_template(tmpl, prompt_text):
    """Build a complete Mini App plan with retries and template fallback.

    Up to 3 LLM retry attempts. Falls back to _build_fallback_plan() on failure.

    Args:
        tmpl: Loaded YAML prompt template dict
        prompt_text: Raw user prompt

    Returns:
        Plan dict with keys: brand, theme, tabBar, pages, widgets
    """
    import re
    import logging
    logger = logging.getLogger(__name__)

    defaults = tmpl.get('defaults', {})
    prompts = tmpl.get('prompts', {})
    tabbar_default = tmpl.get('mini_app', {}).get('tabBar', {}).get('default', [])
    industry = defaults.get('industry', 'General')

    # ── Resolve engine ──
    engine = None
    master_pm_id = None
    try:
        from agent_matrix.engine import UnifiedLLM
        from agent_matrix import models as agent_models
        agents = agent_models.list_agents(role_type='master', active_only=True)
        if agents:
            engine = UnifiedLLM(agents[0])
            master_pm_id = agents[0].get('provider_model_id')
    except Exception as exc:
        logger.warning('[MiniApp] Engine init failed: %s', exc)

    def _call_llm_json(system_msg, user_msg, temperature=0.3, max_tokens=2000):
        """Call LLM with retries, parse JSON, return {} on any failure."""
        if not engine:
            return {}
        for attempt in range(3):
            try:
                raw = engine.chat(
                    [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                    temperature=temperature + (0.2 if attempt > 0 else 0),
                    max_tokens=max_tokens,
                    provider_model_id=master_pm_id,
                )
                if not raw or not isinstance(raw, str) or len(raw) < 20:
                    continue
                # Extract JSON
                match = re.search(r'\{[\s\S]*\}', raw)
                if match:
                    return json.loads(match.group(0))
                match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
                if match:
                    return json.loads(match.group(1))
            except Exception:
                continue
        return {}

    # ── Attempt LLM-based plan generation ──
    plan = None
    if engine:
        try:
            brand_name = defaults.get('site_name', 'Mini App')
            style_pref = defaults.get('style', 'Modern')

            # Round 1: Parse
            parse_tpl = prompts.get('parse', '')
            if parse_tpl:
                parsed = _call_llm_json(
                    parse_tpl.replace('{行业}', industry).replace('{用户输入}', prompt_text),
                    prompt_text)
                brand_name = parsed.get('brand_name', brand_name)
                style_pref = parsed.get('style_preference', style_pref)

            # Round 2: Brand
            brand_tpl = prompts.get('brand', '')
            if brand_tpl:
                brand = _call_llm_json(
                    brand_tpl.replace('{品牌名称}', brand_name).replace('{行业}', industry).replace('{风格偏好}', style_pref),
                    'Generate brand config for: ' + brand_name)
            else:
                brand = {}
            brand.setdefault('app_name', brand_name)
            brand.setdefault('tagline', defaults.get('tone', ''))
            brand.setdefault('primary_color', defaults.get('primary_color', '#4F46E5'))
            brand.setdefault('secondary_color', defaults.get('accent_color', '#10B981'))
            brand.setdefault('accent_color', defaults.get('accent_color', '#F59E0B'))

            # Round 3: Per-page content
            pages = []
            all_widgets = []
            for p in tmpl.get('pages', []):
                slug = p.get('id', '')
                title = p.get('name', slug)
                page_tpl = prompts.get('page_' + slug, '')
                if page_tpl:
                    content = _call_llm_json(
                        page_tpl.replace('{品牌名称}', brand_name).replace('{行业}', industry).replace('{风格偏好}', style_pref),
                        'Generate page: ' + title)
                    sections = content.get('sections', [])
                    for w in content.get('widgets', []):
                        w.setdefault('page', slug)
                        all_widgets.append(w)
                else:
                    sections = []

                pages.append({'slug': slug, 'title': title, 'sections': sections})

            plan = {
                'brand': brand,
                'theme': {'primary_color': brand.get('primary_color', '#4F46E5'),
                           'secondary_color': brand.get('secondary_color', '#10B981'),
                           'accent_color': brand.get('accent_color', '#F59E0B')},
                'tabBar': tabbar_default,
                'pages': pages,
                'widgets': all_widgets,
            }
        except Exception as exc:
            logger.warning('[MiniApp] LLM plan generation failed: %s', exc)

    # ── Fallback: template-based plan ──
    if not plan or not plan.get('pages'):
        logger.warning('[MiniApp] Falling back to template-based plan')
        plan = _build_fallback_plan(tmpl, prompt_text)

    return plan


def _build_fallback_plan(tmpl, prompt_text):
    """Build a plan from template defaults without LLM."""
    defaults = tmpl.get('defaults', {})
    pages_raw = tmpl.get('pages', [])

    return {
        'brand': {
            'app_name': defaults.get('site_name', tmpl.get('name', 'Mini App')),
            'tagline': f"Your {defaults.get('industry', '')} mini program",
            'primary_color': defaults.get('primary_color', '#4F46E5'),
            'secondary_color': defaults.get('accent_color', '#10B981'),
            'accent_color': defaults.get('accent_color', '#F59E0B'),
        },
        'theme': {
            'primary_color': defaults.get('primary_color', '#4F46E5'),
            'secondary_color': defaults.get('accent_color', '#10B981'),
            'accent_color': defaults.get('accent_color', '#F59E0B'),
        },
        'tabBar': tmpl.get('mini_app', {}).get('tabBar', {}).get('default', []),
        'pages': [
            {'slug': p.get('id', f'page_{i}'), 'title': p.get('name', f'Page {i+1}'), 'sections': [
                {'id': 'hero', 'type': 'banner', 'title': p.get('name', '') + ' Hero', 'content': ''},
                {'id': 'content', 'type': 'card', 'title': 'Content', 'content': ''},
            ]} for i, p in enumerate(pages_raw)
        ] if pages_raw else [
            {'slug': 'home', 'title': 'Home', 'sections': [
                {'id': 'hero', 'type': 'banner', 'title': 'Welcome', 'content': prompt_text},
            ]}
        ],
        'widgets': [
            {'id': 'chat-widget', 'type': 'chat', 'title': 'AI Assistant', 'icon': '💬'},
        ],
    }


@mini_app_admin_bp.route('/mini-app/generate', methods=['POST'])
def mini_app_generate():
    """Trigger mini-app generation for specified platforms.

    Optional project binding:
        - project_id: generate a new version under an existing project
        - project_name: create a new project (if project_id not given) and
                        generate its first version
    When bound to a project, output is written to a versioned workspace dir
    (workspace/<slug>/v<N>/) and recorded in the DB (version history).
    Without a project, falls back to the legacy ephemeral 'dist/' behavior.
    """
    admin, err = _require_admin()
    if err: return err

    _cleanup_old_tasks()

    data = request.get_json(force=True, silent=True) or {}
    platforms = data.get('platforms', ['telegram'])
    options = data.get('options', {})
    project_id = data.get('project_id')
    project_name = (data.get('project_name') or '').strip()
    prompt = (data.get('prompt') or '').strip()
    template = (data.get('template') or '').strip()

    if not isinstance(platforms, list) or not platforms:
        return _error('platforms must be a non-empty list')

    # Resolve or create the bound project (optional)
    from .models import (get_project, create_project,
                         next_version_no, create_version)
    project = None
    if project_id:
        project = get_project(project_id)
        if not project:
            return _error('Project not found', 404)
    elif project_name:
        project = create_project(name=project_name, created_by=admin.get('user_id', 0))

    # ── AI Prompt Branch ──
    if prompt:
        if not project:
            project_name = project_name or 'AI Generated App'
            project = create_project(name=project_name, created_by=admin.get('user_id', 0))
        return _mini_app_generate_with_ai(
            project, platforms, prompt, template, options,
            create_version, next_version_no, admin
        )

    version_no = None
    output_base = None
    if project:
        version_no = next_version_no(project['id'])
        output_base = _project_version_dir(project['slug'], version_no)

    task_id = str(uuid.uuid4())[:8]
    _mini_app_tasks[task_id] = {
        'id': task_id,
        'status': 'pending',
        'platforms': platforms,
        'created_at': datetime.now().timestamp(),
        'results': {},
        'project_id': project['id'] if project else None,
        'project_slug': project['slug'] if project else None,
        'version_no': version_no,
    }

    def _run_generation():
        try:
            _mini_app_tasks[task_id]['status'] = 'running'

            from .internal_client import get_brand_settings, get_draft_tokens
            from .mini_app.engine import MiniAppEngine

            brand = get_brand_settings() or {}
            draft_tokens = get_draft_tokens() or {}
            site_config = {'draft_tokens': draft_tokens}

            engine = MiniAppEngine(site_config=site_config, brand_settings=brand)
            results = engine.generate(platforms, options, output_base=output_base)

            _mini_app_tasks[task_id]['results'] = results
            _mini_app_tasks[task_id]['status'] = 'completed'

            # Persist version record when bound to a project
            if project and version_no:
                try:
                    create_version(
                        project_id=project['id'],
                        version_no=version_no,
                        platforms=platforms,
                        options=options,
                        result=results,
                        output_path=output_base,
                        status='completed',
                    )
                except Exception as ve:
                    import traceback
                    print(f'[MiniApp] version persist failed: {ve}')
                    traceback.print_exc()
        except Exception as e:
            import traceback
            _mini_app_tasks[task_id]['status'] = 'failed'
            _mini_app_tasks[task_id]['error'] = str(e)
            _mini_app_tasks[task_id]['traceback'] = traceback.format_exc()

    thread = threading.Thread(target=_run_generation, daemon=True)
    thread.start()

    return _success({
        'task_id': task_id,
        'status': 'pending',
        'project_id': project['id'] if project else None,
        'project_slug': project['slug'] if project else None,
        'version_no': version_no,
    })


@mini_app_admin_bp.route('/mini-app/status/<task_id>', methods=['GET'])
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
        'project_id': task.get('project_id'),
        'project_slug': task.get('project_slug'),
        'version_no': task.get('version_no'),
    })


@mini_app_admin_bp.route('/mini-app/download/<platform>/<task_id>', methods=['GET'])
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
        from .mini_app.packager import MiniAppPackager
        packager = MiniAppPackager()
        zip_path = packager.package(platform, output_dir)

        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{platform}-mini-app-{task_id}.zip'
        )
    except Exception as e:
        return _error(str(e), 500)


def _build_deployer_credentials(platform: str) -> dict:
    """Fetch the active dev account for a platform with decrypted secrets."""
    from .submodules.accounts.models import get_by_platform_raw
    from .submodules.accounts.crypto import decrypt

    account = get_by_platform_raw(platform, active_only=True)
    if not account:
        return None
    return {
        'bot_token': decrypt(account.get('bot_token', '')),
        'access_token': decrypt(account.get('access_token', '')),
        'channel_id': account.get('channel_id', ''),
        'liff_id': account.get('channel_id', ''),
    }


@mini_app_admin_bp.route('/mini-app/deploy/<platform>', methods=['POST'])
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
        creds = _build_deployer_credentials(platform)
        if not creds:
            return _error(f'No active dev_account found for {platform}', 404)

        from .mini_app.deployer import MiniAppDeployer
        deployer = MiniAppDeployer(dev_accounts={platform: creds})

        deploy_url = data.get('deploy_url', '')
        if platform == 'telegram':
            res = deployer.deploy_telegram(webapp_url=deploy_url or result.get('output_dir', ''))
        elif platform == 'line':
            res = deployer.deploy_line(
                liff_id=creds['liff_id'],
                endpoint_url=deploy_url or result.get('output_dir', ''),
            )
        else:
            res = {'success': False, 'error': 'Unsupported platform'}

        return _success(res)
    except Exception as e:
        return _error(str(e), 500)


# ── Deploy All ──────────────────────────

@mini_app_admin_bp.route('/mini-app/deploy-all', methods=['POST'])
def mini_app_deploy_all():
    """Deploy version to all configured platforms at once."""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    version_id = data.get('version_id')
    if not version_id:
        return _error('version_id is required')

    from .models import get_version
    version = get_version(version_id)
    if not version:
        return _error('Version not found', 404)

    platforms = [p for p in _get_mini_app_platforms() if p.get('configured')]
    if not platforms:
        return _success({'note': 'No platforms configured. Configure at least one in Dev Accounts.'})

    results = {}
    for p in platforms:
        pid = p.get('id', p.get('platform', ''))
        try:
            creds = _build_deployer_credentials(pid)
            from .mini_app.deployer import MiniAppDeployer
            deployer = MiniAppDeployer(dev_accounts={pid: creds} if creds else {})

            if pid in ('telegram',):
                webapp_url = data.get('webapp_url', '')
                res = deployer.deploy_telegram(webapp_url) if (webapp_url and creds) else {'success': False, 'error': 'webapp_url or credentials required'}
            elif pid in ('line',):
                res = deployer.deploy_line(data.get('liff_id'), data.get('url')) if creds else {'success': False, 'error': 'line credentials required'}
            else:
                res = {'success': True, 'note': 'Package ready for manual upload'}
            results[pid] = res
        except Exception as e:
            results[pid] = {'success': False, 'error': str(e)}

    all_ok = all(r.get('success') for r in results.values())
    return jsonify({'data': results, 'success': all_ok})


# ── Mini App Preview Routes ──────────────────────────

@mini_app_admin_bp.route('/mini-app/preview/<int:version_id>')
def mini_app_preview(version_id):
    """Render mini-app preview page from AI-generated plan."""
    admin, err = _require_admin()
    if err: return err

    from .models import get_version
    version = get_version(version_id)
    if not version:
        return 'Version not found', 404

    plan = version.get('ai_plan')
    if not plan:
        return 'No AI plan found for this version', 404

    from .mini_app.preview_renderer import MiniAppPreviewRenderer
    renderer = MiniAppPreviewRenderer()
    html = renderer.render(plan)
    return html


@mini_app_admin_bp.route('/mini-app/preview/<int:version_id>/data')
def mini_app_preview_data(version_id):
    """Return draft data for the preview editor (compatible with existing editor API)."""
    admin, err = _require_admin()
    if err: return err

    from .models import get_version
    version = get_version(version_id)
    if not version:
        return jsonify({'error': 'Version not found'}), 404

    plan = version.get('ai_plan', {})

    # Build draft_blocks compatible with editor JS API
    draft_blocks = {}
    for page in plan.get('pages', []):
        slug = page.get('slug', '')
        page_blocks = []
        for i, section in enumerate(page.get('sections', [])):
            page_blocks.append({
                'id': i + 1,
                'title': section.get('title', ''),
                'content': section.get('description', section.get('subtitle', '')),
                'icon': section.get('icon', ''),
                'block_type': section.get('block_type', 'text'),
                'is_published': 0,
            })
        draft_blocks[slug] = page_blocks

    # Build draft_tokens from plan
    brand = plan.get('brand', {})
    theme = plan.get('theme', {})
    draft_tokens = {
        'brand': {
            'site_name': brand.get('app_name', ''),
            'tagline': brand.get('tagline', ''),
            'brand_story': brand.get('brand_story', ''),
            'slogan': brand.get('tagline', ''),
        },
        'colors': {
            'primary': theme.get('primary_color', '#4F46E5'),
            'secondary': theme.get('secondary_color', '#10B981'),
            'accent': theme.get('accent_color', '#F59E0B'),
        },
        'meta': {
            'mini_app': True,
        },
    }

    return jsonify({
        'draft_tokens': draft_tokens,
        'draft_blocks': draft_blocks,
        'mini_app': True,
        'version_id': version_id,
    })
