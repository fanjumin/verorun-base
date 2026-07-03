#!/usr/bin/env python3
"""API V1 Routes — 统一的API v1端点"""
import json
import os
import sys
import threading
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, stream_with_context
from models import get_db
from services.jwt_service import validate_token

# 创建蓝图
api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

def api_ok(data=None):
    return jsonify({'success': True, 'data': data})

def api_err(msg, code=400):
    return jsonify({'success': False, 'error': msg}), code

def get_current_user_id(token):
    """验证token并返回用户ID"""
    payload = validate_token(token)
    if not payload:
        return None
    return payload.get('user_id')

def require_auth():
    """认证装饰器辅助函数"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None, api_err('未提供有效的Token', 401)
    token = auth.replace('Bearer ', '')
    user_id = get_current_user_id(token)
    if not user_id:
        return None, api_err('无效或过期的Token', 401)
    return user_id, None

# =============================================
# RAG 知识库检索（统一函数）
# =============================================

def _rag_search(query: str, top_k: int = 5, category: str = None) -> list:
    """检索 knowledge_blocks，返回排序后的知识片段列表"""
    try:
        from models import get_db
        with get_db() as conn:
            chars = list(query.replace(' ', ''))
            bigrams = [query[i:i+2] for i in range(len(query)-1)]
            search_terms = set(chars + bigrams)

            sql = "SELECT * FROM knowledge_blocks"
            params = []
            if category:
                sql += " WHERE category=?"
                params.append(category)
            sql += " ORDER BY priority DESC"
            all_blocks = [dict(r) for r in conn.execute(sql, params).fetchall()]

        results = []
        for block in all_blocks:
            score = 0.0
            keywords = (block['keywords'] or '').split(',')
            content = block['content'] or ''
            title = block['title'] or ''

            kw_matches = sum(1 for kw in keywords if kw and kw in query)
            if kw_matches > 0:
                score += min(kw_matches / len(keywords), 1.0) * 0.6

            content_chars = set(content)
            title_chars = set(title)
            char_overlap = len(search_terms & content_chars) / max(len(search_terms), 1)
            title_overlap = len(search_terms & title_chars) / max(len(search_terms), 1)
            score += char_overlap * 0.25 + title_overlap * 0.15

            if query in content:
                score += 0.3
            if query in title:
                score += 0.2

            if score > 0:
                results.append({
                    'title': block['title'],
                    'content': block['content'],
                    'category': block['category'],
                    'score': round(score, 4),
                })

        results.sort(key=lambda x: -x['score'])
        return results[:min(top_k, 20)]
    except Exception as e:
        print(f'[RAG] Search error: {e}')
        return []

def _build_rag_context(knowledge: list) -> str:
    """将检索到的知识片段格式化为系统提示上下文"""
    if not knowledge:
        return ''
    ctx = '\n\n以下是与用户问题相关的内部知识库内容，请优先参考这些信息回答：\n'
    for i, k in enumerate(knowledge, 1):
        ctx += f'\n[{i}] {k["title"]}\n{k["content"]}\n'
    ctx += '\n请基于以上知识回答用户问题。如果知识库中没有相关信息，请如实告知用户。'
    return ctx

# ── 简易IP限流 ──
_rate_limit_store = {}
_RATE_LIMIT_CLEANUP_INTERVAL = 300  # 5分钟清理一次
_rate_limit_last_cleanup = time.time()

def _ensure_rate_limit():
    global _rate_limit_last_cleanup
    now = time.time()
    if now - _rate_limit_last_cleanup > _RATE_LIMIT_CLEANUP_INTERVAL:
        _rate_limit_last_cleanup = now
        cutoff = now - 60
        for k in list(_rate_limit_store.keys()):
            _rate_limit_store[k] = [t for t in _rate_limit_store[k] if t > cutoff]
            if not _rate_limit_store[k]:
                del _rate_limit_store[k]

def _check_rate_limit(key, max_per_minute=10):
    now = time.time()
    if key not in _rate_limit_store:
        _rate_limit_store[key] = []
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < 60]
    if len(_rate_limit_store[key]) >= max_per_minute:
        return False
    _rate_limit_store[key].append(now)
    return True

# =============================================
# 会话与聊天相关接口
# =============================================

@api_v1_bp.route('/chat/save', methods=['POST'])
def save_messages():
    """保存用户会话消息（无需登录）"""
    data = request.get_json() or {}
    openid = data.get('openid')
    messages = data.get('messages', [])

    if not openid:
        return api_err('openid是必需的', 400)

    # IP限流
    _ensure_rate_limit()
    if not _check_rate_limit(request.remote_addr or 'unknown'):
        return api_err('请求太频繁', 429)

    from models import get_db
    import json
    with get_db() as conn:
        now = datetime.now().isoformat()
        existing = conn.execute('SELECT created_at FROM chat_messages WHERE openid=?', (openid,)).fetchone()
        if existing:
            conn.execute(
                'UPDATE chat_messages SET messages=?, updated_at=? WHERE openid=?',
                (json.dumps(messages, ensure_ascii=False), now, openid)
            )
        else:
            conn.execute(
                'INSERT INTO chat_messages (openid, messages, created_at, updated_at) VALUES (?, ?, ?, ?)',
                (openid, json.dumps(messages, ensure_ascii=False), now, now)
            )
        conn.commit()

    return api_ok({'saved': True})

@api_v1_bp.route('/chat/history', methods=['POST'])
def get_chat_history():
    """获取会话历史（无需登录）"""
    data = request.get_json() or {}
    openid = data.get('openid')
    
    if not openid:
        return api_err('openid是必需的', 400)
    
    from models import get_db
    import json
    with get_db() as conn:
        row = conn.execute('SELECT messages FROM chat_messages WHERE openid=?', (openid,)).fetchone()
        messages = json.loads(row['messages']) if row else []
    
    return api_ok({'messages': messages})

@api_v1_bp.route('/chat/request', methods=['POST'])
def chat_request():
    """非流式AI对话请求（带RAG知识增强）"""
    user_id, error = require_auth()
    if error:
        return error

    data = request.get_json() or {}
    messages = data.get('messages', [])
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 2048)
    skip_rag = data.get('skip_rag', False)  # 可选跳过RAG

    if not messages:
        return api_err('messages是必需的', 400)

    # ── RAG 知识增强 ──
    knowledge_injected = False
    if not skip_rag:
        # 取用户最后一条消息作为查询
        last_user_msg = ''
        for m in reversed(messages):
            if m.get('role') == 'user':
                last_user_msg = m.get('content', '')[:200]
                break
        if last_user_msg:
            knowledge = _rag_search(last_user_msg, top_k=5)
            if knowledge:
                ctx = _build_rag_context(knowledge)
                # 追加到已有的 system 消息，或新建一条
                has_system = False
                for m in messages:
                    if m.get('role') == 'system':
                        m['content'] += ctx
                        has_system = True
                        break
                if not has_system:
                    messages.insert(0, {'role': 'system', 'content': '你是一个智能客服助手。' + ctx})
                knowledge_injected = True

    try:
        # 从system_config读取小程序AI配置
        from models import get_db
        with get_db() as conn:
            rows = {r['key']: r['value'] for r in
                    conn.execute("SELECT key, value FROM system_config WHERE key IN "
                                "('mp_ai_provider','mp_ai_model','mp_ai_base_url','mp_ai_api_key')").fetchall()}

        provider = rows.get('mp_ai_provider', 'deepseek') or 'deepseek'
        model = rows.get('mp_ai_model', 'deepseek-chat') or 'deepseek-chat'
        base_url = rows.get('mp_ai_base_url', 'https://api.deepseek.com') or 'https://api.deepseek.com'
        api_key = rows.get('mp_ai_api_key', '')

        # 回退
        if not api_key:
            fallback_keys = {
                'deepseek': 'deepseek_api_key',
                'dashscope': 'dashscope_api_key',
                'openai': 'openai_api_key',
                'openrouter': 'openrouter_api_key',
            }
            fallback = fallback_keys.get(provider)
            if fallback:
                with get_db() as conn2:
                    row = conn2.execute("SELECT value FROM system_config WHERE key=?", (fallback,)).fetchone()
                api_key = row['value'] if row else ''
            if not api_key:
                api_key = os.environ.get(f'{provider.upper()}_API_KEY', '')

        if not api_key:
            return api_err(f'AI API Key 未配置，请在系统设置「小程序 AI 配置」中设置', 500)

        # 调用 AI API
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        content = resp.choices[0].message.content

        # 异步记录token消耗
        if hasattr(resp, 'usage') and resp.usage:
            try:
                from agent_matrix.engine import _log_token_usage
                threading.Thread(target=_log_token_usage, args=(
                    0, 'AI客服', model, provider,
                    resp.usage.prompt_tokens or 0,
                    resp.usage.completion_tokens or 0,
                    resp.usage.total_tokens or 0,
                    'chat', 'text', user_id, None, None
                ), daemon=True).start()
            except ImportError:
                pass

        return api_ok({
            'content': content,
            'rag': knowledge_injected,
        })

    except Exception as e:
        return api_err(f'AI对话请求失败: {str(e)}', 500)


@api_v1_bp.route('/chat/public', methods=['POST'])
def chat_public():
    """公开AI对话（官网商务机器人/抖音小程序，无需登录，带限流+RAG）"""
    data = request.get_json() or {}
    messages = data.get('messages', [])
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 2048)
    source = data.get('source', 'website')  # website / douyin / tiktok

    if not messages:
        return api_err('messages是必需的', 400)

    # 简易IP限流（每IP每分钟10次）
    ip = request.remote_addr or 'unknown'
    _ensure_rate_limit()
    if not _check_rate_limit(ip):
        return api_err('请求太频繁，请稍后再试', 429)

    # ── RAG 知识增强 ──
    last_user_msg = ''
    for m in reversed(messages):
        if m.get('role') == 'user':
            last_user_msg = m.get('content', '')[:200]
            break
    if last_user_msg:
        knowledge = _rag_search(last_user_msg, top_k=5)
        if knowledge:
            ctx = _build_rag_context(knowledge)
            has_system = False
            for m in messages:
                if m.get('role') == 'system':
                    m['content'] += ctx
                    has_system = True
                    break
            if not has_system:
                messages.insert(0, {'role': 'system',
                    'content': f'你是VeroRon 维洛智能的商务助手。用户来自: {source}。'
                               f'请用中文友好地回答关于产品、价格、功能的问题。' + ctx})

    try:
        from models import get_db
        with get_db() as conn:
            rows = {r['key']: r['value'] for r in
                    conn.execute("SELECT key, value FROM system_config WHERE key IN "
                                "('mp_ai_provider','mp_ai_model','mp_ai_base_url','mp_ai_api_key')").fetchall()}

        provider = rows.get('mp_ai_provider', 'deepseek') or 'deepseek'
        model = rows.get('mp_ai_model', 'deepseek-chat') or 'deepseek-chat'
        base_url = rows.get('mp_ai_base_url', 'https://api.deepseek.com') or 'https://api.deepseek.com'
        api_key = rows.get('mp_ai_api_key', '')

        if not api_key:
            for fk in ['deepseek_api_key', 'dashscope_api_key']:
                with get_db() as c:
                    r = c.execute("SELECT value FROM system_config WHERE key=?", (fk,)).fetchone()
                if r and r['value']:
                    api_key = r['value']
                    break
            if not api_key:
                api_key = os.environ.get('DEEPSEEK_API_KEY', '')

        if not api_key:
            return api_err('AI 服务暂未配置', 500)

        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return api_ok({'content': resp.choices[0].message.content})

    except Exception as e:
        return api_err(f'请求失败: {str(e)}', 500)

@api_v1_bp.route('/chat', methods=['POST'])
def chat_stream():
    """流式AI对话接口（免登录）"""
    import logging
    logging.info(f"[DEBUG] chat_stream called, path={request.path}, method={request.method}")
    
    data = request.get_json() or {}
    messages = data.get('messages', [])
    profile = data.get('profile', {})
    visit_count = data.get('visitCount', 1)
    three_ask_state = data.get('threeAskState', 0)
    
    if not messages:
        return api_err('messages是必需的', 400)
    
    def generate():
        import logging
        yield 'data: {"role":"assistant"}\n\n'
        
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            
            # RAG检索
            retrieved_knowledge = []
            user_query = messages[-1]['content'] if messages else ''
            if user_query:
                try:
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'cognition-service'))
                    from services.embedding import search_knowledge
                    retrieved_knowledge = search_knowledge(user_query, top_k=3)
                except Exception as e:
                    logging.warning(f"RAG检索失败，使用默认回答: {e}")
            
            # 构建系统提示词（包含检索到的知识）
            knowledge_context = ''
            if retrieved_knowledge:
                knowledge_context = "参考知识：\n" + "\n".join([f"- {item.get('content', '')}" for item in retrieved_knowledge])
            
            system_prompt = f"""
