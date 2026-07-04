#!/usr/bin/env python3
"""
Plugin System — BasePlugin abstract class
==========================================
All plugins must inherit from BasePlugin.

i18n: plugins use their own i18n/{locale}.yml files,
      accessed via self.t() method — completely isolated
      from system i18n _().
"""

import os
import yaml
from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod

_YAML_CACHE: Dict[str, Dict[str, Dict[str, str]]] = {}
"""Cache: {plugin_name: {locale: {source: translation}}}"""


def _load_plugin_yaml(plugin_name: str, i18n_dir: str) -> Dict[str, Dict[str, str]]:
    """Load all yaml files from a plugin's i18n/ directory.

    Returns {locale: {source: translation}}
    """
    if plugin_name in _YAML_CACHE:
        return _YAML_CACHE[plugin_name]

    result = {}
    if not os.path.isdir(i18n_dir):
        _YAML_CACHE[plugin_name] = result
        return result

    for fname in os.listdir(i18n_dir):
        if not fname.endswith(('.yml', '.yaml')):
            continue
        locale = fname.rsplit('.', 1)[0]  # 'zh-CN.yml' → 'zh-CN'
        fpath = os.path.join(i18n_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            result[locale] = data
        except Exception:
            result[locale] = {}

    _YAML_CACHE[plugin_name] = result
    return result


def clear_plugin_yaml_cache(plugin_name: str = None):
    """Clear yaml cache for a plugin (or all if None)."""
    if plugin_name:
        _YAML_CACHE.pop(plugin_name, None)
    else:
        _YAML_CACHE.clear()


class BasePlugin(ABC):
    """Abstract base class for all plugins."""

    # ── 必须设置的元数据 ──
    name: str = ''
    version: str = '0.1.0'
    description: str = ''
    author: str = ''
    depends_on: List[str] = []
    config_schema: Dict[str, Any] = {}

    def __init__(self):
        self._config = {}
        self._i18n_data: Dict[str, Dict[str, str]] = {}
        self._load_i18n()

    # ── i18n ──

    def _get_i18n_dir(self) -> str:
        """Return absolute path to this plugin's i18n/ directory."""
        return os.path.join(os.path.dirname(
            __import__(self.__class__.__module__).__file__), 'i18n')

    def _load_i18n(self):
        """Pre-load this plugin's translation files."""
        self._i18n_data = _load_plugin_yaml(self.name, self._get_i18n_dir())

    def t(self, text: str, locale: str = None) -> str:
        """Plugin i18n: translate text using own i18n/{locale}.yml.

        Falls back to original text if no translation found.
        Locale defaults to system DEPLOY_LANG or 'zh-CN'.
        """
        if locale is None:
            try:
                from i18n import get_lang
                locale = get_lang()
            except Exception:
                locale = 'zh-CN'
        translations = self._i18n_data.get(locale, {})
        return translations.get(text, text)

    # ── 生命周期 ──

    def on_install(self, registry) -> bool:
        """Called when plugin is first installed. Override to init DB tables etc."""
        return True

    def on_enable(self, registry) -> bool:
        """Called when plugin is enabled. Override to set up resources."""
        return True

    def on_disable(self, registry) -> bool:
        """Called when plugin is disabled. Override to clean up resources."""
        return True

    def on_uninstall(self, registry) -> bool:
        """Called when plugin is uninstalled. Drop tables, clean config."""
        return True

    # ── 功能注册（可选覆盖） ──

    def register_routes(self) -> List:
        """Return a list of Flask Blueprints to register."""
        return []

    def register_jobs(self) -> List[Dict[str, Any]]:
        """Return a list of APScheduler job config dicts."""
        return []

    def register_dag_nodes(self) -> Dict[str, Any]:
        """Return {node_type: handler_function} for DAG workflow engine."""
        return {}

    def register_health_checks(self) -> List[Dict[str, Any]]:
        """Return a list of health check item dicts."""
        return []

    def get_event_handlers(self) -> Dict[str, Callable]:
        """Return {event_name: handler_function} to subscribe to system events."""
        return {}

    # ── 工具方法 ──

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a plugin config value from plugin.json 'config' section."""
        return self._config.get(key, default)

    def log(self, message: str, level: str = 'info'):
        """Log a message with plugin name prefix."""
        print(f'[{self.name}/{level}] {message}')

    def validate_config(self) -> List[str]:
        """Validate _config against config_schema. Return list of errors."""
        errors = []
        for key, rules in self.config_schema.items():
            required = rules.get('required', False)
            if required and key not in self._config:
                errors.append(f'{self.name}: missing required config "{key}"')
        return errors
