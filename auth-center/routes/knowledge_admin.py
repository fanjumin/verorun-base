#!/usr/bin/env python3
"""Knowledge Base Admin — 知识库管理后台路由

管理端 6 个端点，操作 knowledge_blocks 表（主库 PostgreSQL）。

依赖: 复用 auth-center 的 JWT 鉴权，目标表为主库 knowledge_blocks。
"""
from i18n import _
import sys, os, json, logging, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Blueprint, jsonify, request
from models import get_db

logger = logging.getLogger(__name__)

knowledge_bp = Blueprint('knowledge_admin', __name__, url_prefix='/admin/knowledge')


def _require_admin():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        return None, (jsonify({'success': False, 'error': _('Please login first')}), 401)
    from services.jwt_service import validate_token
    payload = validate_token(token)
    if not payload:
        return None, (jsonify({'success': False, 'error': _('Invalid Token')}), 401)
    if not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': _('Requires admin permissions')}), 403)
    return payload, None


def _success(data=None, message='ok'):
    return jsonify({'success': True, 'data': data, 'message': message})


def _error(message, code=400):
    return jsonify({'success': False, 'error': message}), code


# ── 1. 知识库统计 ──

@knowledge_bp.route('/stats', methods=['GET'])
def kb_stats():
    """知识库统计"""
    admin, err = _require_admin()
    if err: return err

    try:
        with get_db() as db:
            total = db.execute(
                "SELECT COUNT(*) as c FROM knowledge_blocks WHERE deleted_at IS NULL"
            ).fetchone()['c']
            by_category = db.execute(
                "SELECT category, COUNT(*) as cnt FROM knowledge_blocks WHERE deleted_at IS NULL GROUP BY category ORDER BY cnt DESC"
            ).fetchall()
            by_scope = db.execute(
                "SELECT scope, COUNT(*) as cnt FROM knowledge_blocks WHERE deleted_at IS NULL GROUP BY scope"
            ).fetchall()
            total_hits = db.execute(
                "SELECT COALESCE(SUM(hit_count), 0) as hits FROM knowledge_blocks WHERE deleted_at IS NULL"
            ).fetchone()['hits']

        return _success({
            'total_entries': total,
            'by_category': [dict(r) for r in by_category],
            'by_scope': [dict(r) for r in by_scope],
            'total_hits': total_hits,
        })
    except Exception as e:
        logger.exception('kb_stats failed')
        return _error(str(e), 500)


# ── 2. 知识条目列表（分页+搜索）──