你是VeroRun的AI助手。请根据用户的问题，结合参考知识进行回答。

{knowledge_context}

回答规则：
1. 优先使用参考知识中的信息
2. 如果参考知识中没有相关内容，可以用你的通用知识回答
3. 回答要友好、专业、简洁
"""
            
            # 构建消息
            chat_messages = [{"role": "system", "content": system_prompt}]
            for msg in messages:
                chat_messages.append({"role": msg.get('role', 'user'), "content": msg.get('content', '')})
            
            # 调用AI引擎
            from agent_matrix.engine import AIEngine
            
            config = {
                'provider': 'dashscope',
                'model_name': 'qwen-turbo',
                'system_prompt': system_prompt
            }
            
            engine = AIEngine(config)
            full_reply = ''
            
            def _sse_event(event_type, **kwargs):
                """SSE data line with proper JSON encoding to prevent XSS/protocol injection."""
                payload = {'type': event_type}
                payload.update(kwargs)
                return f'data: {json.dumps(payload, ensure_ascii=False)}\n\n'
            
            for token in engine.chat_stream(chat_messages, temperature=0.7, max_tokens=2048):
                if token.startswith("Error:"):
                    yield _sse_event('error', content=token)
                    return
                full_reply += token
                yield _sse_event('token', content=token)
            
            yield _sse_event('done', reply=full_reply, retrievedKnowledge=retrieved_knowledge)
            
        except Exception as e:
            import logging
            logging.error(f"[API] 流式对话失败: {e}")
            yield _sse_event('error', content=f'对话失败: {str(e)}')
    
    return Response(stream_with_context(generate()),
                   mimetype='text/event-stream',
                   headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

# =============================================
# 用户画像与会话摘要
# =============================================

@api_v1_bp.route('/profile/save', methods=['POST'])
def save_profile():
    """保存用户画像（无需登录）"""
    data = request.get_json() or {}
    openid = data.get('openid')
    profile = data.get('profile', {})
    
    if not openid:
        return api_err('openid是必需的', 400)
    
    from models import get_db
    import json
    with get_db() as conn:
        now = datetime.now().isoformat()
        existing = conn.execute('SELECT created_at FROM mp_profiles WHERE openid=?', (openid,)).fetchone()
        if existing:
            conn.execute(
                'UPDATE mp_profiles SET profile=?, updated_at=? WHERE openid=?',
                (json.dumps(profile, ensure_ascii=False), now, openid)
            )
        else:
            conn.execute(
                'INSERT INTO mp_profiles (openid, profile, created_at, updated_at) VALUES (?, ?, ?, ?)',
                (openid, json.dumps(profile, ensure_ascii=False), now, now)
            )
        conn.commit()
    
    return api_ok({})

@api_v1_bp.route('/profile/get', methods=['POST'])
def get_profile():
    """获取用户画像（无需登录）"""
    data = request.get_json() or {}
    openid = data.get('openid')
    
    if not openid:
        return api_err('openid是必需的', 400)
    
    from models import get_db
    import json
    with get_db() as conn:
        row = conn.execute('SELECT profile FROM mp_profiles WHERE openid=?', (openid,)).fetchone()
        profile = json.loads(row['profile']) if row else {}
    
    return api_ok({'profile': profile})

@api_v1_bp.route('/profile/summary', methods=['POST'])
def save_summary():
    """保存会话摘要文本（无需登录）"""
    data = request.get_json() or {}
    openid = data.get('openid')
    summary = data.get('summary', '')
    
    if not openid:
        return api_err('openid是必需的', 400)
    
    from models import get_db
    with get_db() as conn:
        now = datetime.now().isoformat()
        existing = conn.execute('SELECT created_at FROM mp_profiles WHERE openid=?', (openid,)).fetchone()
        if existing:
            conn.execute(
                'UPDATE mp_profiles SET summary=?, updated_at=? WHERE openid=?',
                (summary, now, openid)
            )
        else:
            conn.execute(
                'INSERT INTO mp_profiles (openid, summary, created_at, updated_at) VALUES (?, ?, ?, ?)',
                (openid, summary, now, now)
            )
        conn.commit()
    
    return api_ok({})

# =============================================
# 知识库与RAG检索
# =============================================

@api_v1_bp.route('/knowledge/list', methods=['POST'])
def list_knowledge():
    """获取知识库列表"""
    user_id, error = require_auth()
    if error:
        return error
    
    data = request.get_json() or {}
    keyword = data.get('keyword')
    category = data.get('category')
    page = data.get('page', 1)
    page_size = data.get('pageSize', 10)
    
    # 知识库列表获取逻辑
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
        from models import get_db
        
        with get_db() as db:
            query = "SELECT * FROM knowledge_blocks WHERE 1=1"
            params = []
            
            if keyword:
                query += " AND (title LIKE ? OR content LIKE ? OR keywords LIKE ?)"
                params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " ORDER BY priority DESC, created_at DESC"
            
            # 分页
            offset = (page - 1) * page_size
            query += " LIMIT ? OFFSET ?"
            params.extend([page_size, offset])
            
            rows = db.execute(query, params).fetchall()
            
            # 获取总数
            count_query = "SELECT COUNT(*) as total FROM knowledge_blocks WHERE 1=1"
            count_params = []
            if keyword:
                count_query += " AND (title LIKE ? OR content LIKE ? OR keywords LIKE ?)"
                count_params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
            if category:
                count_query += " AND category = ?"
                count_params.append(category)
            
            total = db.execute(count_query, count_params).fetchone()['total']
            
            result = [{
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'keywords': row['keywords'].split(',') if row['keywords'] else [],
                'category': row['category'],
                'priority': row['priority'],
                'createdAt': row['created_at']
            } for row in rows]
            
            return api_ok({
                'items': result,
                'total': total,
                'page': page,
                'pageSize': page_size,
                'pages': max(1, (total + page_size - 1) // page_size)
            })
    except Exception as e:
        import logging
        logging.error(f"[API] 获取知识库列表失败: {e}")
        return api_err(f'获取知识库失败: {str(e)}', 500)

@api_v1_bp.route('/knowledge/save', methods=['POST'])
def save_knowledge():
    """新增/更新知识块"""
    user_id, error = require_auth()
    if error:
        return error
    
    data = request.get_json() or {}
    kb_id = data.get('id')
    title = data.get('title')
    content = data.get('content')
    keywords = data.get('keywords', [])
    category = data.get('category')
    priority = data.get('priority', 0)
    
    if not kb_id or not title or not content:
        return api_err('id, title和content是必需的', 400)
    
    # 知识块保存逻辑
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
        from models import get_db
        
        keywords_str = ','.join(keywords) if isinstance(keywords, list) else str(keywords)
        
        with get_db() as db:
            # 检查是否已存在
            existing = db.execute("SELECT id FROM knowledge_blocks WHERE id = ?", (kb_id,)).fetchone()
            
            if existing:
                # 更新
                db.execute("""
                    UPDATE knowledge_blocks 
                    SET title=?, content=?, keywords=?, category=?, priority=?
                    WHERE id=?
                """, (title, content, keywords_str, category, priority, kb_id))
                db.commit()
                return api_ok({'id': kb_id, 'message': '知识块已更新'})
            else:
                # 新增
                db.execute("""
                    INSERT INTO knowledge_blocks (id, title, content, keywords, category, priority)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (kb_id, title, content, keywords_str, category, priority))
                db.commit()
                return api_ok({'id': kb_id, 'message': '知识块已创建'})
    except Exception as e:
        import logging
        logging.error(f"[API] 保存知识块失败: {e}")
        return api_err(f'保存知识块失败: {str(e)}', 500)

