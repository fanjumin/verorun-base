#!/usr/bin/env python3
"""Test admin imports on server from correct project directory."""
import sys
import os

# Change to auth-center directory
os.chdir('/home/easykai/easykai-workspace/easykai.cn/auth-center')
sys.path.insert(0, '.')
sys.path.insert(0, '..')

# Cache stdlib platform
import platform as _stdlib_platform
_ = _stdlib_platform.system

print('=== Testing imports ===')

# Test hooks import
try:
    from plugin_manager.hooks import get_hook_registry
    h = get_hook_registry()
    print(f'hooks OK: {h}')
except Exception as e:
    import traceback
    print(f'hooks FAIL: {e}')
    traceback.print_exc()

# Test admin import
try:
    from routes.admin import blueprint
    print(f'admin blueprint OK: {blueprint.name}')
except Exception as e:
    import traceback
    print(f'admin FAIL: {e}')
    traceback.print_exc()

print('=== Done ===')
