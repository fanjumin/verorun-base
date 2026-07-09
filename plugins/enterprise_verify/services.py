#!/usr/bin/env python3
"""Enterprise Verification Plugin — OCR 识别 + AI 自动审核"""
import sys, os, json, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'auth-center'))

SILICONFLOW_BASE_URL = 'https://api.siliconflow.cn/v1'
DEFAULT_OCR_MODEL = 'deepseek-ai/DeepSeek-OCR'
DEFAULT_AUDIT_MODEL = 'deepseek-ai/DeepSeek-V3'


def _get_config(key: str, default=''):
    """从主系统 system_config 表读取配置"""
    try:
        from models import get_db
        with get_db() as conn:
            row = conn.execute("SELECT value FROM system_config WHERE key=?", (key,)).fetchone()
            return row['value'] if row else default
    except Exception:
        return default


def _get_siliconflow_api_key() -> str:
    """获取硅基流动 API Key"""
    key = _get_config('siliconflow_api_key', '')
    if not key:
        key = os.environ.get('SILICONFLOW_API_KEY', '')
    return key


def ocr_business_license(image_base64: str) -> dict:
    """
    调用硅基流动 DeepSeek-OCR 识别营业执照
    返回: {company_name, reg_num, address, legal_person, registered_capital, business_scope}
    """
    api_key = _get_siliconflow_api_key()
    if not api_key:
        raise RuntimeError('硅基流动 API Key 未配置（system_config.siliconflow_api_key）')

    if ',' in image_base64:
        image_base64 = image_base64.split(',', 1)[1]

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=SILICONFLOW_BASE_URL)

    resp = client.chat.completions.create(
        model=DEFAULT_OCR_MODEL,
        messages=[{
            'role': 'user',
            'content': [
                {
                    'type': 'image_url',
                    'image_url': {
                        'url': f'data:image/jpeg;base64,{image_base64}',
                        'detail': 'high',
                    }
                },
                {
                    'type': 'text',
                    'text': (
                        '<image>\n'
                        '<|grounding|>Extract all text from this business license image. '
                        'Return ONLY valid JSON with these exact fields:\n'
                        '{\n'
                        '  "company_name": "企业名称/Company Name",\n'
                        '  "reg_num": "统一社会信用代码/Unified Social Credit Code (18 digits)",\n'
                        '  "legal_person": "法定代表人/Legal Representative",\n'
                        '  "address": "企业地址/Registered Address",\n'
                        '  "registered_capital": "注册资本/Registered Capital",\n'
                        '  "business_scope": "经营范围/Business Scope"\n'
                        '}\n'
                        'Fill empty string for any field not found. MUST output pure JSON.'
                    ),
                }
            ],
        }],
        temperature=0.1,
        max_tokens=2048,
    )

    text = resp.choices[0].message.content.strip()
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        result = json.loads(json_match.group())
    else:
        result = json.loads(text)

    fields = ['company_name', 'reg_num', 'legal_person', 'address', 'registered_capital', 'business_scope']
    for f in fields:
        result.setdefault(f, '')

    return result


def _validate_tax_id(tax_id: str) -> bool:
    """简单校验统一社会信用代码格式（18位字母数字）"""
    if not tax_id:
        return False
    tax_id = tax_id.strip().upper()
    return bool(re.match(r'^[0-9A-HJ-NPQRTUWXY]{18}$', tax_id))


def auto_audit(company_name: str, tax_id: str) -> dict:
    """
    AI 自动审核企业认证
    返回: {decision: 'approve'|'pending', confidence: float, reason: str}
    """
    if not company_name or not tax_id:
        return {'decision': 'pending', 'confidence': 0.0, 'reason': '企业名称或税号为空'}

    if not _validate_tax_id(tax_id):
        return {'decision': 'pending', 'confidence': 0.0, 'reason': '统一社会信用代码格式不正确'}

    api_key = _get_siliconflow_api_key()
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=SILICONFLOW_BASE_URL)
            resp = client.chat.completions.create(
                model=DEFAULT_AUDIT_MODEL,
                messages=[
                    {'role': 'system', 'content': '你是一个企业认证审核助手。判断企业名称和统一社会信用代码是否基本匹配。返回JSON: {"decision": "approve"|"pending", "confidence": 0-1, "reason": "简要说明"}'},
                    {'role': 'user', 'content': f'企业名称: {company_name}\n统一社会信用代码: {tax_id}\n请判断是否通过:'}
                ],
                temperature=0.1,
                max_tokens=512,
                response_format={'type': 'json_object'},
            )
            text = resp.choices[0].message.content.strip()
            result = json.loads(text)
            confidence = result.get('confidence', 0.0)
            if confidence >= 0.8 and result.get('decision') == 'approve':
                return {'decision': 'approve', 'confidence': confidence, 'reason': result.get('reason', 'AI 审核通过')}
            return {'decision': 'pending', 'confidence': confidence, 'reason': result.get('reason', 'AI 审核不确定，需人工复核')}
        except Exception:
            pass

    return {'decision': 'approve', 'confidence': 0.85, 'reason': '格式校验通过，已自动认证'}