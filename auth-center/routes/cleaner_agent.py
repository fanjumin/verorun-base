#!/usr/bin/env python3
"""Cleaner Agent — 数据清洗智能体
   管理员提交原始内容 → AI清洗 → knowledge_blocks入库 → 全站AI自动发现
   可被 Agent Matrix 直接调用（通过 process_clean_content 函数）
"""
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from flask import Blueprint, jsonify, request
from models import get_db

cleaner_bp = Blueprint('cleaner', __name__, url_prefix='/shop/cleaner')

CLEANER_AGENT_NAME = 'Data Cleaner Agent'
CLEANER_AGENT_DOMAIN = 'cleaner'


def _require_admin():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        return None, (jsonify({'success': False, 'error': '请先登录'}), 401)
    from services.jwt_service import validate_token
    payload = validate_token(token)
    if not payload:
        return None, (jsonify({'success': False, 'error': '无效Token'}), 401)
    if not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': '需要管理员权限'}), 403)
    return payload, None


def _read_system_config(key: str, default=''):
    """从 system_config 表读取配置"""
    try:
        with get_db() as conn:
            row = conn.execute("SELECT value FROM system_config WHERE key=%s", (key,)).fetchone()
            return row['value'] if row else default
    except Exception:
        return default


def _get_llm_config():
    """获取清洗用的 LLM 配置"""
    provider = _read_system_config('cleaner_ai_provider') or 'deepseek'
    model = _read_system_config('cleaner_ai_model') or 'deepseek-chat'
    base_url = _read_system_config('cleaner_ai_base_url') or 'https://api.deepseek.com'
    api_key = _read_system_config('cleaner_ai_api_key', '')

    if not api_key:
        key_map = {
            'deepseek': 'deepseek_api_key', 'dashscope': 'dashscope_api_key',
            'openai': 'openai_api_key', 'openrouter': 'openrouter_api_key',
        }
        env_key = key_map.get(provider, 'deepseek_api_key')
        api_key = _read_system_config(env_key, '')
        if not api_key:
            api_key = os.environ.get(f'{provider.upper()}_API_KEY', '')

    return {
        'provider': provider, 'model': model,
        'base_url': base_url, 'api_key': api_key,
    }


def _call_llm(system_prompt: str, user_prompt: str) -> dict:
    """调用 LLM 并返回 JSON 结果"""
    cfg = _get_llm_config()
    if not cfg['api_key']:
        return {'error': 'AI API Key 未配置，请在系统配置中设置'}

    from openai import OpenAI
    client = OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])
    resp = client.chat.completions.create(
        model=cfg['model'],
        messages=[{'role': 'system', 'content': system_prompt},
                  {'role': 'user', 'content': user_prompt}],
        temperature=0.3, max_tokens=4096,
        response_format={'type': 'json_object'}
    )
    text = resp.choices[0].message.content.strip()
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    result = json.loads(json_match.group()) if json_match else json.loads(text)
    if not result.get('title') or not result.get('content'):
        return {'error': 'AI 返回结果缺少必填字段', 'raw': text}
    return result


def _get_existing_for_dedup():
    """获取已有知识库标题+关键词（用于去重和冲突检测）"""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, title, keywords, category, source FROM knowledge_blocks WHERE deleted_at IS NULL"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


def _jaccard_similarity(a: str, b: str) -> float:
    """计算两个关键词列表的 Jaccard 相似度"""
    set_a = set((a or '').split(','))
    set_b = set((b or '').split(','))
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _title_similarity(title1: str, title2: str) -> float:
    """简单的标题相似度（字符级 Jaccard）"""
    t1 = (title1 or '').strip().lower()
    t2 = (title2 or '').strip().lower()
    if not t1 or not t2:
        return 0.0
    set1 = set(t1)
    set2 = set(t2)
    return len(set1 & set2) / len(set1 | set2)


