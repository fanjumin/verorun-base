#!/usr/bin/env python3
"""Content Factory Plugin — AI 内容加工 (Qwen 提取+分析+改写)"""
import json, logging
from typing import Optional
from plugins.content_factory.models import get_cf_db

logger = logging.getLogger(__name__)


def _get_ai_key() -> Optional[str]:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'auth-center'))
    from models import get_db
    with get_db() as conn:
        row = conn.execute("SELECT value FROM system_config WHERE key='dashscope_text_key'").fetchone()
    return row['value'] if row else None


def _call_qwen(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    import requests, json
    api_key = _get_ai_key()
    if not api_key:
        raise RuntimeError(_"DashScope Text Key is not configured")
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {'model': 'qwen-turbo', 'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens, 'temperature': 0.7}
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']


PROCESS_PROMPT = """请处理以下原始内容，输出JSON：

{{
  "title": _"Optimized Title (Concise and powerful, within 20 characters)",
  "summary": _"One-sentence summary (within 50 characters)",
  "body": _"Reformat the main text with Markdown. Leave a blank line between paragraphs, use '-' for lists, and bold numbers and percentages with **. Do not use ```.",
  "keywords": [_"Keyword 1", _"Keyword 2", _"Keyword 3"],
  "risk_level": "low / normal / high / critical"
}}

原始内容：
标题：{title}
作者：{author}
正文原文：
{content}"""


def process_raw_content(raw_id: int, admin_id: int = 1) -> dict:
    conn = get_cf_db()
    raw = conn.execute('SELECT * FROM raw_contents WHERE id=?', (raw_id,)).fetchone()
    if not raw:
        return {'success': False, 'error': _'Content does not exist'}
    if raw['status'] == 'processed':
        return {'success': False, 'error': _'Already processed'}

    conn.execute("UPDATE raw_contents SET status='processing' WHERE id=?", (raw_id,))
    conn.commit()

    try:
        raw_content = (raw['content_html'] or raw['content_text'] or '')[:24000]
        cover_url = ''
        try:
            cj = json.loads(raw['content_json'] or '{}')
            cover_url = cj.get('cover_url', '')
        except:
            pass

        prompt = PROCESS_PROMPT.format(title=raw['title'] or _'No Title', author=raw['author'] or _'Unknown', content=raw_content)
        result_text = _call_qwen(prompt)
        data = json.loads(result_text)

        cur = conn.execute(
            """INSERT INTO processed_contents (raw_id, content_type, title, summary, body, keywords,
               risk_level, status, created_by)
               VALUES (?, 'article', ?, ?, ?, ?, ?, 'draft', ?) RETURNING id""",
            (raw_id, (data.get('title') or raw['title'])[:200], (data.get('summary') or '')[:500],
             data.get('body', ''), ','.join(data.get('keywords', [])),
             data.get('risk_level', 'normal'), admin_id)
        )
        conn.commit()
        pid = cur.fetchone()['id']
        if cover_url:
            conn.execute("UPDATE processed_contents SET image_url=? WHERE id=?", (cover_url, pid))
            conn.commit()
        conn.execute("UPDATE raw_contents SET status='processed', summary=? WHERE id=?", (data.get('summary', ''), raw_id))
        conn.commit()
        return {'success': True, 'processed_id': pid, 'title': data.get('title', '')}

    except json.JSONDecodeError:
        try:
            cleaned = result_text.strip()
            if cleaned.startswith('```'): cleaned = cleaned.split('\n', 1)[1]
            if cleaned.endswith('```'): cleaned = cleaned.rsplit('```', 1)[0]
            data = json.loads(cleaned.strip())
        except:
            conn.execute(_"UPDATE raw_contents SET status='failed', error_msg='JSON parsing failed' WHERE id=?", (raw_id,))
            conn.commit()
            return {'success': False, 'error': f_'AI output format error: {result_text[:200]}', 'raw_output': result_text}

        cur = conn.execute(
            """INSERT INTO processed_contents (raw_id, content_type, title, summary, body, keywords,
               risk_level, status, created_by)
               VALUES (?, 'article', ?, ?, ?, ?, ?, 'draft', ?) RETURNING id""",
            (raw_id, data.get('title', '')[:200], data.get('summary', '')[:500],
             data.get('body', ''), ','.join(data.get('keywords', [])),
             data.get('risk_level', 'normal'), admin_id)
        )
        conn.commit()
        pid = cur.fetchone()['id']
        if cover_url:
            conn.execute("UPDATE processed_contents SET image_url=? WHERE id=?", (cover_url, pid))
            conn.commit()
        conn.execute("UPDATE raw_contents SET status='processed', summary=? WHERE id=?", (data.get('summary', ''), raw_id))
        conn.commit()
        return {'success': True, 'processed_id': pid}

    except Exception as e:
        logger.exception(f"[CF] AI加工失败 raw_id={raw_id}")
        conn.execute("UPDATE raw_contents SET status='failed', error_msg=? WHERE id=?", (str(e)[:200], raw_id))
        conn.commit()
        return {'success': False, 'error': str(e)}


def batch_process(raw_ids: list, admin_id: int = 1) -> dict:
    ok = 0
    fail = 0
    results = []
    for rid in raw_ids:
        r = process_raw_content(rid, admin_id)
        if r['success']:
            ok += 1
            results.append(r)
        else:
            fail += 1
    return {'success': ok > 0, 'ok': ok, 'fail': fail, 'results': results}