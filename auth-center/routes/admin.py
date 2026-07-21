




# ═══════════════════════════════════════════════════════════
#  本地媒体库 API — 上传 / 列表 / 下载 / 删除 / 推送
# ═══════════════════════════════════════════════════════════

MEDIA_LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', '..', 'admin', 'static', 'media')

def _media_lib_ensure_dir():
    os.makedirs(MEDIA_LIB_DIR, exist_ok=True)
    os.makedirs(os.path.join(MEDIA_LIB_DIR, 'thumbs'), exist_ok=True)

@admin_bp.route('/media-library/upload', methods=['POST'])
def media_library_upload():
    admin, err = _require_admin()
    if err:
        return err
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': _('No file selected')}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'success': False, 'error': _('File name is empty')}), 400
    _media_lib_ensure_dir()
    import uuid as _uuid
    safe_name = _uuid.uuid4().hex + os.path.splitext(f.filename)[1].lower()
    save_path = os.path.join(MEDIA_LIB_DIR, safe_name)
    f.save(save_path)
    file_size = os.path.getsize(save_path)
    mime = f.content_type or 'application/octet-stream'
    # 兜底：浏览器可能不传正确 content_type，按扩展名补
    if mime == 'application/octet-stream' or not mime:
        ext = os.path.splitext(f.filename)[1].lower()
        ext_map = {'.mp4':'video/mp4','.mov':'video/quicktime','.avi':'video/x-msvideo',
                   '.webm':'video/webm','.mkv':'video/x-matroska','.flv':'video/x-flv','.m4v':'video/mp4',
                   '.mp3':'audio/mpeg','.wav':'audio/wav','.ogg':'audio/ogg','.flac':'audio/flac',
                   '.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.gif':'image/gif','.webp':'image/webp'}
        mime = ext_map.get(ext, mime)
    # 缩略图：视频缩略图由本地 FFmpeg 预生成后一并上传，服务器仅存储分发
    # 图片本身就是缩略图，不设 thumb_path，前端用 file_path 显示
    thumb_name = ''

    with get_db() as conn:
        new_id = conn.execute(
            "INSERT INTO media_files (filename, original_name, mime_type, file_size, file_path, thumb_path) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (safe_name, f.filename, mime, file_size, 'media/' + safe_name,
             'media/thumbs/' + thumb_name if thumb_name else '')
        ).fetchone()['id']
        conn.commit()
    return jsonify({
        'success': True,
        'data': {
            'id': new_id, 'filename': safe_name, 'original_name': f.filename,
            'mime_type': mime, 'file_size': file_size,
            'thumb_path': 'media/thumbs/' + thumb_name if thumb_name else ''
        }
    })

