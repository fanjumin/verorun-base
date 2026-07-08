#!/usr/bin/env python3
"""
Plugin Manager — 管理 API（供 Admin 后台调用）
================================================
9 个 REST 端点，返回 JSON。

端点列表:
  GET    /admin/plugins              — 列出所有插件
  GET    /admin/plugins/discover     — 扫描新插件
  POST   /admin/plugins/<id>/install  — 安装
  POST   /admin/plugins/<id>/enable   — 启用
  POST   /admin/plugins/<id>/disable  — 禁用
  POST   /admin/plugins/<id>/activate — 激活
  POST   /admin/plugins/<id>/uninstall— 卸载
  GET    /admin/plugins/<id>/config   — 读取配置
  POST   /admin/plugins/<id>/config   — 保存配置
"""

import json
import traceback
from datetime import datetime
from flask import Blueprint, jsonify, request

from .manager import PluginManager
from .models import PluginStatus
from .exceptions import PluginError

bp = Blueprint('plugin_manager_api', __name__, url_prefix='/admin/plugins')


def _get_manager() -> PluginManager:
    """从 Flask 扩展中获取 PluginManager 实例"""
    try:
        from flask import current_app
        mgr = current_app.extensions.get('plugin_manager')
        if mgr is None:
            return None
        return mgr
    except Exception:
        return None


def _json_result(success: bool, data=None, error: str = None, code: int = 200):
    """统一 json 响应"""
    resp = {'success': success}
    if data is not None:
        resp['data'] = data
    if error:
        resp['error'] = error
    return jsonify(resp), code


def _info_to_dict(info) -> dict:
    """PluginInfo → dict，用于 JSON 序列化"""
    d = info.to_dict()
    d['status'] = info.status.value if hasattr(info.status, 'value') else info.status
    # 确保 metadata 是 dict
    if isinstance(d.get('metadata'), str):
        d['metadata'] = json.loads(d['metadata'])
    # 处理 config（确保不超长）
    if isinstance(d.get('config'), str):
        d['config'] = json.loads(d['config'])
    return d


# ── 1. 列出所有插件 ────────────────────────────────────────────────

@bp.route('', methods=['GET'])
def list_plugins():
    """列出所有插件（含状态、版本信息）"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    status_filter = request.args.get('status')
    plugins = [p for p in mgr.list_plugins(status_filter)]
    return _json_result(True, data=[_info_to_dict(p) for p in plugins])


# ── 2. 发现新插件 ──────────────────────────────────────────────────

@bp.route('/discover', methods=['GET'])
def discover_plugins():
    """扫描 plugins/ 目录，返回所有插件（含已安装的）"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    try:
        all_plugins = mgr.discover_all()
        # 标记已安装
        installed_ids = {p.identifier for p in mgr._cache.values()}
        dicts = []
        for p in all_plugins:
            d = _info_to_dict(p)
            d['installed'] = p.identifier in installed_ids
            if p.identifier in mgr._cache:
                cached = mgr._cache[p.identifier]
                d['status'] = cached.status.value if cached.status else 'unknown'
            dicts.append(d)

        return _json_result(True, data={
            'total': len(dicts),
            'plugins': dicts,
        })
    except Exception as e:
        return _json_result(False, error=str(e), code=500)


# ── 3. 安装 ────────────────────────────────────────────────────────

@bp.route('/<identifier>/install', methods=['POST'])
def install_plugin(identifier: str):
    """安装插件"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    try:
        info = mgr.install(identifier)
        return _json_result(True, data=_info_to_dict(info))
    except PluginError as e:
        return _json_result(False, error=str(e), code=400)
    except Exception as e:
        traceback.print_exc()
        return _json_result(False, error=f'Install failed: {e}', code=500)


# ── 4. 启用 ────────────────────────────────────────────────────────

@bp.route('/<identifier>/enable', methods=['POST'])
def enable_plugin(identifier: str):
    """启用插件（执行 setup）"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    try:
        info = mgr.enable(identifier)
        return _json_result(True, data=_info_to_dict(info))
    except PluginError as e:
        return _json_result(False, error=str(e), code=400)
    except Exception as e:
        traceback.print_exc()
        return _json_result(False, error=f'Enable failed: {e}', code=500)


# ── 5. 禁用 ────────────────────────────────────────────────────────

