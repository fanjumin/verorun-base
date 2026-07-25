#!/usr/bin/env python3
"""Site Builder — Flask Blueprint Routes

Endpoints: ~13
Prefix: /admin/site-builder/
"""

import os, sys, json, yaml

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

    try:
        from site_builder.engine import SiteBuilderEngine
        import logging, traceback
        logger = logging.getLogger(__name__)
        engine = SiteBuilderEngine()

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
        logger.error(
            f"Site Builder preview failed: user_input={user_input[:100]}, "
            f"prompt_id={prompt_id}, error={e}, traceback={traceback.format_exc()}"
        )
        error_msg = str(e)[:500]
        return _error(_('Plan generation failed') + f': {error_msg}', 500)


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

    # 4. Save version snapshot before promoting
    from site_builder.site_settings.models import save_site_version
    version_info = save_site_version()

    # 5. Promote tokens: draft_json → token_json
    promote_draft_tokens()

    # 6. Promote blocks: is_published=0 → is_published=1
    with get_db() as conn:
        conn.execute("UPDATE cms_blocks SET is_published=1 WHERE is_published=0")
        conn.execute("UPDATE cms_posts SET is_published=1 WHERE is_published=0")
        conn.commit()

    return _success({
        'published': True,
        'version': version_info,
    }, 'Draft published to production')


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

    raw_tokens = get_draft_tokens()
    if raw_tokens is None:
        raw_tokens = {}

    # Ensure nested keys exist to prevent Jinja2 UndefinedError
    draft_tokens = {
        'brand': raw_tokens.get('brand', {
            'site_name': 'Site Name',
            'slogan': 'Welcome',
            'brand_story': '',
        }),
        'colors': raw_tokens.get('colors', {}),
        'typography': raw_tokens.get('typography', {}),
        'spacing': raw_tokens.get('spacing', {}),
        'navigation': raw_tokens.get('navigation', {'items': []}),
        'footer': raw_tokens.get('footer', {'copyright': '\u00a9 AI Generated Preview'}),
    }

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
# ── Draft Editor API (Preview-as-Editor) ────────────────────
# ══════════════════════════════════════════════════════════════


@site_builder_bp.route('/api/draft/update-block', methods=['POST'])
def update_draft_block():
    """Update a single draft block field (text edit, visibility, etc.)"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    block_id = data.get('block_id')
    field = data.get('field', '')
    value = data.get('value', '')
    scope = data.get('scope', 'block')  # 'block' | 'token'

    if not block_id:
        return _error('block_id is required')

    # Whitelist: allowed fields to update
    allowed_fields = {'title', 'subtitle', 'content', 'link_text', 'link_url', 'image_url', 'icon', 'extra_json'}
    if field not in allowed_fields:
        return _error(f'Field "{field}" is not editable')

    if scope == 'token':
        # Special block_id -> update design_tokens.draft_json
        from site_builder.site_settings.models import update_draft_token_field
        ok, tokens = update_draft_token_field(block_id, field, value)
        if not ok:
            return _error(f'Unknown token block_id: {block_id}')
        return _success({'block_id': block_id, 'field': field, 'value': value})
    else:
        # Numeric block_id -> update cms_blocks
        from models import get_db
        with get_db() as conn:
            if field == 'extra_json':
                # Merge extra_json (don't overwrite entire field)
                existing = conn.execute(
                    "SELECT extra_json FROM cms_blocks WHERE id=%s AND is_published=0",
                    (block_id,)
                ).fetchone()
                if not existing:
                    return _error('Block not found', 404)
                current = json.loads(existing['extra_json'] or '{}')
                if isinstance(value, dict):
                    current.update(value)
                else:
                    current = value
                value = json.dumps(current, ensure_ascii=False)

            conn.execute(
                f"UPDATE cms_blocks SET {field}=%s, updated_at=NOW() WHERE id=%s AND is_published=0",
                (value, block_id)
            )
            conn.commit()
        return _success({'block_id': block_id, 'field': field, 'value': value})


@site_builder_bp.route('/api/draft/update-block-order', methods=['POST'])
def update_draft_block_order():
    """Batch update block positions (drag-sort result)"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    order = data.get('order', [])  # [{block_id: 1, position: 0}, ...]

    if not order or not isinstance(order, list):
        return _error('order must be a non-empty array')

    from models import get_db
    with get_db() as conn:
        for item in order:
            bid = item.get('block_id')
            pos = item.get('position')
            if bid is not None and pos is not None:
                conn.execute(
                    "UPDATE cms_blocks SET position=%s, updated_at=NOW() WHERE id=%s AND is_published=0",
                    (pos, bid)
                )
        conn.commit()

    return _success({'updated': len(order)})


