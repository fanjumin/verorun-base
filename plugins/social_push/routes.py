#!/usr/bin/env python3
"""Social Push Plugin — /admin/social/* 多平台社媒内容发布路由

迁移自 auth-center/routes/social_push.py（Phase 2 物理解耦）。
- 发布日志读写：插件独立库 social_push.db（get_sp_db）
- 主库只读（cms_posts / system_config）：get_main_db
- 发布 services：经 auth-center sys.path 复用

LLM 说明（Phase 3）：
  AI 文案（通义千问）与 AI 配图（通义万相）走全站【公共 LLM 服务】
  services.ai_content_generator，而非本插件私有能力，也不属于"发布平台"。
  agent_matrix 内核自身亦依赖该公共服务，故不下沉、不搬动，保持共享。
  概念上：AI = 创作工具（ai_capabilities），社媒号 = 发布渠道（platforms），二者分离。
"""

import sys, os, json, logging

_auth_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center')
if _auth_dir not in sys.path:
    sys.path.insert(0, _auth_dir)

from flask import Blueprint, request, jsonify
from i18n import _

from .models import get_sp_db

logger = logging.getLogger(__name__)

social_bp = Blueprint('social', __name__, url_prefix='/admin/social')

# 仅"发布渠道"——真实社媒平台。AI 能力不在此列（见文件顶部说明）。
PLATFORM_INFO = {
    'wechat': {'name': _('微信公众号'), 'icon': '💬'},
    'weibo':  {'name': _('微博'),       'icon': '📢'},
    'toutiao':{'name': _('今日头条'),    'icon': '📰'},
}


# ── Helpers ──
def _require_admin():
    from routes.admin import _require_admin as _ra
    return _ra()


def _log(admin_id, action, target_type='', target_id='', detail=''):
    from routes.admin import _log as _l
    _l(admin_id, action, target_type, target_id, detail)


def _get_main_db():
    """主库只读连接（system_config / cms_posts）"""
    from models import get_db
    return get_db()


# =============================================
# 配置检测
# =============================================

@social_bp.route('/check-config', methods=['GET'])
def check_config():
    """Check platform + AI capability config.

    返回结构（Phase 3 拆分）：
      - platforms:       仅【发布渠道】社媒号（wechat/weibo/toutiao）
      - ai_capabilities: 【创作工具】AI 文案/配图（走公共 LLM 服务，非发布平台）
    兼容：仍保留 platforms 字段，但不再混入 AI 项；前端据两字段分区渲染。
    """
    admin, err = _require_admin()
    if err:
        return err
    with _get_main_db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM system_config WHERE key IN "
            "('wechat_app_id','wechat_app_secret','weibo_app_key','weibo_access_token','toutiao_app_id','toutiao_access_token','dashscope_api_key','dashscope_text_key')"
        ).fetchall()
    cfg = {r['key']: r['value'] for r in rows}
    return jsonify({
        'success': True,
        'data': {
            'platforms': [
                {
                    'id': 'wechat',
                    'name': _('微信公众号'),
                    'icon': '💬',
                    'configured': bool(cfg.get('wechat_app_id') and cfg.get('wechat_app_secret')),
                    'fields_needed': [] if (cfg.get('wechat_app_id') and cfg.get('wechat_app_secret')) else ['AppID', 'AppSecret'],
                },
                {
                    'id': 'weibo',
                    'name': _('微博'),
                    'icon': '📢',
                    'configured': bool(cfg.get('weibo_app_key') and cfg.get('weibo_access_token')),
                    'fields_needed': [] if (cfg.get('weibo_app_key') and cfg.get('weibo_access_token')) else ['App Key', 'Access Token'],
                },
                {
                    'id': 'toutiao',
                    'name': _('今日头条'),
                    'icon': '📰',
                    'configured': bool(cfg.get('toutiao_app_id') and cfg.get('toutiao_access_token')),
                    'fields_needed': [] if (cfg.get('toutiao_app_id') and cfg.get('toutiao_access_token')) else ['App ID', 'Access Token'],
                },
            ],
            'ai_capabilities': [
                {
                    'id': 'image_gen',
                    'name': _('AI配图 (通义万相)'),
                    'icon': '🎨',
                    'configured': bool(cfg.get('dashscope_api_key')),
                    'fields_needed': [] if cfg.get('dashscope_api_key') else [_('通义万相 Key')],
                },
                {
                    'id': 'text_gen',
                    'name': _('AI文案 (通义千问)'),
                    'icon': '✍️',
                    'configured': bool(cfg.get('dashscope_text_key')),
                    'fields_needed': [] if cfg.get('dashscope_text_key') else ['DashScope Key'],
                },
            ],
        }
    })


