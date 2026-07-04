#!/usr/bin/env python3
"""
Plugin System — PluginRegistry
===============================
Discovers, loads, enables, and manages plugin lifecycle.

Plugin directory structure:
    plugins/
    ├── base.py              # BasePlugin
    ├── registry.py          # ← this file
    ├── hooks.py             # EventBus
    ├── __init__.py          # load_plugins()
    └── your_plugin/
        ├── __init__.py      # Must contain BasePlugin subclass
        ├── plugin.json      # Metadata
        ├── i18n/            # Plugin's own translations
        │   ├── zh-CN.yml
        │   └── en.yml
        └── README.zh-CN.md  # Plugins docs in various languages
"""

import os
import sys
import json
import importlib
import threading
from typing import Dict, List, Optional, Any

from plugins.base import BasePlugin, clear_plugin_yaml_cache
from plugins.hooks import EventName, get_event_bus


class PluginInfo:
    """Runtime info for a loaded plugin."""

    def __init__(self, name: str, path: str, metadata: dict):
        self.name = name
        self.path = path
        self.metadata = metadata
        self.instance: Optional[BasePlugin] = None
        self.status: str = 'discovered'  # discovered | loaded | enabled | disabled | error

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'version': self.metadata.get('version', '0.0.0'),
            'description': self.metadata.get('description', ''),
            'author': self.metadata.get('author', ''),
            'enabled': self.metadata.get('enabled', True),
            'depends_on': self.metadata.get('depends_on', []),
            'status': self.status,
        }


