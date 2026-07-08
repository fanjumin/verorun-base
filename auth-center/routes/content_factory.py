#!/usr/bin/env python3
"""Content Factory Routes — /admin/content-factory/*"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, request, jsonify
from models import get_db
from routes.admin import _require_admin, _log
from services.content_factory import run_collection
from services.content_factory.ai_processor import process_raw_content, batch_process

logger = logging.getLogger(__name__)
cf_bp = Blueprint('content_factory', __name__, url_prefix='/admin/content-factory')


# =============================================
# 1. 来源管理 CRUD
# =============================================

@cf_bp.route('/sources', methods=['GET'])
def list_sources():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM content_sources ORDER BY sort_order, id'
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@cf_bp.route('/sources', methods=['POST'])
def add_source():
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    required = ['name', 'source_type', 'url']
    for k in required:
        if not d.get(k):
            return jsonify({'success': False, 'error': f'{k} 必填'})
    with get_db() as conn:
        conn.execute(
            """INSERT INTO content_sources (name, source_type, platform, url, config_json,
               crawl_interval, keywords, max_per_run, created_by)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (d['name'], d['source_type'], d.get('platform', ''),
             d['url'], json.dumps(d.get('config', {}), ensure_ascii=False),
             int(d.get('crawl_interval', 0)),
             d.get('keywords', ''),
             int(d.get('max_per_run', 10)),
             admin['user_id'])
        )
        conn.commit()
        sid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    _log(admin['user_id'], 'cf_source_add', 'content_source', str(sid), f"来源: {d['name']}")
    return jsonify({'success': True, 'id': sid})


@cf_bp.route('/sources/<int:sid>', methods=['PUT'])
def update_source(sid):
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    fields = ['name', 'source_type', 'platform', 'url', 'crawl_interval',
              'keywords', 'max_per_run', 'is_active', 'sort_order']
    sets = []
    vals = []
    for k in fields:
        if k in d:
            sets.append(f'{k}=?')
            vals.append(d[k])
    if not sets:
        return jsonify({'success': False, 'error': '无更新字段'})
    sets.append("config_json=?")
    vals.append(json.dumps(d.get('config', {}), ensure_ascii=False))
    vals.append(sid)
    with get_db() as conn:
        conn.execute(
            f"UPDATE content_sources SET {', '.join(sets)} WHERE id=?", vals
        )
        conn.commit()
    _log(admin['user_id'], 'cf_source_update', 'content_source', str(sid))
    return jsonify({'success': True})


@cf_bp.route('/sources/<int:sid>', methods=['DELETE'])
def delete_source(sid):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute('DELETE FROM content_sources WHERE id=?', (sid,))
        conn.commit()
    _log(admin['user_id'], 'cf_source_delete', 'content_source', str(sid))
    return jsonify({'success': True})


# =============================================
# 2. 采集执行
# =============================================

@cf_bp.route('/crawl', methods=['POST'])
def trigger_crawl():
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    source_id = d.get('source_id')
    if not source_id:
        return jsonify({'success': False, 'error': 'source_id 必填'})
    result = run_collection(source_id, admin_id=admin['user_id'])
    _log(admin['user_id'], 'cf_crawl', 'content_source', str(source_id),
         f"新增 {result.get('inserted',0)}, 跳过 {result.get('skipped',0)}")
    return jsonify(result)


# =============================================
# 3. 原始内容列表
# =============================================

