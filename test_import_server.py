#!/usr/bin/env python3
"""Test imports on server - with platform cache fix"""
import sys

# Cache stdlib platform BEFORE inserting project root
import platform as _stdlib_platform
_ = _stdlib_platform.system

sys.path.insert(0, '/home/easykai/easykai-workspace/easykai.cn/auth-center')
sys.path.insert(0, '/home/easykai/easykai-workspace/easykai.cn')

try:
    from plugin_manager.hooks import get_hook_registry
    print('hooks import OK')
    h = get_hook_registry()
    print(f'hook registry: {h}')
except Exception as e:
    import traceback
    print(f'hooks import FAIL: {e}')
    traceback.print_exc()

# Test specific imports from routes.admin (avoid relative import issues)
try:
    # Import the module directly
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'routes.admin',
        '/home/easykai/easykai-workspace/easykai.cn/auth-center/routes/admin.py'
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print('admin import OK (via spec)')
    if hasattr(mod, 'blueprint'):
        print(f'  blueprint: {mod.blueprint.name}')
    if hasattr(mod, 'dashboard'):
        print(f'  dashboard function: {mod.dashboard}')
except Exception as e:
    import traceback
    print(f'admin import FAIL: {e}')
    traceback.print_exc()

print('=== All tests done ===')
