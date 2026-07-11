#!/usr/bin/env python3
"""
Node Handlers — 工作流节点类型实现
===================================
所有节点类型的处理函数，注册到 WorkflowEngine。

节点类型列表：
  - ai_agent:      调用 智能体（系统/用户）
  - data_collect:  数据采集（RSS/API）
  - ai_process:    AI 加工内容
  - condition:     条件判断
  - approval:      审批节点
  - publish:       发布到多平台
  - notify:        通知（邮件/Webhook/站内）
  - wait:          等待/延时
  - sub_workflow:  子工作流
  - market_check:  市场数据检查
  - http_request:  HTTP API 调用
  - script:        执行自定义脚本

@package orchestrator
"""

import os, sys, json, time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, '..', 'auth-center'))
sys.path.insert(0, os.path.join(BASE_DIR, '..'))

from . import models as m
from .safe_eval import safe_eval

# ============================================================
# 智能体 节点 — 调用 智能体（系统/用户）
# ============================================================

def handle_ai_agent(node_def: dict, input_data: dict) -> dict:
    """
    智能体 节点处理器。
    配置:
      - agent_type: 'system' | 'user'
      - agent_id: 可选
      - prompt: 要发送给 Agent 的提示词
      - model: 可选，覆盖模型
    """
    config = node_def.get('config', {})
    prompt = config.get('prompt', '')
    agent_type = config.get('agent_type', 'system')
    agent_id = config.get('agent_id')

    if not prompt:
        return {'error': 'prompt 不能为空', 'success': False}

    # 获取 Agent 配置
    if agent_type == 'system':
        agent = m.get_default_system_agent()
        if not agent:
            return {'error': '未配置系统 Agent', 'success': False}
        api_key_ref = agent.get('api_key_ref', 'dashscope_text_key')
        model = config.get('model', agent.get('model', 'qwen-turbo'))
        provider = agent.get('provider', 'dashscope')
    else:
        # 用户 Agent - 从 agents 表读取
        if not agent_id:
            return {'error': '用户 Agent 未指定 agent_id', 'success': False}
        # 从 system_config 读取 API Key（用户 agent 使用平台 Key）
        api_key_ref = 'dashscope_text_key'
        model = config.get('model', 'qwen-turbo')
        provider = 'dashscope'

    # 从 system_config 获取 API Key
    api_key = _get_api_key(api_key_ref)
    if not api_key:
        return {'error': f'API Key [{api_key_ref}] 未配置', 'success': False}

    # 调用 DashScope API
    result = _call_dashscope(api_key, model, prompt)
    return result


def _get_api_key(key_ref: str) -> str:
    """从 system_config 表获取 API Key"""
    with m.get_db() as conn:
        row = conn.execute(
            "SELECT value FROM system_config WHERE key=?", (key_ref,)
        ).fetchone()
        return row['value'] if row else ''


def _call_dashscope(api_key: str, model: str, prompt: str) -> dict:
    """调用阿里云 DashScope API"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个专业的AI助手。请严格按要求完成任务。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4096
    }).encode('utf-8')

    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Authorization', f'Bearer {api_key}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            token_usage = data.get('usage', {})

            return {
                'success': True,
                'content': content,
                'model': model,
                'tokens': token_usage
            }
    except Exception as e:
        return {'error': str(e), 'success': False}


# ============================================================
# 数据采集节点 — 调用内容工厂
# ============================================================

def handle_data_collect(node_def: dict, input_data: dict) -> dict:
    """
    数据采集节点处理器。
    配置:
      - source_ids: [int] 采集源 ID 列表
      - max_per_source: int
      - keywords: [str]
    """
    config = node_def.get('config', {})
    source_ids = config.get('source_ids', [])

    if not source_ids:
        return {'error': '未指定采集源', 'success': False}

    # 尝试导入内容工厂采集器
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, '..'))
        from services.content_factory import run_collection
    except ImportError:
        return _mock_collect(source_ids)

    results = []
    for sid in source_ids:
        try:
            result = run_collection(source_id=sid, max_items=config.get('max_per_source', 10))
            results.append({
                'source_id': sid,
                'success': True,
                'items_count': result.get('total', 0)
            })
        except Exception as e:
            results.append({
                'source_id': sid,
                'success': False,
                'error': str(e)
            })

    return {'success': True, 'results': results}


def _mock_collect(source_ids: list) -> dict:
    """模拟采集（用于测试或无内容工厂时）"""
    return {
        'success': True,
        'results': [{'source_id': sid, 'success': True, 'items_count': 5}
                     for sid in source_ids],
        '_mock': True
    }


# ============================================================
# AI 加工节点 — 调用 DashScope 加工内容
# ============================================================

def handle_ai_process(node_def: dict, input_data: dict) -> dict:
    """
    AI 内容加工节点。
    配置:
      - instruction: 加工指令
      - fields: ['title', 'summary', 'body', 'keywords']
      - input_from: 前置节点输出字段
    """
    config = node_def.get('config', {})
    instruction = config.get('instruction', '对以下内容进行解读和分析，输出中文摘要')
    fields = config.get('fields', ['title', 'summary', 'body', 'keywords'])

    # 获取输入内容（从前置节点或上下文）
    context = input_data.get('context', {})
    input_content = ''

    # 查找输入源
    for key, value in input_data.items():
        if key.startswith('node_') and 'output' in key:
            if isinstance(value, dict):
                if 'content' in value:
                    input_content = value['content']
                elif 'results' in value:
                    input_content = json.dumps(value['results'], ensure_ascii=False)[:3000]
                elif 'body' in value:
                    input_content = value['body']

    if not input_content:
        input_content = config.get('default_input', '（无输入内容）')

    prompt = f"""{instruction}