@bp.route('/<identifier>/disable', methods=['POST'])
def disable_plugin(identifier: str):
    """禁用插件"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    try:
        info = mgr.disable(identifier)
        return _json_result(True, data=_info_to_dict(info))
    except PluginError as e:
        return _json_result(False, error=str(e), code=400)
    except Exception as e:
        traceback.print_exc()
        return _json_result(False, error=f'Disable failed: {e}', code=500)


# ── 6. 激活 ────────────────────────────────────────────────────────

@bp.route('/<identifier>/activate', methods=['POST'])
def activate_plugin(identifier: str):
    """激活插件（加载模块 + 注册路由）"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    try:
        info = mgr.activate(identifier)
        return _json_result(True, data=_info_to_dict(info))
    except PluginError as e:
        return _json_result(False, error=str(e), code=400)
    except Exception as e:
        traceback.print_exc()
        return _json_result(False, error=f'Activate failed: {e}', code=500)


# ── 7. 卸载 ────────────────────────────────────────────────────────

@bp.route('/<identifier>/uninstall', methods=['POST'])
def uninstall_plugin(identifier: str):
    """卸载插件（需要确认）"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    # 安全确认: 必须传 confirm=true
    confirm = request.json.get('confirm', False) if request.is_json else False
    if not confirm:
        return _json_result(False, error='请确认卸载（confirm=true）', code=400)

    try:
        mgr.uninstall(identifier)
        return _json_result(True, data={'identifier': identifier, 'status': 'uninstalled'})
    except PluginError as e:
        return _json_result(False, error=str(e), code=400)
    except Exception as e:
        traceback.print_exc()
        return _json_result(False, error=f'Uninstall failed: {e}', code=500)


# ── 8. 读取配置 ────────────────────────────────────────────────────

@bp.route('/<identifier>/config', methods=['GET'])
def get_plugin_config(identifier: str):
    """读取插件配置"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    info = mgr.get_info(identifier)
    if not info:
        return _json_result(False, error=f'Plugin "{identifier}" not found', code=404)

    return _json_result(True, data={
        'identifier': identifier,
        'config': info.config,
        'settings_schema': info.settings_schema,
    })


# ── 9. 保存配置 ────────────────────────────────────────────────────

@bp.route('/<identifier>/config', methods=['POST'])
def set_plugin_config(identifier: str):
    """保存插件配置"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    if not request.is_json:
        return _json_result(False, error='请求体必须是 JSON', code=400)

    config = request.json
    if not isinstance(config, dict):
        return _json_result(False, error='配置必须是键值对对象', code=400)

    try:
        for key, value in config.items():
            mgr.set_config(identifier, key, value)
        info = mgr.get_info(identifier)
        return _json_result(True, data={
            'identifier': identifier,
            'config': info.config if info else config,
        })
    except PluginError as e:
        return _json_result(False, error=str(e), code=400)
    except Exception as e:
        traceback.print_exc()
        return _json_result(False, error=f'Config save failed: {e}', code=500)


# ── 10. 列出所有 Action 钩子 ─────────────────────────────────

@bp.route('/hooks/actions', methods=['GET'])
def list_hook_actions():
    """列出所有已注册的 Action 钩子"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)
    hook_name = request.args.get('hook')
    data = mgr._hook_registry.list_actions(hook_name)
    return _json_result(True, data=data)


# ── 11. 列出所有 Filter 钩子 ─────────────────────────────────

@bp.route('/hooks/filters', methods=['GET'])
def list_hook_filters():
    """列出所有已注册的 Filter 钩子"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)
    hook_name = request.args.get('hook')
    data = mgr._hook_registry.list_filters(hook_name)
    return _json_result(True, data=data)


# ── 12. 依赖拓扑排序 ─────────────────────────────────────

@bp.route('/dependency-order', methods=['GET'])
def dependency_order():
    """返回拓扑排序后的安装/激活顺序"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)
    try:
        order = mgr.resolve_install_order()
        return _json_result(True, data={'order': order})
    except Exception as e:
        return _json_result(False, error=str(e), code=400)


# ── 13. 依赖树 ──────────────────────────────────────────

@bp.route('/<identifier>/dependencies', methods=['GET'])
def plugin_dependencies(identifier: str):
    """获取插件依赖树"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)
    tree = mgr.get_dependency_tree(identifier)
    dependents = mgr.get_dependents_tree(identifier)
    return _json_result(True, data={'depends_on': tree, 'depended_by': dependents})


# ── 14. 配置校验（不保存） ───────────────────────────────

@bp.route('/<identifier>/config/validate', methods=['POST'])
def validate_plugin_config(identifier: str):
    """校验插件配置（不保存）"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    config = request.json if request.is_json else None
    result = mgr.validate_config(identifier, config)
    return _json_result(result['success'], data={
        'errors': result['errors'],
        'schema': result['schema'],
    }, error=result['errors'][0] if result['errors'] else None)