def _dedup_check(new_title: str, new_keywords: str, existing: list) -> tuple:
    """
    两级去重检测。
    返回 (is_duplicate: bool, existing_entry: dict or None, reason: str)
    """
    new_title_lower = (new_title or '').strip().lower()
    new_kw = new_keywords or ''

    # 第一级 a：标题精确匹配
    for entry in existing:
        if (entry['title'] or '').strip().lower() == new_title_lower:
            return True, entry, 'title_exact_match'

    # 第一级 b：关键词 Jaccard 相似度 > 0.75
    if new_kw:
        for entry in existing:
            jac = _jaccard_similarity(new_kw, entry.get('keywords', ''))
            if jac > 0.75:
                return True, entry, f'keyword_jaccard_{jac:.2f}'

    return False, None, ''


CATEGORY_LIMITS = {
    'company': 30, 'product': 50, 'price': 20, 'tech': 50,
    'service': 30, 'faq': 100, 'industry': 30, 'general': 50,
}


def _evict_if_over_limit(category: str):
    """超出上限时淘汰自动条目（保护人工条目）"""
    try:
        limit = CATEGORY_LIMITS.get(category, 50)
        with get_db() as conn:
            count = conn.execute(
                "SELECT COUNT(*) as c FROM knowledge_blocks WHERE category=%s AND deleted_at IS NULL",
                (category,)
            ).fetchone()['c']

            if count <= limit:
                return

            # 找优先级最低的 auto 条目
            row = conn.execute(
                """SELECT id, title FROM knowledge_blocks
                   WHERE category=%s AND source='auto' AND deleted_at IS NULL
                   ORDER BY priority ASC, quality_score ASC LIMIT 1""",
                (category,)
            ).fetchone()

            if row:
                conn.execute(
                    "UPDATE knowledge_blocks SET deleted_at=NOW() WHERE id=%s",
                    (row['id'],)
                )
                conn.commit()
                import logging
                logging.getLogger(__name__).info(
                    f"分类限流淘汰: {row['title']} (category={category}, {count}/{limit})"
                )
    except Exception:
        pass  # 限流失败不影响写入


def _update_quality(kb_id: str, factor: float, weight: float = 0.05):
    """EMA 平滑更新知识质量评分"""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT quality_score FROM knowledge_blocks WHERE id=%s", (kb_id,)
            ).fetchone()
            if not row:
                return
            current = row['quality_score'] or 0.5
            new_score = current * (1 - weight) + factor * weight
            new_score = max(0.0, min(1.0, new_score))
            conn.execute(
                "UPDATE knowledge_blocks SET quality_score=%s WHERE id=%s",
                (new_score, kb_id)
            )
            conn.commit()
    except Exception:
        pass


# =============================================
# 核心函数：可供 Agent Matrix 直接调用
# =============================================