@admin_bp.route('/media-library/list', methods=['GET'])
def media_library_list():
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    if limit > 500: limit = 500
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM media_files").fetchone()['c']
        rows = conn.execute(
            "SELECT id, filename, original_name, mime_type, file_size, file_path, thumb_path, push_status, created_at FROM media_files ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        ).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows], 'total': total, 'page': page, 'limit': limit})

@admin_bp.route('/media-library/<int:fid>', methods=['DELETE'])
def media_library_delete(fid):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute("SELECT * FROM media_files WHERE id=%s", (fid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('File does not exist')}), 404
        fp = os.path.join(MEDIA_LIB_DIR, row['filename'])
        if os.path.exists(fp):
            os.remove(fp)
        if row['thumb_path']:
            tp = os.path.join(MEDIA_LIB_DIR, '..', row['thumb_path'])
            if os.path.exists(tp):
                os.remove(tp)
        conn.execute("DELETE FROM media_files WHERE id=%s", (fid,))
        conn.commit()
    return jsonify({'success': True})

@admin_bp.route('/media-library/<int:fid>/download', methods=['GET'])
def media_library_download(fid):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute("SELECT * FROM media_files WHERE id=%s", (fid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('File does not exist')}), 404
    fp = os.path.join(MEDIA_LIB_DIR, row['filename'])
    if not os.path.exists(fp):
        return jsonify({'success': False, 'error': _('File deleted')}), 404
    return _send_file_or_stream(fp, row['original_name'], row['mime_type'])

@admin_bp.route('/media-library/<int:fid>/push', methods=['POST'])
def media_library_push(fid):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    target = data.get('target', 'feishu')
    with get_db() as conn:
        row = conn.execute("SELECT * FROM media_files WHERE id=%s", (fid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('File does not exist')}), 404

    file_url = deploy.url("agent") + "/static/" + row["file_path"]
    filename = row['original_name']
    mime = row['mime_type']

    result = {'success': True, 'target': target}
    if target in ('feishu', 'wecom'):
        try:
            im = None
            import flask as _flask
            pm = _flask.current_app.extensions.get('plugin_manager') if hasattr(_flask.current_app, 'extensions') else None
            if pm and pm.is_enabled('im_gateway'):
                im = pm.get_instance('im_gateway')
            if im is None:
                result = {'success': False, 'error': _('IM Gateway plugin is not enabled, cannot push')}
            else:
                im.push_media(target, file_url, filename, mime)
        except Exception as e:
            result = {'success': False, 'error': f'{target} Push Failed: ' + str(e)}

    if result['success']:
        with get_db() as conn:
            conn.execute(
                "UPDATE media_files SET push_status='done', push_target=%s, "
                "pushed_at=NOW(), updated_at=NOW() WHERE id=%s",
                (target, fid)
            )
            conn.commit()
    return jsonify(result)


# NOTE: 媒体推送函数（_push_media_to_feishu / _push_media_to_wecom / _upload_feishu_*
#        / _fetch_as_base64）已迁移至 plugins/im_gateway/adapters/，
#        由 media_library_push 通过插件实例 im.push_media() 调用。


def _send_file_or_stream(fp, filename, mime):
    from flask import Response, request as _req
    range_header = _req.headers.get('Range', None)
    size = os.path.getsize(fp)
    if range_header:
        import re
        byte_range = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if byte_range:
            start = int(byte_range.group(1))
            end = int(byte_range.group(2)) if byte_range.group(2) else size - 1
            length = end - start + 1
            with open(fp, 'rb') as f:
                f.seek(start)
                data = f.read(length)
            return Response(data, 206, {
                'Content-Type': mime,
                'Content-Range': 'bytes {}-{}/{}'.format(start, end, size),
                'Content-Length': str(length),
                'Accept-Ranges': 'bytes',
                'Content-Disposition': 'inline; filename="{}"'.format(filename)
            })
    from flask import send_file as _sf
    return _sf(fp, mimetype=mime, as_attachment=False,
               download_name=filename, conditional=True)


# =============================================
# OAuth 提供商配置（多租户抖音登录）
# =============================================

# ════════════════════════════════════════════════════════════════
# OAuth 登录配置管理已迁移至 plugins/oauth_config/（Phase 4A 逻辑解耦）
#   - REST 路由：plugins/oauth_config/routes.py（/admin/oauth/configs）
#   - oauth_providers 表仍留主库，供登录回调链路（auth.py / *_service）共享读取
#   - 登录回调链路（auth.py oauth_login/callback、oauth_service）保持不变
# ════════════════════════════════════════════════════════════════


def _get_media_agent_id():
    """获取 Media Agent 的 ID（带缓存）"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM agent_matrix WHERE name='Media Agent' AND role_type='sub' AND is_active=1"
        ).fetchone()
    if row:
        return row['id']
    # fallback: 找 domain='media' 的活跃 agent
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM agent_matrix WHERE domain='media' AND is_active=1 LIMIT 1"
        ).fetchone()
    return row['id'] if row else 0


# =============================================
# API Quota Management
# =============================================
@admin_bp.route('/quota/stats', methods=['GET'])
def quota_stats():
    """API配额概览统计数据"""
    admin, err = _require_admin()
    if err:
        return err
    from models import TIERS
    with get_db() as conn:
        total_keys = conn.execute('SELECT COUNT(*) as c FROM api_keys').fetchone()['c']
        active_keys = conn.execute('SELECT COUNT(*) as c FROM api_keys WHERE active=1').fetchone()['c']
        today_calls = conn.execute("SELECT COALESCE(SUM(calls_today),0) as c FROM api_keys WHERE last_reset=CURRENT_DATE").fetchone()['c']
        total_calls = conn.execute('SELECT COALESCE(SUM(calls_total),0) as c FROM api_keys').fetchone()['c']
        user_tiers = conn.execute(
            "SELECT a.tier, COUNT(DISTINCT a.user_id) as count FROM app_authorizations a WHERE a.active=1 GROUP BY a.tier"
        ).fetchall()
    tier_breakdown = {}
    for t in ['free', 'standard', 'pro']:
        tier_breakdown[t] = {'name': TIERS.get(t, {}).get('name', t), 'daily_limit': TIERS.get(t, {}).get('daily_limit', 0), 'count': 0}
    for r in user_tiers:
        if r['tier'] in tier_breakdown:
            tier_breakdown[r['tier']]['count'] = r['count']
    return jsonify({'success': True, 'data': {
        'total_keys': total_keys, 'active_keys': active_keys,
        'today_calls': today_calls, 'total_calls': total_calls,
        'tier_breakdown': tier_breakdown
    }})


@admin_bp.route('/quota/users', methods=['GET'])
def quota_users():
    """查询所有用户的配额信息"""
    admin, err = _require_admin()
    if err:
        return err
    from models import TIERS
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    search = request.args.get('search', '').strip()

    with get_db() as conn:
        where = ''
        params = []
        if search:
            where = "WHERE (u.username LIKE %s OR u.display_name LIKE %s)"
            params = [f'%{search}%', f'%{search}%']
        total = conn.execute(f'SELECT COUNT(*) as c FROM users u {where}', params).fetchone()['c']
        rows = conn.execute(f"""
            SELECT u.id, u.username, u.display_name, u.created_at,
                   COALESCE(a.tier, 'free') as tier,
                   COALESCE(a.calls_today, 0) as calls_today,
                   COALESCE(a.calls_total, 0) as calls_total,
                   (SELECT COUNT(*) FROM api_keys k WHERE k.user_id=u.id AND k.active=1) as active_keys
            FROM users u
            LEFT JOIN app_authorizations a ON u.id=a.user_id AND a.active=1
            {where}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset]).fetchall()
        users = [dict(r) for r in rows]
        for u in users:
            tier_info = TIERS.get(u['tier'], TIERS['free'])
            u['daily_limit'] = tier_info['daily_limit']
            u['tier_name'] = tier_info['name']
    return jsonify({'success': True, 'data': {
        'total': total, 'page': page, 'limit': limit, 'users': users
    }})


