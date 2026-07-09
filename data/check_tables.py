#!/usr/bin/env python3
import sys, os, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'auth-center'))
os.environ['DB_PATH'] = os.path.join(os.path.dirname(__file__), 'data', 'x7k2m9a4.db')

try:
    from models.database import get_db, DB_PATH
    print(f'OK: DB_PATH={DB_PATH}')
except Exception as e:
    print(f'IMPORT ERROR: {e}')
    traceback.print_exc()
    sys.exit(1)

with get_db() as m:
    tables = set(r[0] for r in m.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
    for t in ['site_domains', 'i18n_strings', 'enterprise_verifications', 'cluster_services', 'cms_posts']:
        exists = t in tables
        print(f'{t}: {exists}')
    print(f'Total tables: {len(tables)}')