@api_v1_bp.route('/knowledge/delete', methods=['POST'])
def delete_knowledge():
    """删除知识块"""
    user_id, error = require_auth()
    if error:
        return error
    
    data = request.get_json() or {}
    kb_id = data.get('id')
    
    if not kb_id:
        return api_err('id是必需的', 400)
    
    # 知识块删除逻辑
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
        from models import get_db
        
        with get_db() as db:
            result = db.execute("DELETE FROM knowledge_blocks WHERE id = ?", (kb_id,)).rowcount
            db.commit()
            
            if result > 0:
                return api_ok({'id': kb_id, 'message': '知识块已删除'})
            else:
                return api_err('知识块不存在', 404)
    except Exception as e:
        import logging
        logging.error(f"[API] 删除知识块失败: {e}")
        return api_err(f'删除知识块失败: {str(e)}', 500)


@api_v1_bp.route('/rag/search', methods=['POST'])
def rag_search():
    """混合语义检索（无需登录，供抖音小程序调用）"""
    
    data = request.get_json() or {}
    query = data.get('query')
    top_k = data.get('topK', 5)
    category = data.get('category')
    
    if not query:
        return api_err('query是必需的', 400)
    
    try:
        # 从 knowledge_blocks 表中检索匹配的知识块
        from models import get_db
        with get_db() as conn:
            # 关键词匹配：拆分为单个中文字符+双字组合进行模糊匹配
            chars = list(query.replace(' ', ''))
            bigrams = [query[i:i+2] for i in range(len(query)-1)]
            search_terms = set(chars + bigrams)
            
            # 获取所有知识块
            sql = "SELECT * FROM knowledge_blocks"
            params = []
            if category:
                sql += " WHERE category=?"
                params.append(category)
            sql += " ORDER BY priority DESC"
            all_blocks = conn.execute(sql, params).fetchall() if not category else \
                         conn.execute(sql, params).fetchall()
            if category:
                all_blocks = [dict(r) for r in all_blocks]
            else:
                all_blocks = [dict(r) for r in conn.execute("SELECT * FROM knowledge_blocks ORDER BY priority DESC").fetchall()]
        
        # 评分：计算查询词与关键词+内容的匹配度
        results = []
        for block in all_blocks:
            score = 0.0
            keywords = (block['keywords'] or '').split(',')
            content = block['content'] or ''
            title = block['title'] or ''
            
            # 关键词匹配（权重0.6）
            kw_matches = sum(1 for kw in keywords if kw and kw in query)
            if kw_matches > 0:
                score += min(kw_matches / len(keywords), 1.0) * 0.6
            
            # 内容/标题字符匹配（权重0.4）
            content_chars = set(content)
            title_chars = set(title)
            char_overlap = len(search_terms & content_chars) / max(len(search_terms), 1)
            title_overlap = len(search_terms & title_chars) / max(len(search_terms), 1)
            score += char_overlap * 0.25 + title_overlap * 0.15
            
            # 精确短语匹配加分
            if query in content:
                score += 0.3
            if query in title:
                score += 0.2
            
            if score > 0:
                results.append({'block': {
                    'id': block['id'],
                    'title': block['title'],
                    'content': block['content'],
                    'category': block['category'],
                    'keywords': block['keywords'],
                }, 'score': round(score, 4)})
        
        # 排序取Top-K
        results.sort(key=lambda x: -x['score'])
        results = results[:min(top_k, 20)]
        
        return api_ok(results if results else [])
        
    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.error(f'[api_v1] RAG检索失败: {e}')
        return api_ok([])

