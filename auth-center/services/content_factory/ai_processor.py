#!/usr/bin/env python3
"""Content Factory — AI 内容加工 (单Agent: Qwen 提取+分析+改写)"""
import json, logging
from typing import Optional
from models import get_db

logger = logging.getLogger(__name__)

# ── 从 system_config 读取 AI Key ──
def _get_ai_key() -> Optional[str]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM system_config WHERE key='dashscope_text_key'"
        ).fetchone()
    return row['value'] if row else None


def _call_qwen(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    """调用通义千问 (与 social_push 风格一致)"""
    import requests, json

    api_key = _get_ai_key()
    if not api_key:
        raise RuntimeError("DashScope Text Key 未配置")

    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    body = {
        'model': 'qwen-turbo',
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.7,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']


# ── Prompt 模板 ──
SYSTEM_PROMPT = """你是一个专业的内容编辑。你负责：
1. 从原始HTML中提取正文，保留段落结构
2. 用规范Markdown重新排版（## 标题、段落空行、**加粗**关键数据）
3. 每段之间空一行，保持可读性
4. 生成适合本站发布的干净版本

要求：
- 输出完美排版的Markdown，段落分明
- 保留原文关键数据（数字、百分比、日期等）
- 不添加原文没有的信息
- 输出 JSON 格式"""

PROCESS_PROMPT = """请处理以下原始内容，输出JSON：

{{
  "title": "优化后的标题（简洁有力，20字以内）",
  "summary": "一句话摘要（50字以内）",
  "body": "用Markdown重排的正文。每段之间空一行，列表用-开头，数字/百分比用**加粗**。不要用```包裹。",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "risk_level": "low / normal / high / critical"
}}

原始内容：
标题：{title}
作者：{author}
正文原文：
{content}"""


def process_raw_content(raw_id: int, admin_id: int = 1) -> dict:
    """对单条 raw_content 做 AI 加工，返回 processed_content id"""
    with get_db() as conn:
        raw = conn.execute(
            'SELECT * FROM raw_contents WHERE id=?', (raw_id,)
        ).fetchone()
    if not raw:
        return {'success': False, 'error': '内容不存在'}
    if raw['status'] == 'processed':
        return {'success': False, 'error': '已加工过'}

    # 标记 processing
    with get_db() as conn:
        conn.execute(
            "UPDATE raw_contents SET status='processing' WHERE id=?", (raw_id,)
        )
        conn.commit()

    try:
        # 使用 HTML 原文（保留段落结构），若没有则回退到纯文本
        raw_content = (raw['content_html'] or raw['content_text'] or '')[:24000]
        if len(raw.get('content_html') or raw.get('content_text') or '') > 24000:
            logger.warning(f'Content #{raw["id"]} truncated at 24000 chars for AI processing')
        # 提取封面图
        cover_url = ''
        try:
            cj = json.loads(raw['content_json'] or '{}')
            cover_url = cj.get('cover_url', '')
        except:
            pass

        prompt = PROCESS_PROMPT.format(
            title=raw['title'] or '无标题',
            author=raw['author'] or '未知',
            content=raw_content,
        )
        result_text = _call_qwen(prompt)

        # 解析 JSON
        data = json.loads(result_text)

        # 写入 processed_contents
        with get_db() as conn:
            conn.execute(
                """INSERT INTO processed_contents
                   (raw_id, content_type, title, summary, body, keywords,
                    risk_level, status, created_by)
                   VALUES (?, 'article', ?, ?, ?, ?, ?, 'draft', ?)""",
                (raw_id,
                 (data.get('title') or raw['title'])[:200],
                 (data.get('summary') or '')[:500],
                 data.get('body', ''),
                 ','.join(data.get('keywords', [])),
                 data.get('risk_level', 'normal'),
                 admin_id)
            )
            conn.commit()
            pid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            # 保存封面图
            if cover_url:
                conn.execute(
                    "UPDATE processed_contents SET image_url=? WHERE id=?",
                    (cover_url, pid)
                )
                conn.commit()
            # 更新 raw 状态
            conn.execute(
                "UPDATE raw_contents SET status='processed', summary=? WHERE id=?",
                (data.get('summary', ''), raw_id)
            )
            conn.commit()

        return {'success': True, 'processed_id': pid, 'title': data.get('title', '')}

    except json.JSONDecodeError:
        # 尝试修复：Qwen 偶尔输出非纯净 JSON
        try:
            cleaned = result_text.strip()
            if cleaned.startswith('```'):
                cleaned = cleaned.split('\n', 1)[1]
            if cleaned.endswith('```'):
                cleaned = cleaned.rsplit('```', 1)[0]
            data = json.loads(cleaned.strip())
        except:
            # 降级：存为纯文本
            with get_db() as conn:
                conn.execute(
                    "UPDATE raw_contents SET status='failed', error_msg='JSON解析失败' WHERE id=?",
                    (raw_id,)
                )
                conn.commit()
            return {'success': False, 'error': f'AI输出格式异常: {result_text[:200]}', 'raw_output': result_text}

        with get_db() as conn:
            conn.execute(
                """INSERT INTO processed_contents
                   (raw_id, content_type, title, summary, body, keywords,
                    risk_level, status, created_by)
                   VALUES (?, 'article', ?, ?, ?, ?, ?, 'draft', ?)""",
                (raw_id, data.get('title', '')[:200], data.get('summary', '')[:500],
                 data.get('body', ''), ','.join(data.get('keywords', [])),
                 data.get('risk_level', 'normal'), admin_id)
            )
            conn.commit()
            pid = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
            if cover_url:
                conn.execute("UPDATE processed_contents SET image_url=? WHERE id=?", (cover_url, pid))
                conn.commit()
            conn.execute(
                "UPDATE raw_contents SET status='processed', summary=? WHERE id=?",
                (data.get('summary', ''), raw_id)
            )
            conn.commit()
        return {'success': True, 'processed_id': pid}

    except Exception as e:
        logger.exception(f"[CF] AI加工失败 raw_id={raw_id}")
        with get_db() as conn:
            conn.execute(
                "UPDATE raw_contents SET status='failed', error_msg=? WHERE id=?",
                (str(e)[:200], raw_id)
            )
            conn.commit()
        return {'success': False, 'error': str(e)}


def batch_process(raw_ids: list, admin_id: int = 1) -> dict:
    """批量加工，逐条调用"""
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
