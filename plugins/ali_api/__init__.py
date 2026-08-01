#!/usr/bin/env python3
"""
1688 Supply Chain Plugin — AliApiPlugin
=========================================
Provides 1688 product sourcing, AI optimization, and local publishing.

i18n: Uses self.t() for all user-facing strings.
      Translations in:  plugins/ali_api/i18n/{locale}.yml
"""

from plugin_manager.base import BasePlugin
from .plugin_i18n import set_plugin


class AliApiPlugin(BasePlugin):
    name = 'ali_api'
    version = '1.0.0'
    description = '1688 供应链采集插件 — 商品搜索、AI 优化、本地商城发布'
    author = 'VeroRun'

    def on_enable(self, registry):
        """插件启用时: 初始化独立数据库表 + 设置 i18n 桥接"""
        try:
            from .models import init_tables
            init_tables()
        except Exception as e:
            print(f'[AliApi] DB init warning: {e}')
        set_plugin(self)
        # 注册订单监听
        try:
            from plugin_manager.event_bus import get_event_bus, EventName
            bus = get_event_bus()
            bus.on(EventName.ORDER_PAID, self._on_order_paid)
        except Exception as e:
            print(f'[AliApi] EventBus init warning: {e}')
        return True

    def on_disable(self):
        """插件禁用时注销事件监听"""
        try:
            from plugin_manager.event_bus import get_event_bus, EventName
            get_event_bus().off(EventName.ORDER_PAID, self._on_order_paid)
        except Exception:
            pass

    def _on_order_paid(self, **kwargs):
        """订单支付后：检查是否涉及 1688 货源，自动创建采购单草稿"""
        order_id = kwargs.get('order_id')
        if not order_id:
            return
        try:
            import json, logging
            logger = logging.getLogger(__name__)
            with get_db() as conn:
                from .models import AliPurchaseOrder
                # 通过主库查询该订单的所有商品
                from .models import get_main_db
                with get_main_db() as main_conn:
                    items = main_conn.execute(
                        """SELECT oi.*, p.features, p.title as prod_title
                           FROM order_items oi
                           JOIN products p ON oi.product_id = p.id
                           WHERE oi.order_id = %s""", (order_id,)
                    ).fetchall()
                for item in items:
                    item = dict(item)
                    try:
                        features = json.loads(item.get('features', '{}'))
                    except (json.JSONDecodeError, TypeError):
                        features = {}
                    if not features.get('ali_source'):
                        continue
                    ali_pid = features.get('ali_product_id', '')
                    if not ali_pid:
                        continue
                    # 检查是否已存在
                    if AliPurchaseOrder.get_by_local_item(conn, item['id']):
                        continue
                    # 从 ali_api_items 获取供应商信息
                    ali_item = main_conn.execute(
                        """SELECT * FROM ali_api_items WHERE product_id=%s""", (ali_pid,)
                    ).fetchone()
                    ali_item = dict(ali_item) if ali_item else {}
                    AliPurchaseOrder.insert(conn, {
                        'local_order_id': item['order_id'],
                        'local_order_item_id': item['id'],
                        'product_id': item['product_id'],
                        'ali_product_id': ali_pid,
                        'quantity': item.get('quantity', 1),
                        'price': float(item.get('unit_price', 0)),
                        'total_fee': float(item.get('subtotal', 0)),
                        'supplier_name': ali_item.get('seller_name', ''),
                        'supplier_id': ali_item.get('seller_id', ''),
                    })
                conn.commit()
                logger.info(f'[AliApi] 已为订单 {order_id} 创建采购单草稿')
        except Exception as e:
            print(f'[AliApi] Order listening exception: {e}')

    def register_routes(self):
        """注册路由蓝图"""
        from .routes.admin import ali_admin_bp
        return [ali_admin_bp]


def get_db():
    """快捷访问独立数据库（供事件监听内使用）"""
    from .models import get_db as _get_db
    return _get_db()