@admin_bp.route('/quota/users/<int:uid>/tier', methods=['POST'])
def quota_set_user_tier(uid):
    """设置用户的API配额等级"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    tier = data.get('tier', '').strip()
    from models import TIERS
    if tier not in TIERS:
        return jsonify({'success': False, 'error': f'Invalid tier: {tier}'}), 400
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM app_authorizations WHERE user_id=%s AND active=1", (uid,)
        ).fetchone()
        if existing:
            conn.execute("UPDATE app_authorizations SET tier=%s, last_reset=CURRENT_DATE WHERE id=%s", (tier, existing['id']))
        else:
            conn.execute(
                "INSERT INTO app_authorizations (user_id, app_name, tier, active) VALUES (%s, 'platform', %s, 1)",
                (uid, tier)
            )
        conn.commit()
    _log(admin['user_id'], 'set_user_tier', 'user', str(uid), f'tier→{tier}')
    return jsonify({'success': True, 'message': f'User level updated to {TIERS[tier]["name"]}'})


@admin_bp.route('/quota/keys', methods=['GET'])
def quota_keys():
    """查询所有API Key的配额使用情况"""
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    with get_db() as conn:
        total = conn.execute('SELECT COUNT(*) as c FROM api_keys').fetchone()['c']
        rows = conn.execute("""
            SELECT k.id, k.name, k.key_prefix, k.calls_today, k.calls_total,
                   k.last_reset, k.last_used, k.active, k.created_at,
                   COALESCE(u.display_name, u.username, '') as user_name, u.id as user_id,
                   COALESCE(a.tier, 'free') as tier
            FROM api_keys k
            LEFT JOIN users u ON k.user_id=u.id
            LEFT JOIN app_authorizations a ON u.id=a.user_id AND a.active=1
            ORDER BY k.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset)).fetchall()
    return jsonify({'success': True, 'data': {
        'total': total, 'page': page, 'limit': limit, 'keys': [dict(r) for r in rows]
    }})


