#!/usr/bin/env python3
"""
快递鸟 (Kdniao) 物流查询 API 客户端

功能：
1. 即时查询物流轨迹 (RequestType=8001)
2. 支持 600+ 快递公司自动识别
3. 支持从系统配置表读取商户 ID 和 API Key

对接文档：https://www.kdniao.com/api-monitor
"""

import hashlib
import json
import base64
import logging
import os
from typing import Dict, Any, List, Tuple, Optional
from urllib import request, parse

logger = logging.getLogger(__name__)

# ── 默认配置（环境变量兜底）──
KDNIAO_EBUSINESS_ID = os.environ.get('KDNIAO_EBUSINESS_ID', '')
KDNIAO_API_KEY = os.environ.get('KDNIAO_API_KEY', '')
KDNIAO_API_URL = os.environ.get('KDNIAO_API_URL',
    'https://api.kdniao.com/api/dist')


def get_kdniao_config_from_db(site_domain: str = '') -> Tuple[str, str]:
    """
    从 oauth_providers 表按站点域名读取快递鸟商户配置。

    流程：
      1. 从 oauth_providers WHERE provider='kdniao' AND site_domain=?
         → client_key = EID, client_secret = API Key
      2. 没找到 → 环境变量兜底

    Returns:
        (eid, api_key)
    """
    try:
        from models import get_db
        with get_db() as conn:
            # 优先按域名查
            if site_domain:
                row = conn.execute(
                    "SELECT client_key, client_secret FROM oauth_providers "
                    "WHERE site_domain=? AND provider='kdniao' AND is_active=1",
                    (site_domain,)
                ).fetchone()
                if row and row['client_key'] and row['client_secret']:
                    return row['client_key'], row['client_secret']

            # 没有域名配置 → 全局兜底
            rows = conn.execute(
                "SELECT key, value FROM system_config WHERE key IN ('kdniao_eid', 'kdniao_api_key')"
            ).fetchall()
        cfg = {r['key']: r['value'] for r in rows}
        eid = cfg.get('kdniao_eid', '').strip() or KDNIAO_EBUSINESS_ID
        api_key = cfg.get('kdniao_api_key', '').strip() or KDNIAO_API_KEY
        return eid, api_key
    except Exception:
        return KDNIAO_EBUSINESS_ID, KDNIAO_API_KEY


def _generate_data_sign(request_data: str, api_key: str) -> str:
    """
    生成 DataSign: Base64(MD5(RequestData + ApiKey))
    """
    raw = request_data + api_key
    md5 = hashlib.md5(raw.encode('utf-8')).hexdigest()
    return base64.b64encode(md5.encode('utf-8')).decode('utf-8')


def query_track(shipper_code: str, logistic_code: str,
                order_code: str = '', customer_name: str = '',
                eid: str = '', api_key: str = '') -> Tuple[bool, Dict[str, Any], str]:
    """
    查询物流轨迹（快递鸟在途监控即时查询, RequestType=8001）

    Args:
        shipper_code: 快递公司编码 (如 SF, YTO, ZTO)
        logistic_code: 快递单号
        order_code: 订单号 (可选)
        customer_name: 顺丰必填(收/寄件人手机号后4位), 其他可空
        eid: 快递鸟商户ID（为空则从 DB 或环境变量读取）
        api_key: 快递鸟 API Key（为空则从 DB 或环境变量读取）

    Returns:
        (success, data, error_message)
    """
    # 优先使用传入参数，其次从 DB 读取，最后回退环境变量
    if not eid or not api_key:
        eid_from_db, api_key_from_db = get_kdniao_config_from_db()
        eid = eid or eid_from_db
        api_key = api_key or api_key_from_db

    if not eid or not api_key:
        return False, {}, ('快递鸟未配置: 请在「系统设置→基本设置→物流配送（快递鸟）」'
                           '中填写商户ID和API Key')

    # 组装业务参数
    req_body = {
        'OrderCode': order_code,
        'ShipperCode': shipper_code,
        'LogisticCode': logistic_code,
    }
    # 顺丰需要 CustomerName（手机号后4位）
    if customer_name:
        req_body['CustomerName'] = customer_name

    request_data = json.dumps(req_body, ensure_ascii=False, separators=(',', ':'))
    data_sign = _generate_data_sign(request_data, api_key)

    post_data = parse.urlencode({
        'RequestType': '8001',
        'EBusinessID': eid,
        'RequestData': request_data,
        'DataSign': data_sign,
        'DataType': '2',
    }).encode('utf-8')

    try:
        req = request.Request(KDNIAO_API_URL, data=post_data, method='POST')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded;charset=utf-8')

        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            result = json.loads(body)

            if result.get('Success'):
                traces = result.get('Traces', [])
                formatted_traces = []
                for t in traces:
                    formatted_traces.append({
                        'time': t.get('AcceptTime', ''),
                        'station': t.get('AcceptStation', ''),
                        'remark': t.get('Remark', ''),
                    })
                formatted_traces.sort(key=lambda x: x['time'], reverse=True)

                data = {
                    'shipper_code': shipper_code,
                    'logistic_code': logistic_code,
                    'traces': formatted_traces,
                    'state': int(result.get('State', 0)),
                    'state_text': _state_text(str(result.get('State', '0'))),
                    'state_ex': result.get('StateEx', ''),
                    'location': result.get('Location', ''),
                }
                return True, data, ''
            else:
                reason = result.get('Reason', '查询失败')
                return False, {}, f'快递鸟查询失败: {reason}'

    except json.JSONDecodeError as e:
        return False, {}, f'解析响应失败: {e}'
    except Exception as e:
        return False, {}, f'网络请求失败: {e}'


def _state_text(state: str) -> str:
    """物流状态文字 (在途监控状态码)"""
    state_map = {
        '0': '无轨迹',
        '1': '已揽收',
        '2': '在途中',
        '3': '签收',
        '4': '问题件',
        '5': '转寄',
        '6': '退签',
        '7': '待清关',
        '8': '清关中',
        '9': '已拒收',
        '10': '待交付',
        '11': '已交付',
        '14': '退货中',
    }
    return state_map.get(state, f'未知({state})')


def get_shipping_status_text(shipping_status: str) -> str:
    """订单发货状态文字"""
    status_map = {
        'pending': '待发货',
        'shipped': '已发货',
        'delivered': '已签收',
    }
    return status_map.get(shipping_status, shipping_status)
