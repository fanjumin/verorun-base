#!/usr/bin/env python3
"""
Plugin System — Entry Point
=============================
"""

import os

_registry = None


def get_plugin_registry():
    """Get the global PluginRegistry singleton."""
    global _registry
    if _registry is None:
        from plugins.registry import PluginRegistry
        plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        _registry = PluginRegistry(plugins_dir)
    return _registry


def load_plugins(app):
    """Discover, load, enable, and mount all plugins onto a Flask app.

    Called from auth_blueprint.py during app initialization.
    """
    registry = get_plugin_registry()

    # Discover and load
    loaded = registry.load_all()
    print(f'[Plugin] discovered {len(loaded)} plugins: {loaded}')

    # Enable all (respects plugin.json enabled flag)
    for name in loaded:
        info = registry.get_info(name)
        if info and info.metadata.get('enabled', True):
            registry.enable(name)

    # Mount routes
    registry.mount_all(app)
    print(f'[Plugin] ✅ {registry.count_enabled()} plugins active')

    return registry