@admin_bp.route('/quota/keys/<int:kid>/reset', methods=['POST'])
def quota_reset_key(kid):
    """重置单个API Key的日调用量"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute("UPDATE api_keys SET calls_today=0, last_reset=CURRENT_DATE WHERE id=%s", (kid,))
        conn.commit()
    _log(admin['user_id'], 'reset_key_quota', 'api_key', str(kid))
    return jsonify({'success': True, 'message': _('Daily call count for the key has been reset')})


@admin_bp.route('/quota/overview', methods=['GET'])
def quota_overview():
    """详细配额使用报表（最近7天趋势）"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        # 每日总调用量最近7天
        daily = conn.execute("""
            SELECT last_reset as date, SUM(calls_today) as calls_count
            FROM api_keys WHERE last_reset >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY last_reset ORDER BY last_reset
        """).fetchall()
        daily_stats = [dict(r) for r in daily]
        # 超出阈值（calls_today >= tier daily_limit * 0.8）的key
        from models import TIERS
        near_limit = conn.execute("""
            SELECT k.id, k.name, k.key_prefix, k.calls_today,
                   COALESCE(u.display_name, u.username, '') as user_name
            FROM api_keys k
            LEFT JOIN users u ON k.user_id=u.id
            LEFT JOIN app_authorizations a ON u.id=a.user_id AND a.active=1
            WHERE k.active=1
        """).fetchall()
        near_limit_list = []
        for r in near_limit:
            tier_key = 'free'
            with get_db() as conn2:
                tr = conn2.execute(
                    "SELECT tier FROM app_authorizations WHERE user_id=%s AND active=1",
                    (r['user_id'],)
                ).fetchone()
                if tr:
                    tier_key = tr['tier']
            limit_val = TIERS.get(tier_key, TIERS['free'])['daily_limit']
            if limit_val > 0 and r['calls_today'] >= limit_val * 0.8:
                nr = dict(r)
                nr['daily_limit'] = limit_val
                nr['usage_pct'] = round(r['calls_today'] / limit_val * 100, 1)
                near_limit_list.append(nr)
    return jsonify({'success': True, 'data': {
        'daily_stats': daily_stats,
        'near_limit_keys': near_limit_list
    }})


# ── 客户管理 (Customer Management) ──

@admin_bp.route('/customers', methods=['GET'])
def customer_list():
    """客户列表 — 统一查看个人/企业认证状态"""
    admin, err = _require_admin()
    if err:
        return err
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    search = request.args.get("search", "").strip()
    cust_type = request.args.get("type", "").strip()       # enterprise / individual / ''
    verify_status = request.args.get("verify", "").strip() # verified / unverified / ''
    offset = (page - 1) * limit

    where = []
    params = []

    if search:
        where.append("(u.phone LIKE %s OR COALESCE(u.display_name, u.username) LIKE %s OR u.enterprise_name LIKE %s)")
        s = '%' + search + '%'
        params.extend([s, s, s])

    if cust_type == 'enterprise':
        where.append("u.enterprise_verified = 1")
    elif cust_type == 'individual':
        where.append("u.enterprise_verified = 0")

    if verify_status == 'verified':
        where.append("(u.enterprise_verified = 1 OR u.is_real_name_verified = 1)")
    elif verify_status == 'unverified':
        where.append("u.enterprise_verified = 0 AND u.is_real_name_verified = 0")

    wsql = 'WHERE ' + ' AND '.join(where) if where else ''

    from_sql = ("FROM users u")
    sql = ("SELECT u.id, u.phone, COALESCE(u.display_name, u.username) as nickname, u.email, "
           "u.created_at, u.last_login, u.active, "
           "u.is_real_name_verified, u.real_name_verified_at, u.verified_by, "
           "u.enterprise_name, u.enterprise_tax_id, u.enterprise_verified, u.enterprise_verified_at, "
           "'' as plan_key, NULL as sub_expires "
           + from_sql + ' ' + wsql + ' ORDER BY u.created_at DESC LIMIT %s OFFSET %s')
    csql = 'SELECT COUNT(DISTINCT u.id) as c ' + from_sql + ' ' + wsql

    with get_db() as conn:
        total = conn.execute(csql, params).fetchone()['c']
        rows = conn.execute(sql, params + [limit, offset]).fetchall()

    customers = []
    for r in rows:
        c = dict(r)
        if c.get('enterprise_verified'):
            c['cert_status'] = 'enterprise'
            c['cert_badge'] = _('Enterprise Verified')
        elif c.get('is_real_name_verified'):
            c['cert_status'] = 'individual'
            c['cert_badge'] = _('Individual Verified')
        else:
            c['cert_status'] = 'none'
            c['cert_badge'] = _('Unverified')
        customers.append(c)

    return jsonify({"success": True, "data": {
        "total": total, "page": page, "limit": limit,
        "customers": customers,
    }})





# ════════════════════════════════════════════════════════════════
# i18n 翻译管理
# ════════════════════════════════════════════════════════════════