# =============================================
# 其他业务接口
# =============================================

@api_v1_bp.route('/notify/feishu', methods=['POST'])
def send_feishu_notify():
    """飞书卡片通知代理发送"""
    user_id, error = require_auth()
    if error:
        return error
    
    data = request.get_json() or {}
    card_data = data.get('cardData', {})
    webhook_url = data.get('webhookUrl')
    
    # 飞书通知发送逻辑
    if webhook_url:
        try:
            import requests
            import json
            headers = {'Content-Type': 'application/json'}
            response = requests.post(webhook_url, headers=headers, json=card_data, timeout=10)
            if response.status_code == 200:
                return api_ok({'result': 'success', 'message': '飞书通知已发送'})
            else:
                return api_ok({'result': 'failed', 'message': f'飞书返回错误: {response.status_code}'})
        except Exception as e:
            import logging
            logging.warning(f"[API] 飞书通知发送失败: {e}")
            return api_ok({'result': 'error', 'message': str(e)})
    
    return api_ok({'result': 'skipped', 'message': '未提供webhookUrl'})

@api_v1_bp.route('/feedback/save', methods=['POST'])
def save_feedback():
    """保存用户反馈（无需登录，供抖音小程序调用）"""
    data = request.get_json() or {}
    openid = data.get('openid')
    message_id = data.get('messageId')
    feedback = data.get('feedback')
    content = data.get('content')
    query = data.get('query')
    retrieved_ids = data.get('retrievedIds', [])
    ai_reply = data.get('aiReply')
    retrieved_knowledge = data.get('retrievedKnowledge', [])
    timestamp = data.get('timestamp')

    # 验证必填字段
    if not openid:
        return api_err('openid是必需的', 400)
    if not message_id:
        return api_err('messageId是必需的', 400)
    if not feedback:
        return api_err('feedback是必需的', 400)
    if not content:
        return api_err('content是必需的', 400)
    if not query:
        return api_err('query是必需的', 400)
    if not ai_reply:
        return api_err('aiReply是必需的', 400)
    
    # 用户反馈保存逻辑
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
        from models import get_db
        
        with get_db() as db:
            db.execute("""
                INSERT INTO user_feedback (user_id, type, category, title, content, contact, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                None,  # user_id (抖音用户无 user_id)
                'rating',  # type
                'chat',  # category
                f'来自抖音小程序的聊天反馈',  # title
                f'问题: {query}\nAI回复: {ai_reply}\n用户反馈: {feedback or ""}\n评价: {content or ""}',  # content
                openid or '',  # contact (使用 openid)
                'pending'
            ))
            db.commit()
            feedback_id = db.execute("SELECT last_insert_rowid() as id").fetchone()['id']
            return api_ok({'feedbackId': feedback_id, 'message': '反馈已保存'})
    except Exception as e:
        import logging
        logging.error(f"[API] 保存用户反馈失败: {e}")
        return api_ok({'feedbackId': None, 'message': f'保存失败: {str(e)}'})

@api_v1_bp.route('/visit/increment', methods=['POST'])
def increment_visit():
    """递增用户来访次数并返回最新值（无需登录）"""
    data = request.get_json() or {}
    openid = data.get('openid')
    
    if not openid:
        return api_err('openid是必需的', 400)
    
    # 访问计数递增逻辑
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))
        from models import get_db
        
        with get_db() as db:
            # 尝试更新现有记录
            result = db.execute("""
                UPDATE mp_profiles 
                SET visit_count = visit_count + 1, 
                    updated_at = datetime('now')
                WHERE openid = ?
            """, (openid,)).rowcount
            
            # 如果没有更新任何行，说明是首次访问，需要插入新记录
            if result == 0:
                db.execute("""
                    INSERT INTO mp_profiles (openid, visit_count, created_at, updated_at)
                    VALUES (?, 1, datetime('now'), datetime('now'))
                """, (openid,))
            
            db.commit()
            
            # 获取最新的访问次数
            row = db.execute("SELECT visit_count FROM mp_profiles WHERE openid = ?", (openid,)).fetchone()
            visit_count = row['visit_count'] if row else 1
            
            return api_ok({'visitCount': visit_count, 'openid': openid})
    except Exception as e:
        import logging
        logging.error(f"[API] 访问计数更新失败: {e}")
        return api_ok({'visitCount': 1, 'openid': openid, 'error': str(e)})