@knowledge_bp.route('/entries', methods=['GET'])
def kb_list():
    """知识条目列表"""
    admin, err = _require_admin()
    if err: return err

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)
    keyword = request.args.get('keyword', '').strip()
    category = request.args.get('category', '').strip()
    scope = request.args.get('scope', '').strip()
    sort = request.args.get('sort', 'created_at')

    sort_col = 'created_at' if sort == 'created_at' else 'hit_count'
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    try:
        with get_db() as db:
            where = ["deleted_at IS NULL"]
            params = []

            if keyword:
                where.append("(title LIKE %s OR content LIKE %s OR keywords LIKE %s)")
                kw = f'%{keyword}%'
                params.extend([kw, kw, kw])
            if category:
                where.append("category=%s")
                params.append(category)
            if scope:
                where.append("scope=%s")
                params.append(scope)

            where_clause = ' AND '.join(where)

            count_sql = f"SELECT COUNT(*) as total FROM knowledge_blocks WHERE {where_clause}"
            total = db.execute(count_sql, params).fetchone()['total']

            offset = (page - 1) * page_size
            data_sql = f"SELECT * FROM knowledge_blocks WHERE {where_clause} ORDER BY {sort_col} DESC, priority DESC LIMIT %s OFFSET %s"
            rows = db.execute(data_sql, params + [page_size, offset]).fetchall()

            items = [dict(r) for r in rows]

        return _success({
            'items': items,
            'total': total,
            'page': page,
            'pageSize': page_size,
            'pages': max(1, (total + page_size - 1) // page_size),
        })
    except Exception as e:
        logger.exception('kb_list failed')
        return _error(str(e), 500)


# ── 3. 新增知识条目 ──

@knowledge_bp.route('/entries', methods=['POST'])
def kb_create():
    """新增知识条目"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True)
    if not data:
        return _error(_('Request body is required'))
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title or not content:
        return _error(_('Title and content are required'))

    kb_id = data.get('id', f'kb_admin_{uuid.uuid4().hex[:12]}')
    keywords = data.get('keywords', '')
    if isinstance(keywords, (list, tuple)):
        keywords = ','.join(keywords)
    category = data.get('category', 'general')
    priority = data.get('priority', 5)
    scope = data.get('scope', 'system')
    source = data.get('source', 'manual')

    try:
        with get_db() as db:
            db.execute(
                """INSERT INTO knowledge_blocks (id, title, content, keywords, category, priority, scope, source, owner_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET
                       title=excluded.title, content=excluded.content,
                       keywords=excluded.keywords, category=excluded.category,
                       priority=excluded.priority, scope=excluded.scope,
                       updated_at=NOW()""",
                (kb_id, title, content, keywords, category, priority, scope, source, admin.get('user_id'))
            )
            db.commit()
        return _success({'id': kb_id}, _('Knowledge entry saved'))
    except Exception as e:
        logger.exception('kb_create failed')
        return _error(str(e), 500)


# ── 4. 更新知识条目 ──

@knowledge_bp.route('/entries/<entry_id>', methods=['PUT'])
def kb_update(entry_id):
    """更新知识条目"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True) or {}
    if not data:
        return _error(_('Request body is required'))

    fields = []
    params = []
    for col in ('title', 'content', 'keywords', 'category', 'priority', 'scope'):
        if col in data:
            val = data[col]
            if col == 'keywords' and isinstance(val, (list, tuple)):
                val = ','.join(val)
            fields.append(f"{col}=%s")
            params.append(val)

    if not fields:
        return _error(_('No valid fields to update'))
    fields.append("updated_at=NOW()")
    params.append(entry_id)

    try:
        with get_db() as db:
            sql = f"UPDATE knowledge_blocks SET {', '.join(fields)} WHERE id=%s AND deleted_at IS NULL"
            db.execute(sql, params)
            db.commit()
        return _success(None, _('Updated'))
    except Exception as e:
        logger.exception('kb_update failed')
        return _error(str(e), 500)


# ── 5. 删除知识条目（软删除）──

@knowledge_bp.route('/entries/<entry_id>', methods=['DELETE'])
def kb_delete(entry_id):
    """删除知识条目（软删除）"""
    admin, err = _require_admin()
    if err: return err

    try:
        with get_db() as db:
            db.execute(
                "UPDATE knowledge_blocks SET deleted_at=NOW() WHERE id=%s AND deleted_at IS NULL",
                (entry_id,)
            )
            db.commit()
        return _success(None, _('Deleted'))
    except Exception as e:
        logger.exception('kb_delete failed')
        return _error(str(e), 500)


# ── 6. RAG 检索 ──

@knowledge_bp.route('/search', methods=['POST'])
def kb_search():
    """RAG 检索知识库"""
    admin, err = _require_admin()
    if err: return err

    data = request.get_json(force=True) or {}
    query = (data.get('query', '') or data.get('q', '')).strip()
    if not query:
        return _error(_('Query is required'))
    top_k = data.get('topK', 5)
    top_k = max(1, min(20, top_k))
    category = data.get('category', '').strip()

    try:
        with get_db() as conn:
            where = ["deleted_at IS NULL"]
            params = [f'%{query}%', f'%{query}%']
            if category:
                where.append("category=%s")
                params.append(category)
            where_clause = ' AND '.join(where)

            # Full-text + keyword scoring
            rows = conn.execute(
                f"SELECT * FROM knowledge_blocks WHERE {where_clause} AND "
                "(title LIKE %s OR content LIKE %s) ORDER BY priority DESC, hit_count DESC LIMIT %s",
                params + [top_k * 2]
            ).fetchall()

        scored = []
        q_lower = query.lower()
        for row in rows:
            score = 0.0
            title_lower = (row['title'] or '').lower()
            content_lower = (row['content'] or '')[:500].lower()

            if query.lower() in title_lower:
                score += 0.4
            if query.lower() in content_lower:
                score += 0.2

            keywords = (row['keywords'] or '').lower().split(',')
            kw_matches = sum(1 for kw in keywords if kw.strip() and kw.strip() in q_lower)
            if keywords and kw_matches:
                score += min(kw_matches / len(keywords), 1.0) * 0.3

            score += min(row['hit_count'] / 10, 0.1)

            if score > 0:
                scored.append((row, score))

        scored.sort(key=lambda x: -x[1])
        scored = scored[:top_k]

        # Update hit_count
        for row, _ in scored:
            try:
                with get_db() as upd:
                    upd.execute(
                        "UPDATE knowledge_blocks SET hit_count = hit_count + 1 WHERE id=%s",
                        (row['id'],)
                    )
                    upd.commit()
            except Exception:
                pass

        results = [{
            'id': row['id'],
            'title': row['title'],
            'content': row['content'][:300],
            'keywords': row['keywords'].split(',') if row['keywords'] else [],
            'category': row['category'],
            'score': round(score, 3),
        } for row, score in scored]

        return _success({'results': results, 'total': len(results)})
    except Exception as e:
        logger.exception('kb_search failed')
        return _error(str(e), 500)
