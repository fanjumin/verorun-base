#!/usr/bin/env python3
"""
plugins/hooks.py — 事件钩子系统
================================
提供跨插件的发布-订阅事件机制。

Event hook system for inter-plugin communication.
Supports publish-subscribe pattern for decoupled plugin interaction.

i18n compliance: event descriptions use Chinese source keys.
"""

import os
import sys
import threading
from typing import Callable, Dict, List, Any

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from i18n import _


# ═══════════════════════════════════════════════════════════════
# 预定义事件名称常量
# ═══════════════════════════════════════════════════════════════

class EventName:
    """系统预定义事件名称常量"""

    # ── 应用生命周期 ──
    APP_READY = 'app.ready'
    APP_SHUTDOWN = 'app.shutdown'

    # ── 用户事件 ──
    USER_REGISTERED = 'user.registered'
    USER_LOGIN = 'user.login'
    USER_LOGOUT = 'user.logout'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'

    # ── 订单/支付事件 ──
    ORDER_CREATED = 'order.created'
    ORDER_PAID = 'order.paid'
    ORDER_REFUNDED = 'order.refunded'
    ORDER_CANCELLED = 'order.cancelled'

    # ── 订阅事件 ──
    SUB_CREATED = 'subscription.created'
    SUB_RENEWED = 'subscription.renewed'
    SUB_EXPIRED = 'subscription.expired'
    SUB_CANCELLED = 'subscription.cancelled'

    # ── 内容事件 ──
    CMS_CONTENT_PUBLISHED = 'cms.content_published'
    CMS_CONTENT_UPDATED = 'cms.content_updated'
    CMS_CONTENT_DELETED = 'cms.content_deleted'

    # ── 调度器事件 ──
    SCHEDULER_JOB_STARTED = 'scheduler.job_started'
    SCHEDULER_JOB_COMPLETED = 'scheduler.job_completed'
    SCHEDULER_JOB_FAILED = 'scheduler.job_failed'

    # ── 健康检查事件 ──
    HEALTH_CHECK_PASSED = 'health.check_passed'
    HEALTH_CHECK_WARNING = 'health.check_warning'
    HEALTH_CHECK_ERROR = 'health.check_error'

    # ── 插件事件 ──
    PLUGIN_INSTALLED = 'plugin.installed'
    PLUGIN_ENABLED = 'plugin.enabled'
    PLUGIN_DISABLED = 'plugin.disabled'
    PLUGIN_UNINSTALLED = 'plugin.uninstalled'


# ═══════════════════════════════════════════════════════════════
# 事件描述（用于管理界面展示）
# ═══════════════════════════════════════════════════════════════

EVENT_DESCRIPTIONS: Dict[str, str] = {
    EventName.APP_READY: '应用启动就绪',
    EventName.APP_SHUTDOWN: '应用即将关闭',
    EventName.USER_REGISTERED: '用户注册完成',
    EventName.USER_LOGIN: '用户登录成功',
    EventName.USER_LOGOUT: '用户退出登录',
    EventName.USER_UPDATED: '用户信息更新',
    EventName.USER_DELETED: '用户被删除',
    EventName.ORDER_CREATED: '订单创建',
    EventName.ORDER_PAID: '订单支付完成',
    EventName.ORDER_REFUNDED: '订单退款完成',
    EventName.ORDER_CANCELLED: '订单取消',
    EventName.SUB_CREATED: '订阅创建',
    EventName.SUB_RENEWED: '订阅续费',
    EventName.SUB_EXPIRED: '订阅过期',
    EventName.SUB_CANCELLED: '订阅取消',
    EventName.CMS_CONTENT_PUBLISHED: 'CMS内容发布',
    EventName.CMS_CONTENT_UPDATED: 'CMS内容更新',
    EventName.CMS_CONTENT_DELETED: 'CMS内容删除',
    EventName.SCHEDULER_JOB_STARTED: '定时任务开始',
    EventName.SCHEDULER_JOB_COMPLETED: '定时任务完成',
    EventName.SCHEDULER_JOB_FAILED: '定时任务失败',
    EventName.HEALTH_CHECK_PASSED: '健康检查通过',
    EventName.HEALTH_CHECK_WARNING: '健康检查警告',
    EventName.HEALTH_CHECK_ERROR: '健康检查错误',
    EventName.PLUGIN_INSTALLED: '插件安装完成',
    EventName.PLUGIN_ENABLED: '插件已启用',
    EventName.PLUGIN_DISABLED: '插件已禁用',
    EventName.PLUGIN_UNINSTALLED: '插件已卸载',
}


# ═══════════════════════════════════════════════════════════════
# 事件总线
# ═══════════════════════════════════════════════════════════════

class EventBus:
    """
    中央事件总线 — 单例模式。

    用法:
        bus = get_event_bus()
        bus.on('user.registered', my_handler)
        bus.emit('user.registered', user_id=123)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def on(self, event_name: str, handler: Callable):
        """
        注册事件处理器。

        Args:
            event_name: 事件名称（如 EventName.ORDER_PAID）
            handler: 回调函数，接收 **kwargs 参数
        """
        with self._lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)

    def off(self, event_name: str, handler: Callable):
        """
        注销事件处理器。
        """
        with self._lock:
            if event_name in self._handlers and handler in self._handlers[event_name]:
                self._handlers[event_name].remove(handler)

    def emit(self, event_name: str, **kwargs):
        """
        触发事件，调用所有注册的处理器。
        每个处理器在 try/except 中执行，单个失败不影响其他处理器。

        Args:
            event_name: 事件名称
            **kwargs: 传递给处理器的参数
        """
        with self._lock:
            handlers = list(self._handlers.get(event_name, []))

        if not handlers:
            return

        for handler in handlers:
            try:
                handler(**kwargs)
            except Exception as e:
                print(f'[EventBus] {_("Event handler error")} event={event_name} '
                      f'handler={handler.__name__} error={e}')

    def clear(self):
        """清空所有事件处理器（慎用）"""
        with self._lock:
            self._handlers.clear()

    def get_event_count(self, event_name: str = None) -> int:
        """获取已注册的处理器数量"""
        with self._lock:
            if event_name:
                return len(self._handlers.get(event_name, []))
            return sum(len(h) for h in self._handlers.values())

    def list_events(self) -> List[str]:
        """列出所有已注册的事件类型"""
        with self._lock:
            return list(self._handlers.keys())


# ─── 全局实例访问 ───
_event_bus: EventBus = None


def get_event_bus() -> EventBus:
    """获取全局事件总线（单例）"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def register_plugin_hooks(hooks: Dict[str, Any]):
    """
    批量注册插件的事件处理器。

    Args:
        hooks: 字典 {event_name: handler_fn}
    """
    bus = get_event_bus()
    for event_name, handler in hooks.items():
        bus.on(event_name, handler)
