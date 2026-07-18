"""Check syntax of all modified files."""
import sys, os, py_compile

files = [
    'auth-center/models/cms.py',
    'auth-center/models/database.py',
    'auth-center/routes/admin.py',
    'auth-center/routes/agents.py',
    'auth-center/routes/auth.py',
    'auth-center/routes/cleaner_agent.py',
    'auth-center/routes/footer_admin.py',
    'auth-center/routes/header_admin.py',
    'auth-center/routes/sessions.py',
    'auth-center/routes/shop_admin.py',
    'auth-center/routes/social_media.py',
    'auth-center/routes/user.py',
    'plugins/analytics/tracker.py',
    'plugins/content_factory/routes.py',
    'plugins/sms/models.py',
    'plugins/sms/routes.py',
    'plugins/verification/models.py',
    'plugins/wishlist/__init__.py',
    'plugins/reviews/__init__.py',
    'admin/app.py',
]

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
errors = []
for f in files:
    path = os.path.join(root, f)
    if not os.path.exists(path):
        errors.append(f'{f}: FILE NOT FOUND')
        continue
    try:
        py_compile.compile(path, doraise=True)
        print(f'✅ {f}')
    except py_compile.PyCompileError as e:
        errors.append(f'{f}: {e}')
        print(f'❌ {f}: {e}')

if errors:
    print(f'\n{len(errors)} errors found!')
    sys.exit(1)
else:
    print(f'\nAll files OK!')
