"""商品评价系统插件"""
from i18n import _
import logging
from typing import List

from plugin_manager.base import BasePlugin
from plugin_manager.event_bus import EventName, get_event_bus
from .models import get_db, get_main_db, init_db

logger = logging.getLogger(__name__)


class ReviewsPlugin(BasePlugin):
    name = 'reviews'
    version = '1.1.1'
    description = _('Product Reviews — rate, review, and share photos of purchased products')

    def on_install(self, registry) -> bool:
        """安装时创建插件表"""
        init_db()
        return True

    def on_enable(self, registry) -> bool:
        """订阅事件：支付成功后提示评价"""
        bus = get_event_bus()
        bus.on(EventName.ORDER_PAID, self._on_order_paid)
        return True

    def on_disable(self, registry) -> bool:
        bus = get_event_bus()
        bus.off(EventName.ORDER_PAID, self._on_order_paid)
        return True

    def _on_order_paid(self, **kwargs):
        """支付成功后记录——用户可在订单页写评价"""
        logger.info(f"[Reviews] 订单 {kwargs.get('order_id')} 已支付，可评价")

    def register_routes(self) -> List:
        from .routes import init_routes, reviews_bp
        init_routes(get_db, get_main_db, self.t)
        return [reviews_bp]