# =============================================
# 统一内容生成
# =============================================

CONTENT_TYPES = {
    'wechat': {
        'label': _('公众号文章'),
        'types': [{'id': 'article', 'name': _('文章')}, {'id': 'announcement', 'name': _('通知')}, {'id': 'promotion', 'name': _('推广')}],
    },
    'weibo': {
        'label': _('微博'),
        'types': [{'id': 'weibo', 'name': _('微博')}],
    },
}


@social_bp.route('/content-types', methods=['GET'])
def get_content_types():
    """Return available content types per platform."""
    admin, err = _require_admin()
    if err:
        return err
    platform = request.args.get('platform', 'wechat')
    info = CONTENT_TYPES.get(platform, CONTENT_TYPES['wechat'])
    return jsonify({'success': True, 'data': info})


@social_bp.route('/generate', methods=['POST'])
def generate_content():
    """Generate article content using AI."""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    topic = data.get('topic', '').strip()
    content_type = data.get('content_type', 'article')
    temperature = data.get('temperature', 0.7)

    if not topic:
        return jsonify({'success': False, 'error': _('请输入主题')}), 400

    try:
        from services.ai_content_generator import generate_article
        result = generate_article(topic, content_type, temperature)
        _log(admin['user_id'], 'social_generate', 'social', '', f'Type: {content_type}, Topic: {topic}')
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.exception('AI generate failed')
        return jsonify({'success': False, 'error': _('生成失败: {error}').format(error=str(e))}), 500


# =============================================
# 配图生成
# =============================================

@social_bp.route('/generate-image', methods=['POST'])
def generate_image():
    """Generate an image using 通义万相."""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    prompt = data.get('prompt', '').strip()
    title = data.get('title', '').strip()
    use_for_cover = data.get('cover', True)

    if not prompt and not title:
        return jsonify({'success': False, 'error': _('请输入图片描述或文章标题')}), 400

    try:
        from services.ai_content_generator import generate_image as gen_img
        from services.ai_content_generator import generate_cover_image

        if use_for_cover and title:
            oss_url = generate_cover_image(title, prompt or title)
        else:
            oss_url = gen_img(prompt or _('配图：{title}').format(title=title))

        # 下载到本地，不暴露外部 OSS URL
        import uuid, urllib.request
        SAVE_DIR = os.path.join(_auth_dir, '..', 'admin', 'static', 'uploads', 'temp')
        os.makedirs(SAVE_DIR, exist_ok=True)
        img_data = urllib.request.urlopen(oss_url, timeout=30).read()
        ext = '.png'
        if 'jpg' in oss_url or 'jpeg' in oss_url:
            ext = '.jpg'
        elif 'webp' in oss_url:
            ext = '.webp'
        filename = f'{uuid.uuid4().hex}{ext}'
        with open(os.path.join(SAVE_DIR, filename), 'wb') as f:
            f.write(img_data)
        local_url = f'/static/uploads/temp/{filename}'

        _log(admin['user_id'], 'social_gen_image', 'social', '', f'Prompt: {prompt or title}')
        return jsonify({'success': True, 'data': {'image_url': local_url}})
    except Exception as e:
        logger.exception('Image generation failed')
        return jsonify({'success': False, 'error': _('生成图片失败: {error}').format(error=str(e))}), 500


# =============================================
# 发布到多平台
# =============================================

@social_bp.route('/publish', methods=['POST'])
def publish_content():
    """Publish content to one or more platforms."""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    title = data.get('title', '').strip()
    body = data.get('body', '').strip()
    body_html = data.get('body_html', '').strip() or body
    summary = data.get('summary', '').strip()
    author = data.get('author', 'admin')
    cover_image_url = data.get('cover_image_url', '').strip()
    platforms = data.get('platforms', ['wechat'])  # list of platform ids
    auto_publish = data.get('auto_publish', False)

    if not title or not body:
        return jsonify({'success': False, 'error': _('标题和正文不能为空')}), 400

    admin_id = admin['user_id']
    results = []

    for platform in platforms:
        result = _publish_to_platform(
            platform=platform,
            title=title,
            body=body,
            body_html=body_html,
            summary=summary,
            author=author,
            cover_image_url=cover_image_url,
            auto_publish=auto_publish,
            admin_id=admin_id,
        )
        results.append(result)

    return jsonify({'success': True, 'data': {'results': results}})