@cf_bp.route('/contents', methods=['GET'])
def list_contents():
    admin, err = _require_admin()
    if err: return err
    source_id = request.args.get('source_id')
    status = request.args.get('status', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    offset = (page - 1) * limit

    where = ['1=1']
    params = []
    if source_id:
        where.append('r.source_id=?')
        params.append(int(source_id))
    if status:
        where.append('r.status=?')
        params.append(status)

    with get_db() as conn:
        total = conn.execute(
            f'SELECT COUNT(*) FROM raw_contents r WHERE {" AND ".join(where)}', params
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT r.*, s.name as source_name
                FROM raw_contents r LEFT JOIN content_sources s ON r.source_id=s.id
                WHERE {" AND ".join(where)}
                ORDER BY r.id DESC LIMIT ? OFFSET ?""",
            params + [limit, offset]
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows],
                    'total': total, 'page': page, 'limit': limit})


@cf_bp.route('/contents/<int:rid>', methods=['DELETE'])
def delete_content(rid):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute('DELETE FROM raw_contents WHERE id=?', (rid,))
        conn.execute('DELETE FROM processed_contents WHERE raw_id=?', (rid,))
        conn.commit()
    _log(admin['user_id'], 'cf_delete', 'raw_content', str(rid))
    return jsonify({'success': True})


# =============================================
# 4. AI 加工
# =============================================

@cf_bp.route('/process', methods=['POST'])
def process():
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    raw_ids = d.get('raw_ids', [])
    if not raw_ids:
        return jsonify({'success': False, 'error': 'raw_ids 必填'})
    result = batch_process(raw_ids, admin_id=admin['user_id'])
    _log(admin['user_id'], 'cf_process', '', '',
         f"加工 {len(raw_ids)} 条: OK={result.get('ok',0)} FAIL={result.get('fail',0)}")
    return jsonify(result)


# =============================================
# 5. 加工内容列表
# =============================================

@cf_bp.route('/processed', methods=['GET'])
def list_processed():
    admin, err = _require_admin()
    if err: return err
    status = request.args.get('status', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    offset = (page - 1) * limit

    where = ['1=1']
    params = []
    if status:
        where.append('p.status=?')
        params.append(status)

    with get_db() as conn:
        total = conn.execute(
            f'SELECT COUNT(*) FROM processed_contents p WHERE {" AND ".join(where)}', params
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT p.*, r.title as raw_title, r.source_url
                FROM processed_contents p
                LEFT JOIN raw_contents r ON p.raw_id=r.id
                WHERE {" AND ".join(where)}
                ORDER BY p.id DESC LIMIT ? OFFSET ?""",
            params + [limit, offset]
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows],
                    'total': total, 'page': page, 'limit': limit})


@cf_bp.route('/processed/batch-delete', methods=['POST'])
def batch_delete_processed():
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    ids = d.get('ids', [])
    if not ids:
        return jsonify({'success': False, 'error': 'ids 必填'})
    with get_db() as conn:
        for pid in ids:
            conn.execute('DELETE FROM skill_pushes WHERE processed_id=?', (pid,))
            conn.execute('DELETE FROM processed_contents WHERE id=?', (pid,))
        conn.commit()
    _log(admin['user_id'], 'cf_batch_delete', 'processed', f'{len(ids)}条')
    return jsonify({'success': True, 'deleted': len(ids)})