@admin_bp.route('/i18n/translations', methods=['GET'])
def admin_i18n_list():
    """列出翻译（分页+搜索）"""
    admin, err = _require_admin()
    if err:
        return err

    locale = request.args.get('locale', 'en')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    offset = (page - 1) * limit

    from i18n import list_translations
    data = list_translations(locale=locale, search=search, offset=offset, limit=limit)
    return jsonify({'success': True, 'data': data})


@admin_bp.route('/i18n/translations', methods=['POST'])
def admin_i18n_create():
    """新增一条翻译"""
    admin, err = _require_admin()
    if err:
        return err

    data = request.get_json(force=True) or {}
    locale = data.get('locale', 'en')
    source = (data.get('source') or '').strip()
    translation = (data.get('translation') or '').strip()

    if not source:
        return jsonify({'success': False, 'error': _(_('Original text cannot be empty'))}), 400

    from i18n import set_translation
    ok = set_translation(locale, source, translation, is_auto=0)
    return jsonify({'success': ok, 'error': '' if ok else _(_('Write failed'))}),
    201 if ok else 400,


@admin_bp.route('/i18n/translations/<int:tid>', methods=['PUT'])
def admin_i18n_update(tid):
    """编辑一条翻译"""
    admin, err = _require_admin()
    if err:
        return err

    data = request.get_json(force=True) or {}
    translation = (data.get('translation') or '').strip()
    is_auto = data.get('is_auto', 0)

    with get_db() as conn:
        exist = conn.execute('SELECT id FROM i18n_strings WHERE id=%s', (tid,)).fetchone()
        if not exist:
            return jsonify({'success': False, 'error': _(_('Translation does not exist'))}), 404
        conn.execute(
            "UPDATE i18n_strings SET translation=%s, is_auto=%s, updated_at=NOW() WHERE id=%s",
            (translation, is_auto, tid)
        )
        conn.commit()

    return jsonify({'success': True, 'message': _('Updated')})


@admin_bp.route('/i18n/translations/<int:tid>', methods=['DELETE'])
def admin_i18n_delete(tid):
    """删除一条翻译"""
    admin, err = _require_admin()
    if err:
        return err

    from i18n import delete_translation
    ok = delete_translation(tid)
    return jsonify({'success': ok, 'error': '' if ok else _('Delete failed')})


@admin_bp.route('/i18n/seed', methods=['POST'])
def admin_i18n_seed():
    """从 YAML 同步翻译到 DB"""
    admin, err = _require_admin()
    if err:
        return err

    locale = request.args.get('locale', 'en')
    from i18n import seed_from_yaml
    count = seed_from_yaml(locale)
    return jsonify({'success': True, 'message': f'Synchronized {count} records to DB'})


# ═══════════════════════════════════════════════════════
# Provider API Key 管理（LLM 供应商 Key 统一管理）
# 与 /admin/api-keys（用户 API Key）不同，此路由组管理 LLM 供应商的 API Key
# ═══════════════════════════════════════════════════════

@admin_bp.route('/provider-api-keys', methods=['GET'])
def provider_api_key_list():
    """列出所有 Provider API Key（key_value_enc 脱敏）"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, provider, description, is_active, "
            "CASE WHEN key_value_enc != '' THEN 1 ELSE 0 END AS has_value, "
            "created_at, updated_at "
            "FROM provider_api_keys ORDER BY id"
        ).fetchall()
        return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@admin_bp.route('/provider-api-keys', methods=['POST'])
def provider_api_key_create():
    """新增 Provider API Key（value 加密存储）"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    name = (data.get('name') or '').strip()
    key_value = (data.get('key_value') or '').strip()
    provider = (data.get('provider') or '').strip()
    if not name or not key_value:
        return jsonify({'success': False, 'error': _('Name and Key cannot be empty')}), 400

    from services.crypto import encrypt
    encrypted = encrypt(key_value)

    with get_db() as conn:
        row = conn.execute(
            'INSERT INTO provider_api_keys (name, key_value_enc, provider, description) '
            'VALUES (%s,%s,%s,%s) RETURNING id',
            (name, encrypted, provider, data.get('description', ''))
        ).fetchone()
        conn.commit()
        kid = row['id']
    _log(admin['user_id'], 'create_provider_key', 'provider_api_key', str(kid), name)
    return jsonify({'success': True, 'data': {'id': kid}})