# ── 15. 批量保存配置（带校验） ───────────────────────────

@bp.route('/<identifier>/config/batch', methods=['POST'])
def batch_save_config(identifier: str):
    """批量保存配置（带 Schema 校验 + 类型转换）"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    if not request.is_json:
        return _json_result(False, error='请求体必须是 JSON', code=400)

    config = request.json
    if not isinstance(config, dict):
        return _json_result(False, error='配置必须是键值对对象', code=400)

    result = mgr.set_config_batch(identifier, config)
    if result['success']:
        return _json_result(True, data={
            'errors': result['errors'],
            'config': result['coerced'],
        })
    return _json_result(False, data={
        'errors': result['errors'],
    }, error=result['errors'][0] if result['errors'] else None)


# ── 16. 读取插件日志 ─────────────────────────────────────

@bp.route('/<identifier>/log', methods=['GET'])
def plugin_log(identifier: str):
    """读取插件日志最后 N 行"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    try:
        lines = int(request.args.get('lines', 50))
    except ValueError:
        lines = 50
    if lines < 1:
        lines = 50
    if lines > 500:
        lines = 500

    content = mgr.read_log(identifier, lines)
    return _json_result(True, data={'log': content, 'lines': lines})


# ── 17. 清空插件日志 ─────────────────────────────────────

@bp.route('/<identifier>/log', methods=['DELETE'])
def clear_plugin_log(identifier: str):
    """清空插件日志"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    ok = mgr.clear_log(identifier)
    return _json_result(ok, data={'cleared': ok})


# ====================================================================
# 商店 API
# ====================================================================

# ── 18. 浏览商店 ─────────────────────────────────────────

@bp.route('/store/browse', methods=['GET'])
def store_browse():
    """浏览商店插件列表"""
    mgr = _get_manager()
    if not mgr or not mgr.store_client:
        return _json_result(False, error='Store not available', code=503)

    query = request.args.get('q', '')
    category = request.args.get('category', '')
    price_type = request.args.get('price_type', '')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))

    data = mgr.store_client.search(query, category, price_type, page, page_size)
    return _json_result(True, data=data)


# ── 19. 商店插件详情 ─────────────────────────────────────

@bp.route('/store/<identifier>', methods=['GET'])
def store_detail(identifier: str):
    """商店插件详情"""
    mgr = _get_manager()
    if not mgr or not mgr.store_client:
        return _json_result(False, error='Store not available', code=503)

    detail = mgr.store_client.get_detail(identifier)
    if not detail:
        return _json_result(False, error=f'Plugin "{identifier}" not found in store', code=404)
    return _json_result(True, data=detail)


# ── 20. 从商店安装 ───────────────────────────────────────

@bp.route('/store/<identifier>/install', methods=['POST'])
def store_install(identifier: str):
    """从商店安装插件（未来: 下载 + 解压 + 安装流程）"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    detail = mgr.store_client.get_detail(identifier) if mgr.store_client else None
    if not detail:
        return _json_result(False, error=f'Plugin "{identifier}" not found in store', code=404)

    # 如果已安装，直接返回
    existing = mgr.get_info(identifier)
    if existing and existing.status != PluginStatus.UNKNOWN.value:
        return _json_result(True, data={'identifier': identifier, 'status': 'already_installed'})

    try:
        info = mgr.install(identifier)
        return _json_result(True, data={
            'identifier': identifier,
            'status': 'installed',
            'version': info.version,
        })
    except Exception as e:
        traceback.print_exc()
        return _json_result(False, error=f'Install failed: {e}', code=500)


# ====================================================================
# License API
# ====================================================================

# ── 21. 激活 License ─────────────────────────────────────

@bp.route('/license/activate', methods=['POST'])
def license_activate():
    """激活 License"""
    mgr = _get_manager()
    if not mgr or not mgr.license_manager:
        return _json_result(False, error='License manager not available', code=503)

    data = request.json if request.is_json else {}
    plugin_id = data.get('plugin_id', '')
    license_key = data.get('license_key', '')
    customer_email = data.get('customer_email', '')

    if not plugin_id or not license_key:
        return _json_result(False, error='plugin_id and license_key required', code=400)

    result = mgr.license_manager.activate(plugin_id, license_key, customer_email)
    if result.get('success'):
        return _json_result(True, data=result.get('license', {}))
    return _json_result(False, error=result.get('error', 'activation failed'), code=400)


# ── 22. 验证 License ─────────────────────────────────────