def _publish_to_platform(platform, title, body, body_html, summary, author,
                         cover_image_url, auto_publish, admin_id):
    """Publish to a single platform. Returns {platform, status, media_id, message, error}."""
    if platform == 'wechat':
        return _publish_wechat(title, body_html, summary, author, cover_image_url, auto_publish, admin_id)
    elif platform == 'weibo':
        return _publish_weibo(title, body, cover_image_url, admin_id)
    elif platform == 'toutiao':
        return _publish_toutiao(title, body_html, summary, cover_image_url, admin_id)
    else:
        return {'platform': platform, 'status': 'failed', 'error': _('不支持的平台: {platform}').format(platform=platform)}


def _publish_wechat(title, body_html, summary, author, cover_image_url, auto_publish, admin_id):
    """Publish to WeChat Official Account."""
    try:
        from services.wechat_push_service import create_draft, submit_publish, upload_article_image
        thumb_media_id = ''
        publish_id = ''
        status = 'draft'

        if cover_image_url:
            thumb_media_id = upload_article_image(cover_image_url, is_url=True)

        media_id = create_draft(
            title=title, content_html=body_html, author=author,
            digest=summary or title[:100], thumb_media_id=thumb_media_id or '',
        )

        if auto_publish:
            publish_id = submit_publish(media_id)
            status = 'publishing'

        with get_sp_db() as conn:
            conn.execute(
                """INSERT INTO social_push_logs
                   (platform, content_type, title, summary, article_json, media_id, publish_id, status, admin_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ('wechat', 'article', title, summary,
                 json.dumps({'body_html': body_html, 'cover_url': cover_image_url}, ensure_ascii=False),
                 media_id, publish_id or '', status, admin_id)
            )
            conn.commit()

        _log(admin_id, 'social_publish', 'social', media_id, f'WeChat: {title}')
        return {
            'platform': 'wechat',
            'status': status,
            'media_id': media_id,
            'publish_id': publish_id,
            'message': _('微信草稿已创建') if not auto_publish else _('微信发布任务已提交'),
        }
    except Exception as e:
        logger.exception('WeChat publish failed')
        with get_sp_db() as conn:
            conn.execute(
                """INSERT INTO social_push_logs
                   (platform, content_type, title, article_json, status, admin_id, error_msg)
                   VALUES (?, ?, ?, ?, 'failed', ?, ?)""",
                ('wechat', 'article', title,
                 json.dumps({'body': body_html[:200]}, ensure_ascii=False), admin_id, str(e))
            )
            conn.commit()
        return {'platform': 'wechat', 'status': 'failed', 'error': str(e)}


def _publish_weibo(title, body, cover_image_url, admin_id):
    """Publish to Weibo."""
    try:
        from services.weibo_service import publish_weibo
        text = f'{title}\n\n{body}'[:2000] if title else body[:2000]
        result = publish_weibo(text=text, image_url=cover_image_url or None)

        with get_sp_db() as conn:
            conn.execute(
                """INSERT INTO social_push_logs
                   (platform, content_type, title, summary, article_json, media_id, status, admin_id)
                   VALUES (?, ?, ?, ?, ?, ?, 'published', ?)""",
                ('weibo', 'post', title, body[:100],
                 json.dumps({'body': body, 'cover_url': cover_image_url}, ensure_ascii=False),
                 result.get('id', ''), admin_id)
            )
            conn.commit()

        _log(admin_id, 'social_publish', 'social', result.get('id', ''), f'Weibo: {title}')
        return {'platform': 'weibo', 'status': 'published', 'media_id': result.get('id', ''), 'message': _('微博已发布')}
    except Exception as e:
        logger.exception('Weibo publish failed')
        with get_sp_db() as conn:
            conn.execute(
                """INSERT INTO social_push_logs
                   (platform, content_type, title, article_json, status, admin_id, error_msg)
                   VALUES (?, ?, ?, ?, 'failed', ?, ?)""",
                ('weibo', 'post', title,
                 json.dumps({'body': body[:200]}, ensure_ascii=False), admin_id, str(e))
            )
            conn.commit()
        return {'platform': 'weibo', 'status': 'failed', 'error': str(e)}


def _publish_toutiao(title, body_html, summary, cover_image_url, admin_id):
    """Publish to 今日头条."""
    try:
        from services.toutiao_service import publish_article
        result = publish_article(
            title=title,
            content_html=body_html,
            cover_url=cover_image_url or '',
            summary=summary or title[:200],
        )
        with get_sp_db() as conn:
            conn.execute(
                """INSERT INTO social_push_logs
                   (platform, content_type, title, summary, article_json, media_id, status, admin_id)
                   VALUES (?, ?, ?, ?, ?, ?, 'published', ?)""",
                ('toutiao', 'article', title, summary[:100],
                 json.dumps({'body': body_html[:500], 'cover_url': cover_image_url}, ensure_ascii=False),
                 result.get('id', ''), admin_id)
            )
            conn.commit()
        _log(admin_id, 'social_publish', 'social', result.get('id', ''), f'Toutiao: {title}')
        return {'platform': 'toutiao', 'status': 'published', 'media_id': result.get('id', ''), 'message': _('头条已发布')}
    except Exception as e:
        logger.exception('Toutiao publish failed')
        with get_sp_db() as conn:
            conn.execute(
                """INSERT INTO social_push_logs
                   (platform, content_type, title, article_json, status, admin_id, error_msg)
                   VALUES (?, ?, ?, ?, 'failed', ?, ?)""",
                ('toutiao', 'article', title,
                 json.dumps({'body': body_html[:200]}, ensure_ascii=False), admin_id, str(e))
            )
            conn.commit()
        return {'platform': 'toutiao', 'status': 'failed', 'error': str(e)}


# =============================================
# 发布状态查询
# =============================================

@social_bp.route('/publish-status/<publish_id>', methods=['GET'])
def check_publish_status(publish_id):
    """Check WeChat publish status."""
    admin, err = _require_admin()
    if err:
        return err
    try:
        from services.wechat_push_service import get_publish_status
        result = get_publish_status(publish_id)
        status = result.get('publish_status', 'unknown')
        with get_sp_db() as conn:
            conn.execute(
                "UPDATE social_push_logs SET status=?, error_msg=? WHERE publish_id=?",
                (status, result.get('errmsg', ''), publish_id)
            )
            conn.commit()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================
# 发布历史
# =============================================

@social_bp.route('/history', methods=['GET'])
def push_history():
    """Get social push history."""
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    platform = request.args.get('platform', '')
    offset = (page - 1) * limit

    where = ''
    params = []
    if platform:
        where = 'WHERE platform=?'
        params.append(platform)

    with get_sp_db() as conn:
        total = conn.execute(f'SELECT COUNT(*) as c FROM social_push_logs {where}', params).fetchone()
        rows = conn.execute(
            f"""SELECT id, platform, content_type, title, summary, media_id, publish_id,
                       status, push_time, error_msg, created_at, admin_id
               FROM social_push_logs {where}
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            params + [limit, offset]
        ).fetchall()

    return jsonify({
        'success': True,
        'data': {
            'total': total['c'],
            'page': page,
            'limit': limit,
            'items': [dict(r) for r in rows],
        }
    })


# =============================================
# CMS文章导入
# =============================================

@social_bp.route('/import-from-cms', methods=['GET'])
def import_cms_articles():
    """List published CMS articles for import into social push editor."""
    admin, err = _require_admin()
    if err:
        return err
    with _get_main_db() as conn:
        rows = conn.execute(
            "SELECT id, slug, category, title, excerpt, content, cover_image, author, "
            "is_published, published_at, created_at "
            "FROM cms_posts WHERE is_published=1 "
            "ORDER BY published_at DESC LIMIT 50"
        ).fetchall()
    return jsonify({
        'success': True,
        'data': [dict(r) for r in rows]
    })


# =============================================
# 删除历史
# =============================================

@social_bp.route('/history/<int:log_id>', methods=['DELETE'])
def delete_history(log_id):
    """Delete a push history entry."""
    admin, err = _require_admin()
    if err:
        return err
    with get_sp_db() as conn:
        conn.execute('DELETE FROM social_push_logs WHERE id=?', (log_id,))
        conn.commit()
    _log(admin['user_id'], 'social_delete', 'social', str(log_id))
    return jsonify({'success': True})
