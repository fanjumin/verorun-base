#!/usr/bin/env python3
"""
Plugin System — EventBus
==========================
Publish-subscribe event system for inter-plugin communication.

Events are identified by EventName constants.
Plugins subscribe via get_event_handlers() or bus.on().
"""

import threading
from typing import Dict, Callable, Any


class EventName:
    """Predefined system event constants."""
    APP_READY = 'app.ready'
    APP_SHUTDOWN = 'app.shutdown'
    USER_REGISTERED = 'user.registered'
    USER_LOGIN = 'user.login'
    USER_LOGOUT = 'user.logout'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'
    ORDER_CREATED = 'order.created'
    ORDER_PAID = 'order.paid'
    ORDER_REFUNDED = 'order.refunded'
    ORDER_CANCELLED = 'order.cancelled'
    ORDER_SHIPPED = 'order.shipped'
    ORDER_COMPLETED = 'order.completed'
    SUB_CREATED = 'sub.created'
    SUB_RENEWED = 'sub.renewed'
    SUB_EXPIRED = 'sub.expired'
    SUB_CANCELLED = 'sub.cancelled'
    CMS_CONTENT_PUBLISHED = 'cms.published'
    CMS_CONTENT_UPDATED = 'cms.updated'
    CMS_CONTENT_DELETED = 'cms.deleted'
    SCHEDULER_JOB_STARTED = 'scheduler.job_started'
    SCHEDULER_JOB_COMPLETED = 'scheduler.job_completed'
    SCHEDULER_JOB_FAILED = 'scheduler.job_failed'
    HEALTH_CHECK_PASSED = 'health.passed'
    HEALTH_CHECK_WARNING = 'health.warning'
    HEALTH_CHECK_ERROR = 'health.error'
    PLUGIN_INSTALLED = 'plugin.installed'
    PLUGIN_ENABLED = 'plugin.enabled'
    PLUGIN_DISABLED = 'plugin.disabled'
    PLUGIN_UNINSTALLED = 'plugin.uninstalled'


class EventBus:
    """Simple in-process publish-subscribe event bus."""

    def __init__(self):
        self._handlers: Dict[str, list] = {}
        self._lock = threading.Lock()

    def on(self, event: str, handler: Callable):
        """Subscribe to an event."""
        with self._lock:
            self._handlers.setdefault(event, []).append(handler)

    def off(self, event: str, handler: Callable = None):
        """Unsubscribe. If handler is None, removes all handlers for event."""
        with self._lock:
            if handler is None:
                self._handlers.pop(event, None)
            else:
                handlers = self._handlers.get(event, [])
                self._handlers[event] = [h for h in handlers if h is not handler]

    def emit(self, event: str, **kwargs):
        """Emit an event with keyword arguments."""
        with self._lock:
            handlers = list(self._handlers.get(event, []))
        for handler in handlers:
            try:
                handler(**kwargs)
            except Exception as e:
                print(f'[EventBus] handler error for {event}: {e}')

    def clear(self):
        """Remove all handlers (for testing)."""
        with self._lock:
            self._handlers.clear()


# Module-level singleton
_BUS = None
_BUS_LOCK = threading.Lock()


def get_event_bus() -> EventBus:
    """Get the global EventBus singleton."""
    global _BUS
    if _BUS is None:
        with _BUS_LOCK:
            if _BUS is None:
                _BUS = EventBus()
    return _BUS