@bp.route('/license/<plugin_id>/validate', methods=['GET'])
def license_validate(plugin_id: str):
    """验证 License"""
    mgr = _get_manager()
    if not mgr or not mgr.license_manager:
        return _json_result(False, error='License manager not available', code=503)

    result = mgr.license_manager.validate(plugin_id)
    return _json_result(result.get('valid', False), data=result)


# ── 23. 反激活 License ───────────────────────────────────

@bp.route('/license/<plugin_id>/deactivate', methods=['POST'])
def license_deactivate(plugin_id: str):
    """反激活 License"""
    mgr = _get_manager()
    if not mgr or not mgr.license_manager:
        return _json_result(False, error='License manager not available', code=503)

    result = mgr.license_manager.deactivate(plugin_id)
    if result.get('success'):
        return _json_result(True, data={'deactivated': True})
    return _json_result(False, error=result.get('error', 'deactivation failed'), code=400)


# ── 24. License 列表 ──────────────────────────────────────

@bp.route('/licenses', methods=['GET'])
def license_list():
    """列出所有 License"""
    mgr = _get_manager()
    if not mgr or not mgr.license_manager:
        return _json_result(False, error='License manager not available', code=503)

    licenses = mgr.license_manager.list_licenses()
    return _json_result(True, data={'licenses': licenses})


# ====================================================================
# 支付 / 购买 API
# ====================================================================

from .payment import (
    get_payment_router, create_payment_order,
    update_payment_order, get_payment_order, OrderStatus,
)
from .subscription import get_subscription_manager


# ── 25. 发起购买 ─────────────────────────────────────────

@bp.route('/store/<identifier>/purchase', methods=['POST'])
def store_purchase(identifier: str):
    """发起购买，返回支付二维码"""
    mgr = _get_manager()
    if not mgr:
        return _json_result(False, error='PluginManager not initialized', code=503)

    store = mgr.store_client
    if not store:
        return _json_result(False, error='Store not available', code=503)

    detail = store.get_detail(identifier)
    if not detail:
        return _json_result(False, error=f'Plugin "{identifier}" not found', code=404)

    if detail.get('price_type') == 'free':
        return _json_result(False, error='This plugin is free, no purchase needed', code=400)

    channel = (request.json or {}).get('channel', 'alipay')
    customer_email = (request.json or {}).get('customer_email', '')
    amount_fen = detail.get('price_amount', 0)
    price_type = detail.get('price_type', 'onetime')

    if amount_fen <= 0:
        return _json_result(False, error='Invalid price', code=400)

    # 检查是否已有 License
    if mgr.license_manager:
        existing = mgr.license_manager.get_license(identifier)
        if existing and existing.get('license_status') in ('active', 'grace'):
            return _json_result(False, data={'license': existing},
                                error='Plugin already licensed', code=409)

    # 创建订单
    order = create_payment_order(
        plugin_id=identifier,
        channel=channel,
        amount_fen=amount_fen,
        subject=detail.get('name', identifier),
        description=detail.get('description', ''),
        customer_email=customer_email,
    )

    # 调用支付网关
    router = get_payment_router()
    provider = router.get_provider(channel)
    result = provider.create_order(order)

    if result.success:
        update_payment_order(
            order.order_no,
            trade_no=result.trade_no,
            qr_code=result.qr_code,
        )
        return _json_result(True, data={
            'order_no': order.order_no,
            'qr_code': result.qr_code,
            'redirect_url': result.redirect_url,
            'amount_fen': amount_fen,
            'price_type': price_type,
            'channel': channel,
        })

    update_payment_order(order.order_no, status='failed')
    return _json_result(False, error=result.error or 'Payment creation failed', code=502)


# ── 26. 查询订单状态 ─────────────────────────────────────

@bp.route('/payment/<order_no>/status', methods=['GET'])
def payment_order_status(order_no: str):
    """查询订单支付状态"""
    order = get_payment_order(order_no)
    if not order:
        return _json_result(False, error='Order not found', code=404)

    return _json_result(True, data=order.to_dict())


# ── 27. 支付回调 Webhook（统一入口） ─────────────────────

