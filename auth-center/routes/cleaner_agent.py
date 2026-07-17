#!/usr/bin/env python3
"""Cleaner Agent — 数据清洗智能体
   管理员提交原始内容 → AI清洗 → knowledge_blocks入库 → 全站AI自动发现
   可被 Agent Matrix 直接调用（通过 process_clean_content 函数）
"""
import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from flask import Blueprint, jsonify, request
from i18n import _
from models import get_db

cleaner_bp = Blueprint('cleaner', __name__, url_prefix='/shop/cleaner')

CLEANER_AGENT_NAME = 'Data Cleaner Agent'
CLEANER_AGENT_DOMAIN = 'cleaner'


def _require_admin():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '') if auth.startswith('Bearer ') else auth
    if not token:
        return None, (jsonify({'success': False, 'error': _('请先登录')}), 401)
    from services.jwt_service import validate_token
    payload = validate_token(token)
    if not payload:
        return None, (jsonify({'success': False, 'error': _('无效Token')}), 401)
    if not payload.get('is_admin'):
        return None, (jsonify({'success': False, 'error': _('需要管理员权限')}), 403)
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
        return {'error': _('AI API Key 未配置，请在系统配置中设置')}

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
        return {'error': _('AI 返回结果缺少必填字段'), 'raw': text}
    return result


def _get_existing_titles():
    """获取已有知识库标题（用于去重）"""
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT title FROM knowledge_blocks").fetchall()
            return {r['title'].strip().lower() for r in rows}
    except Exception:
        return set()


# =============================================
# 核心函数：可供 Agent Matrix 直接调用
# =============================================

def process_clean_content(raw_content: str, admin_id: int = 0) -> dict:
    """清洗一条原始内容，写入 knowledge_blocks

    返回：{'success': bool, 'kb_id': '...' or 'duplicate',
           'title': '...', 'category': '...', 'error': '...'}
    """
    if not raw_content or not raw_content.strip():
        return {'success': False, 'error': _('内容不能为空')}

    raw_content = raw_content.strip()[:50000]
    existing_titles = _get_existing_titles()

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

    with get_db() as conn:
        if result.get('is_duplicate'):
            conn.execute("UPDATE knowledge_queue SET status='done', cleaned_id='duplicate' WHERE id=%s", (qid,))
            conn.commit()
            return {'success': True, 'kb_id': 'duplicate', 'title': result['title'],
                    'category': result.get('category', ''), 'message': _('检测到重复，已跳过')}

        kb_id = 'kb_cleaner_' + str(qid) + '_' + ''.join(re.findall(r'\w', result['title'])[:10])
        conn.execute(
            '''INSERT INTO knowledge_blocks
               (id, title, content, keywords, category, priority, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,NOW())
               ON CONFLICT (id) DO NOTHING''',
            (kb_id, result['title'][:200], result['content'],
             result.get('keywords', '')[:500], result.get('category', 'general'), 5)
        )
        conn.execute("UPDATE knowledge_queue SET status='done', cleaned_id=%s WHERE id=%s", (kb_id, qid))
        conn.commit()

    return {
        'success': True, 'kb_id': kb_id, 'title': result['title'],
        'category': result.get('category', 'general'),
        'keywords': result.get('keywords', ''),
        'message': _('清洗完成，已写入知识库')
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
        return jsonify({'success': False, 'error': _('内容不能为空')}), 400

    result = process_clean_content(raw, admin_id=payload['user_id'])
    if not result['success']:
        return jsonify({'success': False, 'error': result['error']}), 500
    return jsonify({'success': True, 'data': result, 'message': result.get('message', _('清洗完成'))})


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
            return jsonify({'success': False, 'error': _('队列项不存在')}), 404
        if row['status'] == 'cleaning':
            return jsonify({'success': False, 'error': _('正在清洗中，请勿重复执行')}), 400

    result = process_clean_content(row['raw_content'], admin_id=payload['user_id'])
    if not result['success']:
        return jsonify({'success': False, 'error': result['error']}), 500
    return jsonify({'success': True, 'data': result, 'message': result.get('message', _('清洗完成'))})


@cleaner_bp.route('/run-all', methods=['POST'])
def run_all():
    payload, err = _require_admin()
    if err:
        return err
    with get_db() as conn:
        rows = conn.execute("SELECT id, raw_content FROM knowledge_queue WHERE status='pending' ORDER BY id ASC").fetchall()

    if not rows:
        return jsonify({'success': True, 'data': [], 'message': _('没有待清洗项')})

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
        'message': _('完成 {done}/{len_results} 项', done=done, len_results=len(results))
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
