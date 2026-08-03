"""WSGI wrapper: fix sys.path then run gunicorn for auth-center.
Usage: python3 run_auth_wsgi.py  -w 4 -b 0.0.0.0:8081
"""
import sys, os

# Strip project root from sys.path before gunicorn imports platform
ROOT = os.path.dirname(os.path.abspath(__file__))
while ROOT in sys.path:
    sys.path.remove(ROOT)
while '' in sys.path:
    sys.path.remove('')

# Add auth-center to path
sys.path.insert(0, os.path.join(ROOT, 'auth-center'))
# Add project root at END (so platform module shadow doesn't affect stdlib)
sys.path.append(ROOT)

import gunicorn.app.wsgiapp as wsgiapp
sys.argv = ['gunicorn'] + sys.argv[1:] + ['auth_server:app']
wsgiapp.run()
