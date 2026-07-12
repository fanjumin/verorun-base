#!/usr/bin/env python3
"""
Logistics Plugin Services — 物流查询核心逻辑
==============================================
封装快递鸟 Kdniao API 客户端，从插件配置读取。
"""
import hashlib
import json
import base64
import logging
import os
from typing import Dict, Any, List, Tuple
from urllib import request, parse

from .models import get_logistics_db

logger = logging.getLogger(__name__)

# ── 默认配置（环境变量兜底）──
KDNIAO_API_URL = os.environ.get('KDNIAO_API_URL',
    'https://api.kdniao.com/api/dist')


def _get_kdniao_config() -> Tuple[str, str]:
    """读取快递鸟配置：优先环境变量，其次插件配置（完全独立）"""
    eid = os.environ.get('KDNIAO_EBUSINESS_ID', '').strip()
    api_key = os.environ.get('KDNIAO_API_KEY', '').strip()
    if eid and api_key:
        return eid, api_key

    try:
        import flask
        pm = flask.current_app.extensions.get('plugin_manager')
        plugin = pm.get_instance('logistics') if (pm and pm.is_enabled('logistics')) else None
        if plugin:
            peid, pkey = plugin.get_kdniao_config()
            eid = eid or peid
            api_key = api_key or pkey
    except Exception:
        pass
    return eid, api_key


def _generate_data_sign(request_data: str, api_key: str) -> str:
    raw = request_data + api_key
    md5 = hashlib.md5(raw.encode('utf-8')).hexdigest()
    return base64.b64encode(md5.encode('utf-8')).decode('utf-8')


def query_track(shipper_code: str, logistic_code: str,
                order_code: str = '', customer_name: str = '',
                eid: str = '', api_key: str = '') -> Tuple[bool, Dict[str, Any], str]:
    """查询物流轨迹（快递鸟在途监控即时查询, RequestType=8001）"""
    if not eid or not api_key:
        eid, api_key = _get_kdniao_config()
    if not eid or not api_key:
        _log_query(shipper_code, logistic_code, order_code, False, '快递鸟未配置')
        return False, {}, '快递鸟未配置: 请在系统设置→基本设置→物流配送中填写商户ID和API Key'

    req_body = {
        'OrderCode': order_code,
        'ShipperCode': shipper_code,
        'LogisticCode': logistic_code,
    }
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
                formatted = [{'time': t.get('AcceptTime', ''), 'station': t.get('AcceptStation', ''), 'remark': t.get('Remark', '')} for t in traces]
                formatted.sort(key=lambda x: x['time'], reverse=True)
                data = {
                    'shipper_code': shipper_code,
                    'logistic_code': logistic_code,
                    'traces': formatted,
                    'state': int(result.get('State', 0)),
                    'state_text': _state_text(str(result.get('State', '0'))),
                    'state_ex': result.get('StateEx', ''),
                    'location': result.get('Location', ''),
                }
                _log_query(shipper_code, logistic_code, order_code, True)
                return True, data, ''
            else:
                reason = result.get('Reason', '查询失败')
                _log_query(shipper_code, logistic_code, order_code, False, reason)
                return False, {}, f'快递鸟查询失败: {reason}'
    except json.JSONDecodeError as e:
        _log_query(shipper_code, logistic_code, order_code, False, str(e))
        return False, {}, f'解析响应失败: {e}'
    except Exception as e:
        _log_query(shipper_code, logistic_code, order_code, False, str(e))
        return False, {}, f'网络请求失败: {e}'


def _state_text(state: str) -> str:
    return {
        '0': '无轨迹', '1': '已揽收', '2': '在途中', '3': '签收',
        '4': '问题件', '5': '转寄', '6': '退签', '7': '待清关',
        '8': '清关中', '9': '已拒收', '10': '待交付', '11': '已交付', '14': '退货中',
    }.get(state, f'未知({state})')


def get_shipping_status_text(shipping_status: str) -> str:
    return {
        'pending': '待发货',
        'shipped': '已发货',
        'delivered': '已签收',
    }.get(shipping_status, shipping_status)


def _log_query(shipper_code, logistic_code, order_code, success, error_msg=''):
    try:
        conn = get_logistics_db()
        conn.execute(
            'INSERT INTO logistics_queries (shipper_code, logistic_code, order_code, success, error_msg) VALUES (?,?,?,?,?)',
            (shipper_code, logistic_code, order_code, 1 if success else 0, error_msg)
        )
        conn.commit()
    except Exception as e:
        print(f'[LogisticsPlugin] 日志写入失败: {e}')