@site_builder_bp.route('/api/draft/delete-block', methods=['POST'])
def delete_draft_block():
    """Soft-delete a draft block (set extra_json.deleted=true)"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    block_id = data.get('block_id')

    if not block_id:
        return _error('block_id is required')

    from models import get_db
    with get_db() as conn:
        existing = conn.execute(
            "SELECT extra_json FROM cms_blocks WHERE id=%s AND is_published=0",
            (block_id,)
        ).fetchone()
        if not existing:
            return _error('Block not found', 404)

        current = json.loads(existing['extra_json'] or '{}')
        current['deleted'] = True
        conn.execute(
            "UPDATE cms_blocks SET extra_json=%s, updated_at=NOW() WHERE id=%s AND is_published=0",
            (json.dumps(current, ensure_ascii=False), block_id)
        )
        conn.commit()

    return _success({'block_id': block_id, 'deleted': True})


@site_builder_bp.route('/api/draft/add-block', methods=['POST'])
def add_draft_block():
    """Insert a new block at a specified position"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    page = data.get('page', 'home')
    position = data.get('position', 0)
    block_type = data.get('block_type', 'feature-card')
    title = data.get('title', 'New Section')
    content = data.get('content', '')
    icon = data.get('icon', '')

    from models import get_db
    with get_db() as conn:
        # Shift existing blocks' positions to make room
        conn.execute(
            "UPDATE cms_blocks SET position=position+1 WHERE page=%s AND position>=%s AND is_published=0",
            (page, position)
        )

        row = conn.execute(
            """INSERT INTO cms_blocks (page, position, block_type, title, content, icon, is_published, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, 0, NOW(), NOW()) RETURNING id""",
            (page, position, block_type, title, content, icon)
        ).fetchone()
        new_id = row['id'] if row else None
        conn.commit()

    return _success({'block_id': new_id, 'page': page, 'position': position})


@site_builder_bp.route('/api/draft/update-tokens', methods=['POST'])
def update_draft_tokens():
    """Update design tokens (colors/spacing/typography/navigation/footer)"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    scope = data.get('scope', '')  # colors | spacing | typography | navigation | footer
    new_data = data.get('data', {})

    allowed_scopes = {'colors', 'spacing', 'typography', 'navigation', 'footer'}
    if scope not in allowed_scopes:
        return _error(f'Invalid scope: {scope}')

    from site_builder.site_settings.models import get_draft_tokens, save_draft_tokens

    tokens = get_draft_tokens()
    if tokens is None:
        tokens = {}

    # Deep merge (preserve other scopes unchanged)
    if scope in tokens and isinstance(tokens[scope], dict):
        tokens[scope].update(new_data)
    else:
        tokens[scope] = new_data

    save_draft_tokens('platform', tokens)
    return _success({'scope': scope, 'updated': new_data})


@site_builder_bp.route('/api/draft/upload-image', methods=['POST'])
def upload_draft_image():
    """Upload a replacement image for a draft block"""
    admin, err = _require_admin()
    if err: return err

    if 'file' not in request.files:
        return _error('No file uploaded')

    file = request.files['file']
    block_id = request.form.get('block_id', '')
    field = request.form.get('field', 'image_url')

    # Validate file type
    allowed_ext = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return _error(f'Unsupported file type: {ext}')

    # Limit size to 5MB
    file.seek(0, 2)
    if file.tell() > 5 * 1024 * 1024:
        return _error('File too large (max 5MB)')
    file.seek(0)

    # Save file
    import uuid
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(
        os.path.dirname(__file__), '..', 'admin', 'static', 'uploads', 'draft'
    )
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    url = f"/static/uploads/draft/{filename}"

    # Update data
    if block_id and block_id.isdigit():
        from models import get_db
        with get_db() as conn:
            conn.execute(
                "UPDATE cms_blocks SET image_url=%s WHERE id=%s AND is_published=0",
                (url, int(block_id))
            )
            conn.commit()
    else:
        # Update design_tokens (e.g. logo_url, favicon_url)
        from site_builder.site_settings.models import get_draft_tokens, save_draft_tokens
        tokens = get_draft_tokens() or {}
        tokens.setdefault('brand', {})[field] = url
        save_draft_tokens('platform', tokens)

    return _success({'url': url, 'block_id': block_id, 'field': field})


# ══════════════════════════════════════════════════════════════
# ── Site Version History API ──────────────────────────────────
# ══════════════════════════════════════════════════════════════


@site_builder_bp.route('/versions', methods=['GET'])
def list_versions():
    """List all site versions (newest first)."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.site_settings.models import list_site_versions
    versions = list_site_versions()
    return _success({'versions': versions})


