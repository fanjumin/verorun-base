#!/usr/bin/env python3
"""AI Content Generator — text via DashScope Qwen, image via 通义万相.
   Two separate API keys stored in system_config.
   Free tier: qwen-turbo (100万 tokens/月), wanx2.1-t2i-turbo.
"""

import logging, json, os, requests, time, ipaddress, socket
from urllib.parse import urlparse
from models import get_db

logger = logging.getLogger(__name__)

DASHSCOPE_BASE = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

# =============================================
# Config helpers
# =============================================

def _get_key(key_name):
    """Read a specific API key from system_config."""
    with get_db() as conn:
        row = conn.execute("SELECT value FROM system_config WHERE key=%s", (key_name,)).fetchone()
    if row and row['value']:
        return row['value']
    return ''


# =============================================
# 文案生成 — DashScope Qwen
# =============================================

def _qwen_chat(messages, model='qwen-turbo', temperature=0.7):
    """Call Qwen via LLMGateway (unified entry with token logging)."""
    from agent_matrix.engine import get_gateway
    gw = get_gateway()
    resp = gw.chat(
        provider='dashscope',
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=4096,
        module='content_generator',
    )
    return resp.choices[0].message.content


CONTENT_PROMPTS = {
    'article': '''请帮我写一篇微信公众号文章，主题是：{topic}

要求：
1. 标题：吸引眼球，20字以内
2. 正文：800-1500字，段落清晰
3. 摘要：100字以内的文章摘要
4. 风格：专业但易懂

输出格式：
---
标题：【标题】
摘要：【摘要】
正文：
【正文内容】
---''',

    'weibo': '''请帮我写一条微博，内容是：{topic}

要求：
1. 正文：140字以内，简洁有力
2. 可以带1-2个话题标签
3. 风格：轻松有趣

输出格式：
---
正文：
【微博正文】
---''',

    'toutiao': '''请帮我写一篇今日头条文章，主题是：{topic}

要求：
1. 标题：吸引点击，30字以内
2. 正文：500-1000字，信息密度高
3. 风格：资讯类，客观

输出格式：
---
标题：【标题】
正文：
【正文内容】
---''',

    'announcement': '''请帮我写一则通知，内容是：{topic}

输出格式：
---
标题：【标题】
正文：
【正文内容】
---''',

    'promotion': '''请帮我写一则推广文案，内容是：{topic}

输出格式：
---
标题：【标题】
摘要：【摘要】
正文：
【正文内容】
---''',
}


def generate_article(topic, content_type='article', temperature=0.7):
    """Generate content using DashScope Qwen. Returns {title, summary, body, body_html}."""
    prompt_template = CONTENT_PROMPTS.get(content_type, CONTENT_PROMPTS['article'])
    prompt = prompt_template.replace('{topic}', topic)

    messages = [
        {'role': 'system', 'content': '你是一个专业的中文内容创作者。'},
        {'role': 'user', 'content': prompt},
    ]

    result = _qwen_chat(messages, temperature=temperature)
    return _parse_output(result, content_type)


def _parse_output(text, content_type='article'):
    """Parse AI output into structured fields."""
    title = ''
    summary = ''
    body = ''
    body_lines = []
    current_section = None

    for line in text.strip().split('\n'):
        stripped = line.strip()
        if stripped.startswith('标题：') or stripped.startswith('标题:'):
            title = stripped.split('：', 1)[-1] if '：' in stripped else stripped.split(':', 1)[-1]
            title = title.strip('【】').strip()
        elif stripped.startswith('摘要：') or stripped.startswith('摘要:'):
            summary = stripped.split('：', 1)[-1] if '：' in stripped else stripped.split(':', 1)[-1]
            summary = summary.strip('【】').strip()
        elif stripped.startswith('正文：') or stripped.startswith('正文:'):
            current_section = 'body'
        elif stripped.startswith('---'):
            continue
        elif current_section == 'body':
            body_lines.append(stripped)

    body = '\n'.join(body_lines).strip()
    if not title and not body:
        for line in text.strip().split('\n'):
            if line.strip() and not line.strip().startswith('---'):
                title = line.strip()
                break
        body = text

    if content_type == 'weibo':
        return {
            'title': title or '微博',
            'summary': summary or body[:100],
            'body': body,
            'body_html': body,
        }

    body_html = ''
    for para in body.split('\n'):
        para = para.strip()
        if para:
            body_html += f'<p>{para}</p>\n'

    return {
        'title': title or '未命名',
        'summary': summary or title[:100],
        'body': body,
        'body_html': body_html or body,
    }


# =============================================
# 配图生成 — Wan2.7-Image (DashScope Async API)
# =============================================

WANX_URL = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/image-generation/generation'
TASK_URL = 'https://dashscope.aliyuncs.com/api/v1/tasks'


def _get_image_key():
    """Get image generation API key from system_config."""
    key = _get_key('dashscope_api_key')
    if not key:
        raise ValueError('通义万相 Key 未配置，请在系统设置中配置')
    return key


