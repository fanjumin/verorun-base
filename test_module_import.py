#!/usr/bin/env python3
"""Test that the analytics module can be imported and filter is registered"""
import sys
sys.path.insert(0, '.')

# Check module can be imported
from plugins.analytics import enrich_dashboard
print('Module loaded OK')
print('Function:', enrich_dashboard)

# Check if filter is registered
from plugin_manager.hooks import get_hook_registry
hooks = get_hook_registry()
filters = hooks.list_filters('dashboard.data')
print('dashboard.data filters:', filters)