@bp.route('/payment/notify/<channel>', methods=['POST'])
def payment_notify(channel: str):
    """支付回调 Webhook"""
    router = get_payment_router()
    provider = router.get_provider(channel)

    if channel == 'alipay':
        raw_data = request.form.to_dict()
    elif channel == 'mock':
        raw_data = request.json or request.form.to_dict()
    else:
        return _json_result(False, error=f'Unknown channel: {channel}', code=400)

    # 验证签名
    is_valid, parsed = provider.verify_notify(raw_data)
    if not is_valid:
        if channel == 'mock':
            parsed = raw_data
        else:
            return 'failure', 400

    trade_status = parsed.get('trade_status', 'TRADE_SUCCESS')
    out_trade_no = parsed.get('out_trade_no', '')
    trade_no = parsed.get('trade_no', '')

    if not out_trade_no:
        return _json_result(False, error='Missing order_no', code=400)

    # 查询订单
    order = get_payment_order(out_trade_no)
    if not order:
        return _json_result(False, error='Order not found', code=404)

    # 幂等：已支付的订单不再重复处理
    if order.status == OrderStatus.PAID:
        return 'success'

    if trade_status in ('TRADE_SUCCESS', 'TRADE_FINISHED'):
        # 支付成功 → 激活 License
        update_payment_order(
            out_trade_no,
            status='paid',
            trade_no=trade_no or parsed.get('trade_no', ''),
            paid_at=datetime.now().isoformat(),
        )

        # 激活 License
        mgr = _get_manager()
        if mgr and mgr.license_manager:
            lic_result = mgr.license_manager.activate(
                plugin_id=order.plugin_id,
                license_key=out_trade_no,
                customer_email=order.customer_email,
            )
            if not lic_result.get('success'):
                print(f'[Payment] License activation failed for {order.plugin_id}')

            # 订阅模式 → 创建订阅记录
            store = mgr.store_client
            if store:
                detail = store.get_detail(order.plugin_id)
                if detail and detail.get('price_type') == 'sub':
                    sm = get_subscription_manager()
                    sm.create(
                        plugin_id=order.plugin_id,
                        license_key=out_trade_no,
                        order_no=out_trade_no,
                        interval_type=detail.get('price_interval', 'month'),
                        amount_fen=detail.get('price_amount', 0),
                    )

        # 触发购买成功钩子
        _fire_payment_hook(order.plugin_id, 'purchase', out_trade_no)

        return 'success'

    return 'pending', 200


# ── 28. 退款 ─────────────────────────────────────────────

@bp.route('/payment/<order_no>/refund', methods=['POST'])
def payment_refund(order_no: str):
    """退款"""
    order = get_payment_order(order_no)
    if not order:
        return _json_result(False, error='Order not found', code=404)

    if order.status != OrderStatus.PAID:
        return _json_result(False, error='Order not paid or already refunded', code=400)

    router = get_payment_router()
    provider = router.get_provider(order.channel)
    result = provider.refund(order_no)

    if result.success:
        update_payment_order(order_no, status='refunded')
        if _get_manager() and _get_manager().license_manager:
            _get_manager().license_manager.deactivate(order.plugin_id)
        _fire_payment_hook(order.plugin_id, 'refund', order_no)
        return _json_result(True, data={'refunded': True})

    return _json_result(False, error=result.error or 'Refund failed', code=502)


# ====================================================================
# 订阅管理 API
# ====================================================================

# ── 29. 列出所有订阅 ─────────────────────────────────────

@bp.route('/subscriptions', methods=['GET'])
def list_subscriptions():
    """列出所有订阅"""
    sm = get_subscription_manager()
    subs = [s.to_dict() for s in sm.list_subscriptions()]
    return _json_result(True, data={'subscriptions': subs})


# ── 30. 取消订阅 ─────────────────────────────────────────

@bp.route('/subscriptions/<plugin_id>/cancel', methods=['POST'])
def cancel_subscription(plugin_id: str):
    """取消订阅"""
    sm = get_subscription_manager()
    body = request.json or {}
    immediate = body.get('immediate', False)

    ok = sm.cancel(plugin_id, immediate=immediate)
    if ok:
        return _json_result(True, data={'canceled': True, 'immediate': immediate})
    return _json_result(False, error='Subscription not found', code=404)


# ── 31. 手动续费 ─────────────────────────────────────────

@bp.route('/subscriptions/<plugin_id>/renew', methods=['POST'])
def renew_subscription(plugin_id: str):
    """手动续费"""
    sm = get_subscription_manager()
    ok = sm.renew(plugin_id)
    if ok:
        sub = sm.get_subscription(plugin_id)
        return _json_result(True, data=sub.to_dict() if sub else {})
    return _json_result(False, error='Renewal failed', code=400)


# ── 工具: 触发支付相关钩子 ──────────────────────────────

def _fire_payment_hook(plugin_id: str, event: str, order_no: str):
    try:
        mgr = _get_manager()
        if mgr and mgr._hook:
            mgr._hook.do_action(f'plugin/{event}', {
                'plugin_id': plugin_id,
                'order_no': order_no,
            })
    except Exception as e:
        print(f'[Payment] Hook error: {e}')