class PluginRegistry:
    """Central registry for all plugins."""

    def __init__(self, plugins_dir: str):
        self.plugins_dir = os.path.abspath(plugins_dir)
        self._plugins: Dict[str, PluginInfo] = {}
        self._lock = threading.Lock()
        self._bus = get_event_bus()

    # ── Discovery ──

    def discover(self) -> List[str]:
        """Scan plugins/ directory for plugin subdirectories.

        Returns list of discovered plugin names.
        A valid plugin must have both __init__.py and plugin.json.
        """
        discovered = []
        if not os.path.isdir(self.plugins_dir):
            return discovered
        for entry in sorted(os.listdir(self.plugins_dir)):
            plugin_dir = os.path.join(self.plugins_dir, entry)
            if not os.path.isdir(plugin_dir):
                continue
            if entry.startswith('_') or entry.startswith('.'):
                continue
            if not os.path.isfile(os.path.join(plugin_dir, '__init__.py')):
                continue
            if not os.path.isfile(os.path.join(plugin_dir, 'plugin.json')):
                continue
            discovered.append(entry)
        return discovered

    # ── Load ──

    def load(self, name: str) -> Optional[PluginInfo]:
        """Load a single plugin by name."""
        with self._lock:
            if name in self._plugins:
                return self._plugins[name]

            plugin_dir = os.path.join(self.plugins_dir, name)
            meta_path = os.path.join(plugin_dir, 'plugin.json')

            if not os.path.isdir(plugin_dir):
                print(f'[Plugin] {name}: directory not found')
                return None
            if not os.path.isfile(meta_path):
                print(f'[Plugin] {name}: plugin.json not found')
                return None

            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f'[Plugin] {name}: failed to read plugin.json: {e}')
                info = PluginInfo(name, plugin_dir, {})
                info.status = 'error'
                self._plugins[name] = info
                return info

            info = PluginInfo(name, plugin_dir, metadata)

            # Import the plugin module
            try:
                if plugin_dir not in sys.path:
                    sys.path.insert(0, self.plugins_dir)
                    sys.path.insert(0, plugin_dir)

                mod = importlib.import_module(name)
                # Find BasePlugin subclass in the module
                instance = None
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, BasePlugin) and attr is not BasePlugin:
                        instance = attr()
                        instance._config = metadata.get('config', {})
                        instance._load_i18n()
                        break

                if instance is None:
                    print(f'[Plugin] {name}: no BasePlugin subclass found')
                    info.status = 'error'
                    self._plugins[name] = info
                    return info

                info.instance = instance
                info.status = 'loaded'
                self._plugins[name] = info
                return info

            except Exception as e:
                print(f'[Plugin] {name}: load error: {e}')
                import traceback
                traceback.print_exc()
                info.status = 'error'
                self._plugins[name] = info
                return info

    # ── Enable / Disable ──

    def enable(self, name: str) -> bool:
        """Enable a plugin: check deps, call on_enable, register handlers."""
        info = self._plugins.get(name)
        if not info or not info.instance:
            print(f'[Plugin] {name}: not loaded')
            return False

        if info.status == 'enabled':
            return True

        # Check dependencies
        deps = info.metadata.get('depends_on', [])
        for dep in deps:
            dep_info = self._plugins.get(dep)
            if not dep_info or dep_info.status != 'enabled':
                print(f'[Plugin] {name}: dependency {dep} not enabled')
                return False

        try:
            result = info.instance.on_enable(self)
            if not result:
                print(f'[Plugin] {name}: on_enable returned False')
                info.status = 'error'
                return False

            # Register event handlers
            handlers = info.instance.get_event_handlers()
            for event, handler in handlers.items():
                self._bus.on(event, handler)

            info.status = 'enabled'
            print(f'[Plugin] ✅ {name} v{info.metadata.get("version", "?")} enabled')
            return True

        except Exception as e:
            print(f'[Plugin] {name}: enable error: {e}')
            info.status = 'error'
            return False

    def disable(self, name: str) -> bool:
        """Disable a plugin: call on_disable, unregister handlers."""
        info = self._plugins.get(name)
        if not info or not info.instance:
            return False

        try:
            result = info.instance.on_disable(self)
            # Unregister event handlers
            handlers = info.instance.get_event_handlers()
            for event, handler in handlers.items():
                self._bus.off(event, handler)

            info.status = 'disabled'
            print(f'[Plugin] {name} disabled')
            return result

        except Exception as e:
            print(f'[Plugin] {name}: disable error: {e}')
            return False

    def install(self, name: str) -> bool:
        """Install a plugin: call on_install."""
        info = self._plugins.get(name)
        if not info or not info.instance:
            return False
        try:
            result = info.instance.on_install(self)
            if result:
                print(f'[Plugin] ✅ {name} installed')
            return result
        except Exception as e:
            print(f'[Plugin] {name}: install error: {e}')
            return False

    def uninstall(self, name: str) -> bool:
        """Uninstall a plugin: disable + on_uninstall + clear cache."""
        info = self._plugins.get(name)
        if not info or not info.instance:
            return False
        self.disable(name)
        try:
            result = info.instance.on_uninstall(self)
            clear_plugin_yaml_cache(name)
            self._plugins.pop(name, None)
            if result:
                print(f'[Plugin] {name} uninstalled')
            return result
        except Exception as e:
            print(f'[Plugin] {name}: uninstall error: {e}')
            return False

    # ── Mount routes ──

    def mount_all(self, app):
        """Register all enabled plugins' blueprints onto Flask app."""
        for name, info in self._plugins.items():
            if info.status != 'enabled' or not info.instance:
                continue
            bps = info.instance.register_routes()
            for bp in bps:
                prefix = f'/plugin/{name}'
                app.register_blueprint(bp, url_prefix=prefix)
                print(f'[Plugin] {name}: mounted {prefix}')

    # ── Query ──

    def get(self, name: str) -> Optional[BasePlugin]:
        """Get plugin instance by name."""
        info = self._plugins.get(name)
        return info.instance if info else None

    def get_info(self, name: str) -> Optional[PluginInfo]:
        return self._plugins.get(name)

    def is_enabled(self, name: str) -> bool:
        info = self._plugins.get(name)
        return info is not None and info.status == 'enabled'

    def count(self) -> int:
        return len(self._plugins)

    def count_enabled(self) -> int:
        return sum(1 for p in self._plugins.values() if p.status == 'enabled')

    def list_all(self) -> List[dict]:
        return [info.to_dict() for info in self._plugins.values()]

    def load_all(self) -> List[str]:
        """Discover and load all plugins. Returns list of loaded names."""
        loaded = []
        for name in self.discover():
            info = self.load(name)
            if info and info.status != 'error':
                loaded.append(name)
        return loaded