# =============================================
# 6. AI 排版 + 配图 (给CMS编辑器用)
# =============================================
@cf_bp.route('/ai-format', methods=['POST'])
def ai_format():
    """AI 深度排版：修复格式 + 生成摘要 + 配图建议"""
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    content = d.get('content', '')
    title = d.get('title', '')
    if not content.strip():
        return jsonify({'success': False, 'error': '内容不可为空'})
    from services.ai_content_generator import _qwen_chat
    prompt = f"""你是一个专业的内容排版编辑。请仔细阅读全文，然后执行以下步骤：

## 任务
1. **修复排版错误**：纠正缩进、标点符号(全角/半角混用)、段落分段、多余换行
2. **重新组织结构**：用 <h2> 或 <h3> 划分章节，每章之间用 <p> 段落，列表用 <ul><li>
3. **数据突出**：重要数字、百分比、日期用 <strong> 加粗
4. **生成摘要**：用 <blockquote> 包裹一句话摘要放在正文开头
5. **配图建议**：在正文末尾添加 <p class="cover-suggest">配图建议：xxx</p>，建议一张与内容相关的封面图描述

## 输出要求
- 输出纯 HTML，不要用 markdown
- 段落分明，每段之间空行
- 保持原文意思完整不变
- 不要丢失任何原文内容

原文标题：{title}
原文正文：
{content[:8000]}"""
    try:
        result = _qwen_chat([{'role': 'user', 'content': prompt}], temperature=0.3)
        _log(admin['user_id'], 'cf_ai_format', '', '', f'AI排版: {title[:30]}')
        return jsonify({'success': True, 'formatted': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@cf_bp.route('/ai-cover', methods=['POST'])
def ai_cover():
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    title = d.get('title', '')
    topic = d.get('topic', '')
    prompt_text = d.get('prompt', '')
    if not prompt_text:
        prompt_text = f'科技金融封面图：{topic or title}，深色科幻风格，蓝紫渐变'
    from services.ai_content_generator import generate_image
    try:
        url = generate_image(prompt_text, size='1280x720')
        _log(admin['user_id'], 'cf_ai_cover', '', '', f'配图: {title[:30]}')
        return jsonify({'success': True, 'image_url': url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# =============================================
# 7. 编辑加工内容
# =============================================

@cf_bp.route('/processed/<int:pid>', methods=['GET'])
def get_processed(pid):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        row = conn.execute(
            """SELECT p.*, r.title as raw_title, r.source_url, r.content_text as raw_text
               FROM processed_contents p LEFT JOIN raw_contents r ON p.raw_id=r.id
               WHERE p.id=?""",
            (pid,)
        ).fetchone()
    if not row:
        return jsonify({'success': False, 'error': '不存在'})
    return jsonify({'success': True, 'data': dict(row)})


@cf_bp.route('/processed/<int:pid>', methods=['PUT'])
def update_processed(pid):
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    fields = ['title', 'summary', 'body', 'keywords', 'risk_level', 'status']
    sets = []
    vals = []
    for k in fields:
        if k in d:
            sets.append(f'{k}=?')
            vals.append(d[k])
    if sets:
        vals.append(pid)
        with get_db() as conn:
            conn.execute(
                f"UPDATE processed_contents SET {', '.join(sets)} WHERE id=?", vals
            )
            conn.commit()
    return jsonify({'success': True})


# =============================================
# 8. 审核流程
# =============================================

@cf_bp.route('/review', methods=['POST'])
def review_content():
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    pid = d.get('processed_id')
    action = d.get('action', '')  # submit_review / approve / reject / back_to_draft
    if not pid or action not in ('submit_review', 'approve', 'reject', 'back_to_draft'):
        return jsonify({'success': False, 'error': 'processed_id 和 action 必填'})

    status_map = {
        'submit_review': 'review',   # draft → review
        'approve': 'approved',       # review → approved
        'reject': 'rejected',        # review → rejected
        'back_to_draft': 'draft',    # any → draft
    }
    target = status_map[action]

    with get_db() as conn:
        pc = conn.execute('SELECT * FROM processed_contents WHERE id=?', (pid,)).fetchone()
        if not pc:
            return jsonify({'success': False, 'error': '不存在'})
        # 状态机校验
        cur = pc['status']
        valid_transitions = {
            'draft': ['submit_review', 'publish'],
            'review': ['approve', 'reject'],
            'rejected': ['submit_review', 'back_to_draft'],
            'approved': ['publish', 'back_to_draft'],
            'published': [],
        }
        if action not in valid_transitions.get(cur, []):
            return jsonify({'success': False, 'error': f'状态 {cur} 不允许执行 {action}'})

        conn.execute(
            "UPDATE processed_contents SET status=?, reviewed_by=?, reviewed_at=datetime('now') WHERE id=?",
            (target, admin['user_id'], pid)
        )
        conn.commit()

    action_labels = {'submit_review': '提交审核', 'approve': '通过', 'reject': '驳回', 'back_to_draft': '退回草稿'}
    _log(admin['user_id'], f'cf_review_{action}', 'processed_content', str(pid),
         f'{action_labels[action]}: {pc["title"][:50]}')
    return jsonify({'success': True, 'status': target})


# =============================================
# 9. 发布 (内部 → CMS 文章)
# =============================================

@cf_bp.route('/publish', methods=['POST'])
def publish():
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    pid = d.get('processed_id')
    platform = d.get('platform', 'internal')
    if not pid:
        return jsonify({'success': False, 'error': 'processed_id 必填'})

    with get_db() as conn:
        pc = conn.execute('SELECT * FROM processed_contents WHERE id=?', (pid,)).fetchone()
    if not pc:
        return jsonify({'success': False, 'error': '加工内容不存在'})
    if pc['status'] not in ('approved', 'draft'):
        return jsonify({'success': False, 'error': f'当前状态 {pc["status"]} 不允许发布（需 approved 或 draft）'})

    if platform == 'internal':
        from models.cms import upsert_post
        import time
        slug = f'cf-{pid}-{int(time.time())}'
        post = upsert_post({
            'slug': slug,
            'category': 'content_factory',
            'title': pc['title'] or f"内容工厂#{pid}",
            'excerpt': pc['summary'] or '',
            'content': pc['body'] or '',
            'cover_image': pc['image_url'] or '',
            'author': f'admin_{admin["display_name"]}',
            'is_published': 1,
            'source': 'factory',
            'source_id': pid,
        })
        post_id = post.get('id')
        with get_db() as conn:
            conn.execute(
                "UPDATE processed_contents SET is_published=1, status='published' WHERE id=?",
                (pid,)
            )
            conn.commit()
        _log(admin['user_id'], 'cf_publish', 'processed_content', str(pid),
             f"发布到本站 post_id={post_id}")
        return jsonify({'success': True, 'post_id': post_id, 'platform': 'internal'})

    elif platform in ('social', 'both'):
        from routes.social_push import _publish_to_platform
        social_platforms = d.get('social_platforms', ['wechat'])
        auto_publish = d.get('auto_publish', False)
        social_results = []
        for sp in social_platforms:
            result = _publish_to_platform(
                platform=sp,
                title=pc['title'] or '',
                body=pc['body'] or '',
                body_html=pc.get('body_html', '') or pc['body'] or '',
                summary=pc['summary'] or '',
                author=f'admin_{admin["display_name"]}',
                cover_image_url=pc['image_url'] or '',
                auto_publish=auto_publish,
                admin_id=admin['user_id'],
            )
            social_results.append(result)

        # 如果 both，先发 CMS 再发社媒
        post_id = None
        if platform == 'both':
            from models.cms import upsert_post
            import time
            slug = f'cf-{pid}-{int(time.time())}'
            post = upsert_post({
                'slug': slug,
                'category': 'content_factory',
                'title': pc['title'] or f"内容工厂#{pid}",
                'excerpt': pc['summary'] or '',
                'content': pc['body'] or '',
                'cover_image': pc['image_url'] or '',
                'author': f'admin_{admin["display_name"]}',
                'is_published': 1,
                'source': 'factory',
                'source_id': pid,
            })
            post_id = post.get('id')

        with get_db() as conn:
            conn.execute(
                "UPDATE processed_contents SET is_published=1, status='published' WHERE id=?",
                (pid,)
            )
            conn.commit()

        log_msg = f"社媒发布: {', '.join(social_platforms)}"
        if post_id:
            log_msg += f", CMS post_id={post_id}"
        _log(admin['user_id'], 'cf_publish_social', 'processed_content', str(pid), log_msg)

        resp = {'success': True, 'platform': platform, 'social_results': social_results}
        if post_id:
            resp['post_id'] = post_id
        return jsonify(resp)
    else:
        return jsonify({'success': False, 'error': f'未知发布平台: {platform}'})


# =============================================
# 10. 任务列表
# =============================================

@cf_bp.route('/tasks', methods=['GET'])
def list_tasks():
    admin, err = _require_admin()
    if err: return err
    source_id = request.args.get('source_id')
    limit = int(request.args.get('limit', 20))

    where = ['1=1']
    params = []
    if source_id:
        where.append('t.source_id=?')
        params.append(int(source_id))

    with get_db() as conn:
        rows = conn.execute(
            f"""SELECT t.*, s.name as source_name
                FROM content_tasks t LEFT JOIN content_sources s ON t.source_id=s.id
                WHERE {" AND ".join(where)}
                ORDER BY t.id DESC LIMIT ?""",
            params + [limit]
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


# =============================================
# 11. 仪表盘统计
# =============================================

@cf_bp.route('/stats', methods=['GET'])
def stats():
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        source_count = conn.execute('SELECT COUNT(*) FROM content_sources WHERE is_active=1').fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM raw_contents WHERE status='pending'").fetchone()[0]
        processed = conn.execute("SELECT COUNT(*) FROM processed_contents").fetchone()[0]
        published = conn.execute("SELECT COUNT(*) FROM processed_contents WHERE is_published=1").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM raw_contents WHERE status='failed'").fetchone()[0]
        recent_sources = conn.execute(
            'SELECT name, last_crawled_at FROM content_sources ORDER BY last_crawled_at DESC LIMIT 5'
        ).fetchall()
    return jsonify({'success': True, 'data': {
        'source_count': source_count,
        'pending': pending,
        'processed': processed,
        'published': published,
        'failed': failed,
        'recent_sources': [dict(r) for r in recent_sources],
    }})


# =============================================
# 12. Skill 推送
# =============================================

@cf_bp.route('/push-skill', methods=['POST'])
def push_to_skill():
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    pid = d.get('processed_id')
    target = d.get('target_agent', 'hermes')
    if not pid:
        return jsonify({'success': False, 'error': 'processed_id 必填'})

    from services.content_factory.skill_pusher import push_to_skill as do_push
    result = do_push(pid, admin_id=admin['user_id'], target_agent=target)
    if result['success']:
        _log(admin['user_id'], 'cf_skill_push', 'processed_content', str(pid),
             f"推送到{target}: {result['skill_name']}")
    return jsonify(result)


@cf_bp.route('/pushed-skills', methods=['GET'])
def list_pushed():
    admin, err = _require_admin()
    if err: return err
    from services.content_factory.skill_pusher import list_pushed_skills
    skills = list_pushed_skills()
    return jsonify({'success': True, 'data': skills})


@cf_bp.route('/pushed-skills/<int:push_id>', methods=['DELETE'])
def delete_pushed(push_id):
    admin, err = _require_admin()
    if err: return err
    with get_db() as conn:
        conn.execute("DELETE FROM skill_pushes WHERE id=?", (push_id,))
        conn.commit()
    _log(admin['user_id'], 'cf_skill_delete', 'skill_push', str(push_id))
    return jsonify({'success': True})


# =============================================
# 13. 用户端拉取 Skill API (无认证, 只读)
# =============================================

@cf_bp.route('/api/v1/skills', methods=['GET'])
def api_list_skills():
    """用户端 Hermes/OpenClaw 可调用的拉取列表"""
    agent = request.args.get('agent', 'hermes')
    from services.content_factory.skill_pusher import list_pushed_skills
    skills = list_pushed_skills(limit=50, target_agent=agent)
    return jsonify({
        'success': True,
        'agent': agent,
        'count': len(skills),
        'skills': [{
            'id': s['id'],
            'skill_name': s['skill_name'],
            'title': s['title'],
            'description': s['description'],
            'category': s['skill_category'],
            'version': s['skill_version'],
            'pushed_at': s['last_pushed_at'],
        } for s in skills],
    })


@cf_bp.route('/api/v1/skills/<int:push_id>/download', methods=['GET'])
def api_download_skill(push_id):
    """用户端拉取单个 skill 的 SKILL.md 内容"""
    from services.content_factory.skill_pusher import get_skill_for_download
    skill = get_skill_for_download(push_id)
    if not skill:
        return jsonify({'success': False, 'error': '不存在'}), 404
    return jsonify({'success': True, 'skill': skill})


# =============================================
# 14. 静态页面生成
# =============================================

@cf_bp.route('/generate-static', methods=['POST'])
def generate_static():
    """一键生成静态 HTML — 单篇或全站"""
    admin, err = _require_admin()
    if err: return err
    d = request.get_json() or {}
    action = d.get('action', 'post')
    slug = d.get('slug', '')

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'platform'))
        from staticgen import generate_post, generate_all, generate_category, generate_docs_index

        results = []
        if action == 'all':
            results = generate_all()
        elif action == 'category' and d.get('cat_slug'):
            r = generate_category(d['cat_slug'])
            results = [r]
        elif action == 'docs_index':
            r = generate_docs_index()
            results = [r]
        elif slug:
            r = generate_post(slug)
            results = [r]
        else:
            return jsonify({'success': False, 'error': '请指定 slug 或 action=all'})

        ok = sum(1 for r in results if r.get('ok'))
        fail = sum(1 for r in results if not r.get('ok'))
        _log(admin['user_id'], 'cf_static_gen', '', '',
             f"{action}: {ok} ok, {fail} fail")
        return jsonify({
            'success': True,
            'action': action,
            'ok': ok,
            'fail': fail,
            'results': [{'path': r.get('path', ''), 'ok': r.get('ok', False),
                         'error': r.get('error', '')} for r in results]
        })
    except Exception as e:
        logger.exception("Static generation failed")
        return jsonify({'success': False, 'error': str(e)})


@cf_bp.route('/push-to-knowledge', methods=['POST'])
def push_processed_to_knowledge():
    """将加工内容推送到知识库（调用数据清洗智能体）"""
    admin, err = _require_admin()
    if err:
        return err
    d = request.get_json() or {}
    pid = d.get('processed_id')
    if not pid:
        return jsonify({'success': False, 'error': 'processed_id 必填'}), 400

    with get_db() as conn:
        row = conn.execute("SELECT id, title, body, keywords, content_type "
                           "FROM processed_contents WHERE id=?", (pid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '加工内容不存在'}), 404

    # 拼装原始内容（含标题+正文+关键词）
    raw = f"标题：{row['title'] or ''}\n关键词：{row['keywords'] or ''}\n类型：{row['content_type'] or ''}\n正文：{row['body'] or ''}"

    # 调用 Cleaner 的清洗函数
    from routes.cleaner_agent import process_clean_content
    result = process_clean_content(raw, admin_id=admin['user_id'])

    _log(admin['user_id'], 'cf_to_knowledge', 'processed_content', str(pid),
         f"知识库ID: {result.get('kb_id', '?')}")
    return jsonify(result)