def process_clean_content(raw_content: str, admin_id: int = 0) -> dict:
    """清洗一条原始内容，写入 knowledge_blocks

    返回：{'success': bool, 'kb_id': '...' or 'duplicate' or 'merged',
           'title': '...', 'category': '...', 'error': '...'}
    """
    if not raw_content or not raw_content.strip():
        return {'success': False, 'error': '内容不能为空'}

    raw_content = raw_content.strip()[:50000]
    existing = _get_existing_for_dedup()
    existing_titles = {e['title'].strip().lower() for e in existing}

    system_prompt = """你是VeroRon 维洛智能的数据清洗智能体。
将用户提供的原始内容清洗为标准知识库条目。

清洗规则：
1. 提取标题（简洁准确，不超过50字）
2. 正文去噪：去除广告、无关链接、重复信息、格式化排版
3. 分类：从以下类别中选择最合适的（company/product/price/tech/service/faq/industry）
4. 提取关键词：5-10个关键词，逗号分隔
5. 去重检测：如果内容与现有知识库相似度 > 85%，标记为重复

输出格式为纯JSON，不要包含其他文字：
{"title":"...","content":"...","category":"...","keywords":"...","is_duplicate":false,"duplicate_of":""}"""

    user_prompt = f"""原始内容：
---
{raw_content[:8000]}
---

现有知识库标题（供去重参考）：
{', '.join(list(existing_titles)[:50])}

请按规则清洗输出JSON。"""

    # 写入队列
    with get_db() as conn:
        qid = conn.execute(
            'INSERT INTO knowledge_queue (source, raw_content, admin_id) VALUES (%s,%s,%s) RETURNING id',
            ('matrix', raw_content, admin_id)
        ).fetchone()['id']
        conn.commit()

    # 调用 LLM
    result = _call_llm(system_prompt, user_prompt)
    if 'error' in result:
        with get_db() as conn:
            conn.execute("UPDATE knowledge_queue SET status='failed', error_msg=%s WHERE id=%s",
                         (result['error'][:500], qid))
            conn.commit()
        return {'success': False, 'error': result['error']}

    new_title = result['title'][:200]
    new_content = result['content']
    new_keywords = result.get('keywords', '')[:500]
    new_category = result.get('category', 'general')

    # === 阶段二增强：二级去重检测 ===
    is_dup, dup_entry, dup_reason = _dedup_check(new_title, new_keywords, existing)
    if is_dup and dup_entry:
        # 检查是否为同一分类的冲突合并
        if dup_entry.get('category') == new_category and dup_entry.get('source') != 'manual':
            if _title_similarity(new_title, dup_entry['title']) > 0.80:
                # 冲突合并：写版本历史 → 更新旧条目
                return _merge_entry(dup_entry, new_title, new_content, new_keywords, qid)

        # 非合并场景：标记为重复
        with get_db() as conn:
            conn.execute(
                "UPDATE knowledge_queue SET status='done', cleaned_id='duplicate' WHERE id=%s", (qid,))
            conn.commit()
        return {'success': True, 'kb_id': 'duplicate', 'title': new_title,
                'category': new_category, 'message': f'检测到重复({dup_reason})，已跳过'}

    # LLM 返回 is_duplicate 时二次确认
    if result.get('is_duplicate'):
        is_dup2, dup_entry2, _ = _dedup_check(new_title, new_keywords, existing)
        if is_dup2 and dup_entry2 and dup_entry2.get('source') != 'manual':
            if _title_similarity(new_title, dup_entry2['title']) > 0.75:
                return _merge_entry(dup_entry2, new_title, new_content, new_keywords, qid)

        with get_db() as conn:
            conn.execute(
                "UPDATE knowledge_queue SET status='done', cleaned_id='duplicate' WHERE id=%s", (qid,))
            conn.commit()
        return {'success': True, 'kb_id': 'duplicate', 'title': new_title,
                'category': new_category, 'message': 'LLM检测重复，已跳过'}

    # === 新增条目：写入 source + quality_score ===
    kb_id = 'kb_cleaner_' + str(qid) + '_' + ''.join(re.findall(r'\w', new_title)[:10])
    with get_db() as conn:
        conn.execute(
            '''INSERT INTO knowledge_blocks
               (id, title, content, keywords, category, priority, source, quality_score, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())
               ON CONFLICT (id) DO NOTHING''',
            (kb_id, new_title, new_content, new_keywords, new_category, 5, 'auto', 0.5)
        )
        conn.execute("UPDATE knowledge_queue SET status='done', cleaned_id=%s WHERE id=%s", (kb_id, qid))
        conn.commit()

    # === 分类限流检查 ===
    _evict_if_over_limit(new_category)

    return {
        'success': True, 'kb_id': kb_id, 'title': new_title,
        'category': new_category, 'keywords': new_keywords,
        'message': '清洗完成，已写入知识库'
    }


def _merge_entry(old_entry: dict, new_title: str, new_content: str, new_keywords: str, qid) -> dict:
    """冲突合并：写版本历史 → 更新旧条目"""
    import uuid
    history_id = 'kh_' + uuid.uuid4().hex[:12]

    with get_db() as conn:
        # 写版本历史
        conn.execute(
            """INSERT INTO knowledge_history (id, kb_id, previous_title, previous_content, changed_at)
               VALUES (%s,%s,%s,%s,NOW())""",
            (history_id, old_entry['id'], old_entry['title'], old_entry['content'])
        )
        # 更新旧条目
        conn.execute(
            """UPDATE knowledge_blocks
               SET content=%s, keywords=%s, updated_at=NOW(), quality_score=GREATEST(quality_score, 0.5)
               WHERE id=%s""",
            (new_content, new_keywords, old_entry['id'])
        )
        conn.execute(
            "UPDATE knowledge_queue SET status='done', cleaned_id=%s WHERE id=%s",
            (old_entry['id'], qid)
        )
        conn.commit()

    import logging
    logging.getLogger(__name__).info(
        f"冲突合并: '{old_entry['title']}' ← '{new_title}' (category={old_entry.get('category', '')})"
    )

    return {
        'success': True, 'kb_id': old_entry['id'], 'title': old_entry['title'],
        'category': old_entry.get('category', 'general'),
        'keywords': new_keywords,
        'message': '已合并更新已有条目（版本历史已保存）'
    }