def generate_image(prompt, size='1024x1024', reference_image_url=None):
    """Generate image via wan2.7-image (async API). Supports style_ref(img2img)."""
    api_key = _get_image_key()
    size_map = {'1024x1024': '1024*1024', '1280x720': '1280*720', '720x1280': '720*1280'}
    ds_size = size_map.get(size, '1024*1024')

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'X-DashScope-Async': 'enable',
    }

    body = {
        'model': 'wan2.7-image-pro',
        'input': {
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                    ],
                }
            ],
        },
        'parameters': {'size': ds_size, 'n': 1},
    }

    # 图生图：通过 style_ref 参数传入参考图
    if reference_image_url:
        body['parameters']['style_ref'] = reference_image_url

    # Submit async task
    resp = requests.post(WANX_URL, headers=headers, json=body, timeout=30)
    result = resp.json()

    task_id = result.get('output', {}).get('task_id', '')
    if not task_id:
        raise ValueError(f'图片生成提交失败: {result.get("message", str(result))}')

    # Poll for result
    poll_headers = {'Authorization': f'Bearer {api_key}'}
    for i in range(30):
        time.sleep(2)
        poll = requests.get(f'{TASK_URL}/{task_id}', headers=poll_headers, timeout=15)
        sr = poll.json()
        status = sr.get('output', {}).get('task_status', '')
        logger.info(f'  图片生成 poll {i+1}: {status}')

        if status == 'SUCCEEDED':
            # DashScope v3 response: output.choices[0].message.content[0].image
            choices = sr.get('output', {}).get('choices', [])
            if choices:
                content = choices[0].get('message', {}).get('content', [])
                if (
                    isinstance(content, list) and len(content) > 0
                    and isinstance(content[0], dict)
                    and content[0].get('image')
                ):
                    return content[0]['image']
                # Also try flat text URL inside content
                if isinstance(content, list) and len(content) > 0:
                    text = content[0].get('text', '')
                    if text and text.startswith('http'):
                        return text
            # Fallback: old API format (output.results[0].url)
            results = sr.get('output', {}).get('results', [])
            if results and results[0].get('url'):
                return results[0]['url']
            # Fallback: b64_json
            if results and results[0].get('b64_json'):
                import base64
                img_data = base64.b64decode(results[0]['b64_json'])
                local_path = f'/tmp/gen_img_{task_id[:8]}.png'
                with open(local_path, 'wb') as f:
                    f.write(img_data)
                logger.info(f'Image saved to {local_path}')
                return f'file://{local_path}'
            logger.error(f'图片生成成功但无法解析响应: {json.dumps(sr.get("output", {}), ensure_ascii=False)[:500]}')
            raise ValueError('图片生成成功但无法解析响应URL')

        elif status in ('FAILED',):
            err_msg = sr.get('output', {}).get('message', status)
            # Check for partial results with error (legacy format)
            results = sr.get('output', {}).get('results', [])
            if results and results[0].get('url'):
                return results[0]['url']
            # Check new format for partial results
            choices = sr.get('output', {}).get('choices', [])
            if choices:
                content = choices[0].get('message', {}).get('content', [])
                if isinstance(content, list) and len(content) > 0:
                    img_url = content[0].get('image', '')
                    if img_url:
                        return img_url
            raise ValueError(f'图片生成失败: {err_msg}')

    raise ValueError('图片生成超时')


def generate_cover_image(title, topic=''):
    """Generate cover image for article."""
    prompt = f'公众号封面：{topic or title}，简约设计'
    return generate_image(prompt, size='1280x720')


def _validate_image_url(image_url):
    """校验图片 URL，防止 SSRF 攻击。只允许 http/https 公网地址。"""
    parsed = urlparse(image_url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f'不支持的 URL 协议: {parsed.scheme}')
    hostname = parsed.hostname
    if not hostname:
        raise ValueError('无效的 URL 主机名')
    # 禁止内网地址
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
    except Exception:
        raise ValueError(f'无法解析主机名: {hostname}')
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        raise ValueError(f'禁止访问内网地址: {hostname}')
    if ip.is_multicast or ip.is_reserved:
        raise ValueError(f'禁止访问保留地址: {hostname}')

def download_image_to_file(image_url, filepath):
    """Download image URL to local file."""
    _validate_image_url(image_url)
    resp = requests.get(image_url, timeout=60)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(resp.content)
    return filepath


def analyze_image(image_url, question='请详细描述这张图片的内容、布局、颜色和文字信息'):
    """Use Qwen3-V to analyze an image. Returns analysis text."""
    _validate_image_url(image_url)
    api_key = _get_key('dashscope_text_key')
    if not api_key:
        raise ValueError('dashscope_text_key 未配置')

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    body = {
        'model': 'qwen-vl-max',
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': question},
                    {'type': 'image_url', 'image_url': {'url': image_url}},
                ]
            }
        ],
        'max_tokens': 2048,
    }
    resp = requests.post(
        f'{DASHSCOPE_BASE}/chat/completions',
        headers=headers, json=body, timeout=60
    )
    result = resp.json()
    choices = result.get('choices', [])
    if choices and choices[0].get('message', {}).get('content'):
        return choices[0]['message']['content']
    raise ValueError(f'Qwen3-V 调用失败: {result.get("message", str(result))}')