@site_builder_bp.route('/versions/<int:version_id>', methods=['GET'])
def get_version(version_id):
    """Get full version data (snapshot + blocks) for preview."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.site_settings.models import get_site_version
    version = get_site_version(version_id)
    if not version:
        return _error('Version not found', 404)
    return _success(version)


@site_builder_bp.route('/versions/<int:version_id>/restore', methods=['POST'])
def restore_version(version_id):
    """Restore a version snapshot back to draft.
    
    Does NOT auto-publish. User can then edit and publish manually.
    """
    admin, err = _require_admin()
    if err: return err

    from site_builder.site_settings.models import restore_site_version
    ok = restore_site_version(version_id)
    if not ok:
        return _error('Version not found or restore failed', 404)
    return _success({'restored': version_id}, 'Version restored to draft. Edit and publish to make it live.')


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

# Workspace root — generated projects/versions are cached here
MINIAPP_WORKSPACE = os.path.join(BASE_DIR, 'mini_app', 'workspace')


def _cleanup_old_tasks():
    now = datetime.now().timestamp()
    expired = [k for k, v in _mini_app_tasks.items()
               if now - v.get('created_at', 0) > _MINI_APP_TASK_TTL]
    for k in expired:
        _mini_app_tasks.pop(k, None)


def _project_version_dir(slug: str, version_no: int) -> str:
    """Return the absolute output dir for a project version."""
    return os.path.join(MINIAPP_WORKSPACE, slug, f'v{version_no}')


# ── Mini-App Project Management ────────────────────────

@site_builder_bp.route('/mini-app/projects', methods=['GET'])
def mini_app_list_projects():
    """List all mini-app projects."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import list_projects
    return _success(list_projects())


@site_builder_bp.route('/mini-app/projects', methods=['POST'])
def mini_app_create_project():
    """Create a new mini-app project."""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True, silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return _error('Project name is required')

    from site_builder.models import create_project
    project = create_project(
        name=name,
        description=data.get('description', ''),
        created_by=admin.get('user_id', 0),
    )
    return _success(project, _('Project created'))


@site_builder_bp.route('/mini-app/projects/<int:project_id>', methods=['GET'])
def mini_app_get_project(project_id):
    """Get a project with its version history."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_project, list_versions
    project = get_project(project_id)
    if not project:
        return _error('Project not found', 404)
    project['versions'] = list_versions(project_id)
    return _success(project)


@site_builder_bp.route('/mini-app/projects/<int:project_id>', methods=['DELETE'])
def mini_app_delete_project(project_id):
    """Delete a project (DB records + workspace files)."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_project, delete_project
    project = get_project(project_id)
    if not project:
        return _error('Project not found', 404)

    # Remove workspace directory for this project
    proj_dir = os.path.join(MINIAPP_WORKSPACE, project['slug'])
    if os.path.isdir(proj_dir):
        shutil.rmtree(proj_dir, ignore_errors=True)

    delete_project(project_id)
    return _success(None, _('Project deleted'))