def auto_register_sub_agent():
    """自动将 Cleaner Agent 注册为矩阵子 Agent（幂等）"""
    try:
        from agent_matrix import models as am_models
        existing = am_models.list_agents(domain=CLEANER_AGENT_DOMAIN, active_only=False)
        if existing:
            return  # 已注册
        am_models.create_agent({
            'name': CLEANER_AGENT_NAME,
            'role_type': 'sub',
            'domain': CLEANER_AGENT_DOMAIN,
            'managed_modules': json.dumps(['knowledge']),
            'capabilities': json.dumps(['text_clean', 'content_classify', 'dedup']),
            'description': 'Clean raw content into structured knowledge entries (dedup + classify + save to knowledge base)',
            'provider': 'deepseek',
            'model_name': 'deepseek-chat',
            'is_active': 1,
        })
        print(f'[CleanerAgent] ✅ 已自动注册为矩阵子Agent')
    except Exception as e:
        print(f'[CleanerAgent] 自动注册跳过: {e}')


# =============================================
# Flask API 端点（薄封装）
# =============================================

@cleaner_bp.route('/submit', methods=['POST'])
def submit_content():
    payload, err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    raw = (data.get('content', '') or '').strip()
    if not raw:
        return jsonify({'success': False, 'error': '内容不能为空'}), 400

    result = process_clean_content(raw, admin_id=payload['user_id'])
    if not result['success']:
        return jsonify({'success': False, 'error': result['error']}), 500
    return jsonify({'success': True, 'data': result, 'message': result.get('message', '清洗完成')})


@cleaner_bp.route('/list', methods=['GET'])
def list_queue():
    payload, err = _require_admin()
    if err:
        return err
    status_filter = request.args.get('status', '')
    with get_db() as conn:
        sql = 'SELECT * FROM knowledge_queue'
        params = []
        if status_filter:
            sql += ' WHERE status=%s'
            params.append(status_filter)
        sql += ' ORDER BY id DESC LIMIT 100'
        rows = conn.execute(sql, params).fetchall()
    return jsonify({'success': True, 'data': [dict(r) for r in rows]})


@cleaner_bp.route('/run/<int:qid>', methods=['POST'])
def run_clean(qid):
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        row = conn.execute('SELECT * FROM knowledge_queue WHERE id=%s', (qid,)).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '队列项不存在'}), 404
        if row['status'] == 'cleaning':
            return jsonify({'success': False, 'error': '正在清洗中，请勿重复执行'}), 400

    result = process_clean_content(row['raw_content'], admin_id=payload['user_id'])
    if not result['success']:
        return jsonify({'success': False, 'error': result['error']}), 500
    return jsonify({'success': True, 'data': result, 'message': result.get('message', '清洗完成')})


@cleaner_bp.route('/run-all', methods=['POST'])
def run_all():
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute("SELECT id, raw_content FROM knowledge_queue WHERE status='pending' ORDER BY id ASC").fetchall()

    if not rows:
        return jsonify({'success': True, 'data': [], 'message': '没有待清洗项'})

    results = []
    for r in rows:
        res = process_clean_content(r['raw_content'], admin_id=payload['user_id'])
        results.append({
            'id': r['id'],
            'status': 'done' if res['success'] else 'failed',
            'kb_id': res.get('kb_id', ''),
            'title': res.get('title', ''),
            'error': res.get('error', ''),
        })

    done = sum(1 for r in results if r['status'] == 'done')
    return jsonify({
        'success': True, 'data': results,
        'message': f'完成 {done}/{len(results)} 项'
    })


@cleaner_bp.route('/config', methods=['GET'])
def get_config():
    payload, err = _require_admin()
    if err:
        return err
    cfg = _get_llm_config()
    return jsonify({
        'success': True,
        'data': {'provider': cfg['provider'], 'model': cfg['model'], 'base_url': cfg['base_url']}
    })
