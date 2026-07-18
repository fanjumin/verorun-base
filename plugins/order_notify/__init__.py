"""订单通知插件 — 基于事件系统的自动通知"""
import logging

from plugin_manager.base import BasePlugin
from plugin_manager.event_bus import EventName, get_event_bus
from .models import get_main_db, init_db, close_db

logger = logging.getLogger(__name__)


class OrderNotifyPlugin(BasePlugin):
    name = 'order_notify'
    version = '1.0.0'
    description = '订单通知 — 下单/支付成功/发货/退款时自动发送通知'

    def on_enable(self, registry) -> bool:
        init_db()
        bus = get_event_bus()
        bus.on(EventName.ORDER_CREATED, self._on_created)
        bus.on(EventName.ORDER_PAID, self._on_paid)
        bus.on(EventName.ORDER_SHIPPED, self._on_shipped)
        bus.on(EventName.ORDER_REFUNDED, self._on_refunded)
        bus.on(EventName.ORDER_CANCELLED, self._on_cancelled)
        bus.on(EventName.ORDER_COMPLETED, self._on_completed)
        return True

    def on_disable(self, registry) -> bool:
        bus = get_event_bus()
        bus.off(EventName.ORDER_CREATED, self._on_created)
        bus.off(EventName.ORDER_PAID, self._on_paid)
        bus.off(EventName.ORDER_SHIPPED, self._on_shipped)
        bus.off(EventName.ORDER_REFUNDED, self._on_refunded)
        bus.off(EventName.ORDER_CANCELLED, self._on_cancelled)
        bus.off(EventName.ORDER_COMPLETED, self._on_completed)
        return True

    # ── 通知辅助 ──

    def _notify_user(self, user_id: int, title: str, content: str, link: str = ''):
        """发送站内通知"""
        try:
            from notification_service import send_notification_by_event
            import inspect
            # 兼容不同导入路径
            send_notification_by_event('system', user_id, {
                'title': title,
                'content': content,
                'link_url': link,
            })
        except Exception as e:
            logger.warning(f"[OrderNotify] 发送通知失败: {e}")

    # ── 事件处理 ──

    def _on_created(self, **kw):
        """下单通知"""
        uid = kw.get('user_id')
        oid = kw.get('order_id')
        total = kw.get('total', 0)
        if uid:
            self._notify_user(
                uid,
                self.t(_('Order has been created')),
                self.t('您的订单 %s 已创建，金额 ¥%.2f，请尽快完成支付。') % (oid, total),
                f'/shop/orders'
            )

    def _on_paid(self, **kw):
        """支付成功通知"""
        oid = kw.get('order_id')
        uid = kw.get('user_id', 0)
        # 事件参数里可能没有 user_id，从数据库查
        if not uid:
            try:
                with get_main_db() as conn:
                    row = conn.execute(
                        'SELECT user_id FROM order_items WHERE order_id=? LIMIT 1', (oid,)
                    ).fetchone()
                    if row:
                        uid = row['user_id']
            except Exception:
                pass
        if uid:
            self._notify_user(
                uid,
                self.t(_('Payment successful')),
                self.t(_('Your order %s has been successfully paid. We will ship it to you as soon as possible!')) % oid,
                f'/shop/orders'
            )

    def _on_shipped(self, **kw):
        """发货通知"""
        uid = kw.get('user_id')
        oid = kw.get('order_id')
        company = kw.get('company', '')
        tracking = kw.get('tracking_number', '')
        if uid:
            msg = self.t(_('Your order %s has been shipped!')) % oid
            if company and tracking:
                msg += self.t('\n快递: %s | 单号: %s') % (company, tracking)
            self._notify_user(uid, self.t(_('Shipped')), msg, f'/shop/orders')

    def _on_refunded(self, **kw):
        """退款通知"""
        uid = kw.get('user_id')
        oid = kw.get('order_id')
        reason = kw.get('reason', '')
        if uid:
            msg = self.t('您的订单 %s 已收到退款申请') % oid
            if reason:
                msg += self.t('\n原因: %s') % reason
            self._notify_user(uid, self.t('退款申请已提交'), msg, f'/shop/orders')

    def _on_cancelled(self, **kw):
        """取消通知"""
        uid = kw.get('user_id')
        oid = kw.get('order_id')
        if uid:
            self._notify_user(uid, self.t(_('Order canceled')),
                              self.t(_('Your order %s has been canceled.')) % oid, f'/shop/orders')

    def _on_completed(self, **kw):
        """完成通知"""
        uid = kw.get('user_id')
        oid = kw.get('order_id')
        if uid:
            self._notify_user(uid, self.t(_('Order completed')),
                              self.t('您的订单 %s 已完成，欢迎再次光临！请给商品评价吧。') % oid,
                              f'/shop/orders')
