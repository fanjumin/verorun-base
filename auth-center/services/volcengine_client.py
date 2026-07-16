#!/usr/bin/env python3
"""
Volcengine (火山引擎) Client — 声音复刻 / TTS / 数字人视频
=========================================================
AK/SK HMAC-SHA256 签名认证，不是 Bearer Token。
"""

import json, time, hashlib, hmac, uuid, logging, requests
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)

# ── Config keys in system_config ──
CFG_ACCESS_KEY = 'volcengine_access_key'
CFG_SECRET_KEY = 'volcengine_secret_key'

# ── API endpoints ──
VOICE_CLONE_URL  = 'https://openspeech.bytedance.com/api/v1/mega_tts/audio'
TTS_STREAM_URL   = 'https://openspeech.bytedance.com/api/v1/tts'
AVATAR_VIDEO_URL = 'https://open.byteplus.com/api/v1/avatar'


def _get_config():
    """从 system_config 表读取火山引擎 AK/SK"""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from models import get_db
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key, value FROM system_config WHERE key IN (%s,%s)",
            (CFG_ACCESS_KEY, CFG_SECRET_KEY)
        ).fetchall()
    cfg = {r['key']: r['value'] for r in rows}
    return cfg


def _sign(method, url, body, access_key, secret_key, service='openspeech', region='cn-north-1'):
    """
    火山引擎 API v4 签名 (HMAC-SHA256)
    参见: https://www.volcengine.com/docs/6561/1354862
    """
    # 解析 URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.hostname
    path = parsed.path
    query = parsed.query

    # Current time
    t = datetime.utcnow()
    timestamp = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')

    # Step 1: Canonical Request
    canonical_headers = f'content-type:application/json\nhost:{host}\nx-date:{timestamp}\n'
    signed_headers = 'content-type;host;x-date'
    payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    canonical_request = f'{method}\n{path}\n{query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'

    # Step 2: String to Sign
    credential_scope = f'{datestamp}/{region}/{service}/request'
    string_to_sign = f'HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'

    # Step 3: Signature
    def _hmac(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    k_date = _hmac(secret_key.encode('utf-8'), datestamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    k_signing = _hmac(k_service, 'request')
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # Authorization header
    auth = (
        f'HMAC-SHA256 Credential={access_key}/{credential_scope}, '
        f'SignedHeaders={signed_headers}, Signature={signature}'
    )
    return {
        'Content-Type': 'application/json',
        'Host': host,
        'X-Date': timestamp,
        'Authorization': auth,
    }


def _post(url, payload, service='openspeech'):
    """发送带签名的 POST 请求"""
    cfg = _get_config()
    ak = cfg.get(CFG_ACCESS_KEY, '')
    sk = cfg.get(CFG_SECRET_KEY, '')
    if not ak or not sk:
        raise ValueError('火山引擎配置不完整，请在系统设置中配置 volcengine_access_key 和 volcengine_secret_key')

    body = json.dumps(payload, ensure_ascii=False)
    headers = _sign('POST', url, body, ak, sk, service=service)
    resp = requests.post(url, data=body, headers=headers, timeout=60)
    data = resp.json()
    logger.info(f'[Volcengine] POST {url} → status={resp.status_code}')
    return data


# ============================================================
# 声音复刻
# ============================================================

def voice_clone(audio_url: str, voice_name: str) -> dict:
    """
    上传声音样本，触发声音复刻。
    audio_url: 音频文件的公网可访问 URL（wav/mp3，16kHz 单声道，10-30s）
    voice_name: 声音名称
    返回: {voice_id, status}
    
    火山引擎 MegaTTS 文档: https://www.volcengine.com/docs/6561/1354862
    """
    payload = {
        'app': {'appid': str(uuid.uuid4())},
        'user': {'uid': 'admin'},
        'audio': {
            'audio_type': 'url',
            'url': audio_url,
        },
        'request': {
            'reqid': str(uuid.uuid4()),
            'operation': 'query',
            'text': '',  # 复刻模式无需 text
            'voice_type': voice_name,
        }
    }
    result = _post(VOICE_CLONE_URL, payload)
    return _parse_clone_result(result)


def _parse_clone_result(result: dict) -> dict:
    """解析声音复刻结果"""
    code = result.get('code', -1)
    if code != 3000:
        msg = result.get('message', '未知错误')
        return {'success': False, 'error': f'声音复刻失败 (code={code}): {msg}'}

    reqid = result.get('reqid', '')
    # 轮询 voice_id — 火山引擎异步返回
    return {'success': True, 'voice_id': '', 'reqid': reqid, 'status': 'processing',
            'message': '声音复刻任务已提交，请稍后查询'}


# ============================================================
# 流式 TTS（文本转语音）
# ============================================================

def tts(text: str, voice_id: str, output_path: str | None = None) -> dict:
    """
    文本转语音，使用已克隆的声音。
    text: 要合成的文本
    voice_id: 声音复刻返回的 voice_id
    output_path: 输出文件路径（可选）
    返回: {success, audio_url|audio_path, duration}
    """
    payload = {
        'app': {'appid': str(uuid.uuid4())},
        'user': {'uid': 'admin'},
        'audio': {
            'voice_type': voice_id,
            'encoding': 'mp3',
            'speed_ratio': 1.0,
        },
        'request': {
            'reqid': str(uuid.uuid4()),
            'text': text,
            'text_type': 'plain',
            'operation': 'query',
        }
    }
    result = _post(TTS_STREAM_URL, payload)
    return _parse_tts_result(result, output_path)


def _parse_tts_result(result: dict, output_path: str | None = None) -> dict:
    code = result.get('code', -1)
    if code != 3000:
        return {'success': False, 'error': f'TTS 失败 (code={code}): {result.get("message","")}'}

    audio_data = result.get('data', '')
    if not audio_data:
        return {'success': False, 'error': 'TTS 返回空音频数据'}

    import base64
    audio_bytes = base64.b64decode(audio_data)

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)
        return {'success': True, 'audio_path': output_path, 'size': len(audio_bytes)}
    return {'success': True, 'audio_data': audio_bytes, 'size': len(audio_bytes)}


# ============================================================
# 照片驱动数字人 — 口播视频
# ============================================================

def avatar_video(text: str, voice_id: str, image_url: str,
                 background_color: str = '#00ff00') -> dict:
    """
    生成数字人口播视频。
    text: 口播文案
    voice_id: 声音 ID
    image_url: 数字人形象照片 URL
    background_color: 背景色（用于绿幕抠图时用 #000000）
    返回: {success, task_id}
    
    火山引擎数字人文档: https://www.volcengine.com/docs/6561/1329500
    """
    payload = {
        'user': {'uid': str(uuid.uuid4())},
        'request': {
            'req_key': 'avatar_video',
            'binary_data_base64': [],
            'image_url': image_url,
            'text': text,
            'voice_type': voice_id,
            'background_color': background_color,
            'video_format': 'mp4',
            'resolution': '1080p',
        }
    }

    result = _post(AVATAR_VIDEO_URL, payload, service='byteplus')
    return _parse_avatar_result(result)


def _parse_avatar_result(result: dict) -> dict:
    code = result.get('code', -1)
    if code != 10000:
        return {'success': False, 'error': f'数字人视频生成失败 (code={code}): {result.get("message","")}'}

    data = result.get('data', {})
    task_id = data.get('task_id', '')
    return {'success': True, 'task_id': task_id, 'status': 'processing',
            'message': '视频生成任务已提交'}


def query_avatar_task(task_id: str) -> dict:
    """
    查询数字人视频任务状态。
    返回: {success, status, video_url, error}
    status: processing / done / failed
    """
    payload = {
        'user': {'uid': str(uuid.uuid4())},
        'request': {
            'req_key': 'avatar_video_query',
            'task_id': task_id,
        }
    }
    result = _post(AVATAR_VIDEO_URL, payload, service='byteplus')
    code = result.get('code', -1)
    if code != 10000:
        return {'success': False, 'status': 'failed',
                'error': f'查询失败 (code={code}): {result.get("message","")}'}

    data = result.get('data', {})
    status = data.get('status', 'processing')
    video_url = data.get('video_url', '')
    return {'success': True, 'status': status, 'video_url': video_url}