@site_builder_bp.route('/mini-app/projects/<int:project_id>/versions', methods=['GET'])
def mini_app_list_versions(project_id):
    """List all versions of a project."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_project, list_versions
    if not get_project(project_id):
        return _error('Project not found', 404)
    return _success(list_versions(project_id))


@site_builder_bp.route('/mini-app/versions/<int:version_id>/download/<platform>', methods=['GET'])
def mini_app_download_version(version_id, platform):
    """Download a specific version's platform output as .zip (from workspace)."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_version
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
        from site_builder.mini_app.packager import MiniAppPackager
        # Package into the version's own directory to keep artifacts together
        pkg_base = os.path.join(os.path.dirname(output_dir), 'packages')
        os.makedirs(pkg_base, exist_ok=True)
        packager = MiniAppPackager(output_base=pkg_base)
        zip_path = packager.package(platform, output_dir)

        from flask import send_file
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'{platform}-v{version["version_no"]}.zip'
        )
    except Exception as e:
        return _error(str(e), 500)


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


# ── Mini App AI Helpers ──────────────────────────────

def _mini_app_generate_with_ai(project, platforms, prompt, template, options,
                                create_version, next_version_no, admin):
    """AI-prompt branch: call LLM to build plan, create version, return preview URL."""

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


def _save_ai_fields(version_id, prompt, template, plan):
    """Persist AI-generation metadata to the mini_app_versions row."""
    try:
        from models import get_db
        from site_builder.models import TABLE_MINIAPP_VERSIONS
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
    prompts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prompts')
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
    """Build a complete Mini App plan via Master Agent LLM from template + user input.

    Calls the Master Agent in up to (2 + N_pages) rounds:
      1. Parse user requirement (brand name, features, style)
      2. Brand configuration (name, tagline, story, colors)
      3. Per-page content (sections with block_type + widgets)

    Falls back to template defaults when LLM is unavailable (graceful degradation).

    Args:
        tmpl: Loaded YAML prompt template dict with 'prompts' and 'defaults' keys
        prompt_text: Raw user prompt from the frontend AI input

    Returns:
        Plan dict with keys: brand, theme, tabBar, pages, widgets
    """
    import re
    from agent_matrix.engine import UnifiedLLM
    from agent_matrix import models as agent_models

    defaults = tmpl.get('defaults', {})
    prompts = tmpl.get('prompts', {})
    tabbar_default = tmpl.get('mini_app', {}).get('tabBar', {}).get('default', [])

    industry = defaults.get('industry', 'General')
    style = defaults.get('style', 'Modern')

    # ── Resolve Master Agent ──
    engine = None
    try:
        agents = agent_models.list_agents(role_type='master', active_only=True)
        if agents:
            engine = UnifiedLLM(agents[0])
    except Exception:
        pass

    def _call_llm_json(system_msg, user_msg, temperature=0.3, max_tokens=2000):
        """Call LLM and parse JSON from response. Returns {} on any failure."""
        if not engine:
            return {}
        try:
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ]
            raw = engine.chat(messages, temperature=temperature, max_tokens=max_tokens)
            # Attempt direct JSON extraction
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                return json.loads(match.group(0))
            # Attempt markdown code block
            match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
            if match:
                return json.loads(match.group(1))
            logger.warning('[MiniApp] LLM JSON parse failed, raw: %s', raw[:200])
        except Exception as exc:
            logger.warning('[MiniApp] LLM call failed: %s', exc)
        return {}

    # ── Round 1: Parse user requirement ──
    parse_tpl = prompts.get('parse', '')
    if parse_tpl and engine:
        parse_tpl = parse_tpl.replace('{行业}', industry).replace('{用户输入}', prompt_text)
        parsed = _call_llm_json(parse_tpl, prompt_text)
    else:
        parsed = {}

    brand_name = parsed.get('brand_name',
        defaults.get('site_name', 'Mini App').replace('{品牌名称}', 'Mini App'))
    style_pref = parsed.get('style_preference', style)

    # ── Round 2: Brand & theme configuration ──
    brand_tpl = prompts.get('brand', '')
    if brand_tpl and engine:
        brand_tpl = (brand_tpl
            .replace('{品牌名称}', brand_name)
            .replace('{行业}', industry)
            .replace('{风格偏好}', style_pref))
        brand = _call_llm_json(brand_tpl, 'Generate brand config for: ' + brand_name)
    else:
        brand = {}

    brand.setdefault('app_name', brand_name)
    brand.setdefault('tagline', defaults.get('tone', ''))
    brand.setdefault('brand_story', '')
    brand.setdefault('primary_color', defaults.get('primary_color', '#4F46E5'))
    brand.setdefault('secondary_color', defaults.get('accent_color', '#10B981'))
    brand.setdefault('accent_color', defaults.get('accent_color', '#F59E0B'))

    # ── Round 3: Per-page content (one LLM call per page) ──
    pages = []
    all_widgets = []

    for p in tmpl.get('pages', []):
        slug = p.get('id', '')
        title = p.get('name', slug)
        page_key = 'page_' + slug
        page_tpl = prompts.get(page_key, '')

        if page_tpl and engine:
            page_tpl = (page_tpl
                .replace('{品牌名称}', brand_name)
                .replace('{行业}', industry)
                .replace('{风格偏好}', style_pref))
            content = _call_llm_json(page_tpl, 'Generate page: ' + title)
            sections = content.get('sections', [])
            for w in content.get('widgets', []):
                w.setdefault('page', slug)
                all_widgets.append(w)
        else:
            sections = []

        pages.append({
            'slug': slug,
            'title': title,
            'sections': sections,
        })

    return {
        'brand': brand,
        'theme': {
            'primary_color': brand.get('primary_color', '#4F46E5'),
            'secondary_color': brand.get('secondary_color', '#10B981'),
            'accent_color': brand.get('accent_color', '#F59E0B'),
        },
        'tabBar': tabbar_default,
        'pages': pages,
        'widgets': all_widgets,
    }


