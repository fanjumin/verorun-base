"""WSGI wrapper: fix sys.path then run gunicorn for admin (port 8084).
Usage: python3 run_admin_wsgi.py -c gunicorn_admin.conf.py
"""
import sys, os

ROOT = os.path.dirname(os.path.abspath(__file__))
while ROOT in sys.path:
    sys.path.remove(ROOT)
while '' in sys.path:
    sys.path.remove('')

# Add auth-center + project root for imports
sys.path.insert(0, os.path.join(ROOT, 'auth-center'))
sys.path.append(ROOT)

import gunicorn.app.wsgiapp as wsgiapp
sys.argv = ['gunicorn'] + sys.argv[1:] + ['admin.app:app']
wsgiapp.run()