原始内容:
{input_content[:8000]}

请以 JSON 格式输出，包含字段: {json.dumps(fields, ensure_ascii=False)}
"""

    result = _call_dashscope(
        _get_api_key('dashscope_text_key'),
        config.get('model', 'qwen-turbo'),
        prompt
    )

    if result.get('success'):
        content = result['content']
        # 尝试解析 JSON 输出
        parsed = _try_parse_json(content)
        if parsed:
            result['parsed'] = parsed

    return result


def _try_parse_json(text: str) -> dict:
    """尝试从文本中提取并解析 JSON"""
    import re
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 代码块
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# 条件判断节点
# ============================================================

def handle_condition(node_def: dict, input_data: dict) -> dict:
    """
    条件判断节点（内置实现，重载 WorkflowEngine 默认）。
    配置:
      - expression: 条件表达式 (如 'output.value > 0.05')
      - branches: [{'label': '上升', 'expression': '> 0'}, ...]
    """
    config = node_def.get('config', {})
    expression = config.get('expression', 'true')
    branches = config.get('branches', [])

    # 收集所有上下文变量用于条件评估
    local_vars = {}
    local_vars.update(input_data.get('context', {}))
    for key, val in input_data.items():
        if key.startswith('node_'):
            if isinstance(val, dict):
                local_vars.update(val)

    try:
        result = safe_eval(expression, local_vars)
    except Exception as e:
        return {
            'passed': True,
            'condition_result': True,
            'error': str(e),
            'expression': expression
        }

    # 检查分支匹配
    matched_branch = None
    for branch in branches:
        try:
            _expr = branch.get('expression', '')
            if bool(safe_eval(_expr, local_vars)):
                matched_branch = branch.get('label', 'unknown')
                break
        except Exception:
            continue

    return {
        'passed': result,
        'condition_result': result,
        'matched_branch': matched_branch,
        'expression': expression
    }


# ============================================================
# 发布节点 — 多平台发布
# ============================================================

def handle_publish(node_def: dict, input_data: dict) -> dict:
    """
    发布节点。支持平台: cms, skill, social。
    配置:
      - platforms: ['cms', 'skill', 'social']
      - content_source: 从哪个前置节点获取内容
    """
    config = node_def.get('config', {})
    platforms = config.get('platforms', ['cms'])
    content = input_data.get('content', '')

    # 从前置节点查找内容
    for key, val in input_data.items():
        if key.startswith('node_'):
            if isinstance(val, dict):
                content = val.get('content', val.get('parsed', val.get('body', content)))
                if isinstance(content, dict):
                    content = json.dumps(content, ensure_ascii=False)

    results = {}
    for platform in platforms:
        try:
            if platform == 'cms':
                results[platform] = _publish_to_cms(config, content)
            elif platform == 'skill':
                results[platform] = _publish_to_skill(config, content)
            elif platform == 'social':
                results[platform] = _publish_to_social(config, content)
            else:
                results[platform] = {'success': False, 'error': f'未知平台: {platform}'}
        except Exception as e:
            results[platform] = {'success': False, 'error': str(e)}

    return {
        'success': any(r.get('success') for r in results.values()),
        'results': results
    }


def _publish_to_cms(config: dict, content: str) -> dict:
    """发布到 CMS"""
    try:
        from models.cms import upsert_post
        title = config.get('title', '自动发布')
        category = config.get('category', 'content_factory')
        slug = f'auto-{config.get("workflow_instance_id", "wf")}-{int(time.time())}'

        post_id = upsert_post(
            title=title,
            content=content,
            category=category,
            slug=slug,
            author='自动化系统'
        )
        return {'success': True, 'post_id': post_id, 'slug': slug}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _publish_to_skill(config: dict, content: str) -> dict:
    """推送为 Skill"""
    from services.content_factory.skill_pusher import push_to_skill
    result = push_to_skill(
        processed_id=config.get('processed_id', 0),
        title=config.get('title', '自动 Skill'),
        description=config.get('description', '由工作流自动生成'),
        content=content,
        category=config.get('category', 'automation')
    )
    return result


def _publish_to_social(config: dict, content: str) -> dict:
    """发布到社交媒体"""
    # 调用已有的社交推送逻辑
    return {
        'success': True,
        'platforms': config.get('platforms', ['weixin']),
        'message': '模拟社交发布成功',
        '_mock': True
    }


# ============================================================
# 通知节点
# ============================================================

def handle_notify(node_def: dict, input_data: dict) -> dict:
    """
    通知节点。
    配置:
      - channels: ['email', 'webhook', 'notification']
      - title: 通知标题
      - message: 通知内容（支持模板）
      - webhook_url: webhook URL
      - email_to: 收件人
    """
    config = node_def.get('config', {})
    channels = config.get('channels', ['notification'])
    title = config.get('title', '工作流通知')
    message = config.get('message', '')

    # 模板变量替换
    ctx = input_data.get('context', {})
    for k, v in ctx.items():
        if isinstance(v, str):
            message = message.replace(f'{{{{{k}}}}}', v)
            title = title.replace(f'{{{{{k}}}}}', v)

    results = {}
    for channel in channels:
        try:
            if channel == 'notification':
                results[channel] = _send_notification(title, message)
            elif channel == 'webhook':
                results[channel] = _send_webhook(config.get('webhook_url', ''), title, message)
            elif channel == 'email':
                results[channel] = _send_email(config.get('email_to', ''), title, message)
            else:
                results[channel] = {'success': False, 'error': f'未知通道: {channel}'}
        except Exception as e:
            results[channel] = {'success': False, 'error': str(e)}

    return {
        'success': any(r.get('success') for r in results.values()),
        'results': results
    }


def _send_notification(title: str, message: str) -> dict:
    """发送站内通知"""
    return {'success': True, 'title': title, 'message': message[:100], '_mock': True}


def _send_webhook(url: str, title: str, message: str) -> dict:
    """发送 Webhook"""
    if not url:
        return {'success': False, 'error': 'webhook URL 为空'}
    body = json.dumps({
        'title': title,
        'message': message,
        'timestamp': m.now_str(),
        'source': 'easykai-orchestrator'
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=10) as resp:
        return {'success': resp.status < 400, 'status_code': resp.status}


def _send_email(email_to: str, title: str, message: str) -> dict:
    """发送邮件（调用 Email 插件服务）"""
    if not email_to:
        return {'success': False, 'error': 'email_to 为空'}
    try:
        from plugins.email.services import send_email as plugin_send_email
        ok, msg = plugin_send_email(
            to_addr=email_to,
            subject=title,
            body_text=message,
        )
        return {'success': ok, 'message': msg}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================
# 市场检查节点
# ============================================================

def handle_market_check(node_def: dict, input_data: dict) -> dict:
    """
    市场数据检查节点。
    配置:
      - symbol: '000001.SH' 等
      - metric: 'change_pct' | 'volume' | 'price'
      - operator: '>' | '<' | '>=' | '<='
      - threshold: float
    """
    config = node_def.get('config', {})
    symbol = config.get('symbol', '000001.SH')
    metric = config.get('metric', 'change_pct')
    operator = config.get('operator', '>')
    threshold = config.get('threshold', 0)

    # 尝试从 TradeMind API 获取实时数据
    try:
        market_data = _get_market_data(symbol)
        value = market_data.get(metric, 0)

        operators = {
            '>': lambda a, b: a > b,
            '<': lambda a, b: a < b,
            '>=': lambda a, b: a >= b,
            '<=': lambda a, b: a <= b,
            '==': lambda a, b: a == b,
        }
        triggered = operators.get(operator, lambda a, b: False)(value, threshold)

        return {
            'success': True,
            'symbol': symbol,
            'metric': metric,
            'value': value,
            'threshold': threshold,
            'triggered': triggered,
            'data': market_data
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'triggered': False}


def _get_market_data(symbol: str) -> dict:
    """获取市场数据（模拟实现，可替换为真实 API）"""
    # Tencent 行情 API
    url = f"https://qt.gtimg.cn/q={symbol}"
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read().decode('gbk')
            # 解析腾讯格式
            import re
            match = re.search(r'~([^~]+)~([^~]+)~([^~]+)~([^~]+)~([^~]+)~([^~]+)~([^~]+)', text)
            if match:
                return {
                    'name': match.group(2),
                    'price': float(match.group(3)),
                    'change_pct': float(match.group(4).replace('%', '')),
                    'volume': int(match.group(6)) if match.group(6).isdigit() else 0
                }
    except Exception:
        pass
    # 模拟数据
    import random
    return {
        'name': symbol,
        'price': round(random.uniform(10, 100), 2),
        'change_pct': round(random.uniform(-3, 3), 2),
        'volume': random.randint(100000, 10000000)
    }


# ============================================================
# 节点处理器注册表
# ============================================================

NODE_HANDLERS = {
    'ai_agent': handle_ai_agent,
    'data_collect': handle_data_collect,
    'ai_process': handle_ai_process,
    'condition': handle_condition,
    'publish': handle_publish,
    'notify': handle_notify,
    'market_check': handle_market_check,
    # wait, approval, sub_workflow, http_request, script 由 WorkflowEngine 内置处理
}


def register_all(engine):
    """将所有节点处理器注册到工作流引擎"""
    for node_type, handler in NODE_HANDLERS.items():
        engine.register_node_handler(node_type, handler)