@site_builder_bp.route('/mini-app/generate', methods=['POST'])
def mini_app_generate():
    """Trigger mini-app generation for specified platforms.

    Optional project binding:
        - project_id: generate a new version under an existing project
        - project_name: create a new project (if project_id not given) and
                        generate its first version
    When bound to a project, output is written to a versioned workspace dir
    (mini_app/workspace/<slug>/v<N>/) and recorded in the DB (version history).
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
    from site_builder.models import (get_project, create_project,
                                      next_version_no, create_version)
    project = None
    if project_id:
        project = get_project(project_id)
        if not project:
            return _error('Project not found', 404)
    elif project_name:
        project = create_project(name=project_name, created_by=admin.get('user_id', 0))

    # ── AI Prompt Branch ──
    if prompt and project:
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

            from services.brand_service import get_brand_settings
            from site_builder.site_settings.models import get_draft_tokens
            from site_builder.mini_app.engine import MiniAppEngine

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
        'project_id': task.get('project_id'),
        'project_slug': task.get('project_slug'),
        'version_no': task.get('version_no'),
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


# ── Mini App Preview Routes ──────────────────────────

@site_builder_bp.route('/mini-app/preview/<int:version_id>')
def mini_app_preview(version_id):
    """Render mini-app preview page from AI-generated plan."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_version
    version = get_version(version_id)
    if not version:
        return 'Version not found', 404

    plan = version.get('ai_plan')
    if not plan:
        return 'No AI plan found for this version', 404

    from site_builder.mini_app.preview_renderer import MiniAppPreviewRenderer
    renderer = MiniAppPreviewRenderer()
    html = renderer.render(plan)
    return html


@site_builder_bp.route('/mini-app/preview/<int:version_id>/data')
def mini_app_preview_data(version_id):
    """Return draft data for the preview editor (compatible with existing editor API)."""
    admin, err = _require_admin()
    if err: return err

    from site_builder.models import get_version
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