@admin_bp.route('/provider-api-keys/<int:kid>', methods=['PUT'])
def provider_api_key_update(kid):
    """更新 Provider API Key（value 可选更新）"""
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    with get_db() as conn:
        row = conn.execute('SELECT * FROM provider_api_keys WHERE id=%s', (kid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('Not found')}), 404

        updates = []
        params = []
        for field in ['name', 'provider', 'description']:
            if field in data and data[field] is not None:
                updates.append(f'{field}=%s')
                params.append(data[field].strip() if isinstance(data[field], str) else data[field])
        if 'is_active' in data:
            updates.append('is_active=%s')
            params.append(1 if data['is_active'] else 0)
        if data.get('key_value', '').strip():
            from services.crypto import encrypt
            updates.append('key_value_enc=%s')
            params.append(encrypt(data['key_value'].strip()))
        if not updates:
            return jsonify({'success': True, 'message': _('No changes')})

        updates.append('updated_at=NOW()')
        params.append(kid)
        conn.execute(
            f"UPDATE provider_api_keys SET {','.join(updates)} WHERE id=%s",
            params
        )
        conn.commit()
    _log(admin['user_id'], 'update_provider_key', 'provider_api_key', str(kid))
    return jsonify({'success': True})


@admin_bp.route('/provider-api-keys/<int:kid>', methods=['DELETE'])
def provider_api_key_delete(kid):
    """删除 Provider API Key（检查引用）"""
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        # 检查是否被 provider_models 引用
        refs = conn.execute(
            'SELECT COUNT(*) as cnt FROM provider_models WHERE api_key_id=%s', (kid,)
        ).fetchone()
        if refs['cnt'] > 0:
            return jsonify({
                'success': False,
                'error': _('Key is referenced by %(count)s model(s), please unlink first', count=refs['cnt'])
            }), 400

        row = conn.execute('SELECT name FROM provider_api_keys WHERE id=%s', (kid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('Not found')}), 404
        conn.execute('DELETE FROM provider_api_keys WHERE id=%s', (kid,))
        conn.commit()
    _log(admin['user_id'], 'delete_provider_key', 'provider_api_key', str(kid), row['name'])
    return jsonify({'success': True})


# ═══════════════════════════════════════════════════════
# LLM Quota 管理（按用户/模型/模块的精细化配额）
# ═══════════════════════════════════════════════════════

@admin_bp.route('/llm-quotas', methods=['GET'])
def llm_quota_list():
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM llm_quotas ORDER BY target_type, target_id'
        ).fetchall()
        return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@admin_bp.route('/llm-quotas', methods=['POST'])
def llm_quota_create():
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    target_type = data.get('target_type', 'module')
    if target_type not in ('user', 'model', 'module', 'global'):
        return jsonify({'success': False, 'error': _('Invalid target_type')}), 400
    with get_db() as conn:
        row = conn.execute(
            'INSERT INTO llm_quotas (target_type, target_id, daily_limit, rate_limit, rate_window_sec) '
            'VALUES (%s,%s,%s,%s,%s) RETURNING id',
            (target_type, data.get('target_id'), data.get('daily_limit', 0),
             data.get('rate_limit', 0), data.get('rate_window_sec', 60))
        ).fetchone()
        conn.commit()
    _log(admin['user_id'], 'create_llm_quota', 'llm_quota', str(row['id']))
    return jsonify({'success': True, 'data': {'id': row['id']}})


@admin_bp.route('/llm-quotas/<int:qid>', methods=['PUT'])
def llm_quota_update(qid):
    admin, err = _require_admin()
    if err:
        return err
    data = request.get_json(force=True) or {}
    with get_db() as conn:
        row = conn.execute('SELECT * FROM llm_quotas WHERE id=%s', (qid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': _('Not found')}), 404
        updates = []
        params = []
        for field in ['target_type', 'daily_limit', 'rate_limit', 'rate_window_sec', 'target_id', 'is_active']:
            if field in data:
                updates.append(f'{field}=%s')
                params.append(data[field])
        if not updates:
            return jsonify({'success': True, 'message': _('No changes')})
        updates.append('updated_at=NOW()')
        params.append(qid)
        conn.execute(f"UPDATE llm_quotas SET {','.join(updates)} WHERE id=%s", params)
        conn.commit()
    return jsonify({'success': True})


@admin_bp.route('/llm-quotas/<int:qid>', methods=['DELETE'])
def llm_quota_delete(qid):
    admin, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        conn.execute('DELETE FROM llm_quotas WHERE id=%s', (qid,))
        conn.commit()
    _log(admin['user_id'], 'delete_llm_quota', 'llm_quota', str(qid))
    return jsonify({'success': True})
